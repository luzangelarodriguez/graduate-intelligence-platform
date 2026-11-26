"""
Diagnóstico de cobertura curricular real para un programa.

Uso:
    python scripts/diag/cobertura_real.py [program_id]

Por defecto analiza el programa 13.

Seguridad:
  - La URL de la base de datos se pide por getpass; nunca se imprime.
  - SET default_transaction_read_only = on se ejecuta antes de cualquier consulta.

Salida:
  - Pantalla (stdout).
  - outputs/cobertura_real_<program_id>.csv  (ignorado por git).
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import defaultdict

# ── Importaciones de producción ──────────────────────────────────────────────

# Añadir raíz del proyecto al path para importar módulos de producción
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from api.market_sample import _MARKET_SAMPLE_CTE
from api.skills_analysis_logic import (
    frequency_threshold,
    is_transversal,
    norm,
    process_job_skill_rows,
)
from crawlers.storage.postgres_warehouse import canonicalize_skill

# ── SQL (reutiliza las mismas queries de producción) ─────────────────────────

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

_SQL_MARKET_SIZE = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT COUNT(DISTINCT ms.empleo_id)::int AS n_vacantes_muestra
    FROM market_sample ms
    WHERE ms.especializacion_id = %s
"""

_SQL_PROG_SKILLS = """
    SELECT COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*) AS cobertura,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT m.asignatura), NULL) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
    GROUP BY COALESCE(ms.skill_normalized, ms.skill_original)
    ORDER BY cobertura DESC
"""

# ── Conexión ─────────────────────────────────────────────────────────────────

def _connect():
    import getpass
    import psycopg2
    import psycopg2.extras

    db_url = getpass.getpass("DATABASE_URL (no se imprime): ").strip()
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SET default_transaction_read_only = on")
    return conn


def fetch_all(conn, sql: str, params: tuple) -> list[dict]:
    import psycopg2.extras
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


# ── Helpers de agrupación ────────────────────────────────────────────────────

_CARGO_PREFIJOS = {
    "analista", "gerente", "ingeniero", "ingeniera", "especialista",
    "coordinador", "coordinadora", "director", "directora", "asesor", "asesora",
}


def _tokens(skill: str) -> frozenset[str]:
    return frozenset(re.split(r"[\s\-_/]+", norm(skill)) - {""})


def _es_cargo(skill: str) -> bool:
    tokens = _tokens(skill)
    return bool(tokens & _CARGO_PREFIJOS)


def _agrupar_casi_duplicados(skills_freq: list[dict]) -> list[list[dict]]:
    """
    Agrupa habilidades que comparten al menos 2 tokens (o comparten raíz de 5+ chars).
    Retorna lista de grupos con >1 miembro.
    """
    n = len(skills_freq)
    padre = list(range(n))

    def find(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            padre[px] = py

    tok_list = [_tokens(s["skill"]) for s in skills_freq]
    for i in range(n):
        for j in range(i + 1, n):
            shared = tok_list[i] & tok_list[j]
            # Criterio: ≥2 tokens en común, o 1 token en común de ≥5 letras
            long_shared = {t for t in shared if len(t) >= 5}
            if len(shared) >= 2 or long_shared:
                union(i, j)

    grupos: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        grupos[find(i)].append(i)

    return [
        [skills_freq[i] for i in idxs]
        for idxs in grupos.values()
        if len(idxs) > 1
    ]


# ── Análisis principal ───────────────────────────────────────────────────────

def analizar(program_id: int, conn) -> None:
    print(f"\n{'='*70}")
    print(f"  DIAGNÓSTICO DE COBERTURA — Programa {program_id}")
    print(f"{'='*70}\n")

    # ── Datos crudos ─────────────────────────────────────────────────────────
    raw_market = fetch_all(conn, _SQL_MARKET_SKILLS, (program_id,))
    size_rows  = fetch_all(conn, _SQL_MARKET_SIZE,   (program_id,))
    prog_rows  = fetch_all(conn, _SQL_PROG_SKILLS,   (program_id,))

    n_vacantes_muestra = int(size_rows[0]["n_vacantes_muestra"]) if size_rows else 0

    # Procesar habilidades de mercado (igual que producción)
    skills_mercado_raw, n_matches = process_job_skill_rows(
        [{"match_id": r["match_id"], "skill": r["skill"]} for r in raw_market]
    )

    threshold = frequency_threshold(n_matches)

    skills_programa = [
        {
            "skill":     r["skill_name"],
            "cobertura": int(r["cobertura"]),
        }
        for r in prog_rows
        if r["skill_name"]
    ]

    # ── (a) Resumen de tamaños ───────────────────────────────────────────────
    print("── (a) VACANTES Y UMBRAL ──────────────────────────────────────────")
    print(f"  Vacantes en la muestra (sin filtro skills): {n_vacantes_muestra}")
    print(f"  Vacantes con habilidades (n_matches):       {n_matches}")
    print(f"  Umbral de frecuencia (≥{threshold}):        {threshold}")
    print()

    # ── (b) Tamaños de universo ──────────────────────────────────────────────
    all_skills = skills_mercado_raw  # todas las que salieron de process_job_skill_rows
    # (ya sin ruido, con subsunción)
    total_distintas = len(all_skills)
    sobre_umbral = [s for s in all_skills if s["frecuencia"] >= threshold]
    con_freq_2   = [s for s in all_skills if s["frecuencia"] >= 2]

    print("── (b) TAMAÑOS DE UNIVERSO ────────────────────────────────────────")
    print(f"  Habilidades distintas (post-subsunción):    {total_distintas}")
    print(f"  Con frecuencia >= umbral ({threshold}):     {len(sobre_umbral)}")
    print(f"  Con frecuencia >= 2:                        {len(con_freq_2)}")
    print()

    # ── (c) Tres métricas de cobertura ───────────────────────────────────────
    from api.skills_analysis_logic import cross_analyze, find_prog_match

    # (i) Métrica actual: >= umbral, sin transversales
    skills_mercado_std = [{"skill": s["skill"], "frecuencia": s["frecuencia"]} for s in sobre_umbral]
    analysis_std = cross_analyze(skills_mercado_std, skills_programa, n_matches)
    cob_actual = analysis_std["cobertura_pct"]

    # (ii) Todas con freq >= 2, sin transversales, sin ponderar
    no_trans_2 = [s for s in con_freq_2 if not is_transversal(s["skill"])]
    cubiertas_2 = [s for s in no_trans_2 if find_prog_match(s["skill"], skills_programa).rule != "ninguna"]
    cob_bin = round(len(cubiertas_2) / len(no_trans_2) * 100, 1) if no_trans_2 else 0.0

    # (iii) Ponderada por frecuencia
    sum_total = sum(s["frecuencia"] for s in no_trans_2)
    sum_cub   = sum(s["frecuencia"] for s in cubiertas_2)
    cob_pond  = round(sum_cub / sum_total * 100, 1) if sum_total else 0.0

    print("── (c) TRES MÉTRICAS DE COBERTURA ────────────────────────────────")
    print(f"  (i)  Actual (>= umbral {threshold}, sin transversales):    {cob_actual}%")
    print(f"       Universo: {len(no_trans_2 if False else skills_mercado_std)} habilidades "
          f"→ {len(analysis_std['fortalezas'])} cubiertas / "
          f"{len(analysis_std['brechas'])} brechas")
    print(f"  (ii) Binaria (freq >= 2, sin transversales):                {cob_bin}%")
    print(f"       Universo: {len(no_trans_2)} habilidades "
          f"→ {len(cubiertas_2)} cubiertas")
    print(f"  (iii) Ponderada por frecuencia (mismo universo que ii):     {cob_pond}%")
    print(f"       Suma freq cubierta {sum_cub} / total {sum_total}")
    print()

    # ── (d) Tabla de habilidades con freq >= 2 ───────────────────────────────
    print("── (d) TABLA: HABILIDADES CON FRECUENCIA >= 2 ────────────────────")
    headers = ["Habilidad", "Freq", "Categoría", "Transversal", "Cubierta", "Match en programa"]
    rows_tabla: list[list] = []

    for s in sorted(con_freq_2, key=lambda x: -x["frecuencia"]):
        skill      = s["skill"]
        freq       = s["frecuencia"]
        cat        = canonicalize_skill(skill).category
        trans      = "Sí" if is_transversal(skill) else "No"
        match_det  = find_prog_match(skill, skills_programa)
        cubierta   = "No" if match_det.rule == "ninguna" else "Sí"
        prog_match = match_det.prog_skill if match_det.prog_skill else "—"
        rows_tabla.append([skill, freq, cat, trans, cubierta, prog_match])

    col_w = [max(len(str(r[i])) for r in rows_tabla + [headers]) for i in range(len(headers))]
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in col_w)
    print(fmt.format(*headers))
    print("  " + "  ".join("-" * w for w in col_w))
    for row in rows_tabla:
        print(fmt.format(*[str(c) for c in row]))
    print()

    # ── (e) Grupos de casi duplicados y cargos ───────────────────────────────
    print("── (e) GRUPOS DE CASI DUPLICADOS (freq >= 2) ─────────────────────")
    grupos = _agrupar_casi_duplicados(con_freq_2)

    # Mapa match_id → skills para contar unión
    job_skills: dict[str, set[str]] = defaultdict(set)
    for r in raw_market:
        job_skills[str(r["match_id"])].add(norm(r["skill"] or ""))

    if not grupos:
        print("  (ningún grupo detectado)")
    for g in sorted(grupos, key=lambda g: -sum(s["frecuencia"] for s in g)):
        names = [s["skill"] for s in g]
        # Unión de match_ids para las skills del grupo
        norm_names = {norm(n) for n in names}
        union_ids = {
            mid for mid, skills in job_skills.items()
            if skills & norm_names
        }
        cargos = [n for n in names if _es_cargo(n)]
        print(f"  Grupo ({len(names)} habilidades, {len(union_ids)} vacantes unión):")
        for s in g:
            cargo_tag = " [CARGO]" if _es_cargo(s["skill"]) else ""
            print(f"    - {s['skill']} (freq={s['frecuencia']}){cargo_tag}")
        if cargos:
            print(f"    ^ formas de cargo: {', '.join(cargos)}")
    print()

    # ── (f) Token-matching para no cubiertas top 30 ──────────────────────────
    print("── (f) TOKEN MATCH PARA NO CUBIERTAS (top 30 por freq) ──────────")
    brechas_top30 = sorted(
        [s for s in con_freq_2 if not is_transversal(s["skill"])
         and find_prog_match(s["skill"], skills_programa).rule == "ninguna"],
        key=lambda x: -x["frecuencia"],
    )[:30]

    if not brechas_top30:
        print("  (sin brechas en top 30)")
    for s in brechas_top30:
        toks = _tokens(s["skill"])
        matches_tok = [
            p["skill"] for p in skills_programa
            if _tokens(p["skill"]) & toks
        ]
        prog_str = ", ".join(matches_tok) if matches_tok else "—"
        print(f"  {s['skill']} (freq={s['frecuencia']}) → {prog_str}")
    print()

    # ── CSV a outputs/ ───────────────────────────────────────────────────────
    out_dir = os.path.join(_ROOT, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, f"cobertura_real_{program_id}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows_tabla)
    print(f"  CSV guardado en: outputs/cobertura_real_{program_id}.csv")
    print()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    program_id = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    conn = _connect()
    try:
        analizar(program_id, conn)
    finally:
        conn.close()
