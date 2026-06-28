#!/usr/bin/env python3
"""
Daily job deactivation sweep (soft-delete, never hard-delete).

Run before or after each scraper cycle:
    python scripts/deactivate_expired_jobs.py

Sets activo=FALSE, fecha_desactivacion=NOW() for any job/empleo
whose fecha_expiracion < CURRENT_DATE. Historical records are preserved.
"""
import logging
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DEACTIVATE_SQL = """
UPDATE {table}
SET activo              = FALSE,
    fecha_desactivacion = NOW()
WHERE activo = TRUE
  AND fecha_expiracion IS NOT NULL
  AND fecha_expiracion < CURRENT_DATE
RETURNING id;
"""


def run_deactivation() -> None:
    try:
        from api.database import get_connection
    except ImportError:
        # Fallback: use psycopg2 directly with DATABASE_URL
        import os
        import psycopg2
        import psycopg2.extras

        url = os.environ.get("DATABASE_URL")
        if not url:
            log.error("DATABASE_URL not set and api.database not importable — aborting.")
            sys.exit(1)

        conn = psycopg2.connect(url)
        conn.autocommit = False

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _sweep(cur)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    import psycopg2.extras

    with get_connection() as conn:
        conn.autocommit = False
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _sweep(cur)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _sweep(cur) -> None:
    total = 0
    for table in ("empleos", "jobs"):
        try:
            cur.execute(DEACTIVATE_SQL.format(table=table))
            rows = cur.fetchall()
            n = len(rows)
            total += n
            if n:
                log.info("Desactivadas %d vacantes en '%s'", n, table)
            else:
                log.info("Sin vacantes vencidas en '%s'", table)
        except Exception as exc:
            # Table might not exist in all environments
            log.warning("No se pudo procesar '%s': %s", table, exc)

    log.info("Sweep completado — %d vacantes desactivadas en total.", total)


if __name__ == "__main__":
    run_deactivation()
