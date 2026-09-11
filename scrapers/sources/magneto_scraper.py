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
    # Magneto renders the job title as plain text (NOT a heading element).
    # The fraud-warning banner IS an h1/h2, so any h1-based selector reliably
    # captures the banner instead of the title. Strategy:
    #
    # 1. aria-current="page" — the breadcrumb item for the current page is always
    #    the job title (e.g. "/ empleos / Diseñador(a) Creativa"). This ARIA
    #    attribute is standard and CSS-class-independent, making it resilient to
    #    CSS-in-JS hashed class names. Appears high in the DOM, before the banner.
    # 2. Breadcrumb container fallbacks — for breadcrumb implementations that
    #    don't set aria-current but use class-based active states.
    # 3. h1 last resort — kept for safety but the fraud guard in base.py
    #    first_text() will skip it if it returns the banner prefix.
    title_selectors=(
        "[aria-current='page']",
        "[aria-current]",
        "nav [class*='active']",
        "nav li:last-child span",
        "nav li:last-child",
        "[class*='breadcrumb'] *:last-child",
        "[class*='breadcrumb'] li:last-child",
        "[data-testid*='breadcrumb'] *:last-child",
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

