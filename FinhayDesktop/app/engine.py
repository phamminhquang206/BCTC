import asyncio
import json
import re
import threading
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from .auth import AuthRequired
from .client import Gateway, leaf_errors, user_error
from .finance import build_result
from .storage import now


def items_of(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ('items', 'events', 'series', 'results'):
        if isinstance(data.get(key), list):
            return data[key]
    return [data]


class Worker(QThread):
    message = Signal(str)
    result = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)
    row_ready = Signal(object)

    def __init__(self, store, action, config=None):
        super().__init__()
        self.store, self.action, self.config = store, action, config or {}
        self.stop_event = threading.Event()

    def pause(self):
        self.stop_event.set()

    def run(self):
        try:
            asyncio.run(self.execute())
        except asyncio.CancelledError:
            self.message.emit('Đã hủy trước khi hoàn tất chuẩn bị danh sách mã.')
        except Exception as exc:
            self.failed.emit(user_error(exc))

    async def execute(self):
        gateway = Gateway(self.store, self.message.emit)
        async with gateway.connect(self.action == 'connect', self.stop_event.is_set):
            if self.action == 'connect':
                # Probe a real statement through this app's own connection.
                rows = await gateway.statements('FPT', 'income-statement', 'quarterly', datetime.now().year - 1, True)
                self.result.emit({'tools': sorted(gateway.tools), 'probe_rows': len(rows)})
            elif self.action == 'catalog':
                data, stamp, cached = await gateway.call('get_stocks_catalog', {}, self.config.get('refresh', False))
                self.result.emit({'rows': items_of(data), 'stamp': stamp, 'cached': cached})
            elif self.action == 'lookup':
                await self.lookup(gateway)
            elif self.action == 'scan':
                await self.scan(gateway)

    async def lookup(self, gateway):
        c = self.config
        symbol, section, refresh = c['symbol'], c['section'], c['refresh']
        tables, stamps = [], []
        if section == 'overview':
            for tool in ('get_stock_profile', 'get_stock_listing', 'get_company_overview'):
                data, stamp, cached = await gateway.call(tool, {'symbol': symbol}, refresh)
                tables.append({'group': tool, 'data': data})
                stamps.append(f'{tool}: {stamp}' + (' • đã lưu' if cached else ' • mới lấy'))
            rows = [dict(nhom=t['group'], chi_tieu=k, gia_tri=v) for t in tables for k, v in t['data'].items()]
            result = {'rows': rows}
        elif section == 'financial':
            rows = []
            for year in range(c['from_year'], c['to_year'] + 1):
                if self.stop_event.is_set():
                    break
                self.message.emit(f'Đang lấy {symbol} — năm {year}…')
                rows.extend(await gateway.statements(symbol, c['report'], c['period'], year, refresh))
            rows.sort(key=lambda row: (row.get('year', 0), row.get('quarter') or 0), reverse=True)
            result = {'rows': rows}
        elif section == 'price':
            quote, stamp, cached = await gateway.call('get_stock_quote', {'symbol': symbol}, True)
            data, history_stamp, history_cached = await gateway.call('get_stock_history', {
                'symbol': symbol, 'resolution': '1D', 'from': c['from_ts'], 'to': c['to_ts']}, refresh)
            result = {'rows': items_of(data), 'quote': quote}
            stamps = [f'Giá hiện tại: {stamp}', f'Lịch sử: {history_stamp}' + (' • đã lưu' if history_cached else ' • mới lấy')]
        else:
            rows, page = [], 1
            while True:
                if self.stop_event.is_set():
                    break
                args = dict(symbol=symbol, page=page, page_size=50)
                data, stamp, cached = await gateway.call('get_stock_events', args, refresh)
                batch = items_of(data)
                rows.extend(batch)
                stamps.append(stamp + (' • đã lưu' if cached else ' • mới lấy'))
                pages = (data.get('pagination') or {}).get('total_pages')
                if len(batch) < 50 or (pages and page >= pages):
                    break
                page += 1
                if page > 200:
                    raise RuntimeError('Quá nhiều trang sự kiện.')
            result = {'rows': rows}
        result.update(symbol=symbol, section=section, stamp='\n'.join(stamps) if stamps else now(), config=c)
        self.result.emit(result)

    async def scan(self, gateway):
        run_id = self.config.get('run_id')
        if run_id:
            config = self.store.config(run_id)
        else:
            config = dict(self.config)
            self.message.emit('Đang lấy danh sách cổ phiếu…')
            if config['symbols']:
                catalog, _, _ = await gateway.call('get_stocks_catalog', {}, config['refresh'])
                names = {r['symbol']: r.get('name', '') for r in items_of(catalog) if r.get('symbol')}
                universe = []
                for symbol in config['symbols']:
                    if self.stop_event.is_set():
                        return
                    listing, _, _ = await gateway.call('get_stock_listing', {'symbol': symbol}, config['refresh'])
                    exchange = str(listing.get('exchange') or '').upper()
                    if exchange not in ('HOSE', 'HNX', 'UPCOM') or (config.get('exchange') and config['exchange'] != exchange):
                        self.message.emit(f'Bỏ qua {symbol}: không xác định được mã thuộc sàn Việt Nam được chọn.')
                        continue
                    universe.append({'symbol': symbol, 'name': names.get(symbol, ''), 'exchange': exchange})
            else:
                universe = await gateway.universe(config.get('exchange'), config['refresh'])
            config['universe'] = {r['symbol']: r for r in universe}
            if not universe:
                raise RuntimeError('Không tìm được cổ phiếu trong phạm vi đã chọn.')
            run_id = self.store.new_run(config, [r['symbol'] for r in universe])
        self.result.emit({'run_id': run_id, 'started': True})
        jobs = self.store.jobs(run_id)
        done = sum(job['status'] != 'pending' for job in jobs)
        self.progress.emit(done, len(jobs))
        for job in jobs:
            if self.stop_event.is_set():
                break
            if job['status'] != 'pending':
                continue
            symbol = job['symbol']
            self.message.emit(f'Đang quét {symbol} ({done + 1}/{len(jobs)})…')
            try:
                rows = []
                for year in (config['year'], config['year'] - 1):
                    rows.extend(await gateway.statements(symbol, 'income-statement', config['period'], year, config['refresh']))
                meta = config['universe'][symbol]
                result = build_result(symbol, meta.get('name', ''), meta.get('exchange', ''), rows,
                                      config['year'], config['quarter'], config['basis'])
                target = next((r for r in rows if r.get('year') == config['year'] and r.get('quarter') == config['quarter']), {})
                result['fetched_at'] = target.get('_fetched_at')
                result['processed_at'] = now()
                result['source'] = 'Finhay MCP'
                result['cache_policy'] = 'refresh' if config['refresh'] else 'prefer_cache'
                self.store.finish(run_id, symbol, result['status'], result)
                self.row_ready.emit(result)
            except Exception as exc:
                if self.stop_event.is_set():
                    break
                leaves = leaf_errors(exc)
                # Authentication and transport failures pause the run with job pending.
                import httpx
                from mcp.client.auth.exceptions import OAuthFlowError
                if any(isinstance(e, (AuthRequired, OAuthFlowError, httpx.TransportError, httpx.HTTPStatusError)) for e in leaves):
                    raise
                result = {'symbol': symbol, 'status': 'error', 'message': user_error(exc)}
                self.store.finish(run_id, symbol, 'error', result)
                self.row_ready.emit(result)
            done += 1
            self.progress.emit(done, len(jobs))
            await asyncio.sleep(.3)
        self.result.emit({'run_id': run_id, 'paused': self.stop_event.is_set(), 'finished': True})
