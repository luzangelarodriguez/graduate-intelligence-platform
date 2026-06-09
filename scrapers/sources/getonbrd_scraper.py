from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="getonbrd",
    base_url="https://www.getonbrd.com",
    search_url_template="https://www.getonbrd.com/jobs?tag={query}",
    card_selectors=(
        "a[href*='/jobs/']",
        "a[href*='/empleos/']",
        "article a[href]",
    ),
    headless_override=False,
    max_runtime_seconds=300,
    max_detail_attempts=50,
    max_pages=5,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
