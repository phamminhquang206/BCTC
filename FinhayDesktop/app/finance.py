"""Deterministic statement mapping. Missing/unknown fields never become zero."""
from decimal import Decimal, InvalidOperation


PATTERNS = (
    ('corporate', 'Doanh thu thuần', 'doanhthuthuanvebanhangvacungcapdichvu',
     'loinhuansauthuethunhapdoanhnghiep', 'loinhuansauthuecuacongtyme'),
    ('bank', 'Tổng thu nhập hoạt động', 'tongthunhaphoatdong',
     'loinhuansauthue', 'codongcuacongtyme'),
    ('securities', 'Doanh thu hoạt động', 'doanhthuhoatdong',
     'lnsauthue', 'lnsauthuecuachusohuu'),
)


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        val = Decimal(str(value))
        if not val.is_finite():
            return None
        return int(val) if val == val.to_integral_value() else float(val)
    except (InvalidOperation, ValueError):
        return None


def normalize(row):
    for kind, label, revenue, profit, parent in PATTERNS:
        if revenue in row and profit in row:
            return dict(kind=kind, revenue_label=label, revenue=number(row[revenue]),
                        profit=number(row[profit]), parent_profit=number(row.get(parent)))
    return dict(kind='unknown', revenue_label='Chưa nhận diện mẫu', revenue=None, profit=None, parent_profit=None)


def previous_period(year, quarter):
    return (year, quarter - 1) if quarter > 1 else (year - 1, 4)


def exact_row(rows, year, quarter):
    return next((r for r in rows if r.get('year') == year and r.get('quarter') == quarter), None)


def comparison(current, base):
    if current is None or base is None:
        return {'delta': None, 'percent': None, 'state': 'Thiếu dữ liệu'}
    delta = current - base
    if base > 0:
        state = 'Chuyển lỗ' if current < 0 else 'So sánh được'
        return {'delta': delta, 'percent': delta / base * 100, 'state': state}
    state = 'Chuyển lãi' if base < 0 and current > 0 else ('Tiếp tục lỗ' if current < 0 else 'Kỳ gốc không dương')
    return {'delta': delta, 'percent': None, 'state': state}


def resolve_quarter(rows, year, quarter, basis):
    row = exact_row(rows, year, quarter)
    if row is None:
        return None
    if basis == 'standalone':
        return row
    if basis != 'cumulative':
        return None
    if quarter == 1:
        return row
    prev = exact_row(rows, year, quarter - 1)
    if prev is None:
        return None
    result = {'year': year, 'quarter': quarter}
    for key, value in row.items():
        if key in ('year', 'quarter'):
            continue
        a, b = number(value), number(prev.get(key))
        result[key] = a - b if a is not None and b is not None else None
    return result


def build_result(symbol, name, exchange, rows, year, quarter, basis):
    raw = exact_row(rows, year, quarter)
    base = dict(symbol=symbol, name=name, exchange=exchange, year=year, quarter=quarter,
                period_basis=basis if quarter else 'annual', currency='VND', report_scope='Nguồn chưa xác định')
    if raw is None:
        return {**base, 'status': 'missing', 'message': 'Không có kỳ được chọn'}
    current = resolve_quarter(rows, year, quarter, basis) if quarter else raw
    # An unverified quarter can be displayed as returned, but is never used for growth.
    val = normalize(current if current is not None else raw)
    base.update(val)
    if val['kind'] == 'unknown':
        return {**base, 'status': 'missing', 'message': 'Chưa nhận diện mẫu báo cáo'}
    incomplete = any(val[k] is None for k in ('revenue', 'profit', 'parent_profit'))
    base.update(status='missing' if incomplete else 'ok', message='Thiếu chỉ tiêu' if incomplete else '')
    if quarter and basis == 'unknown':
        base.update(status='missing', message='Chưa xác minh quý riêng/lũy kế; số hiển thị là số nguồn trả về')
    elif quarter and current is None:
        base.update(status='missing', revenue=None, profit=None, parent_profit=None, message='Thiếu kỳ để tách lũy kế')
    targets = [('yoy', year - 1, quarter)]
    if quarter:
        py, pq = previous_period(year, quarter)
        targets.append(('qoq', py, pq))
    for prefix, by, bq in targets:
        old = resolve_quarter(rows, by, bq, basis) if bq else exact_row(rows, by, None)
        normalized = normalize(old) if old else {}
        for key in ('revenue', 'profit', 'parent_profit'):
            comparable = current is not None and old is not None and normalized.get('kind') == val['kind']
            comp = comparison(base.get(key) if comparable else None, normalized.get(key))
            for field, value in comp.items():
                base[f'{key}_{prefix}_{field}'] = value
    return base
