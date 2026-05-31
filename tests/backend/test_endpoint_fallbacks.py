from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api import services


client = TestClient(app)


def test_programas_detail_falls_back_on_service_failure(monkeypatch):
    monkeypatch.setattr(services, "get_programa_compatibility", lambda program_id: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/api/programas/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["especializacion_id"] == 1
    assert payload["nombre_especializacion"]
    assert payload["skills"] == []


def test_programas_dashboard_falls_back_on_service_failure(monkeypatch):
    monkeypatch.setattr(services, "get_program_dashboard_compatibility", lambda program_id: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/api/dashboard/programa/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == 1
    assert payload["source"] == "fallback"
    assert payload["matches"] == []


def test_curriculum_risk_endpoint_falls_back(monkeypatch):
    monkeypatch.setattr(services, "build_curriculum_risk_index", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/programas/1/curriculum-risk")
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == 1
    assert payload["risk_score"] == 0.0
    assert payload["risk_level"] in {"low", "critical", "medium"}


def test_alignment_endpoint_falls_back(monkeypatch):
    monkeypatch.setattr(services, "build_university_market_alignment", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/programas/1/alignment")
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == 1
    assert payload["alignment_score"] == 0.0


def test_curriculum_simulator_falls_back(monkeypatch):
    monkeypatch.setattr(services, "build_curriculum_impact_simulation", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/curriculum-simulator", params={"program_id": 1, "proposed_skills": "Azure, Databricks", "horizon_months": 12})
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == 1
    assert payload["projected_alignment_score"] >= payload["current_alignment_score"]
    assert "fallback" in payload["simulation_key"]


def test_forecast_summary_falls_back(monkeypatch):
    monkeypatch.setattr(services, "build_forecast_summary", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/forecast-summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_records"] == 0
    assert payload["top_skills"] == []


def test_executive_observatory_falls_back(monkeypatch):
    monkeypatch.setattr(services, "build_executive_observatory_v2", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/executive-observatory")
    assert response.status_code == 200
    payload = response.json()
    assert payload["confidence"] == 0.0
    assert payload["programs_analyzed"] >= 0


def test_program_summary_falls_back(monkeypatch):
    monkeypatch.setattr(services, "build_executive_program_summary", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/program-summary/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == 1
    assert payload["model"] == "deterministic-fallback"


def test_recommendation_explanation_falls_back(monkeypatch):
    monkeypatch.setattr(services, "build_executive_recommendation_explanation", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.get("/recommendation-explanation/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation_id"] == 1
    assert payload["model"] == "deterministic-fallback"


def test_ask_observatory_falls_back(monkeypatch):
    monkeypatch.setattr(services, "executive_ask_observatory", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    response = client.post("/ask-observatory", json={"question": "¿Qué programas requieren actualización inmediata?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["question"]
    assert payload["model"] == "deterministic-fallback"
