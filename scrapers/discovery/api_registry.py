from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

try:
    from scrapers.discovery.anti_seo_filter import is_seo_noise
    from scrapers.discovery.endpoint_ranker import rank_endpoint
    from scrapers.discovery.graphql_detector import is_graphql_endpoint
except ModuleNotFoundError:
    from anti_seo_filter import is_seo_noise
    from endpoint_ranker import rank_endpoint
    from graphql_detector import is_graphql_endpoint


@dataclass(frozen=True)
class ApiEndpointCandidate:
    source: str
    endpoint: str
    method: str = "GET"
    response_type: str = ""
    status: int | None = None
    resource_type: str = ""
    payload_sample: Any | None = None
    request_headers: dict[str, Any] | None = None
    request_payload: Any | None = None
    duration_ms: int | None = None


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def apply_schema() -> None:
    schema = Path(__file__).resolve().parents[2] / "database" / "enterprise_labor_intelligence_schema.sql"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(schema.read_text(encoding="utf-8"))


def create_discovery_run(run_id: str, *, source: str | None, mode: str, metadata: dict[str, Any] | None = None) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.api_discovery_runs (run_id, source, mode, status, metadata)
            VALUES (%s, %s, %s, 'started', %s)
            ON CONFLICT (run_id) DO NOTHING
            """,
            (run_id, source, mode, Json(metadata or {})),
        )


def finish_discovery_run(run_id: str, *, endpoints_found: int, errors: int = 0, status: str = "completed") -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.api_discovery_runs
            SET status = %s, finished_at = now(), endpoints_found = %s, errors = %s
            WHERE run_id = %s
            """,
            (status, endpoints_found, errors, run_id),
        )


def infer_pagination(endpoint: str, payload: Any | None) -> dict[str, Any]:
    low = endpoint.casefold()
    keys = []
    for key in ("page", "per_page", "page_size", "limit", "offset", "cursor", "from", "size"):
        if key in low:
            keys.append(key)
    if isinstance(payload, dict):
        for key in payload.keys():
            if str(key).casefold() in {"page", "pages", "pagination", "total", "next", "cursor"}:
                keys.append(str(key))
    return {"detected": bool(keys), "keys": sorted(set(keys))}


def auth_required(status: int | None, payload: Any | None) -> bool:
    blob = json.dumps(payload, ensure_ascii=False, default=str).casefold() if payload is not None else ""
    return status in {401, 403} or "auth" in blob or "autentic" in blob or "token" in blob


def register_candidates(candidates: list[ApiEndpointCandidate], *, run_id: str | None = None) -> None:
    if not candidates:
        return
    with get_connection() as conn, conn.cursor() as cur:
        registry_rows = []
        metric_rows = []
        request_rows = []
        for candidate in candidates:
            ranking = rank_endpoint(candidate.endpoint, candidate.payload_sample)
            response_type = candidate.response_type or ("graphql" if is_graphql_endpoint(candidate.endpoint, candidate.payload_sample) else "")
            seo = is_seo_noise(candidate.endpoint, candidate.payload_sample)
            registry_rows.append(
                (
                    candidate.source,
                    candidate.endpoint,
                    candidate.method or "GET",
                    response_type,
                    ranking["rank_score"],
                    seo,
                    auth_required(candidate.status, candidate.payload_sample),
                    Json(infer_pagination(candidate.endpoint, candidate.payload_sample)),
                    ranking["rank_score"],
                    Json(ranking),
                )
            )
            if run_id:
                metric_rows.append(
                    (
                        run_id,
                        candidate.source,
                        candidate.endpoint,
                        ranking["richness"],
                        ranking["freshness"],
                        ranking["semantic_density"],
                        ranking["vacancy_quality"],
                        ranking["extraction_completeness"],
                        ranking["seo_noise"],
                    )
                )
                request_rows.append(
                    (
                        run_id,
                        candidate.source,
                        candidate.endpoint,
                        candidate.method,
                        Json(candidate.request_headers or {}),
                        Json(candidate.request_payload or {}),
                        candidate.status,
                        candidate.resource_type,
                        candidate.duration_ms,
                    )
                )
        execute_values(
            cur,
            """
            INSERT INTO public.api_sources_registry (
                source, endpoint, method, response_type, confidence, seo_noise,
                auth_required, pagination, rank_score, ranking_factors
            )
            VALUES %s
            ON CONFLICT (source, endpoint, method)
            DO UPDATE SET
                response_type = EXCLUDED.response_type,
                confidence = EXCLUDED.confidence,
                seo_noise = EXCLUDED.seo_noise,
                auth_required = EXCLUDED.auth_required,
                pagination = EXCLUDED.pagination,
                rank_score = EXCLUDED.rank_score,
                ranking_factors = EXCLUDED.ranking_factors,
                last_seen_at = now()
            """,
            registry_rows,
        )
        if metric_rows:
            execute_values(
                cur,
                """
                INSERT INTO public.api_extraction_metrics (
                    run_id, source, endpoint, richness, freshness, semantic_density,
                    vacancy_quality, extraction_completeness, seo_noise
                )
                VALUES %s
                ON CONFLICT (run_id, source, endpoint)
                DO UPDATE SET
                    richness = EXCLUDED.richness,
                    freshness = EXCLUDED.freshness,
                    semantic_density = EXCLUDED.semantic_density,
                    vacancy_quality = EXCLUDED.vacancy_quality,
                    extraction_completeness = EXCLUDED.extraction_completeness,
                    seo_noise = EXCLUDED.seo_noise
                """,
                metric_rows,
            )
            execute_values(
                cur,
                """
                INSERT INTO public.api_request_logs (
                    run_id, source, endpoint, method, request_headers, request_payload,
                    status_code, resource_type, duration_ms
                )
                VALUES %s
                """,
                request_rows,
            )


def register_response_snapshots(candidates: list[ApiEndpointCandidate]) -> None:
    rows = []
    for candidate in candidates:
        if candidate.payload_sample is None:
            continue
        rows.append(
            (
                candidate.source,
                candidate.endpoint,
                candidate.response_type,
                Json(candidate.payload_sample),
                stable_hash({"endpoint": candidate.endpoint, "payload": candidate.payload_sample}),
            )
        )
    if not rows:
        return
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.api_response_snapshots (
                source, endpoint, content_type, response_sample, response_hash
            )
            VALUES %s
            ON CONFLICT (response_hash) DO NOTHING
            """,
            rows,
        )


def load_candidates_from_json(path: Path) -> list[ApiEndpointCandidate]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        ApiEndpointCandidate(
            source=item.get("source", ""),
            endpoint=item.get("endpoint") or item.get("url", ""),
            method=item.get("method", "GET"),
            response_type=item.get("response_type") or item.get("content_type", ""),
            status=item.get("status"),
            resource_type=item.get("resource_type", ""),
            payload_sample=item.get("sample") or item.get("payload_sample"),
        )
        for item in data
        if item.get("endpoint") or item.get("url")
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Register discovered API endpoints into PostgreSQL registry.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--run-id", default=f"manual_registry_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    args = parser.parse_args()
    apply_schema()
    candidates = load_candidates_from_json(Path(args.input))
    create_discovery_run(args.run_id, source=None, mode="registry_import", metadata={"input": args.input})
    register_candidates(candidates, run_id=args.run_id)
    register_response_snapshots(candidates)
    finish_discovery_run(args.run_id, endpoints_found=len(candidates))
    print(json.dumps({"registered": len(candidates), "run_id": args.run_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

