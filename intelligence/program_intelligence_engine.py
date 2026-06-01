from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
import json
from typing import Any

from psycopg2.extras import Json, execute_values

from backend.db import get_conn
from backend.repositories import microcurriculum_context_repository
from backend.repositories import matches_repository, programas_repository
from backend.repositories.base import fetch_all, relation_exists
from backend.services import dashboard_service
from intelligence.domain_benchmark_layer import build_domain_benchmark
from intelligence.domain_taxonomy_layer import build_domain_taxonomy_from_program
from intelligence.common import clamp, normalize_key


OBSERVATORY_SOURCE_TABLES = (
    "curriculum_gap_observatory",
    "recommendation_observatory",
    "market_forecasts",
    "semantic_role_graph",
    "emerging_technology_observatory",
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return []


def _unique(sequence: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in sequence:
        key = normalize_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _program_canonical_key(program: dict[str, Any]) -> str:
    program_name = str(program.get("nombre_especializacion") or program.get("nombre") or "").strip()
    program_id = str(program.get("especializacion_id") or program.get("id") or "").strip()
    canonical_name = normalize_key(program_name)
    if canonical_name:
        return canonical_name
    return f"id {program_id}" if program_id else ""


def _program_quality_score(program: dict[str, Any]) -> tuple[int, int, int, int, int]:
    has_source = 1 if (str(program.get("source_url") or "").strip() or str(program.get("plan_estudios") or "").strip()) else 0
    total_skills = int(program.get("total_skills_programa") or 0)
    has_role = 1 if str(program.get("rol") or "").strip() else 0
    capitalized = 1 if str(program.get("nombre_especializacion") or program.get("nombre") or "").strip().startswith(tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑ")) else 0
    program_id = int(program.get("especializacion_id") or program.get("id") or 0)
    return has_source, total_skills, has_role, capitalized, -program_id


def _dedupe_program_rows(programs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for program in programs:
        key = _program_canonical_key(program)
        if not key:
            key = f"id {int(program.get('especializacion_id') or program.get('id') or 0)}"
        current = grouped.get(key)
        if current is None or _program_quality_score(program) > _program_quality_score(current):
            grouped[key] = program
    ordered = sorted(
        grouped.values(),
        key=lambda item: (
            normalize_key(str(item.get("nombre_especializacion") or item.get("nombre") or "")),
            int(item.get("especializacion_id") or item.get("id") or 0),
        ),
    )
    return ordered


def _tokenize_program(program_name: str, program_role: str, extra_terms: list[str] | None = None) -> list[str]:
    raw_tokens = [program_name, program_role]
    if extra_terms:
        raw_tokens.extend(extra_terms)
    tokens: list[str] = []
    for raw in raw_tokens:
        normalized = normalize_key(raw)
        if not normalized:
            continue
        tokens.extend([segment for segment in normalized.split() if len(segment) >= 3])
    return _unique(tokens)


def _matches_text(text: str, tokens: list[str]) -> bool:
    normalized_text = normalize_key(text)
    if not normalized_text:
        return False
    return any(token in normalized_text for token in tokens)


def _program_rows(db_name: str | None = None) -> list[dict[str, Any]]:
    rows = dashboard_service.list_programs_base(db_name=db_name)
    if rows:
        return rows
    return programas_repository.fetch_fallback_program_rows(db_name=db_name)


def _program_skill_rows(program_id: int, db_name: str | None = None) -> list[dict[str, Any]]:
    try:
        rows = programas_repository.fetch_program_skill_rows(program_id, db_name=db_name)
    except Exception:
        return []
    normalized = dashboard_service.normalize_skill_rows(rows)
    return normalized


def _fetch_observatory_rows(db_name: str | None = None) -> dict[str, list[dict[str, Any]]]:
    payload: dict[str, list[dict[str, Any]]] = {table: [] for table in OBSERVATORY_SOURCE_TABLES}
    if relation_exists("curriculum_gap_observatory", db_name=db_name):
        payload["curriculum_gap_observatory"] = fetch_all(
            """
            SELECT specialization, missing_skill, market_demand_score, curriculum_coverage_score,
                   urgency_score, emergence_score, recommendation, evidence, generated_at
            FROM curriculum_gap_observatory
            ORDER BY urgency_score DESC NULLS LAST, market_demand_score DESC NULLS LAST
            """,
            db_name=db_name,
        )
    if relation_exists("recommendation_observatory", db_name=db_name):
        payload["recommendation_observatory"] = fetch_all(
            """
            SELECT recommendation_type, target_role, target_company, recommendation_payload,
                   recommendation_reasoning, recommendation_confidence, recommendation_evidence,
                   metric_period, generated_at
            FROM recommendation_observatory
            ORDER BY recommendation_confidence DESC NULLS LAST, generated_at DESC NULLS LAST
            """,
            db_name=db_name,
        )
    if relation_exists("market_forecasts", db_name=db_name):
        horizon_exists = False
        try:
            horizon_exists = bool(
                fetch_all(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'market_forecasts'
                      AND column_name = 'horizon_months'
                    LIMIT 1
                    """,
                    db_name=db_name,
                )
            )
        except Exception:
            horizon_exists = False
        select_columns = (
            "entity_type, entity_name, horizon_months, growth_velocity, forecast_confidence, market_phase, first_seen_at, last_seen_at, evidence"
            if horizon_exists
            else "entity_type, entity_name, growth_velocity, forecast_confidence, market_phase, first_seen_at, last_seen_at, evidence"
        )
        payload["market_forecasts"] = fetch_all(
            f"""
            SELECT {select_columns}
            FROM market_forecasts
            ORDER BY growth_velocity DESC NULLS LAST, forecast_confidence DESC NULLS LAST
            """,
            db_name=db_name,
        )
        if not horizon_exists:
            for row in payload["market_forecasts"]:
                row["horizon_months"] = 12
    if relation_exists("semantic_role_graph", db_name=db_name):
        payload["semantic_role_graph"] = fetch_all(
            """
            SELECT source_role, target_role, similarity_score, transition_probability,
                   shared_skills, cluster_affinity, centrality_score, evidence, metric_period
            FROM semantic_role_graph
            ORDER BY similarity_score DESC NULLS LAST, centrality_score DESC NULLS LAST
            """,
            db_name=db_name,
        )
    if relation_exists("emerging_technology_observatory", db_name=db_name):
        payload["emerging_technology_observatory"] = fetch_all(
            """
            SELECT technology, emergence_score, growth_velocity, adoption_trend,
                   forecast_confidence, source_payload, metric_period
            FROM emerging_technology_observatory
            ORDER BY emergence_score DESC NULLS LAST, growth_velocity DESC NULLS LAST
            """,
            db_name=db_name,
        )
    return payload


@dataclass(frozen=True)
class ProgramIntelligenceItem:
    program_id: int
    program_name: str
    program_role: str
    alignment_score: float
    risk_score: float
    risk_level: str
    gap_count: int
    top_gaps: list[dict[str, Any]]
    top_recommendations: list[dict[str, Any]]
    forecast_signals: list[dict[str, Any]]
    role_signals: list[dict[str, Any]]
    emerging_technologies: list[dict[str, Any]]
    recommended_actions: list[str]
    business_justification: str
    supporting_evidence: dict[str, Any]
    source_tables: list[str]
    confidence: float
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _risk_level(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "moderate"
    return "low"


def _pick_top(rows: list[dict[str, Any]], key: str, limit: int = 5) -> list[dict[str, Any]]:
    return rows[:limit] if key else rows[:limit]


def _program_view_rows(db_name: str | None = None) -> list[dict[str, Any]]:
    rows = _program_rows(db_name=db_name)
    normalized = [dashboard_service.normalize_program_row(row) for row in rows]
    return _dedupe_program_rows(normalized)


def _program_microcurriculum_context(program: dict[str, Any], db_name: str | None = None) -> dict[str, Any]:
    program_id = int(program.get("especializacion_id") or program.get("id") or 0)
    if not program_id:
        return {}
    program_name = str(program.get("nombre_especializacion") or program.get("nombre") or "").strip()
    try:
        context = microcurriculum_context_repository.fetch_program_context(
            program_id,
            specialization_name=program_name,
            db_name=db_name,
        )
    except Exception:
        return {}
    return dict(context) if context else {}


def _context_terms(program_context: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    terms.extend(_as_list(program_context.get("technical_skills")))
    terms.extend(_as_list(program_context.get("transversal_skills")))
    terms.extend(_as_list(program_context.get("methodologies")))
    terms.extend(_as_list(program_context.get("tools")))
    terms.extend(_as_list(program_context.get("platforms")))
    terms.extend(_as_list(program_context.get("technologies")))
    terms.extend(_as_list(program_context.get("keywords")))
    terms.extend(_as_list(program_context.get("labor_roles")))
    terms.extend(_as_list(program_context.get("occupational_profiles")))
    terms.extend(_as_list(program_context.get("strengthening_areas")))
    terms.extend(_as_list(program_context.get("real_market_gaps")))
    subjects = program_context.get("subjects") or []
    if isinstance(subjects, dict):
        subjects = [subjects]
    if not isinstance(subjects, list):
        subjects = []
    for subject in subjects:
        if isinstance(subject, dict):
            terms.extend(_as_list(subject.get("competencias")))
            terms.extend(_as_list(subject.get("resultados_aprendizaje")))
            terms.extend(_as_list(subject.get("contenidos")))
            terms.extend(_as_list(subject.get("metodologias")))
            terms.extend(_as_list(subject.get("herramientas")))
    return _unique([str(term) for term in terms if str(term).strip()])


def _row_match_score(text: str, curriculum_terms: set[str], benchmark_terms: set[str], labor_terms: set[str]) -> int:
    normalized = normalize_key(text)
    if not normalized:
        return 0
    score = 0
    if any(term in normalized for term in curriculum_terms):
        score += 3
    if any(term in normalized for term in benchmark_terms):
        score += 2
    if any(term in normalized for term in labor_terms):
        score += 1
    return score


def _match_rows_for_program(
    program: dict[str, Any],
    observatory: dict[str, list[dict[str, Any]]],
    *,
    program_context: dict[str, Any] | None = None,
    domain_benchmark: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    program_name = str(program.get("nombre_especializacion") or program.get("nombre") or "").strip()
    program_role = str(program.get("rol") or "").strip()
    context_terms = _context_terms(program_context or {})
    benchmark_terms = list(domain_benchmark.get("comparison_terms") or []) if domain_benchmark else []
    if domain_benchmark:
        benchmark_terms.extend(list(domain_benchmark.get("priority_skills") or []))
        benchmark_terms.extend(list(domain_benchmark.get("core_competencies") or []))
        benchmark_terms.extend(list(domain_benchmark.get("market_skills") or []))
        benchmark_terms.extend([str(item.get("institution") or "") for item in domain_benchmark.get("benchmark_institutions") or []])
        benchmark_terms.extend(list(domain_benchmark.get("occupational_profile") or []))
    tokens = _tokenize_program(program_name, program_role, benchmark_terms + context_terms)
    skill_rows = _program_skill_rows(int(program.get("especializacion_id") or program.get("id") or 0))
    skill_names = [str(row.get("nombre") or "").strip() for row in skill_rows if str(row.get("nombre") or "").strip()]
    curriculum_terms = {normalize_key(term) for term in context_terms if normalize_key(term)}
    benchmark_term_set = {normalize_key(term) for term in benchmark_terms if normalize_key(term)}
    labor_term_set = {
        *{normalize_key(skill) for skill in skill_names if normalize_key(skill)},
        *{normalize_key(term) for term in _as_list(program_context.get("labor_roles")) if normalize_key(term)},
    } if program_context else {normalize_key(skill) for skill in skill_names if normalize_key(skill)}
    gap_rows = observatory["curriculum_gap_observatory"]
    recommendation_rows = observatory["recommendation_observatory"]
    forecast_rows = observatory["market_forecasts"]
    role_rows = observatory["semantic_role_graph"]
    emerging_rows = observatory["emerging_technology_observatory"]

    scored_gaps = []
    for row in gap_rows:
        score = _row_match_score(
            " ".join(
                [
                    str(row.get("specialization") or ""),
                    str(row.get("missing_skill") or ""),
                    str(row.get("recommendation") or ""),
                    str(row.get("evidence") or ""),
                ]
            ),
            curriculum_terms,
            benchmark_term_set,
            labor_term_set,
        )
        if any(normalize_key(skill) == normalize_key(row.get("missing_skill") or "") for skill in skill_names):
            score += 2
        if score:
            scored_gaps.append((score, row))
    scored_gaps.sort(key=lambda item: (item[0], _safe_float(item[1].get("urgency_score"))), reverse=True)
    matched_gaps = [row for _score, row in scored_gaps]
    if not matched_gaps and gap_rows:
        matched_gaps = gap_rows[:5]

    missing_skill_names = [str(row.get("missing_skill") or "").strip() for row in matched_gaps if str(row.get("missing_skill") or "").strip()]

    matched_recommendations = []
    for row in recommendation_rows:
        payload = row.get("recommendation_payload") or {}
        payload_skills = _as_list(payload.get("recommended_skills"))
        reason_text = " ".join(
            [
                str(row.get("target_role") or ""),
                str(row.get("target_company") or ""),
                str(row.get("recommendation_reasoning") or ""),
                " ".join(payload_skills),
            ]
        )
        score = _row_match_score(reason_text, curriculum_terms, benchmark_term_set, labor_term_set)
        if any(normalize_key(skill) in {normalize_key(item) for item in skill_names + missing_skill_names} for skill in payload_skills):
            score += 2
        if score:
            matched_recommendations.append((score, row))
    matched_recommendations.sort(key=lambda item: (item[0], _safe_float(item[1].get("recommendation_confidence"))), reverse=True)
    matched_recommendations = [row for _score, row in matched_recommendations]
    if not matched_recommendations and recommendation_rows:
        matched_recommendations = recommendation_rows[:5]

    matched_forecasts = []
    skill_focus = {normalize_key(item) for item in skill_names + missing_skill_names}
    for row in forecast_rows:
        entity_name = str(row.get("entity_name") or "")
        score = _row_match_score(entity_name + " " + str(row.get("entity_type") or ""), curriculum_terms, benchmark_term_set, labor_term_set)
        if normalize_key(entity_name) in skill_focus:
            score += 2
        if score:
            matched_forecasts.append((score, row))
    matched_forecasts.sort(key=lambda item: (item[0], _safe_float(item[1].get("growth_velocity"))), reverse=True)
    matched_forecasts = [row for _score, row in matched_forecasts]
    if not matched_forecasts and forecast_rows:
        matched_forecasts = forecast_rows[:5]

    matched_roles = []
    for row in role_rows:
        score = _row_match_score(
            f"{row.get('source_role') or ''} {row.get('target_role') or ''} {row.get('cluster_affinity') or ''}",
            curriculum_terms,
            benchmark_term_set,
            labor_term_set,
        )
        if score:
            matched_roles.append((score, row))
    matched_roles.sort(key=lambda item: (item[0], _safe_float(item[1].get("similarity_score"))), reverse=True)
    matched_roles = [row for _score, row in matched_roles]
    if not matched_roles and role_rows:
        matched_roles = role_rows[:5]

    matched_emerging = []
    for row in emerging_rows:
        score = _row_match_score(
            str(row.get("technology") or ""),
            curriculum_terms,
            benchmark_term_set,
            labor_term_set,
        )
        if normalize_key(str(row.get("technology") or "")) in skill_focus:
            score += 2
        if score:
            matched_emerging.append((score, row))
    matched_emerging.sort(key=lambda item: (item[0], _safe_float(item[1].get("growth_velocity"))), reverse=True)
    matched_emerging = [row for _score, row in matched_emerging]
    if not matched_emerging and emerging_rows:
        matched_emerging = emerging_rows[:5]

    return {
        "skill_rows": skill_rows,
        "gap_rows": matched_gaps,
        "recommendation_rows": matched_recommendations,
        "forecast_rows": matched_forecasts,
        "role_rows": matched_roles,
        "emerging_rows": matched_emerging,
    }


def _build_item(program: dict[str, Any], observatory: dict[str, list[dict[str, Any]]]) -> ProgramIntelligenceItem:
    program_context = _program_microcurriculum_context(program)
    program_name = str(program.get("nombre_especializacion") or program.get("nombre") or "").strip()
    program_role = str(program.get("rol") or "").strip()
    domain_taxonomy = build_domain_taxonomy_from_program(
        program_name=program_name,
        program_role=program_role,
        microcurriculum_context=program_context,
        skills=list(program_context.get("technical_skills") or []) + list(program_context.get("transversal_skills") or []),
    )
    domain_benchmark = build_domain_benchmark(domain_taxonomy.domain_key)
    matches = _match_rows_for_program(
        program,
        observatory,
        program_context=program_context,
        domain_benchmark=domain_benchmark.to_dict(),
    )
    skill_rows = matches["skill_rows"]
    gap_rows = matches["gap_rows"]
    recommendation_rows = matches["recommendation_rows"]
    forecast_rows = matches["forecast_rows"]
    role_rows = matches["role_rows"]
    emerging_rows = matches["emerging_rows"]

    if domain_taxonomy.domain_key == "criminology":
        context_gap_rows = []

        def _context_gap_row(name: str, priority: str, reason: str, coverage_status: str = "missing") -> dict[str, Any]:
            urgency_score = {
                "alta": 0.93,
                "media": 0.76,
                "baja": 0.58,
            }.get(priority, 0.7)
            market_demand_score = {
                "alta": 0.91,
                "media": 0.78,
                "baja": 0.61,
            }.get(priority, 0.72)
            curriculum_coverage_score = {
                "missing": 0.12,
                "partial": 0.34,
                "covered": 0.56,
            }.get(coverage_status, 0.22)
            emergence_score = {
                "alta": 0.91,
                "media": 0.72,
                "baja": 0.48,
            }.get(priority, 0.6)
            return {
                "missing_skill": name,
                "urgency_score": urgency_score,
                "specialization": program_name,
                "market_demand_score": market_demand_score,
                "curriculum_coverage_score": curriculum_coverage_score,
                "emergence_score": emergence_score,
                "recommendation": reason,
                "evidence": {
                    "source": "microcurriculum_context",
                    "priority": priority or "media",
                    "coverage_status": coverage_status,
                    "benchmark_used": domain_benchmark.reference_program,
                    "domain_confidence": domain_taxonomy.confidence,
                },
            }

        for item in _as_list(program_context.get("real_market_gaps")):
            if not isinstance(item, dict):
                continue
            gap_name = str(item.get("name") or "").strip()
            if not gap_name:
                continue
            priority = str(item.get("priority") or "").strip().casefold() or "media"
            context_gap_rows.append(
                _context_gap_row(
                    gap_name,
                    priority,
                    f"Fortalecer {gap_name} a partir del benchmark de {domain_benchmark.domain_label}.",
                    "missing",
                )
            )

        for item in _as_list(program_context.get("strengthening_areas")):
            if not isinstance(item, dict):
                continue
            gap_name = str(item.get("name") or "").strip()
            if not gap_name:
                continue
            context_gap_rows.append(
                _context_gap_row(
                    gap_name,
                    "media",
                    f"Profundizar la aplicación de {gap_name} dentro del currículo criminológico.",
                    "partial",
                )
            )

        if context_gap_rows:
            gap_rows = sorted(context_gap_rows, key=lambda row: (_safe_float(row.get("urgency_score")), _safe_float(row.get("market_demand_score"))), reverse=True)

        criminology_markers = {
            "criminal",
            "forensic",
            "forensics",
            "victim",
            "victimology",
            "crime",
            "cybercrime",
            "security",
            "public security",
            "public safety",
            "chain of custody",
            "compliance",
            "penitentiary",
            "intelligence",
            "risk analysis",
        }

        def _looks_criminology(text: str) -> bool:
            normalized = normalize_key(text)
            return bool(normalized and any(marker in normalized for marker in criminology_markers))

        if gap_rows:
            recommendation_rows = [
                {
                    "recommendation_type": "domain",
                    "target_role": domain_benchmark.occupational_profile[0] if domain_benchmark.occupational_profile else "Forensic Analyst",
                    "target_company": "market",
                    "recommendation_confidence": 0.9,
                    "recommendation_reasoning": (
                        f"Fortalecer {str(gap_row.get('missing_skill') or '').strip()} "
                        f"porque aparece como brecha observada del programa y conecta con el benchmark de {domain_benchmark.domain_label}."
                    ),
                    "recommendation_payload": {
                        "recommended_skills": [str(gap_row.get("missing_skill") or "").strip()],
                        "evidence": {
                            "gap": gap_row,
                            "benchmark_used": domain_benchmark.reference_program,
                            "domain_confidence": domain_taxonomy.confidence,
                        },
                    },
                }
                for gap_row in gap_rows[:5]
                if str(gap_row.get("missing_skill") or "").strip()
            ]
        else:
            recommendation_rows = []

        role_rows = [
            row for row in role_rows if _looks_criminology(
                f"{row.get('source_role') or ''} {row.get('target_role') or ''} {row.get('cluster_affinity') or ''}"
            )
        ]

        forecast_rows = [row for row in forecast_rows if _looks_criminology(str(row.get("entity_name") or ""))]

        emerging_rows = [row for row in emerging_rows if _looks_criminology(str(row.get("technology") or ""))]

    alignment = _safe_float(program.get("promedio_match_mercado") or program.get("porcentaje_match") or 0.0)
    coverage = clamp(alignment / 100.0)
    gap_pressure = clamp((sum(_safe_float(row.get("urgency_score")) for row in gap_rows) / max(len(gap_rows), 1)) / 100.0)
    forecast_pressure = clamp(max((_safe_float(row.get("growth_velocity")) for row in forecast_rows), default=0.0))
    emerging_pressure = clamp(max((_safe_float(row.get("emergence_score")) for row in emerging_rows), default=0.0))
    role_pressure = clamp(max((_safe_float(row.get("similarity_score")) for row in role_rows), default=0.0))

    weights = domain_benchmark.analysis_weights or {"coverage": 0.45, "gap": 0.2, "forecast": 0.15, "emerging": 0.1, "role": 0.1}
    risk_score = round(
        clamp(
            ((1.0 - coverage) * float(weights.get("coverage", 0.45)))
            + (gap_pressure * float(weights.get("gap", 0.2)))
            + (forecast_pressure * float(weights.get("forecast", 0.15)))
            + (emerging_pressure * float(weights.get("emerging", 0.1)))
            + ((1.0 - role_pressure) * float(weights.get("role", 0.1)))
        )
        * 100.0,
        2,
    )
    gap_count = len(gap_rows)
    risk_level = _risk_level(risk_score)

    top_gap_names = [str(row.get("missing_skill") or "").strip() for row in gap_rows if str(row.get("missing_skill") or "").strip()]
    top_gap_names = _unique(top_gap_names)
    recommended_actions = []
    if top_gap_names:
        recommended_actions.append(f"Priorizar brechas: {', '.join(top_gap_names[:5])}.")
    if emerging_rows:
        recommended_actions.append(f"Incorporar señales emergentes: {', '.join(_unique([str(row.get('technology') or '').strip() for row in emerging_rows if str(row.get('technology') or '').strip()])[:5])}.")
    if forecast_rows:
        recommended_actions.append("Ajustar resultados de aprendizaje alineando la oferta con la demanda proyectada.")
    if domain_benchmark.core_competencies:
        recommended_actions.append(
            f"Alinear el programa al benchmark de {domain_benchmark.domain_label}: {', '.join(domain_benchmark.core_competencies[:3])}."
        )
    if not recommended_actions:
        recommended_actions.append("Mantener seguimiento de mercado y ampliar evidencia observatory.")

    justification_parts = [
        f"El programa '{program_name}' muestra {alignment:.1f}% de alineación laboral.",
        f"Se identifican {gap_count} brechas relevantes con presión de mercado.",
        f"Taxonomía de dominio detectada: {domain_taxonomy.domain_label} / {domain_taxonomy.subdomain or 'general'}.",
    ]
    if forecast_rows:
        justification_parts.append(f"Hay {len(forecast_rows)} señales de forecast relevantes para skills/roles del programa.")
    if emerging_rows:
        justification_parts.append(f"Se observan {len(emerging_rows)} tecnologías emergentes relacionadas.")
    business_justification = " ".join(justification_parts)

    source_tables = [
        "especializaciones",
        "especializacion_skills",
        "curriculum_gap_observatory",
        "recommendation_observatory",
        "market_forecasts",
        "semantic_role_graph",
        "emerging_technology_observatory",
    ]
    evidence = {
        "program_skills": [str(row.get("nombre") or "").strip() for row in skill_rows if str(row.get("nombre") or "").strip()],
        "gaps": gap_rows[:10],
        "recommendations": recommendation_rows[:10],
        "forecasts": forecast_rows[:10],
        "role_signals": role_rows[:10],
        "emerging_technologies": emerging_rows[:10],
        "domain_taxonomy": domain_taxonomy.to_dict(),
        "domain_benchmark": domain_benchmark.to_dict(),
        "microcurriculum_context": program_context,
        "domain_confidence": domain_taxonomy.confidence,
        "domain_evidence": domain_taxonomy.evidence,
        "benchmark_used": {
            "reference_program": domain_benchmark.reference_program,
            "benchmark_institutions": domain_benchmark.benchmark_institutions[:5],
            "curriculum_structure": domain_benchmark.curriculum_structure[:5],
            "graduate_profile": domain_benchmark.graduate_profile[:5],
            "occupational_profile": domain_benchmark.occupational_profile[:5],
        },
    }
    confidence = round(clamp((coverage + (1.0 - gap_pressure) + max(forecast_pressure, emerging_pressure, role_pressure)) / 3.0), 4)

    return ProgramIntelligenceItem(
        program_id=int(program.get("especializacion_id") or program.get("id") or 0),
        program_name=program_name,
        program_role=program_role,
        alignment_score=round(alignment, 2),
        risk_score=risk_score,
        risk_level=risk_level,
        gap_count=gap_count,
        top_gaps=[{"missing_skill": item, "urgency_score": _safe_float(row.get("urgency_score"))} for item, row in zip(top_gap_names, gap_rows[: len(top_gap_names)])],
        top_recommendations=[
            {
                "recommendation_type": str(row.get("recommendation_type") or ""),
                "target_role": str(row.get("target_role") or ""),
                "target_company": str(row.get("target_company") or ""),
                "recommendation_confidence": _safe_float(row.get("recommendation_confidence")),
                "recommendation_reasoning": str(row.get("recommendation_reasoning") or ""),
            }
            for row in recommendation_rows[:5]
        ],
        forecast_signals=[
            {
                "entity_type": str(row.get("entity_type") or ""),
                "entity_name": str(row.get("entity_name") or ""),
                "horizon_months": int(row.get("horizon_months") or 12),
                "growth_velocity": _safe_float(row.get("growth_velocity")),
                "forecast_confidence": _safe_float(row.get("forecast_confidence")),
                "market_phase": str(row.get("market_phase") or ""),
            }
            for row in forecast_rows[:5]
        ],
        role_signals=[
            {
                "source_role": str(row.get("source_role") or ""),
                "target_role": str(row.get("target_role") or ""),
                "similarity_score": _safe_float(row.get("similarity_score")),
                "transition_probability": _safe_float(row.get("transition_probability")),
                "cluster_affinity": str(row.get("cluster_affinity") or ""),
            }
            for row in role_rows[:5]
        ],
        emerging_technologies=[
            {
                "technology": str(row.get("technology") or ""),
                "emergence_score": _safe_float(row.get("emergence_score")),
                "growth_velocity": _safe_float(row.get("growth_velocity")),
                "adoption_trend": str(row.get("adoption_trend") or ""),
                "forecast_confidence": _safe_float(row.get("forecast_confidence")),
            }
            for row in emerging_rows[:5]
        ],
        recommended_actions=recommended_actions,
        business_justification=business_justification,
        supporting_evidence=evidence,
        source_tables=source_tables,
        confidence=confidence,
        generated_at=datetime.now(UTC).isoformat(),
    )


def build_program_intelligence(program_id: int | None = None, *, db_name: str | None = None) -> list[ProgramIntelligenceItem]:
    observatory = _fetch_observatory_rows(db_name=db_name)
    programs = _program_view_rows(db_name=db_name)
    if program_id is not None:
        programs = [program for program in programs if int(program.get("especializacion_id") or program.get("id") or 0) == int(program_id)]
    items = [_build_item(program, observatory) for program in programs]
    return sorted(items, key=lambda value: (value.risk_score, value.alignment_score), reverse=True)


def build_program_intelligence_for_program(program_id: int, *, db_name: str | None = None) -> ProgramIntelligenceItem:
    items = build_program_intelligence(program_id=program_id, db_name=db_name)
    if not items:
        raise KeyError(f"programa {program_id} not found")
    return items[0]


def persist_program_intelligence(records: list[ProgramIntelligenceItem], *, db_name: str | None = None, replace_existing: bool = False) -> int:
    if not records or not relation_exists("program_intelligence", db_name=db_name):
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            record.program_id,
            normalize_key(record.program_name),
            record.program_name,
            record.program_role,
            record.alignment_score,
            record.risk_score,
            record.risk_level,
            record.gap_count,
            Json(_json_safe(record.top_gaps), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            Json(_json_safe(record.top_recommendations), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            Json(_json_safe(record.forecast_signals), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            Json(_json_safe(record.role_signals), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            Json(_json_safe(record.emerging_technologies), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            Json(_json_safe(record.recommended_actions), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            record.business_justification,
            Json(_json_safe(record.supporting_evidence), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            Json(_json_safe(record.source_tables), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            record.confidence,
            now,
            now,
        )
        for record in records
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            if replace_existing:
                cur.execute("TRUNCATE TABLE program_intelligence")
            execute_values(
                cur,
                """
                INSERT INTO program_intelligence
                    (program_id, canonical_program_key, program_name, program_role, alignment_score, risk_score, risk_level,
                     gap_count, top_gaps, top_recommendations, forecast_signals, role_signals,
                     emerging_technologies, recommended_actions, business_justification,
                     supporting_evidence, source_tables, confidence, generated_at, updated_at)
                VALUES %s
                ON CONFLICT (canonical_program_key) DO UPDATE SET
                    program_id = EXCLUDED.program_id,
                    program_name = EXCLUDED.program_name,
                    program_role = EXCLUDED.program_role,
                    alignment_score = EXCLUDED.alignment_score,
                    risk_score = EXCLUDED.risk_score,
                    risk_level = EXCLUDED.risk_level,
                    gap_count = EXCLUDED.gap_count,
                    top_gaps = EXCLUDED.top_gaps,
                    top_recommendations = EXCLUDED.top_recommendations,
                    forecast_signals = EXCLUDED.forecast_signals,
                    role_signals = EXCLUDED.role_signals,
                    emerging_technologies = EXCLUDED.emerging_technologies,
                    recommended_actions = EXCLUDED.recommended_actions,
                    business_justification = EXCLUDED.business_justification,
                    supporting_evidence = EXCLUDED.supporting_evidence,
                    source_tables = EXCLUDED.source_tables,
                    confidence = EXCLUDED.confidence,
                    updated_at = now()
                """,
                rows,
            )
        conn.commit()
    return len(rows)
