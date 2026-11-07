import asyncio
import json
import logging
import time
import re
import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import httpx
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientMetadata, OAuthMetadata, ProtectedResourceMetadata
from pydantic import ConfigDict, field_validator

from .auth import AuthRequired, BrowserLogin, REDIRECT, SERVER, Vault
from .storage import now

# SDK authentication exceptions can contain protocol internals; show only sanitized UI errors.
logging.getLogger('mcp').addHandler(logging.NullHandler())
logging.getLogger('mcp').propagate = False
logging.getLogger('mcp').setLevel(logging.CRITICAL)


ALLOWED = {
    'get_stock_profile', 'get_company_overview', 'get_stock_listing',
    'get_financial_statement', 'get_financial_analysis', 'get_stock_quote',
    'get_stock_history', 'get_stock_events', 'get_stocks_catalog', 'get_index_constituents',
}


class ToolResponseError(RuntimeError):
    pass


class DataUnavailableError(ToolResponseError):
    pass


class RateLimitError(ToolResponseError):
    def __init__(self, retry_after=2):
        self.retry_after = max(0, float(retry_after))
        super().__init__('Finhay đang giới hạn tốc độ. Kết quả đã tải được giữ lại; chờ rồi bấm Tiếp tục nếu tác vụ đã dừng.')


def tool_error(text):
    # Error content is classified, never echoed verbatim into logs or exports.
    if re.search(r'rate\s*limit|too many requests|\b429\b', text, re.I):
        retry = re.search(r'retry[ _-]*after[\s:=\"]+(\d+(?:\.\d+)?)', text, re.I)
        return RateLimitError(float(retry.group(1)) if retry else 2)
    if re.search(r'unauthorized|invalid[ _-]*token|token[ _-]*expired|authentication[ _-]*required', text, re.I):
        return AuthRequired('Phiên đăng nhập Finhay hết hạn hoặc không còn quyền. Kết nối lại rồi tiếp tục lượt quét.')
    if re.search(r'no (?:financial )?data(?: found| available)?|data not found|không có (?:dữ liệu|báo cáo)', text, re.I):
        return DataUnavailableError('Finhay chưa có dữ liệu cho mã/kỳ này.')
    return ToolResponseError('Finhay trả lỗi dữ liệu cho mã/kỳ này. Có thể thử lại mã lỗi sau.')


def unpack(result):
    if result.isError:
        text = ' '.join(getattr(content, 'text', '') for content in result.content)
        if result.structuredContent:
            text += json.dumps(result.structuredContent, ensure_ascii=False)
        raise tool_error(text)
    if result.structuredContent is not None:
        return result.structuredContent
    for content in result.content:
        if getattr(content, 'type', '') == 'text':
            try:
                data = json.loads(content.text)
                return {'items': data} if isinstance(data, list) else data
            except json.JSONDecodeError:
                continue
    raise RuntimeError('Finhay không trả dữ liệu JSON có cấu trúc.')


def retry_delay(response, attempt):
    value = response.headers.get('Retry-After', '') if response is not None else ''
    try:
        return max(0, float(value))
    except ValueError:
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return min(2 ** attempt, 8)


class MarketClientMetadata(OAuthClientMetadata):
    """SDK scope discovery must never expand this app to account access."""
    model_config = ConfigDict(validate_assignment=True)

    @field_validator('scope', mode='before')
    @classmethod
    def market_only(cls, value):
        return 'read:market'


class PersistentOAuthProvider(OAuthClientProvider):
    """Restore expiry and discovery across processes for the pinned MCP SDK 1.30.

    Its default storage loader does not restore token_expiry_time or AS metadata.
    Keep PKCE, issuer binding, exchanges, refresh and state checks in the SDK.
    """
    async def async_auth_flow(self, request):
        # A background SSE GET can wait for headers for a long time. The SDK's
        # OAuth lock would serialize every tools/call behind it. Stream requests
        # use the established session token; POST remains responsible for refresh.
        if request.method in ('GET', 'DELETE') and str(request.url) == SERVER:
            token = self.context.current_tokens
            if token:
                request.headers['Authorization'] = 'Bearer ' + token.access_token
            yield request
            return
        flow = super().async_auth_flow(request)
        try:
            outgoing = await flow.__anext__()
            while True:
                response = yield outgoing
                outgoing = await flow.asend(response)
        except StopAsyncIteration:
            return
        finally:
            await flow.aclose()

    async def _initialize(self):
        await super()._initialize()
        tokens = self.context.current_tokens
        if tokens:
            self.context.update_token_expiry(tokens)
            if tokens.expires_in is not None and tokens.expires_in <= 30:
                self.context.token_expiry_time = time.time() - 1

    async def _refresh_token(self):
        if self.context.oauth_metadata is None:
            async with httpx.AsyncClient(timeout=20, transport=RetryTransport(lambda _: None, lambda: False)) as http:
                resource = await http.get('https://mcp.fhsc.com.vn/.well-known/oauth-protected-resource')
                resource.raise_for_status()
                prm = ProtectedResourceMetadata.model_validate(resource.json())
                await self._validate_resource_match(prm)
                if [str(u).rstrip('/') for u in prm.authorization_servers] != ['https://mcp.fhsc.com.vn']:
                    raise AuthRequired('Máy chủ xác thực đã thay đổi. Cần kết nối lại.')
                response = await http.get('https://mcp.fhsc.com.vn/.well-known/oauth-authorization-server')
                response.raise_for_status()
                metadata = OAuthMetadata.model_validate(response.json())
                if str(metadata.issuer).rstrip('/') != 'https://mcp.fhsc.com.vn':
                    raise AuthRequired('Issuer OAuth không khớp Finhay.')
                client = self.context.client_info
                if client and str(client.issuer).rstrip('/') != 'https://mcp.fhsc.com.vn':
                    raise AuthRequired('Đăng ký client không khớp issuer. Ngắt kết nối rồi kết nối lại.')
                self.context.oauth_metadata = metadata
                self.context.protected_resource_metadata = prm
                self.context.auth_server_url = 'https://mcp.fhsc.com.vn'
        return await super()._refresh_token()

    async def _handle_refresh_response(self, response):
        previous = self.context.current_tokens.refresh_token if self.context.current_tokens else None
        ok = await super()._handle_refresh_response(response)
        if ok and previous and not self.context.current_tokens.refresh_token:
            self.context.current_tokens.refresh_token = previous
            await self.context.storage.set_tokens(self.context.current_tokens)
        return ok


class Gateway:
    def __init__(self, store, notify=lambda message: None):
        self.store, self.notify = store, notify
        self.session = None
        self.tools = {}
        self.cancelled = lambda: False

    @asynccontextmanager
    async def connect(self, interactive=False, cancelled=lambda: False):
        self.cancelled = cancelled
        browser = BrowserLogin(interactive, self.notify, cancelled)
        provider = PersistentOAuthProvider(
            server_url=SERVER,
            client_metadata=MarketClientMetadata(
                client_name='Finhay Desktop Python', redirect_uris=[REDIRECT],
                grant_types=['authorization_code', 'refresh_token'], response_types=['code'],
                token_endpoint_auth_method='none', scope='read:market'),
            storage=Vault(), redirect_handler=browser.redirect, callback_handler=browser.callback,
        )
        try:
            async with httpx.AsyncClient(auth=provider, timeout=httpx.Timeout(45, read=90),
                                         transport=RetryTransport(self.notify, cancelled)) as http:
                async with streamable_http_client(SERVER, http_client=http) as (read, write, _):
                    async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=400 if interactive else 180)) as session:
                        self.session = session
                        await session.initialize()
                        cursor = None
                        self.tools = {}
                        while True:
                            result = await session.list_tools(cursor=cursor)
                            self.tools.update({t.name: t for t in result.tools})
                            cursor = result.nextCursor
                            if not cursor:
                                break
                        yield self
        finally:
            self.session = None
            await browser.close()

    def tool_name(self, name):
        if name not in ALLOWED:
            raise ValueError('Công cụ ngoài phạm vi chỉ đọc.')
        matches = [n for n in self.tools if n == name or n.endswith('_' + name)]
        if len(matches) != 1:
            raise RuntimeError(f'Kết nối Finhay không cung cấp công cụ {name}.')
        return matches[0]

    async def call(self, name, args, refresh=False):
        cached = self.store.cached(name, args) if not refresh else None
        if cached:
            data, stamp = cached
            return data, stamp, True
        actual = self.tool_name(name)
        from mcp.shared.exceptions import McpError
        for attempt in range(4):
            try:
                try:
                    result = await self.session.call_tool(actual, args)
                except McpError as exc:
                    classified = tool_error(str(exc))
                    if isinstance(classified, (RateLimitError, DataUnavailableError, AuthRequired)):
                        raise classified from exc
                    raise
                data = unpack(result)
                break
            except RateLimitError as exc:
                if attempt == 3:
                    raise
                seconds = exc.retry_after if exc.retry_after > 0 else 2 ** attempt
                self.notify(f'Finhay giới hạn tốc độ. Chờ {math.ceil(seconds)} giây rồi tự thử lại…')
                await self.wait_cooldown(seconds + .25)
        self.store.save_response(name, args, data)
        return data, now(), False

    async def wait_cooldown(self, seconds):
        deadline = asyncio.get_running_loop().time() + seconds
        while asyncio.get_running_loop().time() < deadline:
            if self.cancelled():
                raise asyncio.CancelledError()
            await asyncio.sleep(min(.2, max(0, deadline - asyncio.get_running_loop().time())))

    async def statements(self, symbol, report, period, year, refresh):
        rows = []
        for page in range(1, 5):
            try:
                data, stamp, cached = await self.call('get_financial_statement', dict(symbol=symbol, type=report,
                    period=period, year=year, limit=5, page=page), refresh)
            except DataUnavailableError:
                break
            items = data.get('items', [])
            rows.extend({**row, '_fetched_at': stamp, '_cached': cached} for row in items)
            if len(items) < 5:
                break
        return rows

    async def universe(self, exchange, refresh):
        items = []
        indices = {'HOSE': 'VNINDEX', 'HNX': 'HNXINDEX', 'UPCOM': 'UPCOMINDEX'}
        for ex in ([exchange] if exchange else ['HOSE', 'HNX', 'UPCOM']):
            page = 1
            while True:
                if self.cancelled():
                    raise asyncio.CancelledError()
                # Exchange-wide index membership, sorted by ticker, avoids the
                # changing market-cap order of a live screener during pagination.
                data, _, _ = await self.call('get_index_constituents', dict(symbol=indices[ex], sort='symbol', page=page, page_size=50), refresh)
                batch = data.get('items', [])
                items.extend({**r, 'exchange': r.get('exchange') or ex} for r in batch)
                if not batch or len(batch) < 50 or page * 50 >= data.get('total', float('inf')):
                    break
                page += 1
                if page > 200:
                    raise RuntimeError('Phân trang danh sách mã vượt giới hạn an toàn.')
        return list({r['symbol']: r for r in items if r.get('symbol')}.values())


class RetryTransport(httpx.AsyncBaseTransport):
    def __init__(self, notify, cancelled, inner=None):
        self.inner = inner or httpx.AsyncHTTPTransport()
        self.notify, self.cancelled = notify, cancelled

    async def handle_async_request(self, request):
        # Only retry our read-only MCP server, never replay OAuth token exchanges.
        if request.url.host != 'mcp.fhsc.com.vn':
            return await self.inner.handle_async_request(request)
        await request.aread()
        for attempt in range(4):
            response = None
            try:
                response = await self.inner.handle_async_request(request)
                if response.status_code not in (429, 502, 503, 504) or attempt == 3:
                    return response
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
                if attempt == 3:
                    raise
            delay = retry_delay(response, attempt)
            if response is not None:
                await response.aclose()
            self.notify(f'Finhay tạm giới hạn/kém ổn định; chờ {delay:.0f} giây…')
            deadline = asyncio.get_running_loop().time() + delay
            while asyncio.get_running_loop().time() < deadline:
                if self.cancelled():
                    raise RuntimeError('Đã tạm dừng trong khi chờ thử lại.')
                await asyncio.sleep(min(.2, max(0, deadline - asyncio.get_running_loop().time())))

    async def aclose(self):
        await self.inner.aclose()


def leaf_errors(exc):
    if isinstance(exc, BaseExceptionGroup):
        return [leaf for child in exc.exceptions for leaf in leaf_errors(child)]
    return [exc]


def user_error(exc):
    for error in leaf_errors(exc):
        if isinstance(error, ToolResponseError):
            return str(error)
        if isinstance(error, AuthRequired):
            return str(error)
        if isinstance(error, httpx.HTTPStatusError) and error.response.status_code in (401, 403):
            return 'Cần kết nối lại Finhay hoặc kiểm tra quyền truy cập.'
    return 'Không thực hiện được yêu cầu. Kiểm tra mạng, quyền Finhay, mã và kỳ báo cáo. Chi tiết kỹ thuật: ' + type(leaf_errors(exc)[0]).__name__
