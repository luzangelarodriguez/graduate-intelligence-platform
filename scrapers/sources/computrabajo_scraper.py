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


_SECTION_HEADER_RE = re.compile(
    r"^(responsabilidades|funciones|actividades\s+a\s+realizar|"
    r"descripci[oó]n\s+del\s+cargo|qu[eé]\s+har[aá]s|"
    r"requisitos|perfil\s+requerido|perfil\s+del\s+candidato|"
    r"lo\s+que\s+buscamos|conocimientos\s+requeridos|"
    r"habilidades\s+y\s+conocimientos|experiencia\s+requerida)[:\s]*$",
    re.IGNORECASE,
)
_RESPONSABILIDADES_RE = re.compile(
    r"responsabilidades|funciones|actividades|descripci[oó]n\s+del\s+cargo|qu[eé]\s+har[aá]s",
    re.IGNORECASE,
)
_REQUISITOS_RE = re.compile(
    r"requisitos|perfil\s+requerido|perfil\s+del|lo\s+que\s+buscamos|"
    r"conocimientos\s+requeridos|habilidades\s+y\s+conocimientos|experiencia\s+requerida",
    re.IGNORECASE,
)


def _fetch_detail(session: requests.Session, url: str) -> dict[str, str]:
    """Fetch job detail page and return dict with description, responsabilidades, requisitos."""
    empty: dict[str, str] = {"descripcion": "", "responsabilidades": "", "requisitos": ""}
    try:
        resp = session.get(url, timeout=_SESSION_TIMEOUT)
        if resp.status_code != 200:
            return empty
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find the main description container
        container = None
        for sel in (
            "[class*='offer-description']",
            "[class*='job-description']",
            "[id*='offer-description']",
            "section.box_content",
        ):
            container = soup.select_one(sel)
            if container:
                break

        if not container:
            return empty

        full_text = _clean(container.get_text(" "))

        # Try to split into named sections by scanning heading/bold elements
        responsabilidades_parts: list[str] = []
        requisitos_parts: list[str] = []
        current_section: str | None = None

        for el in container.find_all(["h1", "h2", "h3", "h4", "strong", "b", "p", "li"]):
            text = _clean(el.get_text(" "))
            if not text:
                continue
            # Check if this element is a section header
            if _SECTION_HEADER_RE.match(text) or (len(text) < 80 and _SECTION_HEADER_RE.search(text)):
                if _RESPONSABILIDADES_RE.search(text):
                    current_section = "responsabilidades"
                elif _REQUISITOS_RE.search(text):
                    current_section = "requisitos"
                continue
            # Accumulate into current section (skip if heading element)
            if current_section and el.name not in ("h1", "h2", "h3", "h4"):
                if current_section == "responsabilidades":
                    responsabilidades_parts.append(text)
                else:
                    requisitos_parts.append(text)

        return {
            "descripcion": full_text,
            "responsabilidades": " ".join(responsabilidades_parts),
            "requisitos": " ".join(requisitos_parts),
        }
    except Exception:
        pass
    return empty


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

                # Fetch description and named sections (one request, no extras)
                detail: dict[str, str] = {"descripcion": "", "responsabilidades": "", "requisitos": ""}
                if full_url and detail_attempts < 15:
                    detail = _fetch_detail(session, full_url)
                    detail_attempts += 1
                    time.sleep(0.3)

                description     = detail["descripcion"]
                responsabilidades = detail["responsabilidades"]
                requisitos      = detail["requisitos"]
                full_text = " ".join(filter(None, [title, description, responsabilidades, requisitos]))
                domain, skills = _classify(title, full_text)

                # Detect modality / salary from full text
                low = full_text.casefold()
                if "remoto" in low or "teletrabajo" in low:
                    modalidad = "Remoto"
                elif "hibrid" in low:
                    modalidad = "Hibrido"
                elif "presencial" in low:
                    modalidad = "Presencial"
                else:
                    modalidad = ""
                sal_match = re.search(r"(\$ ?[\d.,]+(?:\s*a\s*\$? ?[\d.,]+)?)", full_text)
                salario = sal_match.group(1) if sal_match else ""

                jobs.append({
                    "portal":             "computrabajo",
                    "titulo":             title,
                    "titulo_normalizado": _normalize_role(title),
                    "empresa":            company,
                    "ciudad":             location_text,
                    "modalidad":          modalidad,
                    "salario":            salario,
                    "descripcion":        description,
                    "responsabilidades":  responsabilidades,
                    "requisitos":         requisitos,
                    "seniority":          "",
                    "sector":             "",
                    "dominio":            domain,
                    "fecha_publicacion":  None,
                    "url":                full_url,
                    # Key is 'skills' (not 'skills_empleo') so run_acquisition picks it up
                    "skills":             skills,
                })
            except Exception as exc:
                logger.debug("Computrabajo card error: %s", exc)
                continue

        page += 1
        time.sleep(_PAGE_DELAY)

    logger.info("Computrabajo: returning %d jobs for query '%s'", len(jobs), query)
    return jobs
