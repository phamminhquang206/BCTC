import asyncio
import json
import re
import threading
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from .auth import AuthRequired
from .client import Gateway, leaf_errors, user_error, RateLimitError
from .finance import build_result, sector_info
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


REPORTS = {'income-statement': 'Kết quả kinh doanh', 'balance-sheet': 'Cân đối kế toán', 'cash-flow': 'Lưu chuyển tiền tệ'}


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
            self.message.emit('Đã tạm dừng; các kết quả đã hoàn tất được giữ lại.')
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
                title = {'get_stock_profile': 'Hồ sơ doanh nghiệp', 'get_stock_listing': 'Thông tin niêm yết', 'get_company_overview': 'Chỉ số tài chính'}[tool]
                stamps.append(f'{title}: {stamp}' + (' • đã lưu' if cached else ' • mới lấy'))
            rows = [dict(nhom=t['group'], chi_tieu=k, gia_tri=v) for t in tables for k, v in t['data'].items()]
            result = {'rows': rows, 'overview': {key: table['data'] for key, table in zip(('profile', 'listing', 'metrics'), tables)}}
        elif section == 'financial':
            await self.financial_bundle(gateway)
            return
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

    async def financial_bundle(self, gateway):
        """One connection, all six report/period variants, selected view first.

        Only complete variants enter the GUI cache. Individual source/tool errors
        do not discard successful variants; authentication/connection errors stop
        the batch so the normal reconnect UI can handle them.
        """
        import httpx
        from mcp.client.auth.exceptions import OAuthFlowError

        c = self.config
        reports = [c['report'], *(report for report in REPORTS if report != c['report'])]
        periods = [c['period'], 'annual' if c['period'] == 'quarterly' else 'quarterly']
        variants = [(report, period) for report in reports for period in periods]
        completed, failures = 0, []
        self.progress.emit(0, len(variants))
        for index, (report, period) in enumerate(variants, 1):
            if self.stop_event.is_set():
                break
            rows = []
            period_name = 'Quý' if period == 'quarterly' else 'Năm'
            try:
                for year in range(c['from_year'], c['to_year'] + 1):
                    if self.stop_event.is_set():
                        break
                    self.message.emit(f'{c["symbol"]} · {REPORTS[report]} · {period_name} · {year} ({index}/6)')
                    rows.extend(await gateway.statements(c['symbol'], report, period, year, c['refresh']))
            except Exception as exc:
                if self.stop_event.is_set():
                    break
                if any(isinstance(error, (AuthRequired, RateLimitError, OAuthFlowError, httpx.TransportError, httpx.HTTPStatusError)) for error in leaf_errors(exc)):
                    raise
                error = {'report': report, 'period': period, 'message': user_error(exc)}
                failures.append(error)
                self.message.emit(f'{REPORTS[report]} · {period_name}: chưa tải được. {error["message"]}')
                self.progress.emit(index, len(variants))
                continue
            if self.stop_event.is_set():
                break
            rows.sort(key=lambda row: (row.get('year', 0), row.get('quarter') or 0), reverse=True)
            self.result.emit({'section': 'financial', 'symbol': c['symbol'], 'rows': rows, 'stamp': now(),
                              'config': {**c, 'report': report, 'period': period}})
            completed += 1
            self.progress.emit(index, len(variants))
        self.result.emit({'kind': 'financial_summary', 'symbol': c['symbol'], 'completed': completed,
                          'total': len(variants), 'failed': failures, 'cancelled': self.stop_event.is_set()})

    async def scan(self, gateway):
        run_id = self.config.get('run_id')
        if run_id:
            config = self.store.config(run_id)
            upgraded = self.store.requeue_outdated(run_id, 2)
            if upgraded:
                self.message.emit(f'Đã đưa {upgraded} kết quả cũ vào hàng chờ để bổ sung các kỳ so sánh và nhóm ngành.')
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
        consecutive_errors = 0
        circuit_paused = False
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
                try:
                    # Company classification is reused across scans to avoid an
                    # extra classification request for every repeated scan.
                    profile, profile_stamp, _ = await gateway.call('get_stock_profile', {'symbol': symbol}, False)
                    result.update(sector_info(profile), sector_fetched_at=profile_stamp)
                    if not result.get('sector_group'):
                        result.update(status='missing', message='; '.join(filter(None, (result['message'], 'Finhay chưa có nhóm ngành'))))
                except Exception as exc:
                    import httpx
                    from mcp.client.auth.exceptions import OAuthFlowError
                    if any(isinstance(e, (AuthRequired, RateLimitError, OAuthFlowError, httpx.TransportError, httpx.HTTPStatusError)) for e in leaf_errors(exc)):
                        raise
                    result.update(sector_group=None, status='missing', message='; '.join(filter(None, (result['message'], 'Chưa lấy được nhóm ngành'))))
                    self.message.emit(f'{symbol}: giữ số liệu tài chính; nhóm ngành chưa lấy được. {user_error(exc)}')
                target = next((r for r in rows if r.get('year') == config['year'] and r.get('quarter') == config['quarter']), {})
                result['fetched_at'] = target.get('_fetched_at')
                result['processed_at'] = now()
                result['source'] = 'Finhay MCP'
                result['cache_policy'] = 'refresh' if config['refresh'] else 'prefer_cache'
                self.store.finish(run_id, symbol, result['status'], result)
                self.row_ready.emit(result)
                consecutive_errors = 0
            except Exception as exc:
                if self.stop_event.is_set():
                    break
                leaves = leaf_errors(exc)
                # Authentication and transport failures pause the run with job pending.
                import httpx
                from mcp.client.auth.exceptions import OAuthFlowError
                if any(isinstance(e, (AuthRequired, RateLimitError, OAuthFlowError, httpx.TransportError, httpx.HTTPStatusError)) for e in leaves):
                    raise
                meta = config['universe'].get(symbol, {})
                result = build_result(symbol, meta.get('name', ''), meta.get('exchange', ''), [], config['year'], config['quarter'], config['basis'])
                result.update(status='error', message=user_error(exc), error_kind=type(leaves[0]).__name__)
                self.store.finish(run_id, symbol, 'error', result)
                self.row_ready.emit(result)
                self.message.emit(f'{symbol}: {result["message"]}')
                consecutive_errors += 1
            done += 1
            self.progress.emit(done, len(jobs))
            if consecutive_errors >= 3:
                circuit_paused = True
                self.message.emit('Tạm dừng sau 3 mã lỗi liên tiếp để tránh ghi lỗi hàng loạt. Kiểm tra kết nối/nguồn rồi thử lại các mã lỗi.')
                break
            await asyncio.sleep(.3)
        self.result.emit({'run_id': run_id, 'paused': self.stop_event.is_set() or circuit_paused, 'finished': True,
                          'reason': 'Có 3 mã lỗi liên tiếp; các mã chưa chạy vẫn nằm trong hàng chờ.' if circuit_paused else ''})
