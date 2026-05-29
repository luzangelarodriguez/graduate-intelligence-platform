from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.visual_analytics_labor_agent import (  # noqa: E402
    AgentExtractionResult,
    VisualAnalyticsLaborAgent,
    classify_document_type,
    content_hash,
    evidence_to_dict,
    parse_detail_html,
)
from ml.labor.semantic_job_skill_extractor import extract_semantic_job_skills, semantic_skills_to_dict  # noqa: E402
from scrapers.connectors.indeed_partner_connector import IndeedPartnerConnector  # noqa: E402
from scrapers.connectors.jooble_connector import JoobleConnector  # noqa: E402
from scrapers.connectors.base import absolute_url, compact_text  # noqa: E402

OUTPUT_JSON = ROOT_DIR / "outputs" / "enterprise_agentic_job_extraction_results.json"
QUALITY_REPORT = ROOT_DIR / "outputs" / "job_extraction_quality_report.md"
MARKET_SIGNAL_REPORT = ROOT_DIR / "outputs" / "job_market_signal_report.md"

SOURCE_URLS = {
    "linkedin": ("LinkedIn Jobs", "https://www.linkedin.com/jobs"),
    "elempleo": ("Elempleo", "https://www.elempleo.com/co/ofertas-empleo/"),
    "ticjob": ("Ticjob", "https://ticjob.co/es/search"),
    "hireline": ("Hireline", "https://hireline.io/co/empleos"),
    "computrabajo": ("Computrabajo", "https://co.computrabajo.com"),
    "spe": ("Servicio Publico de Empleo", "https://www.buscadordeempleo.gov.co/#/home"),
    "sena": ("Agencia Publica de Empleo SENA", "https://agenciapublicadeempleo.sena.edu.co"),
    "findjobit": ("FindJobIT", "https://findjobit.com/jobs/country/colombia"),
    "indeed_partner": ("Indeed Partner", "api://indeed_partner"),
    "jooble": ("Jooble", "api://jooble"),
}

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 Version/16.6 Safari/605.1.15",
)

SEARCH_TERMS = ("analista datos", "business intelligence", "power bi", "data analyst", "analytics")


@dataclass(frozen=True)
class AgenticNavigationPolicy:
    min_delay_ms: int = 900
    max_delay_ms: int = 2400
    max_retries: int = 2
    max_pages: int = 2
    max_jobs: int = 30
    headless: bool = True


def is_real_job_posting(payload: dict[str, Any], source_url: str) -> bool:
    return bool(classify_document_type(payload, source_url=source_url)["is_real_job_posting"])


def job_content_hash(*, title: str, company: str, normalized_description: str) -> str:
    return content_hash(title, company, normalized_description)


def _candidate_selectors() -> tuple[str, ...]:
    return (
        "a[href*='job']",
        "a[href*='empleo']",
        "a[href*='oferta']",
        "a[href*='vacante']",
        "a[href*='it-job-openings']",
        "article a[href]",
        "[class*='job'] a[href]",
        "[class*='vacante'] a[href]",
    )


def _looks_like_detail_url(url: str) -> bool:
    lowered = url.casefold()
    if lowered.startswith("javascript:"):
        return False
    return any(token in lowered for token in ("job", "empleo", "oferta", "vacante", "it-job-openings"))


def _extract_links_from_page(page: Any, base_url: str, max_links: int) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for selector in _candidate_selectors():
        try:
            hrefs = page.locator(selector).evaluate_all("(els) => els.map((a) => a.href || a.getAttribute('href')).filter(Boolean)")
        except Exception:
            continue
        for href in hrefs:
            url = absolute_url(base_url, str(href))
            if not _looks_like_detail_url(url) or url in seen:
                continue
            seen.add(url)
            links.append(url)
            if len(links) >= max_links:
                return links
    return links


class EnterpriseAgenticJobExtractor:
    def __init__(self, policy: AgenticNavigationPolicy | None = None) -> None:
        self.policy = policy or AgenticNavigationPolicy()
        self.static_agent = VisualAnalyticsLaborAgent(headless=self.policy.headless, max_jobs=self.policy.max_jobs)

    def inspect_detail_html(self, *, html: str, source_name: str, source_url: str, fallback_title: str = "") -> AgentExtractionResult:
        result = self.static_agent.inspect_static_html(html=html, source_name=source_name, source_url=source_url, fallback_title=fallback_title)
        semantic_items = extract_semantic_job_skills(
            title=result.silver.normalized_title,
            description=result.silver.normalized_description,
            tags=result.silver.job_evidence_skills or result.silver.portal_taxonomy_skills or [],
            evidence_source_type=result.silver.evidence_source_type,
        )
        contextual = {
            **result.silver.contextual,
            "semantic_skill_evidence": semantic_skills_to_dict(semantic_items),
            "skill_confidence_score": max([item.confidence for item in semantic_items], default=0.0),
        }
        result.silver.contextual.update(contextual)
        return result

    def run_source(self, *, source_name: str, source_url: str) -> list[AgentExtractionResult]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - optional runtime
            raise RuntimeError("Playwright is required for enterprise agentic extraction") from exc

        results: list[AgentExtractionResult] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.policy.headless)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport=random.choice(({"width": 1366, "height": 768}, {"width": 1440, "height": 900}, {"width": 1280, "height": 800})),
                locale="es-CO",
            )
            page = context.new_page()
            for attempt in range(self.policy.max_retries + 1):
                try:
                    page.goto(source_url, wait_until="domcontentloaded", timeout=25000)
                    break
                except Exception:
                    if attempt >= self.policy.max_retries:
                        raise
                    time.sleep(1.5 * (attempt + 1))
            for _ in range(self.policy.max_pages):
                page.wait_for_timeout(random.randint(self.policy.min_delay_ms, self.policy.max_delay_ms))
                page.mouse.wheel(0, random.randint(550, 1200))
            links = _extract_links_from_page(page, source_url, self.policy.max_jobs)
            for url in links:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(random.randint(self.policy.min_delay_ms, self.policy.max_delay_ms))
                    page.mouse.wheel(0, random.randint(300, 900))
                    results.append(
                        self.inspect_detail_html(
                            html=page.content(),
                            source_name=source_name,
                            source_url=url,
                            fallback_title=page.title(),
                        )
                    )
                except Exception:
                    continue
            browser.close()
        return results


def deduplicate_results(results: list[AgentExtractionResult]) -> list[AgentExtractionResult]:
    seen: set[str] = set()
    unique: list[AgentExtractionResult] = []
    for item in results:
        key = item.bronze.content_hash
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def write_reports(results: list[AgentExtractionResult], errors: list[dict[str, str]]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps([evidence_to_dict(item) for item in results], indent=2, ensure_ascii=False), encoding="utf-8")
    gold = [item for item in results if item.gold]
    job_postings = [item for item in results if item.silver.document_type == "job_posting"]
    taxonomy = [item for item in results if item.silver.document_type in {"portal_taxonomy", "filter_page", "category_page", "search_listing"}]
    lines = [
        "# Job Extraction Quality Report",
        "",
        f"- Documentos inspeccionados: {len(results)}",
        f"- Vacantes reales: {len(job_postings)}",
        f"- Documentos bloqueados por taxonomia/listado: {len(taxonomy)}",
        f"- Gold aprobadas: {len(gold)}",
        f"- Errores: {len(errors)}",
        "",
    ]
    for item in results[:40]:
        lines.extend(
            [
                f"## {item.silver.normalized_title or item.bronze.page_title}",
                f"- Fuente: {item.silver.source_name}",
                f"- Tipo documento: {item.silver.document_type}",
                f"- Empresa: {item.silver.normalized_company or 'N/A'}",
                f"- URL: {item.silver.source_url}",
                f"- Skills de vacante: {', '.join(item.silver.job_evidence_skills or []) or 'N/A'}",
                f"- Skills de taxonomia bloqueadas: {', '.join(item.silver.portal_taxonomy_skills or []) or 'N/A'}",
                f"- Accepted for Gold: {item.silver.accepted_for_gold}",
                f"- Rechazo/motivo: {item.silver.rejection_reason}",
                "",
            ]
        )
    QUALITY_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    skill_counts: dict[str, int] = {}
    for item in results:
        for skill in item.silver.job_evidence_skills or []:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    market_lines = ["# Job Market Signal Report", "", "## Skills de vacantes reales", ""]
    market_lines.extend([f"- {skill}: {count}" for skill, count in sorted(skill_counts.items(), key=lambda row: row[1], reverse=True)] or ["- Sin skills de vacante real."])
    MARKET_SIGNAL_REPORT.write_text("\n".join(market_lines) + "\n", encoding="utf-8")


def run_enterprise_extraction(*, sources: list[str], execute_network: bool = False, max_jobs: int = 30, max_pages: int = 2) -> dict[str, Any]:
    selected = [source for source in sources if source in SOURCE_URLS] or list(SOURCE_URLS)
    policy = AgenticNavigationPolicy(max_jobs=max_jobs, max_pages=max_pages)
    extractor = EnterpriseAgenticJobExtractor(policy)
    results: list[AgentExtractionResult] = []
    errors: list[dict[str, str]] = []
    if not execute_network:
        dry_run_meta: dict[str, Any] = {}
        if "indeed_partner" in selected:
            _indeed_results, indeed_meta = IndeedPartnerConnector().fetch_agent_results(execute_network=False, max_jobs=max_jobs)
            dry_run_meta["indeed_partner"] = indeed_meta
            if indeed_meta.get("source_status") == "credentials_missing":
                errors.append({"source": "Indeed Partner", "error_type": "credentials_missing", "error_message": "Indeed credentials are not configured"})
        if "jooble" in selected:
            _jooble_results, jooble_meta = JoobleConnector().fetch_agent_results(execute_network=False, max_jobs=max_jobs)
            dry_run_meta["jooble"] = jooble_meta
            if jooble_meta.get("source_status") == "credentials_missing":
                errors.append({"source": "Jooble", "error_type": "credentials_missing", "error_message": "Jooble credentials are not configured"})
        write_reports([], [])
        return {"dry_run": True, "sources": selected, "results": 0, "gold": 0, "source_status": dry_run_meta, "errors": len(errors)}
    for source in selected:
        source_name, url = SOURCE_URLS[source]
        try:
            if source == "indeed_partner":
                indeed_results, indeed_meta = IndeedPartnerConnector().fetch_agent_results(
                    execute_network=execute_network,
                    max_jobs=max_jobs,
                )
                results.extend(indeed_results)
                for error in indeed_meta.get("errors", []):
                    errors.append({"source": source_name, "error_type": str(error.get("error_type", "indeed_error")), "error_message": str(error)[:500]})
                if indeed_meta.get("source_status") == "credentials_missing":
                    errors.append({"source": source_name, "error_type": "credentials_missing", "error_message": "Indeed credentials are not configured"})
            elif source == "jooble":
                jooble_results, jooble_meta = JoobleConnector().fetch_agent_results(
                    execute_network=execute_network,
                    max_jobs=max_jobs,
                )
                results.extend(jooble_results)
                for error in jooble_meta.get("errors", []):
                    errors.append({"source": source_name, "error_type": str(error.get("error_type", "jooble_error")), "error_message": str(error)[:500]})
                if jooble_meta.get("source_status") == "credentials_missing":
                    errors.append({"source": source_name, "error_type": "credentials_missing", "error_message": "Jooble credentials are not configured"})
            else:
                results.extend(extractor.run_source(source_name=source_name, source_url=url))
        except Exception as exc:  # pragma: no cover - network behavior changes by source
            errors.append({"source": source_name, "error_type": type(exc).__name__, "error_message": str(exc)[:500]})
    results = deduplicate_results(results)
    write_reports(results, errors)
    return {"dry_run": False, "results": len(results), "gold": sum(1 for item in results if item.gold), "errors": len(errors)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Enterprise multiportal agentic job extraction.")
    parser.add_argument("--sources", nargs="*", default=list(SOURCE_URLS))
    parser.add_argument("--execute-network", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(run_enterprise_extraction(sources=args.sources, execute_network=args.execute_network, max_jobs=args.max_jobs, max_pages=args.max_pages), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
