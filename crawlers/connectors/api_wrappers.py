from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from graduate_intelligence_platform.backend.app.academic_job_acquisition import get_academic_search_intelligence, source_plan_for  # noqa: E402
from agents.agentic_job_extractor import EnterpriseAgenticJobExtractor  # noqa: E402
from agents.visual_analytics_labor_agent import AgentExtractionResult  # noqa: E402
from scrapers.connectors.criminology_labor_connector import criminology_source_keys, make_criminology_connector  # noqa: E402
from scrapers.connectors.elempleo_connector import ElempleoConnector  # noqa: E402
from scrapers.connectors.findjobit_connector import FindJobITConnector  # noqa: E402
from scrapers.connectors.hireline_connector import HirelineConnector  # noqa: E402
from scrapers.connectors.indeed_partner_connector import IndeedPartnerConnector  # noqa: E402
from scrapers.connectors.jooble_connector import JoobleConnector  # noqa: E402
from scrapers.connectors.ticjob_connector import TicjobConnector  # noqa: E402
from scrapers.sources.computrabajo_scraper import scrape_jobs as _computrabajo_scrape  # noqa: E402
from scrapers.sources.magneto_api_scraper import scrape_jobs as _magneto_scrape  # noqa: E402
from scrapers.sources.torre_scraper import scrape_jobs as _torre_scrape  # noqa: E402
from scrapers.sources.spe_scraper import scrape_jobs as _spe_scrape  # noqa: E402


class ScraperAdapterCrawler:
    """Wraps a scrapers/sources scrape_jobs() function for use in the agent pipeline."""

    def __init__(self, scrape_fn: Any, source_name: str, *, source_plan: dict[str, Any] | None = None) -> None:
        self.scrape_fn = scrape_fn
        self.source_name = source_name
        self.source_plan = source_plan or {}
        self.extractor = EnterpriseAgenticJobExtractor()

    def run(self, *, execute_network: bool = False) -> tuple[list[AgentExtractionResult], list[dict[str, str]]]:
        if not execute_network:
            return [], []
        keywords = self.source_plan.get("keywords") or []
        query = (
            self.source_plan.get("query_es")
            or self.source_plan.get("query")
            or (" ".join(str(k) for k in keywords[:3]) if keywords else "analista datos")
        )
        try:
            raw_jobs = self.scrape_fn(query) or []
        except Exception as exc:
            return [], [{"source": self.source_name, "error_type": "scraper_error", "error_message": str(exc)}]
        results: list[AgentExtractionResult] = []
        for job in raw_jobs:
            if not isinstance(job, dict):
                continue
            html = (
                "<html><body><main>"
                f"<h1>{job.get('title', '')}</h1>"
                f"<div class='company'>{job.get('company', '')}</div>"
                f"<div class='location'>{job.get('location', '')}</div>"
                f"<article class='description'>{job.get('description', '')}</article>"
                "</main></body></html>"
            )
            result = self.extractor.inspect_detail_html(
                html=html,
                source_name=self.source_name,
                source_url=str(job.get("url") or job.get("source_url") or ""),
                fallback_title=str(job.get("title") or ""),
            )
            results.append(result)
        return results, []


class StructuredConnectorCrawler:
    def __init__(self, connector: Any, source_name: str, *, source_plan: dict[str, Any] | None = None) -> None:
        self.connector = connector
        self.source_name = source_name
        self.source_plan = source_plan or {}
        self.extractor = EnterpriseAgenticJobExtractor()

    def run(self, *, execute_network: bool = False) -> tuple[list[AgentExtractionResult], list[dict[str, str]]]:
        jobs, errors = self.connector.fetch_jobs(execute_network=execute_network)
        results: list[AgentExtractionResult] = []
        for job in jobs:
            html = '<html><body><main>'
            html += f'<h1>{job.title}</h1>'
            html += f"<div class='company'>{job.company}</div>"
            html += f"<div class='location'>{job.location}</div>"
            html += f"<article class='description'>{job.description}</article>"
            html += '</main></body></html>'
            result = self.extractor.inspect_detail_html(
                html=html,
                source_name=job.source_name,
                source_url=job.source_url,
                fallback_title=job.title,
            )
            contextual = dict(result.silver.contextual or {})
            if job.raw:
                contextual.update(job.raw)
            if self.source_plan:
                contextual.setdefault('search_context', {})
                contextual['search_context'].update(self.source_plan)
            result.silver.contextual.update(contextual)
            results.append(result)
        return results, [{"source": item.get("source", self.source_name), "error_type": item.get("error_type", "error"), "error_message": item.get("error_message", "")} for item in errors]


class ScraperAdapterCrawler:
    """Adapts a scrape_jobs(query) → list[dict] function to the crawler protocol."""

    def __init__(self, scrape_fn: Any, source_name: str, *, source_plan: dict[str, Any] | None = None) -> None:
        self.scrape_fn = scrape_fn
        self.source_name = source_name
        self.source_plan = source_plan or {}
        self.extractor = EnterpriseAgenticJobExtractor()

    def run(self, *, execute_network: bool = False) -> tuple[list[AgentExtractionResult], list[dict[str, str]]]:
        if not execute_network:
            return [], []
        # Prefer Spanish-first query for Colombian portals
        query: str = (
            self.source_plan.get("query_es")
            or self.source_plan.get("query")
            or " ".join((self.source_plan.get("keywords") or [])[:3])
            or "analista datos"
        )
        try:
            raw_jobs: list[dict[str, Any]] = self.scrape_fn(query) or []
        except Exception as exc:
            return [], [{"source": self.source_name, "error_type": "scraper_error", "error_message": str(exc)}]
        results: list[AgentExtractionResult] = []
        for job in raw_jobs:
            title = str(job.get("title") or job.get("cargo") or "")
            company = str(job.get("company") or job.get("empresa") or "")
            location = str(job.get("location") or job.get("ubicacion") or "Colombia")
            description = str(job.get("description") or job.get("descripcion") or "")
            url = str(job.get("url") or job.get("source_url") or "")
            html = (
                f"<html><body><main>"
                f"<h1>{title}</h1>"
                f"<div class='company'>{company}</div>"
                f"<div class='location'>{location}</div>"
                f"<article class='description'>{description}</article>"
                f"</main></body></html>"
            )
            result = self.extractor.inspect_detail_html(
                html=html,
                source_name=self.source_name,
                source_url=url,
                fallback_title=title,
            )
            if self.source_plan:
                result.silver.contextual.setdefault("search_context", {})
                result.silver.contextual["search_context"].update(self.source_plan)
            results.append(result)
        return results, []


class ComputrabajoAdapterCrawler:
    """Computrabajo-specific adapter: iterates search_terms, deduplicates by content hash."""

    def __init__(self, *, source_plan: dict[str, Any] | None = None) -> None:
        self.source_plan = source_plan or {}
        self.extractor = EnterpriseAgenticJobExtractor()

    def run(self, *, execute_network: bool = False) -> tuple[list[AgentExtractionResult], list[dict[str, str]]]:
        if not execute_network:
            return [], []
        search_terms: list[str] = list(self.source_plan.get("search_terms") or [])
        if not search_terms:
            fallback = (
                self.source_plan.get("query_es")
                or self.source_plan.get("query")
                or "analista datos"
            )
            search_terms = [fallback]
        seen_hashes: set[str] = set()
        results: list[AgentExtractionResult] = []
        errors: list[dict[str, str]] = []
        for term in search_terms:
            try:
                raw_jobs: list[dict[str, Any]] = ct_scrape(term) or []
            except Exception as exc:
                errors.append({"source": "computrabajo", "error_type": "scraper_error", "error_message": str(exc)})
                continue
            for job in raw_jobs:
                title = str(job.get("title") or job.get("cargo") or "")
                description = str(job.get("description") or job.get("descripcion") or "")
                content_hash = hashlib.md5(f"{title}|{description[:120]}".encode()).hexdigest()
                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)
                company = str(job.get("company") or job.get("empresa") or "")
                location = str(job.get("location") or job.get("ubicacion") or "Colombia")
                url = str(job.get("url") or job.get("source_url") or "")
                html = (
                    f"<html><body><main>"
                    f"<h1>{title}</h1>"
                    f"<div class='company'>{company}</div>"
                    f"<div class='location'>{location}</div>"
                    f"<article class='description'>{description}</article>"
                    f"</main></body></html>"
                )
                result = self.extractor.inspect_detail_html(
                    html=html,
                    source_name="computrabajo",
                    source_url=url,
                    fallback_title=title,
                )
                if self.source_plan:
                    result.silver.contextual.setdefault("search_context", {})
                    result.silver.contextual["search_context"].update(self.source_plan)
                results.append(result)
        return results, errors


def _default_search_intelligence() -> dict[str, Any]:
    try:
        return get_academic_search_intelligence()
    except Exception:
        return {"crawler_plans": {}}


def make_connector(source: str, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict[str, Any] | None = None):
    source = source.casefold()
    if source == "indeed":
        source = "indeed_partner"
    intelligence = search_intelligence or _default_search_intelligence()
    plan = source_plan_for(intelligence.get('crawler_plans'), source)
    if source == "indeed_partner":
        return IndeedPartnerConnector(source_plan=plan)
    if source == "jooble":
        return JoobleConnector(source_plan=plan)
    if source == "ticjob":
        return StructuredConnectorCrawler(TicjobConnector(max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), "ticjob", source_plan=plan)
    if source == "elempleo":
        return StructuredConnectorCrawler(ElempleoConnector(max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), "elempleo", source_plan=plan)
    if source == "hireline":
        return StructuredConnectorCrawler(HirelineConnector(max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), "hireline", source_plan=plan)
    if source == "findjobit":
        return StructuredConnectorCrawler(FindJobITConnector(max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), "findjobit", source_plan=plan)
    if source in criminology_source_keys() or source in {"un", "uncareers", "fiscalia", "policia", "policia_nacional_colombia"}:
        return StructuredConnectorCrawler(make_criminology_connector(source, max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), source, source_plan=plan)
    if source == "computrabajo":
        return ScraperAdapterCrawler(_computrabajo_scrape, "computrabajo", source_plan=plan)
    if source == "magneto":
        return ScraperAdapterCrawler(_magneto_scrape, "magneto", source_plan=plan)
    if source == "torre":
        return ScraperAdapterCrawler(_torre_scrape, "torre", source_plan=plan)
    if source == "spe":
        return ScraperAdapterCrawler(_spe_scrape, "spe", source_plan=plan)
    raise KeyError(source)
