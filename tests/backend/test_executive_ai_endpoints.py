from __future__ import annotations

from fastapi.testclient import TestClient

from api import services
from api.main import app


def test_executive_narrative_and_program_summary_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_executive_narrative",
        lambda program_id=None: {
            "program_id": program_id,
            "program_name": "Ingeniería de Datos",
            "narrative": "La institución presenta brechas críticas en AWS y Databricks.",
            "why_at_risk": "El mercado acelera más rápido que el currículo.",
            "evidence_sources": ["program_intelligence", "market_forecasts"],
            "source_tables": ["program_intelligence", "market_forecasts"],
            "supporting_evidence": {"program_id": program_id},
            "confidence": 0.91,
            "model": "gpt-4.1-mini",
            "generated_at": "2026-05-31T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        services,
        "get_program_summary",
        lambda program_id: {
            "program_id": program_id,
            "program_name": "Ingeniería de Datos",
            "summary": "Resumen ejecutivo del programa.",
            "why_at_risk": "Exposición a gaps críticos.",
            "microcurriculum_traceability": {"microcurriculum_name": "Núcleo Datos"},
            "evidence_sources": ["program_intelligence", "curriculum_gap_observatory"],
            "source_tables": ["program_intelligence", "curriculum_gap_observatory"],
            "supporting_evidence": {"program_id": program_id},
            "confidence": 0.89,
            "model": "gpt-4.1-mini",
            "generated_at": "2026-05-31T00:00:00Z",
        },
    )

    client = TestClient(app)
    narrative = client.get("/executive-narrative?program_id=42")
    summary = client.get("/program-summary/42")

    assert narrative.status_code == 200, narrative.text
    assert summary.status_code == 200, summary.text
    assert narrative.json()["program_id"] == 42
    assert "AWS" in narrative.json()["narrative"]
    assert summary.json()["microcurriculum_traceability"]["microcurriculum_name"] == "Núcleo Datos"


def test_recommendation_explanation_and_ask_observatory(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_recommendation_explanation",
        lambda recommendation_id: {
            "recommendation_id": recommendation_id,
            "recommendation_title": "Fortalecer cloud analytics",
            "explanation": "La recomendación mejora la alineación con el mercado.",
            "why_this_recommendation": "El gap está concentrado en AWS y Databricks.",
            "evidence_sources": ["recommendation_observatory", "market_forecasts"],
            "source_tables": ["recommendation_observatory", "market_forecasts"],
            "supporting_evidence": {"recommendation_id": recommendation_id},
            "confidence": 0.93,
            "model": "gpt-4.1-mini",
            "generated_at": "2026-05-31T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        services,
        "ask_observatory",
        lambda question, program_id=None, recommendation_id=None, context=None: {
            "question": question,
            "answer": "Actualizar el currículo eleva la alineación y reduce el riesgo.",
            "evidence_sources": ["program_intelligence", "curriculum_simulations"],
            "source_tables": ["program_intelligence", "curriculum_simulations"],
            "supporting_evidence": {"program_id": program_id, "recommendation_id": recommendation_id, "context": context or {}},
            "confidence": 0.9,
            "model": "gpt-4.1-mini",
            "generated_at": "2026-05-31T00:00:00Z",
        },
    )

    client = TestClient(app)
    explanation = client.get("/recommendation-explanation/88")
    answer = client.post(
        "/ask-observatory",
        json={
            "question": "What happens if we update the curriculum?",
            "program_id": 42,
            "recommendation_id": 88,
            "context": {"selected_skills": ["AWS", "Databricks"]},
        },
    )

    assert explanation.status_code == 200, explanation.text
    assert answer.status_code == 200, answer.text
    assert explanation.json()["recommendation_id"] == 88
    assert answer.json()["answer"].startswith("Actualizar")
