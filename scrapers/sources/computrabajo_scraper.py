from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="computrabajo",
    base_url="https://co.computrabajo.com",
    search_url_template="https://co.computrabajo.com/trabajo-de-{query}",
    card_selectors=("article a[href*='ofertas-de-trabajo']", "a[href*='ofertas-de-trabajo']"),
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)

