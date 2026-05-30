from __future__ import annotations

from fastapi.testclient import TestClient

from api import services
from api.main import app


def test_curriculum_risk_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_curriculum_risk_index",
        lambda program_id: {
            "program_id": program_id,
            "program_name": "Visual Analytics",
            "risk_score": 63.2,
            "risk_level": "high",
            "risk_drivers": [{"driver": "missing_skills", "value": 0.4, "impact": 40.0, "evidence": ["dbt"]}],
            "recommended_actions": ["Fortalecer dbt"],
            "supporting_evidence": {"source_tables": ["especializaciones", "jobs"]},
            "source_tables": ["especializaciones", "jobs"],
            "confidence": 0.83,
        },
    )

    client = TestClient(app)
    response = client.get("/programas/42/curriculum-risk")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["program_id"] == 42
    assert payload["risk_level"] == "high"
    assert payload["recommended_actions"][0] == "Fortalecer dbt"


def test_alignment_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_university_market_alignment",
        lambda program_id: {
            "program_id": program_id,
            "program_name": "Visual Analytics",
            "alignment_score": 78.4,
            "alignment_level": "healthy",
            "current_alignment": 78.4,
            "projected_alignment_if_added": 92.1,
            "missing_skills": ["GenAI", "RAG"],
            "emerging_skills": ["Microsoft Fabric"],
            "company_demand_score": 0.7,
            "labor_demand_score": 0.8,
            "forecasted_demand_score": 0.82,
            "emerging_technology_score": 0.74,
            "explanation": "Alineacion actual: 78.4%.",
            "supporting_evidence": {"source_tables": ["especializaciones", "market_forecasts"]},
            "source_tables": ["especializaciones", "market_forecasts"],
            "confidence": 0.81,
        },
    )

    client = TestClient(app)
    response = client.get("/programas/42/alignment")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["alignment_score"] == 78.4
    assert payload["projected_alignment_if_added"] == 92.1
    assert "GenAI" in payload["missing_skills"]


def test_career_intelligence_and_executive_observatory(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_career_intelligence",
        lambda source_role=None, limit=12: {
            "source_role": source_role or "",
            "transitions": [
                {
                    "source_role": "Business Analyst",
                    "target_role": "Data Analyst",
                    "required_skills": ["SQL", "Power BI"],
                    "difficulty_score": 0.45,
                    "estimated_salary_progression": 1200.0,
                    "transition_probability": 0.72,
                    "source_family": "BI & Visualization",
                    "target_family": "Analytics Engineering",
                    "supporting_evidence": {"source_tables": ["semantic_role_graph"]},
                }
            ],
            "role_network": [{"source_role": "Business Analyst", "target_role": "Data Analyst"}],
            "source_tables": ["semantic_role_graph", "career_transitions"],
            "confidence": 0.9,
        },
    )
    monkeypatch.setattr(
        services,
        "get_executive_observatory",
        lambda: {
            "metrics": [
                {
                    "metric_name": "programs_at_risk",
                    "metric_category": "executive",
                    "metric_value": 4,
                    "metric_period": "2026-05",
                    "confidence_score": 0.9,
                    "source_tables": ["observatory_metrics"],
                    "supporting_evidence": {"alignment_scores": [0.7]},
                }
            ],
            "source_tables": ["observatory_metrics"],
            "confidence": 0.9,
        },
    )
    monkeypatch.setattr(
        services,
        "list_recommendations_v2",
        lambda program_id=None, limit=20, offset=0: {
            "items": [
                {
                    "recommendation_type": "curriculum",
                    "target_entity": "Visual Analytics",
                    "target_company": "curriculum",
                    "recommendation_score": 0.84,
                    "priority": "high",
                    "business_justification": "Brechas de mercado detectadas.",
                    "expected_impact": "Mejorar alineacion",
                    "confidence": 0.8,
                    "estimated_alignment_increase": 11.0,
                    "recommendation_evidence": {"missing_skills": ["GenAI"]},
                    "recommendation_reasoning": "Actualizar curriculum",
                }
            ],
            "count": 1,
            "limit": limit,
            "offset": offset,
            "filters": {"program_id": program_id, "version": "v2", "source": "predictive_engine"},
        },
    )

    client = TestClient(app)
    career = client.get("/career-intelligence?source_role=Business%20Analyst")
    exec_obs = client.get("/executive-observatory")
    recs = client.get("/recommendations-v2?program_id=42")

    assert career.status_code == 200, career.text
    assert career.json()["transitions"][0]["target_role"] == "Data Analyst"
    assert exec_obs.status_code == 200, exec_obs.text
    assert exec_obs.json()["metrics"][0]["metric_name"] == "programs_at_risk"
    assert recs.status_code == 200, recs.text
    assert recs.json()["items"][0]["priority"] == "high"
