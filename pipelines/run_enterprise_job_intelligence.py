from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from psycopg2.extras import execute_values

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.agentic_job_extractor import OUTPUT_JSON as EXTRACTION_JSON, run_enterprise_extraction  # noqa: E402
from backend.db import get_conn  # noqa: E402
from ml.curriculum.curriculum_market_gap_engine import JSON_PATH as GAP_JSON, build_curriculum_market_gap_map  # noqa: E402
from ml.labor.labor_market_skill_extraction_engine import build_labor_market_skill_universe  # noqa: E402
from ml.labor.occupational_skill_cluster_engine import build_occupational_skill_clusters  # noqa: E402
from pipelines.run_agentic_labor_intelligence import load_environment, load_results_from_json, persist_layers  # noqa: E402
from scrapers.discovery.api_endpoint_detector import run_api_discovery  # noqa: E402

OUTPUT_DIR = ROOT_DIR / "outputs"
MIGRATION_013 = ROOT_DIR / "database" / "migrations" / "013_curriculum_market_gap_map.sql"


def _copy_report(source: Path, target_name: str) -> None:
    if source.exists():
        shutil.copyfile(source, OUTPUT_DIR / target_name)


def _persist_market_intelligence(universe: list[Any], clusters: list[Any], gap_map: Any) -> dict[str, Any]:
    load_environment()
    counts = {
        "labor_market_skill_universe": 0,
        "occupational_skill_clusters": 0,
        "curriculum_market_gaps": 0,
        "specialization_skill_affinity": 0,
        "curriculum_recommendation_candidates": 0,
    }
    with get_conn() as conn:
        with conn.cursor() as cur:
            if MIGRATION_013.exists():
                cur.execute(MIGRATION_013.read_text(encoding="utf-8"))
            if universe:
                execute_values(
                    cur,
                    """
                    INSERT INTO labor_market_skill_universe
                        (skill, skill_type, total_weight, evidence_count, source_breakdown, roles, source_urls)
                    VALUES %s
                    ON CONFLICT (skill) DO UPDATE SET
                        skill_type = EXCLUDED.skill_type,
                        total_weight = EXCLUDED.total_weight,
                        evidence_count = EXCLUDED.evidence_count,
                        source_breakdown = EXCLUDED.source_breakdown,
                        roles = EXCLUDED.roles,
                        source_urls = EXCLUDED.source_urls,
                        updated_at = now()
                    """,
                    [
                        (
                            item.skill,
                            item.skill_type,
                            item.total_weight,
                            item.evidence_count,
                            json.dumps(item.source_breakdown, ensure_ascii=False),
                            json.dumps(item.roles, ensure_ascii=False),
                            json.dumps(item.source_urls, ensure_ascii=False),
                        )
                        for item in universe
                    ],
                )
                counts["labor_market_skill_universe"] = len(universe)
            if clusters:
                execute_values(
                    cur,
                    """
                    INSERT INTO occupational_skill_clusters
                        (cluster_name, skills, total_weight, evidence_count, dominant_sources,
                         representative_roles, is_strong_market_signal)
                    VALUES %s
                    ON CONFLICT (cluster_name) DO UPDATE SET
                        skills = EXCLUDED.skills,
                        total_weight = EXCLUDED.total_weight,
                        evidence_count = EXCLUDED.evidence_count,
                        dominant_sources = EXCLUDED.dominant_sources,
                        representative_roles = EXCLUDED.representative_roles,
                        is_strong_market_signal = EXCLUDED.is_strong_market_signal,
                        updated_at = now()
                    """,
                    [
                        (
                            item.cluster_name,
                            json.dumps(item.skills, ensure_ascii=False),
                            item.total_weight,
                            item.evidence_count,
                            json.dumps(item.dominant_sources, ensure_ascii=False),
                            json.dumps(item.representative_roles, ensure_ascii=False),
                            item.is_strong_market_signal,
                        )
                        for item in clusters
                    ],
                )
                counts["occupational_skill_clusters"] = len(clusters)
            graph_payload = {
                "covered": [asdict(item) for item in gap_map.covered_skills],
                "partial": [asdict(item) for item in gap_map.partial_skills],
                "missing": [asdict(item) for item in gap_map.missing_skills],
                "emerging": [asdict(item) for item in gap_map.emerging_skills],
            }
            cur.execute(
                """
                INSERT INTO specialization_curriculum_graph
                    (specialization_id, specialization_name, source_root, documents_processed, skills, profile_concepts, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (specialization_id) DO UPDATE SET
                    specialization_name = EXCLUDED.specialization_name,
                    source_root = EXCLUDED.source_root,
                    documents_processed = EXCLUDED.documents_processed,
                    skills = EXCLUDED.skills,
                    profile_concepts = EXCLUDED.profile_concepts,
                    updated_at = now()
                """,
                (
                    gap_map.specialization_id,
                    gap_map.specialization_name,
                    str(ROOT_DIR / "storage" / "test_microcurriculos" / "especialización en visual analytics y big data"),
                    0,
                    json.dumps(graph_payload, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                ),
            )
            gap_items = [*gap_map.covered_skills, *gap_map.partial_skills, *gap_map.missing_skills, *gap_map.emerging_skills, *gap_map.irrelevant_skills]
            if gap_items:
                execute_values(
                    cur,
                    """
                    INSERT INTO specialization_skill_affinity
                        (specialization_id, skill, cluster_name, affinity_score, coverage_status,
                         matched_curriculum_skill, reason)
                    VALUES %s
                    ON CONFLICT (specialization_id, skill) DO UPDATE SET
                        cluster_name = EXCLUDED.cluster_name,
                        affinity_score = EXCLUDED.affinity_score,
                        coverage_status = EXCLUDED.coverage_status,
                        matched_curriculum_skill = EXCLUDED.matched_curriculum_skill,
                        reason = EXCLUDED.reason,
                        updated_at = now()
                    """,
                    [
                        (
                            gap_map.specialization_id,
                            item.skill,
                            item.cluster_name,
                            item.affinity_score,
                            item.coverage_status,
                            item.matched_curriculum_skill,
                            item.reason,
                        )
                        for item in gap_items
                    ],
                )
                counts["specialization_skill_affinity"] = len(gap_items)
                execute_values(
                    cur,
                    """
                    INSERT INTO curriculum_market_gaps
                        (specialization_id, skill, cluster_name, coverage_status, evidence_weight,
                         evidence_sources, affinity_score, roles, recommendation)
                    VALUES %s
                    ON CONFLICT (specialization_id, skill) DO UPDATE SET
                        cluster_name = EXCLUDED.cluster_name,
                        coverage_status = EXCLUDED.coverage_status,
                        evidence_weight = EXCLUDED.evidence_weight,
                        evidence_sources = EXCLUDED.evidence_sources,
                        affinity_score = EXCLUDED.affinity_score,
                        roles = EXCLUDED.roles,
                        recommendation = EXCLUDED.recommendation,
                        updated_at = now()
                    """,
                    [
                        (
                            gap_map.specialization_id,
                            item.skill,
                            item.cluster_name,
                            item.coverage_status,
                            item.evidence_weight,
                            json.dumps(item.evidence_sources, ensure_ascii=False),
                            item.affinity_score,
                            json.dumps(item.roles, ensure_ascii=False),
                            item.recommendation,
                        )
                        for item in gap_items
                    ],
                )
                counts["curriculum_market_gaps"] = len(gap_items)
            updates = gap_map.recommended_curriculum_updates
            if updates:
                execute_values(
                    cur,
                    """
                    INSERT INTO curriculum_recommendation_candidates
                        (specialization_id, skill, cluster_name, priority, action, evidence_weight, roles)
                    VALUES %s
                    """,
                    [
                        (
                            gap_map.specialization_id,
                            item["skill"],
                            item["cluster_name"],
                            item["priority"],
                            item["action"],
                            item["evidence_weight"],
                            json.dumps(item.get("roles", []), ensure_ascii=False),
                        )
                        for item in updates
                    ],
                )
                counts["curriculum_recommendation_candidates"] = len(updates)
        conn.commit()
    return counts


def _table_counts() -> dict[str, Any]:
    load_environment()
    tables = [
        "bronze_empleos_raw",
        "silver_empleos_normalized",
        "gold_empleos_analytics",
        "labor_market_skill_universe",
        "occupational_skill_clusters",
        "curriculum_market_gaps",
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            result = {}
            for table in tables:
                try:
                    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", (table,))
                    exists_row = cur.fetchone()
                    exists = bool(exists_row["exists"] if isinstance(exists_row, dict) else exists_row[0])
                    if not exists:
                        result[table] = "missing"
                        continue
                    cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
                    row = cur.fetchone()
                    result[table] = int(row["count"] if isinstance(row, dict) else row[0])
                except Exception as exc:
                    result[table] = f"error: {exc}"
                    conn.rollback()
            return result


def run_pipeline(
    *,
    sources: list[str],
    execute_network: bool,
    max_jobs: int,
    max_pages: int,
    quality_review: bool = False,
) -> dict[str, Any]:
    discovery = run_api_discovery(sources=sources, execute_network=execute_network)
    extraction = run_enterprise_extraction(sources=sources, execute_network=execute_network, max_jobs=max_jobs, max_pages=max_pages)
    persistence: dict[str, Any] = {"enabled": False}
    if execute_network:
        results = load_results_from_json(EXTRACTION_JSON)
        try:
            persistence = {"enabled": True, **persist_layers(results, persist_gold=True)}
        except Exception as exc:
            persistence = {"enabled": True, "error": str(exc)}
    universe = build_labor_market_skill_universe(include_database=execute_network, write_output=True)
    clusters = build_occupational_skill_clusters(universe, write_output=True)
    gap_map = build_curriculum_market_gap_map(universe=universe, write_output=True)
    market_persistence: dict[str, Any] = {"enabled": False}
    if execute_network:
        try:
            market_persistence = {"enabled": True, **_persist_market_intelligence(universe, clusters, gap_map)}
        except Exception as exc:
            market_persistence = {"enabled": True, "error": str(exc)}
    _copy_report(OUTPUT_DIR / "job_extraction_quality_report.md", "live_job_extraction_report.md")
    _copy_report(OUTPUT_DIR / "visual_analytics_curriculum_market_gap_map.md", "live_curriculum_gap_report.md")
    _copy_report(OUTPUT_DIR / "occupational_skill_clusters.json", "live_occupational_clusters_report.json")
    _copy_report(OUTPUT_DIR / "labor_market_skill_universe.json", "live_skill_universe_report.json")
    counts = {}
    if execute_network:
        try:
            counts = _table_counts()
        except Exception as exc:
            counts = {"error": str(exc)}
    return {
        "api_discovery": discovery,
        "extraction": extraction,
        "quality_review": quality_review,
        "persistence": persistence,
        "market_persistence": market_persistence,
        "skill_universe": len(universe),
        "occupational_clusters": len(clusters),
        "covered_skills": len(gap_map.covered_skills),
        "missing_skills": len(gap_map.missing_skills),
        "emerging_skills": len(gap_map.emerging_skills),
        "postgres_counts": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run enterprise job intelligence lake pipeline.")
    parser.add_argument("--sources", nargs="*", default=["ticjob", "elempleo"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-network", action="store_true")
    parser.add_argument("--quality-review", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=2)
    args = parser.parse_args()
    execute_network = bool(args.execute_network and not args.dry_run)
    print(
        json.dumps(
            run_pipeline(
                sources=args.sources,
                execute_network=execute_network,
                max_jobs=args.max_jobs,
                max_pages=args.max_pages,
                quality_review=args.quality_review,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
