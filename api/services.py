from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from backend.repositories import microcurriculum_context_repository, programas_repository
from backend.repositories import matches_repository, skills_repository
from backend.services import dashboard_service
from backend.services import recommendation_service
from backend.services.normalization_service import basic_text_key, normalize_program_row

from api.database import fetch_all, fetch_one, relation_exists, relation_has_rows, startup_validate, table_row_count
from services.executive_ai_service import (
    ask_observatory as executive_ask_observatory,
    build_executive_narrative as build_executive_ai_narrative,
    build_program_summary as build_executive_program_summary,
    build_recommendation_explanation as build_executive_recommendation_explanation,
)
from intelligence.predictive_intelligence_engine import (
    build_career_intelligence,
    build_curriculum_risk_index,
    build_executive_metrics,
    build_market_demand_forecasts,
    build_recommendation_v2,
    build_university_market_alignment,
    detect_emerging_skills,
    _safe_float as predictive_safe_float,
)
from intelligence.executive_observatory_engine import build_executive_observatory_v2
from intelligence.curriculum_impact_simulator import build_curriculum_impact_simulation
from intelligence.forecast_expansion_engine import build_forecast_summary
from intelligence.program_intelligence_engine import (
    build_program_intelligence,
    build_program_intelligence_for_program,
    persist_program_intelligence,
)
from intelligence.semantic_search_engine import semantic_search
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map
from intelligence.common import normalize_key


DEFAULT_LIMIT = 20
MAX_LIMIT = 100
logger = logging.getLogger(__name__)

LABOR_CORE_TABLES = ("empleos", "canonical_jobs", "silver_normalized_jobs", "gold_validated_jobs")
CURRICULUM_CORE_TABLES = ("especializaciones", "skills", "labor_program_skill_matches")
ML_CORE_TABLES = ("ml_predictions", "ml_program_job_matches", "ml_training_examples")
OBSERVATORY_TABLES = (
    "observatory_metrics",
    "curriculum_gap_observatory",
    "recommendation_observatory",
    "semantic_role_graph",
    "company_observatory",
    "emerging_technology_observatory",
)
AREA_KEYWORDS_BY_KEY = {
    "datos": ("datos", "data", "analytics", "analitica", "bi", "business intelligence"),
    "tecnologia": ("software", "tecnologia", "cloud", "devops", "arquitectura", "sistemas"),
    "negocios": ("negocio", "gerencia", "marketing", "ventas", "finanzas", "gestion"),
    "operaciones": ("operaciones", "proyectos", "procesos", "calidad", "riesgo", "cumplimiento"),
}


def _log_fallback(endpoint: str, exc: Exception) -> None:
    logger.warning("%s fallback activated: %s", endpoint, exc, exc_info=True)


def _safe_program_base_row(program_id: int, *, db_name: str | None = None) -> dict[str, Any] | None:
    try:
        row = programas_repository.fetch_program_base_row(program_id, db_name=db_name)
        return dict(row) if row else None
    except Exception:
        return None


def _safe_program_name(program_id: int, *, db_name: str | None = None) -> str:
    row = _safe_program_base_row(program_id, db_name=db_name)
    if not row:
        return f"Programa {program_id}"
    return str(row.get("nombre_especializacion") or row.get("nombre") or f"Programa {program_id}")


def _fallback_skill_list(raw_skills: list[Any] | None = None) -> list[dict[str, Any]]:
    skills = []
    for index, item in enumerate(raw_skills or []):
        if isinstance(item, dict):
            name = str(item.get("nombre") or item.get("name") or item.get("skill") or f"Skill {index + 1}")
            skill_id = int(item.get("skill_id") or item.get("id") or index + 1)
        else:
            name = str(item)
            skill_id = index + 1
        skills.append({"skill_id": skill_id, "nombre": name, "conteo": int(getattr(item, "conteo", 1) or 1)})
    return skills


def _fallback_curriculum_risk(program_id: int, *, db_name: str | None = None, reason: str = "fallback") -> dict[str, Any]:
    program_name = _safe_program_name(program_id, db_name=db_name)
    intelligence = {}
    try:
        intelligence = get_program_intelligence(program_id)
    except Exception:
        intelligence = {}
    risk_score = float(intelligence.get("risk_score") or 0.0)
    return {
        "program_id": program_id,
        "program_name": program_name,
        "risk_score": risk_score,
        "risk_level": str(intelligence.get("risk_level") or ("critical" if risk_score >= 75 else "medium" if risk_score >= 50 else "low")),
        "risk_drivers": intelligence.get("risk_drivers") or [],
        "recommended_actions": intelligence.get("recommended_actions") or [],
        "supporting_evidence": {
            "reason": reason,
            "program_intelligence": intelligence,
        },
        "source_tables": ["program_intelligence", "program_risk_index", "curriculum_gap_observatory", "recommendation_observatory"],
        "confidence": float(intelligence.get("confidence") or 0.0),
    }


def _fallback_alignment(program_id: int, *, db_name: str | None = None, reason: str = "fallback") -> dict[str, Any]:
    program_name = _safe_program_name(program_id, db_name=db_name)
    intelligence = {}
    try:
        intelligence = get_program_intelligence(program_id)
    except Exception:
        intelligence = {}
    alignment_score = float(intelligence.get("alignment_score") or 0.0)
    return {
        "program_id": program_id,
        "program_name": program_name,
        "alignment_score": alignment_score,
        "alignment_level": str(intelligence.get("alignment_level") or ("high" if alignment_score >= 70 else "medium" if alignment_score >= 50 else "low")),
        "current_alignment": alignment_score,
        "projected_alignment_if_added": min(100.0, alignment_score + 10.0),
        "missing_skills": [str(item.get("missing_skill") or item.get("skill") or item) for item in (intelligence.get("top_gaps") or [])[:6]],
        "emerging_skills": [str(item.get("skill") or item.get("missing_skill") or item) for item in (intelligence.get("forecast_signals") or [])[:6]],
        "company_demand_score": 0.0,
        "labor_demand_score": 0.0,
        "forecasted_demand_score": 0.0,
        "supporting_evidence": {
            "reason": reason,
            "program_intelligence": intelligence,
        },
        "source_tables": ["program_intelligence", "market_forecasts", "company_observatory", "curriculum_gap_observatory"],
        "confidence": float(intelligence.get("confidence") or 0.0),
    }


def _fallback_curriculum_simulation(
    program_id: int,
    *,
    proposed_skills: list[str] | None = None,
    horizon_months: int = 12,
    db_name: str | None = None,
    reason: str = "fallback",
) -> dict[str, Any]:
    program_name = _safe_program_name(program_id, db_name=db_name)
    skills = [skill.strip() for skill in (proposed_skills or []) if str(skill).strip()]
    current_alignment = _fallback_alignment(program_id, db_name=db_name)["current_alignment"]
    current_risk = _fallback_curriculum_risk(program_id, db_name=db_name)["risk_score"]
    projected_alignment = min(100.0, current_alignment + min(12.0, 2.0 + len(skills) * 1.5))
    projected_risk = max(0.0, current_risk - min(15.0, 3.0 + len(skills) * 1.2))
    projected_employability_gain = round(min(20.0, len(skills) * 3.5 + horizon_months / 12.0 * 2.5), 4)
    projected_gap_reduction = round(min(25.0, len(skills) * 4.0 + horizon_months / 12.0 * 3.0), 4)
    return {
        "program_id": program_id,
        "program_name": program_name,
        "program_role": "",
        "horizon_months": horizon_months,
        "current_alignment_score": current_alignment,
        "current_risk_score": current_risk,
        "projected_alignment_score": projected_alignment,
        "projected_risk_score": projected_risk,
        "projected_employability_gain": projected_employability_gain,
        "projected_gap_reduction": projected_gap_reduction,
        "confidence_score": 0.0,
        "proposed_skills": skills,
        "normalized_skills": [{"skill": skill, "confidence": 0.0} for skill in skills],
        "risk_drivers": [],
        "supporting_evidence": {
            "reason": reason,
            "program_name": program_name,
            "selected_skills": skills,
        },
        "source_tables": ["program_intelligence", "curriculum_gap_observatory", "recommendation_observatory", "market_forecasts"],
        "explanation": "Simulación pendiente de datos suficientes. Se muestra una proyección conservadora basada en la evidencia disponible.",
        "simulation_key": f"fallback-{program_id}-{horizon_months}",
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _fallback_forecast_summary(*, limit: int = DEFAULT_LIMIT, reason: str = "fallback") -> dict[str, Any]:
    bounded_limit = _bounded(limit)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_tables": ["market_forecasts", "skill_trend_forecast", "technology_forecasts", "company_forecasts", "role_forecasts"],
        "total_records": 0,
        "counts": {"skill": 0, "technology": 0, "company": 0, "role": 0},
        "coverage": {"skill": 0.0, "technology": 0.0, "company": 0.0, "role": 0.0},
        "top_skills": [],
        "top_technologies": [],
        "top_companies": [],
        "top_roles": [],
        "limit": bounded_limit,
        "fallback_reason": reason,
    }


def _fallback_executive_observatory(*, reason: str = "fallback") -> dict[str, Any]:
    program_count = 0
    try:
        program_count = int((fetch_one("SELECT COUNT(*)::int AS total FROM program_intelligence") or {}).get("total") or 0)
    except Exception:
        program_count = 0
    return {
        "metrics": [],
        "alignment_average": 0.0,
        "high_risk_programs": [],
        "medium_risk_programs": [],
        "low_risk_programs": [],
        "programs_analyzed": program_count,
        "critical_gaps": [],
        "top_emerging_skills": [],
        "top_recommendations": [],
        "top_programs": [],
        "at_risk_programs": [],
        "executive_narrative": "El observatorio presenta una vista parcial mientras se recupera la evidencia de producción.",
        "source_tables": [
            "program_intelligence",
            "observatory_metrics",
            "recommendation_observatory",
            "curriculum_gap_observatory",
            "market_forecasts",
        ],
        "confidence": 0.0,
        "fallback_reason": reason,
    }


def _bounded(value: int, *, default: int = DEFAULT_LIMIT) -> int:
    try:
        integer = int(value)
    except Exception:
        integer = default
    return max(1, min(integer, MAX_LIMIT))


def _offset(value: int) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _envelope(items: list[dict[str, Any]], *, limit: int, offset: int, total: int, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "items": items[offset : offset + limit],
        "count": total,
        "limit": limit,
        "offset": offset,
        "filters": filters or {},
    }


def _serialize_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        if hasattr(row, "to_dict"):
            result.append(dict(row.to_dict()))
        elif isinstance(row, dict):
            result.append(dict(row))
        else:
            result.append(dict(row))
    return result


def _column_exists(table: str, column: str) -> bool:
    row = fetch_one(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        ) AS exists
        """,
        (table, column),
    )
    return bool(row and row.get("exists"))


def _latest_timestamp(table: str) -> str | None:
    try:
        candidates = [column for column in ("generated_at", "updated_at", "created_at") if _column_exists(table, column)]
        for column in candidates:
            row = fetch_one(f"SELECT MAX({column}) AS latest FROM {table}")
            value = row.get("latest") if row else None
            if value:
                return value.isoformat() if hasattr(value, "isoformat") else str(value)
    except Exception:
        return None
    return None


def _database_connected() -> bool:
    try:
        row = fetch_one("SELECT 1 AS ok")
        return bool(row and row.get("ok"))
    except Exception:
        return False


def _tables_present(table_names: tuple[str, ...]) -> bool:
    try:
        return all(relation_exists(name) for name in table_names)
    except Exception:
        return False


def _observatory_status_payload() -> dict[str, Any]:
    observatory_tables = {}
    for table in OBSERVATORY_TABLES:
        try:
            observatory_tables[table] = relation_exists(table)
        except Exception:
            observatory_tables[table] = False
    missing_tables = [table for table, exists in observatory_tables.items() if not exists]
    completion_percentage = round((len(OBSERVATORY_TABLES) - len(missing_tables)) / max(len(OBSERVATORY_TABLES), 1), 4)
    status = "observatory_ready" if not missing_tables else "partial_observatory"
    observatory_freshness = {
        table: {
            "rows": table_row_count(table),
            "latest": _latest_timestamp(table),
        }
        for table, exists in observatory_tables.items()
        if exists
    }
    return {
        "status": status,
        "observatory_tables": observatory_tables,
        "missing_tables": missing_tables,
        "completion_percentage": completion_percentage,
        "observatory_freshness": observatory_freshness,
    }


def get_health_snapshot() -> dict[str, Any]:
    database_ok = _database_connected()
    labor_core_ok = _tables_present(LABOR_CORE_TABLES)
    curriculum_core_ok = _tables_present(CURRICULUM_CORE_TABLES)
    ml_core_ok = _tables_present(ML_CORE_TABLES)
    observatory_status = _observatory_status_payload()
    observatory_ready = observatory_status["completion_percentage"] >= 1.0
    status = "unhealthy"
    if database_ok:
        if labor_core_ok and curriculum_core_ok and ml_core_ok:
            status = "observatory_ready" if observatory_ready else "healthy"
        else:
            status = "degraded"
    return {
        "status": status,
        "database": "connected" if database_ok else "unavailable",
        "timestamp": datetime.now(UTC),
        "layers": {
            "database": database_ok,
            "labor_core": labor_core_ok,
            "curriculum_core": curriculum_core_ok,
            "ml_core": ml_core_ok,
            "observatory": observatory_ready,
        },
        "checks": {
            "database": database_ok,
            "labor_core": labor_core_ok,
            "curriculum_core": curriculum_core_ok,
            "ml_core": ml_core_ok,
            "observatory": observatory_ready,
            "labor_core_tables": {table: relation_exists(table) for table in LABOR_CORE_TABLES},
            "curriculum_core_tables": {table: relation_exists(table) for table in CURRICULUM_CORE_TABLES},
            "ml_core_tables": {table: relation_exists(table) for table in ML_CORE_TABLES},
        },
        "observatory_status": observatory_status,
        "observatory_freshness": observatory_status["observatory_freshness"],
    }


def get_readiness_snapshot() -> dict[str, Any]:
    snapshot = get_health_snapshot()
    ready = bool(
        snapshot["layers"]["database"]
        and snapshot["layers"]["labor_core"]
        and snapshot["layers"]["curriculum_core"]
        and snapshot["layers"]["ml_core"]
    )
    snapshot["status"] = "ready" if ready else "degraded"
    return snapshot


def get_observatory_status() -> dict[str, Any]:
    observatory_status = _observatory_status_payload()
    return {
        "status": observatory_status["status"],
        "observatory_tables": observatory_status["observatory_tables"],
        "missing_tables": observatory_status["missing_tables"],
        "completion_percentage": observatory_status["completion_percentage"],
    }


def list_observatory_metrics(*, limit: int = DEFAULT_LIMIT, offset: int = 0, metric_category: str | None = None, metric_name: str | None = None) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    clauses: list[str] = []
    params: list[Any] = []
    if metric_category:
        clauses.append("metric_category = %s")
        params.append(metric_category)
    if metric_name:
        clauses.append("metric_name = %s")
        params.append(metric_name)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = fetch_all(
        f"""
        SELECT metric_name, metric_category, metric_value, metric_period, confidence_score, generated_at, source_payload
        FROM observatory_metrics
        {where_sql}
        ORDER BY generated_at DESC NULLS LAST, metric_name ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [limit, offset]),
    )
    count_row = fetch_one(
        f"SELECT COUNT(*)::int AS total FROM observatory_metrics {where_sql}",
        tuple(params),
    )
    return _envelope(_serialize_rows(rows), limit=limit, offset=offset, total=int((count_row or {}).get("total") or 0), filters={"metric_category": metric_category, "metric_name": metric_name})


def list_curriculum_gaps(*, limit: int = DEFAULT_LIMIT, offset: int = 0, specialization: str | None = None) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    if relation_exists("curriculum_gap_observatory") and relation_has_rows("curriculum_gap_observatory"):
        clauses: list[str] = []
        params: list[Any] = []
        if specialization:
            clauses.append("specialization ILIKE %s")
            params.append(f"%{specialization}%")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = fetch_all(
            f"""
            SELECT specialization, missing_skill, market_demand_score, curriculum_coverage_score,
                   urgency_score, emergence_score, recommendation, evidence, generated_at
            FROM curriculum_gap_observatory
            {where_sql}
            ORDER BY urgency_score DESC NULLS LAST, market_demand_score DESC NULLS LAST, missing_skill ASC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )
        count_row = fetch_one(
            f"SELECT COUNT(*)::int AS total FROM curriculum_gap_observatory {where_sql}",
            tuple(params),
        )
        return _envelope(_serialize_rows(rows), limit=limit, offset=offset, total=int((count_row or {}).get("total") or 0), filters={"specialization": specialization})

    intelligence = build_market_skill_intelligence_map(include_database=True, write_output=False)
    rows = [gap.to_dict() for gap in intelligence.curriculum_gaps]
    if specialization:
        rows = [row for row in rows if specialization.casefold() in str(row.get("specialization") or "").casefold()]
    return _envelope(rows, limit=limit, offset=offset, total=len(rows), filters={"specialization": specialization, "source": "market_skill_intelligence"})


def list_recommendations(*, limit: int = DEFAULT_LIMIT, offset: int = 0, recommendation_type: str | None = None, target_company: str | None = None) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    if relation_exists("recommendation_observatory") and relation_has_rows("recommendation_observatory"):
        clauses: list[str] = []
        params: list[Any] = []
        if recommendation_type:
            clauses.append("recommendation_type = %s")
            params.append(recommendation_type)
        if target_company:
            clauses.append("target_company ILIKE %s")
            params.append(f"%{target_company}%")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = fetch_all(
            f"""
            SELECT recommendation_type, target_role, target_company,
                   recommendation_payload, recommendation_reasoning,
                   recommendation_confidence, recommendation_evidence,
                   estimated_alignment_increase, estimated_employability_gain, estimated_risk_reduction,
                   metric_period, generated_at
            FROM recommendation_observatory
            {where_sql}
            ORDER BY recommendation_confidence DESC NULLS LAST, target_role ASC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )
        count_row = fetch_one(
            f"SELECT COUNT(*)::int AS total FROM recommendation_observatory {where_sql}",
            tuple(params),
        )
        return _envelope(_serialize_rows(rows), limit=limit, offset=offset, total=int((count_row or {}).get("total") or 0), filters={"recommendation_type": recommendation_type, "target_company": target_company})

    intelligence = build_market_skill_intelligence_map(include_database=True, write_output=False)
    rows = [
        {
            "recommendation_type": "curriculum",
            "target_role": intelligence.specialization_name,
            "target_company": "curriculum",
            "recommended_skills": [item.skill],
            "market_alignment_score": round(item.market_weight, 4),
            "top_companies": item.companies[:5],
            "recommendation_payload": {
                "recommended_skills": [item.skill],
                "market_alignment_score": round(item.market_weight, 4),
                "why_recommended": [item.recommendation],
            },
            "recommendation_reasoning": item.reason,
            "recommendation_confidence": item.market_weight,
            "recommendation_evidence": item.evidence_sources,
            "estimated_alignment_increase": round(item.market_weight * 10.0, 4),
            "estimated_employability_gain": round(item.market_weight * 8.0, 4),
            "estimated_risk_reduction": round(min(15.0, item.market_weight * 10.0), 4),
        }
        for item in intelligence.recommended_updates
    ]
    if recommendation_type:
        rows = [row for row in rows if row["recommendation_type"] == recommendation_type]
    if target_company:
        rows = [row for row in rows if target_company.casefold() in str(row.get("target_company") or "").casefold()]
    return _envelope(rows, limit=limit, offset=offset, total=len(rows), filters={"recommendation_type": recommendation_type, "target_company": target_company, "source": "market_skill_intelligence"})


def list_company_intelligence(*, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    if relation_exists("company_observatory") and relation_has_rows("company_observatory"):
        rows = fetch_all(
            """
            SELECT company, dominant_stack, dominant_cluster, hiring_velocity,
                   ai_adoption_score, cloud_maturity_score, bi_maturity_score,
                   technology_maturity, top_skills, top_clusters, evidence
            FROM company_observatory
            ORDER BY hiring_velocity DESC NULLS LAST, cloud_maturity_score DESC NULLS LAST
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        count_row = fetch_one("SELECT COUNT(*)::int AS total FROM company_observatory")
        return _envelope(_serialize_rows(rows), limit=limit, offset=offset, total=int((count_row or {}).get("total") or 0), filters={})
    return _envelope([], limit=limit, offset=offset, total=0, filters={})


def list_semantic_roles(*, limit: int = DEFAULT_LIMIT, offset: int = 0, role_family: str | None = None) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    if relation_exists("semantic_role_graph") and relation_has_rows("semantic_role_graph"):
        clauses: list[str] = []
        params: list[Any] = []
        if role_family:
            clauses.append("(source_role ILIKE %s OR target_role ILIKE %s)")
            params.extend([f"%{role_family}%", f"%{role_family}%"])
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = fetch_all(
            f"""
            SELECT source_role, target_role, similarity_score, transition_probability,
                   shared_skills, cluster_affinity, created_at
            FROM semantic_role_graph
            {where_sql}
            ORDER BY similarity_score DESC NULLS LAST, source_role ASC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )
        count_row = fetch_one(
            f"SELECT COUNT(*)::int AS total FROM semantic_role_graph {where_sql}",
            tuple(params),
        )
        return _envelope(_serialize_rows(rows), limit=limit, offset=offset, total=int((count_row or {}).get("total") or 0), filters={"role_family": role_family})
    return _envelope([], limit=limit, offset=offset, total=0, filters={"role_family": role_family})


def list_career_paths(*, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    if relation_exists("career_transitions") and relation_has_rows("career_transitions"):
        rows = fetch_all(
            """
            SELECT source_role, target_role, role_progression_probability,
                   transition_skill_gaps, recommended_next_skills
            FROM career_transitions
            ORDER BY role_progression_probability DESC NULLS LAST, source_role ASC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        count_row = fetch_one("SELECT COUNT(*)::int AS total FROM career_transitions")
        return _envelope(_serialize_rows(rows), limit=limit, offset=offset, total=int((count_row or {}).get("total") or 0), filters={})
    return _envelope([], limit=limit, offset=offset, total=0, filters={})


def _collect_market_forecast_rows(*, db_name: str | None = None) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []

    if relation_exists("market_forecasts", db_name=db_name) and relation_has_rows("market_forecasts", db_name=db_name):
        rows = fetch_all(
            """
            SELECT entity_type, entity_name, horizon_months, growth_velocity, forecast_confidence,
                   market_phase, first_seen_at, last_seen_at, evidence, generated_at
            FROM market_forecasts
            ORDER BY horizon_months ASC NULLS LAST, growth_velocity DESC NULLS LAST, forecast_confidence DESC NULLS LAST
            """,
            db_name=db_name,
        )
        for row in _serialize_rows(rows):
            if not row.get("horizon_months"):
                row["horizon_months"] = 12
            combined.append(row)

    if relation_exists("skill_trend_forecast", db_name=db_name) and relation_has_rows("skill_trend_forecast", db_name=db_name):
        rows = fetch_all(
            """
            SELECT canonical_skill_id, skill_name, horizon_months, growth_score, decline_score,
                   confidence_score, first_seen_at, last_seen_at, source_payload
            FROM skill_trend_forecast
            ORDER BY growth_score DESC NULLS LAST, skill_name ASC
            """,
            db_name=db_name,
        )
        for row in _serialize_rows(rows):
            combined.append(
                {
                    "entity_type": "skill",
                    "entity_name": row.get("skill_name"),
                    "horizon_months": row.get("horizon_months", 12),
                    "growth_velocity": round(predictive_safe_float(row.get("growth_score")) / 100.0, 4),
                    "forecast_confidence": predictive_safe_float(row.get("confidence_score")),
                    "market_phase": "emerging" if predictive_safe_float(row.get("growth_score")) >= 70 else "growing" if predictive_safe_float(row.get("growth_score")) >= 50 else "stable",
                    "first_seen_at": row.get("first_seen_at"),
                    "last_seen_at": row.get("last_seen_at"),
                    "evidence": row.get("source_payload") or {},
                    "canonical_skill_id": row.get("canonical_skill_id"),
                }
            )

    if relation_exists("technology_forecasts", db_name=db_name) and relation_has_rows("technology_forecasts", db_name=db_name):
        rows = fetch_all(
            """
            SELECT entity_name, horizon_months, growth_velocity, forecast_confidence, market_phase,
                   first_seen_at, last_seen_at, source_payload
            FROM technology_forecasts
            ORDER BY growth_velocity DESC NULLS LAST, entity_name ASC
            """,
            db_name=db_name,
        )
        for row in _serialize_rows(rows):
            combined.append(
                {
                    "entity_type": "technology",
                    "entity_name": row.get("entity_name"),
                    "horizon_months": row.get("horizon_months", 12),
                    "growth_velocity": row.get("growth_velocity", 0),
                    "forecast_confidence": row.get("forecast_confidence", 0),
                    "market_phase": row.get("market_phase", ""),
                    "first_seen_at": row.get("first_seen_at"),
                    "last_seen_at": row.get("last_seen_at"),
                    "evidence": row.get("source_payload") or {},
                }
            )

    if relation_exists("company_forecasts", db_name=db_name) and relation_has_rows("company_forecasts", db_name=db_name):
        rows = fetch_all(
            """
            SELECT entity_name, horizon_months, growth_velocity, forecast_confidence, market_phase,
                   first_seen_at, last_seen_at, source_payload
            FROM company_forecasts
            ORDER BY growth_velocity DESC NULLS LAST, entity_name ASC
            """,
            db_name=db_name,
        )
        for row in _serialize_rows(rows):
            combined.append(
                {
                    "entity_type": "company",
                    "entity_name": row.get("entity_name"),
                    "horizon_months": row.get("horizon_months", 12),
                    "growth_velocity": row.get("growth_velocity", 0),
                    "forecast_confidence": row.get("forecast_confidence", 0),
                    "market_phase": row.get("market_phase", ""),
                    "first_seen_at": row.get("first_seen_at"),
                    "last_seen_at": row.get("last_seen_at"),
                    "evidence": row.get("source_payload") or {},
                }
            )

    if relation_exists("role_forecasts", db_name=db_name) and relation_has_rows("role_forecasts", db_name=db_name):
        rows = fetch_all(
            """
            SELECT entity_name, horizon_months, growth_velocity, forecast_confidence, market_phase,
                   first_seen_at, last_seen_at, source_payload
            FROM role_forecasts
            ORDER BY growth_velocity DESC NULLS LAST, entity_name ASC
            """,
            db_name=db_name,
        )
        for row in _serialize_rows(rows):
            combined.append(
                {
                    "entity_type": "role",
                    "entity_name": row.get("entity_name"),
                    "horizon_months": row.get("horizon_months", 12),
                    "growth_velocity": row.get("growth_velocity", 0),
                    "forecast_confidence": row.get("forecast_confidence", 0),
                    "market_phase": row.get("market_phase", ""),
                    "first_seen_at": row.get("first_seen_at"),
                    "last_seen_at": row.get("last_seen_at"),
                    "evidence": row.get("source_payload") or {},
                }
            )

    seen: set[tuple[str, str, int]] = set()
    deduped: list[dict[str, Any]] = []
    for row in sorted(
        combined,
        key=lambda item: (
            str(item.get("entity_type") or ""),
            str(item.get("entity_name") or "").casefold(),
            int(item.get("horizon_months") or 0),
            predictive_safe_float(item.get("growth_velocity")),
            predictive_safe_float(item.get("forecast_confidence")),
        ),
        reverse=True,
    ):
        key = (
            str(row.get("entity_type") or ""),
            str(row.get("entity_name") or "").casefold(),
            int(row.get("horizon_months") or 0),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def list_market_forecast(
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    entity_type: str | None = None,
    entity_name: str | None = None,
    horizon_months: int | None = None,
) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    try:
        rows = _collect_market_forecast_rows()
        if not rows:
            rows = [item.to_dict() for item in build_market_demand_forecasts(persist=False, limit=limit)]
        if entity_type:
            rows = [row for row in rows if str(row.get("entity_type") or "") == entity_type]
        if entity_name:
            rows = [row for row in rows if entity_name.casefold() in str(row.get("entity_name") or "").casefold()]
        if horizon_months is not None:
            rows = [row for row in rows if int(row.get("horizon_months") or 0) == int(horizon_months)]
        return _envelope(rows, limit=limit, offset=offset, total=len(rows), filters={"entity_type": entity_type, "entity_name": entity_name, "horizon_months": horizon_months, "source": "predictive_engine"})
    except Exception as exc:
        _log_fallback("list_market_forecast", exc)
        return _envelope([], limit=limit, offset=offset, total=0, filters={"entity_type": entity_type, "entity_name": entity_name, "horizon_months": horizon_months, "source": "fallback"})


def list_emerging_skills(*, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    intelligence = build_market_skill_intelligence_map(include_database=True, write_output=False)
    rows = [signal.to_dict() for signal in intelligence.emerging_skills]
    predictive_rows = [signal.to_dict() for signal in detect_emerging_skills(limit=limit)]
    merged: dict[str, dict[str, Any]] = {}
    for row in rows + predictive_rows:
        key = str(row.get("skill") or row.get("skill_name") or "").strip()
        if not key:
            continue
        merged[key] = {
            **row,
            "skill": row.get("skill") or row.get("skill_name") or key,
            "skill_name": row.get("skill_name") or row.get("skill") or key,
        }
    rows = sorted(
        merged.values(),
        key=lambda item: (
            predictive_safe_float(item.get("market_weight", item.get("growth_rate", 0))),
            predictive_safe_float(item.get("confidence_score", item.get("market_signal_confidence", 0))),
        ),
        reverse=True,
    )
    return _envelope(rows, limit=limit, offset=offset, total=len(rows), filters={"coverage_status": "emerging"})


def get_curriculum_risk_index(program_id: int) -> dict[str, Any]:
    try:
        return build_curriculum_risk_index(program_id, persist=False).to_dict()
    except Exception as exc:
        _log_fallback("get_curriculum_risk_index", exc)
        return _fallback_curriculum_risk(program_id, reason=str(exc))


def get_university_market_alignment(program_id: int) -> dict[str, Any]:
    try:
        return build_university_market_alignment(program_id, persist=False).to_dict()
    except Exception as exc:
        _log_fallback("get_university_market_alignment", exc)
        return _fallback_alignment(program_id, reason=str(exc))


def get_critical_programs(*, limit: int = DEFAULT_LIMIT, offset: int = 0, horizon_months: int = 12) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    rows: list[dict[str, Any]] = []
    if relation_exists("program_risk_index") and relation_has_rows("program_risk_index"):
        rows = fetch_all(
            """
            SELECT
                COALESCE(pr.program_id, pi.program_id) AS program_id,
                COALESCE(pi.program_name, e.nombre, '') AS program_name,
                COALESCE(pi.program_role, COALESCE(e.rol, '')) AS program_role,
                COALESCE(pi.alignment_score, 0) AS alignment_score,
                COALESCE(pr.risk_score, pi.risk_score, 0) AS risk_score,
                COALESCE(pr.risk_level, pi.risk_level, 'aligned') AS risk_level,
                COALESCE(pi.gap_count, 0) AS gap_count,
                COALESCE((pi.top_gaps->0->>'missing_skill'), '') AS main_gap_driver,
                COALESCE((pi.recommended_actions->0), '') AS recommended_action,
                COALESCE(pei.employability_gain, 0) AS projected_employability_gain,
                COALESCE(pr.horizon_months, 12) AS horizon_months,
                COALESCE(pr.source_payload, pi.supporting_evidence, '{}'::jsonb) AS supporting_evidence,
                COALESCE(pi.source_tables, '[]'::jsonb) AS source_tables,
                COALESCE(pr.confidence_score, pi.confidence, 0) AS confidence,
                COALESCE(pr.generated_at, pi.generated_at::timestamptz, now()) AS generated_at
            FROM program_risk_index pr
            LEFT JOIN program_intelligence pi ON pi.program_id = pr.program_id
            LEFT JOIN especializaciones e ON e.id = pr.program_id
            LEFT JOIN program_employability_index pei ON pei.program_id = pr.program_id
            WHERE pr.horizon_months = %s
              AND COALESCE(pr.risk_score, pi.risk_score, 0) >= 75
            ORDER BY COALESCE(pr.risk_score, pi.risk_score, 0) DESC NULLS LAST, COALESCE(pi.alignment_score, 0) DESC NULLS LAST
            """,
            (horizon_months,),
        )
    if not rows and relation_exists("program_intelligence") and relation_has_rows("program_intelligence"):
        rows = fetch_all(
            """
            SELECT
                program_id,
                program_name,
                program_role,
                alignment_score,
                risk_score,
                risk_level,
                gap_count,
                COALESCE((top_gaps->0->>'missing_skill'), '') AS main_gap_driver,
                COALESCE((top_recommendations->0->>'recommendation_reasoning'), COALESCE((recommended_actions->0), '')) AS recommended_action,
                0 AS projected_employability_gain,
                12 AS horizon_months,
                COALESCE(supporting_evidence, '{}'::jsonb) AS supporting_evidence,
                COALESCE(source_tables, '[]'::jsonb) AS source_tables,
                confidence,
                generated_at
            FROM program_intelligence
            WHERE risk_score >= 75
            ORDER BY risk_score DESC NULLS LAST, alignment_score DESC NULLS LAST
            """,
            db_name=db_name,
        )
    try:
        rows = _serialize_rows(rows)
        return _envelope(rows, limit=limit, offset=offset, total=len(rows), filters={"horizon_months": horizon_months, "source": "program_risk_index"})
    except Exception as exc:
        _log_fallback("get_critical_programs", exc)
        return _envelope([], limit=limit, offset=offset, total=0, filters={"horizon_months": horizon_months, "source": "fallback"})


def get_curriculum_simulator(program_id: int, proposed_skills: str | None = None, *, horizon_months: int = 12) -> dict[str, Any]:
    skills: list[str] = []
    if proposed_skills:
        skills = [part.strip() for part in proposed_skills.split(",") if part.strip()]
    try:
        result = build_curriculum_impact_simulation(program_id, proposed_skills=skills, horizon_months=horizon_months, persist=True)
        return result.to_dict()
    except Exception as exc:
        _log_fallback("get_curriculum_simulator", exc)
        return _fallback_curriculum_simulation(program_id, proposed_skills=skills, horizon_months=horizon_months, reason=str(exc))


def get_forecast_summary(*, limit: int = 25) -> dict[str, Any]:
    try:
        return build_forecast_summary(persist=False, limit=_bounded(limit))
    except Exception as exc:
        _log_fallback("get_forecast_summary", exc)
        return _fallback_forecast_summary(limit=limit, reason=str(exc))


def get_career_intelligence(source_role: str | None = None, limit: int = 12) -> dict[str, Any]:
    try:
        payload = build_career_intelligence(source_role=source_role, limit=limit)
        return {
            "source_role": payload["source_role"],
            "transitions": payload["transitions"],
            "role_network": payload["role_network"][:limit],
            "source_tables": payload["source_tables"],
            "confidence": payload["confidence"],
        }
    except Exception as exc:
        _log_fallback("get_career_intelligence", exc)
        return {
            "source_role": source_role or "",
            "transitions": [],
            "role_network": [],
            "source_tables": ["career_transitions", "semantic_role_graph"],
            "confidence": 0.0,
        }


def get_executive_observatory() -> dict[str, Any]:
    try:
        result = build_executive_observatory_v2(persist=False)
        return result.to_dict()
    except Exception as exc:
        _log_fallback("get_executive_observatory", exc)
        return _fallback_executive_observatory(reason=str(exc))


def get_executive_narrative(program_id: int | None = None) -> dict[str, Any]:
    try:
        return build_executive_ai_narrative(program_id=program_id)
    except Exception as exc:
        _log_fallback("get_executive_narrative", exc)
        fallback = _fallback_executive_observatory(reason=str(exc))
        if program_id is not None:
            program_name = _safe_program_name(program_id)
            return {
                "program_id": program_id,
                "program_name": program_name,
                "narrative": fallback["executive_narrative"],
                "why_at_risk": "Narrativa disponible en modo fallback.",
                "evidence_sources": fallback["source_tables"],
                "source_tables": fallback["source_tables"],
                "supporting_evidence": fallback,
                "confidence": 0.0,
                "model": "deterministic-fallback",
                "generated_at": datetime.now(UTC).isoformat(),
            }
        return {
            "program_id": None,
            "program_name": "",
            "narrative": fallback["executive_narrative"],
            "why_at_risk": "",
            "evidence_sources": fallback["source_tables"],
            "source_tables": fallback["source_tables"],
            "supporting_evidence": fallback,
            "confidence": 0.0,
            "model": "deterministic-fallback",
            "generated_at": datetime.now(UTC).isoformat(),
        }


def get_program_summary(program_id: int) -> dict[str, Any]:
    try:
        return build_executive_program_summary(program_id)
    except Exception as exc:
        _log_fallback("get_program_summary", exc)
        program_name = _safe_program_name(program_id)
        fallback_risk = _fallback_curriculum_risk(program_id, reason=str(exc))
        fallback_alignment = _fallback_alignment(program_id, reason=str(exc))
        return {
            "program_id": program_id,
            "program_name": program_name,
            "summary": f"El programa '{program_name}' se presenta en modo de recuperación de evidencia mientras se estabiliza la integración de datos.",
            "why_at_risk": "El análisis ejecutivo está disponible en modo fallback porque una dependencia de backend no respondió a tiempo.",
            "microcurriculum_traceability": {
                "microcurriculum_name": program_name,
                "covered_skills": [],
                "transversal_skills": [],
                "missing_skills": fallback_alignment.get("missing_skills") or [],
                "strengthening_areas": [],
                "coverage": {},
                "labor_roles": [],
            },
            "evidence_sources": fallback_risk.get("source_tables") or fallback_alignment.get("source_tables") or [],
            "source_tables": fallback_risk.get("source_tables") or fallback_alignment.get("source_tables") or [],
            "supporting_evidence": {
                "program": {"especializacion_id": program_id, "nombre_especializacion": program_name},
                "risk": fallback_risk,
                "alignment": fallback_alignment,
            },
            "confidence": 0.0,
            "model": "deterministic-fallback",
            "generated_at": datetime.now(UTC).isoformat(),
        }


def get_recommendation_explanation(recommendation_id: int) -> dict[str, Any]:
    try:
        return build_executive_recommendation_explanation(recommendation_id)
    except Exception as exc:
        _log_fallback("get_recommendation_explanation", exc)
        return {
            "recommendation_id": recommendation_id,
            "recommendation_title": "Recomendación no disponible",
            "explanation": "La recomendación se encuentra en modo fallback mientras se recupera la evidencia completa.",
            "why_this_recommendation": "Se conservó el análisis con la evidencia disponible.",
            "evidence_sources": ["recommendation_observatory", "curriculum_gap_observatory", "market_forecasts", "program_intelligence"],
            "source_tables": ["recommendation_observatory", "curriculum_gap_observatory", "market_forecasts", "program_intelligence"],
            "supporting_evidence": {"reason": str(exc)},
            "confidence": 0.0,
            "model": "deterministic-fallback",
            "generated_at": datetime.now(UTC).isoformat(),
        }


def ask_observatory(
    question: str,
    *,
    program_id: int | None = None,
    recommendation_id: int | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return executive_ask_observatory(question, program_id=program_id, recommendation_id=recommendation_id, context=context)
    except Exception as exc:
        _log_fallback("ask_observatory", exc)
        fallback = get_executive_narrative(program_id=program_id) if program_id is not None else get_executive_narrative()
        return {
            "question": question,
            "answer": str(fallback.get("narrative") or fallback.get("summary") or question),
            "evidence_sources": fallback.get("evidence_sources") or fallback.get("source_tables") or ["program_intelligence", "executive_observatory"],
            "source_tables": fallback.get("source_tables") or ["program_intelligence", "executive_observatory"],
            "supporting_evidence": {"reason": str(exc), "question": question, "context": context},
            "confidence": float(fallback.get("confidence") or 0.0),
            "model": fallback.get("model") or "deterministic-fallback",
            "generated_at": datetime.now(UTC).isoformat(),
        }


def list_program_intelligence(*, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    try:
        if relation_exists("program_intelligence") and relation_has_rows("program_intelligence"):
            rows = fetch_all(
                """
                SELECT program_id, program_name, program_role, alignment_score, risk_score, risk_level,
                       gap_count, top_gaps, top_recommendations, forecast_signals, role_signals,
                       emerging_technologies, recommended_actions, business_justification,
                       supporting_evidence, source_tables, confidence, generated_at
                FROM program_intelligence
                ORDER BY risk_score DESC NULLS LAST, alignment_score DESC NULLS LAST, generated_at DESC NULLS LAST
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = _dedupe_program_rows(_serialize_rows(rows))
            total = len(rows)
            return {
                "items": rows[offset : offset + limit],
                "count": total,
                "total": total,
                "limit": limit,
                "offset": offset,
                "filters": {},
            }
        rows = [item.to_dict() for item in build_program_intelligence()]
        rows = _dedupe_program_rows(rows)
        total = len(rows)
        return {
            "items": rows[offset : offset + limit],
            "count": total,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {"source": "program_intelligence_engine"},
        }
    except Exception as exc:
        _log_fallback("list_program_intelligence", exc)
        return {
            "items": [],
            "count": 0,
            "total": 0,
            "limit": limit,
            "offset": offset,
            "filters": {"source": "fallback"},
        }


def get_program_intelligence(program_id: int) -> dict[str, Any]:
    try:
        if relation_exists("program_intelligence"):
            row = fetch_one(
                """
                SELECT program_id, program_name, program_role, alignment_score, risk_score, risk_level,
                       gap_count, top_gaps, top_recommendations, forecast_signals, role_signals,
                       emerging_technologies, recommended_actions, business_justification,
                       supporting_evidence, source_tables, confidence, generated_at
                FROM program_intelligence
                WHERE program_id = %s
                """,
                (program_id,),
            )
            if row:
                return dict(row)
        item = build_program_intelligence_for_program(program_id)
        return item.to_dict()
    except Exception as exc:
        _log_fallback("get_program_intelligence", exc)
        return {
            "program_id": program_id,
            "program_name": _safe_program_name(program_id),
            "program_role": "",
            "alignment_score": 0.0,
            "risk_score": 0.0,
            "risk_level": "low",
            "gap_count": 0,
            "top_gaps": [],
            "top_recommendations": [],
            "forecast_signals": [],
            "role_signals": [],
            "emerging_technologies": [],
            "recommended_actions": [],
            "business_justification": "Fallback generado mientras se recupera la evidencia completa.",
            "supporting_evidence": {"reason": str(exc)},
            "source_tables": ["program_intelligence"],
            "confidence": 0.0,
            "generated_at": datetime.now(UTC).isoformat(),
        }


def list_recommendations_v2(*, program_id: int | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    try:
        rows = [item.to_dict() for item in build_recommendation_v2(program_id=program_id, limit=limit)]
        return _envelope(rows, limit=limit, offset=offset, total=len(rows), filters={"program_id": program_id, "version": "v2", "source": "predictive_engine"})
    except Exception as exc:
        _log_fallback("list_recommendations_v2", exc)
        return _envelope([], limit=limit, offset=offset, total=0, filters={"program_id": program_id, "version": "v2", "source": "fallback"})


def build_semantic_search_corpus(entity_type: str) -> list[dict[str, Any]]:
    entity_type = (entity_type or "job").lower()
    if entity_type == "company" and relation_exists("company_observatory"):
        rows = fetch_all(
            """
            SELECT
                company AS title,
                company AS company,
                dominant_cluster AS role_family,
                dominant_stack AS description,
                top_skills AS skills
            FROM company_observatory
            ORDER BY hiring_velocity DESC NULLS LAST
            """
        )
        return _serialize_rows(rows)
    if entity_type == "skill":
        intelligence = build_market_skill_intelligence_map(include_database=True, write_output=False)
        return [
            {
                "id": signal.skill,
                "title": signal.skill,
                "skill": signal.skill,
                "description": signal.reason,
                "skills": [signal.skill, *signal.roles[:5]],
                "role_family": signal.occupational_cluster,
            }
            for signal in intelligence.market_skills
        ]
    if entity_type == "role" and relation_exists("semantic_role_graph"):
        rows = fetch_all(
            """
            SELECT
                source_role AS title,
                source_role,
                target_role,
                similarity_score,
                cluster_affinity,
                COALESCE(shared_skills, ARRAY[]::TEXT[]) AS skills,
                source_role AS role_family,
                COALESCE(shared_skills, ARRAY[]::TEXT[]) AS role_skills
            FROM semantic_role_graph
            ORDER BY similarity_score DESC NULLS LAST
            """
        )
        return _serialize_rows(rows)
    rows = fetch_all(
        """
            SELECT
                j.id,
                COALESCE(j.title, '') AS title,
                COALESCE(NULLIF(j.normalized_company, ''), j.company, '') AS company,
                COALESCE(j.description, '') AS description,
                COALESCE(
                    array_agg(js.canonical_skill ORDER BY js.confidence DESC)
                        FILTER (WHERE js.canonical_skill IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) AS skills
        FROM jobs j
        LEFT JOIN job_skills js ON js.job_id = j.id
        GROUP BY j.id
        ORDER BY j.updated_at DESC NULLS LAST, j.created_at DESC NULLS LAST
        LIMIT 200
        """
    )
    return _serialize_rows(rows)


def semantic_search_results(query: str, *, entity_type: str = "job", limit: int = 10) -> dict[str, Any]:
    limit = _bounded(limit)
    corpus = build_semantic_search_corpus(entity_type)
    results = semantic_search(query, corpus, entity_type=entity_type, limit=limit)
    items = [item.to_dict() for item in results]
    return {
        "query": query,
        "entity_type": entity_type,
        "count": len(items),
        "limit": limit,
        "items": items,
    }


def observatory_summary() -> dict[str, Any]:
    snapshot = get_health_snapshot()
    metrics = list_observatory_metrics(limit=10)
    recommendations = list_recommendations(limit=10)
    gaps = list_curriculum_gaps(limit=10)
    companies = list_company_intelligence(limit=10)
    return {
        "health": snapshot,
        "metrics": metrics,
        "recommendations": recommendations,
        "curriculum_gaps": gaps,
        "company_intelligence": companies,
    }


def _program_limit(value: int) -> int:
    try:
        integer = int(value)
    except Exception:
        integer = 25
    return max(1, min(integer, MAX_LIMIT))


def _dedupe_program_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = normalize_key(str(row.get("program_name") or row.get("nombre_especializacion") or row.get("nombre") or ""))
        if not key:
            key = f"id {int(row.get('program_id') or row.get('especializacion_id') or row.get('id') or 0)}"
        current = grouped.get(key)
        if current is None:
            grouped[key] = row
            continue
        current_score = (
            float(current.get("risk_score") or 0),
            float(current.get("alignment_score") or 0),
            int(current.get("gap_count") or 0),
        )
        candidate_score = (
            float(row.get("risk_score") or 0),
            float(row.get("alignment_score") or 0),
            int(row.get("gap_count") or 0),
        )
        if candidate_score > current_score:
            grouped[key] = row
    return sorted(
        grouped.values(),
        key=lambda item: (
            float(item.get("risk_score") or 0),
            float(item.get("alignment_score") or 0),
            int(item.get("program_id") or item.get("especializacion_id") or item.get("id") or 0),
        ),
        reverse=True,
    )


def list_programas_compatibility(*, limit: int = 25, offset: int = 0) -> dict[str, Any]:
    limit = _program_limit(limit)
    offset = _offset(offset)
    rows = dashboard_service.list_programs_base(db_name=None)
    total = len(rows)
    items = rows[offset : offset + limit]
    return {
        "items": items,
        "count": total,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_programa_compatibility(program_id: int) -> dict[str, Any]:
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=None)
    row = programas_repository.fetch_program_base_row(resolved_id, db_name=None)
    if not row:
        raise KeyError(f"programa {program_id} not found")
    normalized = normalize_program_row(row)
    for item in dashboard_service.list_programs_base(db_name=None):
        if int(item.get("especializacion_id") or 0) == resolved_id:
            normalized.update(item)
            break
    normalized["skills"] = dashboard_service.normalize_skill_rows(
        programas_repository.fetch_program_skill_rows(resolved_id, db_name=None)
    )
    micro_context = microcurriculum_context_repository.fetch_program_context(
        resolved_id,
        specialization_name=normalized.get("nombre_especializacion"),
        db_name=None,
    )
    if micro_context:
        contextual_skills = [
            {"nombre": item.get("name"), "conteo": item.get("frequency", 1)}
            for item in (micro_context.get("technologies") or micro_context.get("technical_skills") or [])
        ]
        scores = micro_context.get("scores") or {}
        normalized.update(
            {
                "curricular_context_source": "microcurriculum_program_contexts",
                "microcurriculum_context": micro_context,
                "skills": contextual_skills,
                "skills_reales_microcurriculo": contextual_skills,
                "competencias_reales_microcurriculo": micro_context.get("transversal_skills") or [],
                "herramientas_reales_microcurriculo": (micro_context.get("tools") or []) + (micro_context.get("platforms") or []),
                "brechas_reales_microcurriculo": micro_context.get("real_market_gaps") or [],
                "areas_a_fortalecer": micro_context.get("strengthening_areas") or [],
                "roles_laborales_contextuales": micro_context.get("labor_roles") or [],
                "benchmarking_contextual": micro_context.get("benchmarking") or [],
                "narrativa_ia": micro_context.get("executive_narrative") or "",
                "total_skills_programa": len(contextual_skills),
                "promedio_match_mercado": float(scores.get("market_skill_coverage") or normalized.get("promedio_match_mercado") or 0),
                "porcentaje_match": float(scores.get("market_skill_coverage") or normalized.get("porcentaje_match") or 0),
                "max_match_mercado": float(scores.get("curricular_relevance") or normalized.get("max_match_mercado") or 0),
                "total_empleos_relacionados": len(micro_context.get("labor_roles") or []),
            }
        )
    return normalized


def get_program_dashboard_compatibility(program_id: int) -> dict[str, Any]:
    current_programs = dashboard_service.list_programs_base(db_name=None)
    selected = get_programa_compatibility(program_id)
    relation = matches_repository.match_relation_name(db_name=None)
    resolved_id = int(selected.get("especializacion_id") or programas_repository.resolve_program_id(program_id, db_name=None))
    matches = (
        matches_repository.fetch_match_rows_for_program(relation, resolved_id, limit=25, db_name=None)
        if relation
        else []
    )
    missing_skills = (
        skills_repository.fetch_missing_market_skill_rows_for_program(relation, resolved_id, 22, db_name=None)
        if relation
        else []
    )
    recommendations = recommendation_service.recommended_program_cards(
        current_programs,
        selected,
        "",
        [],
        [],
        [],
        "",
        area_keywords_by_key=AREA_KEYWORDS_BY_KEY,
        get_program_skill_rows=lambda current_id: programas_repository.fetch_program_skill_rows(current_id, db_name=None),
        skill_identity_key=basic_text_key,
        program_role_candidates=lambda program, limit=4: [
            value
            for value in [
                str(program.get("rol", "") or "").strip(),
                str(program.get("nombre_especializacion", "") or "").strip(),
            ]
            if value
        ][:limit],
        limit=5,
    )
    payload = dashboard_service.program_context_dashboard(
        selected,
        matches=matches,
        missing_skills=missing_skills,
        recommendations=recommendations,
    )
    micro_context = selected.get("microcurriculum_context")
    if micro_context:
        real_gaps = micro_context.get("real_market_gaps") or []
        strengthening = micro_context.get("strengthening_areas") or []
        scores = micro_context.get("scores") or {}
        labor_roles = micro_context.get("labor_roles") or []
        payload["microcurriculum_context"] = micro_context
        payload["missing_skills"] = [
            {"skill_id": index + 1, "nombre": item.get("name"), "conteo": 1, "priority": item.get("priority")}
            for index, item in enumerate(real_gaps)
        ]
        payload["matches"] = [
            {
                "empleo_id": f"context-role-{index + 1}",
                "titulo_empleo": role,
                "total_skills_empleo": len(micro_context.get("technologies") or []),
                "total_skills_especializacion": len(micro_context.get("technologies") or []),
                "skills_en_comun": max(1, len(micro_context.get("technologies") or []) - len(real_gaps)),
                "porcentaje_match": scores.get("market_skill_coverage") or 0,
                "source": "microcurriculum_context",
            }
            for index, role in enumerate(labor_roles)
        ]
        payload["kpis"].update(
            {
                "alignment_score": scores.get("market_skill_coverage") or payload["kpis"].get("alignment_score", 0),
                "missing_critical_skills": len(real_gaps),
                "high_demand_roles": len(labor_roles),
                "employability_trend": scores.get("curricular_relevance") or payload["kpis"].get("employability_trend", 0),
                "digital_coverage": scores.get("market_skill_coverage") or payload["kpis"].get("digital_coverage", 0),
                "curricular_update_signal": "Alta" if len(real_gaps) >= 6 else "Media" if strengthening else "Baja",
            }
        )
        payload["status"].update(
            {
                "curricular_status": "Contextualizado",
                "curricular_status_detail": f"Análisis basado en {micro_context.get('documents_processed')} microcurrículos reales del programa.",
                "ai_signal": micro_context.get("executive_narrative") or payload["status"].get("ai_signal", ""),
                "trend_label": "Tendencia contextual de Visual Analytics y Big Data",
            }
        )
        payload["insights"].update(
            {
                "detected": micro_context.get("executive_narrative") or payload["insights"].get("detected", ""),
                "ai_recommends": [
                    f"Fortalecer {item.get('name')} con mayor profundidad aplicada."
                    for item in real_gaps[:5]
                ],
                "emerging_gap": real_gaps[0].get("name") if real_gaps else "Sin brechas críticas detectadas",
                "critical_signal": "Microcurrículo real indexado",
            }
        )
    payload["source"] = relation or "empleo_skills"
    return payload
