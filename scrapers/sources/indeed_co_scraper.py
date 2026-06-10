from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="indeed_co",
    base_url="https://co.indeed.com",
    search_url_template="https://co.indeed.com/jobs?q={query}&l=Colombia",
    card_selectors=(
        "a[href*='/rc/clk']",
        "a[href*='/pagead/clk']",
        "a[data-jk]",
        "[class*='jobTitle'] a[href]",
        "h2 a[href]",
    ),
    title_selectors=(
        "h1[class*='jobsearch-JobInfoHeader-title']",
        "h1[class*='title']",
        "[data-testid='jobsearch-JobInfoHeader-title']",
        "h1",
    ),
    company_selectors=(
        "[data-testid='inlineHeader-companyName']",
        "[class*='companyName']",
        "[class*='company']",
    ),
    city_selectors=(
        "[data-testid='job-location']",
        "[class*='companyLocation']",
        "[class*='location']",
    ),
    headless_override=False,
    max_runtime_seconds=300,
    max_detail_attempts=50,
    max_pages=5,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
