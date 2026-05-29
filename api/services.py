from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from backend.repositories import microcurriculum_context_repository, programas_repository
from backend.services import dashboard_service
from backend.services.normalization_service import normalize_program_row

from api.database import fetch_all, fetch_one, relation_exists, relation_has_rows, startup_validate, table_row_count
from intelligence.semantic_search_engine import semantic_search
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map


DEFAULT_LIMIT = 20
MAX_LIMIT = 100

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
                   recommendation_confidence, recommendation_evidence, metric_period, generated_at
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


def list_market_forecast(*, limit: int = DEFAULT_LIMIT, offset: int = 0, entity_type: str | None = None) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    if relation_exists("market_forecasts") and relation_has_rows("market_forecasts"):
        clauses: list[str] = []
        params: list[Any] = []
        if entity_type:
            clauses.append("entity_type = %s")
            params.append(entity_type)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = fetch_all(
            f"""
            SELECT entity_type, entity_name, growth_velocity, forecast_confidence, market_phase, evidence, generated_at
            FROM market_forecasts
            {where_sql}
            ORDER BY growth_velocity DESC NULLS LAST, forecast_confidence DESC NULLS LAST
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )
        count_row = fetch_one(f"SELECT COUNT(*)::int AS total FROM market_forecasts {where_sql}", tuple(params))
        return _envelope(_serialize_rows(rows), limit=limit, offset=offset, total=int((count_row or {}).get("total") or 0), filters={"entity_type": entity_type})
    return _envelope([], limit=limit, offset=offset, total=0, filters={"entity_type": entity_type})


def list_emerging_skills(*, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    limit = _bounded(limit)
    offset = _offset(offset)
    intelligence = build_market_skill_intelligence_map(include_database=True, write_output=False)
    rows = [signal.to_dict() for signal in intelligence.emerging_skills]
    return _envelope(rows, limit=limit, offset=offset, total=len(rows), filters={"coverage_status": "emerging"})


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
