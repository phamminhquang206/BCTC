import asyncio
import time
from contextlib import asynccontextmanager

import httpx
import pytest
from PySide6.QtWidgets import QApplication

from app.auth import AuthRequired
from app.engine import Worker
from app.gui import MainWindow


REPORTS = ('income-statement', 'balance-sheet', 'cash-flow')
FIELDS = {'income-statement': 'doanhthuthuanvebanhangvacungcapdichvu',
          'balance-sheet': 'tongcongtaisan', 'cash-flow': 'luuchuyentienthuantrongnam'}


def config(**overrides):
    return {'symbol': 'FPT', 'section': 'financial', 'report': 'cash-flow', 'period': 'annual',
            'from_year': 2024, 'to_year': 2025, 'refresh': True, **overrides}


class FakeGateway:
    def __init__(self, failure=None, callback=None, delay=0):
        self.calls = []
        self.failure, self.callback, self.delay = failure, callback, delay
        self.connect_count = 0

    @asynccontextmanager
    async def connect(self, *args):
        self.connect_count += 1
        yield self

    async def statements(self, symbol, report, period, year, refresh):
        call = (symbol, report, period, year, refresh)
        self.calls.append(call)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.callback:
            self.callback(self)
        if self.failure:
            error = self.failure(call)
            if error:
                raise error
        return [{'year': year, 'quarter': quarter, FIELDS[report]: year * 1_000_000_000 + (quarter or 0), '_fetched_at': 'source-time'}
                for quarter in ((1, 4) if period == 'quarterly' else (None,))]


@pytest.mark.parametrize('refresh', [True, False])
def test_one_lookup_loads_six_variants_selected_first(refresh):
    c = config(refresh=refresh)
    worker = Worker(None, 'lookup', c)
    results, progress = [], []
    worker.result.connect(results.append)
    worker.progress.connect(lambda done, total: progress.append((done, total)))
    gateway = FakeGateway()
    asyncio.run(worker.lookup(gateway))
    reports = [result for result in results if result.get('section') == 'financial']
    assert len(gateway.calls) == 12
    assert gateway.calls[0][1:3] == ('cash-flow', 'annual')
    assert {(r['config']['report'], r['config']['period']) for r in reports} == {(report, period) for report in REPORTS for period in ('quarterly', 'annual')}
    assert all(call[0] == 'FPT' and call[4] == refresh for call in gateway.calls)
    assert all(len(r['rows']) == (4 if r['config']['period'] == 'quarterly' else 2) for r in reports)
    assert progress[0] == (0, 6) and progress[-1] == (6, 6)
    assert results[-1]['completed'] == 6 and results[-1]['failed'] == []
    assert worker.config == c


def test_one_tool_error_keeps_five_other_complete_variants():
    def fail(call):
        return RuntimeError('sample tool error') if call[1:4] == ('balance-sheet', 'annual', 2025) else None
    worker = Worker(None, 'lookup', config())
    results = []
    worker.result.connect(results.append)
    gateway = FakeGateway(failure=fail)
    asyncio.run(worker.lookup(gateway))
    data = [r for r in results if r.get('section') == 'financial']
    assert len(data) == 5
    assert not any(r['config']['report'] == 'balance-sheet' and r['config']['period'] == 'annual' for r in data)
    assert results[-1]['completed'] == 5
    assert results[-1]['failed'][0]['report'] == 'balance-sheet'
    assert len(gateway.calls) == 12


def test_cancellation_never_marks_half_a_variant_loaded():
    worker = Worker(None, 'lookup', config(report='income-statement', period='quarterly'))
    results = []
    worker.result.connect(results.append)
    gateway = FakeGateway(callback=lambda g: worker.pause() if len(g.calls) == 3 else None)
    asyncio.run(worker.lookup(gateway))
    data = [r for r in results if r.get('section') == 'financial']
    assert len(data) == 1
    assert data[0]['config']['period'] == 'quarterly'
    assert len(data[0]['rows']) == 4
    assert results[-1]['cancelled'] and results[-1]['completed'] == 1
    assert len(gateway.calls) == 3


@pytest.mark.parametrize('error', [AuthRequired('reconnect'), httpx.ConnectError('offline')])
def test_connection_errors_stop_without_losing_emitted_variants(error):
    gateway = FakeGateway(failure=lambda call: error if call[2] == 'quarterly' else None)
    worker = Worker(None, 'lookup', config())
    results = []
    worker.result.connect(results.append)
    with pytest.raises(type(error)):
        asyncio.run(worker.lookup(gateway))
    assert len(results) == 1
    assert results[0]['config']['period'] == 'annual'
    assert len(gateway.calls) == 3


def test_click_once_populates_every_report_and_mode(monkeypatch, tmp_path):
    app = QApplication.instance()
    gateway = FakeGateway(delay=.01)
    monkeypatch.setattr('app.engine.Gateway', lambda *args: gateway)
    window = MainWindow(tmp_path)
    window.from_year.setValue(2024)
    window.to_year.setValue(2025)
    window.report_tabs.setCurrentIndex(2)
    window.period.setCurrentIndex(1)
    window.refresh_lookup.setChecked(False)
    window.fetch_buttons['financial'].click()
    assert window.worker is not None
    assert window.report_tabs.isEnabled() and window.period.isEnabled()
    assert not window.from_year.isEnabled() and not window.symbol.isEnabled()
    # Changing the displayed variant while the same submitted bundle is loading
    # must not change the worker's symbol/range or issue a second request.
    window.report_tabs.setCurrentIndex(0)
    window.period.setCurrentIndex(0)
    deadline = time.monotonic() + 5
    while window.worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    try:
        assert window.worker is None
        assert gateway.connect_count == 1
        assert len(gateway.calls) == 12
        assert len(window.financial_cache) == 6
        table = window.lookup_tables['financial']
        for index, report in enumerate(REPORTS):
            window.report_tabs.setCurrentIndex(index)
            for period_index, period in enumerate(('quarterly', 'annual')):
                window.period.setCurrentIndex(period_index)
                assert table.context['report'] == report
                assert table.context['period'] == period
                assert len(table.model.records) == (4 if period == 'quarterly' else 2)
                assert FIELDS[report] in table.model.metrics
        assert len(gateway.calls) == 12
        assert '6/6' in window.statusBar().currentMessage()
        assert window.fetch_buttons['financial'].text() == 'Lấy dữ liệu'
    finally:
        if window.worker:
            window.worker.pause()
            window.worker.wait(3000)
            app.processEvents()
        window.close()
