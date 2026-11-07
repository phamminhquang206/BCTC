from copy import deepcopy
from math import sqrt

import pytest
from PySide6.QtWidgets import QApplication
from app.indicators import calculate_indicators
from app.gui import MainWindow
from test_price_view import bar


def closes(values):
    return [{'c': value} for value in values]


def test_sma_bb_population_std_and_warmup():
    rows = closes([1, 2, 3, 4])
    original = deepcopy(rows)
    result = calculate_indicators(rows, [3], 3, 2)
    assert result['MA3'] == [None, None, 2, 3]
    assert result['BB giữa'] == result['MA3']
    assert result['BB trên'][2] == pytest.approx(2 + 2 * sqrt(2 / 3))
    assert result['BB dưới'][3] == pytest.approx(3 - 2 * sqrt(2 / 3))
    assert rows == original
    assert calculate_indicators([], [20], 20, 2, 14)['RSI14'] == []


def test_wilder_rsi_seed_and_smoothing_known_prices():
    prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
              45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
    result = calculate_indicators(closes(prices), rsi_period=14)['RSI14']
    assert result[:14] == [None] * 14
    assert result[14] == pytest.approx(70.464135, abs=1e-6)
    assert result[15] == pytest.approx(66.249619, abs=1e-6)


@pytest.mark.parametrize('prices,expected', [([1, 2, 3, 4], 100), ([4, 3, 2, 1], 0), ([2, 2, 2, 2], 50)])
def test_rsi_one_way_and_flat(prices, expected):
    assert calculate_indicators(closes(prices), rsi_period=3)['RSI3'][-1] == expected


@pytest.mark.parametrize('missing', [None, 0, -1, float('nan')])
def test_missing_close_breaks_warmup(missing):
    result = calculate_indicators(closes([1, 2, 3, missing, 4, 5, 6]), [2], 2, 2, 2)
    assert result['MA2'][3:5] == [None, None]
    assert result['RSI2'][3:6] == [None, None, None]
    assert result['RSI2'][6] == 100


def test_parameters_are_validated():
    for period in (0, -1, 1, 2.5, True):
        with pytest.raises(ValueError):
            calculate_indicators([], [period])
    with pytest.raises(ValueError):
        calculate_indicators([], bb_period=20, bb_deviation=0)


def test_ui_indicator_toggles_timeframe_hover_and_zoom(tmp_path):
    window = MainWindow(tmp_path)
    window.sections.setCurrentIndex(2)
    panel = window.price_panel
    requests = []
    window.launch = lambda *args: requests.append(args)
    rows = [bar(f'2026-11-{day:02}', o=100, h=130, l=90, c=100 + day) for day in range(2, 28)]
    panel.set_result(rows, {}, 'FPT', '')
    assert panel.chart.indicators == {}
    panel.chart.zoom(.8)
    viewport = (panel.chart.end, panel.chart.count)
    for key in panel.indicator_checks:
        panel.indicator_periods[key].setValue(3)
        panel.indicator_checks[key].setChecked(True)
    assert (panel.chart.end, panel.chart.count) == viewport
    assert panel.chart.indicators['MA3'][rows[-1]['t']] == 126
    assert 'MA3: 126.00' in panel.indicator_values.text()
    window.resize(1360, 900)
    window.show()
    QApplication.processEvents()
    assert not panel.chart.grab().isNull()
    panel.chart.reset_view()
    assert panel.chart.indicators['MA3'][rows[-1]['t']] == 126
    panel.timeframe.setCurrentIndex(1)
    assert len(panel.series) == 4
    # Recomputed from weekly closes (108, 115, 122, 127), not daily MA.
    assert panel.chart.indicators['MA3'][panel.series[-1]['t']] == pytest.approx((115 + 122 + 127) / 3)
    assert panel.chart.indicators['RSI3'][panel.series[-1]['t']] == 100
    assert panel.table.model.column_order == ['t', 'o', 'h', 'l', 'c', 'v']
    for check in panel.indicator_checks.values():
        check.setChecked(False)
    assert panel.chart.indicators == {}
    assert panel.indicator_values.text() == ''
    assert requests == []
    window.close()
