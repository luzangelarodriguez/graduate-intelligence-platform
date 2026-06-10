#!/usr/bin/env python3
"""
scripts/clean_microcurriculo_skills.py

1. Deduplica microcurriculo_skills por (microcurriculo_id, skill_normalized),
   conservando la fila con mayor confidence_score (o la más reciente).

2. Criminología (especializacion_id=108):
   - Normaliza términos en inglés a su equivalente técnico en español.
   - Agrega skills técnicos del microcurrículo que no están en la tabla.

3. Inteligencia Artificial (especializacion_id=92):
   - Agrega skills técnicos del docx que no están en la tabla.

Uso:
    python scripts/clean_microcurriculo_skills.py          # preview
    python scripts/clean_microcurriculo_skills.py --execute  # aplica cambios
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

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

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def connect():
    url = os.getenv("RAILWAY_DATABASE_URL") or os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url, sslmode="require",
                                cursor_factory=psycopg2.extras.RealDictCursor)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "graduate_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# ---------------------------------------------------------------------------
# Step 1 — Deduplication
# ---------------------------------------------------------------------------

def find_duplicates(cur) -> List[dict]:
    """Return rows that are duplicates (same microcurriculo_id + skill_normalized),
    keeping the row with highest confidence_score (tie-break: lowest id kept)."""
    cur.execute("""
        SELECT
            microcurriculo_id,
            skill_normalized,
            COUNT(*) AS cnt,
            array_agg(id ORDER BY confidence_score DESC, id ASC) AS ids
        FROM microcurriculo_skills
        GROUP BY microcurriculo_id, skill_normalized
        HAVING COUNT(*) > 1
    """)
    return cur.fetchall()


def build_delete_ids(duplicates: List[dict]) -> List[int]:
    """For each duplicate group, keep the first id (highest confidence) and
    return the rest for deletion."""
    to_delete: List[int] = []
    for row in duplicates:
        ids = row["ids"]
        to_delete.extend(ids[1:])  # keep ids[0], delete the rest
    return to_delete


# ---------------------------------------------------------------------------
# Step 2 — Criminología normalisation + enrichment
# ---------------------------------------------------------------------------

# Map: english skill_normalized → correct Spanish skill_normalized
CRIMINOLOGIA_TRANSLATIONS = {
    "victimology":             "victimología",
    "criminal analysis":       "análisis criminal",
    "criminal investigation":  "investigación criminal",
    "criminal profiling":      "perfilación criminal",
    "forensic psychology":     "psicología forense",
    "forensic analysis":       "análisis forense",
    "criminal law":            "derecho penal",
    "crime scene":             "escena del crimen",
    "evidence":                "cadena de custodia",
    "criminology":             "criminología",
}

CRIMINOLOGIA_MISSING_SKILLS = [
    ("psicología forense",        "tecnico"),
    ("análisis forense",          "tecnico"),
    ("peritaje psicológico",      "tecnico"),
    ("victimología forense",      "tecnico"),
    ("psicopatología forense",    "tecnico"),
    ("análisis de testimonio",    "tecnico"),
    ("perfilación criminal",      "tecnico"),
    ("investigación criminal",    "tecnico"),
    ("victimología",              "tecnico"),
    ("derecho penal",             "tecnico"),
    ("criminología",              "tecnico"),
    ("criminalística",            "tecnico"),
    ("cadena de custodia",        "tecnico"),
    ("escena del crimen",         "tecnico"),
    ("análisis criminal",         "tecnico"),
]


# ---------------------------------------------------------------------------
# Step 3 — Inteligencia Artificial enrichment
# ---------------------------------------------------------------------------

IA_MISSING_SKILLS = [
    ("python",                    "herramienta"),
    ("redes neuronales",          "tecnico"),
    ("deep learning",             "tecnico"),
    ("machine learning",          "tecnico"),
    ("scikit-learn",              "herramienta"),
    ("tensorflow",                "herramienta"),
    ("pytorch",                   "herramienta"),
    ("árboles de decisión",       "tecnico"),
    ("clustering",                "tecnico"),
    ("regresión",                 "tecnico"),
    ("random forest",             "tecnico"),
    ("clasificación",             "tecnico"),
    ("aprendizaje supervisado",   "tecnico"),
    ("aprendizaje no supervisado","tecnico"),
    ("procesamiento de lenguaje natural", "tecnico"),
    ("visión por computador",     "tecnico"),
    ("inteligencia artificial",   "tecnico"),
    ("redes neuronales convolucionales", "tecnico"),
    ("transformers",              "herramienta"),
    ("numpy",                     "herramienta"),
    ("pandas",                    "herramienta"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_microcurriculo_ids(cur, especializacion_id: int) -> List[int]:
    cur.execute(
        "SELECT id FROM microcurriculos WHERE specialization_id = %s ORDER BY id",
        (especializacion_id,),
    )
    return [r["id"] for r in cur.fetchall()]


def get_existing_skills(cur, microcurriculo_ids: List[int]) -> set:
    if not microcurriculo_ids:
        return set()
    cur.execute(
        "SELECT skill_normalized FROM microcurriculo_skills "
        "WHERE microcurriculo_id = ANY(%s)",
        (microcurriculo_ids,),
    )
    return {r["skill_normalized"].lower() for r in cur.fetchall()}


def get_english_skills(cur, microcurriculo_ids: List[int]) -> List[dict]:
    if not microcurriculo_ids:
        return []
    english_keys = list(CRIMINOLOGIA_TRANSLATIONS.keys())
    cur.execute(
        "SELECT id, microcurriculo_id, skill_normalized FROM microcurriculo_skills "
        "WHERE microcurriculo_id = ANY(%s) AND lower(skill_normalized) = ANY(%s)",
        (microcurriculo_ids, english_keys),
    )
    return cur.fetchall()


# ---------------------------------------------------------------------------
# Preview helpers
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def preview_duplicates(duplicates: List[dict], to_delete: List[int]) -> None:
    _section("PASO 1 — Duplicados a eliminar")
    if not duplicates:
        print("  ✅ No hay duplicados en microcurriculo_skills.")
        return
    for row in duplicates:
        print(f"  micro_id={row['microcurriculo_id']}  "
              f"skill='{row['skill_normalized']}'  "
              f"count={row['cnt']}  "
              f"ids={row['ids']}  → eliminar {row['ids'][1:]}")
    print(f"\n  Total filas a eliminar: {len(to_delete)}")


def preview_translations(english_rows: List[dict]) -> None:
    _section("PASO 2a — Traducciones Criminología")
    if not english_rows:
        print("  ✅ No hay skills en inglés para traducir.")
        return
    for row in english_rows:
        es = CRIMINOLOGIA_TRANSLATIONS.get(row["skill_normalized"].lower(), "?")
        print(f"  id={row['id']}  '{row['skill_normalized']}' → '{es}'")


def preview_inserts(label: str, skills_to_add: List[Tuple[str, str]]) -> None:
    _section(f"PASO {label} — Skills a insertar")
    if not skills_to_add:
        print("  ✅ Todos los skills ya existen.")
        return
    for skill, tipo in skills_to_add:
        print(f"  + {skill!r:45s}  tipo={tipo}")
    print(f"\n  Total a insertar: {len(skills_to_add)}")


# ---------------------------------------------------------------------------
# Execute helpers
# ---------------------------------------------------------------------------

def execute_delete_duplicates(cur, to_delete: List[int]) -> int:
    if not to_delete:
        return 0
    cur.execute("DELETE FROM microcurriculo_skills WHERE id = ANY(%s)", (to_delete,))
    return len(to_delete)


def execute_translations(cur, english_rows: List[dict]) -> int:
    updated = 0
    for row in english_rows:
        es = CRIMINOLOGIA_TRANSLATIONS.get(row["skill_normalized"].lower())
        if not es:
            continue
        cur.execute(
            "UPDATE microcurriculo_skills "
            "SET skill_normalized = %s, skill_original = skill_normalized "
            "WHERE id = %s",
            (es, row["id"]),
        )
        updated += 1
    return updated


def execute_inserts(
    cur,
    microcurriculo_ids: List[int],
    skills_to_add: List[Tuple[str, str]],
    source_label: str,
) -> int:
    if not microcurriculo_ids or not skills_to_add:
        return 0
    # Insert into the first (latest) microcurriculo for this program
    mc_id = microcurriculo_ids[-1]
    inserted = 0
    for skill, tipo in skills_to_add:
        cur.execute("""
            INSERT INTO microcurriculo_skills
                (microcurriculo_id, skill_original, skill_normalized,
                 tipo_skill, confidence_score, source_document)
            VALUES (%s, %s, %s, %s, 0.90, %s)
            ON CONFLICT (microcurriculo_id, skill_normalized, tipo_skill) DO NOTHING
        """, (mc_id, skill, skill, tipo, source_label))
        if cur.rowcount:
            inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Limpia y enriquece microcurriculo_skills"
    )
    parser.add_argument("--execute", action="store_true",
                        help="Aplicar cambios en DB (sin este flag solo preview)")
    args = parser.parse_args()

    conn = connect()
    try:
        cur = conn.cursor()

        # ------------------------------------------------------------------
        # PASO 1 — Deduplication
        # ------------------------------------------------------------------
        duplicates = find_duplicates(cur)
        to_delete = build_delete_ids(duplicates)
        preview_duplicates(duplicates, to_delete)

        # ------------------------------------------------------------------
        # PASO 2 — Criminología (id=108)
        # ------------------------------------------------------------------
        crimi_mc_ids = get_microcurriculo_ids(cur, 108)
        print(f"\n  Criminología microcurriculo_ids: {crimi_mc_ids}")
        english_rows = get_english_skills(cur, crimi_mc_ids)
        preview_translations(english_rows)

        existing_crimi = get_existing_skills(cur, crimi_mc_ids)
        crimi_to_add = [
            (skill, tipo)
            for skill, tipo in CRIMINOLOGIA_MISSING_SKILLS
            if skill.lower() not in existing_crimi
        ]
        preview_inserts("2b", crimi_to_add)

        # ------------------------------------------------------------------
        # PASO 3 — Inteligencia Artificial (id=92)
        # ------------------------------------------------------------------
        ia_mc_ids = get_microcurriculo_ids(cur, 92)
        print(f"\n  IA microcurriculo_ids: {ia_mc_ids}")
        existing_ia = get_existing_skills(cur, ia_mc_ids)
        ia_to_add = [
            (skill, tipo)
            for skill, tipo in IA_MISSING_SKILLS
            if skill.lower() not in existing_ia
        ]
        preview_inserts("3", ia_to_add)

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        print(f"\n{'='*60}")
        print(f"  RESUMEN")
        print(f"{'='*60}")
        print(f"  Duplicados a eliminar  : {len(to_delete)}")
        print(f"  Traducciones inglés→ES : {len(english_rows)}")
        print(f"  Skills nuevos Crimi    : {len(crimi_to_add)}")
        print(f"  Skills nuevos IA       : {len(ia_to_add)}")

        if not args.execute:
            print("\n  ⚠️  Modo PREVIEW — no se modificó nada.")
            print("  Ejecuta con --execute para aplicar los cambios.")
            return

        # ------------------------------------------------------------------
        # Execute
        # ------------------------------------------------------------------
        print("\n  Aplicando cambios...")

        n_del = execute_delete_duplicates(cur, to_delete)
        print(f"  ✅ Duplicados eliminados: {n_del}")

        n_trans = execute_translations(cur, english_rows)
        print(f"  ✅ Traducciones aplicadas: {n_trans}")

        n_crimi = execute_inserts(cur, crimi_mc_ids, crimi_to_add, "manual_enrichment_criminologia")
        print(f"  ✅ Skills Criminología insertados: {n_crimi}")

        n_ia = execute_inserts(cur, ia_mc_ids, ia_to_add, "manual_enrichment_ia")
        print(f"  ✅ Skills IA insertados: {n_ia}")

        conn.commit()
        print("\n  ✅ Commit exitoso. Cambios aplicados en DB.")

    except Exception as exc:
        conn.rollback()
        print(f"\n  ❌ Error: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
