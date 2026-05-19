from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg2
from psycopg2.extras import execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from scrapers.taxonomy.domain_taxonomy import DOMAIN_DEFINITIONS, SKILL_DEFINITIONS, iter_alias_rows
except ModuleNotFoundError:
    from taxonomy.domain_taxonomy import DOMAIN_DEFINITIONS, SKILL_DEFINITIONS, iter_alias_rows


@contextmanager
def get_connection() -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def load_taxonomy() -> None:
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.domains (code, name, description)
            VALUES %s
            ON CONFLICT (code)
            DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
            """,
            [(item.code, item.name, item.description) for item in DOMAIN_DEFINITIONS],
        )
        execute_values(
            cur,
            """
            INSERT INTO public.skills_master (canonical_name, domain, tipo, descripcion)
            VALUES %s
            ON CONFLICT (canonical_name)
            DO UPDATE SET domain = EXCLUDED.domain, tipo = EXCLUDED.tipo, descripcion = EXCLUDED.descripcion
            """,
            [(item.canonical_name, item.domain, item.tipo, item.descripcion) for item in SKILL_DEFINITIONS],
        )
        execute_values(
            cur,
            """
            INSERT INTO public.skills_alias (alias, canonical_skill)
            VALUES %s
            ON CONFLICT (alias)
            DO UPDATE SET canonical_skill = EXCLUDED.canonical_skill
            """,
            list(iter_alias_rows()),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Load the enterprise domain and skills taxonomy into PostgreSQL.")
    parser.parse_args()
    load_taxonomy()
    print("taxonomy loaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
