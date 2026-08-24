from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="magneto",
    base_url="https://www.magneto365.com",
    search_url_template="https://www.magneto365.com/co/empleos?search={query}",
    # Job cards link to /co/empleos/{slug} — exclude bare /empleos/ to avoid nav links
    card_selectors=(
        "article a[href*='/co/empleos/']",
        "[class*='card'] a[href*='/co/empleos/']",
        "[class*='job'] a[href*='/co/empleos/']",
        "[class*='vacancy'] a[href*='/co/empleos/']",
        "a[href*='/co/empleos/']",
    ),
    # Prioritize specific job-title selectors before the generic h1 to avoid
    # capturing "¡Ten cuidado con el fraude!" fraud-warning banners
    title_selectors=(
        "h1[class*='title']",
        "h1[class*='job']",
        "h1[class*='cargo']",
        "[data-testid*='title']",
        "[data-testid*='job']",
        ".job-title",
        ".cargo",
        "h1",
    ),
    company_selectors=(
        "[data-testid*='company']",
        "[class*='company']",
        "[class*='empresa']",
        "[class*='employer']",
    ),
    city_selectors=(
        "[data-testid*='location']",
        "[data-testid*='city']",
        "[class*='location']",
        "[class*='city']",
        "[class*='ciudad']",
        "[class*='ubicacion']",
    ),
    # Magneto detail pages are React-rendered. Try Magneto-specific containers
    # before falling back to generic selectors.
    description_selectors=(
        "[class*='VacancyDetail']",
        "[class*='vacancy-detail']",
        "[class*='job-detail']",
        "[data-testid*='description']",
        "[data-testid*='detail']",
        "[class*='description']",
        "[class*='descripcion']",
        "main",
        "article",
    ),
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)

