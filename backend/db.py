from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse, unquote

import psycopg2
from psycopg2.extras import RealDictCursor


logger = logging.getLogger(__name__)
_LOGGED_CONNECTION_SOURCE: str | None = None


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value not in {None, ""}:
            return value
    return None


def _sslmode_default() -> str:
    return os.getenv("DB_SSLMODE") or os.getenv("PGSSLMODE") or ("require" if os.getenv("APP_ENV") == "production" else "prefer")


def _url_with_sslmode(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme.startswith("postgres"):
        return raw_url
    query = parse_qs(parsed.query, keep_blank_values=True)
    query.setdefault("sslmode", [_sslmode_default()])
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _select_connection_source() -> tuple[str, str | None]:
    url = _first_env("DATABASE_URL", "RAILWAY_DATABASE_URL")
    if url:
        source = "DATABASE_URL" if os.getenv("DATABASE_URL") else "RAILWAY_DATABASE_URL"
        return source, _url_with_sslmode(url)

    db_host = _first_env("DB_HOST")
    pg_host = _first_env("PGHOST")
    host = db_host or pg_host
    port = _first_env("DB_PORT") or _first_env("PGPORT") or "5432"
    database = _first_env("DB_NAME") or _first_env("PGDATABASE")
    user = _first_env("DB_USER") or _first_env("PGUSER")
    password = _first_env("DB_PASSWORD") or _first_env("PGPASSWORD")
    if host and database and user and password:
        return ("DB_HOST" if db_host else "PGHOST"), None
    return "UNCONFIGURED", None


def _database_config(db_name: str | None = None) -> dict[str, Any]:
    source, database_url = _select_connection_source()
    if source in {"DATABASE_URL", "RAILWAY_DATABASE_URL"} and database_url:
        parsed = urlparse(database_url)
        return {
            "connection_source": source,
            "host": parsed.hostname or "",
            "port": parsed.port or 5432,
            "dbname": db_name or parsed.path.lstrip("/"),
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "sslmode": parse_qs(parsed.query).get("sslmode", [_sslmode_default()])[0],
        }

    config = {
        "connection_source": "DB_HOST" if _first_env("DB_HOST") else "PGHOST",
        "host": _first_env("DB_HOST") or _first_env("PGHOST"),
        "port": int(_first_env("DB_PORT") or _first_env("PGPORT") or "5432"),
        "dbname": db_name or _first_env("DB_NAME") or _first_env("PGDATABASE"),
        "user": _first_env("DB_USER") or _first_env("PGUSER"),
        "password": _first_env("DB_PASSWORD") or _first_env("PGPASSWORD"),
        "sslmode": _sslmode_default(),
    }
    missing = [key for key in ("host", "dbname", "user", "password") if not config.get(key)]
    if missing:
        raise RuntimeError(
            "Missing PostgreSQL environment variables: "
            + ", ".join(missing)
            + ". Set DATABASE_URL, RAILWAY_DATABASE_URL, DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD or PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD."
        )
    return config


def get_database_diagnostics(db_name: str | None = None) -> dict[str, Any]:
    config = _database_config(db_name=db_name)
    return {
        "host": config["host"],
        "port": str(config["port"]),
        "database": config["dbname"],
        "connection_source": config["connection_source"],
    }


def _log_database_diagnostics(config: dict[str, Any]) -> None:
    global _LOGGED_CONNECTION_SOURCE
    connection_source = str(config.get("connection_source") or "unknown")
    if _LOGGED_CONNECTION_SOURCE == connection_source:
        return
    logger.info(
        "database_connection_ready",
        extra={
            "database_connection_source": connection_source,
            "database_host": config.get("host"),
            "database_name": config.get("dbname"),
            "database_port": config.get("port"),
        },
    )
    _LOGGED_CONNECTION_SOURCE = connection_source


def get_conn(db_name: str | None = None):
    config = _database_config(db_name=db_name)
    _log_database_diagnostics(config)
    return psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
        sslmode=config["sslmode"],
        connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
        application_name=os.getenv("DB_APPLICATION_NAME", "graduate_intelligence_platform"),
        cursor_factory=RealDictCursor,
    )


@contextmanager
def get_cursor(autocommit: bool = False, db_name: str | None = None):
    conn = get_conn(db_name=db_name)
    conn.autocommit = autocommit
    try:
        with conn.cursor() as cur:
            yield cur
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()
