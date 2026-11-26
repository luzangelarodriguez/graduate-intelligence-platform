"""Elimina filas de prueba/sandbox de la tabla microcurriculos y sus dependencias.

MODO POR DEFECTO: DRY-RUN (solo muestra qué borraría, sin modificar nada).
Para ejecutar el borrado real: pasar --apply.

Uso:
    # Dry-run (seguro, solo lectura):
    DATABASE_URL=postgres://... python scripts/maintenance/borrar_filas_prueba.py

    # Borrado real (irreversible sin el respaldo):
    DATABASE_URL=postgres://... python scripts/maintenance/borrar_filas_prueba.py --apply

    Si DATABASE_URL no está en el entorno, se pide por getpass (nunca se imprime).

GARANTÍAS DE SEGURIDAD:
  - Aborta si los ids detectados no son exactamente {1..10, 21}.
  - En modo --apply:
      1. Guarda un respaldo JSON completo en un directorio temporal del SO
         (tempfile.mkdtemp()) ANTES de cualquier modificación.
      2. Realiza TODOS los borrados en una única transacción; en caso de error
         hace rollback automático y el respaldo queda intacto.
  - En modo dry-run no abre transacción de escritura.

ADVERTENCIA: Esta operación es IRREVERSIBLE sin el respaldo generado.
Revisa el dry-run y confirma los ids antes de usar --apply.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
import psycopg2.extras

from api.microcurriculo_filters import es_fila_de_prueba

# ── Ids esperados (diagnóstico confirmado 2026-11-26) ─────────────────────────
_IDS_ESPERADOS: frozenset[int] = frozenset(range(1, 11)) | {21}  # {1..10, 21}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch(cur, sql: str, params: tuple = ()) -> list[dict]:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _discover_fk_tables(cur) -> list[dict]:
    """Descubre tablas con FK hacia microcurriculos usando information_schema."""
    rows = _fetch(
        cur,
        """
        SELECT
            tc.table_name        AS child_table,
            kcu.column_name      AS fk_column,
            rc.delete_rule       AS on_delete
        FROM information_schema.table_constraints  tc
        JOIN information_schema.key_column_usage    kcu
          ON kcu.constraint_name = tc.constraint_name
         AND kcu.table_schema    = tc.table_schema
        JOIN information_schema.referential_constraints rc
          ON rc.constraint_name  = tc.constraint_name
         AND rc.constraint_schema = tc.table_schema
        JOIN information_schema.key_column_usage    ccu
          ON ccu.constraint_name = rc.unique_constraint_name
         AND ccu.table_schema    = rc.unique_constraint_schema
        WHERE tc.constraint_type   = 'FOREIGN KEY'
          AND ccu.table_name       = 'microcurriculos'
          AND ccu.column_name      = 'id'
          AND tc.table_schema      = 'public'
        ORDER BY tc.table_name
        """,
    )
    return rows


def _count_child_rows(cur, child_table: str, fk_col: str, ids: list[int]) -> int:
    if not ids:
        return 0
    cur.execute(
        f"SELECT COUNT(*) AS n FROM public.{child_table} WHERE {fk_col} = ANY(%s)",
        (ids,),
    )
    return int(cur.fetchone()[0])


def _backup_data(cur, test_ids: list[int], backup_dir: str) -> str:
    """Guarda respaldo JSON con todas las filas y sus skills en backup_dir."""
    micro_rows = _fetch(
        cur,
        "SELECT * FROM microcurriculos WHERE id = ANY(%s) ORDER BY id",
        (test_ids,),
    )
    skills_rows = _fetch(
        cur,
        "SELECT * FROM microcurriculo_skills WHERE microcurriculo_id = ANY(%s) ORDER BY microcurriculo_id, id",
        (test_ids,),
    )
    # Serializar; convierte tipos no-JSON (datetime, Decimal, etc.)
    def _default(o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        return str(o)

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ids": test_ids,
        "microcurriculos": micro_rows,
        "microcurriculo_skills": skills_rows,
    }
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = os.path.join(backup_dir, f"borrar_filas_prueba_backup_{ts}.json")
    with open(backup_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_default)
    return backup_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Ejecutar el borrado real (por defecto: dry-run)")
    args = parser.parse_args()

    dry_run = not args.apply
    mode_label = "DRY-RUN" if dry_run else "APPLY — BORRADO REAL"
    print(f"\n{'='*60}")
    print(f"  MODO: {mode_label}")
    print(f"{'='*60}\n")

    db_url = os.environ.get("DATABASE_URL") or getpass.getpass("DATABASE_URL: ")
    conn = psycopg2.connect(db_url)
    if dry_run:
        conn.set_session(readonly=True, autocommit=True)

    with conn.cursor() as cur:
        # 1. Detectar filas de prueba
        all_micro = _fetch(
            cur,
            "SELECT id, specialization_id, asignatura, source_document FROM microcurriculos ORDER BY id",
        )
        test_rows = [r for r in all_micro if es_fila_de_prueba(r["source_document"], r["asignatura"])]
        test_ids  = sorted(r["id"] for r in test_rows)

        print(f"Filas de prueba detectadas: {len(test_rows)}  ids={test_ids}\n")

        # 2. Listar detalle por fila
        for r in test_rows:
            print(f"  id={r['id']} | programa={r['specialization_id']} | "
                  f"asignatura={r['asignatura']!r} | source_document={r['source_document']!r}")

        # 3. Verificar que son exactamente los ids esperados
        detected_set = set(test_ids)
        if detected_set != _IDS_ESPERADOS:
            only_detected = detected_set - _IDS_ESPERADOS
            only_expected = _IDS_ESPERADOS - detected_set
            print(
                f"\n  ABORT: los ids detectados no coinciden con los esperados.\n"
                f"    Esperados : {sorted(_IDS_ESPERADOS)}\n"
                f"    Detectados: {test_ids}\n"
                f"    Solo en detectados : {sorted(only_detected)}\n"
                f"    Solo en esperados  : {sorted(only_expected)}\n"
                "  Revisa el diagnóstico antes de continuar."
            )
            conn.close()
            sys.exit(1)

        print(f"\n  ✓ Ids coinciden con los esperados: {sorted(_IDS_ESPERADOS)}")

        # 4. Descubrir tablas hijo con FK
        fk_tables = _discover_fk_tables(cur)
        print(f"\nTablas con FK → microcurriculos ({len(fk_tables)}):")
        child_counts: dict[str, int] = {}
        for fk in fk_tables:
            n = _count_child_rows(cur, fk["child_table"], fk["fk_column"], test_ids)
            child_counts[fk["child_table"]] = n
            print(f"  {fk['child_table']}.{fk['fk_column']}  "
                  f"ON DELETE {fk['on_delete']}  → {n} filas afectadas")

        # 5. microcurriculo_skills específicamente
        n_skills = _count_child_rows(cur, "microcurriculo_skills", "microcurriculo_id", test_ids)
        print(f"\nmicrocurriculo_skills afectadas: {n_skills}")

        if dry_run:
            print("\n[DRY-RUN] Ningún cambio realizado. Usa --apply para borrar.")
            conn.close()
            return

        # ── MODO APPLY ────────────────────────────────────────────────────────

        # 6. Respaldo JSON en directorio temporal del SO
        backup_dir = tempfile.mkdtemp(prefix="gip_borrar_prueba_")
        print(f"\nGuardando respaldo en: {backup_dir}")
        backup_path = _backup_data(cur, test_ids, backup_dir)
        print(f"  Respaldo: {backup_path}")

        # 7. Borrado en una sola transacción
        # Cerrar la sesión read-only y abrir una nueva con escritura
        conn.close()
        conn = psycopg2.connect(db_url)
        conn.autocommit = False

        try:
            with conn.cursor() as wcur:
                # Borrar en orden: hijos primero (las que no tienen CASCADE)
                for fk in fk_tables:
                    if fk["on_delete"] != "CASCADE":
                        wcur.execute(
                            f"DELETE FROM public.{fk['child_table']} "
                            f"WHERE {fk['fk_column']} = ANY(%s)",
                            (test_ids,),
                        )
                        print(f"  Borradas {wcur.rowcount} filas de {fk['child_table']}")

                # Borrar microcurriculos (CASCADE borrará el resto automáticamente)
                wcur.execute(
                    "DELETE FROM microcurriculos WHERE id = ANY(%s)",
                    (test_ids,),
                )
                print(f"  Borradas {wcur.rowcount} filas de microcurriculos")

            conn.commit()
            print("\n  ✓ Transacción confirmada. Filas de prueba eliminadas.")

        except Exception as exc:
            conn.rollback()
            print(f"\n  ERROR: {exc}")
            print(f"  Rollback realizado. Respaldo disponible en: {backup_path}")
            conn.close()
            sys.exit(1)

    conn.close()
    print("\nScript completado.")


if __name__ == "__main__":
    main()
