from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="torre",
    base_url="https://torre.ai",
    search_url_template="https://torre.ai/search/jobs?q={query}&location={location}",
    card_selectors=("a[href*='/jobs/']", "a[href*='/opportunities/']", "article a[href]"),
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)

