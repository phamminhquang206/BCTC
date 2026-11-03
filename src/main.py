"""Conservative BCTC growth watcher: source-linked observations only.

The MVP processes explicit official BCTC URLs from config/reports.csv.
No automatic whole-market discovery is claimed. A PDF must contain identifiable
line items and a per-quarter column; otherwise it is flagged for review.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import fitz
import requests
import ssl
import truststore
truststore.inject_into_ssl()  # Use OS CA roots while retaining certificate verification.
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
REPORTS = ROOT / 'reports'
TZ = timezone(timedelta(hours=7))
HEADERS = {'User-Agent': 'VNFinancialGrowthAgent/0.1 (+research; public source only)'}


def now():
    return datetime.now(TZ)


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def get_text_from_pdf(url):
    parsed = requests.utils.urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValueError('Only public HTTPS URLs supported')
    try:
        r = requests.get(url, timeout=35, headers=HEADERS, allow_redirects=True, stream=True)
    except requests.exceptions.SSLError as exc:
        raise RuntimeError('Official PDF HTTPS certificate validation failed. Source is temporarily blocked; do not disable TLS verification. Configure a trusted CA certificate bundle or use a validated alternate official URL.') from exc
    r.raise_for_status()
    if requests.utils.urlparse(r.url).scheme != 'https':
        raise ValueError('Redirected to insecure URL')
    max_bytes = 25 * 1024 * 1024
    raw = bytearray()
    for part in r.iter_content(65536):
        raw.extend(part)
        if len(raw) > max_bytes:
            raise ValueError('PDF exceeds 25MB limit')
    if not raw.startswith(b'%PDF'):
        raise ValueError('URL does not return a PDF')
    with fitz.open(stream=bytes(raw), filetype='pdf') as pdf:
        return '\n'.join(page.get_text() for page in pdf[:min(len(pdf), 30)]), hashlib.sha256(raw).hexdigest()


def parse_number(s):
    # Parsed ONLY for suggested review, not automatic verified financial figures.
    s = s.replace(' ', '').replace('\xa0', '').strip()
    negative = s.startswith('(') and s.endswith(')')
    s = s.strip('()').replace(',', '')
    if not re.fullmatch(r'-?\d+(\.\d+)?', s):
        return None
    n = float(s)
    return -n if negative else n


def inspect(text):
    # Extract candidate rows, but column meaning varies across issuers.
    # Deliberately NOT record values as verified observations.
    result = {}
    for label, pattern in {
        'revenue': r'(?:doanh\s+thu\s+thuần|doanh\s+thu\s+bán\s+hàng\s+và\s+cung\s+cấp\s+dịch\s+vụ)',
        'profit': r'(?:lợi\s+nhuận\s+sau\s+thuế(?:\s+thu\s+nhập\s+doanh\s+nghiệp)?)',
    }.items():
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                result[label] = '\n'.join(lines[max(0, i-1):min(len(lines), i+5)])[:500]
                break
    return result


def growth(curr, old):
    if curr is None or old is None or old <= 0:
        return None
    return (curr / old - 1) * 100


def is_qualified(obs):
    # All three observed values must be independently verified and comparable.
    if not obs.get('verified') or not obs.get('comparable'):
        return False
    x = obs.get('values', {})
    vals = [x.get('revenue'), x.get('revenue_qoq'), x.get('profit'), x.get('profit_qoq')]
    return all(isinstance(v, (int,float)) for v in vals) and vals[0] > vals[1] and vals[2] > vals[3] and vals[2] > 0


def font_name():
    for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont('VNUnicode', path))
            return 'VNUnicode'
    return 'Helvetica'


def pdf_report(rows, log, output):
    f = font_name()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='VNTitle', parent=styles['Heading1'], fontName=f, fontSize=15, alignment=TA_CENTER, leading=20))
    styles.add(ParagraphStyle(name='VN', parent=styles['Normal'], fontName=f, fontSize=8, leading=12))
    doc = SimpleDocTemplate(str(output), pagesize=landscape(A4), leftMargin=30, rightMargin=30)
    story = [Paragraph('Báo cáo sàng lọc BCTC – Việt Nam', styles['VNTitle']), Spacer(1, 12)]
    story.append(Paragraph(f"Ngày chạy: {log['run_at']} | Báo cáo kiểm tra: {log['checked']} | Đạt tiêu chí: {len(rows)} | Chờ xác minh: {log['needs_review']}", styles['VN']))
    story.append(Spacer(1, 8))
    if not rows:
        story.append(Paragraph('Chưa có doanh nghiệp đạt chuẩn với dữ liệu đã xác minh. KHÔNG có nghĩa toàn thị trường không có doanh nghiệp tăng trưởng.', styles['VN']))
    else:
        cols = ['Mã', 'Sàn', 'Quý', 'DT quý', 'DT QoQ', 'LNST quý', 'LNST QoQ', 'Nguồn']
        data = [[Paragraph(c,styles['VN']) for c in cols]]
        for x in rows:
            v = x['values']
            data.append([Paragraph(str(t),styles['VN']) for t in [x['ticker'],x['exchange'],x['period'],v['revenue'], f"{growth(v['revenue'],v['revenue_qoq']):+.1f}%" if growth(v['revenue'],v['revenue_qoq']) is not None else 'N/A', v['profit'],f"{growth(v['profit'],v['profit_qoq']):+.1f}%" if growth(v['profit'],v['profit_qoq']) is not None else 'N/A',x['source_url'][:52]]])
        tbl=Table(data,repeatRows=1,colWidths=[60,60,65,85,85,90,90,240])
        tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP')]))
        story.append(tbl)
    story.append(Spacer(1,12))
    story.append(Paragraph('Phạm vi: chỉ các URL BCTC đã được đưa vào danh sách nguồn và đã qua bước xác minh. Phiên bản này không tự động xác nhận số liệu từ PDF hay quét đầy đủ HOSE/HNX/UPCoM.',styles['VN']))
    doc.build(story)


def run():
    DATA.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    state_path = DATA / 'state.json'
    state = load_json(state_path, {'reports': {}, 'verified_observations': []})
    try:
        with (ROOT / 'config/reports.csv').open(encoding='utf-8-sig', newline='') as file:
            entries = list(csv.DictReader(file))
    except FileNotFoundError:
        entries = []
    errors = []
    checked = 0
    for item in entries:
        url = item.get('report_url','').strip()
        if not url: continue
        key = '|'.join(item.get(k,'') for k in ['ticker','exchange','period','scope','report_url'])
        try:
            txt, sha = get_text_from_pdf(url)
            old = state['reports'].get(key)
            if old and old.get('sha256') == sha and old.get('status') == 'needs_review':
                continue
            checked += 1
            state['reports'][key] = {'ticker':item.get('ticker'), 'exchange':item.get('exchange'), 'period':item.get('period'), 'scope':item.get('scope'), 'source_url':item.get('source_url') or url, 'pdf_url':url, 'sha256':sha, 'status':'needs_review', 'candidates':inspect(txt), 'updated_at':now().isoformat()}
        except Exception as exc:
            errors.append({'ticker':item.get('ticker'), 'url':url, 'error':str(exc)[:400], 'status':'blocked' if 'certificate validation failed' in str(exc) else 'download_failed'})
    verified = [o for o in state.get('verified_observations',[]) if is_qualified(o)]
    log = {'run_at': now().isoformat(), 'reports_configured':len(entries), 'checked':checked, 'needs_review':sum(1 for x in state['reports'].values() if x.get('status')=='needs_review'), 'qualified':len(verified), 'errors':errors, 'coverage':'partial; configured URLs only'}
    state['last_run'] = log
    write_json(state_path,state)
    write_json(DATA / 'scan_log.json',log)
    filename = REPORTS / f"BCTC_Growth_{now().strftime('%Y%m%d')}.pdf"
    pdf_report(verified,log,filename)
    print(json.dumps(log,ensure_ascii=False))
    print('PDF:',filename)


if __name__ == '__main__':
    run()
