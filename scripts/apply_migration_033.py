#!/usr/bin/env python3
"""
Apply migration 033: occupational profiles for Marketing y Publicidad.

Usage:
    python scripts/apply_migration_033.py [--yes]

Behavior:
    1. Reads credentials from environment (same vars as the rest of the app).
    2. Previews how many profiles and patterns would actually be inserted
       (skipping rows that already exist via ON CONFLICT DO NOTHING).
    3. Asks for interactive confirmation "Confirm? [yes/no]" unless --yes is passed.
    4. Runs the whole migration in a single transaction; rolls back on any error.

Does NOT print credential values at any point.
Idempotent: safe to run more than once.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env.local")
except ImportError:
    pass

import psycopg2
import psycopg2.extras
from backend.database_config import get_connection_parameters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

MIGRATION_FILE = ROOT / "database" / "migrations" / "033_marketing_profiles_catalog.sql"

# Profiles defined in this migration (used for the preview count).
_NEW_PROFILES = [
    "Especialista en Marketing Digital",
    "Community Manager",
    "Especialista en SEO/SEM",
    "Brand Manager",
    "Ejecutivo de Cuenta Publicidad",
    "Diseñador / Creativo Publicitario",
    "Analista de Investigación de Mercados",
    "Especialista en Trade Marketing",
    "Especialista en Growth",
    "Especialista en E-commerce",
]

# Patterns defined in this migration (used for the preview count).
_NEW_PATTERNS = [
    "%marketing digital%",
    "%mercadeo%digital%",
    "%digital marketing%",
    "%especialista%marketing%",
    "%coordinador%marketing%",
    "%coordinador%mercadeo%",
    "%analista%marketing%",
    "%analista%mercadeo%",
    "%marketing analyst%",
    "%campa%as digitales%",
    "%director%marketing%",
    "%director%mercadeo%",
    "%jefe%marketing%",
    "%jefe%mercadeo%",
    "%gerente%marketing%",
    "%gerente%mercadeo%",
    "%aprendiz%mercadeo%",
    "%community manager%",
    "%social media%",
    "%gestor%redes sociales%",
    "%content creator%",
    "%creador%contenido%",
    "% seo%",
    "seo %",
    "%pauta digital%",
    "%performance%marketing%",
    "%google ads%",
    "%meta ads%",
    "%paid media%",
    "%brand manager%",
    "%gerente%marca%",
    "%director%marca%",
    "%ejecutivo%cuenta%publicidad%",
    "%ejecutivo%cuenta%agencia%",
    "%director creativo%",
    "%diseñador%publicidad%",
    "%copywriter%",
    "%investigaci%n%mercado%",
    "%market research%",
    "%analista%consumidor%",
    "%trade marketing%",
    "% growth%",
    "%growth hac%",
    "%e-commerce%",
    "%ecommerce%",
    "%comercio electr%nico%",
]


def _connect() -> psycopg2.extensions.connection:
    cfg = get_connection_parameters()
    return psycopg2.connect(
        host=str(cfg["host"]),
        port=int(cfg["port"]),
        dbname=str(cfg["database"]),
        user=str(cfg["user"]),
        password=str(cfg["password"]),
        sslmode=str(cfg["sslmode"]),
        connect_timeout=int(cfg["connect_timeout"]),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _preview(cur: psycopg2.extensions.cursor) -> tuple[int, int]:
    """Return (profiles_to_insert, patterns_to_insert) — what ON CONFLICT would skip."""
    cur.execute(
        "SELECT nombre FROM public.occupational_profiles WHERE nombre = ANY(%s)",
        (_NEW_PROFILES,),
    )
    existing_profiles = {r["nombre"] for r in cur.fetchall()}
    profiles_new = len(_NEW_PROFILES) - len(existing_profiles)

    cur.execute(
        "SELECT patron FROM public.job_profile_mappings WHERE patron = ANY(%s)",
        (_NEW_PATTERNS,),
    )
    existing_patterns = {r["patron"] for r in cur.fetchall()}
    patterns_new = len(_NEW_PATTERNS) - len(existing_patterns)

    return profiles_new, patterns_new


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true",
                        help="Skip interactive confirmation (for CI/automated use).")
    args = parser.parse_args()

    sql = MIGRATION_FILE.read_text(encoding="utf-8")

    conn = _connect()
    try:
        with conn.cursor() as cur:
            # ── Preview ────────────────────────────────────────────────────────
            profiles_new, patterns_new = _preview(cur)

            logger.info("── Migration 033 — preview ──────────────────────────")
            logger.info("  Profiles to insert  : %d / %d", profiles_new, len(_NEW_PROFILES))
            logger.info("  Patterns to insert  : %d / %d", patterns_new, len(_NEW_PATTERNS))
            if profiles_new == 0 and patterns_new == 0:
                logger.info("  Nothing to do — all rows already exist. Exiting.")
                return
            logger.info("────────────────────────────────────────────────────")

            # ── Confirmation ───────────────────────────────────────────────────
            if not args.yes:
                answer = input("\nConfirm? [yes/no]: ").strip().lower()
                if answer != "yes":
                    logger.info("Cancelled.")
                    conn.rollback()
                    return

            # ── Apply in one transaction ───────────────────────────────────────
            cur.execute(sql)
            conn.commit()
            logger.info("✓ Migration 033 applied successfully.")

    except Exception:
        conn.rollback()
        logger.exception("Error — rollback applied.")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
