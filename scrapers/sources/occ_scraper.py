from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper

# OCC Mundial Colombia — https://www.occ.com.co
CONFIG = SourceConfig(
    portal="occ",
    base_url="https://www.occ.com.co",
    search_url_template="https://www.occ.com.co/empleos/q-{query}/",
    card_selectors=(
        "a[href*='/empleo/']",
        "article a[href]",
        "[class*='job-card'] a[href]",
        "[class*='JobCard'] a[href]",
        "[data-testid*='job'] a[href]",
    ),
    title_selectors=(
        "h1",
        "[class*='job-title']",
        "[class*='JobTitle']",
        "[class*='titulo']",
        "h2",
    ),
    company_selectors=(
        "[class*='company']",
        "[class*='empresa']",
        "[class*='Company']",
        "[data-testid*='company']",
    ),
    city_selectors=(
        "[class*='location']",
        "[class*='ciudad']",
        "[class*='Location']",
        "[class*='city']",
    ),
    description_selectors=(
        "[class*='description']",
        "[class*='Description']",
        "[class*='job-detail']",
        "[class*='JobDetail']",
        "main",
        "article",
    ),
    next_selectors=(
        "a[rel='next']",
        "button:has-text('Siguiente')",
        "a:has-text('Siguiente')",
        "[aria-label='Next page']",
        "[class*='pagination'] a:last-child",
    ),
    max_pages=4,
    max_runtime_seconds=300,
    max_detail_attempts=40,
    headless_override=False,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
