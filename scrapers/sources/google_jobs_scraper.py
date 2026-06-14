"""
Google Jobs Colombia scraper (Playwright).

Uses the Google Jobs widget (ibp=htl;jobs) which aggregates listings from
Elempleo, Magneto, Computrabajo, etc. Returns jobs in the project standard
format without needing to visit each source portal directly.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import urllib.parse
from typing import Any

logger = logging.getLogger(__name__)

_SEARCH_URL = (
    "https://www.google.com/search"
    "?q={query}+empleos+Colombia"
    "&ibp=htl;jobs"
    "&hl=es-CO"
    "&gl=co"
)

# Selectors for the Google Jobs panel cards
_CARD_SELECTORS = [
    "[jsname='MQHble']",          # job card container (desktop)
    "li[class*='iFjolb']",        # job card list item
    "[data-ved] [role='listitem']",
    "[class*='pE8vnd']",          # card inner
]

_TITLE_SELECTORS = [
    "[class*='BjJfJf']",
    "h2[class*='title']",
    "[data-title]",
    "h2",
    "h3",
]

_COMPANY_SELECTORS = [
    "[class*='vNEEBe']",
    "[class*='company']",
    "[class*='empresa']",
]

_LOCATION_SELECTORS = [
    "[class*='Qk80Jf']",
    "[class*='location']",
    "[class*='ciudad']",
]

_VIA_SELECTORS = [
    "[class*='Via']",
    "[class*='via']",
]

_DETAIL_PANEL_SELECTORS = [
    "[class*='KLsYvd']",
    "[class*='HBvzbc']",
    "div[data-share-url]",
]

_MAX_CARDS = 30
_MAX_RUNTIME = 90  # seconds


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


async def _scrape(query: str, limit: int, headless: bool) -> list[dict[str, Any]]:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    from scrapers.domain_classifier import classify_text_domain
    from scrapers.skill_extractor import extract_skills
    from scrapers.sources.base import normalize_role

    encoded = urllib.parse.quote_plus(query)
    url = _SEARCH_URL.format(query=encoded)

    jobs: list[dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True if os.getenv("CI") == "true" else headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            locale="es-CO",
            extra_http_headers={"Accept-Language": "es-CO,es;q=0.9"},
        )
        page = await context.new_page()
        try:
            logger.info("Google Jobs: navigating to %s", url)
            await page.goto(url, timeout=30_000, wait_until="domcontentloaded")

            # Accept cookies if prompted
            for btn_text in ("Aceptar todo", "Accept all", "Aceptar"):
                try:
                    btn = page.get_by_role("button", name=re.compile(btn_text, re.I))
                    if await btn.count() > 0:
                        await btn.first.click(timeout=3_000)
                        await page.wait_for_timeout(1_000)
                        break
                except Exception:
                    pass

            # Wait for job cards
            cards_loaded = False
            for sel in _CARD_SELECTORS:
                try:
                    await page.wait_for_selector(sel, timeout=10_000)
                    cards_loaded = True
                    break
                except PWTimeout:
                    continue

            if not cards_loaded:
                logger.warning("Google Jobs: no job cards found for query '%s'", query)
                return []

            # Collect cards
            for sel in _CARD_SELECTORS:
                cards = await page.query_selector_all(sel)
                if cards:
                    break

            logger.info("Google Jobs: found %d cards", len(cards))

            for card in cards[: min(limit, _MAX_CARDS)]:
                try:
                    # Extract title
                    title = ""
                    for ts in _TITLE_SELECTORS:
                        el = await card.query_selector(ts)
                        if el:
                            title = _clean(await el.inner_text())
                            if title:
                                break

                    # Extract company
                    company = ""
                    for cs in _COMPANY_SELECTORS:
                        el = await card.query_selector(cs)
                        if el:
                            company = _clean(await el.inner_text())
                            if company:
                                break

                    # Extract location
                    location = ""
                    for ls in _LOCATION_SELECTORS:
                        el = await card.query_selector(ls)
                        if el:
                            location = _clean(await el.inner_text())
                            if location:
                                break

                    # Extract source portal (via)
                    via = "google_jobs"
                    for vs in _VIA_SELECTORS:
                        el = await card.query_selector(vs)
                        if el:
                            via_text = _clean(await el.inner_text())
                            if via_text:
                                via = via_text.replace("Via ", "").replace("via ", "").strip()
                                break

                    if not title:
                        continue

                    # Click card to load description in detail panel
                    description = ""
                    try:
                        await card.click(timeout=5_000)
                        await page.wait_for_timeout(1_500)
                        for dp in _DETAIL_PANEL_SELECTORS:
                            panel = await page.query_selector(dp)
                            if panel:
                                description = _clean(await panel.inner_text())
                                if len(description) > 50:
                                    break
                    except Exception:
                        pass

                    # Classify and extract skills
                    domain = classify_text_domain(f"{title} {description}").primary_domain
                    skills = extract_skills(description or title, domain_hint=domain)

                    jobs.append({
                        "portal": f"google_jobs:{via}",
                        "titulo": title,
                        "titulo_normalizado": normalize_role(title),
                        "empresa": company,
                        "ciudad": location or "Colombia",
                        "modalidad": "",
                        "salario": "",
                        "descripcion": description,
                        "seniority": "",
                        "sector": "",
                        "dominio": domain,
                        "fecha_publicacion": None,
                        "url": page.url,
                        "skills_empleo": skills,
                        "fuente_via": via,
                    })
                    logger.debug("Google Jobs: extracted '%s' @ %s", title, company)

                except Exception as exc:
                    logger.debug("Google Jobs: card error: %s", exc)
                    continue

        except Exception as exc:
            logger.error("Google Jobs scraper error: %s", exc)
        finally:
            await browser.close()

    logger.info("Google Jobs: returning %d jobs for query '%s'", len(jobs), query)
    return jobs


def scrape_jobs(
    query: str,
    location: str = "Colombia",
    limit: int = 50,
    headless: bool = True,
) -> list[dict[str, Any]]:
    return asyncio.run(_scrape(query=query, limit=limit, headless=headless))
