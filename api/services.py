from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from api.database import fetch_all, fetch_one, relation_exists, relation_has_rows, startup_validate, table_row_count
from intelligence.semantic_search_engine import semantic_search
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map


DEFAULT_LIMIT = 20
MAX_LIMIT = 100


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
    candidates = [column for column in ("generated_at", "updated_at", "created_at") if _column_exists(table, column)]
    for column in candidates:
        row = fetch_one(f"SELECT MAX({column}) AS latest FROM {table}")
        value = row.get("latest") if row else None
        if value:
            return value.isoformat() if hasattr(value, "isoformat") else str(value)
    return None


def get_health_snapshot() -> dict[str, Any]:
    required_relations = (
        "jobs",
        "observatory_metrics",
        "curriculum_gap_observatory",
        "recommendation_observatory",
        "semantic_role_graph",
        "company_observatory",
        "emerging_technology_observatory",
    )
    checks = {
        "database": False,
        "jobs_table": relation_exists("jobs"),
        "observatory_metrics": relation_exists("observatory_metrics") and relation_has_rows("observatory_metrics"),
        "curriculum_gap_observatory": relation_exists("curriculum_gap_observatory"),
        "recommendation_observatory": relation_exists("recommendation_observatory"),
        "semantic_role_graph": relation_exists("semantic_role_graph"),
        "company_observatory": relation_exists("company_observatory"),
        "emerging_technology_observatory": relation_exists("emerging_technology_observatory"),
    }
    validation = startup_validate(required_relations=required_relations)
    checks["database"] = bool(validation.get("database"))
    observatory_freshness = {
        table: {
            "rows": table_row_count(table),
            "latest": _latest_timestamp(table),
        }
        for table in required_relations
        if relation_exists(table)
    }
    status = "ok" if checks["database"] and checks["jobs_table"] else "degraded"
    if not checks["observatory_metrics"]:
        status = "degraded"
    return {
        "status": status,
        "database": "connected" if checks["database"] else "unavailable",
        "timestamp": datetime.now(UTC),
        "checks": checks,
        "observatory_freshness": observatory_freshness,
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
