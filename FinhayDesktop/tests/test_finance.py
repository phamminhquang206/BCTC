import pytest
from app.finance import build_result, comparison, normalize, previous_period, resolve_quarter


def corp(year, quarter, revenue, profit, parent=None):
    return dict(year=year, quarter=quarter, doanhthuthuanvebanhangvacungcapdichvu=revenue,
                loinhuansauthuethunhapdoanhnghiep=profit, loinhuansauthuecuacongtyme=parent)


@pytest.mark.parametrize('row,kind,expected', [
    ({'doanhthuthuanvebanhangvacungcapdichvu': 20225449892881, 'loinhuansauthuethunhapdoanhnghiep': 2994964817097, 'loinhuansauthuecuacongtyme': 2509522220121}, 'corporate', 2509522220121),
    ({'tongthunhaphoatdong': 19269531000000, 'loinhuansauthue': 8633290000000, 'codongcuacongtyme': 8629050000000}, 'bank', 8629050000000),
    ({'doanhthuhoatdong': 3601759602481, 'lnsauthue': 819689190094, 'lnsauthuecuachusohuu': 817461309800}, 'securities', 817461309800),
])
def test_live_sample_mapping(row, kind, expected):
    # Values sampled from the connected Finhay tools; no account information.
    result = normalize(row)
    assert result['kind'] == kind
    assert result['parent_profit'] == expected


def test_unknown_and_null_stay_missing():
    assert normalize({'unknown': 5})['revenue'] is None
    assert normalize(corp(2025, 1, None, 0))['revenue'] is None
    assert normalize(corp(2025, 1, 0, 0))['revenue'] == 0


@pytest.mark.parametrize('current,base,percent,state', [
    (120, 100, 20, 'So sánh được'), (-20, 100, -120, 'Chuyển lỗ'),
    (10, -5, None, 'Chuyển lãi'), (-3, -5, None, 'Tiếp tục lỗ'),
    (10, 0, None, 'Kỳ gốc không dương'), (None, 10, None, 'Thiếu dữ liệu'),
])
def test_growth(current, base, percent, state):
    result = comparison(current, base)
    assert result['percent'] == percent
    assert result['state'] == state


def test_q1_uses_previous_year_q4_and_exact_year():
    rows = [corp(2025, 1, 120, 12, 10), corp(2024, 4, 100, 10, 9), corp(2024, 1, 80, 8, 7)]
    result = build_result('FPT', '', '', rows, 2025, 1, 'standalone')
    assert previous_period(2025, 1) == (2024, 4)
    assert result['revenue_qoq_percent'] == 20
    assert result['revenue_yoy_percent'] == 50
    missing = build_result('FPT', '', '', rows, 2025, 2, 'standalone')
    assert missing['status'] == 'missing'
    assert missing['revenue'] is None


def test_cumulative_conversion_and_missing_previous():
    rows = [corp(2025, 1, 100, 10, 8), corp(2025, 2, 250, 25, 20)]
    assert resolve_quarter(rows, 2025, 2, 'cumulative')['doanhthuthuanvebanhangvacungcapdichvu'] == 150
    assert resolve_quarter(rows, 2025, 1, 'cumulative') == rows[0]
    assert resolve_quarter(rows[1:], 2025, 2, 'cumulative') is None
    result = build_result('FPT', '', '', rows, 2025, 2, 'cumulative')
    assert result['revenue'] == 150
    assert result['revenue_qoq_percent'] == 50


def test_unknown_basis_displays_raw_without_growth():
    rows = [corp(2025, 2, 250, 25, 20), corp(2024, 2, 200, 20, 15)]
    result = build_result('FPT', '', '', rows, 2025, 2, 'unknown')
    assert result['revenue'] == 250
    assert result['revenue_yoy_percent'] is None
    assert result['status'] == 'missing'


def test_annual_and_cross_template_not_comparable():
    result = build_result('X', '', '', [corp(2025, None, 120, 10, 9), corp(2024, None, 100, 8, 7)], 2025, None, 'unknown')
    assert result['revenue_yoy_percent'] == 20
    assert 'revenue_qoq_percent' not in result
    rows = [corp(2025, 1, 120, 10, 9), dict(year=2024, quarter=1, tongthunhaphoatdong=100, loinhuansauthue=8)]
    assert build_result('X', '', '', rows, 2025, 1, 'standalone')['revenue_yoy_percent'] is None
