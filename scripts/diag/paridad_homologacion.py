"""
Diagnóstico de paridad: compara process_job_skill_rows antes y después de
la homologación con canonical_key (fix/homologar-antes-de-contar).

Preparación en tu PC (una vez, sin cambiar de rama):
    git show origin/main:api/skills_analysis_logic.py \\
        > scripts/diag/skills_analysis_logic_v0.py

Uso:
    python scripts/diag/paridad_homologacion.py [program_id ...]

    Sin argumentos analiza: 1 9 11 13 20 108 109 146

Seguridad:
  - La URL de BD se pide por getpass; nunca se imprime.
  - conn.set_session(readonly=True) antes de cualquier consulta.

Salida:
  - Consola (tabla compacta por programa).
  - outputs/paridad_homologacion_<timestamp>.csv  (ignorado por git).
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys
from datetime import datetime

# ── Path setup ────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Cargar versión "antes" (copia congelada de origin/main) ──────────────────

V0_PATH = os.path.join(SCRIPT_DIR, "skills_analysis_logic_v0.py")
if not os.path.exists(V0_PATH):
    sys.exit(
        f"\nFalta el archivo de referencia:\n  {V0_PATH}\n\n"
        "Genera el archivo antes de ejecutar este script:\n"
        "  git show origin/main:api/skills_analysis_logic.py "
        "> scripts/diag/skills_analysis_logic_v0.py\n"
    )

spec = importlib.util.spec_from_file_location("skills_analysis_logic_v0", V0_PATH)
_mod_v0 = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(_mod_v0)  # type: ignore[union-attr]
process_job_skill_rows_v0 = _mod_v0.process_job_skill_rows

# ── Importar versión "después" (producción real de esta rama) ─────────────────

from api.skills_analysis_logic import (  # noqa: E402
    cross_analyze,
    frequency_threshold,
    process_job_skill_rows as process_job_skill_rows_v1,
)

# ── SQL: intenta api.market_sample; fallback a outputs/market_sample_copy.py ──

try:
    from api.market_sample import _MARKET_SAMPLE_CTE  # noqa: E402
except ImportError:
    _outputs = os.path.join(ROOT, "outputs")
    sys.path.insert(0, _outputs)
    from market_sample_copy import _MARKET_SAMPLE_CTE  # type: ignore[no-redef]  # noqa: E402

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

# ── Veredicto (mismos umbrales que el frontend) ───────────────────────────────

_AC, _AK, _FC, _FK = 50, 6, 75, 3


def _veredicto(cobertura: float, n_criticas: int) -> str:
    if cobertura < _AC or n_criticas >= _AK:
        return "Actualizar"
    if cobertura < _FC or n_criticas >= _FK:
        return "Fortalecer"
    return "Mantener"


# ── Conexión ──────────────────────────────────────────────────────────────────

def _connect():
    import getpass
    import psycopg2
    import psycopg2.extras

    db_url = getpass.getpass("DATABASE_URL (no se imprime): ").strip()
    conn = psycopg2.connect(db_url)
    conn.set_session(readonly=True)
    return conn


def _fetch(conn, sql: str, params: tuple) -> list[dict]:
    import psycopg2.extras
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


# ── Análisis de un programa ───────────────────────────────────────────────────

def _run_analysis(conn, program_id: int, process_fn) -> dict:
    """Runs market + cross analysis using the given process_job_skill_rows function."""
    raw_rows  = _fetch(conn, _SQL_MARKET_SKILLS, (program_id,))
    prog_rows = _fetch(conn, _SQL_PROG_SKILLS,   (program_id,))

    skills_programa = [
        {"skill": r["skill_name"], "cobertura": int(r["cobertura"]), "asignaturas": []}
        for r in prog_rows if r["skill_name"]
    ]

    rows_for_fn = [{"match_id": r["match_id"], "skill": r["skill"]} for r in raw_rows]
    skills_raw, n_matches = process_fn(rows_for_fn)
    skills_market = [{"skill": s["skill"], "frecuencia": s["frecuencia"]} for s in skills_raw]

    analysis = cross_analyze(skills_market, skills_programa, n_matches)

    return {
        "n_matches":       n_matches,
        "umbral":          frequency_threshold(n_matches),
        "n_habilidades":   len(skills_raw),
        "cobertura_pct":   analysis["cobertura_pct"],
        "n_fortalezas":    len(analysis["fortalezas"]),
        "n_brechas":       len(analysis["brechas"]),
        "n_criticas":      len(analysis["brechas_criticas"]),
        "evidencia_baja":  analysis["evidencia_baja"],
        "veredicto":       _veredicto(
            analysis["cobertura_pct"],
            len(analysis["brechas_criticas"]),
        ),
        "skills":          {s["skill"]: s["frecuencia"] for s in skills_raw},
    }


# ── Comparación ───────────────────────────────────────────────────────────────

def _compare(before: dict, after: dict) -> dict:
    sk_b = before["skills"]
    sk_a = after["skills"]

    changed: list[dict] = []
    for skill in sk_b:
        if skill in sk_a:
            if sk_b[skill] != sk_a[skill]:
                changed.append({"skill": skill, "freq_antes": sk_b[skill], "freq_despues": sk_a[skill]})
        else:
            # Might have been merged under alias destination
            changed.append({"skill": skill, "freq_antes": sk_b[skill], "freq_despues": "desaparece"})

    new_skills: list[str] = [s for s in sk_a if s not in sk_b]

    return {
        "changed":    changed,
        "new_skills": new_skills,
    }


# ── Reporte ───────────────────────────────────────────────────────────────────

_SEP = "─" * 80
_COLS = ["programa", "n_matches", "umbral", "n_hab", "cobertura_%",
         "fortalezas", "brechas", "criticas", "evidencia_baja", "veredicto"]


def _fmt_row(prog_id: int, r: dict) -> list:
    return [
        prog_id,
        r["n_matches"],
        r["umbral"],
        r["n_habilidades"],
        f"{r['cobertura_pct']:.1f}",
        r["n_fortalezas"],
        r["n_brechas"],
        r["n_criticas"],
        r["evidencia_baja"],
        r["veredicto"],
    ]


def _print_comparison(program_id: int, before: dict, after: dict, diff: dict) -> None:
    print(f"\n{_SEP}")
    print(f"  Programa {program_id}")
    print(_SEP)

    header = f"  {'Métrica':<18} {'ANTES':>12} {'DESPUÉS':>12} {'DELTA':>8}"
    print(header)
    print(f"  {'':─<18} {'':─>12} {'':─>12} {'':─>8}")

    metrics = [
        ("n_matches",     "n_matches",   "d"),
        ("umbral",        "umbral",      "d"),
        ("n_habilidades", "n_hab.",      "d"),
        ("cobertura_pct", "cobertura %", "f"),
        ("n_fortalezas",  "fortalezas",  "d"),
        ("n_brechas",     "brechas",     "d"),
        ("n_criticas",    "críticas",    "d"),
    ]

    for key, label, fmt in metrics:
        vb = before[key]
        va = after[key]
        if fmt == "f":
            delta = f"{va - vb:+.1f}" if isinstance(va, (int, float)) else "—"
            vbs, vas = f"{vb:.1f}", f"{va:.1f}"
        else:
            delta = f"{va - vb:+d}" if isinstance(va, int) else "—"
            vbs, vas = str(vb), str(va)
        changed = " ◄" if delta not in ("0", "+0", "+0.0", "—") else ""
        print(f"  {label:<18} {vbs:>12} {vas:>12} {delta:>8}{changed}")

    vb_ev = before["evidencia_baja"]
    va_ev = after["evidencia_baja"]
    ev_delta = " ◄ CAMBIA" if vb_ev != va_ev else ""
    print(f"  {'evidencia_baja':<18} {str(vb_ev):>12} {str(va_ev):>12}{ev_delta}")

    vb_ver = before["veredicto"]
    va_ver = after["veredicto"]
    ver_delta = " ◄ CAMBIA" if vb_ver != va_ver else ""
    print(f"  {'veredicto':<18} {vb_ver:>12} {va_ver:>12}{ver_delta}")

    if diff["changed"]:
        print(f"\n  Habilidades que cambian de frecuencia o desaparecen:")
        for c in diff["changed"]:
            print(f"    {c['skill']}: {c['freq_antes']} → {c['freq_despues']}")

    if diff["new_skills"]:
        print(f"\n  Habilidades nuevas (solo en 'después'):")
        for s in diff["new_skills"]:
            print(f"    + {s} (freq={after['skills'].get(s, '?')})")


# ── Main ──────────────────────────────────────────────────────────────────────

DEFAULT_PROGRAMS = [1, 9, 11, 13, 20, 108, 109, 146]


def main() -> None:
    programs = [int(p) for p in sys.argv[1:]] if sys.argv[1:] else DEFAULT_PROGRAMS

    conn = _connect()
    print(f"\nAnalizando {len(programs)} programas: {programs}")

    results_csv: list[list] = []
    csv_header = ["programa", "version"] + _COLS[1:]

    for prog_id in programs:
        try:
            before = _run_analysis(conn, prog_id, process_job_skill_rows_v0)
            after  = _run_analysis(conn, prog_id, process_job_skill_rows_v1)
            diff   = _compare(before, after)
            _print_comparison(prog_id, before, after, diff)

            results_csv.append(["ANTES"] + _fmt_row(prog_id, before))
            results_csv.append(["DESPUÉS"] + _fmt_row(prog_id, after))

        except Exception as exc:
            print(f"\n  Programa {prog_id}: ERROR — {exc}")

    conn.close()

    # CSV
    out_dir = os.path.join(ROOT, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(out_dir, f"paridad_homologacion_{ts}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["version"] + _COLS)
        w.writerows(results_csv)
    print(f"\n  CSV guardado en: outputs/paridad_homologacion_{ts}.csv\n")


if __name__ == "__main__":
    main()
