from __future__ import annotations

from api import services


def test_health_snapshot_healthy_and_partial_observatory(monkeypatch):
    core_tables = set(services.LABOR_CORE_TABLES) | set(services.CURRICULUM_CORE_TABLES) | set(services.ML_CORE_TABLES)

    monkeypatch.setattr(services, "fetch_one", lambda sql, params=(): {"ok": 1})
    monkeypatch.setattr(services, "relation_exists", lambda name: name in core_tables)
    monkeypatch.setattr(services, "table_row_count", lambda name: 7)
    monkeypatch.setattr(services, "_latest_timestamp", lambda name: "2026-05-29T00:00:00+00:00")

    snapshot = services.get_health_snapshot()

    assert snapshot["database"] == "connected"
    assert snapshot["status"] == "healthy"
    assert snapshot["layers"]["database"] is True
    assert snapshot["layers"]["labor_core"] is True
    assert snapshot["layers"]["curriculum_core"] is True
    assert snapshot["layers"]["ml_core"] is True
    assert snapshot["layers"]["observatory"] is False
    assert snapshot["observatory_status"]["status"] == "partial_observatory"
    assert snapshot["observatory_status"]["completion_percentage"] == 0.0


def test_observatory_status_ready(monkeypatch):
    all_tables = set(services.OBSERVATORY_TABLES)

    monkeypatch.setattr(services, "relation_exists", lambda name: name in all_tables)
    monkeypatch.setattr(services, "table_row_count", lambda name: 3)
    monkeypatch.setattr(services, "_latest_timestamp", lambda name: "2026-05-29T00:00:00+00:00")

    observatory = services.get_observatory_status()

    assert observatory["status"] == "observatory_ready"
    assert observatory["completion_percentage"] == 1.0
    assert observatory["missing_tables"] == []
    assert all(observatory["observatory_tables"].values())


def test_readiness_snapshot_ready(monkeypatch):
    tables = set(services.LABOR_CORE_TABLES) | set(services.CURRICULUM_CORE_TABLES) | set(services.ML_CORE_TABLES)

    monkeypatch.setattr(services, "fetch_one", lambda sql, params=(): {"ok": 1})
    monkeypatch.setattr(services, "relation_exists", lambda name: name in tables)
    monkeypatch.setattr(services, "table_row_count", lambda name: 1)
    monkeypatch.setattr(services, "_latest_timestamp", lambda name: None)

    readiness = services.get_readiness_snapshot()

    assert readiness["status"] == "ready"
    assert readiness["layers"]["database"] is True
    assert readiness["layers"]["labor_core"] is True
    assert readiness["layers"]["curriculum_core"] is True
    assert readiness["layers"]["ml_core"] is True


def test_health_snapshot_database_failure(monkeypatch):
    monkeypatch.setattr(services, "fetch_one", lambda sql, params=(): (_ for _ in ()).throw(RuntimeError("db down")))
    monkeypatch.setattr(services, "relation_exists", lambda name: False)

    snapshot = services.get_health_snapshot()

    assert snapshot["status"] == "unhealthy"
    assert snapshot["database"] == "unavailable"
    assert snapshot["layers"]["database"] is False

