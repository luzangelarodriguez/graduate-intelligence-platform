from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, execute_values


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"

CURRICULAR_TABLES = [
    "especializaciones",
    "skills",
    "herramientas",
    "competencias",
    "habilidades_blandas",
    "perfiles_egreso",
    "especializacion_skills",
    "especializacion_herramientas",
    "especializacion_competencias",
    "especializacion_habilidades_blandas",
]


@dataclass(frozen=True)
class DbConfig:
    label: str
    host: str
    port: int
    dbname: str
    user: str
    password: str
    sslmode: str = "prefer"
    connect_timeout: int = 15

    def redacted(self) -> str:
        return f"{self.label}: {self.user}@{self.host}:{self.port}/{self.dbname} sslmode={self.sslmode}"


class SyncError(RuntimeError):
    pass


def load_dotenv_files() -> None:
    for name in (".env", ".env.development", ".env.local"):
        path = ROOT / name
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def setup_logging() -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"sync_to_railway_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    return log_path


def parse_database_url(label: str, database_url: str, sslmode: str) -> DbConfig:
    parsed = urlparse(database_url)
    if not parsed.hostname or not parsed.path:
        raise SyncError(f"{label}: DATABASE_URL invalida.")
    return DbConfig(
        label=label,
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        sslmode=sslmode,
    )


def config_from_prefixed_env(
    *,
    label: str,
    prefix: str,
    defaults: dict[str, str] | None = None,
    sslmode_default: str = "prefer",
) -> DbConfig:
    defaults = defaults or {}
    database_url = os.getenv(f"{prefix}DATABASE_URL")
    if database_url:
        return parse_database_url(label, database_url, os.getenv(f"{prefix}DB_SSLMODE", sslmode_default))

    values = {
        "host": os.getenv(f"{prefix}DB_HOST") or os.getenv(f"{prefix}PGHOST") or defaults.get("host"),
        "port": os.getenv(f"{prefix}DB_PORT") or os.getenv(f"{prefix}PGPORT") or defaults.get("port", "5432"),
        "dbname": os.getenv(f"{prefix}DB_NAME") or os.getenv(f"{prefix}PGDATABASE") or defaults.get("dbname"),
        "user": os.getenv(f"{prefix}DB_USER") or os.getenv(f"{prefix}PGUSER") or defaults.get("user"),
        "password": os.getenv(f"{prefix}DB_PASSWORD") or os.getenv(f"{prefix}PGPASSWORD") or defaults.get("password"),
        "sslmode": os.getenv(f"{prefix}DB_SSLMODE") or defaults.get("sslmode", sslmode_default),
    }
    missing = [key for key, value in values.items() if value in (None, "")]
    if missing:
        raise SyncError(f"{label}: faltan variables de conexion: {', '.join(missing)}")
    return DbConfig(
        label=label,
        host=str(values["host"]),
        port=int(str(values["port"])),
        dbname=str(values["dbname"]),
        user=str(values["user"]),
        password=str(values["password"]),
        sslmode=str(values["sslmode"]),
    )


def get_local_config() -> DbConfig:
    return config_from_prefixed_env(
        label="local",
        prefix="LOCAL_",
        defaults={
            "host": "127.0.0.1",
            "port": "5433",
            "dbname": "cliente_a_db",
            "user": "postgres",
            "password": "postgres",
            "sslmode": "prefer",
        },
    )


def get_railway_config() -> DbConfig:
    if os.getenv("RAILWAY_DATABASE_URL"):
        return parse_database_url("railway", os.environ["RAILWAY_DATABASE_URL"], os.getenv("RAILWAY_DB_SSLMODE", "require"))
    if os.getenv("DATABASE_URL"):
        return parse_database_url("railway", os.environ["DATABASE_URL"], os.getenv("DB_SSLMODE", "require"))

    try:
        return config_from_prefixed_env(label="railway", prefix="RAILWAY_", sslmode_default="require")
    except SyncError:
        if os.getenv("ALLOW_DB_ENV_TARGET", "").lower() not in {"1", "true", "yes"}:
            raise SyncError(
                "No se encontro RAILWAY_DATABASE_URL, DATABASE_URL ni RAILWAY_DB_*. "
                "Para evitar sincronizar contra la base local por accidente, configure "
                "RAILWAY_DATABASE_URL en .env.local. Use ALLOW_DB_ENV_TARGET=true solo en Railway."
            )
        return config_from_prefixed_env(label="railway", prefix="", sslmode_default="require")


def connect(config: DbConfig):
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        sslmode=config.sslmode,
        connect_timeout=config.connect_timeout,
        application_name="graduate_intelligence_sync_to_railway",
    )


def validate_not_same_database(local: DbConfig, railway: DbConfig, allow_same_db: bool) -> None:
    same = (
        local.host == railway.host
        and local.port == railway.port
        and local.dbname == railway.dbname
        and local.user == railway.user
    )
    if same and not allow_same_db:
        raise SyncError(
            "La conexion local y Railway parecen apuntar a la misma base. "
            "Use --allow-same-db solo si esta validando el script."
        )


def fetch_columns(conn, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND is_generated = 'NEVER'
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [row[0] for row in cur.fetchall()]


def fetch_primary_key(conn, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid
             AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
              AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            """,
            (f"public.{table}",),
        )
        return [row[0] for row in cur.fetchall()]


def fetch_unique_constraints(conn, table: str) -> list[list[str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT array_agg(a.attname ORDER BY array_position(i.indkey, a.attnum)) AS columns
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid
             AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
              AND i.indisunique
              AND NOT i.indisprimary
            GROUP BY i.indexrelid
            ORDER BY COUNT(*) DESC
            """,
            (f"public.{table}",),
        )
        return [list(row[0]) for row in cur.fetchall()]


def validate_table(conn, table: str, label: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
        if cur.fetchone()[0] is None:
            raise SyncError(f"{label}: la tabla public.{table} no existe.")


def table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
        return cur.fetchone()[0] is not None


def count_rows(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM public.{}").format(sql.Identifier(table)))
        return int(cur.fetchone()[0])


def choose_conflict_columns(conn, table: str, common_columns: list[str]) -> list[str]:
    primary_key = fetch_primary_key(conn, table)
    if primary_key and set(primary_key).issubset(common_columns):
        return primary_key
    for unique_columns in fetch_unique_constraints(conn, table):
        if unique_columns and set(unique_columns).issubset(common_columns):
            return unique_columns
    raise SyncError(f"railway: public.{table} no tiene PK/UNIQUE usable para UPSERT.")


def upsert_batch(target_conn, table: str, columns: list[str], conflict_columns: list[str], rows: list[tuple]) -> int:
    if not rows:
        return 0
    adapted_rows = [
        tuple(Json(value) if isinstance(value, (dict, list)) else value for value in row)
        for row in rows
    ]

    update_columns = [col for col in columns if col not in conflict_columns]
    if update_columns:
        update_sql = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
            for col in update_columns
        )
        conflict_action = sql.SQL("DO UPDATE SET {}").format(update_sql)
    else:
        conflict_action = sql.SQL("DO NOTHING")

    statement = sql.SQL("INSERT INTO public.{} ({}) VALUES %s ON CONFLICT ({}) {}").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(map(sql.Identifier, conflict_columns)),
        conflict_action,
    )
    with target_conn.cursor() as cur:
        execute_values(cur, statement.as_string(target_conn), adapted_rows, page_size=len(adapted_rows))
    return len(adapted_rows)


def reset_sequence(target_conn, table: str) -> None:
    if "id" not in fetch_columns(target_conn, table):
        return
    with target_conn.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (f"public.{table}", "id"))
        sequence_row = cur.fetchone()
        if not sequence_row or not sequence_row[0]:
            return
        cur.execute(
            sql.SQL("SELECT setval(%s, COALESCE((SELECT MAX(id) FROM public.{}), 1), true)").format(
                sql.Identifier(table)
            ),
            (sequence_row[0],),
        )


def sync_table(source_conn, target_conn, table: str, batch_size: int) -> dict[str, int | str]:
    validate_table(target_conn, table, "railway")
    if not table_exists(source_conn, table):
        logging.warning("Omitiendo public.%s: no existe en PostgreSQL local.", table)
        return {
            "table": table,
            "source_rows": 0,
            "upserted_rows": 0,
            "conflict_key": "skipped_missing_source",
        }

    source_columns = fetch_columns(source_conn, table)
    target_columns = fetch_columns(target_conn, table)
    common_columns = [col for col in source_columns if col in target_columns]
    if not common_columns:
        raise SyncError(f"public.{table}: no hay columnas comunes entre local y Railway.")

    conflict_columns = choose_conflict_columns(target_conn, table, common_columns)
    local_count = count_rows(source_conn, table)
    logging.info("Migrando public.%s | origen=%s | columnas=%s", table, local_count, ", ".join(common_columns))

    select_sql = sql.SQL("SELECT {} FROM public.{} ORDER BY {}").format(
        sql.SQL(", ").join(map(sql.Identifier, common_columns)),
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, conflict_columns)),
    )

    processed = 0
    with source_conn.cursor() as source_cur:
        source_cur.execute(select_sql)
        while True:
            rows = source_cur.fetchmany(batch_size)
            if not rows:
                break
            processed += upsert_batch(target_conn, table, common_columns, conflict_columns, rows)

    reset_sequence(target_conn, table)
    return {
        "table": table,
        "source_rows": local_count,
        "upserted_rows": processed,
        "conflict_key": ",".join(conflict_columns),
    }


def inspect_table_for_sync(source_conn, target_conn, table: str) -> dict[str, int | str]:
    validate_table(target_conn, table, "railway")
    if not table_exists(source_conn, table):
        logging.warning("Dry-run public.%s | omitida: no existe en PostgreSQL local.", table)
        return {
            "table": table,
            "source_rows": 0,
            "target_rows_before": count_rows(target_conn, table),
            "common_columns": 0,
            "conflict_key": "skipped_missing_source",
        }

    source_columns = fetch_columns(source_conn, table)
    target_columns = fetch_columns(target_conn, table)
    common_columns = [col for col in source_columns if col in target_columns]
    if not common_columns:
        raise SyncError(f"public.{table}: no hay columnas comunes entre local y Railway.")

    conflict_columns = choose_conflict_columns(target_conn, table, common_columns)
    return {
        "table": table,
        "source_rows": count_rows(source_conn, table),
        "target_rows_before": count_rows(target_conn, table),
        "common_columns": len(common_columns),
        "conflict_key": ",".join(conflict_columns),
    }


def parse_tables(raw_tables: str | None) -> list[str]:
    if not raw_tables:
        return CURRICULAR_TABLES
    tables = [part.strip() for part in raw_tables.split(",") if part.strip()]
    if not tables:
        raise SyncError("--tables no contiene tablas validas.")
    return tables


def run_sync(tables: Iterable[str], batch_size: int, dry_run: bool, allow_same_db: bool) -> int:
    local_config = get_local_config()
    railway_config = get_railway_config()
    validate_not_same_database(local_config, railway_config, allow_same_db)

    logging.info("Conexion origen: %s", local_config.redacted())
    logging.info("Conexion destino: %s", railway_config.redacted())
    if dry_run:
        logging.info("Modo dry-run activo: valida conexiones/tablas sin insertar datos.")

    results: list[dict[str, int | str]] = []
    with connect(local_config) as source_conn, connect(railway_config) as target_conn:
        source_conn.autocommit = True
        target_conn.autocommit = False

        with source_conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            logging.info("Local OK: database=%s user=%s", *cur.fetchone())
        with target_conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            logging.info("Railway OK: database=%s user=%s", *cur.fetchone())

        try:
            for table in tables:
                if dry_run:
                    result = inspect_table_for_sync(source_conn, target_conn, table)
                    logging.info(
                        "Dry-run public.%s | local=%s | railway_actual=%s | columnas_comunes=%s | clave=%s",
                        result["table"],
                        result["source_rows"],
                        result["target_rows_before"],
                        result["common_columns"],
                        result["conflict_key"],
                    )
                    continue
                results.append(sync_table(source_conn, target_conn, table, batch_size))

            if dry_run:
                target_conn.rollback()
                return 0

            target_conn.commit()
        except Exception:
            target_conn.rollback()
            logging.exception("Fallo la sincronizacion. Rollback aplicado en Railway.")
            raise

    logging.info("Resumen final")
    for result in results:
        logging.info(
            "Tabla=%s | origen=%s | upsert=%s | clave=%s",
            result["table"],
            result["source_rows"],
            result["upserted_rows"],
            result["conflict_key"],
        )
    return 0


def main() -> int:
    load_dotenv_files()
    log_path = setup_logging()
    parser = argparse.ArgumentParser(description="Sincroniza datos curriculares locales hacia PostgreSQL Railway.")
    parser.add_argument("--tables", help="Lista separada por coma. Por defecto migra tablas curriculares core.")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("SYNC_BATCH_SIZE", "1000")))
    parser.add_argument("--dry-run", action="store_true", help="Valida conexiones y tablas sin insertar.")
    parser.add_argument("--allow-same-db", action="store_true", help="Permite origen y destino iguales para pruebas.")
    args = parser.parse_args()

    logging.info("Log: %s", log_path)
    try:
        return run_sync(parse_tables(args.tables), args.batch_size, args.dry_run, args.allow_same_db)
    except Exception as exc:
        logging.error("Sincronizacion fallida: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
