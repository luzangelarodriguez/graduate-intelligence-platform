from __future__ import annotations

from scrapers.lakehouse.magneto_api_extractor import extract


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    pages = max(1, limit // 20)
    result = extract(query, pages=pages, page_size=min(50, max(10, limit)), dry_run=False)
    return result

