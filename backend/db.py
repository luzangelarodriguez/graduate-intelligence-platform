from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn(db_name: str | None = None):
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5433'),
        dbname=db_name or os.getenv('DB_NAME', 'cliente_a_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        sslmode=os.getenv('DB_SSLMODE', 'prefer'),
        connect_timeout=int(os.getenv('DB_CONNECT_TIMEOUT', '10')),
        application_name=os.getenv('DB_APPLICATION_NAME', 'graduate_intelligence_platform'),
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
