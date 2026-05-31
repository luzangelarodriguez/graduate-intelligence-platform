from __future__ import annotations

from fastapi.testclient import TestClient

from api import services
from api.main import app


def test_critical_programs_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_critical_programs",
        lambda limit=20, offset=0, horizon_months=12: {
            "items": [
                {
                    "program_id": 42,
                    "program_name": "Visual Analytics",
                    "program_role": "BI",
                    "alignment_score": 48.0,
                    "risk_score": 82.0,
                    "risk_level": "critical",
                    "gap_count": 7,
                    "main_gap_driver": "AWS",
                    "recommended_action": "Incluir AWS",
                    "projected_employability_gain": 12.5,
                    "horizon_months": horizon_months,
                    "supporting_evidence": {"source_tables": ["program_intelligence"]},
                    "source_tables": ["program_intelligence"],
                    "confidence": 0.81,
                    "generated_at": "2026-05-31T00:00:00Z",
                }
            ],
            "count": 1,
            "limit": limit,
            "offset": offset,
            "filters": {"horizon_months": horizon_months},
        },
    )

    client = TestClient(app)
    response = client.get("/critical-programs?horizon_months=12")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["items"][0]["risk_level"] == "critical"
    assert payload["items"][0]["main_gap_driver"] == "AWS"


def test_curriculum_simulator_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_curriculum_simulator",
        lambda program_id, proposed_skills=None, horizon_months=12: {
            "program_id": program_id,
            "program_name": "Data Engineering",
            "program_role": "DE",
            "horizon_months": horizon_months,
            "current_alignment_score": 48.0,
            "current_risk_score": 76.0,
            "projected_alignment_score": 63.0,
            "projected_risk_score": 58.0,
            "projected_employability_gain": 14.5,
            "projected_gap_reduction": 32.0,
            "confidence_score": 0.82,
            "proposed_skills": ["AWS", "Databricks"],
            "normalized_skills": [{"canonical_skill": "AWS"}, {"canonical_skill": "Databricks"}],
            "risk_drivers": [{"driver": "curriculum_gap", "value": 82, "impact": 32}],
            "supporting_evidence": {"source_tables": ["program_intelligence"]},
            "source_tables": ["program_intelligence", "curriculum_gap_observatory"],
            "explanation": "Simulación basada en brechas reales.",
            "simulation_key": "program-42",
            "generated_at": "2026-05-31T00:00:00Z",
        },
    )

    client = TestClient(app)
    response = client.get("/curriculum-simulator?program_id=42&proposed_skills=AWS,Databricks")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["projected_alignment_score"] == 63.0
    assert payload["proposed_skills"] == ["AWS", "Databricks"]


def test_forecast_summary_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_forecast_summary",
        lambda limit=25: {
            "generated_at": "2026-05-31T00:00:00Z",
            "source_tables": ["market_forecasts", "technology_forecasts", "company_forecasts", "role_forecasts"],
            "total_records": 4,
            "counts": {"skill": 1, "technology": 1, "company": 1, "role": 1},
            "coverage": {"skill": 0.25, "technology": 0.25, "company": 0.25, "role": 0.25},
            "top_skills": [
                {
                    "entity_type": "skill",
                    "entity_name": "AWS",
                    "horizon_months": 12,
                    "growth_velocity": 0.82,
                    "forecast_confidence": 0.78,
                    "market_phase": "emerging",
                    "first_seen_at": None,
                    "last_seen_at": None,
                    "evidence": {"source": "market_forecasts"},
                }
            ],
            "top_technologies": [],
            "top_companies": [],
            "top_roles": [],
        },
    )

    client = TestClient(app)
    response = client.get("/forecast-summary")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["counts"]["technology"] == 1
    assert payload["top_skills"][0]["entity_name"] == "AWS"
