from __future__ import annotations

from fastapi.testclient import TestClient

from api import services
from api.main import app


def test_dashboard_programa_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_program_dashboard_compatibility",
        lambda program_id: {
            "program_id": program_id,
            "program": {
                "especializacion_id": program_id,
                "nombre_especializacion": "Visual Analytics y Big Data",
                "rol": "Analista BI",
                "total_skills_programa": 12,
                "total_herramientas": 5,
                "total_competencias": 4,
                "total_habilidades_blandas": 3,
                "promedio_match_mercado": 76.2,
                "porcentaje_match": 76.2,
                "max_match_mercado": 91.0,
                "total_empleos_relacionados": 31,
                "skills_cubiertas": 9,
                "skills": [{"skill_id": 1, "nombre": "Power BI", "conteo": 4}],
            },
            "kpis": {
                "alignment_score": 76.2,
                "missing_critical_skills": 4,
                "high_demand_roles": 8,
                "employability_trend": 81.4,
                "digital_coverage": 58.0,
                "curricular_update_signal": "Media",
            },
            "status": {
                "curricular_status": "Contextualizado",
                "curricular_status_detail": "Análisis basado en microcurrículos reales del programa.",
                "ai_signal": "Señal IA",
                "trend_label": "Tendencia contextual de Visual Analytics y Big Data",
            },
            "missing_skills": [{"skill_id": 1, "nombre": "dbt", "conteo": 3}],
            "matches": [
                {
                    "especializacion_id": program_id,
                    "empleo_id": "job-1",
                    "titulo_empleo": "Analytics Engineer",
                    "total_skills_empleo": 8,
                    "total_skills_especializacion": 12,
                    "skills_en_comun": 6,
                    "porcentaje_match": 75.0,
                }
            ],
            "recommendations": [{"nombre": "Cloud Analytics Engineer", "match": 81.2, "reason": "Ruta cercana"}],
            "insights": {
                "detected": "Se detectó alineación relevante.",
                "ai_recommends": ["Fortalecer dbt"],
                "emerging_gap": "dbt",
                "critical_signal": "Microcurrículo real indexado",
            },
            "source": "vw_labor_program_job_matches",
        },
    )

    client = TestClient(app)
    response = client.get("/api/dashboard/programa/42")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["program_id"] == 42
    assert payload["program"]["nombre_especializacion"] == "Visual Analytics y Big Data"
    assert payload["kpis"]["alignment_score"] == 76.2
    assert payload["matches"][0]["titulo_empleo"] == "Analytics Engineer"
    assert payload["recommendations"][0]["nombre"] == "Cloud Analytics Engineer"


def test_dashboard_programa_404(monkeypatch) -> None:
    def fake_get_program_dashboard_compatibility(_program_id: int):
        raise KeyError("programa 999 not found")

    monkeypatch.setattr(services, "get_program_dashboard_compatibility", fake_get_program_dashboard_compatibility)

    client = TestClient(app)
    response = client.get("/api/dashboard/programa/999")

    assert response.status_code == 404
    assert "not found" in response.text.lower()
