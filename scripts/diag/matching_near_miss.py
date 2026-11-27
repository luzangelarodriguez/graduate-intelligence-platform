"""
Diagnóstico de posibles falsos negativos en el cruce de skills mercado ↔ programa.

Para cada programa analizado imprime:
  1. Nº de skills del programa + muestra de las 30 primeras por cobertura.
  2. Para las 25 brechas con mayor frecuencia de mercado:
       brecha · frecuencia · 3 skills del programa más similares · similitud
       "POSIBLE FALSO NEGATIVO" si similitud >= 0.5
  3. Resumen: % de las 25 brechas con posible falso negativo +
     estimación de idioma (proporción skills ES en programa vs skills EN en mercado).

Similitud entre dos skills = max(
    difflib.SequenceMatcher sobre canonical_key normalizadas,
    Jaccard de tokens sin stopwords (ES + EN) tras strip de acentos
)

Uso:
    DATABASE_URL=postgres://user:pass@host/db python scripts/diag/matching_near_miss.py
    # o sin variable → pide la URL completa por getpass (nunca se imprime)
"""
from __future__ import annotations

import difflib
import getpass
import os
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 no encontrado.  Instala con:  pip install psycopg2-binary")
    sys.exit(1)

from api.market_sample import _MARKET_SAMPLE_CTE
from api.microcurriculo_filters import SQL_FILTRO_NO_PRUEBA, SQL_FILTRO_NO_PRUEBA_PARAMS
from api.skills_analysis_logic import (
    canonical_key,
    cross_analyze,
    process_job_skill_rows,
)

# ── Programas ──────────────────────────────────────────────────────────────────
PROGRAM_IDS = [13, 9, 109, 1, 11]

# ── Umbral de posible falso negativo ──────────────────────────────────────────
NEAR_MISS_THRESHOLD: float = 0.5

# ── Stopwords gramaticales (artículos, preposiciones, conjunciones)  ──────────
# Solo palabras vacías gramaticales para el filtro Jaccard.
# NO incluir términos de dominio (datos, analisis, tools…): quitarlos haría
# que skills como "análisis de datos" y "data analysis" perdieran tokens útiles.
_GRAMMAR_ES: frozenset[str] = frozenset({
    "de", "en", "y", "el", "la", "los", "las", "un", "una", "con",
    "para", "por", "del", "al", "se", "que", "a", "o", "e",
})
_GRAMMAR_EN: frozenset[str] = frozenset({
    "of", "in", "and", "the", "a", "an", "with", "for", "to", "by",
})
# Stopwords para Jaccard: solo gramáticas de ambos idiomas
_ALL_STOPWORDS: frozenset[str] = _GRAMMAR_ES | _GRAMMAR_EN

# ── Marcadores de idioma (para estimación ES vs EN) ───────────────────────────
# Se usan sobre tokens SIN filtrar (incluye gramáticas y dominio).
_STOPWORDS_ES: frozenset[str] = frozenset({
    "de", "en", "y", "el", "la", "los", "las", "un", "una", "con",
    "para", "por", "del", "al", "se", "que", "a", "o", "e",
})
_STOPWORDS_EN: frozenset[str] = frozenset({
    "of", "in", "and", "the", "a", "an", "with", "for", "to", "by",
})


# ── SQL (copiados literalmente de producción) ──────────────────────────────────
_SQL_MARKET_SKILLS = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT ms.match_id,
           ms.empleo_id,
           jsonb_array_elements_text(ms.skills_empleo) AS skill
    FROM market_sample ms
    WHERE ms.especializacion_id = %s
      AND ms.skills_empleo IS NOT NULL
      AND jsonb_typeof(ms.skills_empleo) = 'array'
      AND ms.skills_empleo != '[]'::jsonb
"""

_SQL_PROG_SKILLS = f"""
    SELECT COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*) AS cobertura,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT m.asignatura), NULL) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
      {SQL_FILTRO_NO_PRUEBA}
    GROUP BY COALESCE(ms.skill_normalized, ms.skill_original)
    ORDER BY cobertura DESC
"""


# ── Helpers internos ───────────────────────────────────────────────────────────

def _strip_accents(s: str) -> str:
    n = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


def _tokens(s: str) -> set[str]:
    """Tokens sin stopwords tras strip de acentos."""
    return {t for t in _strip_accents(s).split() if t not in _ALL_STOPWORDS and len(t) > 1}


# ── Función pura de similitud ─────────────────────────────────────────────────

def skill_similarity(a: str, b: str) -> float:
    """
    Similitud entre dos skills.

    = max(
        difflib.SequenceMatcher ratio sobre canonical_key(a) vs canonical_key(b),
        índice de Jaccard sobre tokens sin stopwords (ES+EN gramaticales) tras strip acentos
      )

    Nota: SequenceMatcher no es simétrico en Python (el orden de las cadenas
    afecta la detección de bloques). Se toman AMBAS direcciones y se usa el max.

    Rango [0.0, 1.0].  Función pura sin efectos secundarios.
    """
    ca = canonical_key(a)
    cb = canonical_key(b)

    # difflib sobre claves canónicas — se calcula en ambas direcciones (no es simétrico)
    ratio = max(
        difflib.SequenceMatcher(None, ca, cb).ratio(),
        difflib.SequenceMatcher(None, cb, ca).ratio(),
    )

    # Jaccard sobre tokens sin stopwords gramaticales
    ta = _tokens(ca)
    tb = _tokens(cb)
    if ta or tb:
        intersection = len(ta & tb)
        union = len(ta | tb)
        jaccard = intersection / union if union > 0 else 0.0
    else:
        jaccard = 0.0

    return round(max(ratio, jaccard), 4)


# ── Conexión ──────────────────────────────────────────────────────────────────

def _connect() -> "psycopg2.extensions.connection":
    db_url = os.environ.get("DATABASE_URL") or getpass.getpass(
        "DATABASE_URL (postgres://user:pass@host/db): "
    )
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _fetch_all(cur, sql: str, params: tuple) -> list[dict]:
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


# ── Construcción de skills_programa (igual que producción + fix cobertura) ────

def _build_prog_skills(cur, program_id: int) -> list[dict]:
    rows = _fetch_all(cur, _SQL_PROG_SKILLS, (program_id,) + SQL_FILTRO_NO_PRUEBA_PARAMS)
    result = []
    for r in rows:
        if not r["skill_name"]:
            continue
        asigs = list(r["asignaturas"]) if r["asignaturas"] else []
        raw_count = int(r["cobertura"])
        cobertura = len(asigs) if asigs else (1 if raw_count > 0 else 0)
        result.append({
            "skill":       r["skill_name"],
            "asignaturas": asigs,
            "cobertura":   cobertura,
        })
    return result


# ── Estimación de idioma ──────────────────────────────────────────────────────

def _raw_tokens(s: str) -> set[str]:
    """Tokens sin filtrar (incluye stopwords gramaticales), solo strip acentos."""
    return set(_strip_accents(s).split())


def _lang_estimate(prog_skills: list[dict], market_skills: list[dict]) -> dict:
    """
    Proporción de skills del programa con al menos una palabra marcadora española
    vs proporción de skills de mercado con al menos una palabra marcadora inglesa.

    Usa tokens SIN filtrar (incluye preposiciones/artículos) para detectar idioma.
    """
    if prog_skills:
        prog_es = sum(
            1 for s in prog_skills
            if _raw_tokens(s["skill"]) & _STOPWORDS_ES
        ) / len(prog_skills)
    else:
        prog_es = 0.0

    if market_skills:
        mkt_en = sum(
            1 for s in market_skills
            if _raw_tokens(s["skill"]) & _STOPWORDS_EN
        ) / len(market_skills)
    else:
        mkt_en = 0.0

    return {"pct_prog_es": round(prog_es * 100, 1), "pct_mkt_en": round(mkt_en * 100, 1)}


# ── Análisis por programa ─────────────────────────────────────────────────────

def _analyze_program(cur, prog_id: int) -> None:
    rows = _fetch_all(cur, _SQL_MARKET_SKILLS, (prog_id,))
    prog_skills = _build_prog_skills(cur, prog_id)

    market_skills, n_matches = process_job_skill_rows(rows, min_freq=2, hard_cap=None)
    cross = cross_analyze(market_skills, prog_skills, n_matches)

    brechas = sorted(cross["brechas"], key=lambda x: -x["frecuencia_mercado"])
    top_brechas = brechas[:25]

    print(f"\n{'=' * 70}")
    print(f"PROGRAMA {prog_id}  —  {len(prog_skills)} skills en microcurrículos  "
          f"| {len(market_skills)} skills mercado (min_freq=2)  "
          f"| {n_matches} vacantes")
    print(f"  Fortalezas: {len(cross['fortalezas'])}  "
          f"Brechas: {len(cross['brechas'])}  "
          f"Cobertura: {cross['cobertura_pct']}%")
    print(f"{'=' * 70}")

    # ── 1. Muestra de skills del programa ─────────────────────────────────────
    print(f"\n--- Skills del programa (top 30 por cobertura) ---")
    for i, s in enumerate(prog_skills[:30], 1):
        print(f"  {i:>3}. [{s['cobertura']:>2}] {s['skill']}")

    # ── 2. Near-miss para top-25 brechas ─────────────────────────────────────
    print(f"\n--- Top-25 brechas de mercado vs skills del programa ---")
    near_miss_count = 0

    for brecha in top_brechas:
        b_skill = brecha["skill"]
        b_freq  = brecha["frecuencia_mercado"]

        # calcula similitud contra todas las skills del programa
        scored = [
            (skill_similarity(b_skill, p["skill"]), p["skill"])
            for p in prog_skills
        ]
        scored.sort(key=lambda x: -x[0])
        top3 = scored[:3]

        max_sim = top3[0][0] if top3 else 0.0
        flag = "  *** POSIBLE FALSO NEGATIVO ***" if max_sim >= NEAR_MISS_THRESHOLD else ""
        if max_sim >= NEAR_MISS_THRESHOLD:
            near_miss_count += 1

        print(f"\n  Brecha: {b_skill!r:40s}  freq={b_freq}{flag}")
        for sim, ps in top3:
            bar = "█" * int(sim * 20)
            print(f"    sim={sim:.3f} |{bar:<20}| prog: {ps!r}")

    # ── 3. Resumen ────────────────────────────────────────────────────────────
    lang = _lang_estimate(prog_skills, market_skills)
    pct_near_miss = round(near_miss_count / len(top_brechas) * 100, 1) if top_brechas else 0.0

    print(f"\n--- Resumen programa {prog_id} ---")
    print(f"  Posibles falsos negativos (sim >= {NEAR_MISS_THRESHOLD}): "
          f"{near_miss_count}/{len(top_brechas)} = {pct_near_miss}%")
    print(f"  Idioma estimado — skills programa con stopwords ES: {lang['pct_prog_es']}%")
    print(f"  Idioma estimado — skills mercado con stopwords EN:  {lang['pct_mkt_en']}%")
    if lang["pct_prog_es"] >= 40 and lang["pct_mkt_en"] >= 40:
        print("  ⚠ Mezcla de idiomas: el programa tiene skills en ES y el mercado en EN.")
        print("    Considerar ampliar TEXT_SYNONYMS o normalizar el idioma en la ingesta.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("Near-miss matching — graduate-intelligence-platform")
    print("=" * 70)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            for prog_id in PROGRAM_IDS:
                _analyze_program(cur, prog_id)
    finally:
        conn.close()
    print("\nFin del diagnóstico.")


if __name__ == "__main__":
    main()
