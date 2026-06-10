from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


# remoterocketship.com returns 403 "Host not in allowlist" for headless=True (Cloudflare IP allowlist).
# headless_override=False is mandatory for this portal.
CONFIG = SourceConfig(
    portal="remoterocketship",
    base_url="https://remoterocketship.com",
    search_url_template="https://remoterocketship.com/search?q={query}",
    card_selectors=(
        "a[href*='/jobs/']",
        "a[href*='/job/']",
        "[class*='job-card'] a[href]",
        "[class*='listing'] a[href]",
    ),
    title_selectors=(
        "h1[class*='title']",
        "h1[class*='job']",
        "[class*='job-title']",
        "h1",
    ),
    company_selectors=(
        "[class*='company']",
        "[class*='employer']",
        "a[href*='/company/']",
    ),
    city_selectors=(
        "[class*='location']",
        "[class*='remote']",
        "[class*='region']",
    ),
    headless_override=False,
    max_runtime_seconds=300,
    max_detail_attempts=50,
    max_pages=5,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
