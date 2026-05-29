from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from psycopg2.extras import Json, execute_values

from backend.db import get_conn
from crawlers.storage.postgres_warehouse import load_environment
from intelligence.company_observatory_engine import CompanyObservatoryItem, build_company_observatory
from intelligence.curriculum_gap_observatory import CurriculumGapObservation, build_curriculum_gap_observatory
from intelligence.emerging_technology_engine import EmergingTechnologyItem, build_emerging_technology_observatory
from intelligence.market_forecasting_engine import MarketForecast
from intelligence.observatory_metrics_engine import ObservatoryMetric, build_observatory_metrics
from intelligence.recommendation_api_engine import RecommendationAPIItem, build_recommendation_api_payload
from intelligence.semantic_role_graph_engine import SemanticRoleGraphEdge, build_semantic_role_graph
from ml.curriculum.curriculum_market_gap_engine import build_curriculum_market_gap_map
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map

ROOT_DIR = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = ROOT_DIR / "outputs" / "analytics"
DASHBOARD_DIR = ROOT_DIR / "outputs" / "dashboard_datasets"
MIGRATIONS = [
    ROOT_DIR / "database" / "migrations" / "015_labor_acquisition_warehouse.sql",
    ROOT_DIR / "database" / "migrations" / "016_labor_intelligence_enrichment.sql",
    ROOT_DIR / "database" / "migrations" / "017_labor_intelligence_qa_feedback.sql",
    ROOT_DIR / "database" / "migrations" / "018_labor_curriculum_intelligence.sql",
    ROOT_DIR / "database" / "migrations" / "019_labor_observatory_layer.sql",
]


def _apply_migrations(cur: Any) -> None:
    for migration in MIGRATIONS:
        if migration.exists():
            cur.execute(migration.read_text(encoding="utf-8"))


def _period_key() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _load_previous_metric_values(cur: Any, metric_period: str) -> dict[str, float]:
    cur.execute(
        """
        SELECT DISTINCT ON (metric_name)
            metric_name,
            metric_value
        FROM observatory_metrics
        WHERE metric_period < %s
        ORDER BY metric_name, metric_period DESC, generated_at DESC
        """,
        (metric_period,),
    )
    return {str(row["metric_name"]): float(row["metric_value"]) for row in cur.fetchall()}


def _to_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serialized: dict[str, Any] = {}
            for field in fieldnames:
                value = row.get(field, "")
                if isinstance(value, (dict, list)):
                    serialized[field] = json.dumps(value, ensure_ascii=False)
                else:
                    serialized[field] = value
            writer.writerow(serialized)
    return str(path)


def _persist_metrics(cur: Any, rows: list[ObservatoryMetric]) -> int:
    if not rows:
        return 0
    now = datetime.now(UTC)
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
        [
            (
                row.metric_name,
                row.metric_category,
                row.metric_value,
                row.metric_period,
                row.confidence_score,
                Json(row.source_payload),
                now,
                now,
            )
            for row in rows
        ],
    )
    return len(rows)


def _persist_gap_observations(cur: Any, rows: list[CurriculumGapObservation]) -> int:
    if not rows:
        return 0
    now = datetime.now(UTC)
    execute_values(
        cur,
        """
        INSERT INTO curriculum_gap_observatory
            (specialization, missing_skill, market_demand_score, curriculum_coverage_score, urgency_score, emergence_score, recommendation, evidence, generated_at, updated_at)
        VALUES %s
        ON CONFLICT (specialization, missing_skill) DO UPDATE SET
            market_demand_score = EXCLUDED.market_demand_score,
            curriculum_coverage_score = EXCLUDED.curriculum_coverage_score,
            urgency_score = EXCLUDED.urgency_score,
            emergence_score = EXCLUDED.emergence_score,
            recommendation = EXCLUDED.recommendation,
            evidence = EXCLUDED.evidence,
            updated_at = now()
        """,
        [
            (
                row.specialization,
                row.missing_skill,
                row.market_demand_score,
                row.curriculum_coverage_score,
                row.urgency_score,
                row.emergence_score,
                row.recommendation,
                Json(row.evidence),
                now,
                now,
            )
            for row in rows
        ],
    )
    return len(rows)


def _persist_recommendations(cur: Any, rows: list[RecommendationAPIItem], metric_period: str) -> int:
    if not rows:
        return 0
    deduped: dict[tuple[str, str, str, str], RecommendationAPIItem] = {}
    for row in rows:
        key = (row.recommendation_type, row.target_role, row.target_company, metric_period)
        current = deduped.get(key)
        if current is None or row.recommendation_confidence >= current.recommendation_confidence:
            deduped[key] = row
    rows = list(deduped.values())
    now = datetime.now(UTC)
    execute_values(
        cur,
        """
        INSERT INTO recommendation_observatory
            (recommendation_type, target_role, target_company, recommendation_payload, recommendation_reasoning, recommendation_confidence, recommendation_evidence, metric_period, generated_at, updated_at)
        VALUES %s
        ON CONFLICT (recommendation_type, target_role, target_company, metric_period) DO UPDATE SET
            recommendation_payload = EXCLUDED.recommendation_payload,
            recommendation_reasoning = EXCLUDED.recommendation_reasoning,
            recommendation_confidence = EXCLUDED.recommendation_confidence,
            recommendation_evidence = EXCLUDED.recommendation_evidence,
            updated_at = now()
        """,
        [
            (
                row.recommendation_type,
                row.target_role,
                row.target_company,
                Json(row.recommendation_payload),
                row.recommendation_reasoning,
                row.recommendation_confidence,
                Json(row.recommendation_evidence),
                metric_period,
                now,
                now,
            )
            for row in rows
        ],
    )
    return len(rows)


def _persist_role_graph(cur: Any, rows: list[SemanticRoleGraphEdge], metric_period: str) -> int:
    if not rows:
        return 0
    now = datetime.now(UTC)
    execute_values(
        cur,
        """
        INSERT INTO semantic_role_graph
            (source_role, target_role, similarity_score, transition_probability, shared_skills, cluster_affinity, centrality_score, evidence, metric_period, generated_at, updated_at)
        VALUES %s
        ON CONFLICT (source_role, target_role, metric_period) DO UPDATE SET
            similarity_score = EXCLUDED.similarity_score,
            transition_probability = EXCLUDED.transition_probability,
            shared_skills = EXCLUDED.shared_skills,
            cluster_affinity = EXCLUDED.cluster_affinity,
            centrality_score = EXCLUDED.centrality_score,
            evidence = EXCLUDED.evidence,
            updated_at = now()
        """,
        [
            (
                row.source_role,
                row.target_role,
                row.similarity_score,
                row.transition_probability,
                Json(row.shared_skills),
                row.cluster_affinity,
                row.centrality_score,
                Json(row.evidence),
                metric_period,
                now,
                now,
            )
            for row in rows
        ],
    )
    return len(rows)


def _persist_company_observatory(cur: Any, rows: list[CompanyObservatoryItem], metric_period: str) -> int:
    if not rows:
        return 0
    now = datetime.now(UTC)
    execute_values(
        cur,
        """
        INSERT INTO company_observatory
            (company, dominant_stack, dominant_cluster, hiring_velocity, ai_adoption_score, cloud_maturity_score, bi_maturity_score, technology_maturity, top_skills, top_clusters, evidence, metric_period, generated_at, updated_at)
        VALUES %s
        ON CONFLICT (company, metric_period) DO UPDATE SET
            dominant_stack = EXCLUDED.dominant_stack,
            dominant_cluster = EXCLUDED.dominant_cluster,
            hiring_velocity = EXCLUDED.hiring_velocity,
            ai_adoption_score = EXCLUDED.ai_adoption_score,
            cloud_maturity_score = EXCLUDED.cloud_maturity_score,
            bi_maturity_score = EXCLUDED.bi_maturity_score,
            technology_maturity = EXCLUDED.technology_maturity,
            top_skills = EXCLUDED.top_skills,
            top_clusters = EXCLUDED.top_clusters,
            evidence = EXCLUDED.evidence,
            updated_at = now()
        """,
        [
            (
                row.company,
                row.dominant_stack,
                row.dominant_cluster,
                row.hiring_velocity,
                row.ai_adoption_score,
                row.cloud_maturity_score,
                row.bi_maturity_score,
                row.technology_maturity,
                Json(row.top_skills),
                Json(row.top_clusters),
                Json(row.evidence),
                metric_period,
                now,
                now,
            )
            for row in rows
        ],
    )
    return len(rows)


def _persist_emerging_technology(cur: Any, rows: list[EmergingTechnologyItem], metric_period: str) -> int:
    if not rows:
        return 0
    now = datetime.now(UTC)
    execute_values(
        cur,
        """
        INSERT INTO emerging_technology_observatory
            (technology, emergence_score, growth_velocity, adoption_trend, forecast_confidence, source_payload, metric_period, generated_at, updated_at)
        VALUES %s
        ON CONFLICT (technology, metric_period) DO UPDATE SET
            emergence_score = EXCLUDED.emergence_score,
            growth_velocity = EXCLUDED.growth_velocity,
            adoption_trend = EXCLUDED.adoption_trend,
            forecast_confidence = EXCLUDED.forecast_confidence,
            source_payload = EXCLUDED.source_payload,
            updated_at = now()
        """,
        [
            (
                row.technology,
                row.emergence_score,
                row.growth_velocity,
                row.adoption_trend,
                row.forecast_confidence,
                Json(row.source_payload),
                metric_period,
                now,
                now,
            )
            for row in rows
        ],
    )
    return len(rows)


def _export_dashboard_datasets(
    *,
    metrics: list[ObservatoryMetric],
    gap_observations: list[CurriculumGapObservation],
    role_graph: list[SemanticRoleGraphEdge],
    company_obs: list[CompanyObservatoryItem],
    emerging_tech: list[EmergingTechnologyItem],
    recommendations: list[RecommendationAPIItem],
) -> dict[str, str]:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    exports = {
        "observatory_metrics.csv": _write_csv(
            DASHBOARD_DIR / "observatory_metrics.csv",
            [row.to_dict() for row in metrics],
            ["metric_name", "metric_category", "metric_value", "metric_period", "confidence_score", "generated_at", "source_payload"],
        ),
        "curriculum_gap_dashboard.csv": _write_csv(
            DASHBOARD_DIR / "curriculum_gap_dashboard.csv",
            [row.to_dict() for row in gap_observations],
            ["specialization", "missing_skill", "market_demand_score", "curriculum_coverage_score", "urgency_score", "emergence_score", "recommendation", "evidence"],
        ),
        "semantic_role_graph.csv": _write_csv(
            DASHBOARD_DIR / "semantic_role_graph.csv",
            [row.to_dict() for row in role_graph],
            ["source_role", "target_role", "similarity_score", "transition_probability", "shared_skills", "cluster_affinity", "centrality_score", "evidence"],
        ),
        "company_intelligence_dashboard.csv": _write_csv(
            DASHBOARD_DIR / "company_intelligence_dashboard.csv",
            [row.to_dict() for row in company_obs],
            ["company", "dominant_stack", "dominant_cluster", "hiring_velocity", "ai_adoption_score", "cloud_maturity_score", "bi_maturity_score", "technology_maturity", "top_skills", "top_clusters", "evidence"],
        ),
        "emerging_technology_dashboard.csv": _write_csv(
            DASHBOARD_DIR / "emerging_technology_dashboard.csv",
            [row.to_dict() for row in emerging_tech],
            ["technology", "emergence_score", "growth_velocity", "adoption_trend", "forecast_confidence", "source_payload"],
        ),
        "recommendation_dashboard.csv": _write_csv(
            DASHBOARD_DIR / "recommendation_dashboard.csv",
            [row.to_dict() for row in recommendations],
            ["recommendation_type", "target_role", "target_company", "recommended_skills", "market_alignment_score", "top_companies", "recommendation_payload", "recommendation_reasoning", "recommendation_confidence", "recommendation_evidence"],
        ),
    }
    return exports


def run_observatory_layer(
    *,
    jobs: list[dict[str, Any]],
    company_profiles: list[Any],
    role_signals: list[Any],
    forecasts: list[MarketForecast],
    career_transitions: list[Any],
    persist: bool = True,
    metric_period: str | None = None,
    write_output: bool = True,
) -> dict[str, Any]:
    metric_period = metric_period or _period_key()
    previous_metric_values: dict[str, float] = {}
    if persist:
        load_environment()
        with get_conn() as conn:
            with conn.cursor() as cur:
                _apply_migrations(cur)
                previous_metric_values = _load_previous_metric_values(cur, metric_period)
    market_intelligence = build_market_skill_intelligence_map(include_database=True, write_output=write_output)
    gap_map = build_curriculum_market_gap_map(write_output=write_output)
    metrics = build_observatory_metrics(
        market_intelligence=market_intelligence,
        company_profiles=company_profiles,
        role_signals=role_signals,
        gap_map=gap_map,
        forecasts=forecasts,
        metric_period=metric_period,
        previous_values=previous_metric_values,
    )
    gap_observations = build_curriculum_gap_observatory(gap_map=gap_map, metric_period=metric_period, write_output=write_output)
    recommendations = build_recommendation_api_payload(
        market_intelligence=market_intelligence,
        gap_map=gap_map,
        company_profiles=company_profiles,
        role_signals=role_signals,
        career_transitions=career_transitions,
        metric_period=metric_period,
        write_output=write_output,
    )
    role_graph = build_semantic_role_graph(jobs=jobs, role_signals=role_signals, career_transitions=career_transitions, metric_period=metric_period, write_output=write_output)
    company_obs = build_company_observatory(company_profiles=company_profiles, metric_period=metric_period, write_output=write_output)
    emerging_tech = build_emerging_technology_observatory(forecasts=forecasts, market_intelligence=market_intelligence, metric_period=metric_period, write_output=write_output)
    dashboard_exports = _export_dashboard_datasets(
        metrics=metrics,
        gap_observations=gap_observations,
        role_graph=role_graph,
        company_obs=company_obs,
        emerging_tech=emerging_tech,
        recommendations=recommendations,
    )

    persisted = {
        "observatory_metrics": 0,
        "curriculum_gap_observatory": 0,
        "recommendation_observatory": 0,
        "semantic_role_graph": 0,
        "company_observatory": 0,
        "emerging_technology_observatory": 0,
    }
    if persist:
        load_environment()
        with get_conn() as conn:
            with conn.cursor() as cur:
                _apply_migrations(cur)
                persisted["observatory_metrics"] = _persist_metrics(cur, metrics)
                persisted["curriculum_gap_observatory"] = _persist_gap_observations(cur, gap_observations)
                persisted["recommendation_observatory"] = _persist_recommendations(cur, recommendations, metric_period)
                persisted["semantic_role_graph"] = _persist_role_graph(cur, role_graph, metric_period)
                persisted["company_observatory"] = _persist_company_observatory(cur, company_obs, metric_period)
                persisted["emerging_technology_observatory"] = _persist_emerging_technology(cur, emerging_tech, metric_period)
            conn.commit()

    return {
        "metric_period": metric_period,
        "market_skills": len(market_intelligence.market_skills),
        "gap_observations": len(gap_observations),
        "recommendations": len(recommendations),
        "role_graph_edges": len(role_graph),
        "company_profiles": len(company_obs),
        "emerging_technologies": len(emerging_tech),
        "persisted": persisted,
        "dashboard_exports": dashboard_exports,
    }
