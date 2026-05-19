from __future__ import annotations

import argparse
import csv
import html as html_lib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

from ticjob_scraper import VisibleTextParser, normalize_text, repair_text


SEARCH_URL = "https://ticjob.co/es/ajax/SearchResults"
DEFAULT_OUTPUT_JSON = "ticjob_deep_bi_jobs.json"
DEFAULT_OUTPUT_CSV = "ticjob_deep_bi_jobs.csv"
DEFAULT_SKILLS_CSV = "ticjob_deep_bi_skills.csv"


BI_TERMS: List[Tuple[str, float]] = [
    ("inteligencia de negocios", 4.5),
    ("business intelligence", 4.5),
    ("data analyst", 3.5),
    ("analista de datos", 3.5),
    ("analista bi", 3.5),
    ("power bi", 3.0),
    ("tableau", 3.0),
    ("qlik", 2.5),
    ("looker", 2.5),
    ("dashboards", 1.5),
    ("dashboard", 1.5),
    ("kpi", 1.5),
    ("reporting", 1.2),
    ("visualizacion de datos", 1.5),
    ("storytelling", 1.2),
    ("sql", 1.5),
    ("etl", 1.5),
    ("elt", 1.5),
    ("data lake", 1.5),
    ("data warehouse", 1.5),
    ("modelado de datos", 1.2),
    ("gobierno del dato", 1.2),
]


SKILL_CANONICAL = {
    "power bi": "Power BI",
    "tableau": "Tableau",
    "qlik": "Qlik",
    "looker": "Looker",
    "sql": "SQL",
    "etl": "ETL",
    "elt": "ELT",
    "data lake": "Data lake",
    "data warehouse": "Data warehouse",
    "data analyst": "Data Analyst",
    "analista de datos": "Analista de datos",
    "analista bi": "Analista BI",
    "business intelligence": "Business Intelligence",
    "inteligencia de negocios": "Inteligencia de negocios",
    "dashboard": "Dashboard",
    "dashboards": "Dashboards",
    "kpi": "KPI",
    "reporting": "Reporting",
    "visualizacion de datos": "Visualizacion de datos",
    "storytelling": "Storytelling",
    "modelado de datos": "Modelado de datos",
    "gobierno del dato": "Gobierno del dato",
    "excel": "Excel",
}


DEEP_SKILL_TERMS: List[Tuple[str, str]] = [
    ("business intelligence", "Business Intelligence"),
    ("inteligencia de negocios", "Inteligencia de negocios"),
    ("data analyst", "Data Analyst"),
    ("analista de datos", "Analista de datos"),
    ("analista bi", "Analista BI"),
    ("data engineer", "Data Engineer"),
    ("sql", "SQL"),
    ("etl", "ETL"),
    ("elt", "ELT"),
    ("power bi", "Power BI"),
    ("tableau", "Tableau"),
    ("qlik", "Qlik"),
    ("looker", "Looker"),
    ("dashboard", "Dashboard"),
    ("dashboards", "Dashboards"),
    ("kpi", "KPI"),
    ("reporting", "Reporting"),
    ("visualizacion de datos", "Visualizacion de datos"),
    ("storytelling", "Storytelling"),
    ("data lake", "Data lake"),
    ("data warehouse", "Data warehouse"),
    ("modelado de datos", "Modelado de datos"),
    ("gobierno del dato", "Gobierno del dato"),
    ("python", "Python"),
    ("pyspark", "PySpark"),
    ("git", "GIT"),
    ("azure data factory", "Azure Data Factory"),
    ("azure databricks", "Azure Databricks"),
    ("azure data lake", "Azure Data Lake"),
    ("azure fabric", "Azure Fabric"),
    ("data factory", "Data Factory"),
    ("databricks", "Databricks"),
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


def contains_term(text: str, term: str) -> bool:
    needle = normalize_text(term)
    if not needle:
        return False
    if " " not in needle and len(needle) <= 3:
        return re.search(rf"\b{re.escape(needle)}\b", text) is not None
    return needle in text


def fetch(url: str, timeout: int = 30) -> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def parse_search_results(text: str) -> List[Dict[str, str]]:
    pattern = re.compile(
        r'<a\s+class="job-title search-item-link"\s+href="([^"]+)">\s*([^<]+)</a>',
        flags=re.I | re.S,
    )
    items: List[Dict[str, str]] = []
    for href, title in pattern.findall(text):
        href = html_lib.unescape(href).strip()
        title = html_lib.unescape(re.sub(r"\s+", " ", title)).strip()
        if not href or not title:
            continue
        items.append({"job_url": href, "job_title": title})
    return unique_dicts(items, key="job_url")


def unique_dicts(items: Sequence[Dict[str, str]], key: str) -> List[Dict[str, str]]:
    seen: set[str] = set()
    out: List[Dict[str, str]] = []
    for item in items:
        value = item.get(key, "")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(item)
    return out


def parse_title_meta(html: str) -> Tuple[str, str, str]:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    if not m:
        return "", "", ""
    title = html_lib.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    offer_title = ""
    company = ""
    location = ""
    m2 = re.search(r"Oferta de trabajo\s+(.*?)\s+en\s+(.*?)\s+de\s+(.*?)\s*-\s*ticjob\.co", title, flags=re.I)
    if m2:
        offer_title = html_lib.unescape(m2.group(1)).strip()
        location = html_lib.unescape(m2.group(2)).strip()
        company = html_lib.unescape(m2.group(3)).strip()
    return offer_title, company, location


def parse_detail_page(url: str, html: str) -> Dict[str, Any]:
    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    lines = parser.lines()

    title, company, location = parse_title_meta(html)
    if not title and lines:
        title = lines[0].strip()

    desc_start = next((i for i, line in enumerate(lines) if normalize_text(line) == "descripcion de la oferta"), None)
    stack_start = next((i for i, line in enumerate(lines) if normalize_text(line) == "stack de la oferta"), None)
    similar_start = next((i for i, line in enumerate(lines) if "ofertas de trabajo similares" in normalize_text(line)), None)
    summary_start = next((i for i, line in enumerate(lines) if normalize_text(line) == "resumen de la oferta"), None)

    body_start = (desc_start + 1) if desc_start is not None else 0
    body_end = stack_start if stack_start is not None else (similar_start if similar_start is not None else len(lines))
    description_lines = [line for line in lines[body_start:body_end] if normalize_text(line)]

    stack_lines: List[str] = []
    if stack_start is not None:
        stack_end = similar_start if similar_start is not None else (summary_start if summary_start is not None else len(lines))
        stack_lines = [line for line in lines[stack_start + 1 : stack_end] if normalize_text(line)]

    raw_text = " ".join(description_lines + stack_lines)
    text_norm = normalize_text(" ".join([title, company, location, raw_text]))
    skills = []
    for term, label in DEEP_SKILL_TERMS:
        if contains_term(text_norm, term):
            skills.append(label)
    skills = unique(skills)

    signals = detect_signals(text_norm)

    return {
        "job_url": url,
        "job_title": title,
        "company": company,
        "location": location,
        "description": " ".join(description_lines).strip(),
        "stack": " ".join(stack_lines).strip(),
        "full_text": raw_text,
        "skills": skills,
        "signals": signals,
        "source_lines": len(lines),
    }


def canonical_skill(name: str) -> str:
    cleaned = repair_text(name).strip()
    if not cleaned:
        return ""
    return SKILL_CANONICAL.get(normalize_text(cleaned), cleaned)


def detect_signals(text_norm: str) -> List[str]:
    hits = []
    for term, _weight in BI_TERMS:
        if contains_term(text_norm, term):
            hits.append(term)
    return unique(hits)


def bi_score(job: Dict[str, Any]) -> float:
    text_norm = normalize_text(" ".join([job.get("job_title", ""), job.get("company", ""), job.get("location", ""), job.get("description", ""), job.get("stack", ""), " ".join(job.get("skills", []) or []), " ".join(job.get("signals", []) or [])]))
    score = 0.0
    for term, weight in BI_TERMS:
        if contains_term(text_norm, term):
            score += weight
    title = normalize_text(job.get("job_title", ""))
    if "inteligencia de negocios" in title or "business intelligence" in title:
        score += 3.0
    if "analista" in title and ("datos" in title or "bi" in title):
        score += 2.0
    if any(contains_term(text_norm, t) for t in ("power bi", "tableau", "qlik", "looker")):
        score += 2.0
    if any(contains_term(text_norm, t) for t in ("dashboard", "dashboards", "kpi", "reporting", "visualizacion de datos")):
        score += 1.0
    return round(score, 2)


def is_bi_related(job: Dict[str, Any], min_score: float) -> bool:
    return bi_score(job) >= min_score


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def scrape_jobs(max_pages: int, timeout: int) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    seen_urls: set[str] = set()
    jobs: List[Dict[str, Any]] = []
    metrics = {"pages": 0, "search_results": 0, "detail_pages": 0, "discarded": 0}

    for page in range(1, max_pages + 1):
        search_html = fetch(f"{SEARCH_URL}?page={page}", timeout=timeout)
        page_items = parse_search_results(search_html)
        metrics["pages"] += 1
        metrics["search_results"] += len(page_items)
        if not page_items:
            break

        for item in page_items:
            url = item["job_url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            try:
                detail_html = fetch(url, timeout=timeout)
                detail = parse_detail_page(url, detail_html)
                detail["search_title"] = item["job_title"]
                detail["match_score"] = bi_score(detail)
                jobs.append(detail)
                metrics["detail_pages"] += 1
            except Exception:
                metrics["discarded"] += 1
                continue

    jobs = sorted(jobs, key=lambda item: (-float(item.get("match_score", 0)), item.get("job_title", "")))
    return jobs, metrics


def summarize(jobs: Sequence[Dict[str, Any]], min_score: float) -> Dict[str, Any]:
    matched = [job for job in jobs if is_bi_related(job, min_score=min_score)]
    skill_counter: Counter[str] = Counter()
    signal_counter: Counter[str] = Counter()
    for job in matched:
        for skill in job.get("skills", []) or []:
            skill_counter[skill] += 1
        for signal in job.get("signals", []) or []:
            signal_counter[signal] += 1
    return {
        "jobs_total": len(jobs),
        "jobs_bi": len(matched),
        "top_skills": [{"skill": skill, "count": count} for skill, count in skill_counter.most_common(25)],
        "top_signals": [{"signal": signal, "count": count} for signal, count in signal_counter.most_common(15)],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Deep scrape TICJOB and extract BI-related jobs and skills.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum search-result pages to crawl.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--min-score", type=float, default=5.0, help="Minimum BI score to keep a job.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_JSON, help="Output JSON file.")
    parser.add_argument("--csv-output", default=DEFAULT_OUTPUT_CSV, help="Output CSV file with matched jobs.")
    parser.add_argument("--skills-output", default=DEFAULT_SKILLS_CSV, help="Output CSV file with aggregated skills.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args(argv)

    jobs, metrics = scrape_jobs(max_pages=args.max_pages, timeout=args.timeout)
    summary = summarize(jobs, min_score=args.min_score)
    matched = [job for job in jobs if is_bi_related(job, min_score=args.min_score)]
    payload = {
        "source": SEARCH_URL,
        "metrics": metrics,
        "minimum_score": args.min_score,
        "summary": summary,
        "jobs": matched,
    }

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )

    csv_rows = []
    for job in matched:
        csv_rows.append(
            {
                "job_title": job.get("job_title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "match_score": job.get("match_score", 0),
                "skills": "; ".join(job.get("skills", []) or []),
                "signals": "; ".join(job.get("signals", []) or []),
                "job_url": job.get("job_url", ""),
            }
        )
    write_csv(Path(args.csv_output), csv_rows, ["job_title", "company", "location", "match_score", "skills", "signals", "job_url"])
    write_csv(Path(args.skills_output), summary["top_skills"], ["skill", "count"])

    print(f"[done] pages: {metrics['pages']}")
    print(f"[done] search_results: {metrics['search_results']}")
    print(f"[done] detail_pages: {metrics['detail_pages']}")
    print(f"[done] BI jobs: {summary['jobs_bi']}")
    if summary["top_skills"]:
        print("[done] top skills: " + ", ".join(f"{x['skill']}={x['count']}" for x in summary["top_skills"][:10]))
    print(f"[done] json: {output_path.resolve()}")
    print(f"[done] csv: {Path(args.csv_output).resolve()}")
    print(f"[done] skills csv: {Path(args.skills_output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
