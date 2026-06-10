from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


# computrabajo returns 403 "Host not in allowlist" for headless=True (Cloudflare IP allowlist).
# headless_override=False is mandatory for this portal.
CONFIG = SourceConfig(
    portal="computrabajo",
    base_url="https://co.computrabajo.com",
    search_url_template="https://co.computrabajo.com/trabajo-de-{query}",
    card_selectors=("article a[href*='ofertas-de-trabajo']", "a[href*='ofertas-de-trabajo']"),
    headless_override=False,
    max_runtime_seconds=300,
    max_detail_attempts=50,
    max_pages=5,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)

