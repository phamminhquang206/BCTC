"""Pilot the documented vnstock Fundamental quarterly financial API.

Keeps raw field IDs/units and periods for auditing; does not silently certify
figures or overwrite manually verified observations.
"""
import csv, json, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"api_scan.json"
PERIODS=("2025-Q3","2026-Q2","2026-Q3")

def safe(v):
    import math
    if v is None:return None
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError):return None

def main():
    from vnstock import Fundamental
    with (ROOT/"config/table_tickers.csv").open(encoding="utf-8-sig",newline="") as f:
        tickers=[r["ticker"].strip().upper() for r in csv.DictReader(f) if r.get("ticker","").strip()]
    results=[]
    for ticker in tickers[:20]:
        if not re.fullmatch(r"[A-Z]{3,5}",ticker):continue
        item={"ticker":ticker,"source":"vnstock Fundamental (underlying provider selected by library)","status":"not_processed"}
        try:
            df=Fundamental().equity(ticker).income_statement(period="quarter",format="long")
            item["columns"]=[str(c) for c in df.columns]
            if not {"period","id","value"}.issubset(df.columns):
                item["status"]="unexpected_schema"
            else:
                relevant=df[df["period"].astype(str).isin(PERIODS)].copy()
                item["periods_found"]=sorted(set(relevant["period"].astype(str)))
                item["field_ids"]=sorted(set(relevant["id"].astype(str)))[:160]
                item["raw_rows"]=[]
                for _,row in relevant.iterrows():
                    field=str(row["id"])
                    if field.upper() in ("IS_NET_REVENUE","IS_NET_PROFIT_AFTER_TAX","IS_REVENUE"):
                        item["raw_rows"].append({"period":str(row["period"]),"id":field,"name":str(row.get("name","")),"unit":str(row.get("unit","")),"value":safe(row["value"])})
                item["raw_rows"]=item["raw_rows"][:160]
                item["status"]="data_received_review_mapping" if item["raw_rows"] else "no_matching_fields"
        except Exception as exc:
            item["status"]="api_error"
            item["error"]=str(exc)[:400]
        results.append(item)
        time.sleep(2)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"run_at":datetime.now(timezone(timedelta(hours=7))).isoformat(),"periods_requested":PERIODS,"coverage":"3-ticker API pilot only; values not verified","results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"api_pilot":len(results),"statuses":[{"ticker":r["ticker"],"status":r["status"]} for r in results]},ensure_ascii=False))
if __name__=="__main__":main()
