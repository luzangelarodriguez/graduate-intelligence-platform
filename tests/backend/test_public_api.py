from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from api.main import app
from api import services


client = TestClient(app)


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(
        services,
        "get_health_snapshot",
        lambda: {
            "status": "ok",
            "database": "connected",
            "timestamp": datetime.now(UTC),
            "checks": {"database": True, "jobs_table": True},
            "observatory_freshness": {},
        },
    )
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"


def test_recommendations_endpoint(monkeypatch):
    monkeypatch.setattr(
        services,
        "list_recommendations",
        lambda **kwargs: {
            "items": [
                {
                    "recommendation_type": "career",
                    "target_role": "Analytics Engineer",
                    "target_company": "market",
                }
            ],
            "count": 1,
            "limit": kwargs.get("limit", 20),
            "offset": kwargs.get("offset", 0),
            "filters": {"recommendation_type": kwargs.get("recommendation_type")},
        },
    )
    response = client.get("/recommendations?limit=10&offset=0&recommendation_type=career")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["target_role"] == "Analytics Engineer"


def test_semantic_search_endpoint(monkeypatch):
    monkeypatch.setattr(
        services,
        "semantic_search_results",
        lambda query, entity_type="job", limit=10: {
            "query": query,
            "entity_type": entity_type,
            "count": 1,
            "limit": limit,
            "items": [
                {
                    "entity_type": entity_type,
                    "entity_id": "1",
                    "title": "Analytics Engineer",
                    "similarity_score": 0.91,
                    "evidence": {"matched_query": query},
                }
            ],
        },
    )
    response = client.get("/semantic-search?q=Analytics Engineer&entity_type=role&limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["entity_type"] == "role"
    assert payload["items"][0]["title"] == "Analytics Engineer"


def test_observatory_status_endpoint(monkeypatch):
    monkeypatch.setattr(
        services,
        "get_observatory_status",
        lambda: {
            "status": "partial_observatory",
            "observatory_tables": {
                "observatory_metrics": False,
                "curriculum_gap_observatory": False,
                "recommendation_observatory": False,
            },
            "missing_tables": [
                "observatory_metrics",
                "curriculum_gap_observatory",
                "recommendation_observatory",
            ],
            "completion_percentage": 0.5,
        },
    )
    response = client.get("/observatory-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial_observatory"
    assert payload["completion_percentage"] == 0.5
