from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from statistics import mean
from typing import Any

from psycopg2.extras import Json, execute_values

from backend.repositories import programas_repository
from backend.repositories.base import cursor, fetch_all, fetch_one, relation_exists
from intelligence.domain_benchmark_layer import build_domain_benchmark
from intelligence.domain_taxonomy_layer import build_domain_taxonomy_from_program
from intelligence.common import clamp, normalize_key
from intelligence.program_intelligence_engine import build_program_intelligence_for_program
from intelligence.skill_normalization_engine import normalize_skill_batch


SIMULATION_HORIZONS = (6, 12, 24)


@dataclass(frozen=True)
class CurriculumImpactSimulation:
    program_id: int
    program_name: str
    program_role: str
    horizon_months: int
    current_alignment_score: float
    current_risk_score: float
    projected_alignment_score: float
    projected_risk_score: float
    projected_employability_gain: float
    projected_gap_reduction: float
    confidence_score: float
    proposed_skills: list[str] = field(default_factory=list)
    normalized_skills: list[dict[str, Any]] = field(default_factory=list)
    risk_drivers: list[dict[str, Any]] = field(default_factory=list)
    supporting_evidence: dict[str, Any] = field(default_factory=dict)
    source_tables: list[str] = field(default_factory=list)
    explanation: str = ""
    simulation_key: str = ""
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = normalize_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _risk_level(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "observation"
    return "aligned"


def _load_program_base(program_id: int, *, db_name: str | None = None) -> dict[str, Any] | None:
    if programas_repository.fetch_program_base_row:
        row = programas_repository.fetch_program_base_row(program_id, db_name=db_name)
        if row:
            return dict(row)
    return None


def _load_program_intelligence(program_id: int, *, db_name: str | None = None) -> dict[str, Any] | None:
    if not relation_exists("program_intelligence", db_name=db_name):
        return None
    row = fetch_one(
        """
        SELECT *
        FROM program_intelligence
        WHERE program_id = %s
        ORDER BY generated_at DESC NULLS LAST
        LIMIT 1
        """,
        (program_id,),
        db_name=db_name,
    )
    return dict(row) if row else None


def _load_gap_rows(program_name: str, *, db_name: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if relation_exists("curriculum_gap_observatory", db_name=db_name):
        rows = fetch_all(
            """
            SELECT specialization, missing_skill, market_demand_score, curriculum_coverage_score,
                   urgency_score, emergence_score, recommendation, evidence, generated_at
            FROM curriculum_gap_observatory
            WHERE specialization ILIKE %s
            ORDER BY urgency_score DESC NULLS LAST, market_demand_score DESC NULLS LAST, missing_skill ASC
            """,
            (f"%{program_name}%",),
            db_name=db_name,
        )
    return [dict(row) for row in rows]


def _load_recommendation_rows(program_name: str, *, db_name: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if relation_exists("recommendation_observatory", db_name=db_name):
        rows = fetch_all(
            """
            SELECT recommendation_type, target_role, target_company, recommendation_payload,
                   recommendation_reasoning, recommendation_confidence, recommendation_evidence,
                   metric_period, generated_at,
                   estimated_alignment_increase, estimated_employability_gain, estimated_risk_reduction
            FROM recommendation_observatory
            WHERE target_role ILIKE %s OR recommendation_payload::text ILIKE %s
            ORDER BY recommendation_confidence DESC NULLS LAST, generated_at DESC NULLS LAST
            """,
            (f"%{program_name}%", f"%{program_name}%"),
            db_name=db_name,
        )
    return [dict(row) for row in rows]


def _load_skill_forecasts(*, db_name: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if relation_exists("market_forecasts", db_name=db_name):
        rows = fetch_all(
            """
            SELECT entity_type, entity_name, horizon_months, growth_velocity, forecast_confidence,
                   market_phase, first_seen_at, last_seen_at, evidence, updated_at AS generated_at
            FROM market_forecasts
            WHERE entity_type = 'skill'
            ORDER BY growth_velocity DESC NULLS LAST, forecast_confidence DESC NULLS LAST
            """,
            db_name=db_name,
        )
    return [dict(row) for row in rows]


def _normalize_program_skills(program_name: str, gap_rows: list[dict[str, Any]], recommendation_rows: list[dict[str, Any]], proposed_skills: list[str], *, db_name: str | None = None) -> list[dict[str, Any]]:
    raw_skills: list[str] = []
    raw_skills.extend([str(row.get("missing_skill") or "").strip() for row in gap_rows if str(row.get("missing_skill") or "").strip()])
    for row in recommendation_rows:
        payload = row.get("recommendation_payload") or {}
        if isinstance(payload, dict):
            raw_skills.extend([str(skill or "").strip() for skill in payload.get("recommended_skills", []) if str(skill or "").strip()])
    raw_skills.extend([str(skill or "").strip() for skill in proposed_skills if str(skill or "").strip()])
    raw_skills = _unique(raw_skills)
    if not raw_skills:
        return []
    normalized = normalize_skill_batch(raw_skills, db_name=db_name, persist=True, source=f"curriculum_simulator:{normalize_key(program_name)}")
    return [item.to_dict() for item in normalized]


def _gap_lookup(gap_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in gap_rows:
        missing_skill = str(row.get("missing_skill") or "").strip()
        if not missing_skill:
            continue
        lookup[normalize_key(missing_skill)] = dict(row)
    return lookup


def _forecast_lookup(forecast_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in forecast_rows:
        name = str(row.get("entity_name") or "").strip()
        if not name:
            continue
        lookup[normalize_key(name)] = dict(row)
    return lookup


def _build_risk_drivers(
    *,
    matched_gap_rows: list[dict[str, Any]],
    matched_forecasts: list[dict[str, Any]],
    normalized_skills: list[dict[str, Any]],
    projected_gap_reduction: float,
) -> list[dict[str, Any]]:
    drivers: list[dict[str, Any]] = []
    if matched_gap_rows:
        top_gap = matched_gap_rows[0]
        drivers.append(
            {
                "driver": "curriculum_gap",
                "value": round(_safe_float(top_gap.get("urgency_score")), 4),
                "impact": round(projected_gap_reduction, 4),
                "evidence": [str(top_gap.get("missing_skill") or "")],
            }
        )
    if matched_forecasts:
        drivers.append(
            {
                "driver": "market_pressure",
                "value": round(mean([_safe_float(row.get("growth_velocity")) for row in matched_forecasts]), 4),
                "impact": round(min(20.0, projected_gap_reduction * 0.5), 4),
                "evidence": [str(row.get("entity_name") or "") for row in matched_forecasts[:3]],
            }
        )
    if normalized_skills:
        drivers.append(
            {
                "driver": "skill_mappings",
                "value": round(mean([_safe_float(row.get("confidence_score")) for row in normalized_skills]), 4),
                "impact": round(min(15.0, len(normalized_skills) * 2.5), 4),
                "evidence": [str(row.get("canonical_skill") or "") for row in normalized_skills[:3]],
            }
        )
    return drivers


def _persist_gap_mappings(
    *,
    program_id: int,
    program_name: str,
    gap_rows: list[dict[str, Any]],
    normalized_skills: list[dict[str, Any]],
    db_name: str | None = None,
) -> int:
    if not gap_rows or not relation_exists("program_skill_gap", db_name=db_name):
        return 0
    skill_lookup = {normalize_key(str(row.get("canonical_skill") or "")): row for row in normalized_skills}
    rows: list[tuple[Any, ...]] = []
    for row in gap_rows:
        missing_skill = str(row.get("missing_skill") or "").strip()
        if not missing_skill:
            continue
        normalized_key = normalize_key(missing_skill)
        normalized = skill_lookup.get(normalized_key)
        market_demand = _safe_float(row.get("market_demand_score"))
        urgency = _safe_float(row.get("urgency_score"))
        emergence = _safe_float(row.get("emergence_score"))
        confidence = min(1.0, max(_safe_float(row.get("curriculum_coverage_score")) / 100.0, _safe_float(normalized.get("confidence_score")) if normalized else 0.0))
        employability_impact = clamp((market_demand * 0.5 + urgency * 0.35 + emergence * 0.15) / 100.0) * 100.0
        rows.append(
            (
                program_id,
                normalized_key or normalize_key(f"{program_name}:{missing_skill}"),
                normalized.get("canonical_skill_id") if normalized else None,
                normalized.get("canonical_skill") if normalized else missing_skill,
                "curricular",
                market_demand,
                employability_impact,
                urgency,
                confidence,
                Json(
                    _json_safe(
                        {
                            "specialization": row.get("specialization"),
                            "evidence": row.get("evidence"),
                            "recommendation": row.get("recommendation"),
                            "emergence_score": emergence,
                            "normalized_skill": normalized,
                        }
                    ),
                    dumps=lambda obj: json.dumps(obj, ensure_ascii=False),
                ),
            )
        )
    if not rows:
        return 0
    with cursor(db_name=db_name) as cur:
        execute_values(
            cur,
            """
            INSERT INTO program_skill_gap
                (program_id, gap_key, canonical_skill_id, missing_skill, gap_type,
                 market_pressure, employability_impact, urgency_score, confidence_score, source_payload)
            VALUES %s
            ON CONFLICT (program_id, gap_key) DO UPDATE SET
                canonical_skill_id = EXCLUDED.canonical_skill_id,
                missing_skill = EXCLUDED.missing_skill,
                gap_type = EXCLUDED.gap_type,
                market_pressure = EXCLUDED.market_pressure,
                employability_impact = EXCLUDED.employability_impact,
                urgency_score = EXCLUDED.urgency_score,
                confidence_score = EXCLUDED.confidence_score,
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            rows,
        )
    return len(rows)


def _persist_program_market_pressure(
    *,
    program_id: int,
    projected_risk_score: float,
    normalized_skills: list[dict[str, Any]],
    matched_forecasts: list[dict[str, Any]],
    gap_rows: list[dict[str, Any]],
    db_name: str | None = None,
) -> int:
    if not relation_exists("program_market_pressure", db_name=db_name):
        return 0
    urgency_component = (mean([_safe_float(row.get("urgency_score")) for row in gap_rows]) / 100.0) if gap_rows else 0.0
    forecast_component = mean([_safe_float(row.get("growth_velocity")) for row in matched_forecasts]) if matched_forecasts else 0.0
    risk_component = 1.0 - clamp(projected_risk_score / 100.0)
    base_pressure = clamp((urgency_component + forecast_component + risk_component) / 3.0)
    employer_count = len({str(row.get("target_company") or "") for row in matched_forecasts if str(row.get("target_company") or "")})
    skill_count = len(normalized_skills)
    rows = []
    for horizon in SIMULATION_HORIZONS:
        factor = {6: 0.92, 12: 1.0, 24: 1.08}.get(horizon, 1.0)
        rows.append(
            (
                program_id,
                horizon,
                round(clamp(base_pressure * factor) * 100.0, 4),
                employer_count,
                skill_count,
                round(clamp((skill_count / max(len(gap_rows), 1)) * 100.0), 4),
                round(min(1.0, max(0.35, mean([_safe_float(row.get("forecast_confidence")) for row in matched_forecasts]) if matched_forecasts else 0.5)), 4),
                Json(
                    _json_safe(
                        {
                            "projected_risk_score": projected_risk_score,
                            "matched_forecasts": matched_forecasts[:10],
                            "normalized_skills": normalized_skills[:10],
                        }
                    ),
                    dumps=lambda obj: json.dumps(obj, ensure_ascii=False),
                ),
            )
        )
    with cursor(db_name=db_name) as cur:
        execute_values(
            cur,
            """
            INSERT INTO program_market_pressure
                (program_id, horizon_months, pressure_score, employer_count, skill_count,
                 forecast_coverage_score, confidence_score, source_payload)
            VALUES %s
            ON CONFLICT (program_id, horizon_months) DO UPDATE SET
                pressure_score = EXCLUDED.pressure_score,
                employer_count = EXCLUDED.employer_count,
                skill_count = EXCLUDED.skill_count,
                forecast_coverage_score = EXCLUDED.forecast_coverage_score,
                confidence_score = EXCLUDED.confidence_score,
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            rows,
        )
    return len(rows)


def _persist_program_employability(
    *,
    program_id: int,
    current_alignment_score: float,
    projected_alignment_score: float,
    projected_employability_gain: float,
    projected_gap_reduction: float,
    confidence_score: float,
    supporting_evidence: dict[str, Any],
    db_name: str | None = None,
) -> int:
    if not relation_exists("program_employability_index", db_name=db_name):
        return 0
    employability_score = clamp(projected_alignment_score / 100.0) * 100.0
    rows = [
        (
            program_id,
            round(employability_score, 4),
            round(projected_employability_gain, 4),
            round(max(0.0, current_alignment_score - projected_alignment_score), 4),
            round(max(0.0, projected_alignment_score - current_alignment_score), 4),
            round(confidence_score, 4),
            Json(_json_safe(supporting_evidence), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
        )
    ]
    with cursor(db_name=db_name) as cur:
        execute_values(
            cur,
            """
            INSERT INTO program_employability_index
                (program_id, employability_score, employability_gain, employability_loss,
                 expected_alignment_improvement, confidence_score, source_payload)
            VALUES %s
            ON CONFLICT (program_id) DO UPDATE SET
                employability_score = EXCLUDED.employability_score,
                employability_gain = EXCLUDED.employability_gain,
                employability_loss = EXCLUDED.employability_loss,
                expected_alignment_improvement = EXCLUDED.expected_alignment_improvement,
                confidence_score = EXCLUDED.confidence_score,
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            rows,
        )
    return 1


def _persist_program_risk(
    *,
    program_id: int,
    projected_risk_score: float,
    confidence_score: float,
    explanation: str,
    supporting_evidence: dict[str, Any],
    db_name: str | None = None,
) -> int:
    if not relation_exists("program_risk_index", db_name=db_name):
        return 0
    rows = []
    for horizon in SIMULATION_HORIZONS:
        factor = {6: 0.92, 12: 1.0, 24: 1.08}.get(horizon, 1.0)
        risk_score = round(clamp(projected_risk_score * factor / 100.0) * 100.0, 4)
        rows.append(
            (
                program_id,
                horizon,
                risk_score,
                _risk_level(risk_score),
                explanation,
                round(confidence_score, 4),
                Json(_json_safe(supporting_evidence), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            )
        )
    with cursor(db_name=db_name) as cur:
        execute_values(
            cur,
            """
            INSERT INTO program_risk_index
                (program_id, horizon_months, risk_score, risk_level, risk_explanation, confidence_score, source_payload)
            VALUES %s
            ON CONFLICT (program_id, horizon_months) DO UPDATE SET
                risk_score = EXCLUDED.risk_score,
                risk_level = EXCLUDED.risk_level,
                risk_explanation = EXCLUDED.risk_explanation,
                confidence_score = EXCLUDED.confidence_score,
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            rows,
        )
    return len(rows)


def build_curriculum_impact_simulation(
    program_id: int,
    proposed_skills: list[str] | None = None,
    *,
    horizon_months: int = 12,
    db_name: str | None = None,
    persist: bool = True,
) -> CurriculumImpactSimulation:
    program = _load_program_base(program_id, db_name=db_name)
    if not program:
        raise KeyError(f"programa {program_id} not found")
    intelligence = _load_program_intelligence(program_id, db_name=db_name) or build_program_intelligence_for_program(program_id, db_name=db_name).to_dict()
    program_name = str(intelligence.get("program_name") or program.get("nombre_especializacion") or program.get("nombre") or "").strip()
    program_role = str(intelligence.get("program_role") or program.get("rol") or "").strip()
    base_evidence = intelligence.get("supporting_evidence") or {}
    domain_taxonomy = build_domain_taxonomy_from_program(
        program_name=program_name,
        program_role=program_role,
        microcurriculum_context={
            "detected_domain": str(base_evidence.get("domain_taxonomy", {}).get("domain_key") or "").strip(),
            "detected_subdomain": str(base_evidence.get("domain_taxonomy", {}).get("subdomain") or "").strip(),
            "technical_skills": list(base_evidence.get("program_skills") or []),
            "transversal_skills": [],
            "subjects": [],
            "tools": [],
            "technologies": [],
            "keywords": [],
            "labor_roles": [program_role] if program_role else [],
            "real_market_gaps": [str(item.get("missing_skill") or "") for item in intelligence.get("top_gaps", []) if str(item.get("missing_skill") or "").strip()],
            "strengthening_areas": intelligence.get("recommended_actions") or [],
        },
        skills=list(base_evidence.get("program_skills") or []),
    )
    domain_benchmark = build_domain_benchmark(domain_taxonomy.domain_key)
    current_alignment = _safe_float(intelligence.get("alignment_score") or program.get("promedio_match_mercado") or 0.0) * 1.0
    current_risk = _safe_float(intelligence.get("risk_score") or 0.0)

    gap_rows = _load_gap_rows(program_name, db_name=db_name)
    recommendation_rows = _load_recommendation_rows(program_name, db_name=db_name)
    forecast_rows = _load_skill_forecasts(db_name=db_name)

    proposed_raw = [str(skill or "").strip() for skill in (proposed_skills or []) if str(skill or "").strip()]
    if not proposed_raw:
        proposed_raw.extend([str(row.get("missing_skill") or "").strip() for row in gap_rows if str(row.get("missing_skill") or "").strip()])
    if not proposed_raw:
        for row in recommendation_rows:
            payload = row.get("recommendation_payload") or {}
            if isinstance(payload, dict):
                proposed_raw.extend([str(skill or "").strip() for skill in payload.get("recommended_skills", []) if str(skill or "").strip()])
    proposed_raw = _unique(proposed_raw)

    normalized_skills = _normalize_program_skills(program_name, gap_rows, recommendation_rows, proposed_raw, db_name=db_name)
    gap_lookup = _gap_lookup(gap_rows)
    forecast_lookup = _forecast_lookup(forecast_rows)

    matched_gap_rows: list[dict[str, Any]] = []
    matched_forecasts: list[dict[str, Any]] = []
    matched_canonical: set[str] = set()
    for skill in normalized_skills:
        canonical = normalize_key(str(skill.get("canonical_skill") or ""))
        if not canonical:
            continue
        if canonical in gap_lookup and canonical not in matched_canonical:
            matched_gap_rows.append(gap_lookup[canonical])
            matched_canonical.add(canonical)
        if canonical in forecast_lookup:
            matched_forecasts.append(forecast_lookup[canonical])

    matched_gap_count = len(matched_gap_rows)
    total_gap_count = max(len(gap_rows), len(gap_lookup), 1)
    horizon_weight = {6: 0.35, 12: 0.65, 24: 1.0}.get(int(horizon_months), max(0.25, min(1.0, horizon_months / 24.0)))
    horizon_momentum = {6: 0.55, 12: 0.8, 24: 1.0}.get(int(horizon_months), max(0.25, min(1.0, horizon_months / 24.0)))
    projected_gap_reduction = round(
        clamp(((matched_gap_count / total_gap_count) * 100.0) * horizon_momentum + (len(normalized_skills) * 1.5), 0.0, 100.0),
        4,
    )

    market_pressure = mean([_safe_float(row.get("market_demand_score")) for row in matched_gap_rows]) if matched_gap_rows else 0.0
    forecast_pressure = mean([_safe_float(row.get("growth_velocity")) for row in matched_forecasts]) if matched_forecasts else 0.0
    urgency_pressure = mean([_safe_float(row.get("urgency_score")) for row in matched_gap_rows]) if matched_gap_rows else 0.0
    normalized_confidence = mean([_safe_float(row.get("confidence_score")) for row in normalized_skills]) if normalized_skills else 0.0

    projected_alignment_gain = round(
        clamp(
            (
                (projected_gap_reduction * 0.10)
                + (market_pressure * 0.05)
                + (forecast_pressure * 0.25)
                + (urgency_pressure * 0.05)
            )
            * horizon_weight,
            0.0,
            100.0,
        ),
        4,
    )
    projected_alignment_score = round(min(100.0, current_alignment + projected_alignment_gain), 4)
    projected_risk_score = round(
        max(
            0.0,
            current_risk
            - (
                (
                    (projected_gap_reduction * 0.08)
                    + (forecast_pressure * 0.20)
                    + (normalized_confidence * 2.0)
                )
                * horizon_weight
            ),
        ),
        4,
    )
    projected_employability_gain = round(
        clamp(projected_alignment_gain * 0.8 + (forecast_pressure * 0.35 * horizon_weight) + (market_pressure * 0.08), 0.0, 100.0),
        4,
    )
    confidence_score = round(clamp((normalized_confidence * 0.45) + (min(len(normalized_skills), 8) / 10.0) + (len(matched_gap_rows) / max(total_gap_count, 1) * 0.35) + (len(matched_forecasts) / max(len(normalized_skills), 1) * 0.2), 0.15, 0.98), 4)

    risk_drivers = _build_risk_drivers(
        matched_gap_rows=matched_gap_rows,
        matched_forecasts=matched_forecasts,
        normalized_skills=normalized_skills,
        projected_gap_reduction=projected_gap_reduction,
    )
    explanation = (
        f"El programa '{program_name}' presenta {len(gap_rows)} brechas observadas y {len(normalized_skills)} habilidades propuestas. "
        f"La simulación proyecta una alineación de {projected_alignment_score:.1f}% y una reducción de riesgo de {current_risk - projected_risk_score:.1f} puntos "
        f"si se incorporan las habilidades priorizadas. "
        f"Dominio académico inferido: {domain_taxonomy.domain_label} / {domain_taxonomy.subdomain or 'general'}."
    )
    source_tables = [
        "especializaciones",
        "program_intelligence",
        "curriculum_gap_observatory",
        "recommendation_observatory",
        "market_forecasts",
        "skill_normalization_mappings",
    ]
    supporting_evidence = {
        "current_alignment_score": current_alignment,
        "current_risk_score": current_risk,
        "gap_count": len(gap_rows),
        "matched_gap_count": matched_gap_count,
        "matched_forecast_count": len(matched_forecasts),
        "recommendation_count": len(recommendation_rows),
        "normalized_skills": normalized_skills[:10],
        "gap_samples": matched_gap_rows[:5],
        "forecast_samples": matched_forecasts[:5],
        "horizon_months": horizon_months,
        "horizon_weight": horizon_weight,
        "horizon_momentum": horizon_momentum,
        "projected_alignment_delta": projected_alignment_gain,
        "projected_risk_delta": round(max(0.0, current_risk - projected_risk_score), 4),
        "projected_employability_delta": projected_employability_gain,
        "domain_taxonomy": domain_taxonomy.to_dict(),
        "domain_benchmark": domain_benchmark.to_dict(),
        "source_tables": source_tables,
    }
    simulation_key = normalize_key(f"program:{program_id}:horizon:{horizon_months}:{','.join([str(item.get('canonical_skill') or '') for item in normalized_skills])}")
    result = CurriculumImpactSimulation(
        program_id=program_id,
        program_name=program_name,
        program_role=program_role,
        horizon_months=horizon_months,
        current_alignment_score=round(current_alignment, 4),
        current_risk_score=round(current_risk, 4),
        projected_alignment_score=projected_alignment_score,
        projected_risk_score=projected_risk_score,
        projected_employability_gain=projected_employability_gain,
        projected_gap_reduction=projected_gap_reduction,
        confidence_score=confidence_score,
        proposed_skills=proposed_raw,
        normalized_skills=normalized_skills,
        risk_drivers=risk_drivers,
        supporting_evidence=supporting_evidence,
        source_tables=source_tables,
        explanation=explanation,
        simulation_key=simulation_key,
        generated_at=datetime.now(UTC).isoformat(),
    )

    if persist:
        persist_curriculum_simulation(result, db_name=db_name)
        _persist_gap_mappings(program_id=program_id, program_name=program_name, gap_rows=gap_rows, normalized_skills=normalized_skills, db_name=db_name)
        _persist_program_market_pressure(
            program_id=program_id,
            projected_risk_score=projected_risk_score,
            normalized_skills=normalized_skills,
            matched_forecasts=matched_forecasts,
            gap_rows=gap_rows,
            db_name=db_name,
        )
        _persist_program_employability(
            program_id=program_id,
            current_alignment_score=current_alignment,
            projected_alignment_score=projected_alignment_score,
            projected_employability_gain=projected_employability_gain,
            projected_gap_reduction=projected_gap_reduction,
            confidence_score=confidence_score,
            supporting_evidence=supporting_evidence,
            db_name=db_name,
        )
        _persist_program_risk(
            program_id=program_id,
            projected_risk_score=projected_risk_score,
            confidence_score=confidence_score,
            explanation=explanation,
            supporting_evidence=supporting_evidence,
            db_name=db_name,
        )
    return result


def persist_curriculum_simulation(result: CurriculumImpactSimulation, *, db_name: str | None = None) -> int:
    if not relation_exists("curriculum_simulations", db_name=db_name):
        return 0
    row = (
        result.simulation_key,
        result.program_id,
        Json(_json_safe(result.proposed_skills), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
        result.projected_alignment_score,
        result.projected_risk_score,
        result.projected_employability_gain,
        result.projected_gap_reduction,
        result.confidence_score,
        result.explanation,
        Json(_json_safe(result.supporting_evidence), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
        datetime.now(UTC),
        datetime.now(UTC),
    )
    with cursor(db_name=db_name) as cur:
        execute_values(
            cur,
            """
            INSERT INTO curriculum_simulations
                (simulation_key, program_id, proposed_skills, projected_alignment_score,
                 projected_risk_score, projected_employability_gain, projected_gap_reduction,
                 confidence_score, explanation, source_payload, generated_at, updated_at)
            VALUES %s
            ON CONFLICT (simulation_key) DO UPDATE SET
                program_id = EXCLUDED.program_id,
                proposed_skills = EXCLUDED.proposed_skills,
                projected_alignment_score = EXCLUDED.projected_alignment_score,
                projected_risk_score = EXCLUDED.projected_risk_score,
                projected_employability_gain = EXCLUDED.projected_employability_gain,
                projected_gap_reduction = EXCLUDED.projected_gap_reduction,
                confidence_score = EXCLUDED.confidence_score,
                explanation = EXCLUDED.explanation,
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            [row],
        )
    return 1
