from datetime import datetime, timedelta
from copy import deepcopy

from PySide6.QtWidgets import QApplication

from app.price_view import VN, price_series, valid_ohlc, candle_color, GREEN, RED, FLAT
from app.gui import MainWindow
from app.price_view import candle_change


def bar(day, o=100, h=120, l=90, c=110, v=100):
    return dict(t=int(datetime.fromisoformat(day).replace(tzinfo=VN).timestamp()), o=o, h=h, l=l, c=c, v=v)


def test_weekly_ohlc_volume_and_day_order():
    rows = [bar('2026-11-03', 110, 130, 100, 125, 200), bar('2026-10-30'), bar('2026-11-02', 105, 115, 95, 110, 300)]
    original = deepcopy(rows)
    day = price_series(rows, '1D')
    assert [r['t'] for r in day] == sorted(r['t'] for r in rows)
    week = price_series(rows, '1W')
    assert len(week) == 2
    assert week[1] == bar('2026-11-02', 105, 130, 95, 125, 500)
    assert rows == original


def test_vietnam_week_boundary_and_cross_year():
    late_sunday_utc = datetime.fromisoformat('2026-11-01T18:00:00+00:00').timestamp()
    monday_vn = {**bar('2026-11-02'), 't': late_sunday_utc}
    assert price_series([monday_vn], '1W')[0]['t'] == bar('2026-11-02')['t']
    week = price_series([bar('2025-12-31'), bar('2026-01-01', c=115)], '1W')
    assert len(week) == 1
    assert week[0]['t'] == bar('2025-12-29')['t']
    assert week[0]['c'] == 115


def test_missing_ohlc_never_becomes_a_fake_candle_or_zero_volume():
    rows = [bar('2026-11-02'), bar('2026-11-03', o=None, v=None)]
    daily = price_series(rows)
    assert len(daily) == 2 and not valid_ohlc(daily[1])
    week = price_series(rows, '1W')[0]
    assert week['o'] is None and week['c'] is None and week['v'] is None
    assert not valid_ohlc(bar('2026-11-02', h=95))
    assert not valid_ohlc(bar('2026-11-02', c=float('nan')))
    assert price_series([bar('2026-11-02', v=0)], '1W')[0]['v'] == 0


def test_duplicate_daily_stamp_does_not_double_weekly_volume():
    rows = [bar('2026-11-02', v=100), bar('2026-11-02', c=115, v=200)]
    assert len(price_series(rows)) == 1
    assert price_series(rows, '1W')[0]['v'] == 200


def test_green_red_doji_match_open_close():
    assert candle_color(bar('2026-11-02', c=110)) == GREEN
    assert candle_color(bar('2026-11-02', c=95)) == RED
    assert candle_color(bar('2026-11-02', c=100)) == FLAT


def test_switch_day_week_is_local_and_exports_matching_series(tmp_path):
    app = QApplication.instance()
    window = MainWindow(tmp_path)
    window.sections.setCurrentIndex(2)
    rows = [bar('2026-11-02', v=100), bar('2026-11-03', c=115, v=200)]
    window.on_result('lookup', {'section': 'price', 'symbol': 'MWG', 'rows': rows, 'stamp': 'cache-time',
        'quote': {'price': 115, 'change_percent': 1.2, 'updated_at': '2026-11-03T08:00:00+00:00'}})
    requests = []
    window.launch = lambda *args: requests.append(args)
    panel = window.price_panel
    window.resize(1440, 1000)
    window.show()
    app.processEvents()
    assert panel.table.isHidden()
    assert len(panel.chart.rows) == 2
    assert panel.chart.height() > 300
    panel.timeframe.setCurrentIndex(1)
    assert len(panel.chart.rows) == 1
    assert panel.chart.rows[0]['v'] == 300
    assert panel.table.model.column_labels['t'] == 'Tuần từ (thứ Hai)'
    exported = panel.table.export_data(panel.table.rows(False))
    assert exported[0]['Tuần từ (thứ Hai)'] == '02/11/2026'
    assert exported[0]['Khối lượng (cổ phiếu)'] == 300
    assert exported[0]['Đóng cửa (VND)'] == 115
    panel.show_table.setChecked(True)
    app.processEvents()
    assert panel.table.isVisible()
    panel.show_table.setChecked(False)
    panel.timeframe.setCurrentIndex(0)
    assert len(panel.table.rows(False)) == 2
    assert requests == []
    window.close()


def test_chart_zoom_reset_and_single_or_empty_series(tmp_path):
    from app.price_view import CandlestickChart
    chart = CandlestickChart()
    start = datetime(2025, 1, 1, tzinfo=VN)
    chart.set_rows([{**bar('2025-01-01'), 't': int((start + timedelta(days=i)).timestamp())} for i in range(240)])
    assert len(chart.visible_rows) == 150
    chart.zoom(.8)
    assert len(chart.visible_rows) == 120
    chart.reset_view()
    assert len(chart.visible_rows) == 240
    chart.set_rows([bar('2026-11-02')])
    chart.resize(600, 350)
    chart.show()
    QApplication.processEvents()
    assert not chart.grab().isNull()
    chart.set_rows([])
    assert not chart.grab().isNull()
    chart.close()


def test_candle_percent_bases_and_missing_data():
    import pytest
    assert candle_change(110, 100) == pytest.approx(10)
    assert candle_change(90, 100) == pytest.approx(-10)
    assert candle_change(100, 100) == 0
    for base in (None, 0, -1, float('nan')):
        assert candle_change(100, base) is None


def test_sidebar_and_percent_follow_active_timeframe(tmp_path):
    import pytest
    window = MainWindow(tmp_path)
    window.sections.setCurrentIndex(2)
    panel = window.price_panel
    rows = [bar('2026-10-30', c=100), bar('2026-11-02', o=100, c=110),
            bar('2026-11-03', o=110, c=120)]
    panel.set_result(rows, {}, 'FPT', '')
    window.resize(1360, 900)
    window.show()
    QApplication.processEvents()
    assert panel.candle_values['open_change'].text() == '+9.09%'
    assert panel.candle_values['previous_change'].text() == '+9.09%'
    assert window.from_date.parent().isAncestorOf(window.fetch_buttons['price'])
    before = panel.chart.width()
    panel.show_details.setChecked(False)
    QApplication.processEvents()
    assert panel.sidebar.isHidden() and panel.chart.width() > before
    panel.timeframe.setCurrentIndex(1)
    assert panel.candle_values['open_change'].text() == '+20.00%'
    assert panel.candle_values['previous_change'].text() == '+20.00%'
    panel.show_candle(panel.series[0])
    assert panel.candle_values['previous_change'].text() == '—'
    # Missing preceding close must not silently compare to an older candle.
    panel.timeframe.setCurrentIndex(0)
    panel.set_result([rows[0], bar('2026-11-02', c=None), rows[-1]], {}, 'FPT', '')
    assert panel.candle_values['previous_change'].text() == '—'
    window.close()
