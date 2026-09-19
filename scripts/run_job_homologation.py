#!/usr/bin/env python3
"""
Motor de homologación ocupacional — Fase B.

Aplica los patrones ILIKE de job_profile_mappings sobre jobs.title y actualiza:
  - jobs.perfil_id              → FK al perfil ganador (mayor confianza)
  - jobs.homologacion_estado    → 'auto'
  - jobs.homologacion_confianza → confianza del patrón que matcheó

Comportamiento:
  - Solo procesa jobs con homologacion_estado = 'pending' (idempotente por defecto).
  - Si un job matchea múltiples patrones, gana el de mayor confianza.
  - Jobs sin match quedan en 'pending' sin modificación.
  - Con --rerun también reprocesa jobs ya en estado 'auto'.
  - Con --dry-run muestra el plan sin tocar la base de datos ni pedir confirmación.

Uso:
    python scripts/run_job_homologation.py --dry-run
    python scripts/run_job_homologation.py
    python scripts/run_job_homologation.py --rerun
    python scripts/run_job_homologation.py --dry-run --limit 100
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env.local")
except ImportError:
    pass

import psycopg2
import psycopg2.extras
from backend.database_config import get_connection_parameters

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conexión (psycopg2 directo, sin cargar el motor de embeddings)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

# Simula el mejor match por job: mayor confianza, desempate por jpm.id menor.
_SIMULATE_SQL = """
WITH candidatos AS (
    SELECT
        j.id                  AS job_id,
        j.title,
        jpm.perfil_id,
        jpm.confianza,
        ROW_NUMBER() OVER (
            PARTITION BY j.id
            ORDER BY jpm.confianza DESC, jpm.id ASC
        ) AS rn
    FROM public.jobs j
    JOIN public.job_profile_mappings jpm
        ON j.title ILIKE jpm.patron
       AND jpm.activo = TRUE
    JOIN public.occupational_profiles op
        ON op.id = jpm.perfil_id
       AND op.activo = TRUE
    WHERE j.homologacion_estado = ANY(%(estados)s)
      AND j.activo = TRUE
      {limit_clause}
)
SELECT job_id, title, perfil_id, confianza
FROM candidatos
WHERE rn = 1
ORDER BY job_id
"""

# Backup de solo las filas que serán modificadas.
_BACKUP_SQL = """
CREATE TABLE IF NOT EXISTS public.{backup_table} AS
SELECT * FROM public.jobs WHERE id = ANY(%(ids)s)
"""

# UPDATE real: DISTINCT ON garantiza un solo registro por job_id.
_UPDATE_SQL = """
UPDATE public.jobs AS j
SET
    perfil_id              = best.perfil_id,
    homologacion_estado    = 'auto',
    homologacion_confianza = best.confianza,
    updated_at             = now()
FROM (
    SELECT DISTINCT ON (j2.id)
        j2.id         AS job_id,
        jpm.perfil_id,
        jpm.confianza
    FROM public.jobs j2
    JOIN public.job_profile_mappings jpm
        ON j2.title ILIKE jpm.patron
       AND jpm.activo = TRUE
    JOIN public.occupational_profiles op
        ON op.id = jpm.perfil_id
       AND op.activo = TRUE
    WHERE j2.homologacion_estado = ANY(%(estados)s)
      AND j2.activo = TRUE
      {limit_clause}
    ORDER BY j2.id, jpm.confianza DESC, jpm.id ASC
) AS best
WHERE j.id = best.job_id
RETURNING j.id
"""


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def run(*, dry_run: bool, rerun: bool, limit: int | None) -> None:
    estados = ["pending", "auto"] if rerun else ["pending"]
    limit_subquery = (
        f"AND j.id IN ("
        f"  SELECT id FROM public.jobs"
        f"  WHERE homologacion_estado = ANY(%(estados)s) AND activo = TRUE"
        f"  ORDER BY id LIMIT {limit}"
        f")"
        if limit else ""
    )
    limit_subquery_upd = limit_subquery.replace("j.id IN", "j2.id IN", 1) if limit else ""

    conn = _connect()
    try:
        with conn.cursor() as cur:
            # ── 1. Simulación (siempre, incluido dry-run) ──────────────────
            cur.execute(
                _SIMULATE_SQL.format(limit_clause=limit_subquery),
                {"estados": estados},
            )
            rows = cur.fetchall()
            total = len(rows)

            if total == 0:
                logger.info("No hay jobs pendientes que matcheen algún patrón. Nada que hacer.")
                return

            job_ids = [r["job_id"] for r in rows]

            # Resumen por perfil
            from collections import Counter
            perfil_counts: Counter = Counter(r["perfil_id"] for r in rows)

            cur.execute(
                "SELECT id, nombre FROM public.occupational_profiles WHERE id = ANY(%s)",
                (list(perfil_counts.keys()),),
            )
            nombres = {r["id"]: r["nombre"] for r in cur.fetchall()}

            logger.info("── Plan de homologación ─────────────────────────────")
            logger.info("  Jobs a actualizar : %d", total)
            for pid, cnt in sorted(perfil_counts.items(), key=lambda x: -x[1]):
                logger.info("  %-45s  %d jobs", nombres.get(pid, f"id={pid}"), cnt)
            logger.info("─────────────────────────────────────────────────────")

            if dry_run:
                logger.info("DRY-RUN activo — no se aplica ningún cambio ni se pide confirmación.")
                return

            # ── 2. Confirmación interactiva ────────────────────────────────
            respuesta = input(
                f"\n¿Confirmas actualizar {total} jobs en producción? "
                "Escribe 'si' para continuar: "
            ).strip().lower()
            if respuesta != "si":
                logger.info("Operación cancelada por el usuario.")
                conn.rollback()
                return

            # ── 3. Backup de filas afectadas ───────────────────────────────
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_table = f"backup_homologacion_{fecha}"
            cur.execute(
                _BACKUP_SQL.format(backup_table=backup_table),
                {"ids": job_ids},
            )
            logger.info("Backup creado: public.%s (%d filas)", backup_table, total)

            # ── 4. UPDATE real ─────────────────────────────────────────────
            cur.execute(
                _UPDATE_SQL.format(limit_clause=limit_subquery_upd),
                {"estados": estados},
            )
            updated_ids = [r["id"] for r in cur.fetchall()]
            conn.commit()
            logger.info(
                "✓ %d jobs actualizados a homologacion_estado='auto'. "
                "Backup en public.%s",
                len(updated_ids),
                backup_table,
            )

    except Exception:
        conn.rollback()
        logger.exception("Error durante la homologación — rollback aplicado.")
        sys.exit(1)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Motor de homologación ocupacional (Fase B).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el plan sin modificar la base de datos ni pedir confirmación.",
    )
    p.add_argument(
        "--rerun",
        action="store_true",
        help="Reprocesa también jobs con estado 'auto' (útil tras ampliar el catálogo).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Procesa solo los primeros N jobs (para pruebas).",
    )
    return p


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    args = _build_parser().parse_args()
    run(dry_run=args.dry_run, rerun=args.rerun, limit=args.limit)


if __name__ == "__main__":
    main()
