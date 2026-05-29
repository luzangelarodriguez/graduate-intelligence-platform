from __future__ import annotations

import os

import httpx
import pytest


API_BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8010").rstrip("/")
ACCESS_TOKEN = os.getenv("TEST_ACCESS_TOKEN", "")


def api_client(*, auth: bool = False) -> httpx.Client:
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"} if auth and ACCESS_TOKEN else {}
    return httpx.Client(base_url=API_BASE_URL, headers=headers, timeout=10)


def require_api_available() -> None:
    try:
        response = api_client().get("/api/health")
    except httpx.HTTPError as exc:
        pytest.skip(f"FastAPI no disponible en {API_BASE_URL}: {exc}")
    if response.status_code >= 500:
        pytest.skip(f"FastAPI disponible pero no saludable: {response.text}")


def require_auth_token() -> None:
    if not ACCESS_TOKEN:
        pytest.skip("Define TEST_ACCESS_TOKEN para ejecutar endpoints protegidos.")


def first_program_id() -> int:
    require_auth_token()
    with api_client(auth=True) as client:
        response = client.get("/api/programas", params={"limit": 1})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["items"], "Se requiere al menos un programa para pruebas funcionales."
    return int(payload["items"][0]["especializacion_id"])


def test_health_endpoint_reports_database_status() -> None:
    require_api_available()
    with api_client() as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "fastapi-postgresql"
    assert payload["database"] == "ok"


def test_programas_endpoint_returns_page_contract() -> None:
    require_api_available()
    require_auth_token()
    with api_client(auth=True) as client:
        response = client.get("/api/programas", params={"limit": 5})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert {"items", "count", "limit", "offset"}.issubset(payload)
    assert payload["limit"] == 5
    assert isinstance(payload["items"], list)


def test_dashboard_kpis_endpoint_returns_kpi_contract() -> None:
    require_api_available()
    require_auth_token()
    with api_client(auth=True) as client:
        response = client.get("/api/dashboard/kpis")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "kpis" in payload
    assert "source" in payload
    assert {"total_programas", "total_empleos", "total_matches"}.issubset(payload["kpis"])


def test_matches_endpoint_returns_page_contract() -> None:
    require_api_available()
    require_auth_token()
    with api_client(auth=True) as client:
        response = client.get("/api/matches", params={"limit": 5})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert {"items", "count", "limit", "offset"}.issubset(payload)
    assert isinstance(payload["items"], list)


def test_recommendations_endpoints_return_page_contracts() -> None:
    require_api_available()
    program_id = first_program_id()
    with api_client(auth=True) as client:
        program_response = client.get("/api/recommendations/programs", params={"program_id": program_id, "limit": 3})
        jobs_response = client.get("/api/recommendations/jobs", params={"program_id": program_id, "limit": 3})
    assert program_response.status_code == 200, program_response.text
    assert jobs_response.status_code == 200, jobs_response.text
    assert {"items", "count", "limit", "offset"}.issubset(program_response.json())
    assert {"items", "count", "limit", "offset"}.issubset(jobs_response.json())
