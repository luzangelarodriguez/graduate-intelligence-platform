from __future__ import annotations

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
    raise KeyError(source)
