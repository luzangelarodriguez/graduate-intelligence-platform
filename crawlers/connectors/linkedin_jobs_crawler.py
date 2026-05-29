from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.agentic_job_extractor import EnterpriseAgenticJobExtractor  # noqa: E402
from agents.visual_analytics_labor_agent import AgentExtractionResult  # noqa: E402

SESSION_STATE_PATH = ROOT_DIR / ".local_sessions" / "linkedin_storage_state.json"
LINKEDIN_OUTPUT_REPORT = ROOT_DIR / "outputs" / "linkedin_jobs_crawler_report.md"
DEFAULT_KEYWORDS = [
    "data analyst",
    "business intelligence",
    "power bi",
    "analytics engineer",
    "data visualization",
    "big data",
    "data engineer",
]
DEFAULT_LOCATION = "Colombia"


@dataclass(frozen=True)
class LinkedInCrawlerConfig:
    storage_state_path: Path = SESSION_STATE_PATH
    keywords: list[str] | None = None
    location: str = DEFAULT_LOCATION
    max_jobs: int = 20
    max_pages: int = 1
    headless: bool = True


def storage_state_message(path: Path = SESSION_STATE_PATH) -> str:
    return f"Ejecuta primero scripts/linkedin_manual_login.py. No se encontro sesion local en {path}."


def _job_search_url(keyword: str, location: str, page: int = 0) -> str:
    start = max(page, 0) * 25
    return (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={quote_plus(keyword)}&location={quote_plus(location)}&start={start}"
    )


def _is_security_checkpoint(page: Any) -> bool:
    url = str(getattr(page, "url", "") or "").casefold()
    try:
        text = page.locator("body").inner_text(timeout=1500).casefold()
    except Exception:
        text = ""
    markers = (
        "captcha",
        "checkpoint",
        "security verification",
        "verificacion de seguridad",
        "verificación de seguridad",
        "unusual activity",
    )
    return any(marker in url or marker in text for marker in markers)


def _extract_detail_payload(page: Any, job_url: str) -> dict[str, Any]:
    title = ""
    company = ""
    location = ""
    date_posted = ""
    description = ""
    modality = ""
    try:
        title = page.locator("h1").first.inner_text(timeout=3000)
    except Exception:
        title = ""
    for selector in (".job-details-jobs-unified-top-card__company-name", ".jobs-unified-top-card__company-name", "[class*='company-name']"):
        try:
            company = page.locator(selector).first.inner_text(timeout=1500)
            if company:
                break
        except Exception:
            continue
    for selector in (".job-details-jobs-unified-top-card__primary-description-container", ".jobs-unified-top-card__bullet", "[class*='location']"):
        try:
            location = page.locator(selector).first.inner_text(timeout=1500)
            if location:
                break
        except Exception:
            continue
    for selector in ("time", "[class*='posted']", "[class*='listed']"):
        try:
            date_posted = page.locator(selector).first.inner_text(timeout=1200)
            if date_posted:
                break
        except Exception:
            continue
    for selector in (".jobs-description-content__text", "#job-details", "[class*='description']"):
        try:
            description = page.locator(selector).first.inner_text(timeout=3000)
            if description:
                break
        except Exception:
            continue
    lowered = description.casefold()
    if "remote" in lowered or "remoto" in lowered:
        modality = "remote"
    elif "hybrid" in lowered or "hibrido" in lowered or "híbrido" in lowered:
        modality = "hybrid"
    elif "presencial" in lowered or "onsite" in lowered:
        modality = "onsite"
    return {
        "title": title,
        "company": company,
        "location": location or DEFAULT_LOCATION,
        "modality": modality,
        "description": description,
        "requirements": [],
        "responsibilities": [],
        "date_posted": date_posted,
        "job_url": job_url,
        "source_name": "linkedin",
    }


class LinkedInJobsCrawler:
    def __init__(self, config: LinkedInCrawlerConfig | None = None) -> None:
        self.config = config or LinkedInCrawlerConfig()
        self.keywords = self.config.keywords or DEFAULT_KEYWORDS
        self.extractor = EnterpriseAgenticJobExtractor()

    def ensure_storage_state(self) -> tuple[bool, str]:
        path = self.config.storage_state_path
        if not path.exists():
            return False, storage_state_message(path)
        return True, "storage_state_available"

    def run(self, *, execute_network: bool = False) -> tuple[list[AgentExtractionResult], list[dict[str, str]]]:
        ready, message = self.ensure_storage_state()
        if not ready:
            return [], [{"source": "linkedin", "error_type": "missing_storage_state", "error_message": message}]
        if not execute_network:
            return [], [{"source": "linkedin", "error_type": "dry_run", "error_message": "network_not_executed"}]
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - optional runtime
            return [], [{"source": "linkedin", "error_type": "playwright_missing", "error_message": str(exc)}]

        results: list[AgentExtractionResult] = []
        errors: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            context = browser.new_context(
                storage_state=str(self.config.storage_state_path),
                viewport={"width": 1366, "height": 850},
                locale="es-CO",
            )
            page = context.new_page()
            for keyword in self.keywords:
                for page_index in range(self.config.max_pages):
                    if len(results) >= self.config.max_jobs:
                        break
                    search_url = _job_search_url(keyword, self.config.location, page_index)
                    try:
                        page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
                        page.wait_for_timeout(random.randint(1600, 3200))
                        page.mouse.wheel(0, random.randint(500, 1100))
                        if _is_security_checkpoint(page):
                            errors.append({"source": "linkedin", "error_type": "security_checkpoint", "error_message": "captcha_or_checkpoint_detected"})
                            browser.close()
                            write_linkedin_report(results, errors)
                            return results, errors
                        links = page.locator("a[href*='/jobs/view/']").evaluate_all(
                            "(els) => [...new Set(els.map((a) => a.href).filter(Boolean))]"
                        )
                        for link in links:
                            job_url = str(link).split("?")[0]
                            if job_url in seen_urls or len(results) >= self.config.max_jobs:
                                continue
                            seen_urls.add(job_url)
                            detail = context.new_page()
                            try:
                                detail.goto(job_url, wait_until="domcontentloaded", timeout=35000)
                                detail.wait_for_timeout(random.randint(1800, 3600))
                                if _is_security_checkpoint(detail):
                                    errors.append({"source": "linkedin", "error_type": "security_checkpoint", "error_message": "captcha_or_checkpoint_detected"})
                                    detail.close()
                                    browser.close()
                                    write_linkedin_report(results, errors)
                                    return results, errors
                                payload = _extract_detail_payload(detail, job_url)
                                html = "<html><body><main>"
                                html += f"<h1>{payload['title']}</h1>"
                                html += f"<div class='company'>{payload['company']}</div>"
                                html += f"<div class='location'>{payload['location']}</div>"
                                html += f"<article class='description'>{payload['description']}</article>"
                                html += "</main></body></html>"
                                result = self.extractor.inspect_detail_html(
                                    html=html,
                                    source_name="linkedin",
                                    source_url=job_url,
                                    fallback_title=payload["title"],
                                )
                                contextual = dict(result.silver.contextual)
                                contextual.update(
                                    {
                                        "modality": payload["modality"],
                                        "date_posted": payload["date_posted"],
                                        "requirements": payload["requirements"],
                                        "responsibilities": payload["responsibilities"],
                                    }
                                )
                                result.silver.contextual.update(contextual)
                                results.append(result)
                            except Exception as exc:
                                errors.append({"source": "linkedin", "error_type": type(exc).__name__, "error_message": str(exc)[:400]})
                            finally:
                                try:
                                    detail.close()
                                except Exception:
                                    pass
                            time.sleep(random.uniform(1.2, 2.8))
                    except Exception as exc:
                        errors.append({"source": "linkedin", "error_type": type(exc).__name__, "error_message": str(exc)[:400]})
                if len(results) >= self.config.max_jobs:
                    break
            browser.close()
        write_linkedin_report(results, errors)
        return results, errors


def write_linkedin_report(results: list[AgentExtractionResult], errors: list[dict[str, str]]) -> None:
    LINKEDIN_OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LinkedIn Jobs Crawler Report",
        "",
        f"- Resultados: {len(results)}",
        f"- Errores: {len(errors)}",
        "- Storage state: local file used, contents never printed.",
        "",
        "## Vacantes",
    ]
    for result in results[:40]:
        lines.extend(
            [
                f"- {result.silver.normalized_title} | {result.silver.normalized_company} | {result.silver.normalized_location}",
                f"  - URL: {result.silver.source_url}",
                f"  - Skills: {', '.join(result.silver.job_evidence_skills or []) or 'N/A'}",
            ]
        )
    lines.extend(["", "## Errores"])
    lines.extend([f"- {error['error_type']}: {error['error_message']}" for error in errors] or ["- Sin errores."])
    LINKEDIN_OUTPUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    crawler = LinkedInJobsCrawler(LinkedInCrawlerConfig(headless=False))
    results, errors = crawler.run(execute_network=True)
    print(json.dumps({"results": len(results), "errors": errors}, indent=2, ensure_ascii=False))
    return 0 if results or errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
