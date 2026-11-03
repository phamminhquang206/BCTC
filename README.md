# Vietnam Financial Growth Agent — GitHub Actions MVP

A conservative cloud-ready foundation. **Not** a complete automatic HOSE/HNX/UPCoM crawler or ChatGPT MCP server yet.

## New discovery step (experimental)
- Each run first searches public indexed references to official HOSE/HNX/UPCoM domains for the latest completed calendar quarter. This is **best-effort search-index discovery**, not an official market-wide disclosure feed.
- Candidates from clearly identifiable HOSE official PDF URLs can be appended to `config/reports.csv`, marked `scope=unverified`. Ambiguous HNX/UPCoM references go to `data/discovered_pages.json` for manual verification rather than being misclassified.
- Review `data/discovery_log.json` for search/API failures and coverage limitations. Found PDFs are extracted to candidate snippets but are **not promoted to verified revenue or LNST** automatically. This means the qualified-company PDF can remain empty even when PDFs were downloaded.
- Search engines may block automated requests or index too few reports; if that happens, the log records the gap. Full automation needs tested official publication source adapters and numerical validation.

## What works
- GitHub Actions scheduled 05:00 UTC = 12:00 Vietnam every day (GitHub can delay/drop scheduled jobs).
- Processes public **HTTPS PDF** URLs listed in `config/reports.csv` (ticker, exchange, period, scope, published_at, report_url, source_url).
- Keeps SHA256 and candidate text snippets for manual validation; never mislabels unverified extracted rows as financial facts.
- Persistent checkpoint in `data/state.json` committed back to repository; run logs; Unicode Vietnamese PDF.
- Deterministic validation and QoQ growth filtering when independently verified observations have been added.
- Artifacts uploaded per run; files also checked into repo for simpler retrieval.

## What does NOT work yet
- No comprehensive whole-market discovery from HOSE/HNX/UPCoM; initial search-index discovery is incomplete and official source listing adapters must be developed and tested for each site's access policies.
- No unattended reliable table/column extraction and validation across all BCTC formats. Candidate text requires human validation.
- No MCP endpoint connected to ChatGPT; needs securely hosted API service and plugin MCP configuration.
- No persistent external cloud database. For low-volume MVP, state is stored by Git commits; at scale use D1/Postgres.
- Not an investment recommendation.

## Quick start
1. Create a **private GitHub repository**, upload all files preserving `.github/workflows/daily.yml`.
2. In Repository Settings → Actions → General, enable workflow `Read and write permissions` if repository policy blocks workflow writes. The workflow already requests `contents: write`.
3. Set `config/reports.csv` to **real report PDF URLs from official disclosure pages**, respecting website terms and access rules. Current file intentionally empty.
4. Open Actions → Daily Vietnamese Financial Growth Scan → Run workflow for first test.
5. Inspect the `reports/` PDF and `data/scan_log.json`. Configure and validate real official source adapters before describing coverage as market-wide.
6. To use verified observations, populate `data/state.json` `verified_observations` only from verified numbers with source and compatible scope; review data provenance manually in this MVP.

## Future cloud architecture
- Official disclosure adapter per exchange + issuer IR → stable announcement queue with cursors and rate limits.
- PDF/XLS financial parser + independent numerical cross-check → quarterly observation store → deterministic growth engine.
- D1/Postgres and secure MCP endpoint for ChatGPT `scan_new_reports`, `get_scan_progress`, `filter_growth_companies`, `generate_pdf_report`.
- PDF snapshots and notification only on new verified opportunities.

GitHub's scheduled start is best effort, and an inactive repository can have scheduled workflows disabled. Test quotas/permissions and keep repository private while state contains nonpublic metadata.
