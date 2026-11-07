import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import asyncio
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.gui import MainWindow, apply_theme
from app.overview_view import OverviewView, overview_from_rows
from app.ui_controls import StepSpinBox
from app.engine import Worker


@pytest.fixture(scope='module')
def qt_app():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    return app


def deliver(window, report='income-statement', symbol='FPT', period='quarterly', start=2024, end=2026, amount=1_000_000_000):
    rows = [{'year': year, 'quarter': q if period == 'quarterly' else None,
             'doanhthuthuanvebanhangvacungcapdichvu': amount + q,
             'loinhuansauthuethunhapdoanhnghiep': 100_000_000}
            for year in range(start, end + 1) for q in ((1, 2, 3, 4) if period == 'quarterly' else (1,))]
    window.on_result('lookup', {'section': 'financial', 'symbol': symbol, 'rows': rows, 'stamp': 'sample',
        'config': {'report': report, 'period': period, 'from_year': start, 'to_year': end}})


def test_report_revisit_keeps_values_filter_units_and_period_position(qt_app, tmp_path):
    window = MainWindow(tmp_path)
    window.from_year.setValue(2024)
    window.to_year.setValue(2026)
    deliver(window)
    table = window.lookup_tables['financial']
    table.unit.setCurrentIndex(1)
    table.query.setText('doanh thu')
    table.move(-2)
    last_period = table.model.visible_periods[-1]
    launches = []
    window.launch = lambda *args: launches.append(args)
    window.report_tabs.setCurrentIndex(1)
    assert table.model.records == []
    deliver(window, report='balance-sheet', amount=7_000_000_000)
    assert table.model.records[0]['doanhthuthuanvebanhangvacungcapdichvu'] == 7_000_000_001
    window.report_tabs.setCurrentIndex(0)
    assert table.model.records[0]['doanhthuthuanvebanhangvacungcapdichvu'] == 1_000_000_001
    assert table.query.text() == 'doanh thu'
    assert table.unit.currentData() == 1_000_000
    assert table.model.visible_periods[-1] == last_period
    assert launches == []
    window.close()


def test_contexts_never_mix_symbol_period_or_year_range(qt_app, tmp_path):
    window = MainWindow(tmp_path)
    window.from_year.setValue(2024)
    window.to_year.setValue(2026)
    deliver(window)
    table = window.lookup_tables['financial']
    window.symbol.setText('VCB')
    assert not table.model.records
    deliver(window, symbol='VCB', amount=9_000_000_000)
    window.symbol.setText('FPT')
    assert table.model.records[0]['doanhthuthuanvebanhangvacungcapdichvu'] == 1_000_000_001
    window.period.setCurrentIndex(1)
    assert not table.model.records
    window.period.setCurrentIndex(0)
    assert table.model.records
    window.to_year.setValue(2025)
    assert not table.model.records
    window.to_year.setValue(2026)
    assert len(table.model.records) == 12
    window.close()


def test_late_report_result_does_not_replace_active_selection(qt_app, tmp_path):
    window = MainWindow(tmp_path)
    window.from_year.setValue(2024)
    window.to_year.setValue(2026)
    window.report_tabs.setCurrentIndex(1)
    deliver(window)
    table = window.lookup_tables['financial']
    assert not table.model.records
    assert 'Cân đối kế toán' in table.heading.text()
    window.report_tabs.setCurrentIndex(0)
    assert table.model.records
    window.close()


def test_financial_memory_cache_is_bounded(qt_app, tmp_path):
    window = MainWindow(tmp_path)
    for year in range(2000, 2015):
        deliver(window, start=year, end=year)
    assert len(window.financial_cache) == 12
    assert all(key[3] >= 2003 for key in window.financial_cache)
    assert len(window.financial_states) <= 12
    window.close()


def test_spin_buttons_work_and_stop_at_limits(qt_app):
    spin = StepSpinBox()
    spin.setRange(2024, 2026)
    spin.setValue(2025)
    spin.show()
    qt_app.processEvents()
    assert spin.increase_button.text() == '+'
    assert spin.lineEdit().width() >= spin.lineEdit().fontMetrics().horizontalAdvance('2025')
    QTest.mouseClick(spin.increase_button, Qt.LeftButton)
    assert spin.value() == 2026
    assert not spin.increase_button.isEnabled()
    QTest.mouseClick(spin.decrease_button, Qt.LeftButton)
    assert spin.value() == 2025
    QTest.mouseClick(spin.decrease_button, Qt.LeftButton)
    assert spin.value() == 2024
    assert not spin.decrease_button.isEnabled()
    spin.close()


def test_overview_is_readable_with_industry_and_missing_values(qt_app):
    view = OverviewView()
    data = {
        'profile': {'name_vn': 'Công ty thử nghiệm', 'name_en': 'Sample Company', 'sector': [{'name': 'Công nghệ'}, {'name': 'Phần mềm'}], 'about': 'Cung cấp dịch vụ phần mềm.'},
        'listing': {'exchange': 'HOSE', 'listing_date': '2006-12-13', 'outstanding_shares': 1_234_567, 'free_float_pct': 0, 'treasury_shares': None},
        'metrics': {'pe': None, 'pb': 0, 'eps': 13657, 'industry': {'pe': 14.183297, 'pb': 1.1262985556}},
    }
    view.set_overview(data, 'FPT', 'sample')
    assert view.company_name.text() == 'Công ty thử nghiệm'
    assert view.sector.text() == 'Ngành: Công nghệ › Phần mềm'
    assert view.card_values['pe'].text() == 'Chưa có dữ liệu'
    assert view.card_values['pb'].text() == '0'
    assert view.card_values['eps'].text() == '13,657'
    assert view.listing_values['listing_date'].text() == '13/12/2006'
    assert view.listing_values['free_float_pct'].text() == '0 %'
    assert view.listing_values['treasury_shares'].text() == 'Chưa có dữ liệu'
    pe_row = next(r for r in range(view.ratios.rowCount()) if view.ratios.item(r, 0).text() == 'P/E')
    assert view.ratios.item(pe_row, 1).text() == 'Chưa có dữ liệu'
    assert view.ratios.item(pe_row, 2).text() == '14.18'
    exported = view.export_data()
    assert any(r['Nhóm'] == 'Trung bình ngành' and r['Chỉ tiêu'] == 'P/E' and r['Giá trị'] == 14.183297 for r in exported)
    assert not any(isinstance(r['Giá trị'], (dict, list)) for r in exported)
    view.close()


def test_legacy_overview_rows_are_supported(qt_app):
    data = overview_from_rows([
        {'nhom': 'get_stock_profile', 'chi_tieu': 'name_vn', 'gia_tri': 'Doanh nghiệp cũ'},
        {'nhom': 'get_company_overview', 'chi_tieu': 'industry', 'gia_tri': {'pe': 15}},
    ])
    view = OverviewView()
    view.set_overview(data, 'FPT')
    assert view.company_name.text() == 'Doanh nghiệp cũ'
    assert view.ratios.item(0, 2).text() == '15'
    view.close()


def test_worker_overview_provides_domain_sections(qt_app):
    class Gateway:
        async def call(self, tool, args, refresh):
            return {'symbol': 'FPT', 'name_vn': 'Công ty thử nghiệm'}, 'sample', False
    worker = Worker(None, 'lookup', {'symbol': 'FPT', 'section': 'overview', 'refresh': False})
    results = []
    worker.result.connect(results.append)
    asyncio.run(worker.lookup(Gateway()))
    assert set(results[0]['overview']) == {'profile', 'listing', 'metrics'}
    assert results[0]['overview']['profile']['name_vn'] == 'Công ty thử nghiệm'
    assert 'get_stock_profile' not in results[0]['stamp']
