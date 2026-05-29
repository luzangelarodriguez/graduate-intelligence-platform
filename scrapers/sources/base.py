from __future__ import annotations

import asyncio
import logging
import re
import time
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
    max_pages: int = 3
    max_runtime_seconds: int = 75
    max_detail_attempts: int = 24


@dataclass(frozen=True)
class WaitResult:
    selector: str
    elapsed_ms: int
    attempts: int
    runtime: dict[str, Any]
    status: str


def build_search_url(template: str, query: str, location: str = "Colombia") -> str:
    return template.format(query=quote_plus(query), location=quote_plus(location))


async def detect_runtime(page: Page) -> dict[str, Any]:
    try:
        return await page.evaluate(
            """() => ({
                nextjs: Boolean(window.__NEXT_DATA__ || document.querySelector('script[src*="/_next/"]')),
                reactRoot: Boolean(
                    document.querySelector('#root, #__next, [data-reactroot]') ||
                    Array.from(document.querySelectorAll('script[src]')).some((script) =>
                        /react|webpack|vite|chunk/i.test(script.getAttribute('src') || '')
                    )
                ),
                likelyPolling: performance.getEntriesByType('resource')
                    .filter((entry) => Date.now() - entry.responseEnd < 5000).length > 8
            })"""
        )
    except Exception:
        return {"nextjs": False, "reactRoot": False, "likelyPolling": False}


async def safe_wait_for_results(
    page: Page,
    selectors: tuple[str, ...],
    *,
    source: str,
    phase: str,
    timeout_ms: int = 12000,
    retries: int = 2,
    fallback_wait_ms: int = 1200,
) -> WaitResult:
    """Wait for real DOM evidence instead of network idleness.

    Modern job portals often keep analytics, GraphQL polling or long-lived XHR
    alive forever. This helper treats visible/attached result selectors as the
    primary readiness signal and falls back to domcontentloaded plus short
    exponential sleeps so a source can degrade without blocking the pipeline.
    """
    started = time.perf_counter()
    runtime = await detect_runtime(page)
    last_error = ""
    for attempt in range(1, retries + 2):
        attempt_deadline = time.perf_counter() + (timeout_ms / 1000)
        for selector in selectors:
            try:
                remaining_ms = int((attempt_deadline - time.perf_counter()) * 1000)
                if remaining_ms <= 0:
                    break
                selector_timeout_ms = max(250, min(remaining_ms, timeout_ms // max(1, len(selectors))))
                await page.wait_for_selector(selector, state="attached", timeout=selector_timeout_ms)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                LOGGER.info(
                    "source=%s phase=%s wait_status=selector_found selector=%r elapsed_ms=%s attempt=%s runtime=%s",
                    source,
                    phase,
                    selector,
                    elapsed_ms,
                    attempt,
                    runtime,
                )
                return WaitResult(selector=selector, elapsed_ms=elapsed_ms, attempts=attempt, runtime=runtime, status="selector_found")
            except PlaywrightTimeoutError as exc:
                last_error = str(exc).splitlines()[0]
            except Exception as exc:
                last_error = str(exc)

        try:
            remaining_ms = max(250, int((attempt_deadline - time.perf_counter()) * 1000))
            await page.wait_for_load_state("domcontentloaded", timeout=min(1000, remaining_ms))
        except PlaywrightTimeoutError as exc:
            last_error = str(exc).splitlines()[0]
        except Exception as exc:
            last_error = str(exc)

        sleep_ms = fallback_wait_ms * attempt
        LOGGER.warning(
            "source=%s phase=%s wait_retry=%s timeout_ms=%s fallback_sleep_ms=%s runtime=%s error=%s",
            source,
            phase,
            attempt,
            timeout_ms,
            sleep_ms,
            runtime,
            last_error,
        )
        await page.wait_for_timeout(sleep_ms)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    LOGGER.error(
        "source=%s phase=%s wait_status=timeout elapsed_ms=%s retries=%s runtime=%s error=%s",
        source,
        phase,
        elapsed_ms,
        retries,
        runtime,
        last_error,
    )
    return WaitResult(selector="", elapsed_ms=elapsed_ms, attempts=retries + 1, runtime=runtime, status="timeout")


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
        page.set_default_timeout(10000)
        url = build_search_url(self.config.search_url_template, query=query, location=location)
        jobs: list[dict[str, Any]] = []
        source_deadline = time.perf_counter() + self.config.max_runtime_seconds
        detail_attempts = 0
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            wait_result = await safe_wait_for_results(
                page,
                self.config.card_selectors,
                source=self.config.portal,
                phase="search",
                timeout_ms=12000,
                retries=2,
            )
            if wait_result.status == "timeout":
                LOGGER.warning("source=%s source_status=degraded phase=search reason=no_result_selectors", self.config.portal)
            seen_links: set[str] = set()
            page_number = 1
            while len(jobs) < limit and page_number <= self.config.max_pages and time.perf_counter() < source_deadline:
                links = await extract_card_links(page, self.config)
                LOGGER.info(
                    "source=%s phase=listing page=%s links=%s jobs=%s limit=%s",
                    self.config.portal,
                    page_number,
                    len(links),
                    len(jobs),
                    limit,
                )
                for link in links:
                    if time.perf_counter() >= source_deadline:
                        LOGGER.warning(
                            "source=%s source_status=degraded reason=source_runtime_budget_exhausted jobs=%s elapsed_seconds=%s",
                            self.config.portal,
                            len(jobs),
                            self.config.max_runtime_seconds,
                        )
                        break
                    if detail_attempts >= self.config.max_detail_attempts:
                        LOGGER.warning(
                            "source=%s source_status=degraded reason=max_detail_attempts attempts=%s jobs=%s",
                            self.config.portal,
                            detail_attempts,
                            len(jobs),
                        )
                        break
                    if link in seen_links or len(jobs) >= limit:
                        continue
                    seen_links.add(link)
                    detail_attempts += 1
                    detail = await self._extract_detail(context, link)
                    if detail.get("titulo") or detail.get("descripcion"):
                        jobs.append(detail)
                if (
                    len(jobs) >= limit
                    or page_number >= self.config.max_pages
                    or detail_attempts >= self.config.max_detail_attempts
                    or time.perf_counter() >= source_deadline
                    or not await self._go_next(page)
                ):
                    break
                page_number += 1
            if len(jobs) < limit and page_number >= self.config.max_pages:
                LOGGER.info(
                    "source=%s source_status=degraded reason=max_pages_reached pages=%s jobs=%s requested_limit=%s",
                    self.config.portal,
                    self.config.max_pages,
                    len(jobs),
                    limit,
                )
        except Exception as exc:
            LOGGER.exception("source=%s failed: %s", self.config.portal, exc)
            await page.screenshot(path=str(screenshots_dir / f"{self.config.portal}_error.png"), full_page=True)
        finally:
            await context.close()
        return jobs

    async def _extract_detail(self, context: Any, url: str) -> dict[str, Any]:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=8000)
            await safe_wait_for_results(
                page,
                ("h1", "h2", "main", "article", *self.config.description_selectors),
                source=self.config.portal,
                phase="detail",
                timeout_ms=2500,
                retries=0,
                fallback_wait_ms=500,
            )
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
        except Exception as exc:
            LOGGER.warning("source=%s source_status=degraded phase=detail url=%s error=%s", self.config.portal, url, exc)
            return {}
        finally:
            await page.close()

    async def _go_next(self, page: Page) -> bool:
        for selector in self.config.next_selectors:
            try:
                target = page.locator(selector).first
                if await target.count() and await target.is_enabled():
                    await target.click()
                    wait_result = await safe_wait_for_results(
                        page,
                        self.config.card_selectors,
                        source=self.config.portal,
                        phase="pagination",
                        timeout_ms=9000,
                        retries=1,
                    )
                    if wait_result.status == "timeout":
                        LOGGER.warning("source=%s source_status=degraded phase=pagination reason=no_next_results", self.config.portal)
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
