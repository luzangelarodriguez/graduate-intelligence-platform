from __future__ import annotations

from scrapers.sources.base import PlaywrightJobSource, SourceConfig, run_async_scraper


CONFIG = SourceConfig(
    portal="servicio_publico_empleo",
    base_url="https://www.serviciodeempleo.gov.co",
    search_url_template="https://www.serviciodeempleo.gov.co/busqueda-empleo?search={query}&location={location}",
    card_selectors=(
        "a[href*='detalle-vacante']",
        "a[href*='detalleVacante']",
        "a[href*='/vacantes/']",
        "a[href*='busqueda-empleo'][href*='id']",
    ),
)


def scrape_jobs(query: str, location: str = "Colombia", limit: int = 50, headless: bool = True):
    return run_async_scraper(PlaywrightJobSource(CONFIG), query=query, location=location, limit=limit, headless=headless)
