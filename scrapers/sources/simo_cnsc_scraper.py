"""
Scraper para SIMO (Sistema de Información y Gestión del Empleo Público) — CNSC Colombia.
https://simo.cnsc.gov.co/#ofertaEmpleo

Estrategia:
  1. Intercepta XHR/fetch en Playwright para capturar la API JSON interna que
     la SPA Angular usa. Si en 10s se detecta una respuesta con lista de ofertas,
     parsea JSON directamente (sin navegar oferta a oferta).
  2. Si la API no es detectable (CAPTCHA, sesión requerida, cambio de endpoint),
     cae a extracción por DOM.

Campos extraídos (según estructura pública del portal):
  - denominación del empleo (titulo)
  - entidad (empresa)
  - nivel del cargo (sector)
  - municipio/ciudad (ciudad)
  - propósito del cargo / funciones (descripcion / responsabilidades)
  - requisitos de estudio y experiencia (requisitos)

Registra BLOQUEADO si detecta CAPTCHA o login obligatorio y retorna lista vacía.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

LOGGER = logging.getLogger(__name__)

PORTAL = "simo_cnsc"
BASE_URL = "https://simo.cnsc.gov.co"

# Keywords that indicate a marketing-compatible role (used for domain filtering)
_MARKETING_KEYWORDS = re.compile(
    r"\b(marketing|mercadeo|publicidad|seo|sem|branding|community\s+manager|"
    r"digital|e.?commerce|comunicacion(es)?\s+digital|contenidos?\s+digital|"
    r"growth|analitica\s+(web|digital)|crm|campan[aá])\b",
    re.IGNORECASE,
)

# Known REST paths the SIMO Angular SPA uses (observed via browser DevTools).
# If the first returns 404 / non-JSON, the scraper falls back to the next.
_API_PATHS = [
    "/simo/rest/ofertaEmpleo/listarOfertasVigentes",
    "/simo/rest/ofertaEmpleo/listarOfertas",
    "/simo/api/ofertaEmpleo",
]


def _build_job(raw: dict) -> dict[str, Any]:
    """Map SIMO JSON fields to the platform's standard job dict."""
    titulo = (
        raw.get("denominacionEmpleo")
        or raw.get("denominacion")
        or raw.get("cargo")
        or raw.get("titulo")
        or ""
    ).strip()
    empresa = (
        raw.get("entidad")
        or raw.get("nombreEntidad")
        or raw.get("empresa")
        or ""
    ).strip()
    ciudad = (
        raw.get("municipio")
        or raw.get("ciudad")
        or raw.get("departamento")
        or "Colombia"
    ).strip()
    nivel = (raw.get("nivel") or raw.get("nivelCargo") or "").strip()
    proposito = (raw.get("propositoPrincipal") or raw.get("proposito") or raw.get("descripcion") or "").strip()
    funciones = (raw.get("funciones") or raw.get("descripcionFunciones") or "").strip()
    req_estudio = (raw.get("requisitosEstudio") or raw.get("estudio") or "").strip()
    req_experiencia = (raw.get("requisitosExperiencia") or raw.get("experiencia") or "").strip()
    requisitos = " ".join(filter(None, [req_estudio, req_experiencia])).strip()
    url_convocatoria = raw.get("urlConvocatoria") or raw.get("url") or BASE_URL
    if url_convocatoria and not url_convocatoria.startswith("http"):
        url_convocatoria = BASE_URL + url_convocatoria

    descripcion = " ".join(filter(None, [proposito, funciones]))
    full_text = " ".join(filter(None, [titulo, empresa, nivel, descripcion, requisitos]))

    return {
        "portal": PORTAL,
        "titulo": titulo,
        "titulo_normalizado": titulo.lower(),
        "empresa": empresa,
        "ciudad": ciudad,
        "modalidad": "Presencial",
        "salario": "",
        "descripcion": descripcion[:3000],
        "responsabilidades": funciones[:2000],
        "requisitos": requisitos[:1000],
        "seniority": _detect_seniority(full_text),
        "sector": nivel,
        "dominio": "marketing_commercial",
        "fecha_publicacion": raw.get("fechaPublicacion") or raw.get("fechaVigencia"),
        "url": url_convocatoria,
        "portal_origen": PORTAL,
        "timestamp_extraccion": datetime.now(timezone.utc).isoformat(),
        "skills": [],
    }


def _detect_seniority(text: str) -> str:
    low = text.casefold()
    if any(t in low for t in ("directivo", "asesor", "profesional especializado", "coordinador")):
        return "senior"
    if any(t in low for t in ("asistencial", "auxiliar", "tecnico", "bachiller")):
        return "junior"
    return "mid"


def _is_marketing_relevant(job: dict) -> bool:
    full = " ".join(filter(None, [
        job.get("titulo", ""),
        job.get("descripcion", ""),
        job.get("requisitos", ""),
    ]))
    return bool(_MARKETING_KEYWORDS.search(full))


async def _try_api(session_url: str, query: str, limit: int) -> list[dict] | None:
    """
    Attempt to call the SIMO REST API directly with requests (sync, run in thread).
    Returns list of raw dicts on success, None on failure.
    """
    try:
        import requests  # type: ignore
    except ImportError:
        return None

    headers = {
        "Accept": "application/json",
        "Referer": BASE_URL + "/#ofertaEmpleo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    }
    for path in _API_PATHS:
        url = BASE_URL + path
        try:
            resp = requests.get(url, headers=headers, timeout=15, params={"q": query, "size": limit})
            if resp.status_code == 200:
                ct = resp.headers.get("Content-Type", "")
                if "json" in ct:
                    data = resp.json()
                    # Accept list or dict with "content"/"data"/"items" key
                    if isinstance(data, list):
                        return data
                    for key in ("content", "data", "items", "ofertas", "result"):
                        if isinstance(data.get(key), list):
                            return data[key]
            LOGGER.debug("simo_api path=%s status=%s", path, resp.status_code)
        except Exception as exc:
            LOGGER.debug("simo_api path=%s error=%s", path, exc)
    return None


async def _scrape_playwright(query: str, limit: int, headless: bool) -> list[dict[str, Any]]:
    """
    Playwright-based fallback: intercept XHR responses that look like SIMO offer lists,
    then optionally scrape visible DOM cards if interception fails.
    """
    from playwright.async_api import async_playwright  # type: ignore

    captured: list[dict] = []
    blocked = False

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="es-CO",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
        )
        page = await context.new_page()

        async def _on_response(response):
            nonlocal blocked
            url = response.url
            if "oferta" not in url.lower() and "empleo" not in url.lower():
                return
            try:
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                body = await response.json()
                rows: list[dict] = []
                if isinstance(body, list):
                    rows = body
                else:
                    for key in ("content", "data", "items", "ofertas", "result"):
                        if isinstance(body.get(key), list):
                            rows = body[key]
                            break
                if rows:
                    captured.extend(rows)
                    LOGGER.info("simo_playwright intercepted %d rows from %s", len(rows), url)
            except Exception:
                pass

        page.on("response", _on_response)

        try:
            await page.goto(BASE_URL + "/#ofertaEmpleo", wait_until="domcontentloaded", timeout=20000)
            # Check for CAPTCHA / login wall
            page_text = (await page.inner_text("body")).casefold()
            if any(kw in page_text for kw in ("captcha", "iniciar sesión", "login requerido", "acceso denegado")):
                LOGGER.warning("simo_playwright: CAPTCHA or login wall detected — aborting")
                blocked = True
            else:
                # Wait up to 10s for XHR intercepts
                await page.wait_for_timeout(10000)
                # If no XHR captured, try DOM fallback
                if not captured:
                    await _dom_fallback(page, captured, limit)
        except Exception as exc:
            LOGGER.warning("simo_playwright navigation failed: %s", exc)
        finally:
            await context.close()
            await browser.close()

    if blocked:
        return []
    return captured


async def _dom_fallback(page, captured: list, limit: int) -> None:
    """Extract visible offer cards from the DOM when XHR interception yields nothing."""
    _card_selectors = [
        "app-card-oferta",
        "[class*='oferta-empleo']",
        "[class*='card-oferta']",
        "li[class*='oferta']",
        ".oferta",
    ]
    for sel in _card_selectors:
        try:
            cards = page.locator(sel)
            count = min(await cards.count(), limit)
            if count == 0:
                continue
            for i in range(count):
                card = cards.nth(i)
                text = (await card.inner_text(timeout=2000)).strip()
                if text:
                    captured.append({"denominacionEmpleo": text[:200], "descripcion": text[:1000]})
            LOGGER.info("simo_dom_fallback found %d cards with selector=%s", count, sel)
            return
        except Exception:
            continue


def scrape_jobs(
    query: str,
    location: str = "Colombia",
    limit: int = 50,
    headless: bool = True,
    domain_filter: bool = True,
) -> list[dict[str, Any]]:
    """
    Public interface (matches base.py pattern).

    Strategy:
      1. Direct REST API call (fast, no browser).
      2. Playwright with XHR interception if API fails.
      3. DOM fallback if XHR yields nothing.

    domain_filter=True: only returns jobs with marketing-relevant text.
    Returns [] if CAPTCHA/login blocks access — caller should log and continue.
    """
    # Step 1: direct API
    raw_rows: list[dict] | None = asyncio.run(_try_api(BASE_URL, query, limit))

    # Step 2: Playwright
    if not raw_rows:
        LOGGER.info("simo_cnsc: API unavailable, switching to Playwright")
        raw_rows = asyncio.run(_scrape_playwright(query, limit, headless))

    if not raw_rows:
        LOGGER.warning("simo_cnsc: no results returned (possibly blocked)")
        return []

    jobs = [_build_job(r) for r in raw_rows[:limit]]

    if domain_filter:
        jobs = [j for j in jobs if _is_marketing_relevant(j)]
        LOGGER.info("simo_cnsc: %d marketing-relevant jobs after domain filter", len(jobs))

    return jobs
