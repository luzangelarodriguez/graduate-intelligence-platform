from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse, unquote

import psycopg2
from dotenv import load_dotenv


logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_environment() -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value not in {None, ""}:
            return value.strip()
    return None


def _mask_url(raw_url: str | None) -> str:
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    if not parsed.scheme.startswith("postgres"):
        return raw_url
    if parsed.password is None:
        return raw_url
    netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
    return urlunparse(parsed._replace(netloc=netloc))


def _sslmode_for_mode(mode: str) -> str:
    explicit = _first_env("DB_SSLMODE", "PGSSLMODE")
    if explicit:
        return explicit
    return "require" if mode == "railway" else "prefer"


def _compose_local_url(host: str, port: str, database: str, user: str, password: str, sslmode: str) -> str:
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}?sslmode={sslmode}"


def _select_source() -> tuple[str, str | None]:
    railway_url = _first_env("RAILWAY_DATABASE_URL")
    if railway_url:
        return "railway", railway_url
    database_url = _first_env("DATABASE_URL")
    if database_url:
        return "database_url", database_url
    local_host = _first_env("LOCAL_DB_HOST")
    local_port = _first_env("LOCAL_DB_PORT")
    local_name = _first_env("LOCAL_DB_NAME")
    local_user = _first_env("LOCAL_DB_USER")
    local_password = _first_env("LOCAL_DB_PASSWORD")
    if all([local_host, local_port, local_name, local_user, local_password]):
        return "local", None
    db_host = _first_env("DB_HOST")
    db_port = _first_env("DB_PORT")
    db_name = _first_env("DB_NAME")
    db_user = _first_env("DB_USER")
    db_password = _first_env("DB_PASSWORD")
    if all([db_host, db_port, db_name, db_user, db_password]):
        return "legacy_local", None
    pg_host = _first_env("PGHOST")
    pg_port = _first_env("PGPORT")
    pg_database = _first_env("PGDATABASE")
    pg_user = _first_env("PGUSER")
    pg_password = _first_env("PGPASSWORD")
    if all([pg_host, pg_port, pg_database, pg_user, pg_password]):
        return "pg", None
    return "unconfigured", None


def get_database_mode() -> str:
    _load_environment()
    mode, _ = _select_source()
    return mode


def get_database_url(db_name: str | None = None) -> str | None:
    _load_environment()
    mode, url = _select_source()
    if mode in {"railway", "database_url"} and url:
        parsed = urlparse(url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        query.setdefault("sslmode", [_sslmode_for_mode(mode)])
        if db_name:
            parsed = parsed._replace(path=f"/{db_name}")
        elif not parsed.path.lstrip("/"):
            parsed = parsed._replace(path="/")
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    connection = get_connection_parameters(db_name=db_name)
    if connection["mode"] == "unconfigured":
        return None
    return _compose_local_url(
        str(connection["host"]),
        str(connection["port"]),
        str(connection["database"]),
        str(connection["user"]),
        str(connection["password"]),
        str(connection["sslmode"]),
    )


def get_connection_parameters(db_name: str | None = None) -> dict[str, Any]:
    _load_environment()
    mode, url = _select_source()
    connect_timeout = int(_first_env("DB_CONNECT_TIMEOUT") or "10")
    application_name = _first_env("DB_APPLICATION_NAME") or "graduate_intelligence_platform"
    pool_min_size = int(_first_env("DATABASE_POOL_MIN_SIZE") or "1")
    pool_max_size = int(_first_env("DATABASE_POOL_MAX_SIZE") or "4")

    if mode in {"railway", "database_url"} and url:
        parsed = urlparse(url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        sslmode = query.get("sslmode", [_sslmode_for_mode(mode)])[0]
        return {
            "mode": mode,
            "connection_source": "RAILWAY_DATABASE_URL" if mode == "railway" else "DATABASE_URL",
            "database_url": get_database_url(db_name=db_name),
            "host": parsed.hostname or "",
            "port": parsed.port or 5432,
            "database": db_name or parsed.path.lstrip("/"),
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "sslmode": sslmode,
            "connect_timeout": connect_timeout,
            "application_name": application_name,
            "pool_min_size": pool_min_size,
            "pool_max_size": pool_max_size,
        }

    if mode in {"local", "legacy_local", "pg"}:
        if mode == "local":
            host = _first_env("LOCAL_DB_HOST") or "127.0.0.1"
            port = int(_first_env("LOCAL_DB_PORT") or "5432")
            database = db_name or _first_env("LOCAL_DB_NAME") or "labor_observatory"
            user = _first_env("LOCAL_DB_USER") or "postgres"
            password = _first_env("LOCAL_DB_PASSWORD") or "postgres"
            connection_source = "LOCAL_DB_HOST"
        elif mode == "legacy_local":
            host = _first_env("DB_HOST") or "127.0.0.1"
            port = int(_first_env("DB_PORT") or "5432")
            database = db_name or _first_env("DB_NAME") or "labor_observatory"
            user = _first_env("DB_USER") or "postgres"
            password = _first_env("DB_PASSWORD") or "postgres"
            connection_source = "DB_HOST"
        else:
            host = _first_env("PGHOST") or "127.0.0.1"
            port = int(_first_env("PGPORT") or "5432")
            database = db_name or _first_env("PGDATABASE") or "labor_observatory"
            user = _first_env("PGUSER") or "postgres"
            password = _first_env("PGPASSWORD") or "postgres"
            connection_source = "PGHOST"
        sslmode = _sslmode_for_mode(mode)
        return {
            "mode": "local" if mode == "local" else ("legacy_local" if mode == "legacy_local" else "pg"),
            "connection_source": connection_source,
            "database_url": _compose_local_url(host, str(port), database, user, password, sslmode),
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
            "sslmode": sslmode,
            "connect_timeout": connect_timeout,
            "application_name": application_name,
            "pool_min_size": pool_min_size,
            "pool_max_size": pool_max_size,
        }

    raise RuntimeError(
        "Missing PostgreSQL environment variables: set RAILWAY_DATABASE_URL, DATABASE_URL, "
        "LOCAL_DB_HOST/LOCAL_DB_PORT/LOCAL_DB_NAME/LOCAL_DB_USER/LOCAL_DB_PASSWORD, "
        "DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD, or PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD."
    )


def _row_value(row: Any, key: str, index: int = 0, default: Any = 0) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    if isinstance(row, (tuple, list)):
        return row[index] if len(row) > index else default
    getter = getattr(row, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            return default
    try:
        return row[index]
    except Exception:
        return default


def test_connection() -> dict[str, Any]:
    config = get_connection_parameters()
    diagnostics = {
        "mode": config["mode"],
        "connection_source": config["connection_source"],
        "host": config["host"],
        "port": config["port"],
        "database": config["database"],
        "user": config["user"],
        "tables_found": 0,
    }
    with psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=config["user"],
        password=config["password"],
        sslmode=config["sslmode"],
        connect_timeout=int(config["connect_timeout"]),
        application_name=str(config["application_name"]),
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::int AS total FROM information_schema.tables WHERE table_schema = 'public'")
            row = cur.fetchone()
            tables_found = _row_value(row, "total", index=0, default=0)
            try:
                diagnostics["tables_found"] = int(tables_found or 0)
            except (TypeError, ValueError):
                diagnostics["tables_found"] = 0
    logger.info(
        "database_connection_test",
        extra={
            "database_mode": diagnostics["mode"],
            "database_source": diagnostics["connection_source"],
            "database_host": diagnostics["host"],
            "database_name": diagnostics["database"],
            "tables_found": diagnostics["tables_found"],
        },
    )
    return diagnostics


def _format_diagnostics(diagnostics: dict[str, Any]) -> str:
    return "\n".join(
        [
            "=================================",
            "DATABASE CONFIGURATION",
            "======================",
            f"Mode: {diagnostics.get('mode')}",
            f"Host: {diagnostics.get('host')}",
            f"Port: {diagnostics.get('port')}",
            f"Database: {diagnostics.get('database')}",
            f"User: {diagnostics.get('user')}",
            "==============",
        ]
    )


def main() -> None:
    diagnostics = get_connection_parameters()
    print(_format_diagnostics(diagnostics))


if __name__ == "__main__":
    main()
