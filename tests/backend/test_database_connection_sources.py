from __future__ import annotations

from dataclasses import dataclass

from backend import db as backend_db


@dataclass
class DummyConnection:
    closed: bool = False

    def close(self) -> None:
        self.closed = True


def _capture_connect(monkeypatch):
    captured: dict[str, object] = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return DummyConnection()

    monkeypatch.setattr(backend_db.psycopg2, "connect", fake_connect)
    monkeypatch.setattr(backend_db, "_LOGGED_CONNECTION_SOURCE", None)
    return captured


def test_database_url_priority(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/warehouse")
    monkeypatch.setenv("RAILWAY_DATABASE_URL", "postgresql://rail:pass@rail.example.com:5432/railway")
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    captured = _capture_connect(monkeypatch)

    conn = backend_db.get_conn()
    assert isinstance(conn, DummyConnection)
    assert captured["host"] == "db.example.com"
    assert captured["port"] == 5432
    assert captured["dbname"] == "warehouse"
    assert backend_db.get_database_diagnostics()["connection_source"] == "DATABASE_URL"


def test_railway_database_url_priority(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RAILWAY_DATABASE_URL", "postgresql://user:pass@rail.example.com:6543/railway")
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    captured = _capture_connect(monkeypatch)

    backend_db.get_conn()
    assert captured["host"] == "rail.example.com"
    assert captured["port"] == 6543
    assert captured["dbname"] == "railway"
    assert backend_db.get_database_diagnostics()["connection_source"] == "RAILWAY_DATABASE_URL"


def test_db_host_priority(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RAILWAY_DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "labor_observatory")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "postgres")
    captured = _capture_connect(monkeypatch)

    backend_db.get_conn()
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 5433
    assert captured["dbname"] == "labor_observatory"
    assert backend_db.get_database_diagnostics()["connection_source"] == "DB_HOST"


def test_pghost_priority(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RAILWAY_DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.setenv("PGHOST", "pg.example.com")
    monkeypatch.setenv("PGPORT", "5434")
    monkeypatch.setenv("PGDATABASE", "pg_warehouse")
    monkeypatch.setenv("PGUSER", "pguser")
    monkeypatch.setenv("PGPASSWORD", "pgpass")
    captured = _capture_connect(monkeypatch)

    backend_db.get_conn()
    assert captured["host"] == "pg.example.com"
    assert captured["port"] == 5434
    assert captured["dbname"] == "pg_warehouse"
    assert backend_db.get_database_diagnostics()["connection_source"] == "PGHOST"
