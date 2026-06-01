from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from psycopg2.extras import Json, execute_values

from backend.db import get_cursor
from backend.repositories.microcurriculum_context_repository import fetch_program_context
from intelligence.career_path_engine import build_career_paths
from intelligence.curriculum_gap_observatory import build_curriculum_gap_observatory
from intelligence.curriculum_impact_simulator import build_curriculum_impact_simulation
from intelligence.domain_benchmark_layer import build_domain_benchmark
from intelligence.program_intelligence_engine import build_program_intelligence_for_program, persist_program_intelligence
from intelligence.semantic_role_graph_engine import build_semantic_role_graph
from intelligence.semantic_role_intelligence import build_role_intelligence


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _context_source_document(context: dict[str, Any]) -> str:
    subjects = context.get("subjects") or []
    if isinstance(subjects, list):
        for subject in subjects:
            if not isinstance(subject, dict):
                continue
            document = subject.get("document") or {}
            if isinstance(document, dict):
                source_document = str(document.get("source_document") or document.get("stored_path") or "").strip()
                if source_document:
                    return source_document
    return str(context.get("source_document") or "").strip()


def _fetch_actual_gap_rows(source_document: str) -> list[dict[str, Any]]:
    with get_cursor(db_name=None) as cur:
        cur.execute(
            """
            SELECT gap_type, skill_normalized, severity, demand_count, confidence_score, evidence, source_document
            FROM public.microcurriculo_market_gaps
            WHERE source_document = %s
            ORDER BY confidence_score DESC NULLS LAST, demand_count DESC NULLS LAST, skill_normalized ASC
            """,
            (source_document,),
        )
        return [dict(row) for row in cur.fetchall()]


def _build_gap_items(context: dict[str, Any], actual_rows: list[dict[str, Any]]) -> SimpleNamespace:
    occupational_profiles = [str(item).strip() for item in (context.get("occupational_profiles") or []) if str(item).strip()]
    strengthening_areas = context.get("strengthening_areas") or []
    scores = context.get("scores") or {}
    missing_items: list[Any] = []
    partial_items: list[Any] = []

    for row in actual_rows:
        severity = str(row.get("severity") or "").strip().casefold()
        coverage_status = {
            "high": "missing",
            "medium": "partial",
            "low": "covered",
        }.get(severity, "partial")
        missing_items.append(
            SimpleNamespace(
                skill=str(row.get("skill_normalized") or "").strip(),
                cluster_name=str(row.get("gap_type") or "missing_skill"),
                coverage_status=coverage_status,
                evidence_weight=float(row.get("demand_count") or 1),
                affinity_score=float(row.get("confidence_score") or 0.0),
                evidence_sources={
                    "microcurriculo_market_gaps": 1,
                    "source_hint": (row.get("evidence") or {}).get("source"),
                },
                roles=occupational_profiles,
                reason=f"Gap real observado en microcurriculo_market_gaps para {str(row.get('skill_normalized') or '').strip()}.",
                recommendation=f"Fortalecer {str(row.get('skill_normalized') or '').strip()} dentro del currículo criminológico.",
            )
        )

    # Strengthening areas are preserved in the same analytical chain, but only actual table rows are persisted later.
    for area in strengthening_areas:
        if not isinstance(area, dict):
            continue
        name = str(area.get("name") or "").strip()
        if not name:
            continue
        partial_items.append(
            SimpleNamespace(
                skill=name,
                cluster_name="strengthening_area",
                coverage_status="partial",
                evidence_weight=1.0,
                affinity_score=float(scores.get("curricular_relevance") or 0.0) / 100.0 if scores else 0.25,
                evidence_sources={"microcurriculum_context": 1},
                roles=occupational_profiles,
                reason=str(area.get("reason") or f"Área de fortalecimiento detectada para {name}."),
                recommendation=f"Profundizar la aplicación de {name} dentro del currículo criminológico.",
            )
        )

    return SimpleNamespace(
        specialization_name=str(context.get("specialization_name") or "Especialización en Criminología"),
        specialization_id=int(context.get("specialization_id") or 108),
        emerging_skills=[],
        missing_skills=missing_items,
        partial_skills=partial_items,
    )


def _role_skills(title: str, context: dict[str, Any], benchmark: Any) -> list[str]:
    title_key = title.casefold()
    technical = [str(item.get("name") or "").strip() for item in (context.get("technical_skills") or []) if isinstance(item, dict) and str(item.get("name") or "").strip()]
    transversal = [str(item.get("name") or "").strip() for item in (context.get("transversal_skills") or []) if isinstance(item, dict) and str(item.get("name") or "").strip()]
    market = list(getattr(benchmark, "market_skills", []) or [])
    base = _unique([*technical, *transversal, *market[:4]])

    if "cybercrime" in title_key:
        extra = ["cybercrime", "forensic analysis", "chain of custody", "criminal intelligence"]
    elif "forensic" in title_key:
        extra = ["forensic analysis", "chain of custody", "criminal investigation"]
    elif "intelligence" in title_key:
        extra = ["criminal intelligence", "criminal analysis", "risk analysis"]
    elif "compliance" in title_key:
        extra = ["compliance", "criminal policy", "risk analysis"]
    elif "public safety" in title_key:
        extra = ["public security", "crime prevention", "risk analysis"]
    elif "victim" in title_key:
        extra = ["victimology", "crime prevention", "public security"]
    else:
        extra = list(getattr(benchmark, "core_competencies", [])[:4])
    return _unique([*base, *extra])


def _persist_curriculum_gaps(observations: list[Any]) -> int:
    if not observations:
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            row.specialization,
            row.missing_skill,
            row.market_demand_score,
            row.curriculum_coverage_score,
            row.urgency_score,
            row.emergence_score,
            row.recommendation,
            Json(
                {
                    **(row.evidence or {}),
                    "source": "microcurriculo_market_gaps",
                    "quarantine": {"original_source": (row.evidence or {}).get("source")},
                }
            ),
            now,
            now,
        )
        for row in observations
    ]
    with get_cursor(db_name=None) as cur:
        cur.execute(
            """
            DELETE FROM curriculum_gap_observatory
            WHERE specialization ILIKE %s
               OR evidence::text ILIKE %s
               OR evidence::text ILIKE %s
            """,
            ("%Criminolog%", "%visual_analytics_market_context%", "%AI Analytics%"),
        )
        execute_values(
            cur,
            """
            INSERT INTO curriculum_gap_observatory
                (specialization, missing_skill, market_demand_score, curriculum_coverage_score,
                 urgency_score, emergence_score, recommendation, evidence, generated_at, updated_at)
            VALUES %s
            """,
            rows,
        )
    return len(rows)


def _persist_semantic_role_graph(edges: list[Any], metric_period: str) -> int:
    if not edges:
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            edge.source_role,
            edge.target_role,
            edge.similarity_score,
            edge.transition_probability,
            Json(edge.shared_skills),
            edge.cluster_affinity,
            edge.centrality_score,
            Json(edge.evidence),
            metric_period,
            now,
            now,
        )
        for edge in edges
    ]
    role_terms = ["%Criminal%", "%Victim%", "%Forensic%", "%Compliance%", "%Public Safety%", "%Risk%"]
    with get_cursor(db_name=None) as cur:
        cur.execute(
            """
            DELETE FROM semantic_role_graph
            WHERE LOWER(cluster_affinity) = 'criminology'
               OR source_role ILIKE ANY(%s)
               OR target_role ILIKE ANY(%s)
            """,
            (role_terms, role_terms),
        )
        execute_values(
            cur,
            """
            INSERT INTO semantic_role_graph
                (source_role, target_role, similarity_score, transition_probability, shared_skills,
                 cluster_affinity, centrality_score, evidence, metric_period, generated_at, updated_at)
            VALUES %s
            ON CONFLICT (source_role, target_role, metric_period) DO UPDATE SET
                similarity_score = EXCLUDED.similarity_score,
                transition_probability = EXCLUDED.transition_probability,
                shared_skills = EXCLUDED.shared_skills,
                cluster_affinity = EXCLUDED.cluster_affinity,
                centrality_score = EXCLUDED.centrality_score,
                evidence = EXCLUDED.evidence,
                updated_at = EXCLUDED.updated_at
            """,
            rows,
        )
    return len(rows)


def main() -> None:
    metric_period = datetime.now(UTC).strftime("%Y-%m")
    context = fetch_program_context(108, specialization_name="Especialización en Criminología", db_name=None)
    if not context:
        raise RuntimeError("No se encontró el contexto microcurricular para el programa 108.")

    source_document = _context_source_document(context)
    if not source_document:
        raise RuntimeError("El contexto microcurricular no incluye source_document para el programa 108.")

    actual_gap_rows = _fetch_actual_gap_rows(source_document)
    gap_map = _build_gap_items(context, actual_gap_rows)
    observations = build_curriculum_gap_observatory(gap_map=gap_map, metric_period=metric_period, write_output=False)
    persisted_gap_rows = _persist_curriculum_gaps(observations)

    benchmark = build_domain_benchmark("criminology")
    role_titles = [str(item).strip() for item in (context.get("occupational_profiles") or benchmark.occupational_profile or []) if str(item).strip()]
    jobs = [{"title": title, "skills": _role_skills(title, context, benchmark)} for title in role_titles]
    role_signals = build_role_intelligence(jobs)
    career_transitions = build_career_paths(role_signals, list(benchmark.market_skills or []))
    semantic_edges = build_semantic_role_graph(
        jobs=jobs,
        role_signals=role_signals,
        career_transitions=career_transitions,
        metric_period=metric_period,
        write_output=False,
    )
    persisted_role_edges = _persist_semantic_role_graph(semantic_edges, metric_period)

    item = build_program_intelligence_for_program(108)
    persisted_program_intelligence = persist_program_intelligence([item], replace_existing=False)
    simulation = build_curriculum_impact_simulation(
        108,
        proposed_skills=[gap["missing_skill"] for gap in item.top_gaps if str(gap.get("missing_skill") or "").strip()],
        horizon_months=12,
        persist=True,
    ).to_dict()

    print(json.dumps(
        {
            "metric_period": metric_period,
            "microcurriculum_gap_rows": len(actual_gap_rows),
            "persisted_curriculum_gap_rows": persisted_gap_rows,
            "persisted_semantic_role_edges": persisted_role_edges,
            "persisted_program_intelligence": persisted_program_intelligence,
            "program_intelligence": item.to_dict(),
            "simulation": simulation,
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    ))


if __name__ == "__main__":
    main()
