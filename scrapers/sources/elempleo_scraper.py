from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="elempleo",
    base_url="https://www.elempleo.com",
    search_url_template="https://www.elempleo.com/co/ofertas-empleo/?trabajo={query}",
    card_selectors=("a[href*='/co/ofertas-trabajo/']", "article a[href]"),
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)

