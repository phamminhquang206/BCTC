import csv
import json
from openpyxl import load_workbook
from app.storage import Store
from app.exporting import export_rows


def test_resume_upsert_cache_and_retry(tmp_path):
    path = tmp_path / 'db.sqlite3'
    store = Store(path)
    run = store.new_run({'year': 2025}, ['FPT', 'VCB', 'FPT'])
    store.finish(run, 'FPT', 'ok', {'revenue': 10, 'missing': None})
    store.save_response('statement', {'year': 2025, 'symbol': 'FPT'}, {'items': [{'amount': 12345678901234}]})
    store.close()
    reopened = Store(path)
    assert len(reopened.jobs(run)) == 2
    assert reopened.jobs(run)[0]['status'] == 'ok'
    assert reopened.jobs(run)[1]['status'] == 'pending'
    reopened.finish(run, 'VCB', 'error', {'message': 'network'})
    reopened.retry_errors(run)
    assert reopened.jobs(run)[1]['status'] == 'pending'
    assert reopened.jobs(run)[0]['status'] == 'ok'
    assert reopened.cached('statement', {'symbol': 'FPT', 'year': 2025})[0]['items'][0]['amount'] == 12345678901234
    assert reopened.cached('statement', {'symbol': 'FPT', 'year': 2024}) is None
    reopened.close()


def test_exports_preserve_units_nulls_and_guard_formulas(tmp_path):
    rows = [{'symbol': 'FPT', 'year': 2025, 'quarter': 1, 'revenue': 20225449892881, 'profit': None, 'currency': 'VND', 'note': '=1+1'}]
    xlsx, csvpath = tmp_path / 'data.xlsx', tmp_path / 'data.csv'
    export_rows(xlsx, rows)
    export_rows(csvpath, rows)
    book = load_workbook(xlsx)
    values = list(book['Du lieu'].values)
    assert values[1][3] == 20225449892881
    assert values[1][4] is None
    assert values[1][-1] == "'=1+1"
    assert book['Du lieu']['G2'].data_type == 's'
    with open(csvpath, encoding='utf-8-sig', newline='') as stream:
        record = next(csv.DictReader(stream))
    assert record['revenue'] == '20225449892881'
    assert record['profit'] == ''
    assert record['currency'] == 'VND'


def test_excel_large_vnd_integer_not_rounded(tmp_path):
    path = tmp_path / 'large.xlsx'
    export_rows(path, [{'assets': 123456789012345678}])
    cell = load_workbook(path)['Du lieu']['A2']
    assert cell.value == '123456789012345678'
    assert cell.data_type == 's'
