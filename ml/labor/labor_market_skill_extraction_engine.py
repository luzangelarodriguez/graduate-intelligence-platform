from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    classify_visual_analytics_skill,
    extract_visual_analytics_skills,
    normalize_visual_analytics_skill,
)
from ml.labor.labor_skill_taxonomy_expanded import extract_expanded_labor_skills  # noqa: E402

RESULTS_PATH = ROOT_DIR / "outputs" / "agentic_labor_extraction_results.json"
ENTERPRISE_RESULTS_PATH = ROOT_DIR / "outputs" / "enterprise_agentic_job_extraction_results.json"
UNIVERSE_JSON = ROOT_DIR / "outputs" / "labor_market_skill_universe.json"

EVIDENCE_WEIGHTS = {
    "gold_job_posting": 1.0,
    "silver_job_posting": 0.7,
    "bronze_job_posting": 0.4,
    "portal_taxonomy": 0.1,
    "legacy_empleo_skill": 0.55,
}

EXPANDED_TYPE_BY_SKILL: dict[str, str] = {}


@dataclass(frozen=True)
class LaborSkillEvidence:
    skill: str
    normalized_skill: str
    skill_type: str
    evidence_source: str
    evidence_weight: float
    document_type: str
    source_name: str
    source_url: str
    title: str
    company: str
    role: str
    content_hash: str
    entity_type: str = ""
    evidence_confidence: float = 0.0


@dataclass(frozen=True)
class LaborMarketSkill:
    skill: str
    skill_type: str
    total_weight: float
    evidence_count: int
    source_breakdown: dict[str, int]
    roles: list[str]
    companies: list[str]
    source_urls: list[str]
    evidence: list[LaborSkillEvidence]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        except Exception:
            return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _canonical_skill(value: str) -> str:
    return normalize_visual_analytics_skill(str(value or "").strip())


def _evidence(
    skill: str,
    source: str,
    document_type: str,
    payload: dict[str, Any],
    *,
    entity_type: str = "",
    confidence: float = 0.0,
) -> LaborSkillEvidence:
    normalized = _canonical_skill(skill)
    return LaborSkillEvidence(
        skill=str(skill),
        normalized_skill=normalized,
        skill_type=classify_visual_analytics_skill(normalized),
        evidence_source=source,
        evidence_weight=EVIDENCE_WEIGHTS[source],
        document_type=document_type,
        source_name=str(payload.get("source_name") or ""),
        source_url=str(payload.get("source_url") or ""),
        title=str(payload.get("title") or payload.get("normalized_title") or payload.get("curated_title") or ""),
        company=str(payload.get("company") or payload.get("normalized_company") or ""),
        role=str(payload.get("market_role") or payload.get("normalized_title") or payload.get("title") or ""),
        content_hash=str(payload.get("content_hash") or ""),
        entity_type=entity_type or EXPANDED_TYPE_BY_SKILL.get(normalized, ""),
        evidence_confidence=confidence,
    )


def _expanded_evidence_from_text(text: str, source: str, document_type: str, payload: dict[str, Any], *, section: str) -> list[LaborSkillEvidence]:
    items: list[LaborSkillEvidence] = []
    for skill in extract_expanded_labor_skills(text, section=section):
        EXPANDED_TYPE_BY_SKILL[skill.normalized] = skill.entity_type
        items.append(
            _evidence(
                skill.normalized,
                source,
                document_type,
                payload,
                entity_type=skill.entity_type,
                confidence=skill.confidence,
            )
        )
    return items


def _evidence_from_agentic_results(path: Path = RESULTS_PATH) -> list[LaborSkillEvidence]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    items: list[LaborSkillEvidence] = []
    for row in data:
        silver = row.get("silver") or {}
        bronze = row.get("bronze") or {}
        gold = row.get("gold") or {}
        base = {
            "source_name": silver.get("source_name") or bronze.get("source_name"),
            "source_url": silver.get("source_url") or bronze.get("source_url"),
            "normalized_title": silver.get("normalized_title"),
            "normalized_company": silver.get("normalized_company"),
            "content_hash": silver.get("content_hash") or bronze.get("content_hash"),
        }
        document_type = str(silver.get("document_type") or "unknown")
        if gold:
            gold_payload = {**base, **gold}
            for skill in _as_list(gold.get("normalized_skills")):
                items.append(_evidence(skill, "gold_job_posting", "job_posting", gold_payload))
        job_probability = float(silver.get("job_probability_score") or (silver.get("contextual") or {}).get("job_probability_score") or 0.0)
        curation_level = str(silver.get("curation_level") or (silver.get("contextual") or {}).get("curation_level") or "")
        is_probable_job = document_type == "job_posting" and (silver.get("is_real_job_posting") or job_probability >= 0.30 or curation_level in {"probable_job", "curated_job", "gold_job"})
        if is_probable_job:
            for skill in _as_list(silver.get("job_evidence_skills") or silver.get("extracted_skills")):
                items.append(_evidence(skill, "silver_job_posting", "job_posting", base))
            for semantic in ((silver.get("contextual") or {}).get("semantic_skill_evidence") or []):
                if isinstance(semantic, dict) and semantic.get("skill"):
                    items.append(
                        _evidence(
                            semantic["skill"],
                            "silver_job_posting",
                            "job_posting",
                            base,
                            entity_type=str(semantic.get("skill_type") or ""),
                            confidence=float(semantic.get("confidence") or 0),
                        )
                    )
            raw_text = str(bronze.get("raw_text") or "")
            items.extend(_expanded_evidence_from_text(raw_text, "bronze_job_posting", "job_posting", base, section="description"))
        else:
            for skill in _as_list(silver.get("portal_taxonomy_skills")):
                items.append(_evidence(skill, "portal_taxonomy", document_type, base))
            raw_text = str(bronze.get("raw_text") or "")
            items.extend(_expanded_evidence_from_text(raw_text, "portal_taxonomy", document_type, base, section="portal_taxonomy"))
    return items


def _query_database_evidence() -> list[LaborSkillEvidence]:
    try:
        from dotenv import load_dotenv

        for name in (".env.local", ".env", ".env.development"):
            path = ROOT_DIR / name
            if path.exists():
                load_dotenv(path, override=False)
    except Exception:
        pass
    if not os.getenv("DB_HOST") and not os.getenv("DATABASE_URL") and not os.getenv("RAILWAY_DATABASE_URL"):
        return []
    try:
        from backend.repositories.base import fetch_all, relation_exists
    except Exception:
        return []

    evidence: list[LaborSkillEvidence] = []
    try:
        if relation_exists("public.gold_empleos_analytics"):
            rows = fetch_all(
                """
                SELECT curated_title, source_name, source_url, market_role, content_hash, normalized_skills
                FROM public.gold_empleos_analytics
                """
            )
            for row in rows:
                for skill in _as_list(row.get("normalized_skills")):
                    evidence.append(_evidence(skill, "gold_job_posting", "job_posting", row))
        if relation_exists("public.silver_empleos_normalized"):
            rows = fetch_all(
                """
                SELECT normalized_title, normalized_company, source_name, source_url, content_hash,
                       document_type, is_real_job_posting, job_evidence_skills, portal_taxonomy_skills,
                       COALESCE(job_probability_score, 0) AS job_probability_score, curation_level
                FROM public.silver_empleos_normalized
                """
            )
            for row in rows:
                job_probability = float(row.get("job_probability_score") or 0.0)
                if row.get("document_type") == "job_posting" and (row.get("is_real_job_posting") or job_probability >= 0.30 or row.get("curation_level") in {"probable_job", "curated_job", "gold_job"}):
                    for skill in _as_list(row.get("job_evidence_skills")):
                        evidence.append(_evidence(skill, "silver_job_posting", "job_posting", row))
                else:
                    for skill in _as_list(row.get("portal_taxonomy_skills")):
                        evidence.append(_evidence(skill, "portal_taxonomy", str(row.get("document_type") or "unknown"), row))
        if relation_exists("public.empleo_skills"):
            rows = fetch_all(
                """
                SELECT es.skill_normalized, es.skill_original, e.titulo AS title, e.empresa AS company,
                       e.url AS source_url, e.id::text AS content_hash
                FROM public.empleo_skills es
                LEFT JOIN public.empleos e ON e.id::text = es.empleo_id::text
                WHERE COALESCE(es.skill_normalized, es.skill_original, '') <> ''
                """
            )
            for row in rows:
                evidence.append(_evidence(row.get("skill_normalized") or row.get("skill_original"), "legacy_empleo_skill", "job_posting", row))
        if relation_exists("public.bronze_empleos_raw") and relation_exists("public.silver_empleos_normalized"):
            rows = fetch_all(
                """
                SELECT s.normalized_title, s.normalized_company, s.source_name, s.source_url,
                       s.content_hash, s.document_type, s.is_real_job_posting, b.raw_text,
                       COALESCE(s.job_probability_score, 0) AS job_probability_score, s.curation_level
                FROM public.silver_empleos_normalized s
                INNER JOIN public.bronze_empleos_raw b ON b.content_hash = s.content_hash
                WHERE COALESCE(b.raw_text, '') <> ''
                """
            )
            for row in rows:
                document_type = str(row.get("document_type") or "unknown")
                job_probability = float(row.get("job_probability_score") or 0.0)
                if document_type == "job_posting" and (row.get("is_real_job_posting") or job_probability >= 0.30 or row.get("curation_level") in {"probable_job", "curated_job", "gold_job"}):
                    evidence.extend(_expanded_evidence_from_text(str(row.get("raw_text") or ""), "bronze_job_posting", "job_posting", row, section="description"))
                else:
                    evidence.extend(_expanded_evidence_from_text(str(row.get("raw_text") or ""), "portal_taxonomy", document_type, row, section="portal_taxonomy"))
    except Exception:
        return evidence
    return evidence


def build_labor_market_skill_universe(
    evidence: Iterable[LaborSkillEvidence] | None = None,
    *,
    include_database: bool = True,
    write_output: bool = True,
) -> list[LaborMarketSkill]:
    items = list(evidence) if evidence is not None else []
    if evidence is None:
        items.extend(_evidence_from_agentic_results())
        items.extend(_evidence_from_agentic_results(ENTERPRISE_RESULTS_PATH))
        if include_database:
            items.extend(_query_database_evidence())

    grouped: dict[str, list[LaborSkillEvidence]] = defaultdict(list)
    for item in items:
        if not item.normalized_skill:
            continue
        grouped[item.normalized_skill].append(item)

    universe: list[LaborMarketSkill] = []
    for skill, rows in grouped.items():
        source_counts = defaultdict(int)
        for row in rows:
            source_counts[row.evidence_source] += 1
        universe.append(
            LaborMarketSkill(
                skill=skill,
                skill_type=EXPANDED_TYPE_BY_SKILL.get(skill) or classify_visual_analytics_skill(skill),
                total_weight=round(sum(row.evidence_weight for row in rows), 4),
                evidence_count=len(rows),
                source_breakdown=dict(sorted(source_counts.items())),
                roles=sorted({row.role or row.title for row in rows if row.evidence_source != "portal_taxonomy" and (row.role or row.title)})[:10],
                companies=sorted({row.company for row in rows if row.evidence_source != "portal_taxonomy" and row.company})[:10],
                source_urls=sorted({row.source_url for row in rows if row.source_url})[:10],
                evidence=rows,
            )
        )
    universe = sorted(universe, key=lambda item: (item.total_weight, item.evidence_count, item.skill), reverse=True)
    if write_output:
        UNIVERSE_JSON.parent.mkdir(parents=True, exist_ok=True)
        UNIVERSE_JSON.write_text(json.dumps([asdict(item) for item in universe], indent=2, ensure_ascii=False), encoding="utf-8")
    return universe


def universe_to_dict(universe: list[LaborMarketSkill]) -> list[dict[str, Any]]:
    return [asdict(item) for item in universe]
