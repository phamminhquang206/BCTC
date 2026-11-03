"""Experimental DStock quarterly income-statement collector.

Only public HTML; no login, anti-bot bypass or undocumented private API.
Financial units are preserved from the page; values are NOT certified filings.
"""
from __future__ import annotations
import csv, json, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"table_scan.json"
TZ=timezone(timedelta(hours=7))
PERIODS=("Q3/2025","Q2/2026","Q3/2026")
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; VNFinancialResearch/0.1; public HTML only)"}

def norm(s):
    import unicodedata
    s=unicodedata.normalize("NFD",s.lower())
    return "".join(x for x in s if unicodedata.category(x)!="Mn").replace("đ","d").strip(" +-")

def num(s):
    s=s.strip().replace("\u00a0","").replace(" ","")
    if s in ("","-","—","N/A"): return None
    # DStock display uses comma grouping, decimal dot.
    if not re.fullmatch(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?",s):return None
    return float(s.replace(",",""))

def extract(html):
    soup=BeautifulSoup(html,"html.parser")
    matches=[]
    for table in soup.select("table"):
        trs=[]
        for tr in table.select("tr"):
            cells=tr.find_all(["td","th"],recursive=False)
            if not cells: continue
            trs.append([x.get_text(" ",strip=True) for x in cells])
        for i,row in enumerate(trs):
            periods=[re.search(r"Q\s*([1-4])\s*/\s*(20\d{2})",x,re.I) for x in row]
            indices={f"Q{m.group(1)}/{m.group(2)}":j for j,m in enumerate(periods) if m}
            if not all(k in indices for k in PERIODS):continue
            fields={}
            for values in trs[i+1:]:
                if len(values)<=max(indices.values()):continue
                label=norm(values[0])
                key=None
                if "doanh thu thuan" in label: key="revenue"
                elif "loi nhuan sau thue thu nhap doanh nghiep" in label or label=="loi nhuan sau thue": key="profit"
                if key and key not in fields:
                    fields[key]={k:num(values[j]) for k,j in indices.items() if k in PERIODS}
            if fields:matches.append(fields)
    return matches

def main():
    tickers=[]
    path=ROOT/"config"/"table_tickers.csv"
    if path.exists():
        with path.open(encoding="utf-8-sig",newline="") as f:
            tickers=[r["ticker"].strip().upper() for r in csv.DictReader(f) if r.get("ticker","").strip()]
    results=[]
    for ticker in tickers[:25]:
        if not re.fullmatch(r"[A-Z]{3,5}",ticker):continue
        url="https://dstock.vndirect.com.vn/bao-cao-ket-qua-kinh-doanh/"+quote(ticker)
        item={"ticker":ticker,"source_url":url,"source":"DStock public HTML","status":"unavailable"}
        try:
            response=requests.get(url,headers=HEADERS,timeout=25)
            response.raise_for_status()
            matches=extract(response.text)
            item["table_candidates"]=len(matches)
            if len(matches)==1 and all(all(matches[0].get(k,{}).get(p) is not None for p in PERIODS) for k in ("revenue","profit")):
                v=matches[0];item["values"]=v
                if v["revenue"]["Q2/2026"]>0 and v["profit"]["Q2/2026"]>0:
                    item["qoq_revenue_pct"]=round((v["revenue"]["Q3/2026"]/v["revenue"]["Q2/2026"]-1)*100,2)
                    item["qoq_profit_pct"]=round((v["profit"]["Q3/2026"]/v["profit"]["Q2/2026"]-1)*100,2)
                item["status"]="candidate_unverified"
                item["passes_numeric_screen"]=v["revenue"]["Q3/2026"]>v["revenue"]["Q2/2026"] and v["profit"]["Q3/2026"]>v["profit"]["Q2/2026"] and v["profit"]["Q3/2026"]>0
            else:item["status"]="html_table_missing_or_incomplete"
        except requests.RequestException as e:item["error"]=str(e)[:250]
        results.append(item)
        time.sleep(1)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    output={"run_at":datetime.now(TZ).isoformat(),"coverage":"PILOT only; public DStock HTML, not exchange disclosures","unit":"as displayed by DStock; check page before use","periods":PERIODS,"results":results}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"tickers":len(results),"candidate_unverified":sum(x["status"]=="candidate_unverified" for x in results),"errors":[{"ticker":x["ticker"],"status":x["status"]} for x in results if x["status"]!="candidate_unverified"]},ensure_ascii=False))
if __name__=="__main__":main()
