from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
        cursor_factory=RealDictCursor,
    )


def apply_schema() -> None:
    schema = ROOT_DIR / "database" / "enterprise_labor_intelligence_schema.sql"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(schema.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class SourceReliabilitySnapshot:
    source: str
    reliability_score: float
    success_rate: float
    blocked_auth_rate: float
    timeout_rate: float
    duplication_rate: float
    evidence_quality: float
    semantic_density: float
    extraction_completeness: float
    source_stability: float
    raw_runs: int
    raw_jobs: int
    silver_jobs: int
    gold_jobs: int


def list_sources() -> list[str]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT source FROM public.extraction_runs
            UNION
            SELECT source FROM public.source_quality_metrics
            UNION
            SELECT source FROM public.api_sources_registry
            UNION
            SELECT source FROM public.silver_normalized_jobs
            ORDER BY source
            """
        )
        return [row["source"] for row in cur.fetchall()]


def _quality_metrics(source: str) -> dict[str, float]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE(AVG(success_rate), 0)::float AS success_rate,
                COALESCE(AVG(timeout_rate), 0)::float AS timeout_rate,
                COALESCE(AVG(duplication_rate), 0)::float AS duplication_rate,
                COALESCE(SUM(raw_jobs), 0)::int AS raw_jobs,
                COALESCE(SUM(normalized_jobs), 0)::int AS normalized_jobs
            FROM public.source_quality_metrics
            WHERE source = %s
            """,
            (source,),
        )
        return dict(cur.fetchone() or {})


def _run_metrics(source: str) -> dict[str, float]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*)::int AS runs,
                COUNT(*) FILTER (WHERE status IN ('completed', 'success'))::int AS completed_runs,
                COUNT(*) FILTER (WHERE status = 'blocked_auth')::int AS blocked_auth_runs,
                COALESCE(SUM(raw_count), 0)::int AS raw_jobs,
                COALESCE(SUM(silver_count), 0)::int AS silver_jobs,
                COALESCE(SUM(gold_count), 0)::int AS gold_jobs,
                COALESCE(SUM(error_count), 0)::int AS errors
            FROM public.extraction_runs
            WHERE source = %s
            """,
            (source,),
        )
        return dict(cur.fetchone() or {})


def _evidence_metrics(source: str) -> dict[str, float]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE(AVG(rs.overall_score), AVG(sj.confidence_score), 0)::float AS evidence_quality,
                COALESCE(AVG(rs.semantic_density), 0)::float AS semantic_density,
                COUNT(sj.id)::int AS silver_jobs,
                COUNT(sj.id) FILTER (
                    WHERE sj.titulo IS NOT NULL
                      AND sj.empresa IS NOT NULL
                      AND sj.descripcion IS NOT NULL
                      AND jsonb_array_length(COALESCE(sj.skills, '[]'::jsonb)) > 0
                )::int AS complete_jobs
            FROM public.silver_normalized_jobs sj
            LEFT JOIN public.relevance_scores rs ON rs.job_id = sj.id
            WHERE sj.source = %s
            """,
            (source,),
        )
        return dict(cur.fetchone() or {})


def compute_reliability(source: str) -> SourceReliabilitySnapshot:
    quality = _quality_metrics(source)
    runs = _run_metrics(source)
    evidence = _evidence_metrics(source)
    raw_runs = int(runs.get("runs") or 0)
    completed_runs = int(runs.get("completed_runs") or 0)
    blocked_auth_runs = int(runs.get("blocked_auth_runs") or 0)
    success_rate = float(quality.get("success_rate") or 0)
    if raw_runs and not success_rate:
        success_rate = completed_runs / raw_runs
    blocked_auth_rate = blocked_auth_runs / raw_runs if raw_runs else 0.0
    timeout_rate = float(quality.get("timeout_rate") or 0)
    duplication_rate = float(quality.get("duplication_rate") or 0)
    semantic_density = float(evidence.get("semantic_density") or 0)
    evidence_quality = float(evidence.get("evidence_quality") or 0)
    silver_jobs = int(evidence.get("silver_jobs") or runs.get("silver_jobs") or 0)
    complete_jobs = int(evidence.get("complete_jobs") or 0)
    extraction_completeness = complete_jobs / silver_jobs if silver_jobs else 0.0
    error_count = int(runs.get("errors") or 0)
    source_stability = 1.0 - (error_count / max(1, raw_runs + error_count))
    reliability = (
        clamp(success_rate) * 0.22
        + (1 - clamp(blocked_auth_rate)) * 0.18
        + (1 - clamp(timeout_rate)) * 0.10
        + (1 - clamp(duplication_rate)) * 0.08
        + clamp(evidence_quality) * 0.18
        + clamp(semantic_density) * 0.12
        + clamp(extraction_completeness) * 0.12
    )
    return SourceReliabilitySnapshot(
        source=source,
        reliability_score=clamp(reliability),
        success_rate=clamp(success_rate),
        blocked_auth_rate=clamp(blocked_auth_rate),
        timeout_rate=clamp(timeout_rate),
        duplication_rate=clamp(duplication_rate),
        evidence_quality=clamp(evidence_quality),
        semantic_density=clamp(semantic_density),
        extraction_completeness=clamp(extraction_completeness),
        source_stability=clamp(source_stability),
        raw_runs=raw_runs,
        raw_jobs=int(runs.get("raw_jobs") or quality.get("raw_jobs") or 0),
        silver_jobs=silver_jobs,
        gold_jobs=int(runs.get("gold_jobs") or 0),
    )


def classify_source_tier(snapshot: SourceReliabilitySnapshot, gold_readiness: bool) -> str:
    if gold_readiness and snapshot.reliability_score >= 0.78 and snapshot.blocked_auth_rate <= 0.05:
        return "Gold"
    if snapshot.reliability_score >= 0.62 and snapshot.evidence_quality >= 0.55:
        return "Silver"
    if snapshot.reliability_score >= 0.40 or snapshot.silver_jobs > 0:
        return "Bronze"
    return "Experimental"


def snapshot_to_dict(snapshot: SourceReliabilitySnapshot) -> dict[str, Any]:
    return snapshot.__dict__.copy()
