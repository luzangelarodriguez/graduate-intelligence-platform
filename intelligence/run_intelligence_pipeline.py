from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from psycopg2.extras import Json, execute_values

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_conn  # noqa: E402
from backend.database_config import get_connection_parameters, test_connection  # noqa: E402
from intelligence.career_path_engine import build_career_paths  # noqa: E402
from intelligence.company_intelligence_engine import build_company_profiles  # noqa: E402
from intelligence.company_resolution_engine import resolve_company  # noqa: E402
from intelligence.executive_observatory_engine import build_executive_observatory_v2, persist_executive_observatory_metrics  # noqa: E402
from intelligence.observatory_pipeline import run_observatory_layer  # noqa: E402
from intelligence.program_intelligence_engine import build_program_intelligence, persist_program_intelligence  # noqa: E402
from intelligence.predictive_intelligence_engine import build_executive_metrics, build_market_demand_forecasts, persist_executive_metrics  # noqa: E402
from intelligence.recommendation_intelligence_engine import build_recommendations  # noqa: E402
from intelligence.semantic_role_intelligence import build_role_intelligence, occupational_edges  # noqa: E402
from intelligence.semantic_search_engine import semantic_search  # noqa: E402

MIGRATIONS = [
    ROOT_DIR / "database" / "migrations" / "015_labor_acquisition_warehouse.sql",
    ROOT_DIR / "database" / "migrations" / "016_labor_intelligence_enrichment.sql",
    ROOT_DIR / "database" / "migrations" / "017_labor_intelligence_qa_feedback.sql",
    ROOT_DIR / "database" / "migrations" / "018_labor_curriculum_intelligence.sql",
    ROOT_DIR / "database" / "migrations" / "019_labor_observatory_layer.sql",
    ROOT_DIR / "database" / "migrations" / "020_predictive_intelligence_layer.sql",
    ROOT_DIR / "database" / "migrations" / "021_program_intelligence.sql",
    ROOT_DIR / "database" / "migrations" / "022_program_intelligence_dedup.sql",
    ROOT_DIR / "database" / "migrations" / "023_program_intelligence_table.sql",
]
ANALYTICS_DIR = ROOT_DIR / "outputs" / "analytics"


def _log_stage(step: str, total: int = 8) -> None:
    print(f"[{step}/{total}]")


def _log_stage_message(step: str, message: str, total: int = 8) -> None:
    print(f"[{step}/{total}] {message}")


def _stage_count(label: str, items: list[Any]) -> None:
    print(f"{label}: {len(items)}")


def _run_stage(step: int, title: str, func):
    try:
        _log_stage_message(step, title)
        return func()
    except Exception:
        print(f"[{step}/8] Stage failed: {title}")
        raise


def apply_migrations(cur: Any) -> None:
    for migration in MIGRATIONS:
        if migration.exists():
            cur.execute(migration.read_text(encoding="utf-8"))


def fetch_jobs(limit: int = 500) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            apply_migrations(cur)
            cur.execute(
                """
                SELECT
                    j.id, j.title, j.company, j.normalized_company, j.description, j.location,
                    j.modality, j.seniority, j.curation_level, j.job_probability_score,
                    j.completeness_score, j.created_at,
                    COALESCE(
                        array_agg(js.canonical_skill ORDER BY js.confidence DESC)
                            FILTER (WHERE js.canonical_skill IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) AS skills
                FROM jobs j
                LEFT JOIN job_skills js ON js.job_id = j.id
                GROUP BY j.id
                ORDER BY j.updated_at DESC NULLS LAST, j.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = [dict(row) for row in cur.fetchall()]
            conn.commit()
    for row in rows:
        row["skills"] = list(row.get("skills") or [])
    return rows


def persist_intelligence(payload: dict[str, Any]) -> dict[str, int]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            apply_migrations(cur)
            for job in payload["jobs"]:
                resolution = job["company_resolution"]
                cur.execute(
                    """
                    UPDATE jobs
                    SET canonical_company_name = %s,
                        company_resolution_confidence = %s,
                        inferred_company = %s,
                        resolution_method = %s,
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (
                        resolution["canonical_company_name"],
                        resolution["company_resolution_confidence"],
                        resolution["inferred_company"],
                        resolution["resolution_method"],
                        job["id"],
                    ),
                )
                for alias in resolution.get("company_aliases") or []:
                    cur.execute(
                        """
                        INSERT INTO company_aliases (canonical_company_name, alias, alias_normalized, confidence)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (alias_normalized) DO UPDATE SET
                            canonical_company_name = EXCLUDED.canonical_company_name,
                            confidence = GREATEST(company_aliases.confidence, EXCLUDED.confidence)
                        """,
                        (
                            resolution["canonical_company_name"],
                            alias,
                            alias.casefold().strip(),
                            resolution["company_resolution_confidence"],
                        ),
                    )
            profile_rows = [
                (
                    item.company,
                    Json(item.dominant_skills),
                    Json(item.dominant_clusters),
                    item.hiring_velocity,
                    item.technology_maturity,
                    item.ai_adoption_score,
                    item.bi_maturity_score,
                    item.cloud_maturity_score,
                )
                for item in payload["company_profiles"]
            ]
            if profile_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO company_profiles
                        (canonical_company_name, dominant_skills, dominant_clusters, hiring_velocity,
                         technology_maturity, ai_adoption_score, bi_maturity_score, cloud_maturity_score)
                    VALUES %s
                    ON CONFLICT (canonical_company_name) DO UPDATE SET
                        dominant_skills = EXCLUDED.dominant_skills,
                        dominant_clusters = EXCLUDED.dominant_clusters,
                        hiring_velocity = EXCLUDED.hiring_velocity,
                        technology_maturity = EXCLUDED.technology_maturity,
                        ai_adoption_score = EXCLUDED.ai_adoption_score,
                        bi_maturity_score = EXCLUDED.bi_maturity_score,
                        cloud_maturity_score = EXCLUDED.cloud_maturity_score,
                        updated_at = now()
                    """,
                    profile_rows,
                )
            recommendation_rows = [
                (
                    item.recommendation_type,
                    item.target_entity,
                    item.target_company,
                    item.recommendation_score,
                    item.recommendation_reasoning,
                    Json(item.recommendation_evidence),
                )
                for item in payload["recommendations"]
            ]
            if recommendation_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO recommendation_intelligence
                        (recommendation_type, target_entity, target_company, recommendation_score,
                         recommendation_reasoning, recommendation_evidence)
                    VALUES %s
                    """,
                    recommendation_rows,
                )
            role_rows = [
                (item.role_title, item.role_family, item.semantic_role_cluster, item.role_similarity_score, item.centrality_score)
                for item in payload["role_signals"]
            ]
            if role_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO semantic_role_clusters
                        (role_title, role_family, semantic_role_cluster, role_similarity_score, centrality_score)
                    VALUES %s
                    ON CONFLICT (role_title, semantic_role_cluster) DO UPDATE SET
                        role_family = EXCLUDED.role_family,
                        role_similarity_score = EXCLUDED.role_similarity_score,
                        centrality_score = EXCLUDED.centrality_score
                    """,
                    role_rows,
                )
            edge_rows = [
                (edge["source_role"], edge["target_role"], edge["edge_type"], edge["weight"], Json(edge["evidence"]))
                for edge in payload["role_edges"]
            ]
            if edge_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO occupational_graph_edges (source_role, target_role, edge_type, weight, evidence)
                    VALUES %s
                    ON CONFLICT (source_role, target_role, edge_type) DO UPDATE SET
                        weight = EXCLUDED.weight,
                        evidence = EXCLUDED.evidence
                    """,
                    edge_rows,
                )
            transition_rows = [
                (
                    item.source_role,
                    item.target_role,
                    item.role_progression_probability,
                    Json(item.transition_skill_gaps),
                    Json(item.recommended_next_skills),
                )
                for item in payload["career_transitions"]
            ]
            if transition_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO career_transitions
                        (source_role, target_role, role_progression_probability, transition_skill_gaps, recommended_next_skills)
                    VALUES %s
                    ON CONFLICT (source_role, target_role) DO UPDATE SET
                        role_progression_probability = EXCLUDED.role_progression_probability,
                        transition_skill_gaps = EXCLUDED.transition_skill_gaps,
                        recommended_next_skills = EXCLUDED.recommended_next_skills
                    """,
                    transition_rows,
                )
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'market_forecasts'
                      AND column_name = 'horizon_months'
                ) AS exists
                """
            )
            horizon_exists = bool((cur.fetchone() or {}).get("exists"))
            forecast_source = payload["forecasts"] if horizon_exists else [item for item in payload["forecasts"] if int(getattr(item, "horizon_months", 12) or 12) == 12] or payload["forecasts"][:1]
            if forecast_source:
                execute_values(
                    cur,
                    (
                        """
                        INSERT INTO market_forecasts
                            (entity_type, entity_name, horizon_months, growth_velocity, forecast_confidence, market_phase, first_seen_at, last_seen_at, evidence)
                        VALUES %s
                        ON CONFLICT (entity_type, entity_name, horizon_months) DO UPDATE SET
                            growth_velocity = EXCLUDED.growth_velocity,
                            forecast_confidence = EXCLUDED.forecast_confidence,
                            market_phase = EXCLUDED.market_phase,
                            first_seen_at = LEAST(COALESCE(market_forecasts.first_seen_at, EXCLUDED.first_seen_at), COALESCE(EXCLUDED.first_seen_at, market_forecasts.first_seen_at)),
                            last_seen_at = GREATEST(COALESCE(market_forecasts.last_seen_at, EXCLUDED.last_seen_at), COALESCE(EXCLUDED.last_seen_at, market_forecasts.last_seen_at)),
                            evidence = EXCLUDED.evidence,
                            updated_at = now()
                        """
                        if horizon_exists
                        else """
                        INSERT INTO market_forecasts
                            (entity_type, entity_name, growth_velocity, forecast_confidence, market_phase, first_seen_at, last_seen_at, evidence)
                        VALUES %s
                        ON CONFLICT (entity_type, entity_name) DO UPDATE SET
                            growth_velocity = EXCLUDED.growth_velocity,
                            forecast_confidence = EXCLUDED.forecast_confidence,
                            market_phase = EXCLUDED.market_phase,
                            first_seen_at = LEAST(COALESCE(market_forecasts.first_seen_at, EXCLUDED.first_seen_at), COALESCE(EXCLUDED.first_seen_at, market_forecasts.first_seen_at)),
                            last_seen_at = GREATEST(COALESCE(market_forecasts.last_seen_at, EXCLUDED.last_seen_at), COALESCE(EXCLUDED.last_seen_at, market_forecasts.last_seen_at)),
                            evidence = EXCLUDED.evidence,
                            updated_at = now()
                        """
                    ),
                    [
                        (
                            item.entity_type,
                            item.entity_name,
                            item.horizon_months,
                            item.growth_velocity,
                            item.forecast_confidence,
                            item.market_phase,
                            item.first_seen_at,
                            item.last_seen_at,
                            Json(item.evidence),
                        )
                        if horizon_exists
                        else (
                            item.entity_type,
                            item.entity_name,
                            item.growth_velocity,
                            item.forecast_confidence,
                            item.market_phase,
                            item.first_seen_at,
                            item.last_seen_at,
                            Json(item.evidence),
                        )
                        for item in forecast_source
                    ],
                )
        conn.commit()
    return {
        "company_profiles": len(payload["company_profiles"]),
        "recommendations": len(payload["recommendations"]),
        "role_signals": len(payload["role_signals"]),
        "career_transitions": len(payload["career_transitions"]),
        "forecasts": len(payload["forecasts"]),
        "executive_metrics": len(payload.get("executive_metrics", [])),
    }


def write_reports(payload: dict[str, Any], persisted: dict[str, int]) -> dict[str, str]:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    reports = {
        "company_resolution_report.md": [
            "# Company Resolution Report",
            "",
            f"- Jobs analizados: {len(payload['jobs'])}",
            *[
                f"- {job['company']} -> {job['company_resolution']['canonical_company_name']} "
                f"({job['company_resolution']['resolution_method']}, {job['company_resolution']['company_resolution_confidence']})"
                for job in payload["jobs"][:30]
            ],
        ],
        "company_intelligence_report.md": [
            "# Company Intelligence Report",
            "",
            f"- Perfiles persistidos: {persisted.get('company_profiles', 0)}",
            *[
                f"- {profile.company}: {profile.technology_maturity}; skills={', '.join(profile.dominant_skills[:6])}"
                for profile in payload["company_profiles"][:20]
            ],
        ],
        "recommendation_engine_report.md": [
            "# Recommendation Intelligence Report",
            "",
            f"- Recomendaciones generadas: {persisted.get('recommendations', 0)}",
            *[
                f"- {item.recommendation_type} | {item.target_company}: {item.recommendation_reasoning}"
                for item in payload["recommendations"][:20]
            ],
        ],
        "semantic_role_graph_report.md": [
            "# Semantic Role Graph Report",
            "",
            f"- Roles detectados: {len(payload['role_signals'])}",
            f"- Edges ocupacionales: {len(payload['role_edges'])}",
            *[
                f"- {item.role_title}: {item.role_family} ({item.role_similarity_score})"
                for item in payload["role_signals"][:25]
            ],
        ],
        "career_path_report.md": [
            "# Career Path Report",
            "",
            *[
                f"- {item.source_role} -> {item.target_role}: {item.role_progression_probability}; gaps={', '.join(item.transition_skill_gaps)}"
                for item in payload["career_transitions"]
            ],
        ],
        "emerging_market_forecast.md": [
            "# Emerging Market Forecast",
            "",
            *[
                f"- {item.entity_type}:{item.entity_name} ({item.horizon_months}m): {item.market_phase}; velocity={item.growth_velocity}; confidence={item.forecast_confidence}"
                for item in payload["forecasts"][:30]
            ],
        ],
        "semantic_search_report.md": [
            "# Semantic Search Report",
            "",
            *[
                f"- {item.title}: {item.similarity_score}"
                for item in payload["semantic_search_results"]
            ],
        ],
    }
    paths: dict[str, str] = {}
    for filename, lines in reports.items():
        path = ANALYTICS_DIR / filename
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths[filename] = str(path)
    return paths


def run_intelligence(limit: int = 500, persist: bool = True) -> dict[str, Any]:
    _log_stage_message(1, "Connection validated")

    jobs = _run_stage(2, "Fetching jobs", lambda: fetch_jobs(limit=limit))
    _stage_count("Fetched jobs", jobs)

    def _resolve_jobs() -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for job in jobs:
            resolution = resolve_company(
                job.get("company"),
                context_text=" ".join([str(job.get("title") or ""), str(job.get("description") or "")]),
            )
            resolved.append({**job, "company_resolution": resolution.to_dict()})
        return resolved

    resolved_jobs = _run_stage(3, "Fetching skills", _resolve_jobs)
    market_skills = sorted({skill for job in resolved_jobs for skill in (job.get("skills") or [])})
    _stage_count("Fetched skills", market_skills)

    def _compute_curriculum_gaps() -> tuple[list[str], list[str], list[dict[str, Any]]]:
        emerging = [skill for skill in market_skills if skill in {"Databricks", "Microsoft Fabric", "Synapse", "Copilot BI", "LLM", "RAG"}]
        missing = [skill for skill in market_skills if skill in {"data governance", "MLOps", "DataOps", "Azure", "AWS"}]
        role_signals_local = build_role_intelligence(resolved_jobs)
        return missing, emerging, role_signals_local

    missing_skills, emerging_skills, role_signals = _run_stage(4, "Computing curriculum gaps", _compute_curriculum_gaps)
    _stage_count("Curriculum gaps", missing_skills)

    def _compute_recommendations() -> tuple[list[Any], list[Any], list[Any], list[Any], list[Any]]:
        company_profiles_local = build_company_profiles(resolved_jobs)
        recommendations_local = build_recommendations(
            company_profiles=company_profiles_local,
            missing_skills=missing_skills,
            emerging_skills=emerging_skills,
        )
        role_edges_local = occupational_edges(role_signals)
        career_transitions_local = build_career_paths(role_signals, market_skills)
        semantic_search_results_local = semantic_search("roles similares a Analytics Engineer", resolved_jobs, limit=10)
        return company_profiles_local, recommendations_local, role_edges_local, career_transitions_local, semantic_search_results_local

    company_profiles, recommendations, role_edges, career_transitions, semantic_search_results = _run_stage(5, "Computing recommendations", _compute_recommendations)
    _stage_count("Recommendations", recommendations)

    forecasts = _run_stage(6, "Computing forecasts", lambda: build_market_demand_forecasts(persist=False))
    _stage_count("Forecasts", forecasts)

    payload = {
        "jobs": resolved_jobs,
        "company_profiles": company_profiles,
        "recommendations": recommendations,
        "role_signals": role_signals,
        "role_edges": role_edges,
        "career_transitions": career_transitions,
        "forecasts": forecasts,
        "semantic_search_results": semantic_search_results,
        "executive_metrics": build_executive_metrics(),
    }

    def _persist_results() -> tuple[dict[str, Any], dict[str, int], dict[str, str]]:
        persist_executive_metrics(payload["executive_metrics"])
        observatory_local = run_observatory_layer(
            jobs=resolved_jobs,
            company_profiles=company_profiles,
            role_signals=role_signals,
            forecasts=payload["forecasts"],
            career_transitions=payload["career_transitions"],
            persist=persist,
            write_output=True,
        )
        persisted_local = persist_intelligence(payload) if persist else {}
        program_intelligence_records = build_program_intelligence()
        program_intelligence_count = persist_program_intelligence(program_intelligence_records, replace_existing=True) if persist else 0
        persisted_local["program_intelligence"] = program_intelligence_count
        executive_observatory = build_executive_observatory_v2(persist=False)
        persisted_local["executive_observatory_metrics"] = persist_executive_observatory_metrics(executive_observatory.metrics) if persist else 0
        reports_local = write_reports(payload, persisted_local)
        persisted_local["executive_observatory"] = executive_observatory.to_dict()
        return observatory_local, persisted_local, reports_local

    observatory, persisted, reports = _run_stage(7, "Persisting results", _persist_results)
    _log_stage_message(8, "Pipeline completed")
    return {
        "jobs_analyzed": len(jobs),
        "persisted": persisted,
        "reports": reports,
        "observatory": observatory,
        "top_companies": [profile.to_dict() for profile in company_profiles[:5]],
        "top_forecasts": [forecast.to_dict() for forecast in payload["forecasts"][:5]],
    }


def _print_database_banner() -> None:
    diagnostics = get_connection_parameters()
    print("=================================")
    print("INTELLIGENCE PIPELINE")
    print("=====================")
    print(f"Database mode: {diagnostics['mode']}")
    print(f"Database: {diagnostics['database']}")
    print(f"Host: {diagnostics['host']}")
    print("============================")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run semantic labor and curriculum intelligence layer.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()
    _print_database_banner()
    diagnostics = test_connection()
    print(f"Connection source: {diagnostics['connection_source']}")
    print(json.dumps(run_intelligence(limit=args.limit, persist=not args.no_persist), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
