import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from openpyxl import load_workbook
from app.financial_view import FinancialModel, FinancialView, period_label
from app.financial_labels import ordered_metrics, unit_for
from app.exporting import export_rows
from app.gui import MainWindow


@pytest.fixture(scope='module')
def qt_app():
    return QApplication.instance() or QApplication([])


def statement(year, quarter, revenue, profit=0, eps=13657):
    return {'year': year, 'quarter': quarter, 'doanhthuthuanvebanhangvacungcapdichvu': revenue,
            'loinhuansauthuethunhapdoanhnghiep': profit, 'laicobantrencophieu': eps,
            '_cached': True, '_source': 'Finhay MCP', '_fetched_at': 'original-timestamp'}


def test_matrix_chronological_periods_and_missing_quarter(qt_app):
    model = FinancialModel()
    rows = [statement(2025, 4, 3_000_000_000), statement(2025, 2, 0)]
    model.set_records(rows)
    assert model.visible_periods == [(2025, 2), (2025, 3), (2025, 4)]
    assert model.headerData(2, Qt.Horizontal) == 'Q2/2025'
    metric = model.metrics.index('doanhthuthuanvebanhangvacungcapdichvu')
    assert model.data(model.index(metric, 2)) == '0.0'
    assert model.data(model.index(metric, 3)) == '—'
    assert model.data(model.index(metric, 4)) == '3.0'
    assert not any(k.startswith('_') for k in model.metrics)
    assert rows[0]['doanhthuthuanvebanhangvacungcapdichvu'] == 3_000_000_000


def test_display_units_do_not_scale_eps_and_preserve_original(qt_app):
    model = FinancialModel()
    model.set_records([statement(2025, 1, 2_500_000_000, -100_000_000)])
    revenue = model.metrics.index('doanhthuthuanvebanhangvacungcapdichvu')
    eps = model.metrics.index('laicobantrencophieu')
    profit = model.metrics.index('loinhuansauthuethunhapdoanhnghiep')
    assert model.data(model.index(revenue, 2)) == '2.5'
    assert model.data(model.index(eps, 2)) == '13,657'
    assert model.data(model.index(profit, 2), Qt.ForegroundRole).name() == '#dc2626'
    assert model.data(model.index(revenue, 2), Qt.FontRole).bold()
    model.set_scale(1_000_000)
    assert model.data(model.index(revenue, 2)) == '2,500.0'
    assert model.data(model.index(eps, 2)) == '13,657'
    assert model.value('doanhthuthuanvebanhangvacungcapdichvu', (2025, 1)) == 2_500_000_000
    assert unit_for('cophieuphothongcoquyenbieuquyet') == 'VND'


def test_eight_period_navigation_and_annual_gap(qt_app):
    model = FinancialModel()
    model.set_records([statement(year, q, year * 100 + q) for year in (2023, 2024, 2025) for q in (1, 2, 3, 4)])
    assert len(model.visible_periods) == 8
    assert model.visible_periods[0] == (2024, 1)
    model.set_window(8, 11)
    assert model.visible_periods[-1] == (2025, 3)
    model.set_window(0)
    assert len(model.visible_periods) == 12
    model.set_records([statement(2023, None, 1), statement(2025, None, 2)])
    assert [period_label(p) for p in model.periods] == ['2023', '2024', '2025']
    assert model.value('doanhthuthuanvebanhangvacungcapdichvu', (2024, None)) is None


def test_bank_and_securities_order_follows_statement_flow():
    bank = ordered_metrics(['chiphithuetndnhienhanh', 'tongthunhaphoatdong', 'thunhaplaivacackhoanthunhaptuongtu', 'loinhuansauthue'])
    assert bank[0] == 'thunhaplaivacackhoanthunhaptuongtu'
    assert bank[-1] == 'loinhuansauthue'
    sec = ordered_metrics(['lnsauthue', 'doanhthuhoatdong', 'cackhoangiamtrudoanhthu', 'laicobantrencophieu'])
    assert sec == ['doanhthuhoatdong', 'cackhoangiamtrudoanhthu', 'lnsauthue', 'laicobantrencophieu']


def test_filter_frozen_label_and_transposed_export(qt_app, tmp_path):
    view = FinancialView()
    view.resize(1050, 400)
    view.set_records([statement(2025, 1, 1_000_000_000), statement(2025, 2, 2_000_000_000)], {'symbol': 'FPT', 'report': 'income-statement'})
    view.show()
    qt_app.processEvents()
    view.query.setText('Doanh thu')
    filtered = view.export_data(True)
    assert len(filtered) == 1
    assert filtered[0]['Q1/2025'] == 1_000_000_000
    assert filtered[0]['Đơn vị gốc'] == 'VND'
    assert len(view.export_data(False)) == 3
    path = tmp_path / 'statement.xlsx'
    export_rows(path, filtered)
    assert list(load_workbook(path)['Du lieu'].values)[1][3] == 1_000_000_000
    for row in range(view.model.rowCount()):
        assert view.view.isRowHidden(row) == view.view.frozen.isRowHidden(row)
    position = view.view.frozen.pos()
    view.view.horizontalScrollBar().setValue(view.view.horizontalScrollBar().maximum())
    qt_app.processEvents()
    assert view.view.frozen.pos() == position
    assert view.view.frozen.columnWidth(0) == view.view.columnWidth(0)
    view.close()


def test_unloaded_selection_is_empty_but_loaded_report_returns(qt_app, tmp_path):
    window = MainWindow(tmp_path)
    matrix = window.lookup_tables['financial']
    window.on_result('lookup', {'section': 'financial', 'symbol': 'FPT', 'stamp': 'sample', 'rows': [statement(2025, 1, 1)]})
    window.report_tabs.setCurrentIndex(1)
    assert window.report.currentData() == 'balance-sheet'
    assert matrix.model.records == []
    window.report_tabs.setCurrentIndex(0)
    assert matrix.model.records[0]['doanhthuthuanvebanhangvacungcapdichvu'] == 1
    window.period.setCurrentIndex(1)
    assert matrix.model.records == []
    window.period.setCurrentIndex(0)
    assert matrix.model.records[0]['doanhthuthuanvebanhangvacungcapdichvu'] == 1
    window.close()


def test_frozen_column_with_real_scroll_ranges(qt_app):
    view = FinancialView()
    view.resize(760, 400)
    records = [{'year': year, 'quarter': q, **{f'new_metric_{i}': i * 1_000_000_000 for i in range(40)}}
               for year in (2023, 2024, 2025) for q in (1, 2, 3, 4)]
    view.set_records(records)
    view.window.setCurrentIndex(2)
    view.show()
    qt_app.processEvents()
    main, frozen = view.view, view.view.frozen
    assert main.horizontalScrollBar().maximum() > 0
    assert main.verticalScrollBar().maximum() > 0
    position = frozen.pos()
    main.horizontalScrollBar().setValue(main.horizontalScrollBar().maximum())
    main.verticalScrollBar().setValue(150)
    qt_app.processEvents()
    assert frozen.pos() == position
    assert frozen.verticalScrollBar().value() == main.verticalScrollBar().value()
    assert frozen.visualRect(view.model.index(12, 0)).y() == main.visualRect(view.model.index(12, 0)).y()
    view.close()


def test_primary_filter_and_period_window_export(qt_app):
    view = FinancialView()
    view.set_records([statement(year, q, 1_000_000_000) for year in (2023, 2024, 2025) for q in (1, 2, 3, 4)])
    view.primary_only.setChecked(True)
    rows = view.export_data(True)
    assert len(rows) == 2
    assert 'Q1/2023' not in rows[0]
    assert rows[0]['Q4/2025'] == 1_000_000_000
    view.move(-1)
    assert 'Q4/2025' not in view.export_data(True)[0]
    assert 'Q1/2023' in view.export_data(False)[0]
    view.close()
