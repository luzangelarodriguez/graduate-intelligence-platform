from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from sync_to_railway import (
    CURRICULAR_TABLES,
    SyncError,
    connect,
    get_railway_config,
    load_dotenv_files,
    setup_logging,
    validate_table,
)


ROOT = Path(__file__).resolve().parent


RELATION_CHECKS = {
    "especializacion_skills": [
        ("especializacion_id", "especializaciones", "id"),
        ("skill_id", "skills", "id"),
    ],
    "especializacion_herramientas": [
        ("especializacion_id", "especializaciones", "id"),
        ("herramienta_id", "herramientas", "id"),
    ],
    "especializacion_competencias": [
        ("especializacion_id", "especializaciones", "id"),
        ("competencia_id", "competencias", "id"),
    ],
    "especializacion_habilidades_blandas": [
        ("especializacion_id", "especializaciones", "id"),
        ("habilidad_id", "habilidades_blandas", "id"),
    ],
    "perfiles_egreso": [
        ("especializacion_id", "especializaciones", "id"),
    ],
}


def count_table(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM public."{table}"')
        return int(cur.fetchone()[0])


def orphan_count(conn, table: str, column: str, ref_table: str, ref_column: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM public."{table}" t
            LEFT JOIN public."{ref_table}" r
              ON r."{ref_column}" = t."{column}"
            WHERE t."{column}" IS NOT NULL
              AND r."{ref_column}" IS NULL
            """
        )
        return int(cur.fetchone()[0])


def validate_api_programas(api_base_url: str | None) -> dict[str, object] | None:
    if not api_base_url:
        return None
    url = api_base_url.rstrip("/") + "/api/programas"
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, list):
        total = len(payload)
    elif isinstance(payload, dict):
        total = len(payload.get("programas") or payload.get("items") or payload.get("data") or [])
    else:
        total = 0
    return {"url": url, "status": "ok", "programas": total}


def run_verification(api_base_url: str | None) -> int:
    config = get_railway_config()
    logging.info("Conexion Railway: %s", config.redacted())
    empty_tables: list[str] = []
    table_counts: dict[str, int] = {}
    orphan_results: dict[str, int] = {}

    with connect(config) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            logging.info("Railway OK: database=%s user=%s", *cur.fetchone())

        for table in CURRICULAR_TABLES:
            validate_table(conn, table, "railway")
            total = count_table(conn, table)
            table_counts[table] = total
            if total == 0:
                empty_tables.append(table)
            logging.info("public.%s: %s registros", table, total)

        for table, checks in RELATION_CHECKS.items():
            for column, ref_table, ref_column in checks:
                key = f"{table}.{column}->{ref_table}.{ref_column}"
                orphan_results[key] = orphan_count(conn, table, column, ref_table, ref_column)
                logging.info("Consistencia %s: %s huerfanos", key, orphan_results[key])

    api_result = None
    if api_base_url:
        try:
            api_result = validate_api_programas(api_base_url)
            logging.info("API /api/programas OK: %s programas", api_result["programas"])
        except Exception as exc:
            api_result = {"url": api_base_url.rstrip("/") + "/api/programas", "status": "error", "error": str(exc)}
            logging.warning("No se pudo validar /api/programas: %s", exc)

    summary = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "table_counts": table_counts,
        "empty_tables": empty_tables,
        "orphan_checks": orphan_results,
        "api_programas": api_result,
    }
    output = ROOT / "logs" / f"verify_railway_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("Resumen JSON: %s", output)

    if empty_tables:
        logging.warning("Tablas vacias: %s", ", ".join(empty_tables))
    if any(orphan_results.values()):
        raise SyncError("Se detectaron referencias huerfanas en tablas curriculares.")
    return 0


def main() -> int:
    load_dotenv_files()
    log_path = setup_logging()
    parser = argparse.ArgumentParser(description="Verifica datos curriculares en PostgreSQL Railway.")
    parser.add_argument("--api-base-url", default=os.getenv("API_BASE_URL"), help="Opcional. Ej: https://backend.up.railway.app")
    args = parser.parse_args()

    logging.info("Log: %s", log_path)
    try:
        return run_verification(args.api_base_url)
    except Exception as exc:
        logging.error("Verificacion fallida: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

