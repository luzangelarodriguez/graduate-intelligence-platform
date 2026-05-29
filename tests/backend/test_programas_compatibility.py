from __future__ import annotations

from fastapi.testclient import TestClient

from api import services
from api.main import app


def test_programas_list_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "list_programas_compatibility",
        lambda limit, offset: {
            "items": [
                {
                    "especializacion_id": 1,
                    "nombre_especializacion": "Visual Analytics",
                    "rol": "Analista BI",
                    "total_skills_programa": 10,
                    "total_herramientas": 4,
                    "total_competencias": 3,
                    "total_habilidades_blandas": 2,
                    "promedio_match_mercado": 73.4,
                    "porcentaje_match": 73.4,
                    "max_match_mercado": 88.1,
                    "total_empleos_relacionados": 22,
                    "skills_cubiertas": 8,
                    "skills": [],
                }
            ],
            "count": 1,
            "total": 1,
            "limit": limit,
            "offset": offset,
        },
    )

    client = TestClient(app)
    response = client.get("/api/programas", params={"limit": 5, "offset": 0})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["items"]
    assert payload["count"] == 1
    assert payload["total"] == 1
    assert payload["limit"] == 5
    assert payload["offset"] == 0


def test_programa_detail_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        services,
        "get_programa_compatibility",
        lambda program_id: {
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
            "skills": [
                {"skill_id": 1, "nombre": "Power BI", "conteo": 4},
            ],
        },
    )

    client = TestClient(app)
    response = client.get("/api/programas/42")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["especializacion_id"] == 42
    assert payload["nombre_especializacion"] == "Visual Analytics y Big Data"
    assert payload["skills"][0]["nombre"] == "Power BI"


def test_programas_pagination_passthrough(monkeypatch) -> None:
    seen: dict[str, int] = {}

    def fake_list_programas_compatibility(*, limit: int, offset: int):
        seen["limit"] = limit
        seen["offset"] = offset
        return {
            "items": [],
            "count": 0,
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    monkeypatch.setattr(services, "list_programas_compatibility", fake_list_programas_compatibility)

    client = TestClient(app)
    response = client.get("/api/programas", params={"limit": 7, "offset": 3})

    assert response.status_code == 200
    assert seen == {"limit": 7, "offset": 3}
    assert response.json()["limit"] == 7
    assert response.json()["offset"] == 3


def test_programa_detail_404(monkeypatch) -> None:
    def fake_get_programa_compatibility(_program_id: int):
        raise KeyError("programa 999 not found")

    monkeypatch.setattr(services, "get_programa_compatibility", fake_get_programa_compatibility)

    client = TestClient(app)
    response = client.get("/api/programas/999")

    assert response.status_code == 404
    assert "not found" in response.text.lower()
