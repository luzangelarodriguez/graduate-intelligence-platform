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
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# hl=es-419 (Latin American Spanish) works better than es-CO for the jobs panel
_SEARCH_URL = (
    "https://www.google.com/search"
    "?q={query}+empleos+Colombia"
    "&ibp=htl;jobs"
    "&hl=es-419"
    "&gl=co"
)

# Google Jobs panel card selectors (in priority order)
_CARD_SELECTORS = [
    ".iFjolb",                        # primary card class (desktop)
    "li.iFjolb",
    "[jsname='MQHble']",
    "g-card",
    "[data-ved] li",
    "[class*='pE8vnd']",
]

# Selectors within each card
_TITLE_SEL  = "[class*='BjJfJf'], [class*='sH3zOn'], h3, h2"
_COMPANY_SEL = "[class*='vNEEBe'], [class*='company'], [class*='nJlQNd']"
_LOCATION_SEL = "[class*='Qk80Jf'], [class*='location'], [class*='fcfa4b']"
_VIA_SEL     = "[class*='Via'], [class*='via'], [class*='nJlQNd'] + span"

# Detail panel selectors (shown when a card is clicked)
_DETAIL_SEL = [
    "[class*='KLsYvd']",
    "[class*='HBvzbc']",
    "div[data-share-url]",
    "[class*='YgLbBe']",
]

_MAX_CARDS   = 30
_SCREENSHOT_DIR = Path("logs/screenshots/google_jobs")


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


async def _scrape(query: str, limit: int, headless: bool, verbose: bool = False) -> list[dict[str, Any]]:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    try:
        from scrapers.normalization.classify_domains import classify_text_domain
        from scrapers.normalization.normalize_skills import extract_skills
        from scrapers.normalization.normalize_roles import normalize_role
    except ModuleNotFoundError:
        from normalization.classify_domains import classify_text_domain
        from normalization.normalize_skills import extract_skills
        from normalization.normalize_roles import normalize_role

    encoded = urllib.parse.quote_plus(query)
    url = _SEARCH_URL.format(query=encoded)
    jobs: list[dict[str, Any]] = []

    if verbose:
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True if os.getenv("CI") == "true" else headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            locale="es-419",
            viewport={"width": 1280, "height": 900},
            extra_http_headers={"Accept-Language": "es-419,es;q=0.9"},
        )
        page = await context.new_page()
        try:
            logger.info("Google Jobs: GET %s", url)
            await page.goto(url, timeout=30_000, wait_until="networkidle")

            # Accept cookies if prompted
            for btn_text in ("Aceptar todo", "Accept all", "Aceptar"):
                try:
                    btn = page.get_by_role("button", name=re.compile(btn_text, re.I))
                    if await btn.count() > 0:
                        await btn.first.click(timeout=3_000)
                        await page.wait_for_timeout(1_500)
                        break
                except Exception:
                    pass

            # Extra wait for jobs panel JS to render
            await page.wait_for_timeout(3_000)

            if verbose:
                title = await page.title()
                html  = await page.content()
                shot  = _SCREENSHOT_DIR / f"{re.sub(r'[^a-z0-9]', '_', query.lower())}.png"
                await page.screenshot(path=str(shot), full_page=False)
                print(f"\n[DEBUG] page title : {title}")
                print(f"[DEBUG] screenshot : {shot}")
                print(f"[DEBUG] html[:2000]:\n{html[:2000]}\n")

            # Find cards using each selector until one returns results
            cards: list[Any] = []
            matched_sel = None
            for sel in _CARD_SELECTORS:
                try:
                    await page.wait_for_selector(sel, timeout=5_000)
                    cards = await page.query_selector_all(sel)
                    if cards:
                        matched_sel = sel
                        break
                except PWTimeout:
                    if verbose:
                        print(f"[DEBUG] selector timeout: {sel}")
                    continue

            if not cards:
                logger.warning("Google Jobs: 0 cards for query '%s' — panel may not have loaded", query)
                if verbose:
                    # Print a bigger chunk of HTML to diagnose
                    html = await page.content()
                    print(f"[DEBUG] full html[:5000]:\n{html[:5000]}")
                return []

            logger.info("Google Jobs: %d cards via selector '%s'", len(cards), matched_sel)
            if verbose:
                print(f"[DEBUG] {len(cards)} cards found via: {matched_sel}")

            for i, card in enumerate(cards[: min(limit, _MAX_CARDS)]):
                try:
                    title    = _clean(await (await card.query_selector(_TITLE_SEL) or _NullEl()).inner_text() if await card.query_selector(_TITLE_SEL) else "")
                    company  = _clean(await (await card.query_selector(_COMPANY_SEL) or _NullEl()).inner_text() if await card.query_selector(_COMPANY_SEL) else "")
                    location = _clean(await (await card.query_selector(_LOCATION_SEL) or _NullEl()).inner_text() if await card.query_selector(_LOCATION_SEL) else "")
                    via_el   = await card.query_selector(_VIA_SEL)
                    via      = _clean(await via_el.inner_text()) if via_el else "google_jobs"
                    via      = re.sub(r"(?i)^via\s*", "", via).strip() or "google_jobs"

                    if verbose:
                        print(f"[DEBUG] card {i}: title={title!r} company={company!r} location={location!r}")

                    if not title:
                        continue

                    # Click card to load description panel
                    description = ""
                    try:
                        await card.click(timeout=4_000)
                        await page.wait_for_timeout(2_000)
                        for dp in _DETAIL_SEL:
                            panel = await page.query_selector(dp)
                            if panel:
                                description = _clean(await panel.inner_text())
                                if len(description) > 80:
                                    break
                    except Exception as e:
                        if verbose:
                            print(f"[DEBUG] click error card {i}: {e}")

                    domain = classify_text_domain(f"{title} {description}").primary_domain
                    skills = extract_skills(description or title, domain_hint=domain)

                    jobs.append({
                        "portal":             f"google_jobs:{via}",
                        "titulo":             title,
                        "titulo_normalizado": normalize_role(title),
                        "empresa":            company,
                        "ciudad":             location or "Colombia",
                        "modalidad":          "",
                        "salario":            "",
                        "descripcion":        description,
                        "seniority":          "",
                        "sector":             "",
                        "dominio":            domain,
                        "fecha_publicacion":  None,
                        "url":                page.url,
                        "skills_empleo":      skills,
                        "fuente_via":         via,
                    })
                    logger.info("Google Jobs [%d]: %s @ %s", i + 1, title, company)

                except Exception as exc:
                    logger.debug("Google Jobs: card %d error: %s", i, exc)
                    continue

        except Exception as exc:
            logger.error("Google Jobs scraper error: %s", exc, exc_info=True)
        finally:
            await browser.close()

    logger.info("Google Jobs: returning %d jobs for query '%s'", len(jobs), query)
    return jobs


class _NullEl:
    """Placeholder so we don't need repeated None checks."""
    async def inner_text(self) -> str:
        return ""


def scrape_jobs(
    query: str,
    location: str = "Colombia",
    limit: int = 50,
    headless: bool = True,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    return asyncio.run(_scrape(query=query, limit=limit, headless=headless, verbose=verbose))
