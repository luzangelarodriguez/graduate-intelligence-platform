from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


# TicJob returns 403 "Host not in allowlist" for headless=True.
# headless_override=False is mandatory for this portal.
CONFIG = SourceConfig(
    portal="ticjob",
    base_url="https://ticjob.co",
    search_url_template="https://ticjob.co/es/search?q={query}",
    card_selectors=(
        "a[href*='/LCL/']",
        "a[href*='ticjob.co/LCL']",
        "body",
    ),
    title_selectors=(
        "h1[class*='title']",
        "h1[class*='job']",
        "h1[class*='position']",
        "[data-testid*='title']",
        "h1",
    ),
    company_selectors=(
        "[class*='company']",
        "[class*='empresa']",
        "[class*='employer']",
        "[data-testid*='company']",
    ),
    city_selectors=(
        "[class*='location']",
        "[class*='city']",
        "[class*='ciudad']",
        "[data-testid*='location']",
    ),
    headless_override=False,
    cookie_accept_selector="button:has-text('Aceptar y Continuar')",
    reuse_page_for_details=True,
    max_runtime_seconds=300,
    max_detail_attempts=50,
    max_pages=5,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
