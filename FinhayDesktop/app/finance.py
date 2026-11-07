"""Deterministic statement mapping. Missing/unknown fields never become zero."""
from decimal import Decimal, InvalidOperation


PATTERNS = (
    ('corporate', 'Doanh thu thuần', 'doanhthuthuanvebanhangvacungcapdichvu',
     'loinhuansauthuethunhapdoanhnghiep', 'loinhuansauthuecuacongtyme'),
    ('bank', 'Tổng thu nhập hoạt động', 'tongthunhaphoatdong',
     'loinhuansauthue', 'codongcuacongtyme'),
    ('securities', 'Doanh thu hoạt động', 'doanhthuhoatdong',
     'lnsauthue', 'lnsauthuecuachusohuu'),
    ('insurance', 'Doanh thu thuần (bảo hiểm)', 'doanhthuthuan',
     'lnstthunhapdn', 'lnstcuacongtyme'),
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
    def label(y, q):
        return f'Q{q}/{y}' if q else str(y)

    py, pq = previous_period(year, quarter) if quarter else (year - 1, None)
    targets = {'current': (year, quarter), 'previous': (py, pq), 'year_ago': (year - 1, quarter)}
    source, values = {}, {}
    for key, (y, q) in targets.items():
        raw = exact_row(rows, y, q)
        # Unknown basis is shown explicitly as returned, never compared as a quarter.
        row = (raw if basis == 'unknown' else resolve_quarter(rows, y, q, basis)) if q else raw
        source[key] = row
        values[key] = normalize(row) if row is not None else normalize({})
    current = values['current']
    base = dict(symbol=symbol, name=name, exchange=exchange, year=year, quarter=quarter,
                period_basis=basis if quarter else 'annual', currency='VND', report_scope='Nguồn chưa xác định',
                schema_version=2, period_label=label(year, quarter),
                previous_period_label=label(py, pq), year_ago_period_label=label(year - 1, quarter), **current)
    for metric in ('revenue', 'profit', 'parent_profit'):
        base[f'{metric}_previous'] = values['previous'][metric]
        base[f'{metric}_year_ago'] = values['year_ago'][metric]
    messages = []
    if exact_row(rows, year, quarter) is None:
        messages.append('Không có kỳ được chọn')
    elif quarter and basis == 'unknown':
        messages.append('Chưa xác minh quý riêng/lũy kế; số hiển thị là số nguồn trả về')
    elif source['current'] is None:
        messages.append('Thiếu kỳ để tách lũy kế')
    elif current['kind'] == 'unknown':
        messages.append('Chưa nhận diện mẫu báo cáo')
    elif any(current[k] is None for k in ('revenue', 'profit')):
        messages.append('Thiếu doanh thu hoặc LNST kỳ hiện tại')
    for key, description in (('previous', 'kỳ trước'), ('year_ago', 'cùng kỳ năm trước')):
        if key == 'previous' and not quarter:
            continue
        if any(values[key][metric] is None for metric in ('revenue', 'profit')):
            messages.append(f'Thiếu số liệu {description}')
        elif current['kind'] != 'unknown' and current['kind'] != values[key]['kind']:
            messages.append(f'Mẫu báo cáo {description} khác kỳ hiện tại; không tính %')
    for prefix, target in [('yoy', 'year_ago')] + ([('qoq', 'previous')] if quarter else []):
        old = values[target]
        comparable = (not quarter or basis in ('standalone', 'cumulative')) and current['kind'] != 'unknown' and old['kind'] == current['kind']
        for metric in ('revenue', 'profit', 'parent_profit'):
            comp = comparison(current[metric] if comparable else None, old[metric])
            for field, value in comp.items():
                base[f'{metric}_{prefix}_{field}'] = value
    base.update(status='missing' if messages else 'ok', message='; '.join(dict.fromkeys(messages)))
    return base


def sector_info(profile):
    path = [row for row in (profile.get('sector') or []) if isinstance(row, dict) and row.get('name')]
    top = next((row for row in path if row.get('level') == 1), None)
    group = next((row for row in path if row.get('level') == 3), None)
    group = group or (path[-1] if path else {})
    return {'sector_group': group.get('name'), 'sector_name': (top or {}).get('name'),
            'sector_slug': group.get('slug'), 'sector_level': group.get('level')}
