from __future__ import annotations

from scrapers.lakehouse.magneto_api_extractor import extract


def _normalize(jobs: list[dict]) -> list[dict]:
    return [
        {
            "title": job.get("titulo") or "",
            "company": job.get("empresa") or "",
            "location": job.get("ciudad") or "",
            "description": job.get("descripcion") or "",
            "url": job.get("url") or "",
        }
        for job in jobs
    ]


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    pages = max(1, limit // 20)
    try:
        result = extract(query, pages=pages, page_size=min(50, max(10, limit)), dry_run=False)
        jobs = result.get("jobs", [])
    except Exception:
        jobs = []

    if jobs:
        return _normalize(jobs)

    # API returned no jobs — fall back to Playwright-based scraper
    from scrapers.sources.magneto_scraper import scrape_jobs as _playwright_scrape
    return _playwright_scrape(query, location=location, limit=limit, headless=headless)
