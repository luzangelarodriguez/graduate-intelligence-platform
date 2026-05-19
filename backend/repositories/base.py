from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from backend.db import get_conn


@contextmanager
def cursor(db_name: str | None = None):
    conn = get_conn(db_name=db_name)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params: tuple[Any, ...] = (), *, db_name: str | None = None) -> list[dict[str, Any]]:
    with cursor(db_name=db_name) as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def fetch_one(sql: str, params: tuple[Any, ...] = (), *, db_name: str | None = None) -> dict[str, Any] | None:
    with cursor(db_name=db_name) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def relation_exists(name: str, *, db_name: str | None = None) -> bool:
    row = fetch_one("SELECT to_regclass(%s) IS NOT NULL AS exists", (name,), db_name=db_name)
    return bool(row and row.get("exists"))


def pick_relation(names: tuple[str, ...], *, db_name: str | None = None) -> str | None:
    for name in names:
        if relation_exists(name, db_name=db_name):
            return name
    return None


def relation_has_rows(name: str, *, db_name: str | None = None) -> bool:
    if not relation_exists(name, db_name=db_name):
        return False
    try:
        row = fetch_one(f"SELECT EXISTS (SELECT 1 FROM {name} LIMIT 1) AS has_rows", db_name=db_name)
        return bool(row and row.get("has_rows"))
    except Exception:
        return False
