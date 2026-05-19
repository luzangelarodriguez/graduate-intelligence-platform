from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import ticjob_scraper as ticjob
from ticjob_scraper import extract_skill_names, normalize_text, repair_text, scrape_ticjob


DEFAULT_URL = "https://ticjob.co/es/search"
DEFAULT_MIN_DATE = "2026-04-01"
DEFAULT_MIN_SCORE = 4.0


BI_TERMS: List[Tuple[str, float]] = [
    ("inteligencia de negocios", 3.5),
    ("business intelligence", 3.5),
    ("bi", 1.0),
    ("analista de datos", 2.5),
    ("analista bi", 3.0),
    ("data analyst", 2.5),
    ("data analytics", 2.5),
    ("analytics", 1.5),
    ("analitica", 1.5),
    ("analitica de datos", 2.5),
    ("dashboard", 1.75),
    ("tablero", 1.75),
    ("reporting", 1.5),
    ("visualizacion de datos", 1.75),
    ("storytelling", 1.0),
    ("kpi", 1.5),
    ("etl", 1.75),
    ("elt", 1.75),
    ("data warehouse", 1.75),
    ("data lake", 1.5),
    ("sql", 1.5),
    ("power bi", 2.75),
    ("tableau", 2.5),
    ("qlik", 2.5),
    ("looker", 2.25),
    ("excel", 1.0),
    ("power query", 1.5),
    ("modelado de datos", 1.75),
    ("gobierno del dato", 1.75),
]


SKILL_ALIASES: Dict[str, str] = {
    "power bi": "Power BI",
    "tableau": "Tableau",
    "qlik": "Qlik",
    "looker": "Looker",
    "sql": "SQL",
    "etl": "ETL",
    "elt": "ELT",
    "kpi": "KPI",
    "excel": "Excel",
    "business intelligence": "Business Intelligence",
    "inteligencia de negocios": "Inteligencia de negocios",
    "analitica": "Analitica",
    "analitica de datos": "Analitica de datos",
    "visualizacion de datos": "Visualizacion de datos",
    "gobierno del dato": "Gobierno del dato",
    "data warehouse": "Data warehouse",
    "data lake": "Data lake",
    "power query": "Power Query",
    "modelado de datos": "Modelado de datos",
    "data analytics": "Data analytics",
    "analista bi": "Analista BI",
    "analista de datos": "Analista de datos",
    "data analyst": "Data Analyst",
}


FOCUS_SKILLS = [
    "Power BI",
    "Tableau",
    "SQL",
    "Excel",
    "Business Intelligence",
    "Inteligencia de negocios",
    "Analista de datos",
    "Analista BI",
    "Data Analyst",
    "ETL",
    "ELT",
    "Data warehouse",
    "Data lake",
    "Modelado de datos",
    "Visualizacion de datos",
    "KPI",
    "Reporting",
    "Storytelling",
    "Gobierno del dato",
]


def unique(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        item = repair_text(value).strip()
        if not item:
            continue
        key = normalize_text(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def canonical_skill(name: str) -> str:
    cleaned = repair_text(name).strip()
    if not cleaned:
        return ""
    return SKILL_ALIASES.get(normalize_text(cleaned), cleaned)


def contains_term(text: str, term: str) -> bool:
    phrase = normalize_text(term)
    if not phrase:
        return False
    if " " not in phrase and len(phrase) <= 3:
        return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
    return phrase in text


def job_text(job: Dict[str, Any]) -> str:
    return " ".join(
        [
            repair_text(job.get("job_title", "")),
            repair_text(job.get("company", "")),
            repair_text(job.get("location", "")),
            repair_text(job.get("description", "")),
            " ".join(repair_text(skill) for skill in job.get("skills", []) or []),
        ]
    ).strip()


def is_bi_related(job: Dict[str, Any], min_score: float = DEFAULT_MIN_SCORE) -> Tuple[bool, float, List[str]]:
    text = normalize_text(job_text(job))
    score = 0.0
    hits: List[str] = []

    for term, weight in BI_TERMS:
        if term and contains_term(text, term):
            score += weight
            hits.append(term)

    title = normalize_text(job.get("job_title", ""))
    if "analista" in title and ("datos" in title or "bi" in title):
        score += 1.5
        hits.append("title:analyst")
    if "inteligencia de negocios" in title or "business intelligence" in title:
        score += 2.5
        hits.append("title:bi")
    if "data" in title and "analyst" in title:
        score += 1.5
        hits.append("title:data-analyst")

    if any(contains_term(text, keyword) for keyword in ("power bi", "tableau", "qlik", "looker")):
        score += 2.0
        hits.append("bi-tool")

    if any(contains_term(text, keyword) for keyword in ("dashboard", "kpi", "reporting", "visualizacion de datos", "storytelling")):
        score += 1.0
        hits.append("analytics-output")

    return score >= min_score, round(score, 2), unique(hits)


def detect_skills(job: Dict[str, Any]) -> List[str]:
    text = job_text(job)
    raw = []
    raw.extend(job.get("skills", []) or [])
    raw.extend(extract_skill_names(text))

    extracted: List[str] = []
    for skill in raw:
        canonical = canonical_skill(skill)
        if not canonical:
            continue
        n = normalize_text(canonical)
        if any(focus in n for focus in ("power bi", "tableau", "qlik", "looker", "sql", "etl", "elt", "kpi", "excel", "analytics", "analitica", "business intelligence", "inteligencia de negocios", "data analyst", "analista de datos", "analista bi", "visualizacion")):
            extracted.append(canonical)

    if not extracted:
        text_norm = normalize_text(text)
        for skill in FOCUS_SKILLS:
            if normalize_text(skill) in text_norm:
                extracted.append(skill)

    return unique(extracted)


def summarize_jobs(jobs: Sequence[Dict[str, Any]], min_score: float) -> Dict[str, Any]:
    matched: List[Dict[str, Any]] = []
    skill_counter: Counter[str] = Counter()
    term_counter: Counter[str] = Counter()

    for job in jobs:
        ok, score, hits = is_bi_related(job, min_score=min_score)
        if not ok:
            continue
        skills = detect_skills(job)
        for skill in skills:
            skill_counter[skill] += 1
        for hit in hits:
            term_counter[hit] += 1
        matched.append(
            {
                "job_title": repair_text(job.get("job_title", "")),
                "company": repair_text(job.get("company", "")),
                "date": repair_text(job.get("date", "")),
                "location": repair_text(job.get("location", "")),
                "description": repair_text(job.get("description", "")),
                "skills": skills,
                "match_score": score,
                "match_signals": hits,
            }
        )

    return {
        "total_jobs": len(jobs),
        "matched_jobs": len(matched),
        "top_skills": [{"skill": skill, "count": count} for skill, count in skill_counter.most_common(25)],
        "top_signals": [{"signal": signal, "count": count} for signal, count in term_counter.most_common(15)],
        "jobs": matched,
    }


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_jobs_from_json(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "jobs" in payload:
        jobs = payload["jobs"]
        if isinstance(jobs, list):
            return [job for job in jobs if isinstance(job, dict)]
    if isinstance(payload, list):
        return [job for job in payload if isinstance(job, dict)]
    raise ValueError(f"Unsupported JSON structure in {path}")


def build_rows(jobs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for job in jobs:
        skills = detect_skills(job)
        ok, score, hits = is_bi_related(job)
        rows.append(
            {
                "job_title": repair_text(job.get("job_title", "")),
                "company": repair_text(job.get("company", "")),
                "date": repair_text(job.get("date", "")),
                "location": repair_text(job.get("location", "")),
                "match_score": score,
                "skills": "; ".join(skills),
                "signals": "; ".join(hits),
                "is_bi_related": "yes" if ok else "no",
            }
        )
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Filter TICJOB offers related to business intelligence and extract the skills most requested."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="TICJOB search URL.")
    parser.add_argument("--input", default=None, help="Optional local HTML file to scrape instead of the URL.")
    parser.add_argument("--input-json", default=None, help="Optional JSON file with already scraped TICJOB jobs.")
    parser.add_argument("--min-date", default=DEFAULT_MIN_DATE, help="Minimum publication date for the TICJOB scraper.")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE, help="Minimum relevance score for BI filtering.")
    parser.add_argument("--output", default="ticjob_bi_jobs.json", help="Output JSON file.")
    parser.add_argument("--csv-output", default="ticjob_bi_jobs.csv", help="Output CSV file with matched offers.")
    parser.add_argument("--skills-output", default="ticjob_bi_skills.csv", help="Output CSV file with aggregated skills.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output.")
    args = parser.parse_args(argv)

    if args.input_json:
        jobs = load_jobs_from_json(Path(args.input_json))
        source = str(Path(args.input_json).resolve())
        metrics = {"total_found": len(jobs), "filtered": len(jobs), "discarded": 0}
    else:
        try:
            ticjob.MIN_JOB_DATE = date.fromisoformat(args.min_date)
        except Exception:
            ticjob.MIN_JOB_DATE = date.fromisoformat(DEFAULT_MIN_DATE)
        html = Path(args.input).read_text(encoding="utf-8", errors="replace") if args.input else None
        jobs, metrics = scrape_ticjob(args.url, timeout=args.timeout, html=html)
        source = args.url

    summary = summarize_jobs(jobs, min_score=args.min_score)
    payload = {
        "source": source,
        "minimum_score": args.min_score,
        "metrics": metrics,
        "summary": summary,
    }

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )

    rows = build_rows(summary["jobs"])
    write_csv(
        Path(args.csv_output),
        rows,
        ["job_title", "company", "date", "location", "match_score", "skills", "signals", "is_bi_related"],
    )

    skill_rows = summary["top_skills"]
    write_csv(Path(args.skills_output), skill_rows, ["skill", "count"])

    print(f"[done] source: {source}")
    print(f"[done] total jobs: {summary['total_jobs']}")
    print(f"[done] BI jobs: {summary['matched_jobs']}")
    if skill_rows:
        print("[done] top skills: " + ", ".join(f"{row['skill']}={row['count']}" for row in skill_rows[:10]))
    print(f"[done] json: {output_path.resolve()}")
    print(f"[done] csv: {Path(args.csv_output).resolve()}")
    print(f"[done] skills csv: {Path(args.skills_output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
