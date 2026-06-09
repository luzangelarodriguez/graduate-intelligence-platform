from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


# tecnoempleo.com returns 403 "Host not in allowlist" for headless=True (Cloudflare IP allowlist).
# headless_override=False is mandatory for this portal.
CONFIG = SourceConfig(
    portal="tecnoempleo",
    base_url="https://www.tecnoempleo.com",
    search_url_template="https://www.tecnoempleo.com/busqueda-empleo.php?te={query}",
    card_selectors=(
        "a[href*='/oferta-trabajo/']",
        "a[href*='tecnoempleo.com/oferta-trabajo']",
        "h2 a[href]",
        ".oferta a[href]",
    ),
    title_selectors=(
        "h1.title",
        "h1[class*='job']",
        "h1[class*='oferta']",
        "h1",
    ),
    company_selectors=(
        "[class*='company']",
        "[class*='empresa']",
        "a[href*='/empresa/']",
        "[class*='recruiter']",
    ),
    city_selectors=(
        "[class*='location']",
        "[class*='ciudad']",
        "[class*='ubicacion']",
        "[class*='localidad']",
    ),
    headless_override=False,
    max_runtime_seconds=300,
    max_detail_attempts=50,
    max_pages=5,
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
