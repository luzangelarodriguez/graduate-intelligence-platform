from __future__ import annotations

from dataclasses import dataclass

from backend import database_config


@dataclass
class DummyCursor:
    total: int = 57

    def execute(self, sql: str) -> None:
        self.sql = sql

    def fetchone(self) -> dict[str, int]:
        return {"total": self.total}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@dataclass
class DummyConnection:
    cursor_value: DummyCursor

    def cursor(self):
        return self.cursor_value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_railway_database_url_takes_priority(monkeypatch):
    monkeypatch.setenv("RAILWAY_DATABASE_URL", "postgresql://postgres:secret@ballast.proxy.rlwy.net:59250/railway")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/warehouse")
    monkeypatch.setenv("LOCAL_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("LOCAL_DB_PORT", "5432")
    monkeypatch.setenv("LOCAL_DB_NAME", "labor_observatory")
    monkeypatch.setenv("LOCAL_DB_USER", "postgres")
    monkeypatch.setenv("LOCAL_DB_PASSWORD", "postgres")

    diagnostics = database_config.get_connection_parameters()

    assert diagnostics["mode"] == "railway"
    assert diagnostics["connection_source"] == "RAILWAY_DATABASE_URL"
    assert diagnostics["host"] == "ballast.proxy.rlwy.net"
    assert diagnostics["port"] == 59250
    assert diagnostics["database"] == "railway"


def test_database_url_is_used_when_railway_missing(monkeypatch):
    monkeypatch.delenv("RAILWAY_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/warehouse")
    monkeypatch.setenv("LOCAL_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("LOCAL_DB_PORT", "5432")
    monkeypatch.setenv("LOCAL_DB_NAME", "labor_observatory")
    monkeypatch.setenv("LOCAL_DB_USER", "postgres")
    monkeypatch.setenv("LOCAL_DB_PASSWORD", "postgres")

    diagnostics = database_config.get_connection_parameters()

    assert diagnostics["mode"] == "database_url"
    assert diagnostics["connection_source"] == "DATABASE_URL"
    assert diagnostics["host"] == "db.example.com"
    assert diagnostics["database"] == "warehouse"


def test_local_database_variables_are_used_when_urls_missing(monkeypatch):
    monkeypatch.delenv("RAILWAY_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LOCAL_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("LOCAL_DB_PORT", "5432")
    monkeypatch.setenv("LOCAL_DB_NAME", "labor_observatory")
    monkeypatch.setenv("LOCAL_DB_USER", "postgres")
    monkeypatch.setenv("LOCAL_DB_PASSWORD", "postgres")

    diagnostics = database_config.get_connection_parameters()

    assert diagnostics["mode"] == "local"
    assert diagnostics["connection_source"] == "LOCAL_DB_HOST"
    assert diagnostics["host"] == "127.0.0.1"
    assert diagnostics["database"] == "labor_observatory"


def test_test_connection_reports_table_count(monkeypatch):
    dummy_connection = DummyConnection(cursor_value=DummyCursor(total=57))
    monkeypatch.setenv("RAILWAY_DATABASE_URL", "postgresql://postgres:secret@ballast.proxy.rlwy.net:59250/railway")
    monkeypatch.setattr(database_config.psycopg2, "connect", lambda **kwargs: dummy_connection)

    diagnostics = database_config.test_connection()

    assert diagnostics["mode"] == "railway"
    assert diagnostics["tables_found"] == 57
