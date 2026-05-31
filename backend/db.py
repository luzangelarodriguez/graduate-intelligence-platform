from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.database_config import get_connection_parameters, get_database_url


logger = logging.getLogger(__name__)
_LOGGED_CONNECTION_SOURCE: str | None = None


def get_database_diagnostics(db_name: str | None = None) -> dict[str, Any]:
    config = get_connection_parameters(db_name=db_name)
    return {
        "host": config["host"],
        "port": str(config["port"]),
        "database": config["database"],
        "connection_source": config["connection_source"],
        "mode": config["mode"],
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
            "database_name": config.get("database"),
            "database_port": config.get("port"),
        },
    )
    _LOGGED_CONNECTION_SOURCE = connection_source


def get_conn(db_name: str | None = None):
    config = get_connection_parameters(db_name=db_name)
    _log_database_diagnostics(config)
    database_url = get_database_url(db_name=db_name)
    return psycopg2.connect(
        dsn=database_url,
        connect_timeout=int(config["connect_timeout"]),
        application_name=str(config["application_name"]),
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
