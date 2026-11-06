import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from app.gui import MainWindow, DataTable


@pytest.fixture(scope='module')
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_money_display_numeric_sort_and_filtered_export_order(qt_app):
    table = DataTable(scan=True)
    table.model.set_rows([
        {'symbol': 'FPT', 'revenue': 100_000_000_000, 'status': 'ok'},
        {'symbol': 'VCB', 'revenue': 9_000_000_000, 'status': 'missing'},
        {'symbol': 'SSI', 'revenue': -2_000_000_000, 'status': 'ok'},
    ], {'revenue'})
    col = table.model.keys.index('revenue')
    table.proxy.sort(col, Qt.AscendingOrder)
    assert [r['symbol'] for r in table.rows(True)] == ['SSI', 'VCB', 'FPT']
    assert table.model.data(table.model.index(0, col)) == '100.000'
    assert table.rows(False)[0]['revenue'] == 100_000_000_000
    table.status.setCurrentIndex(table.status.findData('ok'))
    assert [r['symbol'] for r in table.rows(True)] == ['SSI', 'FPT']
    table.query.setText('fpt')
    assert len(table.rows(True)) == 1
    table.close()


def test_reopen_restores_run_and_financial_timestamp(qt_app, tmp_path):
    first = MainWindow(tmp_path)
    run_id = first.store.new_run({'year': 2025, 'quarter': 4, 'basis': 'unknown'}, ['FPT'])
    first.store.finish(run_id, 'FPT', 'missing', {'symbol': 'FPT', 'revenue': 12345678901234, 'status': 'missing'})
    first.close()
    reopened = MainWindow(tmp_path)
    assert reopened.current_run == run_id
    assert reopened.scan_table.model.rows[0]['revenue'] == 12345678901234
    reopened.on_result('lookup', {'section': 'financial', 'symbol': 'FPT', 'stamp': 'processed-now', 'rows': [
        {'year': 2025, 'quarter': 4, '_cached': True, '_fetched_at': 'actual-source-fetch', 'doanhthuthuanvebanhangvacungcapdichvu': 12345678901234}
    ]})
    model = reopened.lookup_tables['financial'].model
    assert model.records[0]['_fetched_at'] == 'actual-source-fetch'
    assert '_cached' not in model.metrics
    reopened.close()
