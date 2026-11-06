import asyncio
import json
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

from keyring.backends.Windows import WinVaultKeyring
from keyring.errors import PasswordDeleteError
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

SERVER = 'https://mcp.fhsc.com.vn/mcp'
REDIRECT = 'http://127.0.0.1:8769/callback'
SERVICE = 'FinhayDesktop-v1'


class AuthRequired(Exception):
    pass


class Vault:
    """Explicit Windows backend; chunk records to fit Credential Manager limits."""
    def __init__(self, backend=None):
        self.backend = backend or WinVaultKeyring()

    def read(self, name):
        count = self.backend.get_password(SERVICE, name + ':count')
        if not count:
            return None
        chunks = [self.backend.get_password(SERVICE, f'{name}:{i}') for i in range(int(count))]
        if any(chunk is None for chunk in chunks):
            return None
        return json.loads(''.join(chunks))

    def write(self, name, value):
        self.delete(name)
        data = json.dumps(value)
        chunks = [data[i:i+800] for i in range(0, len(data), 800)]
        for i, chunk in enumerate(chunks):
            self.backend.set_password(SERVICE, f'{name}:{i}', chunk)
        self.backend.set_password(SERVICE, name + ':count', str(len(chunks)))

    def delete(self, name):
        count = self.backend.get_password(SERVICE, name + ':count')
        for key in [f'{name}:{i}' for i in range(int(count or 0))] + [name + ':count']:
            try:
                self.backend.delete_password(SERVICE, key)
            except PasswordDeleteError:
                pass

    async def get_tokens(self):
        data = self.read('tokens')
        if not data:
            return None
        expiry = data.pop('_expires_at', None)
        if expiry is not None:
            data['expires_in'] = max(0, int(expiry - time.time()))
        return OAuthToken.model_validate(data)

    async def set_tokens(self, tokens):
        data = tokens.model_dump(mode='json')
        if tokens.expires_in is not None:
            data['_expires_at'] = time.time() + tokens.expires_in
        self.write('tokens', data)

    async def get_client_info(self):
        data = self.read('client')
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def set_client_info(self, client_info):
        self.write('client', client_info.model_dump(mode='json'))

    def clear(self):
        self.delete('tokens')
        self.delete('client')


class BrowserLogin:
    def __init__(self, interactive, notify, cancelled=lambda: False):
        self.interactive = interactive
        self.notify = notify
        self.cancelled = cancelled
        self.server = None
        self.expected_state = None
        self.future = None

    async def redirect(self, url):
        if not self.interactive:
            raise AuthRequired('Phiên đăng nhập hết hạn. Bấm Kết nối Finhay rồi tiếp tục lượt quét.')
        self.expected_state = parse_qs(urlparse(url).query).get('state', [None])[0]
        self.future = asyncio.get_running_loop().create_future()
        try:
            self.server = await asyncio.start_server(self.handle, '127.0.0.1', 8769, limit=8192)
        except OSError as exc:
            raise AuthRequired('Cổng callback 8769 đang bận. Đóng ứng dụng đang dùng cổng này rồi kết nối lại.') from exc
        self.notify('Đang chờ bạn đăng nhập và cấp quyền trên trình duyệt (tối đa 5 phút)…')
        if not webbrowser.open(url):
            raise AuthRequired('Không mở được trình duyệt mặc định. Kiểm tra cấu hình trình duyệt Windows.')

    async def handle(self, reader, writer):
        try:
            request = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
            line = request.decode('ascii').split('\r\n')[0].split(' ')
            method, path = line[0], urlparse(line[1])
            query = parse_qs(path.query)
            valid = (method == 'GET' and path.path == '/callback' and self.expected_state
                     and query.get('state', [None])[0] == self.expected_state)
            if not valid:
                status, body = '400 Bad Request', 'Invalid callback.'
            elif query.get('iss', ['https://mcp.fhsc.com.vn'])[0] != 'https://mcp.fhsc.com.vn':
                status, body = '400 Bad Request', 'Invalid issuer.'
            elif query.get('error'):
                if not self.future.done():
                    self.future.set_exception(AuthRequired('Bạn đã từ chối hoặc Finhay không cấp quyền đăng nhập.'))
                status, body = '400 Bad Request', 'Authorization declined. Return to Finhay Desktop.'
            elif query.get('code'):
                if not self.future.done():
                    self.future.set_result((query['code'][0], query['state'][0]))
                status, body = '200 OK', 'Callback received. Return to Finhay Desktop to check connection.'
            else:
                status, body = '400 Bad Request', 'Missing authorization code.'
            content = body.encode('utf-8')
            writer.write(f'HTTP/1.1 {status}\r\nContent-Type: text/plain; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(content)}\r\nConnection: close\r\n\r\n'.encode() + content)
            await writer.drain()
        except (ValueError, IndexError, UnicodeDecodeError, asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def callback(self):
        for _ in range(600):
            if self.cancelled():
                raise AuthRequired('Đã hủy đăng nhập.')
            try:
                return await asyncio.wait_for(asyncio.shield(self.future), .5)
            except asyncio.TimeoutError:
                pass
        raise AuthRequired('Hết thời gian chờ đăng nhập. Bấm Kết nối để thử lại.')

    async def close(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
