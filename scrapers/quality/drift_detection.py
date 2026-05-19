from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.taxonomy.domain_taxonomy import SKILL_BY_CANONICAL, normalize_text


def load_current_skills_from_validation(output_dir: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in output_dir.glob("*.json"):
        if path.name == "summary.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for job in data.get("normalized_jobs", []):
            counts.update(job.get("skills", []))
    return counts


def load_baseline_from_taxonomy() -> Counter[str]:
    return Counter({skill: 1 for skill in SKILL_BY_CANONICAL})


def detect_skill_drift(current: Counter[str], baseline: Counter[str], *, min_count: int = 2) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for skill, current_count in current.most_common():
        if current_count < min_count:
            continue
        baseline_count = baseline.get(normalize_text(skill), baseline.get(skill, 0))
        growth = round((current_count - baseline_count) / max(1, baseline_count), 4)
        if baseline_count == 0 or growth >= 1.0:
            definition = SKILL_BY_CANONICAL.get(skill)
            events.append({
                "skill_normalized": skill,
                "skill_domain": definition.domain if definition else None,
                "current_count": current_count,
                "baseline_count": baseline_count,
                "growth_rate": growth,
                "detection_date": str(date.today()),
                "status": "candidate" if baseline_count == 0 else "growth",
                "evidence": {"source": "labor_engine_validation_phase_1"},
            })
    return events


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def upsert_drift_events(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.skill_drift_events (
                skill_normalized, skill_domain, current_count, baseline_count,
                growth_rate, detection_date, status, evidence
            )
            VALUES %s
            ON CONFLICT (skill_normalized, detection_date)
            DO UPDATE SET
                skill_domain = EXCLUDED.skill_domain,
                current_count = EXCLUDED.current_count,
                baseline_count = EXCLUDED.baseline_count,
                growth_rate = EXCLUDED.growth_rate,
                status = EXCLUDED.status,
                evidence = EXCLUDED.evidence
            """,
            [
                (
                    event["skill_normalized"],
                    event["skill_domain"],
                    event["current_count"],
                    event["baseline_count"],
                    event["growth_rate"],
                    event["detection_date"],
                    event["status"],
                    Json(event["evidence"]),
                )
                for event in events
            ],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect emerging labor skills and skill demand drift.")
    parser.add_argument("--validation-dir", default="outputs/labor_engine_validation_phase_1")
    parser.add_argument("--output", default="outputs/labor_intelligence_stabilization/skill_drift_events.json")
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--write-db", action="store_true")
    args = parser.parse_args()
    events = detect_skill_drift(
        load_current_skills_from_validation(Path(args.validation_dir)),
        load_baseline_from_taxonomy(),
        min_count=args.min_count,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_db:
        upsert_drift_events(events)
    print(json.dumps({"events": len(events), "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

