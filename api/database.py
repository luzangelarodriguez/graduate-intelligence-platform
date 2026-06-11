from __future__ import annotations

import time
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from backend.database_config import get_connection_parameters, get_database_url


@lru_cache(maxsize=1)
def _pool() -> ThreadedConnectionPool:
    params = get_connection_parameters()
    minconn = int(params.get("pool_min_size") or 1)
    maxconn = int(params.get("pool_max_size") or 4)
    dsn = get_database_url()
    # ensure UTF-8 so Spanish characters aren't mangled
    if dsn and "client_encoding" not in dsn:
        sep = "&" if "?" in dsn else "?"
        dsn = f"{dsn}{sep}options=-c%20client_encoding%3DUTF8"
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
    conn.set_client_encoding("UTF8")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool().putconn(conn)


def fetch_all(sql: str, params: tuple[Any, ...] = (), *, db_name: str | None = None) -> list[dict[str, Any]]:
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params: tuple[Any, ...] = (), *, db_name: str | None = None) -> dict[str, Any] | None:
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def relation_exists(name: str, *, db_name: str | None = None) -> bool:
    row = fetch_one("SELECT to_regclass(%s) IS NOT NULL AS exists", (name,), db_name=db_name)
    return bool(row and row.get("exists"))


def relation_has_rows(name: str, *, db_name: str | None = None) -> bool:
    if not relation_exists(name, db_name=db_name):
        return False
    row = fetch_one(f"SELECT EXISTS (SELECT 1 FROM {name} LIMIT 1) AS has_rows", db_name=db_name)
    return bool(row and row.get("has_rows"))


def table_row_count(name: str, *, db_name: str | None = None) -> int:
    if not relation_exists(name, db_name=db_name):
        return 0
    row = fetch_one(f"SELECT COUNT(*)::int AS total FROM {name}", db_name=db_name)
    return int((row or {}).get("total") or 0)


def startup_validate(required_relations: tuple[str, ...] = (), *, db_name: str | None = None) -> dict[str, Any]:
    health = {"database": False, "required_relations": {}, "dsn": "configured"}
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone() or {}
            health["database"] = bool(row.get("ok"))
    for relation in required_relations:
        health["required_relations"][relation] = relation_exists(relation, db_name=db_name)
    return health
