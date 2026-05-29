from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.visual_analytics_labor_agent import (  # noqa: E402
    AgentExtractionResult,
    BronzeEvidence,
    SilverEvidence,
    content_hash,
    detect_language,
)
from ml.labor.semantic_job_skill_extractor import extract_semantic_job_skills, semantic_skills_to_dict  # noqa: E402
from ml.relevance.contextual_job_relevance_engine import result_to_dict, score_contextual_relevance  # noqa: E402
from scrapers.connectors.base import compact_text  # noqa: E402
from scrapers.connectors.indeed_publisher_plugin_config import plugin_search_query, write_publisher_plugin_report  # noqa: E402
from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text  # noqa: E402

REPORT_PATH = ROOT_DIR / "outputs" / "indeed_partner_extraction_report.md"
SKILL_REPORT_PATH = ROOT_DIR / "outputs" / "indeed_partner_skill_report.md"

DEFAULT_QUERY = "Data Analyst OR Business Intelligence OR Power BI OR SQL OR Analytics"
GRAPHQL_QUERY = """
query FindEmployerJobsPartner($input: FindEmployerJobsPartnerInput!) {
  findEmployerJobsPartner(input: $input) {
    pageInfo {
      endCursor
      hasNextPage
    }
    edges {
      cursor
      node {
        id
        jobData {
          title
          dateCreated
          description
          company
          salary {
            period
            maximumMinor
            minimumMinor
            currency
            maximumMajor
            minimumMajor
            basePaySpecified
          }
          jobLocation {
            countryCode
            city
            postalCode
            fullAddress
          }
          externalJobPageUrl
          externalPostingMetadata {
            jobPostingId
            jobRequisitionId
            campaignCategories
            rawInputLocation
            isIntegratedJob
          }
          datePostedOnIndeed
        }
        managementUrls {
          viewJob
        }
      }
    }
  }
}
""".strip()


@dataclass(frozen=True)
class IndeedNormalizedJob:
    source_name: str
    source_job_id: str
    title: str
    company: str
    location: str
    country: str
    city: str
    salary_min: float | None
    salary_max: float | None
    salary_currency: str
    salary_period: str
    description: str
    external_url: str
    indeed_view_url: str
    date_created: str
    date_posted: str
    raw_json: dict[str, Any]
    content_hash: str
    document_type: str
    is_real_job_posting: bool
    invalid_job_reason: str


def _load_environment() -> None:
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def _stable_hash(*parts: str) -> str:
    return hashlib.sha256(normalize_text(" ".join(parts)).encode("utf-8")).hexdigest()


def _salary_major(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def _extract_connection(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    result = data.get("findEmployerJobsPartner") or payload.get("findEmployerJobsPartner") or {}
    if isinstance(result, dict) and "jobs" in result and isinstance(result["jobs"], dict):
        return result["jobs"]
    return result if isinstance(result, dict) else {}


def _extract_nodes(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    connection = _extract_connection(payload)
    page_info = connection.get("pageInfo") or {}
    nodes: list[dict[str, Any]] = []
    if isinstance(connection.get("edges"), list):
        for edge in connection["edges"]:
            node = edge.get("node") if isinstance(edge, dict) else None
            if isinstance(node, dict):
                nodes.append(node)
    elif isinstance(connection.get("nodes"), list):
        nodes = [node for node in connection["nodes"] if isinstance(node, dict)]
    elif isinstance(connection.get("results"), list):
        nodes = [node for node in connection["results"] if isinstance(node, dict)]
    return nodes, page_info


def validate_indeed_job(job: dict[str, Any]) -> tuple[str, bool, str]:
    reasons: list[str] = []
    title = compact_text(job.get("title"))
    company = compact_text(job.get("company"))
    description = compact_text(job.get("description"))
    external_url = compact_text(job.get("external_url"))
    indeed_view_url = compact_text(job.get("indeed_view_url"))
    if not title:
        reasons.append("missing_title")
    if not company:
        reasons.append("missing_company")
    if not description:
        reasons.append("missing_description")
    if len(description) <= 100:
        reasons.append("short_description")
    if not (external_url.startswith(("http://", "https://")) or indeed_view_url.startswith(("http://", "https://"))):
        reasons.append("missing_valid_url")
    if reasons:
        return "unknown", False, ";".join(reasons)
    return "job_posting", True, ""


def normalize_indeed_node(node: dict[str, Any]) -> IndeedNormalizedJob:
    job_data = node.get("jobData") or node.get("job_data") or node
    salary = job_data.get("salary") or {}
    location_data = job_data.get("jobLocation") or job_data.get("job_location") or {}
    metadata = job_data.get("externalPostingMetadata") or job_data.get("external_posting_metadata") or {}
    source_job_id = compact_text(str(node.get("id") or metadata.get("jobPostingId") or metadata.get("jobRequisitionId") or ""))
    title = compact_text(job_data.get("title"))
    company = compact_text(job_data.get("company"))
    description = compact_text(job_data.get("description"))
    external_url = compact_text(job_data.get("externalJobPageUrl") or job_data.get("external_url"))
    indeed_view_url = compact_text((node.get("managementUrls") or {}).get("viewJob") or (node.get("management_urls") or {}).get("view_job"))
    city = compact_text(location_data.get("city"))
    country = compact_text(location_data.get("countryCode"))
    full_address = compact_text(location_data.get("fullAddress") or metadata.get("rawInputLocation"))
    location = full_address or ", ".join([item for item in (city, country) if item])
    raw = {"id": node.get("id"), "jobData": job_data, "managementUrls": node.get("managementUrls") or {}}
    hsh = _stable_hash("indeed_partner", source_job_id, title, company, description, external_url, indeed_view_url)
    validation_payload = {
        "title": title,
        "company": company,
        "description": description,
        "external_url": external_url,
        "indeed_view_url": indeed_view_url,
    }
    document_type, is_real, invalid_reason = validate_indeed_job(validation_payload)
    return IndeedNormalizedJob(
        source_name="indeed_partner",
        source_job_id=source_job_id,
        title=title,
        company=company,
        location=location,
        country=country,
        city=city,
        salary_min=_salary_major(salary.get("minimumMajor")),
        salary_max=_salary_major(salary.get("maximumMajor")),
        salary_currency=compact_text(salary.get("currency")),
        salary_period=compact_text(salary.get("period")),
        description=description,
        external_url=external_url,
        indeed_view_url=indeed_view_url,
        date_created=compact_text(job_data.get("dateCreated")),
        date_posted=compact_text(job_data.get("datePostedOnIndeed")),
        raw_json=raw,
        content_hash=hsh,
        document_type=document_type,
        is_real_job_posting=is_real,
        invalid_job_reason=invalid_reason,
    )


def indeed_job_to_agent_result(job: IndeedNormalizedJob) -> AgentExtractionResult:
    source_url = job.external_url or job.indeed_view_url
    raw_text = compact_text(f"{job.title} {job.company} {job.location} {job.description}")
    semantic_items = extract_semantic_job_skills(title=job.title, description=job.description, evidence_source_type="job_evidence")
    job_skills = [item.skill for item in semantic_items] if job.is_real_job_posting else []
    contextual = score_contextual_relevance(
        title=job.title,
        description=job.description,
        tags=[],
        skills=job_skills,
        technologies=job_skills,
        document_type=job.document_type,
        evidence_source_type="job_evidence" if job.is_real_job_posting else "unknown",
        is_real_job_posting=job.is_real_job_posting,
    )
    bronze = BronzeEvidence(
        source_name=job.source_name,
        source_url=source_url,
        raw_html="",
        raw_text=raw_text,
        raw_json=job.raw_json,
        extraction_timestamp=datetime.now(UTC).isoformat(),
        page_title=job.title,
        http_status=200,
        extraction_method="indeed_partner_graphql",
        content_hash=job.content_hash,
        detected_language=detect_language(raw_text),
    )
    tools = [item.skill for item in semantic_items if item.skill_type in {"tool", "platform"}]
    cloud = [item.skill for item in semantic_items if item.skill_type == "cloud"]
    frameworks = [item.skill for item in semantic_items if item.skill_type in {"framework", "emerging_skill"}]
    contextual_payload = {
        **result_to_dict(contextual),
        "semantic_skill_evidence": semantic_skills_to_dict(semantic_items),
        "source_job_id": job.source_job_id,
        "salary": {
            "min": job.salary_min,
            "max": job.salary_max,
            "currency": job.salary_currency,
            "period": job.salary_period,
        },
        "indeed_view_url": job.indeed_view_url,
    }
    silver = SilverEvidence(
        source_name=job.source_name,
        source_url=source_url,
        normalized_title=job.title,
        normalized_company=job.company,
        normalized_location=job.location,
        normalized_description=job.description,
        extracted_skills=job_skills,
        extracted_tools=tools if job.is_real_job_posting else [],
        extracted_cloud=cloud if job.is_real_job_posting else [],
        extracted_frameworks=frameworks if job.is_real_job_posting else [],
        analytics_density=contextual.analytics_density,
        contextual_relevance_score=contextual.contextual_relevance_score,
        semantic_score=contextual.semantic_similarity,
        rejection_reason=job.invalid_job_reason or "silver_only_indeed_partner",
        accepted_for_gold=False,
        parser_version="indeed_partner_graphql_v1",
        content_hash=job.content_hash,
        contextual=contextual_payload,
        document_type=job.document_type,
        evidence_source_type="job_evidence" if job.is_real_job_posting else "unknown",
        is_real_job_posting=job.is_real_job_posting,
        invalid_job_reason=job.invalid_job_reason,
        job_evidence_skills=job_skills,
        portal_taxonomy_skills=[],
    )
    return AgentExtractionResult(bronze=bronze, silver=silver, gold=None)


class IndeedPartnerConnector:
    source_name = "indeed_partner"

    def __init__(self, *, api_url: str | None = None, access_token: str | None = None, source_id: str | None = None) -> None:
        _load_environment()
        self.api_url = api_url or os.getenv("INDEED_API_URL", "")
        self.access_token = access_token or os.getenv("INDEED_ACCESS_TOKEN", "")
        self.source_id = source_id or os.getenv("INDEED_SOURCE_ID", "")
        self.session = requests.Session()

    def credentials_available(self) -> bool:
        return bool(self.api_url and self.access_token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _variables(self, *, first: int, after: str | None, query: str) -> dict[str, Any]:
        input_payload: dict[str, Any] = {"first": first, "query": query}
        if after:
            input_payload["after"] = after
        if self.source_id:
            input_payload["sourceId"] = self.source_id
        return {"input": input_payload}

    def fetch_jobs(
        self,
        *,
        execute_network: bool = False,
        max_jobs: int = 100,
        query: str = DEFAULT_QUERY,
        page_size: int = 25,
    ) -> dict[str, Any]:
        if not self.credentials_available():
            result = {
                "source_status": "credentials_missing",
                "jobs": [],
                "errors": [{"error_type": "credentials_missing"}],
                "publisher_plugin": write_publisher_plugin_report(),
            }
            write_indeed_reports(result)
            return result
        if not execute_network:
            result = {
                "source_status": "dry_run",
                "jobs": [],
                "errors": [],
                "api_url_configured": bool(self.api_url),
                "source_id_configured": bool(self.source_id),
                "publisher_plugin": write_publisher_plugin_report(),
            }
            write_indeed_reports(result)
            return result

        jobs: list[IndeedNormalizedJob] = []
        errors: list[dict[str, Any]] = []
        after: str | None = None
        has_next = True
        if query == DEFAULT_QUERY:
            query = plugin_search_query()
        while has_next and len(jobs) < max_jobs:
            variables = self._variables(first=min(page_size, max_jobs - len(jobs)), after=after, query=query)
            try:
                response = self.session.post(
                    self.api_url,
                    headers=self._headers(),
                    json={"query": GRAPHQL_QUERY, "variables": variables},
                    timeout=30,
                )
                if response.status_code in {401, 403, 429}:
                    errors.append({"error_type": f"http_{response.status_code}", "rate_limited": response.status_code == 429})
                    break
                response.raise_for_status()
                payload = response.json()
                if payload.get("errors"):
                    errors.append({"error_type": "graphql_errors", "message": str(payload.get("errors"))[:500]})
                nodes, page_info = _extract_nodes(payload)
                jobs.extend(normalize_indeed_node(node) for node in nodes)
                has_next = bool(page_info.get("hasNextPage")) and bool(page_info.get("endCursor"))
                after = page_info.get("endCursor")
                if not nodes:
                    break
            except Exception as exc:  # pragma: no cover - live API behavior
                errors.append({"error_type": type(exc).__name__, "message": str(exc)[:500]})
                break
        result = {"source_status": "ok" if not errors else "partial_error", "jobs": jobs[:max_jobs], "errors": errors}
        write_indeed_reports(result)
        return result

    def fetch_agent_results(self, **kwargs: Any) -> tuple[list[AgentExtractionResult], dict[str, Any]]:
        result = self.fetch_jobs(**kwargs)
        jobs = result.get("jobs", [])
        agent_results = [indeed_job_to_agent_result(job) for job in jobs if isinstance(job, IndeedNormalizedJob)]
        return agent_results, {key: value for key, value in result.items() if key != "jobs"} | {"jobs": len(agent_results)}


def write_indeed_reports(result: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    jobs = [job for job in result.get("jobs", []) if isinstance(job, IndeedNormalizedJob)]
    valid = [job for job in jobs if job.is_real_job_posting]
    invalid = [job for job in jobs if not job.is_real_job_posting]
    city_counts = Counter(job.city or job.location for job in valid)
    company_counts = Counter(job.company for job in valid)
    title_counts = Counter(job.title for job in valid)
    lines = [
        "# Indeed Partner Extraction Report",
        "",
        f"- Source status: {result.get('source_status')}",
        f"- Total jobs obtenidos: {len(jobs)}",
        f"- Jobs validos: {len(valid)}",
        f"- Jobs invalidos: {len(invalid)}",
        f"- Errores API: {len(result.get('errors', []))}",
        f"- Rate limit detectado: {any(error.get('rate_limited') for error in result.get('errors', []))}",
        "",
        "## Cargos principales",
        *[f"- {title}: {count}" for title, count in title_counts.most_common(10)],
        "",
        "## Empresas",
        *[f"- {company}: {count}" for company, count in company_counts.most_common(10)],
        "",
        "## Ciudades",
        *[f"- {city}: {count}" for city, count in city_counts.most_common(10)],
    ]
    if invalid:
        lines.extend(["", "## Invalidos", *[f"- {job.title or 'sin titulo'}: {job.invalid_job_reason}" for job in invalid[:20]]])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    skill_counts: Counter[str] = Counter()
    for job in valid:
        for item in extract_semantic_job_skills(title=job.title, description=job.description, evidence_source_type="job_evidence"):
            skill_counts[item.skill] += 1
    skill_lines = [
        "# Indeed Partner Skill Report",
        "",
        f"- Jobs validos analizados: {len(valid)}",
        "",
        "## Skills detectadas",
        *[f"- {skill}: {count}" for skill, count in skill_counts.most_common(50)],
    ]
    SKILL_REPORT_PATH.write_text("\n".join(skill_lines) + "\n", encoding="utf-8")


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    payload = dict(result)
    payload["jobs"] = [job.__dict__ for job in result.get("jobs", []) if isinstance(job, IndeedNormalizedJob)]
    return payload


if __name__ == "__main__":
    connector = IndeedPartnerConnector()
    print(json.dumps(public_result(connector.fetch_jobs(execute_network=False)), indent=2, ensure_ascii=False))
