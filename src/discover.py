"""Best-effort discovery of *public* quarterly filings, not whole-market coverage.

Search indexes are used as discovery hints. Files are only queued when their
download URL belongs to a recognized official disclosure domain. Every
candidate remains unverified until a person checks the financial statements.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse, urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "reports.csv"
OUT = ROOT / "data" / "discovery_log.json"
QUEUE = ROOT / "data" / "discovered_pages.json"
TZ = timezone(timedelta(hours=7))
UA = {"User-Agent": "VietnamFinancialGrowthResearchBot/0.2 (+public-index; limited discovery)"}
DOMAINS = ("staticfile.hsx.vn", "hsx.vn", "www.hsx.vn", "hnx.vn", "www.hnx.vn",
           "upcom.hnx.vn", "www.upcom.hnx.vn", "owa.hnx.vn", "congbothongtin.ssc.gov.vn")
TICKER_RE = re.compile(r"(?<![A-Z])[A-Z]{3}(?![A-Z])")
PDF_RE = re.compile(r"\.pdf(?:$|[?#])", re.I)
TITLE_RE = re.compile(r"(báo cáo tài chính|bao cao tai chinh|bctc|financial statements?)", re.I)

def recognized(url):
    p = urlparse(url)
    return p.scheme == "https" and p.hostname and p.hostname.lower() in DOMAINS

def period():
    now = datetime.now(TZ)
    q = (now.month - 1) // 3 + 1
    if q == 1:
        return now.year - 1, 4
    return now.year, q - 1

def search_index(query, errors):
    # This index is NOT an exchange feed or a proof of completeness.
    endpoint = "https://www.bing.com/search?format=rss&q=" + quote(query)
    try:
        response = requests.get(endpoint, headers=UA, timeout=18)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            if recognized(link):
                yield {"url": link, "title": title, "index": "Bing RSS"}
    except (requests.RequestException, ET.ParseError) as exc:
        errors.append({"source": "Bing RSS", "query": query, "error": str(exc)[:200]})

def links_from_page(url, errors):
    if not recognized(url):
        return []
    try:
        r = requests.get(url, headers=UA, timeout=18)
        r.raise_for_status()
        if not recognized(r.url) or "text/html" not in r.headers.get("Content-Type", "").lower():
            return []
        html = BeautifulSoup(r.text[:1_500_000], "html.parser")
        found = []
        for a in html.select("a[href]"):
            link = urljoin(r.url, a.get("href", ""))
            if recognized(link) and PDF_RE.search(urlparse(link).path):
                found.append({"url": link, "title": a.get_text(" ", strip=True)[:150], "index": url})
        return found[:25]
    except requests.RequestException as exc:
        errors.append({"source": url, "error": str(exc)[:200]})
        return []

def infer_ticker(title, url):
    # Only exact token in a filing filename or publication title.
    name = urlparse(url).path.rsplit("/", 1)[-1].replace("%20", " ")
    tokens = TICKER_RE.findall(name.upper())
    if not tokens:
        tokens = TICKER_RE.findall(title.upper())
    blacklist = {"PDF", "BCT", "HNX", "HSX", "SSC", "UPM", "QUY", "BAO", "CAO", "TAI", "NAM", "QIII"}
    return next((token for token in tokens if token not in blacklist), "")

def guess_exchange(url):
    h = urlparse(url).hostname.lower()
    if h.endswith("hsx.vn"):
        return "HOSE"
    if "upcom" in h:
        return "UPCoM"
    if h.endswith("hnx.vn"):
        return "HNX/UPCoM (unverified)"
    return "unknown"

def main():
    year, q = period()
    year_s = str(year)
    terms = [
        f'site:staticfile.hsx.vn/Uploads/UploadDocuments/ "báo cáo tài chính" "quý {q}" "{year}" pdf',
        f'site:hnx.vn/vi-vn/ "báo cáo tài chính quý {q}/{year}"',
        f'site:upcom.hnx.vn/ "báo cáo tài chính quý {q}/{year}"',
        f'site:owa.hnx.vn/ftp/cims/ "BCTC" "{year}"',
    ]
    errors, discovered, pages = [], {}, []
    # Load explicit official-source seeds; availability is validated by the PDF downloader.
    seed_path = ROOT / "config" / "official_seed_reports.csv"
    seeds = []
    if seed_path.exists():
        with seed_path.open(encoding="utf-8-sig", newline="") as sf:
            for row in csv.DictReader(sf):
                u = (row.get("report_url") or "").strip()
                if recognized(u) and PDF_RE.search(urlparse(u).path):
                    seeds.append(row)
                else:
                    errors.append({"source": "official_seed_reports.csv", "error": "invalid official HTTPS PDF URL", "ticker": row.get("ticker")})
    for term in terms:
        for candidate in search_index(term, errors):
            url = candidate["url"]
            if PDF_RE.search(urlparse(url).path):
                discovered[url] = candidate
            else:
                pages.append(candidate)
    for item in pages[:30]:
        for candidate in links_from_page(item["url"], errors):
            discovered[candidate["url"]] = candidate

    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    columns = ["ticker", "exchange", "period", "scope", "published_at", "report_url", "source_url"]
    with CONFIG.open(encoding="utf-8-sig", newline="") as fh:
        existing = list(csv.DictReader(fh))
    known = {row["report_url"].strip() for row in existing}
    added = []
    manual = []
    for url, item in sorted(discovered.items()):
        ticker = infer_ticker(item["title"], url)
        exchange = guess_exchange(url)
        # HNX serves both HNX and UPCoM: never guess the listing market.
        if not ticker or exchange in ("HNX/UPCoM (unverified)", "unknown"):
            manual.append({**item, "reason": "ticker or exchange requires verification"})
            continue
        if url not in known:
            row = dict(ticker=ticker, exchange=exchange, period=f"FY{year}-Q{q}",
                       scope="unverified", published_at="", report_url=url,
                       source_url=item["index"] if recognized(item["index"]) else url)
            existing.append(row)
            added.append(row)
            known.add(url)
    for row in seeds:
        url = row["report_url"].strip()
        if url not in known:
            existing.append({k: row.get(k, "") for k in columns})
            added.append(row)
            known.add(url)
    with CONFIG.open("w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=columns)
        wr.writeheader()
        wr.writerows(existing)

    QUEUE.write_text(json.dumps({"pages": pages, "manual_review": manual},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    log = {"time": datetime.now(TZ).isoformat(), "target": f"Q{q}/{year}",
           "method": "public search index hints; not comprehensive official disclosure API",
           "pages_found": len(pages), "pdf_links_found": len(discovered),
           "new_pdfs_queued": len(added), "seed_candidates": len(seeds), "manual_review": len(manual),
           "errors": errors, "coverage": "PARTIAL; seeded URLs plus public search hints; source URLs may be inaccessible"}
    OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False))

if __name__ == "__main__":
    main()
