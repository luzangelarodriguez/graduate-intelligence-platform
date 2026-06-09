#!/usr/bin/env python3
"""
CLI de alto nivel para ejecutar el motor de pertinencia académica de 3 capas.

Uso rápido:
    python scripts/run_semantic_matching.py
    python scripts/run_semantic_matching.py --min-score 60 --persist-embeddings
    python scripts/run_semantic_matching.py --dry-run --limit-jobs 200 --limit-programs 10
    python scripts/run_semantic_matching.py --program-id 42
    python scripts/run_semantic_matching.py --show-gap --top 30
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env.local")
except ImportError:
    pass

from ml.academic_relevance_engine import (
    PERTINENCE_THRESHOLD,
    MatchResult,
    ProgramProfile,
    JobProfile,
    connect,
    load_jobs,
    load_programs,
    persist_embeddings,
    run_matching,
    save_matches,
    _ensure_run,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_programs(programs: List[ProgramProfile], program_id: Optional[int]) -> List[ProgramProfile]:
    if program_id is None:
        return programs
    filtered = [p for p in programs if p.especializacion_id == program_id]
    if not filtered:
        logger.error("No se encontró programa con especializacion_id=%d", program_id)
        sys.exit(1)
    return filtered


def _print_summary(results: List[MatchResult], *, top: int = 20, show_gap: bool = False) -> None:
    if not results:
        print("\n  (sin matches con el umbral indicado)\n")
        return

    print(f"\n{'='*80}")
    print(f"  MATCHES DE PERTINENCIA ACADÉMICA  —  top {min(top, len(results))} de {len(results)}")
    print(f"{'='*80}")

    by_label = {"high": 0, "medium": 0, "low": 0, "no_match": 0}
    for r in results:
        by_label[r.relevance_label] = by_label.get(r.relevance_label, 0) + 1

    print(f"  Alta: {by_label['high']}  |  Media: {by_label['medium']}  |  Baja: {by_label['low']}\n")

    col_prog = 36
    col_job  = 36
    col_co   = 18
    hdr = (f"{'Programa':<{col_prog}}  {'Empleo':<{col_job}}  {'Empresa':<{col_co}}"
           f"  {'Score':>6}  {'Sem':>5}  {'Pert':>5}  {'Label'}")
    print(hdr)
    print("-" * len(hdr))

    for r in results[:top]:
        print(
            f"{r.program_name[:col_prog]:<{col_prog}}  "
            f"{r.job_title[:col_job]:<{col_job}}  "
            f"{r.company[:col_co]:<{col_co}}  "
            f"{r.final_score:>6.1f}  "
            f"{r.semantic_score:>5.1f}  "
            f"{r.pertinence_score:>5.1f}  "
            f"{r.relevance_label}"
        )

    if show_gap and results:
        best = results[0]
        print(f"\n{'─'*80}")
        print(f"Gap del mejor match ({best.program_name[:50]}):")
        print(f"  Skills microcurrículo no cubiertos por «{best.job_title[:50]}»:")
        for sk in best.gap_skills[:15]:
            print(f"    • {sk}")
        if len(best.gap_skills) > 15:
            print(f"    … y {len(best.gap_skills) - 15} más.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Motor de pertinencia académica — wrapper CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--min-score", type=float, default=PERTINENCE_THRESHOLD,
                   help=f"Score mínimo para incluir un match (default {PERTINENCE_THRESHOLD})")
    p.add_argument("--no-domain-filter", action="store_true",
                   help="Desactivar filtro de dominio obligatorio")
    p.add_argument("--persist-embeddings", action="store_true",
                   help="Guardar vectores en microcurriculo_embeddings / job_embeddings")
    p.add_argument("--dry-run", action="store_true",
                   help="No escribe nada en DB; sólo muestra resultados")
    p.add_argument("--limit-jobs", type=int, default=0,
                   help="Limitar empleos procesados (0 = todos)")
    p.add_argument("--limit-programs", type=int, default=0,
                   help="Limitar programas procesados (0 = todos)")
    p.add_argument("--program-id", type=int, default=None,
                   help="Ejecutar sólo para un especializacion_id concreto")
    p.add_argument("--dataset-version", default="hybrid_v2",
                   help="Etiqueta de versión en ml_training_runs")
    p.add_argument("--report", default="outputs/academic_relevance_report.md",
                   help="Ruta del reporte Markdown de salida")
    p.add_argument("--top", type=int, default=20,
                   help="Mostrar top N matches en consola (default 20)")
    p.add_argument("--show-gap", action="store_true",
                   help="Mostrar gap de skills del mejor match en consola")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Logging DEBUG")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Load data
    logger.info("Conectando a la base de datos...")
    conn = connect()
    try:
        programs = load_programs(conn)
        jobs = load_jobs(conn)
    finally:
        conn.close()

    programs = _filter_programs(programs, args.program_id)
    if args.limit_programs:
        programs = programs[: args.limit_programs]
    if args.limit_jobs:
        jobs = jobs[: args.limit_jobs]

    logger.info("Programas: %d  |  Empleos: %d", len(programs), len(jobs))

    # Run matching
    results = run_matching(
        programs=programs,
        jobs=jobs,
        min_score=args.min_score,
        domain_filter=not args.no_domain_filter,
    )

    # Console output
    _print_summary(results, top=args.top, show_gap=args.show_gap)

    # Persist
    if not args.dry_run:
        if results:
            conn2 = connect()
            try:
                if args.persist_embeddings:
                    persist_embeddings(programs, jobs, conn2)
                run_id = _ensure_run(conn2, args.dataset_version)
                saved = save_matches(results, run_id, conn2)
                logger.info("Guardados %d matches en run_id=%d", saved, run_id)
            finally:
                conn2.close()
        else:
            logger.info("Sin matches que guardar.")
    else:
        logger.info("[dry-run] No se escribió nada en DB.")

    # Markdown report via engine's main() without re-running matching
    # (write directly since results are already computed)
    from datetime import date

    report_path = ROOT_DIR / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)

    from ml.academic_relevance_engine import SEMANTIC_WEIGHT, PERTINENCE_WEIGHT, EMBED_MODEL_NAME

    counts = {lbl: sum(1 for r in results if r.relevance_label == lbl)
              for lbl in ("high", "medium", "low", "no_match")}

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Reporte Motor de Pertinencia Académica\n")
        f.write(f"**Fecha:** {date.today()}  |  **Versión:** {args.dataset_version}\n\n")
        f.write(f"## Configuración\n")
        f.write(f"- Modelo semántico: `{EMBED_MODEL_NAME}` (CPU, fallback TF-IDF)\n")
        f.write(f"- BM25: `rank-bm25` (fallback Python nativo)\n")
        f.write(f"- Pesos: semántico×{SEMANTIC_WEIGHT} + pertinencia×{PERTINENCE_WEIGHT}\n")
        f.write(f"- Umbral mínimo: {args.min_score}%\n")
        f.write(f"- Filtro de dominio: {'sí' if not args.no_domain_filter else 'no'}\n")
        f.write(f"- Dry-run: {'sí' if args.dry_run else 'no'}\n\n")
        f.write(f"## Resumen\n")
        f.write(f"- Programas procesados: {len(programs)}\n")
        f.write(f"- Empleos procesados: {len(jobs)}\n")
        f.write(f"- Matches totales: {len(results)}\n")
        for lbl, cnt in counts.items():
            f.write(f"  - `{lbl}`: {cnt}\n")
        f.write(f"\n## Top 30 matches\n")
        f.write("| # | Programa | Empleo | Empresa | Score | Semántico | BM25 | Cobertura | Pertinencia | Label |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(results[:30], 1):
            f.write(
                f"| {i} | {r.program_name[:35]} | {r.job_title[:35]} | {r.company[:20]} "
                f"| **{r.final_score:.1f}** | {r.semantic_score:.1f} | {r.bm25_score:.1f} "
                f"| {r.coverage_score:.1f}% | {r.pertinence_score:.1f}% | `{r.relevance_label}` |\n"
            )

        if results:
            f.write(f"\n## Análisis de gap — mejor match\n")
            best = results[0]
            f.write(f"**Programa:** {best.program_name}  \n")
            f.write(f"**Empleo:** {best.job_title} @ {best.company}  \n")
            f.write(f"**Score:** {best.final_score:.1f}  \n\n")
            f.write(f"```\n{best.explanation}\n```\n\n")
            if best.gap_skills:
                f.write(f"**Skills del microcurrículo no cubiertos** ({len(best.gap_skills)}):\n")
                for sk in best.gap_skills:
                    f.write(f"- {sk}\n")

        # Program coverage summary
        if results:
            f.write(f"\n## Cobertura por programa\n")
            f.write("| Programa | ID | Matches high | Matches medium | Mejor score |\n")
            f.write("|---|---|---|---|---|\n")
            from collections import defaultdict
            prog_data: dict = defaultdict(lambda: {"high": 0, "medium": 0, "best": 0.0})
            for r in results:
                d = prog_data[r.especializacion_id]
                d["name"] = r.program_name
                if r.relevance_label == "high":
                    d["high"] += 1
                elif r.relevance_label == "medium":
                    d["medium"] += 1
                if r.final_score > d["best"]:
                    d["best"] = r.final_score
            for pid, d in sorted(prog_data.items(), key=lambda x: -x[1]["best"]):
                f.write(f"| {d['name'][:40]} | {pid} | {d['high']} | {d['medium']} | {d['best']:.1f} |\n")

    logger.info("Reporte guardado: %s", report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
