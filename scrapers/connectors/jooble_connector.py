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

from agents.visual_analytics_labor_agent import AgentExtractionResult, BronzeEvidence, SilverEvidence, detect_language  # noqa: E402
from graduate_intelligence_platform.backend.app.academic_job_acquisition import source_plan_for  # noqa: E402
from ml.labor.semantic_job_skill_extractor import extract_semantic_job_skills, semantic_skills_to_dict  # noqa: E402
from ml.relevance.contextual_job_relevance_engine import result_to_dict, score_contextual_relevance  # noqa: E402
from scrapers.connectors.base import compact_text  # noqa: E402
from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text  # noqa: E402

REPORT_PATH = ROOT_DIR / "outputs" / "jooble_extraction_report.md"
SKILL_REPORT_PATH = ROOT_DIR / "outputs" / "jooble_skill_report.md"

DEFAULT_JOOBLE_API_URL = "https://jooble.org/api"
DEFAULT_JOOBLE_LOCATION = "Colombia"


@dataclass(frozen=True)
class JoobleNormalizedJob:
    source_name: str
    source_job_id: str
    title: str
    company: str
    location: str
    salary: str
    job_type: str
    description: str
    external_url: str
    date_updated: str
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


def validate_jooble_job(job: dict[str, Any]) -> tuple[str, bool, str]:
    reasons: list[str] = []
    title = compact_text(job.get("title"))
    company = compact_text(job.get("company"))
    description = compact_text(job.get("description"))
    link = compact_text(job.get("external_url"))
    if not title:
        reasons.append("missing_title")
    if not company:
        reasons.append("missing_company")
    if not description:
        reasons.append("missing_description")
    if len(description) < 40:
        reasons.append("short_description_snippet")
    if not link.startswith(("http://", "https://")):
        reasons.append("missing_valid_url")
    if reasons:
        return "unknown", False, ";".join(reasons)
    return "job_posting", True, ""


def normalize_jooble_job(payload: dict[str, Any]) -> JoobleNormalizedJob:
    source_job_id = compact_text(str(payload.get("id") or payload.get("job_id") or ""))
    title = compact_text(payload.get("title"))
    company = compact_text(payload.get("company"))
    location = compact_text(payload.get("location"))
    description = compact_text(payload.get("snippet") or payload.get("description"))
    link = compact_text(payload.get("link") or payload.get("url"))
    validation_payload = {
        "title": title,
        "company": company,
        "description": description,
        "external_url": link,
    }
    document_type, is_real, invalid_reason = validate_jooble_job(validation_payload)
    hsh = _stable_hash("jooble", source_job_id, title, company, location, description, link)
    return JoobleNormalizedJob(
        source_name="jooble",
        source_job_id=source_job_id,
        title=title,
        company=company,
        location=location,
        salary=compact_text(payload.get("salary")),
        job_type=compact_text(payload.get("type")),
        description=description,
        external_url=link,
        date_updated=compact_text(payload.get("updated")),
        raw_json=payload,
        content_hash=hsh,
        document_type=document_type,
        is_real_job_posting=is_real,
        invalid_job_reason=invalid_reason,
    )


def jooble_job_to_agent_result(job: JoobleNormalizedJob, search_context: dict[str, Any] | None = None) -> AgentExtractionResult:
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
        source_url=job.external_url,
        raw_html="",
        raw_text=raw_text,
        raw_json=job.raw_json,
        extraction_timestamp=datetime.now(UTC).isoformat(),
        page_title=job.title,
        http_status=200,
        extraction_method="jooble_rest_api",
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
        "search_context": search_context or {},
        "salary": job.salary,
        "job_type": job.job_type,
        "date_updated": job.date_updated,
    }
    silver = SilverEvidence(
        source_name=job.source_name,
        source_url=job.external_url,
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
        rejection_reason=job.invalid_job_reason or "silver_only_jooble_api",
        accepted_for_gold=False,
        parser_version="jooble_rest_api_v1",
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


class JoobleConnector:
    source_name = "jooble"

    def __init__(self, *, api_key: str | None = None, api_url: str | None = None, source_plan: dict | None = None) -> None:
        _load_environment()
        self.api_key = api_key or os.getenv("JOOBLE_API_KEY", "")
        self.api_url = (api_url or os.getenv("JOOBLE_API_URL", DEFAULT_JOOBLE_API_URL)).rstrip("/")
        self.session = requests.Session()
        self.source_plan = source_plan_for(source_plan, "jooble") if source_plan is not None else {"keywords": [], "roles": [], "families": [], "query": ""}

    def credentials_available(self) -> bool:
        return bool(self.api_key)

    def _endpoint(self) -> str:
        return f"{self.api_url}/{self.api_key}"

    def fetch_jobs(
        self,
        *,
        execute_network: bool = False,
        max_jobs: int = 100,
        keywords: str | None = None,
        location: str | None = None,
        result_on_page: int = 20,
        radius: str = "80",
    ) -> dict[str, Any]:
        if not self.credentials_available():
            result = {"source_status": "credentials_missing", "jobs": [], "errors": [{"error_type": "credentials_missing"}]}
            write_jooble_reports(result)
            return result
        if not execute_network:
            result = {
                "source_status": "dry_run",
                "jobs": [],
                "errors": [],
                "api_url_configured": bool(self.api_url),
                "keywords": keywords or os.getenv("JOOBLE_KEYWORDS") or query or plugin_search_query(),
                "location": location or os.getenv("JOOBLE_LOCATION", DEFAULT_JOOBLE_LOCATION),
            }
            write_jooble_reports(result)
            return result

        jobs: list[JoobleNormalizedJob] = []
        errors: list[dict[str, Any]] = []
        page = 1
        per_page = max(1, min(result_on_page, 50))
        plan_keywords = [str(item).strip() for item in (self.source_plan.get("keywords") or []) if str(item).strip()]
        plan_roles = [str(item).strip() for item in (self.source_plan.get("roles") or []) if str(item).strip()]
        if query is None:
            query = self.source_plan.get("query") or " OR ".join([*plan_keywords, *plan_roles]) or plugin_search_query()
        keywords = keywords or query or os.getenv("JOOBLE_KEYWORDS") or plugin_search_query()
        location = location or os.getenv("JOOBLE_LOCATION", DEFAULT_JOOBLE_LOCATION)
        while len(jobs) < max_jobs:
            payload = {
                "keywords": keywords,
                "location": location,
                "radius": radius,
                "page": str(page),
                "ResultOnPage": str(min(per_page, max_jobs - len(jobs))),
                "companysearch": "false",
            }
            try:
                response = self.session.post(self._endpoint(), json=payload, timeout=30)
                if response.status_code in {403, 404, 429}:
                    errors.append({"error_type": f"http_{response.status_code}", "rate_limited": response.status_code == 429})
                    break
                response.raise_for_status()
                data = response.json()
                page_jobs = data.get("jobs") or []
                jobs.extend(normalize_jooble_job({**item, "search_context": {"query": query, "search_plan": self.source_plan}}) for item in page_jobs if isinstance(item, dict))
                if not page_jobs or len(jobs) >= int(data.get("totalCount") or 0):
                    break
                page += 1
            except Exception as exc:  # pragma: no cover - live API behavior
                errors.append({"error_type": type(exc).__name__, "message": str(exc)[:500]})
                break
        result = {"source_status": "ok" if not errors else "partial_error", "jobs": jobs[:max_jobs], "errors": errors}
        write_jooble_reports(result)
        return result

    def fetch_agent_results(self, **kwargs: Any) -> tuple[list[AgentExtractionResult], dict[str, Any]]:
        result = self.fetch_jobs(**kwargs)
        jobs = result.get("jobs", [])
        agent_results = [jooble_job_to_agent_result(job, job.raw_json.get("search_context") if isinstance(job.raw_json, dict) else None) for job in jobs if isinstance(job, JoobleNormalizedJob)]
        return agent_results, {key: value for key, value in result.items() if key != "jobs"} | {"jobs": len(agent_results)}


def write_jooble_reports(result: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    jobs = [job for job in result.get("jobs", []) if isinstance(job, JoobleNormalizedJob)]
    valid = [job for job in jobs if job.is_real_job_posting]
    invalid = [job for job in jobs if not job.is_real_job_posting]
    title_counts = Counter(job.title for job in valid)
    company_counts = Counter(job.company for job in valid)
    location_counts = Counter(job.location for job in valid)
    lines = [
        "# Jooble API Extraction Report",
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
        "## Ubicaciones",
        *[f"- {location}: {count}" for location, count in location_counts.most_common(10)],
    ]
    if invalid:
        lines.extend(["", "## Invalidos", *[f"- {job.title or 'sin titulo'}: {job.invalid_job_reason}" for job in invalid[:20]]])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    skill_counts: Counter[str] = Counter()
    for job in valid:
        for item in extract_semantic_job_skills(title=job.title, description=job.description, evidence_source_type="job_evidence"):
            skill_counts[item.skill] += 1
    skill_lines = [
        "# Jooble API Skill Report",
        "",
        f"- Jobs validos analizados: {len(valid)}",
        "",
        "## Skills detectadas",
        *[f"- {skill}: {count}" for skill, count in skill_counts.most_common(50)],
    ]
    SKILL_REPORT_PATH.write_text("\n".join(skill_lines) + "\n", encoding="utf-8")


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    payload = dict(result)
    payload["jobs"] = [job.__dict__ for job in result.get("jobs", []) if isinstance(job, JoobleNormalizedJob)]
    return payload


if __name__ == "__main__":
    connector = JoobleConnector()
    print(json.dumps(public_result(connector.fetch_jobs(execute_network=False)), indent=2, ensure_ascii=False))
