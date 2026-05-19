from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

SOURCE_ALIASES = {
    "spe": "servicio_publico_empleo",
}


def canonical_source(value: str) -> str:
    return SOURCE_ALIASES.get(value, value)


def load_validation_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_log_counts(log_path: Path) -> tuple[Counter[str], Counter[str]]:
    attempts: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    if not log_path.exists():
        return attempts, counts
    current_source = None
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        scrape_match = re.search(r"scraping source=([a-zA-Z0-9_]+)", line)
        if scrape_match:
            attempts[canonical_source(scrape_match.group(1))] += 1
        match = re.search(r"source=([a-zA-Z0-9_]+)", line)
        if match:
            current_source = canonical_source(match.group(1))
        if "Timeout" in line and current_source:
            counts[current_source] += 1
    return attempts, counts


def compute_source_metrics(summary: dict[str, Any], *, log_path: Path | None = None) -> list[dict[str, Any]]:
    per_source: dict[str, dict[str, float]] = defaultdict(lambda: {
        "raw_jobs": 0,
        "normalized_jobs": 0,
        "relevant_jobs": 0,
        "duplicates": 0,
        "domain_runs": 0,
    })
    for result in summary.get("results", []):
        expected = set(result.get("expected_domains") or [])
        source_counts = result.get("source_counts") or {}
        contaminations = result.get("contaminations") or []
        contaminated_by_source = Counter(item.get("portal") or "sin_fuente" for item in contaminations)
        for source, count in source_counts.items():
            source = canonical_source(source)
            metrics = per_source[source]
            metrics["domain_runs"] += 1
            metrics["normalized_jobs"] += count
            metrics["raw_jobs"] += max(count, result.get("raw_jobs", 0) / max(1, len(source_counts)))
            metrics["duplicates"] += result.get("duplicates_removed", 0) / max(1, len(source_counts))
            metrics["relevant_jobs"] += max(0, count - contaminated_by_source[source])
    attempt_counts, timeout_counts = parse_log_counts(log_path) if log_path else (Counter(), Counter())
    rows: list[dict[str, Any]] = []
    all_sources = set(per_source) | set(timeout_counts) | set(attempt_counts)
    for source in sorted(all_sources):
        item = per_source[source]
        attempts = max(1, attempt_counts[source] or item["domain_runs"] + timeout_counts[source])
        normalized = item["normalized_jobs"]
        raw = item["raw_jobs"]
        rows.append({
            "source": source,
            "success_rate": round(min(1.0, item["domain_runs"] / attempts), 4),
            "relevance_rate": round((item["relevant_jobs"] / normalized) if normalized else 0.0, 4),
            "timeout_rate": round(timeout_counts[source] / attempts, 4),
            "duplication_rate": round((item["duplicates"] / raw) if raw else 0.0, 4),
            "extraction_date": str(date.today()),
            "raw_jobs": int(raw),
            "normalized_jobs": int(normalized),
            "relevant_jobs": int(item["relevant_jobs"]),
            "timeout_count": int(timeout_counts[source]),
            "error_count": int(timeout_counts[source]),
            "notes": "computed_from_labor_engine_validation_phase_1",
        })
    return rows


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def upsert_source_metrics(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.source_quality_metrics (
                source, success_rate, relevance_rate, timeout_rate, duplication_rate,
                extraction_date, raw_jobs, normalized_jobs, relevant_jobs,
                timeout_count, error_count, notes
            )
            VALUES %s
            ON CONFLICT (source, extraction_date)
            DO UPDATE SET
                success_rate = EXCLUDED.success_rate,
                relevance_rate = EXCLUDED.relevance_rate,
                timeout_rate = EXCLUDED.timeout_rate,
                duplication_rate = EXCLUDED.duplication_rate,
                raw_jobs = EXCLUDED.raw_jobs,
                normalized_jobs = EXCLUDED.normalized_jobs,
                relevant_jobs = EXCLUDED.relevant_jobs,
                timeout_count = EXCLUDED.timeout_count,
                error_count = EXCLUDED.error_count,
                notes = EXCLUDED.notes
            """,
            [
                (
                    row["source"],
                    row["success_rate"],
                    row["relevance_rate"],
                    row["timeout_rate"],
                    row["duplication_rate"],
                    row["extraction_date"],
                    row["raw_jobs"],
                    row["normalized_jobs"],
                    row["relevant_jobs"],
                    row["timeout_count"],
                    row["error_count"],
                    row["notes"],
                )
                for row in rows
            ],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute source quality metrics from validation outputs.")
    parser.add_argument("--summary", default="outputs/labor_engine_validation_phase_1/summary.json")
    parser.add_argument("--log-file", default="logs/labor_engine_validation_phase_1.log")
    parser.add_argument("--output", default="outputs/labor_intelligence_stabilization/source_quality_metrics.json")
    parser.add_argument("--write-db", action="store_true")
    args = parser.parse_args()
    rows = compute_source_metrics(load_validation_summary(Path(args.summary)), log_path=Path(args.log_file))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_db:
        upsert_source_metrics(rows)
    print(json.dumps({"rows": len(rows), "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
