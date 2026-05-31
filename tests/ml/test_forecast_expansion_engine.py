from __future__ import annotations

from datetime import UTC, datetime

from intelligence import forecast_expansion_engine as fee
from intelligence.predictive_intelligence_engine import MarketForecastRecord


def _forecast_record(entity_type: str, entity_name: str, horizon: int, growth: float, confidence: float) -> MarketForecastRecord:
    return MarketForecastRecord(
        entity_type=entity_type,
        entity_name=entity_name,
        horizon_months=horizon,
        growth_velocity=growth,
        forecast_confidence=confidence,
        market_phase="growing",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        evidence={"source": "test"},
    )


def test_forecast_expansion_builds_all_entity_types(monkeypatch) -> None:
    monkeypatch.setattr(
        fee,
        "build_market_demand_forecasts",
        lambda db_name=None, persist=False, limit=50: [
            _forecast_record("skill", "AWS", 12, 0.82, 0.78),
            _forecast_record("skill", "Databricks", 12, 0.74, 0.71),
        ],
    )
    monkeypatch.setattr(fee, "relation_exists", lambda table_name, db_name=None: table_name in {
        "emerging_technology_observatory",
        "company_observatory",
        "semantic_role_graph",
        "career_transitions",
        "skill_trend_forecast",
        "technology_forecasts",
        "company_forecasts",
        "role_forecasts",
        "market_forecasts",
    })
    monkeypatch.setattr(
        fee,
        "fetch_all",
        lambda sql, params=None, db_name=None: (
            [
                {"technology": "Generative AI", "emergence_score": 88, "growth_velocity": 0.86, "adoption_trend": "up", "forecast_confidence": 0.82, "first_seen_at": datetime.now(UTC), "last_seen_at": datetime.now(UTC), "source_payload": {"source": "technology"}},
                {"technology": "Microsoft Fabric", "emergence_score": 81, "growth_velocity": 0.8, "adoption_trend": "up", "forecast_confidence": 0.78, "first_seen_at": datetime.now(UTC), "last_seen_at": datetime.now(UTC), "source_payload": {"source": "technology"}},
            ]
            if "FROM emerging_technology_observatory" in sql
            else [
                {"company": "Globant", "dominant_stack": "AWS", "dominant_cluster": "Cloud Analytics", "hiring_velocity": 74, "ai_adoption_score": 81, "cloud_maturity_score": 77, "bi_maturity_score": 69, "technology_maturity": "advanced", "top_skills": ["AWS"], "top_clusters": ["Cloud Analytics"], "evidence": {"source": "company"}},
                {"company": "Rappi", "dominant_stack": "Databricks", "dominant_cluster": "Data Engineering", "hiring_velocity": 68, "ai_adoption_score": 70, "cloud_maturity_score": 73, "bi_maturity_score": 60, "technology_maturity": "advanced", "top_skills": ["Databricks"], "top_clusters": ["Data Engineering"], "evidence": {"source": "company"}},
            ]
            if "FROM company_observatory" in sql
            else [
                {"source_role": "Business Analyst", "target_role": "Data Analyst", "similarity_score": 0.74, "transition_probability": 0.69, "shared_skills": ["SQL"], "cluster_affinity": 0.71, "created_at": datetime.now(UTC)},
                {"source_role": "Data Analyst", "target_role": "Analytics Engineer", "similarity_score": 0.81, "transition_probability": 0.77, "shared_skills": ["dbt"], "cluster_affinity": 0.79, "created_at": datetime.now(UTC)},
            ]
            if "FROM semantic_role_graph" in sql
            else [
                {"source_role": "Business Analyst", "target_role": "Data Analyst", "role_progression_probability": 0.72, "transition_skill_gaps": ["SQL"], "recommended_next_skills": ["Python"], "created_at": datetime.now(UTC)},
                {"source_role": "Data Analyst", "target_role": "Analytics Engineer", "role_progression_probability": 0.81, "transition_skill_gaps": ["dbt"], "recommended_next_skills": ["dbt"], "created_at": datetime.now(UTC)},
            ]
        ),
    )

    bundle = fee.build_forecast_expansion(persist=False)
    summary = fee.build_forecast_summary(persist=False)

    assert bundle.skill
    assert bundle.technology
    assert bundle.company
    assert bundle.role
    assert summary["counts"]["skill"] > 0
    assert summary["counts"]["technology"] > 0
    assert summary["counts"]["company"] > 0
    assert summary["counts"]["role"] > 0
