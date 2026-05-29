from __future__ import annotations

import os
import time
from contextlib import contextmanager
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus, urlparse, urlunparse

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool


def _environment(value: str | None, default: str) -> str:
    return value if value not in {None, ""} else default


def _default_sslmode() -> str:
    return _environment(os.getenv("DB_SSLMODE"), "require" if os.getenv("DATABASE_URL") else "prefer")


def _normalize_database_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        return raw_url
    if parsed.hostname is None:
        return raw_url
    sslmode = os.getenv("DB_SSLMODE")
    if sslmode and "sslmode=" not in parsed.query:
        query = f"{parsed.query}&sslmode={sslmode}" if parsed.query else f"sslmode={sslmode}"
        parsed = parsed._replace(query=query)
    return urlunparse(parsed)


def _build_database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
    if url:
        return _normalize_database_url(url)

    host = os.getenv("DB_HOST") or os.getenv("LOCAL_DB_HOST") or "127.0.0.1"
    port = os.getenv("DB_PORT") or os.getenv("LOCAL_DB_PORT") or "5432"
    name = os.getenv("DB_NAME") or os.getenv("LOCAL_DB_NAME") or "labor_observatory"
    user = os.getenv("DB_USER") or os.getenv("LOCAL_DB_USER") or "postgres"
    password = os.getenv("DB_PASSWORD") or os.getenv("LOCAL_DB_PASSWORD") or "postgres"
    sslmode = _default_sslmode()
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}"
        f"?sslmode={sslmode}"
    )


@lru_cache(maxsize=1)
def _pool() -> ThreadedConnectionPool:
    minconn = int(os.getenv("DATABASE_POOL_MIN_SIZE", "1"))
    maxconn = int(os.getenv("DATABASE_POOL_MAX_SIZE", "4"))
    dsn = _build_database_url()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return ThreadedConnectionPool(minconn, maxconn, dsn=dsn)
        except Exception as exc:  # pragma: no cover - retry glue
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


@contextmanager
def connection():
    conn = _pool().getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool().putconn(conn)


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def relation_exists(name: str) -> bool:
    row = fetch_one("SELECT to_regclass(%s) IS NOT NULL AS exists", (name,))
    return bool(row and row.get("exists"))


def relation_has_rows(name: str) -> bool:
    if not relation_exists(name):
        return False
    row = fetch_one(f"SELECT EXISTS (SELECT 1 FROM {name} LIMIT 1) AS has_rows")
    return bool(row and row.get("has_rows"))


def table_row_count(name: str) -> int:
    if not relation_exists(name):
        return 0
    row = fetch_one(f"SELECT COUNT(*)::int AS total FROM {name}")
    return int((row or {}).get("total") or 0)


def startup_validate(required_relations: tuple[str, ...] = ()) -> dict[str, Any]:
    health = {"database": False, "required_relations": {}, "dsn": "configured"}
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone() or {}
            health["database"] = bool(row.get("ok"))
    for relation in required_relations:
        health["required_relations"][relation] = relation_exists(relation)
    return health

