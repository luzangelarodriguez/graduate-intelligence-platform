from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
SCRAPER_PATH = BASE_DIR / "ticjob_scraper.py"


def load_scraper_module():
    spec = importlib.util.spec_from_file_location("ticjob_scraper", SCRAPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load scraper module from {SCRAPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load_scraper_module()


SKILL_PREFIX_RE = r"^(?:analista|analistas|desarrollador|desarrolladora|ingeniero|ingeniera|especialista|consultor|consultora|arquitecto|arquitecta|coordinador|coordinadora|gestor|gestora|profesional|tecnico|tecnica|tecnologo|tecnologa|senior|jr|junior|sr|lead|lider|líder)\s+"
SKILL_PHRASE_RE = r"^(?:a fines de|a fines|centrado en|centrada en|enfocado en|enfocada en|orientado a|orientada a|manejo de|conocimiento en|experiencia en|dominio de|desarrollo de|habilidades en)\s+"


def split_candidates(raw: str) -> list[str]:
    text = m.normalize_text(raw)
    if not text:
        return []
    text = text.strip(" .,:;|-")
    text = m.re.sub(SKILL_PREFIX_RE, "", text)
    text = m.re.sub(SKILL_PHRASE_RE, "", text)
    text = text.strip(" .,:;|-")

    candidates = [text]
    if any(sep in text for sep in (" / ", " & ", " + ", " - ")):
        candidates.extend(
            part.strip(" .,:;|-")
            for part in m.re.split(r"\s*(?:/|&|\+|-)\s*", text)
            if part.strip(" .,:;|-")
        )

    out: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip(" .,:;|-")
        if not candidate:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        out.append(candidate)
    return out


def clean_skill_label(raw: str) -> str:
    candidates = split_candidates(raw)
    if not candidates:
        return ""

    polished: list[str] = []
    for candidate in candidates:
        canonical = m.canonicalize_skill_name(candidate)
        if canonical:
            polished.append(canonical)
            continue
        if candidate and m.has_technical_signal(candidate):
            polished.append(candidate)

    if not polished:
        return m.normalize_text(raw)

    best = max(
        polished,
        key=lambda value: (
            len(m.normalize_text(value).split()),
            len(m.normalize_text(value)),
        ),
    )
    return m.normalize_text(best)


def relation_tables(cur) -> dict[str, str]:
    cur.execute(
        """
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema = 'public'
          AND c.column_name = 'skill_id'
          AND c.table_name <> 'skills'
          AND t.table_type = 'BASE TABLE'
        ORDER BY table_name, ordinal_position
        """
    )
    tables: dict[str, str] = {}
    for table_name, _ in cur.fetchall():
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        cols = [row[0] for row in cur.fetchall()]
        if len(cols) >= 2 and "skill_id" in cols:
            other_cols = [c for c in cols if c != "skill_id"]
            if other_cols:
                tables[table_name] = other_cols[0]
    return tables


def merge_skill_relations(cur, relation_map: dict[str, str], old_id: int, new_id: int) -> None:
    if old_id == new_id:
        return
    for table_name, other_col in relation_map.items():
        cur.execute(
            f"""
            DELETE FROM {table_name} old_rows
            USING {table_name} new_rows
            WHERE old_rows.skill_id = %s
              AND new_rows.skill_id = %s
              AND old_rows.{other_col} = new_rows.{other_col}
            """,
            (old_id, new_id),
        )
        cur.execute(
            f"UPDATE {table_name} SET skill_id = %s WHERE skill_id = %s",
            (new_id, old_id),
        )


def main() -> None:
    conn = m.connect_postgres("127.0.0.1", 5433, "cliente_a_db", "postgres", "")
    conn.autocommit = False

    try:
        with conn:
            with conn.cursor() as cur:
                relation_map = relation_tables(cur)
                cur.execute("SELECT id, nombre, categoria FROM skills ORDER BY id")
                rows = cur.fetchall()

                existing_by_name: dict[str, int] = {
                    m.normalize_text(nombre): int(skill_id)
                    for skill_id, nombre, _categoria in rows
                    if m.normalize_text(nombre)
                }
                updates = 0
                merges = 0

                for skill_id, nombre, categoria in rows:
                    cleaned_name = clean_skill_label(nombre)
                    if not cleaned_name:
                        continue
                    cleaned_categoria = m.infer_skill_category(cleaned_name)
                    existing_id = existing_by_name.get(cleaned_name)

                    if existing_id and existing_id != skill_id:
                        merge_skill_relations(cur, relation_map, skill_id, existing_id)
                        cur.execute("DELETE FROM skills WHERE id = %s", (skill_id,))
                        merges += 1
                        continue

                    if existing_id == skill_id and m.normalize_text(nombre) == cleaned_name and categoria == cleaned_categoria:
                        continue

                    cur.execute(
                        "UPDATE skills SET nombre = %s, categoria = %s WHERE id = %s",
                        (cleaned_name, cleaned_categoria, skill_id),
                    )
                    updates += 1
                    existing_by_name[cleaned_name] = skill_id

        print(
            {
                "status": "ok",
                "updated": updates,
                "merged": merges,
                "relation_tables": sorted(relation_map.keys()),
            }
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
