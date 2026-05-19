from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parent
UNIR_DB = BASE_DIR / "unir_especializaciones.db"
DEFAULT_OUTPUT_JSON = BASE_DIR / "unir_market_jobs.json"
DEFAULT_OUTPUT_CSV = BASE_DIR / "unir_market_jobs.csv"
DEFAULT_SKILLS_CSV = BASE_DIR / "unir_market_skills.csv"
DEFAULT_PROGRAMS_CSV = BASE_DIR / "unir_market_programs.csv"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from extract_job_offers_and_skills import (  # noqa: E402
    collect_jobs,
    extract_job_skills,
    normalize_text,
    repair_text,
    write_csv,
)
from ticjob_deep_bi_scraper import scrape_jobs as scrape_ticjob_jobs  # noqa: E402


def unique(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        candidate = repair_text(value).strip()
        if not candidate:
            continue
        key = normalize_text(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def infer_area(name: str, skills: Sequence[str]) -> str:
    text = normalize_text(" ".join([name, " ".join(skills)]))
    if any(term in text for term in ("inteligencia artificial", "machine learning", "data science", "ciencia de datos")):
        return "Tecnologia"
    if any(term in text for term in ("software", "programacion", "arquitectura", "testing", "apis", "git")):
        return "Tecnologia"
    if any(term in text for term in ("visual analytics", "big data", "inteligencia de negocio", "business intelligence", "analitica", "datos")):
        return "Datos y BI"
    if any(term in text for term in ("marketing", "ecommerce", "comercio electronico", "digital", "seo", "sem")):
        return "Negocios y Marketing"
    if any(term in text for term in ("pedagog", "docencia", "educacion", "ensenanza", "enseñanza")):
        return "Educacion"
    if any(term in text for term in ("salud", "sst", "seguridad y salud")):
        return "Salud"
    if any(term in text for term in ("derecho", "jurid", "legal", "compliance")):
        return "Derecho"
    if any(term in text for term in ("financ", "contabilidad", "auditor")):
        return "Finanzas"
    if any(term in text for term in ("talento humano", "gestion humana", "liderazgo", "planeacion")):
        return "Gestion Humana y Liderazgo"
    return "Gestion"


def load_unir_programs(db_path: Path = UNIR_DB) -> List[Dict[str, Any]]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT name, skills_json, source_url, scraped_at FROM programs ORDER BY name").fetchall()
    finally:
        conn.close()

    programs: List[Dict[str, Any]] = []
    for name, skills_json, source_url, scraped_at in rows:
        try:
            skills = json.loads(skills_json or "[]")
        except json.JSONDecodeError:
            skills = []
        cleaned = unique([repair_text(skill).strip() for skill in skills])
        programs.append(
            {
                "name": repair_text(name).strip(),
                "area": infer_area(name, cleaned),
                "skills": cleaned,
                "skill_count": len(cleaned),
                "source_url": repair_text(source_url).strip(),
                "scraped_at": repair_text(scraped_at).strip(),
            }
        )
    return programs


def build_program_keywords(program: Dict[str, Any]) -> List[str]:
    tokens = [program.get("name", "")] + list(program.get("skills", []) or [])
    return unique(tokens)


def build_portal_specs() -> List[Dict[str, Any]]:
    return [
        {
            "type": "portal",
            "name": "Elempleo Colombia",
            "kind": "elempleo",
            "url": "https://www.elempleo.com/co/ofertas-empleo",
            "render_mode": "auto",
            "max_pages": 12,
            "aggressive": True,
        },
        {
            "type": "portal",
            "name": "Elempleo Bogota",
            "kind": "elempleo",
            "url": "https://www.elempleo.com/co/ofertas-empleo/bogota",
            "render_mode": "auto",
            "max_pages": 12,
            "aggressive": True,
        },
        {
            "type": "portal",
            "name": "Elempleo Medellin",
            "kind": "elempleo",
            "url": "https://www.elempleo.com/co/ofertas-empleo/medellin",
            "render_mode": "auto",
            "max_pages": 12,
            "aggressive": True,
        },
        {
            "type": "portal",
            "name": "Computrabajo Colombia",
            "kind": "computrabajo",
            "url": "https://co.computrabajo.com/trabajo-de-colombia",
            "render_mode": "auto",
            "max_pages": 12,
            "aggressive": True,
        },
        {
            "type": "portal",
            "name": "Computrabajo Bogota",
            "kind": "computrabajo",
            "url": "https://co.computrabajo.com/trabajo-de-bogota",
            "render_mode": "auto",
            "max_pages": 12,
            "aggressive": True,
        },
        {
            "type": "portal",
            "name": "Computrabajo Medellin",
            "kind": "computrabajo",
            "url": "https://co.computrabajo.com/trabajo-de-medellin",
            "render_mode": "auto",
            "max_pages": 12,
            "aggressive": True,
        },
    ]


def load_cached_portal_jobs() -> List[Dict[str, Any]]:
    candidates = [
        BASE_DIR / "job_extraction_output_public_aggressive" / "jobs.csv",
        BASE_DIR / "job_extraction_output_public" / "jobs.csv",
    ]
    rows: List[Dict[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                source_text = repair_text(row.get("source") or "")
                source_norm = normalize_text(source_text)
                if "computrabajo" not in source_norm and "elempleo" not in source_norm:
                    continue
                rows.append(
                    {
                        "job_id": row.get("job_id", ""),
                        "job_title": row.get("job_title", ""),
                        "company": row.get("company", ""),
                        "description": row.get("description", ""),
                        "location": row.get("location", ""),
                        "date": row.get("date", ""),
                        "source": source_text,
                    }
                )
    return rows


def infer_source_kind(source_name: str) -> str:
    text = normalize_text(source_name)
    if "ticjob" in text:
        return "ticjob"
    if "computrabajo" in text:
        return "computrabajo"
    if "elempleo" in text:
        return "elempleo"
    return "portal"


def ticjob_job_id(job: Dict[str, Any]) -> str:
    payload = "|".join(
        [
            repair_text(job.get("job_url") or "").strip(),
            repair_text(job.get("job_title") or "").strip(),
            repair_text(job.get("company") or "").strip(),
            repair_text(job.get("location") or "").strip(),
        ]
    )
    return hashlib.sha1(normalize_text(payload).encode("utf-8")).hexdigest()[:20]


def normalize_job_text(job: Dict[str, Any]) -> str:
    pieces = [
        job.get("job_title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("description", ""),
        job.get("stack", ""),
        " ".join(job.get("skills", []) or []),
        " ".join(job.get("signals", []) or []),
    ]
    return normalize_text(" ".join(pieces))


def score_job_against_program(job: Dict[str, Any], program: Dict[str, Any]) -> Dict[str, Any]:
    job_text = normalize_job_text(job)
    job_skill_norms = {normalize_text(skill) for skill in job.get("skills", []) or [] if normalize_text(skill)}
    program_skills = list(program.get("skills", []) or [])
    program_keywords = build_program_keywords(program)

    matched: List[str] = []
    for skill in program_skills:
        key = normalize_text(skill)
        if not key:
            continue
        if key in job_skill_norms or key in job_text:
            matched.append(skill)

    keyword_hits = sum(1 for keyword in program_keywords if normalize_text(keyword) in job_text)
    total = len(program_skills) or max(1, len(program_keywords))
    base_score = round((len(matched) / total) * 100) if total else 0
    bonus = min(15, keyword_hits * 3)
    score = min(100, base_score + bonus)

    missing = [skill for skill in program_skills if normalize_text(skill) not in {normalize_text(item) for item in matched}]
    return {
        "program": program.get("name", ""),
        "area": program.get("area", ""),
        "score": score,
        "matched": unique(matched),
        "missing": unique(missing),
        "keyword_hits": keyword_hits,
        "total_skills": len(program_skills),
    }


def enrich_job(job: Dict[str, Any], source_kind: str, source_name: str) -> Dict[str, Any]:
    record = dict(job)
    record["source_kind"] = source_kind
    record["source"] = repair_text(record.get("source") or source_name).strip() or source_name
    if not record.get("job_id"):
        record["job_id"] = ticjob_job_id(record) if source_kind == "ticjob" else hashlib.sha1(
            normalize_text(
                "|".join(
                    [
                        record.get("job_title", ""),
                        record.get("company", ""),
                        record.get("location", ""),
                        record.get("date", ""),
                        source_name,
                    ]
                )
            ).encode("utf-8")
        ).hexdigest()[:20]

    if source_kind == "ticjob" and not record.get("job_title"):
        record["job_title"] = repair_text(record.get("search_title") or "").strip()

    skills_detail = extract_job_skills(
        {
            "job_id": record["job_id"],
            "job_title": record.get("job_title", ""),
            "description": record.get("description", ""),
        }
    )
    record["skills_detail"] = skills_detail
    record["skills"] = unique([item.get("skill_name", "") for item in skills_detail])
    record["skill_count"] = len(record["skills"])
    return record


def merge_job(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for field in ("job_title", "company", "description", "location", "date", "source", "stack", "signals"):
        current = repair_text(merged.get(field) or "").strip()
        candidate = repair_text(incoming.get(field) or "").strip()
        if not current and candidate:
            merged[field] = candidate
        elif field == "description" and len(candidate) > len(current):
            merged[field] = candidate

    for field in ("source_kind", "job_url"):
        if not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]

    merged_sources = unique((merged.get("sources") or []) + [incoming.get("source", "")])
    if merged_sources:
        merged["sources"] = merged_sources

    merged_skills = unique((merged.get("skills") or []) + (incoming.get("skills") or []))
    merged["skills"] = merged_skills
    merged["skill_count"] = len(merged_skills)
    return merged


def collect_market_jobs(
    ticjob_pages: int,
    timeout: int,
    min_date: str,
    min_other_score: int,
) -> Dict[str, Any]:
    programs = load_unir_programs()
    if not programs:
        raise RuntimeError("No UNIR programs were found in unir_especializaciones.db")

    # Keep the portal crawler less strict so the market coverage is broader.
    import extract_job_offers_and_skills as portal  # noqa: WPS433

    portal.MIN_JOB_DATE = date.fromisoformat(min_date)

    ticjob_jobs_raw, ticjob_metrics = scrape_ticjob_jobs(max_pages=ticjob_pages, timeout=timeout)
    ticjob_jobs = [enrich_job(job, "ticjob", "TICJOB") for job in ticjob_jobs_raw]

    portal_specs = build_portal_specs()
    portal_jobs_raw, portal_errors, source_counts, portal_stats = collect_jobs(portal_specs, BASE_DIR)
    cached_portal_jobs = load_cached_portal_jobs()
    if cached_portal_jobs:
        portal_jobs_raw.extend(cached_portal_jobs)
    portal_jobs = [
        enrich_job(
            job,
            infer_source_kind(repair_text(job.get("source") or "Portal")),
            repair_text(job.get("source") or "Portal"),
        )
        for job in portal_jobs_raw
    ]

    combined: Dict[str, Dict[str, Any]] = {}
    kept_by_source = Counter()
    source_kind_counts = Counter()

    def include(job: Dict[str, Any], source_kind: str) -> bool:
        matches = [score_job_against_program(job, program) for program in programs]
        matches.sort(key=lambda item: (-item["score"], item["program"]))
        best = matches[0] if matches else {"score": 0, "matched": [], "missing": [], "program": "", "area": ""}
        job["program_matches"] = matches[:3]
        job["best_program"] = best["program"]
        job["best_program_area"] = best["area"]
        job["best_score"] = int(best["score"])
        job["matched_skills"] = best["matched"]
        job["missing_skills"] = best["missing"]
        job["relevance_reason"] = "ticjob_all" if source_kind == "ticjob" else "market_overlap"
        if source_kind == "ticjob":
            return True
        return int(best["score"]) >= min_other_score or len(best["matched"]) >= 2

    for job in ticjob_jobs:
        if not include(job, "ticjob"):
            continue
        key = normalize_text("|".join([job.get("job_title", ""), job.get("company", ""), job.get("location", "")]))
        source_kind_counts["ticjob"] += 1
        kept_by_source[job.get("source", "TICJOB")] += 1
        combined[key] = job

    for job in portal_jobs:
        source_kind = job.get("source_kind") or "portal"
        if not include(job, source_kind):
            continue
        key = normalize_text("|".join([job.get("job_title", ""), job.get("company", ""), job.get("location", "")]))
        source_kind_counts[source_kind] += 1
        kept_by_source[job.get("source", source_kind)] += 1
        if key in combined:
            combined[key] = merge_job(combined[key], job)
        else:
            combined[key] = job

    jobs = sorted(
        combined.values(),
        key=lambda item: (
            -int(item.get("best_score", 0)),
            normalize_text(item.get("job_title", "")),
            normalize_text(item.get("company", "")),
        ),
    )

    job_skills: List[Dict[str, Any]] = []
    for job in jobs:
        for skill in job.get("skills_detail", []) or []:
            job_skills.append(
                {
                    "job_id": job["job_id"],
                    "job_title": job.get("job_title", ""),
                    "skill_name": skill.get("skill_name", ""),
                    "confidence": float(skill.get("confidence", 0.0)),
                    "source": job.get("source", ""),
                    "source_kind": job.get("source_kind", ""),
                }
            )

    skill_counter = Counter(item["skill_name"] for item in job_skills if item.get("skill_name"))
    program_counter = Counter(item.get("best_program", "") for item in jobs if item.get("best_program"))

    summary = {
        "jobs_total": len(jobs),
        "jobs_ticjob": sum(1 for item in jobs if item.get("source_kind") == "ticjob"),
        "jobs_portal": sum(1 for item in jobs if item.get("source_kind") != "ticjob"),
        "source_counts": dict(kept_by_source),
        "source_kind_counts": dict(source_kind_counts),
        "top_skills": [{"skill": skill, "count": count} for skill, count in skill_counter.most_common(25)],
        "top_programs": [{"program": program, "count": count} for program, count in program_counter.most_common(15)],
        "program_coverage": [
            {
                "program": program["name"],
                "area": program["area"],
                "skills": len(program["skills"]),
            }
            for program in programs
        ],
    }

    metrics = {
        "ticjob": ticjob_metrics,
        "portal": portal_stats,
        "portal_errors": len(portal_errors),
    }

    return {
        "source": "unir_market_scraper",
        "minimum_date": min_date,
        "match_threshold": min_other_score,
        "metrics": metrics,
        "summary": summary,
        "programs": programs,
        "jobs": jobs,
        "job_skills": job_skills,
        "errors": portal_errors,
    }


def write_outputs(
    payload: Dict[str, Any],
    output_json: Path,
    output_csv: Path,
    output_skills_csv: Path,
    output_programs_csv: Path,
) -> None:
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    jobs_csv_rows: List[Dict[str, Any]] = []
    for job in payload["jobs"]:
        jobs_csv_rows.append(
            {
                "job_id": job.get("job_id", ""),
                "job_title": job.get("job_title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "date": job.get("date", ""),
                "source": job.get("source", ""),
                "source_kind": job.get("source_kind", ""),
                "best_program": job.get("best_program", ""),
                "best_score": job.get("best_score", 0),
                "matched_skills": "; ".join(job.get("matched_skills", []) or []),
                "missing_skills": "; ".join(job.get("missing_skills", []) or []),
                "skills": "; ".join(job.get("skills", []) or []),
                "job_url": job.get("job_url", ""),
            }
        )
    write_csv(output_csv, jobs_csv_rows, [
        "job_id",
        "job_title",
        "company",
        "location",
        "date",
        "source",
        "source_kind",
        "best_program",
        "best_score",
        "matched_skills",
        "missing_skills",
        "skills",
        "job_url",
    ])

    skills_rows = sorted(
        [{"skill": skill, "count": count} for skill, count in Counter(item["skill_name"] for item in payload["job_skills"]).items()],
        key=lambda item: (-item["count"], item["skill"]),
    )
    write_csv(output_skills_csv, skills_rows, ["skill", "count"])

    programs_rows = [
        {
            "program": program["name"],
            "area": program["area"],
            "skill_count": program["skill_count"],
            "source_url": program["source_url"],
            "scraped_at": program["scraped_at"],
        }
        for program in payload["programs"]
    ]
    write_csv(output_programs_csv, programs_rows, ["program", "area", "skill_count", "source_url", "scraped_at"])


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build a UNIR market dataset from TICJOB, Computrabajo and Elempleo.")
    parser.add_argument("--ticjob-pages", type=int, default=12, help="Maximum TICJOB search pages to crawl.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--min-date", default="2024-01-01", help="Minimum accepted date for portal jobs (YYYY-MM-DD).")
    parser.add_argument("--min-other-score", type=int, default=18, help="Minimum score to keep Computrabajo/Elempleo jobs.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_JSON), help="Output JSON file.")
    parser.add_argument("--jobs-csv", default=str(DEFAULT_OUTPUT_CSV), help="Output CSV file for jobs.")
    parser.add_argument("--skills-csv", default=str(DEFAULT_SKILLS_CSV), help="Output CSV file for skills.")
    parser.add_argument("--programs-csv", default=str(DEFAULT_PROGRAMS_CSV), help="Output CSV file for programs.")
    args = parser.parse_args(argv)

    payload = collect_market_jobs(
        ticjob_pages=args.ticjob_pages,
        timeout=args.timeout,
        min_date=args.min_date,
        min_other_score=args.min_other_score,
    )
    write_outputs(
        payload,
        Path(args.output),
        Path(args.jobs_csv),
        Path(args.skills_csv),
        Path(args.programs_csv),
    )

    summary = payload["summary"]
    print(f"[done] jobs_total: {summary['jobs_total']}")
    print(f"[done] jobs_ticjob: {summary['jobs_ticjob']}")
    print(f"[done] jobs_portal: {summary['jobs_portal']}")
    if summary["top_skills"]:
        print("[done] top_skills: " + ", ".join(f"{row['skill']}={row['count']}" for row in summary["top_skills"][:10]))
    if summary["source_counts"]:
        print(
            "[done] source_counts: "
            + ", ".join(f"{name}={count}" for name, count in sorted(summary["source_counts"].items(), key=lambda item: (-item[1], item[0]))[:10])
        )
    print(f"[done] json: {Path(args.output).resolve()}")
    print(f"[done] csv: {Path(args.jobs_csv).resolve()}")
    print(f"[done] skills csv: {Path(args.skills_csv).resolve()}")
    print(f"[done] programs csv: {Path(args.programs_csv).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
