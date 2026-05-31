from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_executive_observatory_endpoint_returns_v2_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.services.get_executive_observatory",
        lambda: {
            "metrics": [],
            "alignment_average": 68.5,
            "high_risk_programs": [{"program_id": 2, "program_name": "Data Engineering"}],
            "medium_risk_programs": [{"program_id": 3, "program_name": "Visual Analytics"}],
            "low_risk_programs": [{"program_id": 1, "program_name": "BI"}],
            "programs_analyzed": 3,
            "critical_gaps": [{"missing_skill": "GenAI"}],
            "top_emerging_skills": [{"skill_name": "AI Agents"}],
            "top_recommendations": [{"recommendation_type": "curriculum"}],
            "top_programs": [{"program_id": 1, "program_name": "BI"}],
            "at_risk_programs": [{"program_id": 2, "program_name": "Data Engineering"}],
            "executive_narrative": "The institution shows moderate alignment with labor market demand.",
            "source_tables": ["program_intelligence", "observatory_metrics", "recommendation_observatory"],
            "confidence": 0.92,
        },
    )

    response = client.get("/executive-observatory")

    assert response.status_code == 200
    payload = response.json()
    assert payload["alignment_average"] == 68.5
    assert payload["programs_analyzed"] == 3
    assert payload["executive_narrative"].startswith("The institution shows moderate alignment")
    assert "AI Agents" in str(payload["top_emerging_skills"])
