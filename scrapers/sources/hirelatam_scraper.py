from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


# hirelatam.com returns 403 "Host not in allowlist" for headless=True (Cloudflare IP allowlist).
# headless_override=False is mandatory for this portal.
CONFIG = SourceConfig(
    portal="hirelatam",
    base_url="https://www.hirelatam.com",
    search_url_template="https://www.hirelatam.com/jobs?search={query}",
    card_selectors=(
        "a[href*='/jobs/']",
        "[class*='job-card'] a[href]",
        "[class*='position'] a[href]",
        "article a[href]",
    ),
    title_selectors=(
        "h1[class*='title']",
        "h1[class*='job']",
        "h1[class*='position']",
        "h1",
    ),
    company_selectors=(
        "[class*='company']",
        "[class*='employer']",
        "[class*='client']",
    ),
    city_selectors=(
        "[class*='location']",
        "[class*='remote']",
        "[class*='country']",
        "[class*='region']",
    ),
    headless_override=False,
    max_runtime_seconds=300,
    max_detail_attempts=50,
    max_pages=5,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
