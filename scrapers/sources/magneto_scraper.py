from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="magneto",
    base_url="https://www.magneto365.com",
    search_url_template="https://www.magneto365.com/co/empleos?search={query}",
    card_selectors=("a[href*='/co/empleos/']", "a[href*='/empleos/']"),
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)

