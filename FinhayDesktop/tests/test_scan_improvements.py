import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.types import CallToolResult, TextContent
from app.client import Gateway, RateLimitError, ToolResponseError, unpack
from app.finance import build_result, sector_info
from app.storage import Store
from app.engine import Worker
from app.gui import MainWindow, DataTable


LIMIT = 'Rate limit exceeded. Current weight used: 129/130. Retry after 22 seconds.'


def result_error(message=LIMIT):
    return CallToolResult(content=[TextContent(type='text', text=message)], isError=True)


def statement(year, quarter, revenue, profit, parent=None):
    return dict(year=year, quarter=quarter, doanhthuthuanvebanhangvacungcapdichvu=revenue,
                loinhuansauthuethunhapdoanhnghiep=profit, loinhuansauthuecuacongtyme=parent)


def test_real_finway_weight_limit_body_is_classified():
    with pytest.raises(RateLimitError) as error:
        unpack(result_error())
    assert error.value.retry_after == 22


def test_mcp_limit_retries_exact_request_and_only_caches_success(tmp_path):
    async def run():
        store = Store(tmp_path/'retry.sqlite3')
        gateway = Gateway(store)
        gateway.tools = {'get_financial_statement': object()}
        gateway.wait_cooldown = AsyncMock()
        success = CallToolResult(content=[], structuredContent={'items': [statement(2026, 3, 300, 30)]})
        gateway.session = SimpleNamespace(call_tool=AsyncMock(side_effect=[result_error(), success]))
        args = {'symbol': 'AAS', 'year': 2026}
        payload, _, _ = await gateway.call('get_financial_statement', args, True)
        assert payload['items'][0]['year'] == 2026
        assert gateway.session.call_tool.await_count == 2
        assert gateway.session.call_tool.await_args_list[0] == gateway.session.call_tool.await_args_list[1]
        gateway.wait_cooldown.assert_awaited_once_with(22.25)
        assert store.cached('get_financial_statement', args)[0] == payload
        store.close()
    asyncio.run(run())


def test_repeated_limit_pauses_without_caching_false_error(tmp_path):
    async def run():
        store = Store(tmp_path/'rate.sqlite3')
        gateway = Gateway(store)
        gateway.tools = {'get_financial_statement': object()}
        gateway.wait_cooldown = AsyncMock()
        gateway.session = SimpleNamespace(call_tool=AsyncMock(return_value=result_error()))
        with pytest.raises(RateLimitError):
            await gateway.call('get_financial_statement', {'symbol': 'AAS'}, True)
        assert gateway.session.call_tool.await_count == 4
        assert gateway.wait_cooldown.await_count == 3
        assert store.cached('get_financial_statement', {'symbol': 'AAS'}) is None
        store.close()
    asyncio.run(run())


def test_waiting_for_quota_can_be_cancelled(tmp_path):
    async def run():
        store = Store(tmp_path/'cancel.sqlite3')
        gateway = Gateway(store)
        gateway.cancelled = lambda: True
        with pytest.raises(asyncio.CancelledError):
            await gateway.wait_cooldown(100)
        store.close()
    asyncio.run(run())


def test_three_period_values_and_growth_are_all_exportable():
    rows = [statement(2026, 3, 300, 30), statement(2026, 2, 200, 20), statement(2025, 3, 150, 15)]
    result = build_result('AAA', 'Sample', 'HOSE', rows, 2026, 3, 'standalone')
    assert [result[k] for k in ('revenue', 'revenue_previous', 'revenue_year_ago')] == [300, 200, 150]
    assert [result[k] for k in ('profit', 'profit_previous', 'profit_year_ago')] == [30, 20, 15]
    assert result['revenue_qoq_percent'] == 50
    assert result['revenue_yoy_percent'] == 100
    assert result['profit_qoq_percent'] == 50
    assert result['profit_yoy_percent'] == 100
    assert result['status'] == 'ok'  # Missing parent-only LNST must not hide total LNST.
    assert result['period_label'] == 'Q3/2026'
    assert result['previous_period_label'] == 'Q2/2026'
    assert result['year_ago_period_label'] == 'Q3/2025'


def test_missing_current_still_displays_two_comparison_periods():
    rows = [statement(2026, 2, 200, 20), statement(2025, 3, 150, 15)]
    result = build_result('AAA', '', '', rows, 2026, 3, 'standalone')
    assert result['revenue'] is None and result['profit'] is None
    assert result['revenue_previous'] == 200 and result['profit_year_ago'] == 15
    assert result['revenue_yoy_percent'] is None
    assert result['status'] == 'missing'


def test_cumulative_comparisons_all_use_standalone_quarters():
    rows = [statement(2026, 1, 100, 10), statement(2026, 2, 300, 30), statement(2026, 3, 600, 60),
            statement(2025, 2, 200, 20), statement(2025, 3, 350, 35)]
    result = build_result('AAA', '', '', rows, 2026, 3, 'cumulative')
    assert [result[k] for k in ('revenue', 'revenue_previous', 'revenue_year_ago')] == [300, 200, 150]
    assert result['revenue_qoq_percent'] == 50 and result['revenue_yoy_percent'] == 100


def test_sector_path_uses_group_and_never_guesses_missing_industry():
    assert sector_info({'sector': [{'name': 'Tài chính', 'level': 1}, {'name': 'Chứng khoán', 'level': 3, 'slug': 'securities'}]})['sector_group'] == 'Chứng khoán'
    assert sector_info({})['sector_group'] is None


def test_observed_insurance_fields_are_mapped_without_changing_values():
    from app.finance import normalize
    value = normalize({'doanhthuthuan': 650747414516, 'lnstthunhapdn': 84353248302, 'lnstcuacongtyme': 84353248302})
    assert value['kind'] == 'insurance'
    assert value['revenue'] == 650747414516
    assert value['profit'] == 84353248302


class ScanGateway:
    def __init__(self, error=None, profile_error=None):
        self.error, self.profile_error = error, profile_error

    async def universe(self, exchange, refresh):
        return [{'symbol': f'X{i:02}', 'name': f'Doanh nghiệp {i}', 'exchange': 'HOSE'} for i in range(5)]

    async def statements(self, symbol, report, period, year, refresh):
        if self.error:
            raise self.error
        return [statement(year, q, q * 100, q * 10) for q in (1, 2, 3, 4)]

    async def call(self, name, args, refresh=False):
        if self.profile_error:
            raise self.profile_error
        return {'sector': [{'level': 3, 'name': 'Nhóm ngành thử nghiệm'}]}, 'profile-time', True


def scan_config():
    return dict(symbols=[], exchange='', period='quarterly', year=2026, quarter=3, basis='standalone', refresh=True)


def test_quota_exhaustion_keeps_jobs_pending_not_red_errors(tmp_path):
    async def run():
        store = Store(tmp_path/'scan.sqlite3')
        worker = Worker(store, 'scan', scan_config())
        with pytest.raises(RateLimitError):
            await worker.scan(ScanGateway(error=RateLimitError(22)))
        jobs = store.jobs(store.runs()[0]['id'])
        assert all(j['status'] == 'pending' for j in jobs)
        store.close()
    asyncio.run(run())


def test_unknown_errors_keep_metadata_and_trip_circuit(tmp_path):
    async def run():
        store = Store(tmp_path/'circuit.sqlite3')
        worker = Worker(store, 'scan', scan_config())
        events = []
        worker.result.connect(events.append)
        await worker.scan(ScanGateway(error=RuntimeError('unexpected source error')))
        jobs = store.jobs(store.runs()[0]['id'])
        assert [j['status'] for j in jobs] == ['error', 'error', 'error', 'pending', 'pending']
        data = json.loads(jobs[0]['result'])
        assert data['name'] == 'Doanh nghiệp 0' and data['year'] == 2026
        assert data['period_label'] == 'Q3/2026'
        assert events[-1]['paused']
        store.close()
    asyncio.run(run())


def test_missing_group_does_not_lose_successful_financial_values(tmp_path):
    async def run():
        store = Store(tmp_path/'group.sqlite3')
        worker = Worker(store, 'scan', scan_config())
        await worker.scan(ScanGateway(profile_error=ToolResponseError('Profile unavailable')))
        result = json.loads(store.jobs(store.runs()[0]['id'])[0]['result'])
        assert result['revenue'] == 300 and result['revenue_previous'] == 200
        assert result['profit_year_ago'] == 30
        assert result['status'] == 'missing' and result['sector_group'] is None
        store.close()
    asyncio.run(run())


def test_legacy_runs_are_requeued_once_without_erasing_results(tmp_path):
    store = Store(tmp_path/'old.sqlite3')
    run_id = store.new_run(scan_config(), ['AAA'])
    store.finish(run_id, 'AAA', 'error', {'symbol': 'AAA', 'message': 'old error'})
    assert store.requeue_outdated(run_id, 2) == 1
    assert json.loads(store.jobs(run_id)[0]['result'])['message'] == 'old error'
    store.finish(run_id, 'AAA', 'ok', {'symbol': 'AAA', 'schema_version': 2})
    assert store.requeue_outdated(run_id, 2) == 0
    store.close()


def test_scan_view_prioritizes_comparison_and_group_columns(tmp_path):
    table = DataTable(scan=True)
    row = build_result('AAA', 'Sample', 'HOSE', [statement(2026, 3, 300, 30), statement(2026, 2, 200, 20), statement(2025, 3, 150, 15)], 2026, 3, 'standalone')
    row.update(sector_group='Chứng khoán', fetched_at='source-time')
    table.set_scan_rows([row], scan_config())
    for key in ('sector_group', 'revenue_previous', 'revenue_year_ago', 'profit_previous', 'profit_year_ago', 'profit_yoy_percent'):
        assert not table.view.isColumnHidden(table.model.keys.index(key))
    assert table.view.isColumnHidden(table.model.keys.index('fetched_at'))
    table.query.setText('Chứng khoán')
    assert len(table.rows(True)) == 1
    table.update_scan_row({**row, 'profit': 40})
    assert table.rows(True)[0]['profit'] == 40
    assert table.query.text() == 'Chứng khoán'
    exported = table.export_data(table.rows(True))[0]
    assert exported['Doanh thu Q2/2026 (VND)'] == 200
    assert exported['LNST Q3/2025 (VND)'] == 15
    assert exported['Nhóm ngành'] == 'Chứng khoán'
    assert 'fetched_at' not in exported
    table.details.setChecked(True)
    assert not table.view.isColumnHidden(table.model.keys.index('fetched_at'))
    table.close()
