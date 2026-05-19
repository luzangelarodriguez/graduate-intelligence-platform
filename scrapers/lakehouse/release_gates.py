from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass(frozen=True)
class ReleaseGateResult:
    allowed: bool
    precision_rate: float
    confidence_avg: float
    gold_validation: int
    threshold_precision: float
    threshold_confidence: float
    threshold_gold: int
    reason: str


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


def evaluate_release_gates(
    *,
    source: str | None = None,
    precision_threshold: float = 0.70,
    confidence_threshold: float = 0.68,
    gold_threshold: int = 30,
) -> ReleaseGateResult:
    with get_connection() as conn, conn.cursor() as cur:
        if source:
            cur.execute(
                """
                SELECT COALESCE(AVG(overall_score), 0)::float AS confidence_avg
                FROM public.relevance_scores rs
                INNER JOIN public.silver_normalized_jobs sj ON sj.id = rs.job_id
                WHERE sj.source = %s
                """,
                (source,),
            )
        else:
            cur.execute("SELECT COALESCE(AVG(overall_score), 0)::float AS confidence_avg FROM public.relevance_scores")
        confidence_avg = float(cur.fetchone()["confidence_avg"] or 0)

        if source:
            cur.execute(
                """
                SELECT COUNT(*)::int AS total,
                       COUNT(*) FILTER (WHERE gv.validado = true)::int AS valid
                FROM public.gold_validated_jobs gv
                INNER JOIN public.silver_normalized_jobs sj ON sj.id = gv.silver_job_id
                WHERE sj.source = %s
                """,
                (source,),
            )
        else:
            cur.execute(
                """
                SELECT COUNT(*)::int AS total,
                       COUNT(*) FILTER (WHERE validado = true)::int AS valid
                FROM public.gold_validated_jobs
                """
            )
        row = cur.fetchone()
        gold_total = int(row["total"] or 0)
        gold_valid = int(row["valid"] or 0)
        precision_rate = (gold_valid / gold_total) if gold_total else 0.0

    allowed = precision_rate >= precision_threshold and confidence_avg >= confidence_threshold and gold_valid >= gold_threshold
    reason = "release_allowed" if allowed else "blocked_until_precision_confidence_and_gold_thresholds_pass"
    return ReleaseGateResult(
        allowed,
        round(precision_rate, 4),
        round(confidence_avg, 4),
        gold_valid,
        precision_threshold,
        confidence_threshold,
        gold_threshold,
        reason,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate KPI release gates for labor evidence.")
    parser.add_argument("--source", default=None)
    parser.add_argument("--precision-threshold", type=float, default=0.70)
    parser.add_argument("--confidence-threshold", type=float, default=0.68)
    parser.add_argument("--gold-threshold", type=int, default=30)
    args = parser.parse_args()
    result = evaluate_release_gates(
        source=args.source,
        precision_threshold=args.precision_threshold,
        confidence_threshold=args.confidence_threshold,
        gold_threshold=args.gold_threshold,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

