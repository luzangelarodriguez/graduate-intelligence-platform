from __future__ import annotations

import os
from contextlib import contextmanager
from urllib.parse import urlparse, unquote

import psycopg2
from psycopg2.extras import RealDictCursor


def _database_config(db_name: str | None = None) -> dict[str, str | int]:
    database_url = os.getenv("DATABASE_URL")
    if database_url and not os.getenv("DB_HOST"):
        parsed = urlparse(database_url)
        return {
            "host": parsed.hostname or "",
            "port": parsed.port or 5432,
            "dbname": db_name or parsed.path.lstrip("/"),
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
        }

    config = {
        "host": os.getenv("DB_HOST") or os.getenv("PGHOST"),
        "port": os.getenv("DB_PORT") or os.getenv("PGPORT") or "5432",
        "dbname": db_name or os.getenv("DB_NAME") or os.getenv("PGDATABASE"),
        "user": os.getenv("DB_USER") or os.getenv("PGUSER"),
        "password": os.getenv("DB_PASSWORD") or os.getenv("PGPASSWORD"),
    }
    missing = [key for key, value in config.items() if value in (None, "")]
    if missing:
        raise RuntimeError(
            "Missing PostgreSQL environment variables: "
            + ", ".join(missing)
            + ". Set DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD in Railway."
        )
    return config


def get_conn(db_name: str | None = None):
    config = _database_config(db_name=db_name)
    return psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
        sslmode=os.getenv("DB_SSLMODE", "require" if os.getenv("APP_ENV") == "production" else "prefer"),
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
