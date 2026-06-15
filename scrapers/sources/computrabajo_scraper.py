"""
Computrabajo Colombia scraper (requests + BeautifulSoup).

The previous Playwright implementation hit 403s even with headless=False
because Cloudflare blocks datacenter IPs. This version uses requests with
a real browser User-Agent and session cookies, which succeeds from most IPs.
"""
from __future__ import annotations

import logging
import re
import time
import urllib.parse
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE   = "https://co.computrabajo.com"
_SEARCH = "https://co.computrabajo.com/trabajo-de-{slug}"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://co.computrabajo.com/",
    "DNT": "1",
}

_MAX_PAGES       = 4
_SESSION_TIMEOUT = 15
_PAGE_DELAY      = 0.8


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _query_to_slug(query: str) -> str:
    """Convert 'psicólogo educativo' → 'psicologo-educativo'."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", query)
    ascii_q = nfkd.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_q.lower()).strip("-")


def _classify(title: str, description: str) -> tuple[str, list[str]]:
    try:
        from scrapers.normalization.classify_domains import classify_text_domain
        from scrapers.normalization.normalize_skills import extract_skills
    except ModuleNotFoundError:
        from normalization.classify_domains import classify_text_domain
        from normalization.normalize_skills import extract_skills
    domain = classify_text_domain(f"{title} {description}").primary_domain
    skills = extract_skills(description or title, domain_hint=domain)
    return domain, skills


def _normalize_role(title: str) -> str:
    try:
        from scrapers.normalization.normalize_roles import normalize_role
    except ModuleNotFoundError:
        from normalization.normalize_roles import normalize_role
    return normalize_role(title)


def _fetch_detail(session: requests.Session, url: str) -> str:
    """Fetch job detail page and return description text."""
    try:
        resp = session.get(url, timeout=_SESSION_TIMEOUT)
        if resp.status_code != 200:
            return ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for sel in (
            "[class*='offer-description']",
            "[class*='job-description']",
            "[id*='offer-description']",
            "section.box_content",
        ):
            el = soup.select_one(sel)
            if el:
                return _clean(el.get_text(" "))
    except Exception:
        pass
    return ""


def scrape_jobs(
    query: str,
    location: str = "Colombia",
    limit: int = 50,
    headless: bool = True,
) -> list[dict[str, Any]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("computrabajo scraper needs beautifulsoup4: pip install beautifulsoup4")
        return []

    session = requests.Session()
    session.headers.update(_HEADERS)

    # Prime session cookie with homepage
    try:
        session.get(_BASE, timeout=_SESSION_TIMEOUT)
        time.sleep(0.4)
    except Exception:
        pass

    slug = _query_to_slug(query)
    jobs: list[dict[str, Any]] = []
    page = 1

    while len(jobs) < limit and page <= _MAX_PAGES:
        url = _SEARCH.format(slug=slug)
        if page > 1:
            url += f"?p={page}"

        logger.info("Computrabajo: GET %s", url)
        try:
            resp = session.get(url, timeout=_SESSION_TIMEOUT)
        except Exception as exc:
            logger.warning("Computrabajo request error: %s", exc)
            break

        if resp.status_code == 403:
            logger.warning("Computrabajo 403 — Cloudflare block on page %d", page)
            break
        if resp.status_code != 200:
            logger.warning("Computrabajo status %s on page %d", resp.status_code, page)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Job cards
        cards = (
            soup.select("article.box_offer")
            or soup.select("[class*='box_offer']")
            or soup.select("article[data-id]")
            or soup.select("a[href*='ofertas-de-trabajo']")
        )
        logger.info("Computrabajo page %d: %d cards", page, len(cards))
        if not cards:
            break

        detail_attempts = 0
        for card in cards:
            if len(jobs) >= limit:
                break
            try:
                # Title
                title_el = card.select_one("h2 a, h3 a, [class*='title'] a, a[title]")
                title    = _clean(title_el.get_text() if title_el else
                                  card.get("title") or "")
                # Company
                comp_el  = card.select_one("[class*='company'], [class*='empresa'], [itemprop='hiringOrganization']")
                company  = _clean(comp_el.get_text() if comp_el else "")
                # Location
                loc_el   = card.select_one("[class*='location'], [class*='ciudad'], [itemprop='jobLocation']")
                location_text = _clean(loc_el.get_text() if loc_el else "Colombia")
                # Link
                link_el  = title_el or card.select_one("a[href]")
                href     = link_el["href"] if link_el and link_el.get("href") else ""
                full_url = (_BASE + href) if href.startswith("/") else href

                if not title:
                    continue

                # Fetch description (limited attempts to stay within runtime)
                description = ""
                if full_url and detail_attempts < 15:
                    description = _fetch_detail(session, full_url)
                    detail_attempts += 1
                    time.sleep(0.3)

                domain, skills = _classify(title, description)

                jobs.append({
                    "portal":             "computrabajo",
                    "titulo":             title,
                    "titulo_normalizado": _normalize_role(title),
                    "empresa":            company,
                    "ciudad":             location_text,
                    "modalidad":          "",
                    "salario":            "",
                    "descripcion":        description,
                    "seniority":          "",
                    "sector":             "",
                    "dominio":            domain,
                    "fecha_publicacion":  None,
                    "url":                full_url,
                    "skills_empleo":      skills,
                })
            except Exception as exc:
                logger.debug("Computrabajo card error: %s", exc)
                continue

        page += 1
        time.sleep(_PAGE_DELAY)

    logger.info("Computrabajo: returning %d jobs for query '%s'", len(jobs), query)
    return jobs
