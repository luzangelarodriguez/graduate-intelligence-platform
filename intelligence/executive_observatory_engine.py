from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from psycopg2.extras import Json, execute_values

from backend.db import get_conn
from backend.repositories.base import fetch_all, fetch_one, relation_exists
from intelligence.common import clamp, normalize_key
from intelligence.program_intelligence_engine import build_program_intelligence, persist_program_intelligence


SOURCE_TABLES = (
    "program_intelligence",
    "observatory_metrics",
    "recommendation_observatory",
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [value] if value else []
    return []


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = normalize_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


@dataclass(frozen=True)
class ExecutiveObservatoryV2:
    alignment_average: float
    high_risk_programs: list[dict[str, Any]]
    medium_risk_programs: list[dict[str, Any]]
    low_risk_programs: list[dict[str, Any]]
    programs_analyzed: int
    critical_gaps: list[dict[str, Any]]
    top_emerging_skills: list[dict[str, Any]]
    top_recommendations: list[dict[str, Any]]
    top_programs: list[dict[str, Any]]
    at_risk_programs: list[dict[str, Any]]
    executive_narrative: str
    metrics: list[dict[str, Any]]
    source_tables: list[str]
    confidence: float
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fetch_program_intelligence_rows(db_name: str | None = None) -> list[dict[str, Any]]:
    if relation_exists("program_intelligence", db_name=db_name):
        rows = fetch_all(
            """
            SELECT program_id, program_name, program_role, alignment_score, risk_score, risk_level,
                   gap_count, top_gaps, top_recommendations, forecast_signals, role_signals,
                   emerging_technologies, recommended_actions, business_justification,
                   supporting_evidence, source_tables, confidence, generated_at
            FROM program_intelligence
            ORDER BY generated_at DESC NULLS LAST, risk_score DESC NULLS LAST, alignment_score DESC NULLS LAST
            """,
            db_name=db_name,
        )
        if rows:
            return rows
    return [item.to_dict() for item in build_program_intelligence(db_name=db_name)]


def _fetch_observatory_summary_rows(db_name: str | None = None) -> dict[str, list[dict[str, Any]]]:
    payload: dict[str, list[dict[str, Any]]] = {
        "observatory_metrics": [],
        "recommendation_observatory": [],
    }
    if relation_exists("observatory_metrics", db_name=db_name):
        payload["observatory_metrics"] = fetch_all(
            """
            SELECT metric_name, metric_category, metric_value, metric_period, confidence_score,
                   source_payload, generated_at
            FROM observatory_metrics
            ORDER BY generated_at DESC NULLS LAST, metric_value DESC NULLS LAST
            """,
            db_name=db_name,
        )
    if relation_exists("recommendation_observatory", db_name=db_name):
        payload["recommendation_observatory"] = fetch_all(
            """
            SELECT recommendation_type, target_role, target_company, recommendation_payload,
                   recommendation_reasoning, recommendation_confidence, recommendation_evidence,
                   metric_period, generated_at
            FROM recommendation_observatory
            ORDER BY recommendation_confidence DESC NULLS LAST, generated_at DESC NULLS LAST
            """,
            db_name=db_name,
        )
    return payload


def _program_risk_bucket(program: dict[str, Any]) -> str:
    risk_score = _safe_float(program.get("risk_score"))
    risk_level = str(program.get("risk_level") or "").lower()
    if risk_level == "high" or risk_score >= 70:
        return "high"
    if risk_level == "moderate" or risk_score >= 40:
        return "medium"
    return "low"


def _gap_entries(program: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = _as_list(program.get("top_gaps"))
    entries: list[dict[str, Any]] = []
    for gap in gaps:
        if isinstance(gap, dict):
            skill = str(gap.get("missing_skill") or gap.get("skill") or "").strip()
            if skill:
                entries.append(
                    {
                        "program_id": int(program.get("program_id") or 0),
                        "program_name": str(program.get("program_name") or ""),
                        "missing_skill": skill,
                        "urgency_score": _safe_float(gap.get("urgency_score")),
                        "risk_score": _safe_float(program.get("risk_score")),
                        "alignment_score": _safe_float(program.get("alignment_score")),
                    }
                )
    return entries


def _emerging_skill_entries(program: dict[str, Any]) -> list[dict[str, Any]]:
    items = _as_list(program.get("emerging_technologies"))
    entries: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            technology = str(item.get("technology") or "").strip()
            if technology:
                entries.append(
                    {
                        "skill_name": technology,
                        "growth_rate": _safe_float(item.get("growth_velocity") or item.get("emergence_score")),
                        "confidence_score": _safe_float(item.get("forecast_confidence")),
                        "first_seen_date": None,
                        "last_seen_date": None,
                        "evidence": item,
                    }
                )
    return entries


def _recommendation_entries(program: dict[str, Any]) -> list[dict[str, Any]]:
    recommendations = _as_list(program.get("top_recommendations"))
    entries: list[dict[str, Any]] = []
    for item in recommendations:
        if isinstance(item, dict):
            entries.append(
                {
                    "recommendation_type": str(item.get("recommendation_type") or "curriculum"),
                    "target_role": str(item.get("target_role") or program.get("program_name") or ""),
                    "target_company": str(item.get("target_company") or "curriculum"),
                    "recommendation_score": _safe_float(item.get("recommendation_confidence")),
                    "priority": "high" if _safe_float(item.get("recommendation_confidence")) >= 0.8 else "medium",
                    "business_justification": str(item.get("recommendation_reasoning") or ""),
                    "expected_impact": "Improve labor alignment",
                    "confidence": _safe_float(item.get("recommendation_confidence")),
                    "estimated_alignment_increase": round(_safe_float(item.get("recommendation_confidence")) * 12.0, 2),
                    "recommendation_evidence": item,
                    "recommendation_reasoning": str(item.get("recommendation_reasoning") or ""),
                }
            )
    return entries


def _top_programs(programs: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    ordered = sorted(programs, key=lambda item: (_safe_float(item.get("alignment_score")), -_safe_float(item.get("risk_score"))), reverse=True)
    return [
        {
            "program_id": int(item.get("program_id") or 0),
            "program_name": str(item.get("program_name") or ""),
            "program_role": str(item.get("program_role") or ""),
            "alignment_score": round(_safe_float(item.get("alignment_score")), 2),
            "risk_score": round(_safe_float(item.get("risk_score")), 2),
            "risk_level": str(item.get("risk_level") or ""),
            "gap_count": int(item.get("gap_count") or 0),
        }
        for item in ordered[:limit]
    ]


def _narrative(
    *,
    alignment_average: float,
    programs_analyzed: int,
    at_risk_programs: list[dict[str, Any]],
    critical_gaps: list[dict[str, Any]],
    emerging_skills: list[dict[str, Any]],
) -> str:
    if not programs_analyzed:
        return "No hay programas disponibles en la observabilidad ejecutiva para generar una narrativa."
    if alignment_average >= 75 and len(at_risk_programs) <= 2:
        tone = "strong alignment with the labor market demand"
    elif alignment_average >= 55:
        tone = "moderate alignment with the labor market demand"
    else:
        tone = "limited alignment with the labor market demand"
    if critical_gaps:
        top_gap_names = _unique_strings([str(row.get("missing_skill") or "") for row in critical_gaps if str(row.get("missing_skill") or "").strip()])
    else:
        top_gap_names = []
    if emerging_skills:
        top_emerging = _unique_strings([str(row.get("skill_name") or "") for row in emerging_skills if str(row.get("skill_name") or "").strip()])
    else:
        top_emerging = []
    gap_text = ", ".join(top_gap_names[:3]) if top_gap_names else "core curriculum gaps"
    emerging_text = ", ".join(top_emerging[:3]) if top_emerging else "emerging analytics and AI opportunities"
    if at_risk_programs:
        risk_count = len(at_risk_programs)
        return (
            f"The institution shows {tone}. {risk_count} programs require intervention. "
            f"The highest-impact opportunities are concentrated in {gap_text} and {emerging_text}."
        )
    return (
        f"The institution shows {tone}. {programs_analyzed} programs are monitored with no immediate high-risk concentration. "
        f"Attention should remain on {gap_text} and {emerging_text} to sustain alignment."
    )


def build_executive_observatory_v2(*, db_name: str | None = None, persist: bool = True) -> ExecutiveObservatoryV2:
    programs = _fetch_program_intelligence_rows(db_name=db_name)
    observatory = _fetch_observatory_summary_rows(db_name=db_name)

    high_risk_programs = [program for program in programs if _program_risk_bucket(program) == "high"]
    medium_risk_programs = [program for program in programs if _program_risk_bucket(program) == "medium"]
    low_risk_programs = [program for program in programs if _program_risk_bucket(program) == "low"]
    programs_analyzed = len(programs)
    alignment_average = round(sum(_safe_float(program.get("alignment_score")) for program in programs) / max(programs_analyzed, 1), 2) if programs else 0.0

    critical_gap_counter: Counter[str] = Counter()
    for program in programs:
        for gap in _gap_entries(program):
            critical_gap_counter[gap["missing_skill"]] += max(int(_safe_float(gap.get("urgency_score")) / 10.0) or 1, 1)
    critical_gaps = [
        {
            "missing_skill": skill,
            "impact_score": float(score),
            "programs_affected": sum(
                1
                for program in programs
                if any(normalize_key(skill) == normalize_key(str(gap.get("missing_skill") or "")) for gap in _gap_entries(program))
            ),
        }
        for skill, score in critical_gap_counter.most_common(10)
    ]

    emerging_counter: Counter[str] = Counter()
    emerging_payload: dict[str, dict[str, Any]] = {}
    for program in programs:
        for item in _emerging_skill_entries(program):
            skill = item["skill_name"]
            emerging_counter[skill] += 1
            current = emerging_payload.get(skill)
            if current is None or item["confidence_score"] >= current["confidence_score"]:
                emerging_payload[skill] = item
    top_emerging_skills = [
        {
            **emerging_payload[skill],
            "program_count": count,
        }
        for skill, count in emerging_counter.most_common(10)
    ]

    recommendations_counter: Counter[tuple[str, str, str]] = Counter()
    recommendation_payload: dict[tuple[str, str, str], dict[str, Any]] = {}
    for program in programs:
        for item in _recommendation_entries(program):
            key = (item["recommendation_type"], item["target_role"], item["target_company"])
            recommendations_counter[key] += 1
            current = recommendation_payload.get(key)
            if current is None or item["confidence"] >= current["confidence"]:
                recommendation_payload[key] = item
    top_recommendations = [
        {**recommendation_payload[key], "program_count": count}
        for key, count in recommendations_counter.most_common(10)
    ]

    at_risk_programs = [
        {
            "program_id": int(program.get("program_id") or 0),
            "program_name": str(program.get("program_name") or ""),
            "program_role": str(program.get("program_role") or ""),
            "alignment_score": round(_safe_float(program.get("alignment_score")), 2),
            "risk_score": round(_safe_float(program.get("risk_score")), 2),
            "risk_level": str(program.get("risk_level") or ""),
            "gap_count": int(program.get("gap_count") or 0),
            "recommended_actions": _as_list(program.get("recommended_actions")),
        }
        for program in programs
        if _program_risk_bucket(program) in {"high", "medium"}
    ]

    top_programs = _top_programs(programs, limit=5)
    executive_narrative = _narrative(
        alignment_average=alignment_average,
        programs_analyzed=programs_analyzed,
        at_risk_programs=at_risk_programs,
        critical_gaps=critical_gaps,
        emerging_skills=top_emerging_skills,
    )

    summary_metrics = [
        {
            "metric_name": "alignment_average",
            "metric_category": "executive_v2",
            "metric_value": alignment_average,
            "metric_period": datetime.now(UTC).strftime("%Y-%m"),
            "confidence_score": round(sum(_safe_float(program.get("confidence")) for program in programs) / max(programs_analyzed, 1), 4) if programs else 0.0,
            "source_tables": ["program_intelligence"],
            "supporting_evidence": {"programs_analyzed": programs_analyzed},
        },
        {
            "metric_name": "high_risk_programs",
            "metric_category": "executive_v2",
            "metric_value": float(len(high_risk_programs)),
            "metric_period": datetime.now(UTC).strftime("%Y-%m"),
            "confidence_score": 0.95,
            "source_tables": ["program_intelligence"],
            "supporting_evidence": {"programs": high_risk_programs[:10]},
        },
        {
            "metric_name": "at_risk_programs",
            "metric_category": "executive_v2",
            "metric_value": float(len(at_risk_programs)),
            "metric_period": datetime.now(UTC).strftime("%Y-%m"),
            "confidence_score": 0.95,
            "source_tables": ["program_intelligence"],
            "supporting_evidence": {"programs": at_risk_programs[:10]},
        },
    ]

    if persist:
        persist_executive_observatory_metrics(summary_metrics, db_name=db_name)

    return ExecutiveObservatoryV2(
        alignment_average=alignment_average,
        high_risk_programs=high_risk_programs[:10],
        medium_risk_programs=medium_risk_programs[:10],
        low_risk_programs=low_risk_programs[:10],
        programs_analyzed=programs_analyzed,
        critical_gaps=critical_gaps,
        top_emerging_skills=top_emerging_skills,
        top_recommendations=top_recommendations,
        top_programs=top_programs,
        at_risk_programs=at_risk_programs[:10],
        executive_narrative=executive_narrative,
        metrics=summary_metrics,
        source_tables=["program_intelligence", "observatory_metrics", "recommendation_observatory"],
        confidence=round(clamp((alignment_average / 100.0) * 0.6 + (1.0 - min(len(at_risk_programs) / max(programs_analyzed, 1), 1.0)) * 0.4), 4),
        generated_at=datetime.now(UTC).isoformat(),
    )


def persist_executive_observatory_metrics(metrics: list[dict[str, Any]], *, db_name: str | None = None) -> int:
    if not metrics or not relation_exists("observatory_metrics", db_name=db_name):
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            metric["metric_name"],
            metric["metric_category"],
            metric["metric_value"],
            metric["metric_period"],
            metric["confidence_score"],
            Json(metric["supporting_evidence"]),
            now,
            now,
        )
        for metric in metrics
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO observatory_metrics
                    (metric_name, metric_category, metric_value, metric_period, confidence_score, source_payload, generated_at, updated_at)
                VALUES %s
                ON CONFLICT (metric_name, metric_period) DO UPDATE SET
                    metric_category = EXCLUDED.metric_category,
                    metric_value = EXCLUDED.metric_value,
                    confidence_score = EXCLUDED.confidence_score,
                    source_payload = EXCLUDED.source_payload,
                    updated_at = now()
                """,
                rows,
            )
        conn.commit()
    return len(rows)
