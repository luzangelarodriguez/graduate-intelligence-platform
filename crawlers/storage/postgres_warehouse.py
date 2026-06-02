from __future__ import annotations

import json
import re
import sys
import unicodedata
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.visual_analytics_labor_agent import AgentExtractionResult  # noqa: E402
from backend.db import get_conn  # noqa: E402
from crawlers.core.data_quality import (  # noqa: E402
    build_quality_envelope,
    job_fingerprint,
    normalize_location,
    normalize_salary,
)
from ml.embeddings.embedding_service import DEFAULT_EMBEDDING_MODEL, encode_texts  # noqa: E402
from ml.labor.labor_skill_taxonomy_expanded import EXPANDED_SKILLS, normalize_text  # noqa: E402
from ml.labor.occupational_skill_cluster_engine import classify_skill_cluster  # noqa: E402

MIGRATION = ROOT_DIR / "database" / "migrations" / "015_labor_acquisition_warehouse.sql"
ENRICHMENT_MIGRATION = ROOT_DIR / "database" / "migrations" / "016_labor_intelligence_enrichment.sql"
ANALYTICS_DIR = ROOT_DIR / "outputs" / "analytics"

SOURCE_CONFIDENCE = {
    "indeed_partner": 0.92,
    "jooble": 0.86,
    "linkedin": 0.82,
    "ticjob": 0.78,
    "elempleo": 0.76,
    "hireline": 0.74,
    "findjobit": 0.70,
}


@dataclass(frozen=True)
class CanonicalSkill:
    name: str
    category: str
    family: str
    alias: str


def load_environment() -> None:
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def _plain(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _norm_key(value: str | None) -> str:
    return normalize_text(value or "")


def _source_confidence(source: str) -> float:
    return SOURCE_CONFIDENCE.get(_norm_key(source), 0.68)


COMPANY_ALIASES = {
    "international business machines": "IBM",
    "ibm colombia": "IBM",
    "ibm": "IBM",
    "globant colombia": "Globant",
    "globant": "Globant",
    "accenture colombia": "Accenture",
    "accenture": "Accenture",
}


def normalize_company(value: str | None) -> tuple[str, float]:
    raw = _plain(value)
    if len(raw) > 90 or len(raw.split()) > 10 or re.search(
        r"\b(rol|requisitos|responsabilidades|condiciones laborales|salario|modalidad|experiencia)\b",
        raw,
        re.IGNORECASE,
    ):
        return "No especificada", 0.35
    if re.search(r"\b(importante empresa|empresa confidencial|confidencial)\b", raw, re.IGNORECASE):
        return "No especificada", 0.45
    if not raw or _norm_key(raw) in {"no especificada", "unknown", "na", "n a"}:
        return "No especificada", 0.0
    normalized = re.sub(r"\b(s\.?a\.?s\.?|s\.?a\.?|ltda\.?|inc\.?|corp\.?|colombia|latam)\b", "", raw, flags=re.IGNORECASE)
    normalized = _plain(normalized).strip(" .,-")
    key = _norm_key(normalized)
    canonical = COMPANY_ALIASES.get(key) or normalized
    confidence = 0.92 if key in COMPANY_ALIASES else 0.78
    if len(canonical.split()) <= 1:
        confidence = max(confidence, 0.84)
    return canonical or raw, round(confidence, 4)


def semantic_title_family(title: str, skills: list[str]) -> tuple[str, str, float]:
    text = _norm_key(" ".join([title, *skills]))
    if any(term in text for term in ("analytics engineer", "data engineer", "etl", "pipeline", "warehouse", "spark", "databricks")):
        return "Analytics Engineering", "Data Engineer + BI + ELT", 0.82
    if any(term in text for term in ("power bi", "tableau", "dashboard", "reporting", "kpi", "bi analyst")):
        return "BI & Visualization", "BI + Visualization + Reporting", 0.80
    if any(term in text for term in ("machine learning", "ai", "mlops", "predictive")):
        return "AI Analytics", "Analytics + AI/ML", 0.74
    if any(term in text for term in ("governance", "quality", "lineage", "metadata")):
        return "Data Governance", "Governance + Quality", 0.72
    return "Enterprise Analytics", "Hybrid Analytics Role", 0.58


def duplicate_group_key(*, title: str, company: str, location: str, skills: list[str]) -> str:
    skill_key = " ".join(sorted(_norm_key(skill) for skill in skills[:8]))
    payload = _norm_key("|".join([title, company, location, skill_key]))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _taxonomy_index() -> dict[str, CanonicalSkill]:
    index: dict[str, CanonicalSkill] = {}
    for canonical, definition in EXPANDED_SKILLS.items():
        category = str(definition.get("category") or "Unknown")
        family = category
        aliases = list(definition.get("aliases") or [])
        aliases.append(canonical)
        for alias in aliases:
            index[_norm_key(str(alias))] = CanonicalSkill(
                name=canonical,
                category=category,
                family=family,
                alias=str(alias),
            )
    return index


TAXONOMY_INDEX = _taxonomy_index()


def canonicalize_skill(skill: str) -> CanonicalSkill:
    key = _norm_key(skill)
    if key in TAXONOMY_INDEX:
        return TAXONOMY_INDEX[key]
    name = _plain(skill)
    return CanonicalSkill(name=name, category="Unclassified", family="Unclassified", alias=name)


def infer_modality(text: str) -> str:
    value = _norm_key(text)
    if any(term in value for term in ("remoto", "remote", "trabajo remoto", "home office")):
        return "Remoto"
    if any(term in value for term in ("hibrido", "hybrid", "mixto")):
        return "Hibrido"
    if any(term in value for term in ("presencial", "onsite", "on site")):
        return "Presencial"
    return "No especificada"


def infer_seniority(text: str) -> str:
    value = _norm_key(text)
    if any(term in value for term in ("senior", "sr", "lider", "lead", "arquitecto", "architect")):
        return "Senior"
    if any(term in value for term in ("junior", "jr", "trainee", "practicante")):
        return "Junior"
    if any(term in value for term in ("semi senior", "semisenior", "mid", "intermedio")):
        return "Semi Senior"
    return "No especificado"


def infer_industry(text: str) -> str:
    value = _norm_key(text)
    if any(term in value for term in ("banco", "financ", "seguros", "riesgo")):
        return "Financiero"
    if any(term in value for term in ("salud", "health", "clinica")):
        return "Salud"
    if any(term in value for term in ("retail", "ecommerce", "comercio")):
        return "Retail"
    if any(term in value for term in ("educacion", "universidad", "academic")):
        return "Educacion"
    if any(term in value for term in ("tecnologia", "software", "analytics", "datos", "data")):
        return "Tecnologia y datos"
    return "No especificada"


def _upsert_lookup(cur: Any, table: str, key_column: str, value: str, extra: dict[str, Any] | None = None) -> int:
    extra = extra or {}
    columns = [key_column, *extra.keys()]
    values = [value, *extra.values()]
    placeholders = ", ".join(["%s"] * len(values))
    updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in extra)
    update_clause = f"DO UPDATE SET {updates}, updated_at = now()" if updates else f"DO UPDATE SET {key_column} = EXCLUDED.{key_column}"
    cur.execute(
        f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES ({placeholders})
        ON CONFLICT ({key_column}) {update_clause}
        RETURNING id
        """,
        values,
    )
    return int(cur.fetchone()["id"])


def _processing_stage(silver: Any) -> str:
    curation_level = str(getattr(silver, "curation_level", "") or silver.contextual.get("curation_level") or "candidate_job")
    if curation_level in {"gold_job", "curated_job", "probable_job"}:
        return curation_level
    return "candidate_job"


def _persistable_job(result: AgentExtractionResult) -> bool:
    silver = result.silver
    source_url = str(silver.source_url or result.bronze.source_url or "")
    hard_blocked = silver.document_type in {"portal_taxonomy", "filter_page", "category_page"} or source_url.startswith("javascript:")
    return not hard_blocked and source_url.startswith(("http://", "https://"))


def _persisted_title(result: AgentExtractionResult) -> str:
    silver = result.silver
    title = _plain(silver.normalized_title)
    if title:
        return title
    fallback = _plain(getattr(result.bronze, "page_title", ""))
    if fallback:
        return fallback[:180]
    fallback = _plain(getattr(result.bronze, "raw_text", ""))
    if fallback:
        return fallback[:180]
    return "Sin titulo"


def _persisted_description(result: AgentExtractionResult) -> str:
    silver = result.silver
    description = _plain(silver.normalized_description)
    if description:
        return description
    fallback = _plain(getattr(result.bronze, "raw_text", ""))
    if fallback:
        return fallback[:4000]
    fallback = _plain(getattr(result.bronze, "page_title", ""))
    if fallback:
        return fallback[:4000]
    return "Sin descripcion"


def _job_skills(result: AgentExtractionResult) -> list[tuple[CanonicalSkill, float, str]]:
    skills: dict[str, tuple[CanonicalSkill, float, str]] = {}
    contextual = result.silver.contextual or {}
    semantic_items = contextual.get("semantic_skill_evidence") or []
    for item in semantic_items:
        raw = str(item.get("skill") or item.get("normalized") or "")
        if not raw:
            continue
        canonical = canonicalize_skill(raw)
        confidence = float(item.get("confidence") or 0.7)
        section = str(item.get("section") or "description")
        current = skills.get(canonical.name)
        if current is None or confidence > current[1]:
            skills[canonical.name] = (canonical, round(min(confidence, 1.0), 4), section)
    for raw in result.silver.job_evidence_skills or result.silver.extracted_skills or []:
        canonical = canonicalize_skill(str(raw))
        current = skills.get(canonical.name)
        if current is None or 0.7 > current[1]:
            skills[canonical.name] = (canonical, 0.7, "description")
    for raw in result.silver.portal_taxonomy_skills or contextual.get("portal_taxonomy_skills") or []:
        canonical = canonicalize_skill(str(raw))
        current = skills.get(canonical.name)
        if current is None or 0.55 > current[1]:
            skills[canonical.name] = (canonical, 0.55, "taxonomy")
    return sorted(skills.values(), key=lambda item: item[1], reverse=True)


def _persist_embeddings(cur: Any, job_ids: list[int]) -> None:
    cur.execute(
        """
        SELECT j.id, j.title, j.description, j.company, j.semantic_title_family,
               COALESCE(json_agg(DISTINCT js.canonical_skill) FILTER (WHERE js.canonical_skill IS NOT NULL), '[]') AS skills
        FROM jobs j
        LEFT JOIN job_skills js ON js.job_id = j.id
        WHERE j.id = ANY(%s)
        GROUP BY j.id
        """,
        (job_ids,),
    )
    rows = cur.fetchall()
    job_texts = [
        " ".join([row["title"] or "", row["description"] or "", row["semantic_title_family"] or "", " ".join(row["skills"] or [])])
        for row in rows
    ]
    title_texts = [row["title"] or "" for row in rows]
    if rows:
        job_vectors = encode_texts(job_texts, model_name=DEFAULT_EMBEDDING_MODEL)
        title_vectors = encode_texts(title_texts, model_name=DEFAULT_EMBEDDING_MODEL)
        execute_values(
            cur,
            """
            INSERT INTO job_embeddings (job_id, embedding_scope, embedding_vector, model_version)
            VALUES %s
            ON CONFLICT (job_id, embedding_scope, model_version) DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                embedding_created_at = now()
            """,
            [
                (row["id"], scope, Json(vector), DEFAULT_EMBEDDING_MODEL)
                for row, job_vector, title_vector in zip(rows, job_vectors, title_vectors, strict=False)
                for scope, vector in (("job", job_vector), ("title", title_vector))
            ],
        )
    cur.execute("SELECT id, canonical_skill FROM canonical_skills")
    skill_rows = cur.fetchall()
    if skill_rows:
        skill_vectors = encode_texts([row["canonical_skill"] for row in skill_rows], model_name=DEFAULT_EMBEDDING_MODEL)
        execute_values(
            cur,
            """
            INSERT INTO skill_embeddings (canonical_skill_id, canonical_skill, embedding_vector, model_version)
            VALUES %s
            ON CONFLICT (canonical_skill, model_version) DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                embedding_created_at = now()
            """,
            [(row["id"], row["canonical_skill"], Json(vector), DEFAULT_EMBEDDING_MODEL) for row, vector in zip(skill_rows, skill_vectors, strict=False)],
        )
    cur.execute("SELECT id, company FROM companies WHERE normalized_company <> 'no especificada'")
    company_rows = cur.fetchall()
    if company_rows:
        company_vectors = encode_texts([row["company"] for row in company_rows], model_name=DEFAULT_EMBEDDING_MODEL)
        execute_values(
            cur,
            """
            INSERT INTO company_embeddings (company_id, embedding_vector, model_version)
            VALUES %s
            ON CONFLICT (company_id, model_version) DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                embedding_created_at = now()
            """,
            [(row["id"], Json(vector), DEFAULT_EMBEDDING_MODEL) for row, vector in zip(company_rows, company_vectors, strict=False)],
        )


def _refresh_duplicate_canonicals(cur: Any, job_ids: list[int]) -> None:
    cur.execute(
        """
        WITH ranked AS (
            SELECT duplicate_group_id, MIN(id) AS canonical_id, COUNT(*) AS total
            FROM jobs
            WHERE duplicate_group_id IS NOT NULL
            GROUP BY duplicate_group_id
        )
        UPDATE jobs j
        SET canonical_job_id = ranked.canonical_id,
            duplicate_confidence = CASE WHEN ranked.total > 1 THEN GREATEST(j.duplicate_confidence, 0.88) ELSE j.duplicate_confidence END
        FROM ranked
        WHERE j.duplicate_group_id = ranked.duplicate_group_id
          AND j.id = ANY(%s)
        """,
        (job_ids,),
    )


def _sanitize_company_values(cur: Any) -> None:
    company_id = _upsert_lookup(
        cur,
        "companies",
        "normalized_company",
        _norm_key("No especificada"),
        {"company": "No especificada", "original_company": "No especificada", "company_confidence_score": 0.0},
    )
    cur.execute(
        """
        UPDATE jobs
        SET company_id = %s,
            company = 'No especificada',
            normalized_company = 'No especificada',
            company_confidence_score = 0.35,
            updated_at = now()
        WHERE char_length(company) > 90
           OR company ~* '(rol:|requisitos:|responsabilidades:|condiciones laborales|modalidad de trabajo|salario:)'
        """,
        (company_id,),
    )


def _refresh_company_profiles(cur: Any) -> None:
    cur.execute("DELETE FROM company_skill_profiles")
    cur.execute("DELETE FROM company_cluster_profiles")
    cur.execute(
        """
        INSERT INTO company_skill_profiles (company_id, canonical_skill, skill_category, job_count, avg_confidence, last_seen_at)
        SELECT j.company_id, js.canonical_skill, js.skill_category, COUNT(DISTINCT j.id), AVG(js.confidence), now()
        FROM jobs j
        INNER JOIN job_skills js ON js.job_id = j.id
        WHERE j.company_id IS NOT NULL
        GROUP BY j.company_id, js.canonical_skill, js.skill_category
        ON CONFLICT (company_id, canonical_skill) DO UPDATE SET
            job_count = EXCLUDED.job_count,
            avg_confidence = EXCLUDED.avg_confidence,
            last_seen_at = now()
        """
    )
    cur.execute(
        """
        SELECT company_id, canonical_skill, skill_category, job_count
        FROM company_skill_profiles
        ORDER BY company_id, job_count DESC
        """
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in cur.fetchall():
        grouped[int(row["company_id"])].append(dict(row))
    rows = []
    for company_id, items in grouped.items():
        category_counts = Counter(item["skill_category"] for item in items for _ in range(int(item["job_count"] or 1)))
        dominant_cluster = category_counts.most_common(1)[0][0] if category_counts else "Enterprise Analytics"
        total_jobs = sum(int(item["job_count"] or 0) for item in items)
        maturity = "advanced" if total_jobs >= 20 else "growing" if total_jobs >= 6 else "emerging"
        top_skills = [item["canonical_skill"] for item in items[:10]]
        rows.append((company_id, dominant_cluster, total_jobs, maturity, Json(top_skills)))
    if rows:
        execute_values(
            cur,
            """
            INSERT INTO company_cluster_profiles (company_id, dominant_cluster, job_count, market_maturity, top_skills)
            VALUES %s
            ON CONFLICT (company_id, dominant_cluster) DO UPDATE SET
                job_count = EXCLUDED.job_count,
                market_maturity = EXCLUDED.market_maturity,
                top_skills = EXCLUDED.top_skills,
                updated_at = now()
            """,
            rows,
        )


def _refresh_emerging_skill_candidates(cur: Any) -> None:
    known = set(EXPANDED_SKILLS)
    cur.execute(
        """
        SELECT js.canonical_skill, COUNT(*) AS evidence_count
        FROM job_skills js
        GROUP BY js.canonical_skill
        """
    )
    rows = []
    for row in cur.fetchall():
        skill = row["canonical_skill"]
        if skill in known:
            continue
        evidence_count = int(row["evidence_count"] or 0)
        score = min(1.0, evidence_count / 10)
        rows.append((skill, _norm_key(skill), evidence_count, score, score, Json({"source": "job_skills"})))
    if rows:
        execute_values(
            cur,
            """
            INSERT INTO emerging_skill_candidates
                (candidate, normalized_candidate, evidence_count, growth_velocity, emergence_score, source_payload, last_seen_at)
            VALUES %s
            ON CONFLICT (candidate) DO UPDATE SET
                evidence_count = EXCLUDED.evidence_count,
                growth_velocity = EXCLUDED.growth_velocity,
                emergence_score = EXCLUDED.emergence_score,
                source_payload = EXCLUDED.source_payload,
                last_seen_at = now()
            """,
            rows,
            template="(%s, %s, %s, %s, %s, %s, now())",
        )


def persist_warehouse(
    results: list[AgentExtractionResult],
    *,
    correlation_id: str,
    sources: list[str],
    source_metrics: dict[str, Any] | None = None,
    errors: list[dict[str, str]] | None = None,
    manifest_path: str = "",
) -> dict[str, int | bool]:
    load_environment()
    source_metrics = source_metrics or {}
    errors = errors or []
    persistable_results = [result for result in results if _persistable_job(result)]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(MIGRATION.read_text(encoding="utf-8"))
            if ENRICHMENT_MIGRATION.exists():
                cur.execute(ENRICHMENT_MIGRATION.read_text(encoding="utf-8"))
            cur.execute(
                """
                INSERT INTO execution_runs (correlation_id, status, sources, execute_network, persist_enabled, manifest_path, metadata)
                VALUES (%s, 'running', %s, TRUE, TRUE, %s, %s)
                ON CONFLICT (correlation_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    sources = EXCLUDED.sources,
                    persist_enabled = EXCLUDED.persist_enabled,
                    manifest_path = EXCLUDED.manifest_path,
                    metadata = EXCLUDED.metadata
                """,
                (correlation_id, Json(sources), manifest_path, Json({"platform": "labor_acquisition"})),
            )
            for source, metric in source_metrics.items():
                cur.execute(
                    """
                    INSERT INTO crawl_metrics
                        (correlation_id, source, requests, successes, failures, blocked, avg_latency_ms, health_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (correlation_id, source) DO UPDATE SET
                        requests = EXCLUDED.requests,
                        successes = EXCLUDED.successes,
                        failures = EXCLUDED.failures,
                        blocked = EXCLUDED.blocked,
                        avg_latency_ms = EXCLUDED.avg_latency_ms,
                        health_score = EXCLUDED.health_score
                    """,
                    (
                        correlation_id,
                        source,
                        int(metric.get("requests") or 0),
                        int(metric.get("successes") or 0),
                        int(metric.get("failures") or 0),
                        int(metric.get("blocked") or 0),
                        float(metric.get("avg_latency_ms") or 0),
                        float(metric.get("health_score") or 0),
                    ),
                )
            if errors:
                execute_values(
                    cur,
                    """
                    INSERT INTO failed_jobs (correlation_id, source, error_type, error_message, source_url, payload)
                    VALUES %s
                    """,
                    [
                        (
                            correlation_id,
                            str(error.get("source") or "unknown"),
                            str(error.get("error_type") or "error"),
                            str(error.get("error_message") or "")[:1000],
                            str(error.get("source_url") or ""),
                            Json(error),
                        )
                        for error in errors
                    ],
                )
            jobs_upserted = 0
            skills_upserted = 0
            persisted_job_ids: list[int] = []
            for result in persistable_results:
                silver = result.silver
                persist_title = _persisted_title(result)
                persist_description = _persisted_description(result)
                text = " ".join([persist_title, persist_description, json.dumps(silver.contextual, ensure_ascii=False)])
                source_name = silver.source_name or result.bronze.source_name
                job_probability = float(getattr(silver, "job_probability_score", 0.0) or silver.contextual.get("job_probability_score") or 0.0)
                curation_level = str(getattr(silver, "curation_level", "") or silver.contextual.get("curation_level") or "probable_job")
                processing_stage = _processing_stage(silver)
                top_reasons = list(getattr(silver, "top_acceptance_reasons", None) or silver.contextual.get("top_acceptance_reasons") or [])
                unknown_candidates = list(getattr(silver, "unknown_skill_candidates", None) or [])
                rejection_reasons = [item for item in str(silver.invalid_job_reason or silver.rejection_reason or "").split(";") if item]
                source_id = _upsert_lookup(cur, "sources", "name", source_name, {"confidence": _source_confidence(source_name)})
                original_company = silver.normalized_company or ""
                company_name, company_confidence = normalize_company(original_company)
                company_id = _upsert_lookup(
                    cur,
                    "companies",
                    "normalized_company",
                    _norm_key(company_name),
                    {"company": company_name, "original_company": original_company or company_name, "company_confidence_score": company_confidence},
                )
                location_payload = normalize_location(silver.normalized_location)
                location = (
                    location_payload.get("normalized_location")
                    or location_payload.get("location")
                    or silver.normalized_location
                    or "No especificada"
                )
                location_id = _upsert_lookup(
                    cur,
                    "locations",
                    "normalized_location",
                    _norm_key(location),
                    {
                        "location": location,
                        "city": location_payload.get("city"),
                        "country": location_payload.get("country"),
                    },
                )
                modality = str(silver.contextual.get("modality") or infer_modality(text))
                modality_id = _upsert_lookup(cur, "modalities", "modality", modality)
                seniority = str(silver.contextual.get("seniority") or infer_seniority(text))
                seniority_id = _upsert_lookup(cur, "seniority_levels", "seniority", seniority)
                industry = str(silver.contextual.get("industry") or infer_industry(text))
                industry_id = _upsert_lookup(cur, "industries", "industry", industry)
                salary = normalize_salary(str(silver.contextual.get("salary") or ""))
                quality = build_quality_envelope(result)
                skill_payload = _job_skills(result)
                skill_names = [item[0].name for item in skill_payload]
                title_family, role_inference, role_similarity = semantic_title_family(persist_title, skill_names)
                duplicate_group = duplicate_group_key(title=persist_title, company=company_name, location=location, skills=skill_names)
                fingerprint = job_fingerprint(
                    title=persist_title,
                    company=company_name,
                    location=location,
                    description=persist_description,
                )
                cur.execute(
                    """
                    INSERT INTO jobs
                        (source_id, company_id, location_id, modality_id, seniority_id, industry_id, execution_id,
                         source, title, company, location, modality, seniority, industry, salary_min, salary_max,
                         salary_currency, salary_period, contract_type, experience_level, description, original_company,
                         normalized_company, company_confidence_score,
                         responsibilities, requirements, source_url, application_url, fingerprint, content_hash,
                         duplicate_group_id, duplicate_confidence, semantic_title_family, role_similarity, occupational_role_inference,
                         completeness_score, extraction_confidence, source_confidence, job_probability_score,
                         curation_level, processing_stage, rejection_reasons, semantic_evidence_count, semantic_evidence,
                         top_acceptance_reasons, unknown_skill_candidates, document_type, is_real_job_posting, raw_context)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (content_hash) DO UPDATE SET
                        fingerprint = EXCLUDED.fingerprint,
                        company_id = EXCLUDED.company_id,
                        location_id = EXCLUDED.location_id,
                        modality_id = EXCLUDED.modality_id,
                        seniority_id = EXCLUDED.seniority_id,
                        industry_id = EXCLUDED.industry_id,
                        source = EXCLUDED.source,
                        title = EXCLUDED.title,
                        company = EXCLUDED.company,
                        original_company = EXCLUDED.original_company,
                        normalized_company = EXCLUDED.normalized_company,
                        company_confidence_score = EXCLUDED.company_confidence_score,
                        location = EXCLUDED.location,
                        modality = EXCLUDED.modality,
                        seniority = EXCLUDED.seniority,
                        industry = EXCLUDED.industry,
                        description = EXCLUDED.description,
                        completeness_score = EXCLUDED.completeness_score,
                        extraction_confidence = EXCLUDED.extraction_confidence,
                        source_confidence = EXCLUDED.source_confidence,
                        job_probability_score = EXCLUDED.job_probability_score,
                        curation_level = EXCLUDED.curation_level,
                        processing_stage = EXCLUDED.processing_stage,
                        rejection_reasons = EXCLUDED.rejection_reasons,
                        semantic_evidence_count = EXCLUDED.semantic_evidence_count,
                        semantic_evidence = EXCLUDED.semantic_evidence,
                        top_acceptance_reasons = EXCLUDED.top_acceptance_reasons,
                        unknown_skill_candidates = EXCLUDED.unknown_skill_candidates,
                        duplicate_group_id = EXCLUDED.duplicate_group_id,
                        duplicate_confidence = EXCLUDED.duplicate_confidence,
                        semantic_title_family = EXCLUDED.semantic_title_family,
                        role_similarity = EXCLUDED.role_similarity,
                        occupational_role_inference = EXCLUDED.occupational_role_inference,
                        raw_context = EXCLUDED.raw_context,
                        updated_at = now()
                    RETURNING id
                    """,
                    (
                        source_id,
                        company_id,
                        location_id,
                        modality_id,
                        seniority_id,
                        industry_id,
                        correlation_id,
                        source_name,
                        persist_title,
                        company_name,
                        location,
                        modality,
                        seniority,
                        industry,
                        salary.get("min") or salary.get("salary_min"),
                        salary.get("max") or salary.get("salary_max"),
                        salary.get("currency") or salary.get("salary_currency"),
                        salary.get("period") or salary.get("salary_period"),
                        str(silver.contextual.get("contract_type") or ""),
                        str(silver.contextual.get("experience_level") or ""),
                        persist_description,
                        original_company,
                        company_name,
                        company_confidence,
                        str(silver.contextual.get("responsibilities") or ""),
                        str(silver.contextual.get("requirements") or ""),
                        silver.source_url,
                        str(silver.contextual.get("application_url") or silver.source_url),
                        fingerprint,
                        silver.content_hash,
                        duplicate_group,
                        0.82 if company_name != "No especificada" else 0.55,
                        title_family,
                        role_similarity,
                        role_inference,
                        quality.completeness_score,
                        max(silver.contextual_relevance_score, silver.semantic_score, quality.completeness_score),
                        _source_confidence(source_name),
                        job_probability,
                        curation_level,
                        processing_stage,
                        Json(rejection_reasons),
                        int(getattr(silver, "semantic_evidence_count", 0) or len(silver.job_evidence_skills or [])),
                        Json(
                            {
                                "job_evidence_skills": silver.job_evidence_skills or [],
                                "semantic_skill_evidence": silver.contextual.get("semantic_skill_evidence") or [],
                                "detected_signals": silver.contextual.get("detected_signals") or [],
                            }
                        ),
                        Json(top_reasons),
                        Json(unknown_candidates),
                        silver.document_type,
                        silver.is_real_job_posting,
                        Json(silver.contextual),
                    ),
                )
                job_id = int(cur.fetchone()["id"])
                persisted_job_ids.append(job_id)
                jobs_upserted += 1
                for canonical, confidence, section in skill_payload:
                    cur.execute(
                        """
                        INSERT INTO canonical_skills (canonical_skill, skill_category, skill_family)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (canonical_skill) DO UPDATE SET
                            skill_category = EXCLUDED.skill_category,
                            skill_family = EXCLUDED.skill_family,
                            updated_at = now()
                        RETURNING id
                        """,
                        (canonical.name, canonical.category, canonical.family),
                    )
                    canonical_skill_id = int(cur.fetchone()["id"])
                    cur.execute(
                        """
                        INSERT INTO skill_aliases (canonical_skill_id, alias, normalized_alias)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (normalized_alias) DO NOTHING
                        """,
                        (canonical_skill_id, canonical.alias, _norm_key(canonical.alias)),
                    )
                    cur.execute(
                        """
                        INSERT INTO job_skills
                            (job_id, canonical_skill_id, canonical_skill, skill_category, skill_family,
                             confidence, evidence_type, source_section)
                        VALUES (%s, %s, %s, %s, %s, %s, 'job_evidence', %s)
                        ON CONFLICT (job_id, canonical_skill) DO UPDATE SET
                            confidence = GREATEST(job_skills.confidence, EXCLUDED.confidence),
                            evidence_type = EXCLUDED.evidence_type,
                            source_section = EXCLUDED.source_section
                        """,
                        (job_id, canonical_skill_id, canonical.name, canonical.category, canonical.family, confidence, section),
                    )
                    skills_upserted += 1
            if persisted_job_ids:
                _persist_embeddings(cur, persisted_job_ids)
                _refresh_duplicate_canonicals(cur, persisted_job_ids)
                _sanitize_company_values(cur)
                _refresh_company_profiles(cur)
                _refresh_emerging_skill_candidates(cur)
            cur.execute(
                """
                UPDATE execution_runs
                SET status = 'success', finished_at = now(),
                    metadata = metadata || %s::jsonb
                WHERE correlation_id = %s
                """,
                (json.dumps({"jobs_upserted": jobs_upserted, "job_skills_upserted": skills_upserted}), correlation_id),
            )
        conn.commit()
        return {"warehouse_enabled": True, "jobs": jobs_upserted, "job_skills": skills_upserted, "valid_results": len(persistable_results)}


def verify_warehouse_counts() -> dict[str, Any]:
    load_environment()
    queries = {
        "jobs_count": "SELECT COUNT(*) AS count FROM jobs",
        "jobs_by_source": "SELECT source, COUNT(*) AS count FROM jobs GROUP BY source ORDER BY count DESC, source",
        "top_skills": """
            SELECT canonical_skill, COUNT(*) AS count
            FROM job_skills
            GROUP BY canonical_skill
            ORDER BY COUNT(*) DESC, canonical_skill
            LIMIT 50
        """,
        "jobs_by_seniority": "SELECT seniority, COUNT(*) AS count FROM jobs GROUP BY seniority ORDER BY count DESC",
        "jobs_by_modality": "SELECT modality, COUNT(*) AS count FROM jobs GROUP BY modality ORDER BY count DESC",
        "recent_companies": "SELECT company, COUNT(*) AS count FROM jobs GROUP BY company ORDER BY MAX(created_at) DESC LIMIT 20",
        "duplicate_groups": "SELECT COUNT(DISTINCT duplicate_group_id) AS count FROM jobs WHERE duplicate_group_id IS NOT NULL",
        "job_embeddings": "SELECT COUNT(*) AS count FROM job_embeddings",
        "skill_embeddings": "SELECT COUNT(*) AS count FROM skill_embeddings",
        "company_embeddings": "SELECT COUNT(*) AS count FROM company_embeddings",
        "company_profiles": "SELECT COUNT(*) AS count FROM company_skill_profiles",
        "emerging_candidates": "SELECT COUNT(*) AS count FROM emerging_skill_candidates",
    }
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(MIGRATION.read_text(encoding="utf-8"))
            if ENRICHMENT_MIGRATION.exists():
                cur.execute(ENRICHMENT_MIGRATION.read_text(encoding="utf-8"))
            result: dict[str, Any] = {}
            for name, query in queries.items():
                cur.execute(query)
                rows = cur.fetchall()
                result[name] = rows[0]["count"] if name in {"jobs_count", "duplicate_groups", "job_embeddings", "skill_embeddings", "company_embeddings", "company_profiles", "emerging_candidates"} else [dict(row) for row in rows]
        conn.commit()
    return result


def write_analytics_reports(counts: dict[str, Any]) -> dict[str, str]:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    company_rows = counts.get("recent_companies", [])
    duplicate_count = counts.get("duplicate_groups", 0)
    emerging_count = counts.get("emerging_candidates", 0)
    reports = {
        "top_skills.md": ["# Top Skills", "", *[f"- {row['canonical_skill']}: {row['count']}" for row in counts.get("top_skills", [])]],
        "source_distribution.md": ["# Source Distribution", "", *[f"- {row['source']}: {row['count']}" for row in counts.get("jobs_by_source", [])]],
        "salary_distribution.md": ["# Salary Distribution", "", "La normalizacion salarial queda disponible en jobs.salary_min/jobs.salary_max para analitica posterior."],
        "emerging_skills.md": ["# Emerging Skills", "", *[f"- {row['canonical_skill']}: {row['count']}" for row in counts.get("top_skills", [])[:15]]],
        "company_skill_distribution.md": ["# Company Skill Distribution", "", *[f"- {row['company']}: {row['count']} job(s)" for row in company_rows]],
        "duplicate_detection_report.md": ["# Duplicate Detection Report", "", f"- Duplicate groups tracked: {duplicate_count}", "- Evidence is preserved per source; duplicate grouping does not delete jobs."],
        "emerging_skill_report.md": ["# Emerging Skill Report", "", f"- Emerging candidates persisted: {emerging_count}", *[f"- {row['canonical_skill']}: {row['count']}" for row in counts.get("top_skills", [])[:20]]],
        "semantic_role_clusters.md": ["# Semantic Role Clusters", "", *[f"- {row['seniority']}: {row['count']}" for row in counts.get("jobs_by_seniority", [])]],
        "labor_market_maturity_report.md": [
            "# Labor Market Maturity Report",
            "",
            f"- Company profiles: {counts.get('company_profiles', 0)}",
            f"- Job embeddings: {counts.get('job_embeddings', 0)}",
            f"- Skill embeddings: {counts.get('skill_embeddings', 0)}",
            f"- Company embeddings: {counts.get('company_embeddings', 0)}",
        ],
        "labor_market_summary.md": [
            "# Labor Market Summary",
            "",
            f"- Total jobs: {counts.get('jobs_count', 0)}",
            f"- Sources: {len(counts.get('jobs_by_source', []))}",
            f"- Skills tracked: {len(counts.get('top_skills', []))}",
            f"- Duplicate groups: {duplicate_count}",
            f"- Embeddings: jobs={counts.get('job_embeddings', 0)}, skills={counts.get('skill_embeddings', 0)}, companies={counts.get('company_embeddings', 0)}",
        ],
    }
    paths: dict[str, str] = {}
    for filename, lines in reports.items():
        path = ANALYTICS_DIR / filename
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths[filename] = str(path)
    return paths
