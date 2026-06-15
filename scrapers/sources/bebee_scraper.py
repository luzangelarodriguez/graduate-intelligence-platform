"""
BeBee Colombia scraper (requests + JSON API).

BeBee exposes a JSON search endpoint that doesn't require JS rendering.
Falls back to HTML scraping if the API returns no results.
"""
from __future__ import annotations

import logging
import re
import time
import urllib.parse
from typing import Any

import requests

logger = logging.getLogger(__name__)

_API_URL  = "https://co.bebee.com/api/jobs"
_HTML_URL = "https://co.bebee.com/jobs/search"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept": "application/json, text/html;q=0.9",
    "Referer": "https://co.bebee.com/",
}

_SESSION_TIMEOUT = 15  # seconds per request
_MAX_PAGES       = 3


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


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


def _api_scrape(query: str, limit: int, session: requests.Session) -> list[dict[str, Any]]:
    """Try BeBee JSON API first."""
    jobs: list[dict[str, Any]] = []
    page = 1
    while len(jobs) < limit and page <= _MAX_PAGES:
        try:
            resp = session.get(
                _API_URL,
                params={"q": query, "country": "CO", "lang": "es", "page": page},
                timeout=_SESSION_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.debug("BeBee API status %s page %d", resp.status_code, page)
                break
            data = resp.json()
            items = data.get("jobs") or data.get("data") or data.get("results") or []
            if not items:
                break
            for item in items:
                title       = _clean(item.get("title") or item.get("name"))
                company     = _clean(item.get("company") or item.get("employer"))
                location    = _clean(item.get("location") or item.get("city") or "Colombia")
                description = _clean(item.get("description") or item.get("body") or "")
                url         = item.get("url") or item.get("link") or ""
                if not title:
                    continue
                domain, skills = _classify(title, description)
                jobs.append({
                    "portal":             "bebee",
                    "titulo":             title,
                    "titulo_normalizado": _normalize_role(title),
                    "empresa":            company,
                    "ciudad":             location,
                    "modalidad":          "",
                    "salario":            "",
                    "descripcion":        description,
                    "seniority":          "",
                    "sector":             "",
                    "dominio":            domain,
                    "fecha_publicacion":  None,
                    "url":                url,
                    "skills_empleo":      skills,
                })
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            logger.debug("BeBee API error page %d: %s", page, exc)
            break
        page += 1
        time.sleep(0.5)
    return jobs


def _html_scrape(query: str, limit: int, session: requests.Session) -> list[dict[str, Any]]:
    """Fallback: parse BeBee search HTML with BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeBee HTML fallback needs beautifulsoup4: pip install beautifulsoup4")
        return []

    jobs: list[dict[str, Any]] = []
    encoded = urllib.parse.quote_plus(query)
    url = f"{_HTML_URL}?q={encoded}&location=Colombia"

    try:
        resp = session.get(url, timeout=_SESSION_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("BeBee HTML status %s", resp.status_code)
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = (
            soup.select("article.bee-job")
            or soup.select("[class*='job-item']")
            or soup.select("[class*='job-card']")
            or soup.select("li[class*='job']")
        )
        logger.info("BeBee HTML: found %d cards", len(cards))
        for card in cards[:limit]:
            title   = _clean(card.select_one("h2, h3, [class*='title']") and
                             card.select_one("h2, h3, [class*='title']").get_text())
            company = _clean(card.select_one("[class*='company']") and
                             card.select_one("[class*='company']").get_text())
            loc     = _clean(card.select_one("[class*='location']") and
                             card.select_one("[class*='location']").get_text())
            href    = card.select_one("a[href]")
            link    = ("https://co.bebee.com" + href["href"]) if href else ""
            if not title:
                continue
            domain, skills = _classify(title, "")
            jobs.append({
                "portal":             "bebee",
                "titulo":             title,
                "titulo_normalizado": _normalize_role(title),
                "empresa":            company or "",
                "ciudad":             loc or "Colombia",
                "modalidad":          "",
                "salario":            "",
                "descripcion":        "",
                "seniority":          "",
                "sector":             "",
                "dominio":            domain,
                "fecha_publicacion":  None,
                "url":                link,
                "skills_empleo":      skills,
            })
    except Exception as exc:
        logger.error("BeBee HTML scrape error: %s", exc)
    return jobs


def scrape_jobs(
    query: str,
    location: str = "Colombia",
    limit: int = 50,
    headless: bool = True,
) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(_HEADERS)

    logger.info("BeBee: scraping query='%s' limit=%d", query, limit)

    # Try JSON API first
    jobs = _api_scrape(query, limit, session)
    logger.info("BeBee API: %d results", len(jobs))

    # Fallback to HTML if API returned nothing
    if not jobs:
        jobs = _html_scrape(query, limit, session)
        logger.info("BeBee HTML fallback: %d results", len(jobs))

    return jobs[:limit]
