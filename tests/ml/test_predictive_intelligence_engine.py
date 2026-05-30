from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import intelligence.predictive_intelligence_engine as engine


def _fake_market_map() -> SimpleNamespace:
    return SimpleNamespace(
        market_skills=[
            SimpleNamespace(skill="Power BI"),
            SimpleNamespace(skill="SQL"),
        ],
        covered_skills=[SimpleNamespace(skill="Power BI")],
        partial_skills=[SimpleNamespace(skill="SQL")],
        missing_skills=[],
        emerging_skills=[SimpleNamespace(skill="Microsoft Fabric")],
        recommended_updates=[],
        curriculum_gaps=[],
    )


def test_curriculum_risk_and_alignment_scores_with_explainability(monkeypatch) -> None:
    monkeypatch.setattr(engine.programas_repository, "resolve_program_id", lambda program_id, db_name=None: program_id)
    monkeypatch.setattr(
        engine.dashboard_service,
        "list_programs_base",
        lambda db_name=None: [
            {"especializacion_id": 1, "nombre_especializacion": "Visual Analytics", "rol": "Analista BI", "promedio_match_mercado": 72.0},
        ],
    )
    monkeypatch.setattr(
        engine.programas_repository,
        "fetch_program_base_row",
        lambda program_id, db_name=None: {"especializacion_id": program_id, "nombre_especializacion": "Visual Analytics", "rol": "Analista BI", "promedio_match_mercado": 72.0},
    )
    monkeypatch.setattr(
        engine.programas_repository,
        "fetch_program_skill_rows",
        lambda program_id, db_name=None: [{"skill_id": 1, "nombre": "Power BI"}, {"skill_id": 2, "nombre": "dbt"}, {"skill_id": 3, "nombre": "RAG"}],
    )
    monkeypatch.setattr(engine, "_fetch_market_skill_map", _fake_market_map)
    monkeypatch.setattr(engine, "relation_exists", lambda name, db_name=None: False)

    risk = engine.build_curriculum_risk_index(1)
    alignment = engine.build_university_market_alignment(1)

    assert risk.program_id == 1
    assert risk.risk_score > 0
    assert risk.risk_level in {"low", "moderate", "high", "critical"}
    assert risk.risk_drivers
    assert risk.recommended_actions
    assert "skills" in risk.supporting_evidence

    assert alignment.program_id == 1
    assert alignment.alignment_score >= 0
    assert alignment.projected_alignment_if_added >= alignment.alignment_score
    assert alignment.explanation
    assert "source_tables" in alignment.supporting_evidence


def test_market_forecasts_cover_four_horizons_and_entity_types(monkeypatch) -> None:
    month_1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    month_2 = datetime(2026, 2, 1, tzinfo=timezone.utc)

    def fake_relation_exists(name: str, db_name=None) -> bool:
        return name in {"jobs", "job_skills", "canonical_skills", "industries"}

    def fake_fetch_all(sql: str, params=(), db_name=None):
        if "unknown_skill_candidates" in sql:
            return [
                {
                    "skill_name": "Microsoft Fabric",
                    "mention_count": 5,
                    "company_count": 3,
                    "first_seen_at": month_1,
                    "last_seen_at": month_2,
                    "roles": ["Analytics Engineer"],
                },
                {
                    "skill_name": "SQL",
                    "mention_count": 10,
                    "company_count": 5,
                    "first_seen_at": month_1,
                    "last_seen_at": month_2,
                    "roles": ["Data Analyst"],
                },
            ]
        if "FROM market_forecasts" in sql:
            return [
                {
                    "entity_name": "Microsoft Fabric",
                    "growth_velocity": 0.82,
                    "forecast_confidence": 0.78,
                    "first_seen_at": month_1,
                    "last_seen_at": month_2,
                    "evidence": {"source": "market_forecasts"},
                }
            ]
        if "'skill' AS entity_type" in sql:
            return [
                {"entity_type": "skill", "entity_name": "Power BI", "month_bucket": month_1, "count": 2, "company_count": 1, "avg_probability": 0.7, "first_seen_at": month_1, "last_seen_at": month_2},
                {"entity_type": "skill", "entity_name": "Power BI", "month_bucket": month_2, "count": 5, "company_count": 2, "avg_probability": 0.8, "first_seen_at": month_1, "last_seen_at": month_2},
            ]
        if "'role' AS entity_type" in sql:
            return [
                {"entity_type": "role", "entity_name": "Analytics Engineer", "month_bucket": month_1, "count": 1, "company_count": 1, "avg_probability": 0.65, "first_seen_at": month_1, "last_seen_at": month_2},
                {"entity_type": "role", "entity_name": "Analytics Engineer", "month_bucket": month_2, "count": 3, "company_count": 2, "avg_probability": 0.82, "first_seen_at": month_1, "last_seen_at": month_2},
            ]
        if "'technology' AS entity_type" in sql:
            return [
                {"entity_type": "technology", "entity_name": "Microsoft Fabric", "month_bucket": month_1, "count": 1, "company_count": 1, "avg_probability": 0.6, "first_seen_at": month_1, "last_seen_at": month_2},
                {"entity_type": "technology", "entity_name": "Microsoft Fabric", "month_bucket": month_2, "count": 4, "company_count": 3, "avg_probability": 0.86, "first_seen_at": month_1, "last_seen_at": month_2},
            ]
        if "'industry' AS entity_type" in sql:
            return [
                {"entity_type": "industry", "entity_name": "Education", "month_bucket": month_1, "count": 2, "company_count": 1, "avg_probability": 0.7, "first_seen_at": month_1, "last_seen_at": month_2},
                {"entity_type": "industry", "entity_name": "Education", "month_bucket": month_2, "count": 2, "company_count": 1, "avg_probability": 0.72, "first_seen_at": month_1, "last_seen_at": month_2},
            ]
        return []

    monkeypatch.setattr(engine, "relation_exists", fake_relation_exists)
    monkeypatch.setattr(engine, "fetch_all", fake_fetch_all)

    forecasts = engine.build_market_demand_forecasts()
    emerging = engine.detect_emerging_skills()

    assert len(forecasts) == 16
    assert {item.horizon_months for item in forecasts} == {3, 6, 12, 24}
    assert any(item.entity_type == "skill" and item.entity_name == "Power BI" for item in forecasts)
    assert emerging
    assert emerging[0].skill_name == "Microsoft Fabric"
    assert emerging[0].confidence_score > 0
