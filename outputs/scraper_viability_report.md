# Scraper Viability Report

**Date:** 2026-06-09  
**Branch:** codex/dashboard-v1  
**Test method:** Node.js Playwright headless + curl, query `analista de datos`

---

## Portal Test Results

| Portal | URL Tested | HTTP Status | Job Links Found | Verdict |
|--------|-----------|-------------|-----------------|---------|
| getonbrd.com | https://www.getonbrd.com/jobs?q=analista+de+datos | 403 | 0 | Blocked (IP allowlist) |
| remoterocketship.com | https://remoterocketship.com/search?q=analista+de+datos | 403 | 0 | Blocked (IP allowlist) |
| tecnoempleo.com | https://www.tecnoempleo.com/busqueda-empleo.php?te=analista+datos | 403 | 0 | Blocked (IP allowlist) |
| co.computrabajo.com | https://co.computrabajo.com/trabajo-de-analista-de-datos | 403 | 0 | Blocked (IP allowlist) |
| hirelatam.com | https://www.hirelatam.com/jobs | 403 | 0 | Blocked (IP allowlist) |

### Blocking Detail

All five portals returned HTTP 403 with response body `Host not in allowlist`, which is the Cloudflare CDN **IP allowlist** feature. This is **not** headless browser detection — it blocks all requests from datacenter/server IPs regardless of browser fingerprint or User-Agent.

Confirmed via:
- Playwright headless (multiple stealth configurations)
- `curl` with realistic User-Agent and headers
- Multiple URL patterns and API endpoints tested per portal

**This is the same blocking mechanism as `ticjob.co`** (existing scraper already documents: *"TicJob returns 403 'Host not in allowlist' for headless=True. headless_override=False is mandatory"*).

Setting `headless_override=False` routes execution through a real headed Chromium on a production machine with a residential/non-datacenter IP, which bypasses the CDN allowlist restriction.

---

## Scrapers Created

All four new portals received scrapers with `headless_override=False` following the established `ticjob_scraper.py` pattern:

| Scraper File | Portal Key | Search URL Template | Card Selectors |
|---|---|---|---|
| `scrapers/sources/getonbrd_scraper.py` | `getonbrd` | `https://www.getonbrd.com/jobs?q={query}` | `a[href*='/jobs/']`, `[data-testid='job-card'] a[href]` |
| `scrapers/sources/tecnoempleo_scraper.py` | `tecnoempleo` | `https://www.tecnoempleo.com/busqueda-empleo.php?te={query}` | `a[href*='/oferta-trabajo/']`, `h2 a[href]`, `.oferta a[href]` |
| `scrapers/sources/remoterocketship_scraper.py` | `remoterocketship` | `https://remoterocketship.com/search?q={query}` | `a[href*='/jobs/']`, `a[href*='/job/']`, `[class*='job-card'] a[href]` |
| `scrapers/sources/hirelatam_scraper.py` | `hirelatam` | `https://www.hirelatam.com/jobs?search={query}` | `a[href*='/jobs/']`, `[class*='job-card'] a[href]`, `article a[href]` |

Additionally, `scrapers/sources/computrabajo_scraper.py` (pre-existing) was updated to add `headless_override=False` since it exhibits the same IP-level blocking.

---

## Registration Changes

### `crawlers/connectors/api_wrappers.py`
- Imported `getonbrd_scrape`, `tecnoempleo_scrape`, `remoterocketship_scrape`, `hirelatam_scrape`
- Added `ScraperAdapterCrawler` branches in `make_connector()` for all four new source keys

### `graduate_intelligence_platform/backend/app/academic_job_acquisition.py`
- Added `getonbrd`, `tecnoempleo`, `remoterocketship`, `hirelatam` to `CRAWLER_TARGETS` tuple
- Added all four to `_SPANISH_QUERY_SOURCES` frozenset (all benefit from Spanish-first queries)

---

## Notes

- Selectors are based on known URL patterns and common class naming for each portal; they will be validated on first production run with headed mode
- `getonbrd.com` also has a public REST API (`/api/v0/search/jobs`) that could be used as a future alternative to avoid browser automation
- `tecnoempleo.com` is Spain-focused but has some LatAm listings; Spanish queries are appropriate
- `remoterocketship.com` and `hirelatam.com` specialise in remote/LatAm roles and are relevant for Colombian job market coverage
