from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError, async_playwright

try:
    from scrapers.normalization.classify_domains import classify_text_domain
    from scrapers.normalization.deduplicate_jobs import job_content_hash
    from scrapers.normalization.normalize_roles import normalize_role
    from scrapers.normalization.normalize_skills import extract_skills
except ModuleNotFoundError:
    from normalization.classify_domains import classify_text_domain
    from normalization.deduplicate_jobs import job_content_hash
    from normalization.normalize_roles import normalize_role
    from normalization.normalize_skills import extract_skills


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceConfig:
    portal: str
    base_url: str
    search_url_template: str
    card_selectors: tuple[str, ...]
    title_selectors: tuple[str, ...] = ("h1", "h2", "[class*='title']", "[class*='cargo']")
    company_selectors: tuple[str, ...] = ("[class*='company']", "[class*='empresa']", "[data-testid*='company']")
    city_selectors: tuple[str, ...] = ("[class*='city']", "[class*='location']", "[class*='ubicacion']")
    description_selectors: tuple[str, ...] = ("[class*='description']", "[class*='descripcion']", "main", "article")
    next_selectors: tuple[str, ...] = ("a[rel='next']", "button:has-text('Siguiente')", "a:has-text('Siguiente')")


def build_search_url(template: str, query: str, location: str = "Colombia") -> str:
    return template.format(query=quote_plus(query), location=quote_plus(location))


async def first_text(page: Page, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count():
                text = (await locator.inner_text(timeout=1500)).strip()
                if text:
                    return re.sub(r"\s+", " ", text)
        except Exception:
            continue
    return ""


async def extract_card_links(page: Page, config: SourceConfig) -> list[str]:
    links: list[str] = []
    for selector in config.card_selectors:
        try:
            cards = page.locator(selector)
            count = min(await cards.count(), 80)
            for index in range(count):
                card = cards.nth(index)
                href = ""
                if await card.evaluate("el => el.tagName.toLowerCase() === 'a'"):
                    href = await card.get_attribute("href") or ""
                if not href:
                    href = await card.locator("a[href]").first.get_attribute("href", timeout=1000) or ""
                if href:
                    links.append(href if href.startswith("http") else f"{config.base_url.rstrip('/')}/{href.lstrip('/')}")
        except Exception:
            continue
    return list(dict.fromkeys(links))


def looks_like_non_job_page(title: str, description: str, url: str) -> bool:
    title_norm = re.sub(r"\s+", " ", title or "").strip().casefold()
    description_norm = re.sub(r"\s+", " ", description or "").strip().casefold()
    url_norm = (url or "").casefold()
    if title_norm in {"inicio", "home", "buscar empleo", "registro de vacantes"}:
        return True
    nav_terms = ("transparencia", "atencion a la ciudadania", "participa", "normativa", "prensa")
    if sum(1 for term in nav_terms if term in description_norm) >= 3:
        return True
    if "registro-de-vacantes" in url_norm and not any(term in description_norm for term in ("cargo", "salario", "experiencia")):
        return True
    return False


class PlaywrightJobSource:
    def __init__(self, config: SourceConfig) -> None:
        self.config = config

    async def scrape(
        self,
        *,
        query: str,
        location: str = "Colombia",
        limit: int = 50,
        headless: bool = True,
        screenshots_dir: str | Path = "logs/screenshots",
    ) -> list[dict[str, Any]]:
        Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            try:
                return await self._scrape_with_browser(
                    browser,
                    query=query,
                    location=location,
                    limit=limit,
                    screenshots_dir=Path(screenshots_dir),
                )
            finally:
                await browser.close()

    async def _scrape_with_browser(
        self,
        browser: Browser,
        *,
        query: str,
        location: str,
        limit: int,
        screenshots_dir: Path,
    ) -> list[dict[str, Any]]:
        context = await browser.new_context(
            locale="es-CO",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        page.set_default_timeout(18000)
        url = build_search_url(self.config.search_url_template, query=query, location=location)
        jobs: list[dict[str, Any]] = []
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle", timeout=20000)
            seen_links: set[str] = set()
            while len(jobs) < limit:
                links = await extract_card_links(page, self.config)
                for link in links:
                    if link in seen_links or len(jobs) >= limit:
                        continue
                    seen_links.add(link)
                    detail = await self._extract_detail(context, link)
                    if detail.get("titulo") or detail.get("descripcion"):
                        jobs.append(detail)
                if len(jobs) >= limit or not await self._go_next(page):
                    break
        except Exception as exc:
            LOGGER.exception("source=%s failed: %s", self.config.portal, exc)
            await page.screenshot(path=str(screenshots_dir / f"{self.config.portal}_error.png"), full_page=True)
        finally:
            await context.close()
        return jobs

    async def _extract_detail(self, context: Any, url: str) -> dict[str, Any]:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=12000)
            except PlaywrightTimeoutError:
                pass
            title = await first_text(page, self.config.title_selectors)
            company = await first_text(page, self.config.company_selectors)
            city = await first_text(page, self.config.city_selectors)
            description = await first_text(page, self.config.description_selectors)
            if looks_like_non_job_page(title, description, url):
                return {}
            domain = classify_text_domain(f"{title} {description}").primary_domain
            skills = extract_skills(description, domain_hint=domain)
            job = {
                "portal": self.config.portal,
                "titulo": title,
                "titulo_normalizado": normalize_role(title),
                "empresa": company,
                "ciudad": city,
                "modalidad": self._detect_modality(description),
                "salario": self._detect_salary(description),
                "descripcion": description,
                "seniority": self._detect_seniority(f"{title} {description}"),
                "sector": "",
                "dominio": domain,
                "fecha_publicacion": None,
                "url": url,
                "portal_origen": self.config.portal,
                "timestamp_extraccion": datetime.now(timezone.utc).isoformat(),
                "skills": [match.skill_normalized for match in skills],
                "skill_matches": skills,
            }
            job["hash_contenido"] = job_content_hash(job)
            return job
        finally:
            await page.close()

    async def _go_next(self, page: Page) -> bool:
        for selector in self.config.next_selectors:
            try:
                target = page.locator(selector).first
                if await target.count() and await target.is_enabled():
                    await target.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _detect_modality(text: str) -> str:
        low = text.casefold()
        if "remoto" in low or "teletrabajo" in low:
            return "Remoto"
        if "hibrid" in low:
            return "Hibrido"
        if "presencial" in low:
            return "Presencial"
        return ""

    @staticmethod
    def _detect_salary(text: str) -> str:
        match = re.search(r"(\$ ?[\d.,]+(?:\s*a\s*\$? ?[\d.,]+)?)", text)
        return match.group(1) if match else ""

    @staticmethod
    def _detect_seniority(text: str) -> str:
        low = text.casefold()
        if any(term in low for term in ("senior", "lider", "coordinador", "jefe", "gerente")):
            return "senior"
        if any(term in low for term in ("junior", "practicante", "trainee", "auxiliar")):
            return "junior"
        return "mid"


def run_async_scraper(scraper: PlaywrightJobSource, **kwargs: Any) -> list[dict[str, Any]]:
    return asyncio.run(scraper.scrape(**kwargs))
