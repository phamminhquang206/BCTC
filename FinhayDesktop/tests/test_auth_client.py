import asyncio
import json
import time

import httpx
from mcp.shared.auth import OAuthToken
from keyring.errors import PasswordDeleteError

from app.auth import AuthRequired, BrowserLogin, Vault
from app.client import Gateway, RetryTransport, retry_delay, PersistentOAuthProvider, MarketClientMetadata
from app.storage import Store


class MemoryBackend:
    def __init__(self):
        self.data = {}

    def get_password(self, service, key):
        return self.data.get((service, key))

    def set_password(self, service, key, value):
        self.data[(service, key)] = value

    def delete_password(self, service, key):
        if (service, key) not in self.data:
            raise PasswordDeleteError()
        del self.data[(service, key)]


def test_vault_chunk_expiry_and_clear():
    async def run():
        backend = MemoryBackend()
        vault = Vault(backend)
        token = OAuthToken(access_token='x' * 5000, token_type='Bearer', expires_in=120, refresh_token='refresh')
        await vault.set_tokens(token)
        assert max(len(v) for v in backend.data.values()) <= 800
        recovered = await vault.get_tokens()
        assert recovered.access_token == token.access_token
        assert 115 <= recovered.expires_in <= 120
        stored = vault.read('tokens')
        stored['_expires_at'] = time.time() - 10
        vault.write('tokens', stored)
        assert (await vault.get_tokens()).expires_in == 0
        vault.clear()
        assert await vault.get_tokens() is None
    asyncio.run(run())


def test_noninteractive_login_does_not_open_browser(monkeypatch):
    def forbidden(url):
        raise AssertionError('browser should not open')
    monkeypatch.setattr('webbrowser.open', forbidden)
    async def run():
        import pytest
        with pytest.raises(AuthRequired):
            await BrowserLogin(False, lambda text: None).redirect('https://example.com/?state=x')
    asyncio.run(run())


def test_loopback_rejects_wrong_state_and_issuer():
    async def run():
        login = BrowserLogin(True, lambda text: None)
        login.expected_state = 'expected'
        login.future = asyncio.get_running_loop().create_future()
        server = await asyncio.start_server(login.handle, '127.0.0.1', 0)
        port = server.sockets[0].getsockname()[1]
        async with server, httpx.AsyncClient(trust_env=False) as http:
            wrong = await http.get(f'http://127.0.0.1:{port}/callback?code=bad&state=wrong')
            assert wrong.status_code == 400 and not login.future.done()
            wrong_issuer = await http.get(f'http://127.0.0.1:{port}/callback?code=bad&state=expected&iss=https://wrong.example')
            assert wrong_issuer.status_code == 400 and not login.future.done()
            right = await http.get(f'http://127.0.0.1:{port}/callback?code=good&state=expected')
            assert right.status_code == 200
            assert await login.callback() == ('good', 'expected')
        server.close()
        await server.wait_closed()
    asyncio.run(run())


def test_retry_429_bounded_and_no_oauth_replay():
    async def run():
        requests = []
        async def handler(request):
            requests.append(request)
            status = 429 if len(requests) < 3 else 200
            return httpx.Response(status, headers={'Retry-After': '0'}, json={'ok': True})
        transport = RetryTransport(lambda text: None, lambda: False, httpx.MockTransport(handler))
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.post('https://mcp.fhsc.com.vn/mcp', json={'method': 'tools/list'})
            assert response.status_code == 200 and len(requests) == 3
            requests.clear()
            response = await client.post('https://open-api.fhsc.com.vn/token', data={})
            assert response.status_code == 429 and len(requests) == 1
    asyncio.run(run())


def test_retry_exhaustion_and_cancellation():
    async def run():
        calls = []
        async def handler(request):
            calls.append(1)
            return httpx.Response(503, headers={'Retry-After': '0'})
        async with httpx.AsyncClient(transport=RetryTransport(lambda _: None, lambda: False, httpx.MockTransport(handler))) as client:
            assert (await client.get('https://mcp.fhsc.com.vn/mcp')).status_code == 503
        assert len(calls) == 4
        response = httpx.Response(429, headers={'Retry-After': '120'})
        assert retry_delay(response, 0) == 120
    asyncio.run(run())


def test_gateway_cache_exact_page_and_universe_pagination(tmp_path):
    async def run():
        store = Store(tmp_path / 'cache.sqlite3')
        gateway = Gateway(store)
        calls = []
        async def fake_call(name, args, refresh=False):
            calls.append((name, args))
            if name == 'get_index_constituents':
                page = args['page']
                return {'items': [{'symbol': f'X{page}-{i}'} for i in range(50 if page == 1 else 2)], 'total': 52}, '', False
            return {'items': [{'year': 2025, 'quarter': 1}]}, '', False
        gateway.call = fake_call
        rows = await gateway.universe('HOSE', True)
        assert len(rows) == 52 and all(r['exchange'] == 'HOSE' for r in rows)
        assert [args['page'] for _, args in calls] == [1, 2]
        assert all(args['sort'] == 'symbol' and args['symbol'] == 'VNINDEX' for _, args in calls)
        calls.clear()
        assert len(await gateway.statements('FPT', 'income-statement', 'quarterly', 2025, True)) == 1
        assert calls[0][1]['year'] == 2025
        store.close()
    asyncio.run(run())


def test_background_stream_does_not_lock_tool_requests():
    async def run():
        gate = asyncio.Event()
        async def handler(request):
            if request.method == 'GET':
                await gate.wait()
            assert request.headers['Authorization'] == 'Bearer session-token'
            return httpx.Response(200, json={})
        provider = PersistentOAuthProvider('https://mcp.fhsc.com.vn/mcp',
            MarketClientMetadata(client_name='test', redirect_uris=['http://127.0.0.1:8769/callback'], scope='read:market'),
            Vault(MemoryBackend()))
        provider._initialized = True
        provider.context.current_tokens = OAuthToken(access_token='session-token', token_type='Bearer')
        async with httpx.AsyncClient(auth=provider, transport=httpx.MockTransport(handler)) as client:
            stream = asyncio.create_task(client.get('https://mcp.fhsc.com.vn/mcp'))
            await asyncio.sleep(.01)
            try:
                result = await asyncio.wait_for(client.post('https://mcp.fhsc.com.vn/mcp', json={}), .5)
                assert result.status_code == 200
            finally:
                gate.set()
                await stream
    asyncio.run(run())
