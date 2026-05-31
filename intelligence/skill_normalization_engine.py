from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Any

from psycopg2.extras import Json, execute_values

from backend.db import get_conn
from backend.repositories.base import fetch_all, relation_exists
from intelligence.common import normalize_key


ACRONYM_OVERRIDES = {
    "ai": "AI",
    "ml": "ML",
    "llm": "LLM",
    "llmops": "LLMOps",
    "rag": "RAG",
    "bi": "BI",
    "sql": "SQL",
    "etl": "ETL",
    "elt": "ELT",
    "api": "API",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "pbi": "Power BI",
    "powerbi": "Power BI",
    "dbt": "dbt",
    "power": "Power",
    "query": "Query",
    "fabric": "Microsoft Fabric",
    "synapse": "Synapse",
    "databricks": "Databricks",
    "bigquery": "BigQuery",
    "redshift": "Redshift",
    "snowflake": "Snowflake",
    "copilot": "Copilot",
    "devops": "DevOps",
    "ops": "Ops",
    "dwh": "Data Warehouse",
    "dw": "Data Warehouse",
}

SYNONYMS = {
    "power bi": "Power BI",
    "pbi": "Power BI",
    "powerbi": "Power BI",
    "microsoft power bi": "Power BI",
    "visual analytics": "Visual Analytics",
    "business intelligence": "Business Intelligence",
    "data warehousing": "Data Warehouse",
    "data warehouse": "Data Warehouse",
    "data lake": "Data Lake",
    "data lakehouse": "Lakehouse",
    "lakehouse": "Lakehouse",
    "dataops": "DataOps",
    "data ops": "DataOps",
    "mops": "MLOps",
    "mlops": "MLOps",
    "llmops": "LLMOps",
    "genai": "Generative AI",
    "gen ai": "Generative AI",
    "copilot bi": "Copilot BI",
    "copilot": "Copilot",
    "rag": "RAG",
    "agentic ai": "Agentic AI",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "data governance": "Data Governance",
    "data quality": "Data Quality",
    "data catalog": "Data Catalog",
    "data lineage": "Data Lineage",
    "cloud analytics": "Cloud Analytics",
    "analytics engineering": "Analytics Engineering",
    "analytics engineer": "Analytics Engineer",
}


@dataclass(frozen=True)
class SkillNormalizationResult:
    raw_skill: str
    raw_skill_normalized: str
    canonical_skill: str
    canonical_skill_id: int | None
    skill_category: str
    skill_family: str
    match_method: str
    confidence_score: float
    source_payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _format_canonical_skill(value: str) -> str:
    normalized = normalize_key(value)
    if not normalized:
        return ""
    if normalized in SYNONYMS:
        return SYNONYMS[normalized]
    parts: list[str] = []
    for token in normalized.split():
        if token in ACRONYM_OVERRIDES:
            parts.append(ACRONYM_OVERRIDES[token])
        elif token.upper() in {"AI", "ML", "BI", "SQL", "ETL", "ELT", "API", "AWS", "GCP"}:
            parts.append(token.upper())
        else:
            parts.append(token.capitalize())
    return " ".join(parts).strip()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def load_skill_catalog(*, db_name: str | None = None) -> list[dict[str, Any]]:
    try:
        if not relation_exists("canonical_skills", db_name=db_name):
            return []
        rows = fetch_all(
            """
            SELECT id, canonical_skill, skill_category, skill_family
            FROM canonical_skills
            ORDER BY canonical_skill ASC
            """,
            db_name=db_name,
        )
    except Exception:
        return []
    return [
        {
            "id": int(row.get("id") or 0),
            "canonical_skill": str(row.get("canonical_skill") or "").strip(),
            "skill_category": str(row.get("skill_category") or "Unknown"),
            "skill_family": str(row.get("skill_family") or "Unknown"),
        }
        for row in rows
        if str(row.get("canonical_skill") or "").strip()
    ]


def normalize_skill(raw_skill: str | None, *, db_name: str | None = None, source_payload: dict[str, Any] | None = None) -> SkillNormalizationResult:
    raw_skill = str(raw_skill or "").strip()
    normalized_raw = normalize_key(raw_skill)
    if not raw_skill:
        return SkillNormalizationResult(
            raw_skill="",
            raw_skill_normalized="",
            canonical_skill="",
            canonical_skill_id=None,
            skill_category="Unknown",
            skill_family="Unknown",
            match_method="empty",
            confidence_score=0.0,
            source_payload=source_payload or {},
        )

    catalog = load_skill_catalog(db_name=db_name)
    try:
        aliases = {
            normalize_key(str(row.get("alias") or row.get("normalized_alias") or "")): {
                "canonical_skill_id": int(row.get("canonical_skill_id") or 0),
                "canonical_skill": str(row.get("canonical_skill") or "").strip(),
            }
            for row in fetch_all(
                """
                SELECT sa.canonical_skill_id, sa.alias, sa.normalized_alias, cs.canonical_skill, cs.skill_category, cs.skill_family
                FROM skill_aliases sa
                INNER JOIN canonical_skills cs ON cs.id = sa.canonical_skill_id
                """,
                db_name=db_name,
            )
        } if relation_exists("skill_aliases", db_name=db_name) and relation_exists("canonical_skills", db_name=db_name) else {}
    except Exception:
        aliases = {}

    synonyms_hit = SYNONYMS.get(normalized_raw)
    if synonyms_hit:
        normalized_raw = normalize_key(synonyms_hit)

    alias_hit = aliases.get(normalized_raw)
    if alias_hit:
        canonical_id = alias_hit["canonical_skill_id"]
        matched = next((row for row in catalog if row["id"] == canonical_id), None)
        return SkillNormalizationResult(
            raw_skill=raw_skill,
            raw_skill_normalized=normalize_key(raw_skill),
            canonical_skill=matched["canonical_skill"] if matched else alias_hit["canonical_skill"],
            canonical_skill_id=canonical_id,
            skill_category=matched["skill_category"] if matched else "Unknown",
            skill_family=matched["skill_family"] if matched else "Unknown",
            match_method="alias",
            confidence_score=0.98,
            source_payload=source_payload or {},
        )

    best_row: dict[str, Any] | None = None
    best_score = 0.0
    for row in catalog:
        candidate = normalize_key(row["canonical_skill"])
        score = max(_similarity(normalized_raw, candidate), _similarity(normalized_raw, normalize_key(_format_canonical_skill(candidate))))
        if score > best_score:
            best_score = score
            best_row = row

    if best_row and best_score >= 0.82:
        return SkillNormalizationResult(
            raw_skill=raw_skill,
            raw_skill_normalized=normalize_key(raw_skill),
            canonical_skill=best_row["canonical_skill"],
            canonical_skill_id=best_row["id"],
            skill_category=best_row["skill_category"],
            skill_family=best_row["skill_family"],
            match_method="fuzzy",
            confidence_score=round(min(1.0, 0.80 + (best_score * 0.2)), 4),
            source_payload=source_payload or {},
        )

    generated = _format_canonical_skill(raw_skill) or raw_skill.strip().title()
    confidence = 0.7 if generated else 0.0
    return SkillNormalizationResult(
        raw_skill=raw_skill,
        raw_skill_normalized=normalize_key(raw_skill),
        canonical_skill=generated,
        canonical_skill_id=None,
        skill_category="Unknown",
        skill_family="Unknown",
        match_method="generated",
        confidence_score=round(confidence, 4),
        source_payload=source_payload or {},
    )


def normalize_skill_batch(skills: list[str], *, db_name: str | None = None, persist: bool = False, source: str = "curriculum") -> list[SkillNormalizationResult]:
    unique_skills = []
    seen: set[str] = set()
    for skill in skills:
        normalized = normalize_key(skill)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_skills.append(skill)
    results = [normalize_skill(skill, db_name=db_name, source_payload={"source": source}) for skill in unique_skills]
    if persist and results:
        persist_skill_normalization_mappings(results, db_name=db_name)
    return results


def persist_skill_normalization_mappings(records: list[SkillNormalizationResult], *, db_name: str | None = None) -> int:
    try:
        if not records or not relation_exists("skill_normalization_mappings", db_name=db_name):
            return 0
    except Exception:
        return 0
    rows = [
        (
            record.raw_skill,
            record.raw_skill_normalized,
            record.canonical_skill_id,
            record.canonical_skill,
            record.match_method,
            record.confidence_score,
            Json(record.source_payload),
        )
        for record in records
    ]
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO skill_normalization_mappings
                        (raw_skill, raw_skill_normalized, canonical_skill_id, canonical_skill, match_method, confidence_score, source_payload)
                    VALUES %s
                    ON CONFLICT (raw_skill_normalized) DO UPDATE SET
                        raw_skill = EXCLUDED.raw_skill,
                        canonical_skill_id = EXCLUDED.canonical_skill_id,
                        canonical_skill = EXCLUDED.canonical_skill,
                        match_method = EXCLUDED.match_method,
                        confidence_score = EXCLUDED.confidence_score,
                        source_payload = EXCLUDED.source_payload,
                        updated_at = now()
                    """,
                    rows,
                )
                alias_rows = [
                    (
                        record.canonical_skill_id,
                        record.raw_skill,
                        record.raw_skill_normalized,
                    )
                    for record in records
                    if record.canonical_skill_id
                ]
                if alias_rows:
                    execute_values(
                        cur,
                        """
                        INSERT INTO skill_aliases
                            (canonical_skill_id, alias, normalized_alias)
                        VALUES %s
                        ON CONFLICT (normalized_alias) DO UPDATE SET
                            canonical_skill_id = EXCLUDED.canonical_skill_id
                        """,
                        alias_rows,
                    )
            conn.commit()
    except Exception:
        return 0
    return len(rows)
