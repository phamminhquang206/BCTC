"""Build a self-contained HTML report from saved Vnstock API observations."""
import html, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data/api_scan.json"
DEST=ROOT/"BCTC_Report.html"
PERIODS=("2025-Q3","2026-Q2","2026-Q3")

def fmt(v):
    return "—" if v is None else f"{v/1e9:,.2f}"

def growth(new, old):
    if new is None or old is None or old <= 0:
        return "—"
    return f"{(new/old-1)*100:+.2f}%"

def cell(s):
    return html.escape(str(s))

def main():
    data=json.loads(SRC.read_text(encoding="utf-8"))
    rows=[]
    qualified=0
    for item in data.get("results",[]):
        vals={(r["period"],r["id"]):r.get("value") for r in item.get("raw_rows",[]) if r.get("unit")=="VNĐ"}
        rev=[vals.get((p,"IS_NET_REVENUE")) for p in PERIODS]
        profit=[vals.get((p,"IS_NET_PROFIT_AFTER_TAX")) for p in PERIODS]
        complete=all(v is not None for v in rev+profit)
        passed=complete and rev[2]>rev[1] and profit[2]>profit[1]
        qualified+=int(passed)
        status="Đạt tiêu chí" if passed else ("Không đạt" if complete else "Thiếu dữ liệu")
        values=[item.get("ticker",""),status,*map(fmt,rev),growth(rev[2],rev[1]),growth(rev[2],rev[0]),*map(fmt,profit),growth(profit[2],profit[1]),growth(profit[2],profit[0])]
        rows.append("<tr data-status='"+("pass" if passed else "other")+"'>"+ "".join("<td>"+cell(x)+"</td>" for x in values)+"</tr>")
    headers=["Mã","Trạng thái","DT Q3/25","DT Q2/26","DT Q3/26","DT QoQ","DT YoY","LNST Q3/25","LNST Q2/26","LNST Q3/26","LNST QoQ","LNST YoY"]
    generated=datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M")
    content="""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Báo cáo tăng trưởng BCTC Q3/2026</title>
<style>body{font:15px system-ui,Arial,sans-serif;color:#17212e;background:#f6f8fb;margin:0;padding:28px}main{max-width:1400px;margin:auto}h1{margin-bottom:5px}.muted{color:#586578}.stats{display:flex;gap:14px;flex-wrap:wrap;margin:22px 0}.stat{background:white;border:1px solid #dfe4eb;border-radius:10px;padding:15px 22px;min-width:130px}.stat strong{display:block;font-size:26px}input,select{padding:10px;border:1px solid #bfc8d4;border-radius:7px;margin:8px 8px 16px 0}table{border-collapse:collapse;width:100%;background:white;white-space:nowrap}th,td{padding:11px;border-bottom:1px solid #e5e9ef;text-align:right}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}th{background:#e9eef5;position:sticky;top:0;cursor:pointer}tr:hover{background:#f2f6ff}.scroll{overflow:auto;border:1px solid #dfe4eb;border-radius:10px}footer{color:#586578;margin-top:22px;line-height:1.6}</style></head><body><main>
<h1>BCTC Growth Scanner — Q3/2026</h1>
<p class="muted">Cập nhật: __DATE__ (GMT+7) · Đơn vị số liệu: tỷ VNĐ · Nguồn: Vnstock API, chưa đối chiếu BCTC gốc.</p>
<div class="stats"><div class="stat">Đã xử lý<strong>__COUNT__</strong></div><div class="stat">Đạt tiêu chí<strong>__PASS__</strong></div><div class="stat">Chưa đạt / thiếu<strong>__OTHER__</strong></div></div>
<label>Tìm mã: <input id="q" placeholder="VD: FPT"></label><label>Hiển thị: <select id="filter"><option value="all">Tất cả</option><option value="pass">Chỉ đạt tiêu chí</option></select></label>
<div class="scroll"><table id="results"><thead><tr>__HEADERS__</tr></thead><tbody>__ROWS__</tbody></table></div>
<footer><p><b>Tiêu chí:</b> Doanh thu thuần và lợi nhuận sau thuế Q3/2026 đều tăng so với Q2/2026; cần đủ dữ liệu cả ba quý. QoQ so với Q2/2026, YoY so với Q3/2025.</p><p>Doanh nghiệp ngân hàng/bảo hiểm có cấu trúc doanh thu khác; dữ liệu thiếu được đánh dấu thay vì tự suy diễn. Kết quả chỉ bao gồm mã đã quét, không đại diện toàn thị trường.</p></footer></main>
<script>const q=document.getElementById('q'),f=document.getElementById('filter'),rows=[...document.querySelectorAll('#results tbody tr')];function update(){const term=q.value.trim().toUpperCase();rows.forEach(r=>r.hidden=!(r.cells[0].textContent.toUpperCase().includes(term)&&(f.value==='all'||r.dataset.status===f.value)))}q.addEventListener('input',update);f.addEventListener('change',update);document.querySelectorAll('th').forEach((th,i)=>{let asc=true;th.addEventListener('click',()=>{const body=document.querySelector('tbody');rows.sort((a,b)=>{const av=a.cells[i].textContent,bv=b.cells[i].textContent;const an=Number(av.replaceAll(',','').replace('%','')),bn=Number(bv.replaceAll(',','').replace('%',''));return (av!=='—'&&bv!=='—'&&!Number.isNaN(an)&&!Number.isNaN(bn)?an-bn:av.localeCompare(bv,'vi'))*(asc?1:-1)});asc=!asc;rows.forEach(r=>body.appendChild(r))})});</script></body></html>"""
    for a,b in {"__DATE__":generated,"__COUNT__":str(len(rows)),"__PASS__":str(qualified),"__OTHER__":str(len(rows)-qualified),"__HEADERS__":"".join("<th>"+cell(x)+"</th>" for x in headers),"__ROWS__":"".join(rows)}.items():
        content=content.replace(a,b)
    DEST.write_text(content,encoding="utf-8")
    print(f"Generated {DEST.name}: {len(rows)} tickers, {qualified} qualified")

if __name__=="__main__":
    main()
