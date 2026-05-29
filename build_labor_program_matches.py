from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from psycopg2.extras import RealDictCursor, execute_values

from sync_to_railway import connect, get_local_config, get_railway_config, load_dotenv_files


ROOT = Path(__file__).resolve().parent
MIGRATION = ROOT / "database" / "migrations" / "008_labor_matching_bridge.sql"


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    return " ".join(text.split())


def token_set(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) >= 2}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def fetch_all(conn, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def execute_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(MIGRATION.read_text(encoding="utf-8"))


def fetch_program_skills(conn) -> dict[int, dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT
            e.id AS especializacion_id,
            e.nombre AS especializacion,
            s.id AS skill_id,
            s.nombre AS skill_name
        FROM public.especializaciones e
        JOIN public.especializacion_skills es ON es.especializacion_id = e.id
        JOIN public.skills s ON s.id = es.skill_id
        ORDER BY e.id, s.nombre
        """,
    )
    programs: dict[int, dict[str, Any]] = {}
    for row in rows:
        program = programs.setdefault(
            int(row["especializacion_id"]),
            {
                "id": int(row["especializacion_id"]),
                "name": row["especializacion"],
                "skills": {},
                "tokens": token_set(row["especializacion"]),
            },
        )
        skill_id = int(row["skill_id"])
        normalized = normalize_text(row["skill_name"])
        program["skills"][skill_id] = {
            "id": skill_id,
            "name": row["skill_name"],
            "normalized": normalized,
            "tokens": token_set(row["skill_name"]),
        }
        program["tokens"].update(token_set(row["skill_name"]))
    return programs


def fetch_jobs(conn) -> dict[str, dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT
            e.id::text AS job_id,
            COALESCE(e.titulo, '') AS title,
            COALESCE(e.descripcion, '') AS description,
            COALESCE(e.empresa, '') AS company,
            es.skill_id,
            COALESCE(s.nombre, es.skill_normalized, es.skill_original, '') AS skill_name
        FROM public.empleos e
        LEFT JOIN public.empleo_skills es ON es.empleo_id::text = e.id::text
        LEFT JOIN public.skills s ON s.id = es.skill_id
        ORDER BY e.id
        """,
    )
    jobs: dict[str, dict[str, Any]] = {}
    for row in rows:
        job = jobs.setdefault(
            str(row["job_id"]),
            {
                "id": str(row["job_id"]),
                "title": row["title"],
                "description": row["description"],
                "company": row["company"],
                "skills": {},
                "skill_names": set(),
                "tokens": token_set(f"{row['title']} {row['description']}"),
            },
        )
        skill_name = str(row.get("skill_name") or "").strip()
        if skill_name:
            normalized = normalize_text(skill_name)
            skill_id = row.get("skill_id")
            key = int(skill_id) if skill_id is not None else normalized
            job["skills"][key] = {
                "id": int(skill_id) if skill_id is not None else None,
                "name": skill_name,
                "normalized": normalized,
                "tokens": token_set(skill_name),
            }
            job["skill_names"].add(normalized)
            job["tokens"].update(token_set(skill_name))
    return jobs


def match_program_job(program: dict[str, Any], job: dict[str, Any], threshold: float) -> list[dict[str, Any]]:
    program_skills = program["skills"]
    job_skill_by_id = {value["id"]: value for value in job["skills"].values() if value["id"] is not None}
    job_skill_by_name = {value["normalized"]: value for value in job["skills"].values() if value["normalized"]}
    matched: list[dict[str, Any]] = []

    for skill_id, program_skill in program_skills.items():
        confidence = 0.0
        source = "no_match"
        if skill_id in job_skill_by_id:
            confidence = 1.0
            source = "exact_skill_id"
        elif program_skill["normalized"] in job_skill_by_name:
            confidence = 0.92
            source = "normalized_skill"
        else:
            similarity = max(
                [jaccard(program_skill["tokens"], job_skill["tokens"]) for job_skill in job["skills"].values()]
                or [0.0]
            )
            text_presence = program_skill["normalized"] and program_skill["normalized"] in normalize_text(
                f"{job['title']} {job['description']}"
            )
            if text_presence:
                confidence = 0.86
                source = "job_text_presence"
            elif similarity >= threshold:
                confidence = min(0.82, 0.55 + similarity)
                source = "fuzzy_skill"

        if confidence > 0:
            matched.append({"skill_id": skill_id, "confidence": round(confidence, 4), "source": source})

    return matched


def build_matches(conn, *, threshold: float, min_score: float, dry_run: bool) -> dict[str, Any]:
    execute_schema(conn)
    programs = fetch_program_skills(conn)
    jobs = fetch_jobs(conn)
    rows: list[tuple[Any, ...]] = []
    program_job_counter: dict[int, set[str]] = defaultdict(set)

    for program in programs.values():
        total_program_skills = max(1, len(program["skills"]))
        for job in jobs.values():
            if not job["skills"]:
                continue
            matched = match_program_job(program, job, threshold)
            if not matched:
                continue
            total_job_skills = max(1, len(job["skills"]))
            raw_score = ((len(matched) / total_job_skills) * 60.0) + ((len(matched) / total_program_skills) * 40.0)
            score = round(min(100.0, raw_score), 2)
            if score < min_score:
                continue
            program_job_counter[program["id"]].add(job["id"])
            for item in matched:
                rows.append(
                    (
                        program["id"],
                        job["id"],
                        item["skill_id"],
                        score,
                        f"labor_program_matching_v1:{item['source']}",
                        item["confidence"],
                    )
                )

    if not dry_run and rows:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO public.labor_program_skill_matches (
                    especializacion_id, job_id, skill_id, match_score, source, confidence
                )
                VALUES %s
                ON CONFLICT (especializacion_id, job_id, skill_id, source)
                DO UPDATE SET
                    match_score = EXCLUDED.match_score,
                    confidence = EXCLUDED.confidence,
                    updated_at = now()
                """,
                rows,
                page_size=1000,
            )

    return {
        "programs": len(programs),
        "jobs": len(jobs),
        "match_rows": len(rows),
        "programs_with_matches": len(program_job_counter),
        "distinct_program_job_matches": sum(len(values) for values in program_job_counter.values()),
        "dry_run": dry_run,
    }


def main() -> int:
    load_dotenv_files()
    parser = argparse.ArgumentParser(description="Construye matches laborales programa-empleo desde skills reales.")
    parser.add_argument("--target", choices=["railway", "local"], default=os.getenv("MATCH_DB_TARGET", "railway"))
    parser.add_argument("--threshold", type=float, default=0.55, help="Umbral Jaccard para fuzzy matching básico.")
    parser.add_argument("--min-score", type=float, default=8.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = get_local_config() if args.target == "local" else get_railway_config()
    with connect(config) as conn:
        conn.autocommit = False
        try:
            result = build_matches(conn, threshold=args.threshold, min_score=args.min_score, dry_run=args.dry_run)
            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
