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
  - Con --dry-run muestra el plan sin tocar la base de datos.

Uso:
    python scripts/run_job_homologation.py
    python scripts/run_job_homologation.py --dry-run
    python scripts/run_job_homologation.py --dry-run --limit 100
    python scripts/run_job_homologation.py --rerun
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env.local")
except ImportError:
    pass

from ml.academic_relevance_engine import connect  # reusa la conexión centralizada

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

# Para cada job en scope, elige el patrón de mayor confianza que matchea su título.
# CTE candidatos → todos los matches; best → el de mayor confianza por job_id.
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
SELECT
    job_id,
    title,
    perfil_id,
    confianza
FROM candidatos
WHERE rn = 1
ORDER BY job_id
"""

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
    limit_clause = f"AND j2.id IN (SELECT id FROM public.jobs WHERE homologacion_estado = ANY(%(estados)s) AND activo = TRUE ORDER BY id LIMIT {limit})" if limit else ""
    limit_clause_sim = f"AND j.id IN (SELECT id FROM public.jobs WHERE homologacion_estado = ANY(%(estados)s) AND activo = TRUE ORDER BY id LIMIT {limit})" if limit else ""

    conn = connect()
    try:
        with conn.cursor() as cur:
            # -- preview siempre visible --
            cur.execute(
                _SIMULATE_SQL.format(limit_clause=limit_clause_sim),
                {"estados": estados},
            )
            rows = cur.fetchall()
            total = len(rows)

            if total == 0:
                logger.info("No hay jobs pendientes que matcheen algún patrón. Nada que hacer.")
                return

            # Resumen por perfil
            from collections import Counter
            perfil_counts: Counter = Counter()
            for r in rows:
                perfil_counts[r["perfil_id"]] += 1

            # Nombres de perfiles
            cur.execute(
                "SELECT id, nombre FROM public.occupational_profiles WHERE id = ANY(%s)",
                (list(perfil_counts.keys()),),
            )
            nombres = {r["id"]: r["nombre"] for r in cur.fetchall()}

            logger.info("── Plan de homologación ─────────────────────────────")
            logger.info("  Jobs a actualizar: %d", total)
            for pid, cnt in sorted(perfil_counts.items(), key=lambda x: -x[1]):
                logger.info("  %-45s  %d jobs", nombres.get(pid, f"id={pid}"), cnt)
            logger.info("─────────────────────────────────────────────────────")

            if dry_run:
                logger.info("DRY-RUN: no se aplicó ningún cambio.")
                return

            # -- UPDATE real --
            cur.execute(
                _UPDATE_SQL.format(limit_clause=limit_clause),
                {"estados": estados},
            )
            updated_ids = [r["id"] for r in cur.fetchall()]
            conn.commit()
            logger.info("✓ %d jobs actualizados a homologacion_estado='auto'.", len(updated_ids))

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
        help="Muestra el plan sin modificar la base de datos.",
    )
    p.add_argument(
        "--rerun",
        action="store_true",
        help="Reprocesa también jobs con estado 'auto' (útil tras agregar nuevos patrones).",
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
