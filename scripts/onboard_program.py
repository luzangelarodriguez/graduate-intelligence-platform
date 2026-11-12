#!/usr/bin/env python3
"""
scripts/onboard_program.py

Flujo único de onboarding para un nuevo programa académico:
  1. Carga microcurrículo del .docx (--preview, nunca --execute sin aprobación)
  2. Lanza adquisición de empleos para el dominio indicado
  3. Ejecuta matching local entre el programa y los empleos capturados
  4. Genera reporte final: ID del programa, empleos por fuente, matches, relevancia

Usage:
    python scripts/onboard_program.py --program-id 115 --domain marketing_commercial [--dry-run] [--limit 20]

Flags:
    --program-id   ID de especialización en DB (obligatorio para matching)
    --domain       Dominio de ml/academic_relevance_engine (obligatorio)
    --dry-run      No escribe nada en DB (default: True — siempre dry-run hasta aprobación)
    --limit        Máx de empleos a scrapenar por query (default: 10)
    --source       Scraper a usar (default: computrabajo; también: elempleo, magneto, simo_cnsc)
    --preview-only Solo muestra el preview del microcurrículo sin correr adquisición
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("onboard_program")


# ---------------------------------------------------------------------------
# Step 1: microcurrículo preview
# ---------------------------------------------------------------------------

def step_microcurriculo_preview(program_id: int | None) -> dict:
    """Run load_microcurriculos --preview in-process and return parsed records."""
    from scripts.load_microcurriculos import discover_all, infer_domain, _normalize_text

    log.info("[1/4] Parsing microcurrículos from storage/test_microcurriculos/")
    records = discover_all()
    if not records:
        log.warning("  No records found. Check that the .docx is in storage/test_microcurriculos/")
        return {"records": [], "program_name": "", "domain_key": ""}

    # Group by programa
    by_prog: dict[str, list] = {}
    for r in records:
        by_prog.setdefault(r["programa"], []).append(r)

    log.info("  Parsed %d asignaturas across %d programas:", len(records), len(by_prog))
    for prog, recs in sorted(by_prog.items()):
        total_skills = sum(sum(len(v) for v in r["skills"].values()) for r in recs)
        log.info("    📚 %s — %d asignaturas, %d skills, domain=%s",
                 prog, len(recs), total_skills, recs[0]["domain_key"])
        for r in recs:
            n_ra = len(r["resultados_aprendizaje"])
            n_sk = sum(len(v) for v in r["skills"].values())
            log.info("       + %s  RA=%d  skills=%d", r["asignatura"], n_ra, n_sk)

    # Return all records; caller picks the right programa by domain
    return {"records": records, "programs": by_prog}


# ---------------------------------------------------------------------------
# Step 2: acquisition
# ---------------------------------------------------------------------------

def step_acquisition(domain: str, sources: list[str], limit: int, dry_run: bool) -> list[dict]:
    """Run acquisition for the given domain using one or more scrapers."""
    from scripts.run_acquisition import FALLBACK_QUERIES

    queries = FALLBACK_QUERIES.get(domain, ["marketing digital", "analista de marketing"])[:3]
    log.info("[2/4] Acquisition — domain=%s, sources=%s, queries=%s, dry_run=%s",
             domain, sources, queries, dry_run)

    all_jobs: list[dict] = []
    for source_name in sources:
        log.info("  Loading scraper: %s", source_name)
        try:
            mod = importlib.import_module(f"scrapers.sources.{source_name}_scraper")
            scrape_fn = getattr(mod, "scrape_jobs")
        except Exception as exc:
            log.warning("  Could not load scraper %s: %s", source_name, exc)
            continue

        for query in queries:
            log.info("  → %s query=%r", source_name, query)
            try:
                jobs = scrape_fn(query=query, location="Colombia", limit=limit, headless=True)
                log.info("    scraped %d jobs", len(jobs))
                for job in jobs:
                    job["_source"] = source_name
                all_jobs.extend(jobs)
            except Exception as exc:
                log.warning("  scraper %s failed for query %r: %s", source_name, query, exc)

    log.info("  Total jobs scraped: %d", len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# Step 3: local matching
# ---------------------------------------------------------------------------

def step_matching(program_id: int, jobs: list[dict], dry_run: bool) -> list[dict]:
    """
    Run the academic relevance engine to match jobs to the program.
    If DB is unavailable (no credentials), falls back to keyword matching.
    """
    log.info("[3/4] Matching — program_id=%d, jobs=%d, dry_run=%s", program_id, len(jobs), dry_run)

    if not jobs:
        log.warning("  No jobs to match.")
        return []

    # Try full engine matching (requires DB)
    try:
        from ml.academic_relevance_engine import connect, build_program_profiles, match_jobs_to_programs
        conn = connect()
        profiles = build_program_profiles(conn, [program_id])
        if not profiles:
            log.warning("  No program profile found for id=%d in DB", program_id)
            conn.close()
            return []
        job_records = []
        for job in jobs:
            job_records.append({
                "id": None,
                "title": job.get("titulo") or job.get("title") or "",
                "company": job.get("empresa") or job.get("company") or "",
                "description": job.get("descripcion") or job.get("description") or "",
                "skills": job.get("skills") or [],
            })
        matches = match_jobs_to_programs(profiles, job_records, domain_filter=False)
        conn.close()
        log.info("  Engine returned %d matches", len(matches))
        return matches
    except Exception as exc:
        log.warning("  Full engine matching failed (%s) — using keyword fallback", exc)

    # Keyword fallback (no DB needed)
    from ml.academic_relevance_engine import _DOMAIN_BUCKETS, _normalize
    domain_kws = set(_DOMAIN_BUCKETS.get("marketing_commercial", []))
    matches = []
    for job in jobs:
        text = _normalize(" ".join(filter(None, [
            job.get("titulo", ""), job.get("descripcion", ""), job.get("requisitos", "")
        ])))
        hits = sum(1 for kw in domain_kws if kw in text)
        if hits >= 1:
            matches.append({
                "job_title": job.get("titulo") or "",
                "company": job.get("empresa") or "",
                "source": job.get("_source", ""),
                "keyword_hits": hits,
                "relevance_label": "medium" if hits >= 3 else "low",
            })
    log.info("  Keyword fallback: %d matches", len(matches))
    return matches


# ---------------------------------------------------------------------------
# Step 4: report
# ---------------------------------------------------------------------------

def step_report(
    program_id: int,
    domain: str,
    records: list[dict],
    jobs: list[dict],
    matches: list[dict],
) -> None:
    log.info("[4/4] Report")
    print()
    print("=" * 70)
    print(f"  ONBOARDING REPORT — program_id={program_id}  domain={domain}")
    print("=" * 70)

    # Microcurriculum summary
    print(f"\n  Microcurrículo: {len(records)} asignaturas parsed")
    if records:
        progs = {r["programa"] for r in records}
        for p in sorted(progs):
            asigs = [r for r in records if r["programa"] == p]
            print(f"    📚 {p}")
            print(f"       {len(asigs)} asignaturas, domain_key={asigs[0]['domain_key']}")

    # Jobs by source
    by_source: dict[str, int] = {}
    for job in jobs:
        src = job.get("_source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
    print(f"\n  Empleos captados: {len(jobs)}")
    for src, count in sorted(by_source.items()):
        print(f"    {src}: {count}")

    # Matches
    high = [m for m in matches if m.get("relevance_label") in ("high", "medium")]
    print(f"\n  Matches relevantes (high+medium): {len(high)} de {len(matches)}")
    for m in sorted(high, key=lambda x: x.get("keyword_hits", 0), reverse=True)[:10]:
        print(f"    [{m.get('relevance_label','?').upper()}] {m.get('job_title','')} @ {m.get('company','')} ({m.get('source','')})")

    print()
    print("  PRÓXIMOS PASOS:")
    print("  1. Si microcurrículo se ve correcto → python scripts/load_microcurriculos.py --execute")
    print("  2. Para ejecutar adquisición real → quitar --dry-run")
    print("  3. Para agregar al frontend → ver PROGRAMS en ObservatorioStorytelling.tsx")
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Onboarding de un programa académico")
    ap.add_argument("--program-id", type=int, required=True, help="ID en tabla especializaciones")
    ap.add_argument("--domain", required=True, help="Dominio (ej: marketing_commercial)")
    ap.add_argument("--dry-run", action="store_true", default=True, help="No escribe en DB (default: True)")
    ap.add_argument("--limit", type=int, default=10, help="Máx empleos por query (default: 10)")
    ap.add_argument("--source", default="computrabajo,elempleo,simo_cnsc",
                    help="Scrapers separados por coma (default: computrabajo,elempleo,simo_cnsc)")
    ap.add_argument("--preview-only", action="store_true",
                    help="Solo muestra el preview del microcurrículo, sin adquisición")
    args = ap.parse_args()

    sources = [s.strip() for s in args.source.split(",") if s.strip()]

    # Step 1
    result = step_microcurriculo_preview(args.program_id)
    records = result.get("records", [])

    if args.preview_only:
        log.info("--preview-only: stopping after microcurrículo preview.")
        return

    # Step 2
    jobs = step_acquisition(args.domain, sources, args.limit, args.dry_run)

    # Step 3
    matches = step_matching(args.program_id, jobs, args.dry_run)

    # Step 4
    step_report(args.program_id, args.domain, records, jobs, matches)


if __name__ == "__main__":
    main()
