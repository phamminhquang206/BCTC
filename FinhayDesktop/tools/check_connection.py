"""Run with the app's Python: python tools/check_connection.py [--login]."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import httpx
from app.client import Gateway, user_error
from app.storage import Store


async def check(login):
    import os
    import tempfile
    async with httpx.AsyncClient(timeout=20) as client:
        for endpoint in ('oauth-protected-resource', 'oauth-authorization-server'):
            response = await client.get('https://mcp.fhsc.com.vn/.well-known/' + endpoint)
            response.raise_for_status()
            metadata = response.json()
            print(endpoint, {k: metadata[k] for k in ('resource', 'issuer', 'registration_endpoint', 'code_challenge_methods_supported') if k in metadata})
    # The diagnostic stores market data in a temporary directory, never account tokens.
    # OAuth registration/tokens use the same app-specific Windows vault as the GUI.
    with tempfile.TemporaryDirectory(prefix='finhay-probe-') as temp:
        store = Store(Path(temp) / 'probe.sqlite3')
        gateway = Gateway(store, print)
        try:
            async with gateway.connect(interactive=login):
                print('MCP tools:', len(gateway.tools))
                rows = await gateway.statements('FPT', 'income-statement', 'quarterly', 2025, True)
                print('FPT 2025 quarterly statement rows:', len(rows))
        except Exception as exc:
            print(user_error(exc))
            return 2
        finally:
            store.close()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--login', action='store_true', help='Open browser to authorize this app')
    sys.exit(asyncio.run(check(parser.parse_args().login)))
