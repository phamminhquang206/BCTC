import csv
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


def safe_cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def export_rows(path, rows, metadata=None):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    if not keys:
        raise ValueError('Không có dữ liệu để xuất.')
    values = [[safe_cell(row.get(k)) for k in keys] for row in rows]
    if str(path).lower().endswith('.csv'):
        with open(path, 'w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(keys)
            writer.writerows(values)
        return
    book = Workbook()
    sheet = book.active
    sheet.title = 'Du lieu'
    sheet.append(keys)
    for row in values:
        # Excel stores only 15 significant digits for numeric cells. Preserve
        # larger VND integers as text instead of silently rounding statements.
        sheet.append([str(v) if isinstance(v, int) and abs(v) >= 10**15 else v for v in row])
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='164E63')
    for col in sheet.columns:
        sheet.column_dimensions[col[0].column_letter].width = min(42, max(16, len(str(col[0].value)) + 2))
    info = book.create_sheet('Thong tin')
    for key, val in {'nguon': 'Finhay MCP', 'don_vi_tien': 'VND (giá trị gốc)', **(metadata or {})}.items():
        info.append([key, safe_cell(val)])
    book.save(path)
