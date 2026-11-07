import asyncio
import json

import httpx
import pytest

from app.auth import AuthRequired, Vault
from app.client import Gateway
from app.engine import Worker
from app.storage import Store
from test_auth_client import MemoryBackend
from test_finance import corp


def test_sdk_oauth_registration_initialize_call_and_refresh(tmp_path, monkeypatch):
    """Exercise the real MCP SDK and OAuth provider against a simulated HTTP server."""
    vault = Vault(MemoryBackend())
    requests, grants = [], []

    class Login:
        def __init__(self, *args):
            self.state = None

        async def redirect(self, url):
            from urllib.parse import parse_qs, urlparse
            params = parse_qs(urlparse(url).query)
            assert params['code_challenge_method'] == ['S256']
            assert params['scope'] == ['read:market']
            self.state = params['state'][0]

        async def callback(self):
            return 'authorization-code', self.state

        async def close(self):
            pass

    async def respond(request):
        path = request.url.path
        if 'oauth-protected-resource' in path:
            return httpx.Response(200, json={'resource': 'https://mcp.fhsc.com.vn/', 'authorization_servers': ['https://mcp.fhsc.com.vn'], 'scopes_supported': ['read:market', 'read:account']})
        if 'oauth-authorization-server' in path or 'openid-configuration' in path:
            return httpx.Response(200, json={'issuer': 'https://mcp.fhsc.com.vn', 'authorization_endpoint': 'https://mcp.fhsc.com.vn/authorize', 'token_endpoint': 'https://mcp.fhsc.com.vn/token', 'registration_endpoint': 'https://mcp.fhsc.com.vn/register', 'response_types_supported': ['code'], 'code_challenge_methods_supported': ['S256'], 'token_endpoint_auth_methods_supported': ['none']})
        if path == '/register':
            data = json.loads(request.content)
            assert data['scope'] == 'read:market'
            return httpx.Response(201, json={**data, 'client_id': 'desktop-client'})
        if path == '/token':
            from urllib.parse import parse_qs
            form = parse_qs(request.content.decode())
            grants.append(form['grant_type'][0])
            token = {'access_token': 'test-access-token', 'token_type': 'Bearer', 'expires_in': 3600, 'scope': 'read:market'}
            if form['grant_type'][0] != 'refresh_token':
                token['refresh_token'] = 'test-refresh-token'
            return httpx.Response(200, json=token)
        if path == '/mcp':
            if request.headers.get('authorization') != 'Bearer test-access-token':
                return httpx.Response(401, headers={'WWW-Authenticate': 'Bearer resource_metadata="https://mcp.fhsc.com.vn/.well-known/oauth-protected-resource"'})
            body = json.loads(request.content)
            requests.append(body['method'])
            if 'id' not in body:
                return httpx.Response(202)
            if body['method'] == 'initialize':
                result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'test', 'version': '1'}}
            elif body['method'] == 'tools/list':
                result = {'tools': [{'name': 'get_financial_statement', 'inputSchema': {'type': 'object'}}]}
            else:
                assert body['params']['name'] == 'get_financial_statement'
                result = {'content': [{'type': 'text', 'text': '[]'}], 'structuredContent': {'items': [corp(2025, 1, 100, 10, 9)]}}
            return httpx.Response(200, json={'jsonrpc': '2.0', 'id': body['id'], 'result': result})
        return httpx.Response(404)

    monkeypatch.setattr('app.client.Vault', lambda: vault)
    monkeypatch.setattr('app.client.BrowserLogin', Login)
    monkeypatch.setattr('app.client.RetryTransport', lambda *args: httpx.MockTransport(respond))

    async def run():
        store = Store(tmp_path / 'protocol.sqlite3')
        gateway = Gateway(store)
        async with gateway.connect(True):
            rows = await gateway.statements('FPT', 'income-statement', 'quarterly', 2025, True)
            assert rows[0]['year'] == 2025
        assert requests[:3] == ['initialize', 'notifications/initialized', 'tools/list']
        assert grants == ['authorization_code']
        token = vault.read('tokens')
        token['_expires_at'] = 0
        vault.write('tokens', token)
        async with gateway.connect(False):
            await gateway.statements('FPT', 'income-statement', 'quarterly', 2025, True)
        assert grants == ['authorization_code', 'refresh_token']
        assert (await vault.get_tokens()).refresh_token == 'test-refresh-token'
        store.close()
    asyncio.run(run())


class FakeGateway:
    def __init__(self):
        self.calls = []
        self.fail = False

    async def universe(self, exchange, refresh):
        return [{'symbol': s, 'name': s, 'exchange': 'HOSE'} for s in ('FPT', 'VCB')]

    async def statements(self, symbol, report, period, year, refresh):
        self.calls.append(symbol)
        if self.fail:
            raise AuthRequired('Cần đăng nhập lại')
        return [corp(year, q, 100, 10, 9) for q in (1, 4)]

    async def call(self, name, args, refresh=False):
        return {'sector': [{'name': 'Nhóm thử nghiệm', 'level': 3}]}, 'sample', True


def test_scan_pause_resume_and_auth_failure_preserves_pending(tmp_path):
    async def run():
        store = Store(tmp_path / 'scan.sqlite3')
        config = dict(symbols=[], exchange='', refresh=True, year=2025, quarter=1, period='quarterly', basis='standalone')
        gateway = FakeGateway()
        worker = Worker(store, 'scan', config)
        worker.row_ready.connect(lambda result: worker.pause())
        await worker.scan(gateway)
        run_id = store.runs()[0]['id']
        jobs = store.jobs(run_id)
        assert [j['status'] for j in jobs] == ['ok', 'pending']
        gateway.calls.clear()
        resume = Worker(store, 'scan', {'run_id': run_id})
        gateway.fail = True
        with pytest.raises(AuthRequired):
            await resume.scan(gateway)
        assert store.jobs(run_id)[1]['status'] == 'pending'
        gateway.fail = False
        gateway.calls.clear()
        await resume.scan(gateway)
        assert gateway.calls == ['VCB', 'VCB']
        assert all(j['status'] == 'ok' for j in store.jobs(run_id))
        assert len(store.jobs(run_id)) == 2
        store.close()
    asyncio.run(run())
