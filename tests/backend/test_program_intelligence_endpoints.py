from __future__ import annotations

from fastapi.testclient import TestClient

from api import services
from api.main import app


def test_program_intelligence_list_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "list_program_intelligence",
        lambda limit=20, offset=0: {
            "items": [
                {
                    "program_id": 1,
                    "program_name": "Visual Analytics",
                    "program_role": "BI Analyst",
                    "alignment_score": 72.0,
                    "risk_score": 28.0,
                    "risk_level": "low",
                    "gap_count": 1,
                    "top_gaps": [{"missing_skill": "dbt"}],
                    "top_recommendations": [],
                    "forecast_signals": [],
                    "role_signals": [],
                    "emerging_technologies": [],
                    "recommended_actions": ["Fortalecer dbt"],
                    "business_justification": "Alineación positiva.",
                    "supporting_evidence": {"program_skills": ["Power BI"]},
                    "source_tables": ["curriculum_gap_observatory"],
                    "confidence": 0.9,
                    "generated_at": "2026-05-01T00:00:00Z",
                }
            ],
            "count": 1,
            "total": 1,
            "limit": limit,
            "offset": offset,
            "filters": {},
        },
    )

    client = TestClient(app)
    response = client.get("/program-intelligence")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["program_name"] == "Visual Analytics"


def test_program_intelligence_detail_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_program_intelligence",
        lambda program_id: {
            "program_id": program_id,
            "program_name": "Visual Analytics",
            "program_role": "BI Analyst",
            "alignment_score": 72.0,
            "risk_score": 28.0,
            "risk_level": "low",
            "gap_count": 1,
            "top_gaps": [{"missing_skill": "dbt"}],
            "top_recommendations": [],
            "forecast_signals": [],
            "role_signals": [],
            "emerging_technologies": [],
            "recommended_actions": ["Fortalecer dbt"],
            "business_justification": "Alineación positiva.",
            "supporting_evidence": {"program_skills": ["Power BI"]},
            "source_tables": ["curriculum_gap_observatory"],
            "confidence": 0.9,
            "generated_at": "2026-05-01T00:00:00Z",
        },
    )

    client = TestClient(app)
    response = client.get("/program-intelligence/1")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["program_id"] == 1
    assert payload["risk_level"] == "low"
