from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from statistics import mean
from typing import Any, Iterable

from backend.repositories import matches_repository, programas_repository, skills_repository
from backend.services import dashboard_service
from backend.repositories.base import cursor, fetch_all, fetch_one, pick_relation, relation_exists
from intelligence.common import clamp, normalize_key
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map


FUTURE_HORIZONS = (3, 6, 12, 24)
SKILL_ENTITY_TYPES = {"skill", "technology"}
ROLE_ENTITY_TYPES = {"role"}
INDUSTRY_ENTITY_TYPES = {"industry"}

TREND_ENTITY_LIMITS = {
    "skill": 40,
    "technology": 25,
    "role": 25,
    "industry": 20,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    try:
        if hasattr(value, "tolist"):
            items = value.tolist()
            if isinstance(items, list):
                return [str(item).strip() for item in items if str(item).strip()]
    except Exception:
        pass
    return []


def _month_key(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m")
    return str(value or "")


def _series_slope(months: list[str], counts: list[int]) -> float:
    if len(counts) < 2:
        return 0.0
    values = [float(count) for count in counts]
    x_values = list(range(len(values)))
    x_mean = mean(x_values)
    y_mean = mean(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
    denominator = sum((x - x_mean) ** 2 for x in x_values) or 1.0
    slope = numerator / denominator
    scale = max(max(values), 1.0)
    return clamp(slope / scale, -1.0, 1.0)


def _projected_growth(base_growth: float, horizon_months: int) -> float:
    horizon_factor = {3: 0.35, 6: 0.60, 12: 1.00, 24: 1.35}.get(horizon_months, 1.0)
    return clamp(base_growth * horizon_factor, -1.0, 1.0)


def _market_phase(growth_velocity: float, count: int) -> str:
    if growth_velocity >= 0.35 and count < 25:
        return "emerging"
    if growth_velocity >= 0.20:
        return "expanding"
    if growth_velocity <= -0.15:
        return "declining"
    return "established"


def _recent_average(points: list[int], window: int) -> float:
    if not points:
        return 0.0
    window = max(1, min(window, len(points)))
    return mean(points[-window:])


def _baseline_average(points: list[int], recent_window: int = 3) -> float:
    if len(points) <= recent_window:
        return mean(points) if points else 0.0
    baseline = points[:-recent_window]
    return mean(baseline) if baseline else 0.0


def _confidence(total_mentions: int, total_companies: int, recent_mentions: int) -> float:
    score = 0.45 + min(total_mentions / 80.0, 0.25) + min(total_companies / 20.0, 0.15) + min(recent_mentions / 15.0, 0.15)
    return round(clamp(score), 4)


def _top_items(counter: Counter[str], limit: int) -> list[str]:
    return [item for item, _count in counter.most_common(limit)]


def _item_text(item: Any, *keys: str) -> str:
    for key in keys:
        if isinstance(item, dict):
            value = item.get(key)
        else:
            value = getattr(item, key, None)
        if value not in {None, ""}:
            return str(value)
    return ""


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value


def _normalize_series(rows: list[dict[str, Any]], *, entity_key: str) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for row in rows:
        entity_name = str(row.get(entity_key) or "").strip()
        if not entity_name:
            continue
        series.append(
            {
                "entity_name": entity_name,
                "month_bucket": _month_key(row.get("month_bucket")),
                "count": int(row.get("count") or 0),
                "company_count": int(row.get("company_count") or 0),
                "avg_probability": _safe_float(row.get("avg_probability")),
                "first_seen_at": row.get("first_seen_at"),
                "last_seen_at": row.get("last_seen_at"),
            }
        )
    return series


def _aggregate_monthly_metrics(series: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in series:
        grouped[row["entity_name"]].append(row)

    metrics: dict[str, dict[str, Any]] = {}
    for entity_name, rows in grouped.items():
        rows = sorted(rows, key=lambda item: item["month_bucket"])
        counts = [int(row["count"]) for row in rows]
        companies = [int(row["company_count"]) for row in rows]
        recent_mentions = int(sum(counts[-3:]))
        previous_mentions = int(sum(counts[:-3])) if len(counts) > 3 else 0
        base_growth = 0.0
        if previous_mentions > 0:
            base_growth = (recent_mentions - previous_mentions / max(len(counts[:-3]), 1) * min(len(counts[-3:]), 3)) / max(previous_mentions, 1)
        elif recent_mentions > 0:
            base_growth = 0.55
        slope = _series_slope([row["month_bucket"] for row in rows], counts)
        growth_velocity = clamp((base_growth * 0.75) + (slope * 0.25), -1.0, 1.0)
        metrics[entity_name] = {
            "rows": rows,
            "counts": counts,
            "companies": companies,
            "total_mentions": sum(counts),
            "total_companies": max(companies) if companies else 0,
            "recent_mentions": recent_mentions,
            "previous_mentions": previous_mentions,
            "growth_velocity": growth_velocity,
            "forecast_confidence": _confidence(sum(counts), max(companies) if companies else 0, recent_mentions),
            "market_phase": _market_phase(growth_velocity, sum(counts)),
            "first_seen_at": min((row.get("first_seen_at") for row in rows if row.get("first_seen_at")), default=None),
            "last_seen_at": max((row.get("last_seen_at") for row in rows if row.get("last_seen_at")), default=None),
            "slope": slope,
        }
    return metrics


@dataclass(frozen=True)
class CurriculumRiskIndex:
    program_id: int
    program_name: str
    risk_score: float
    risk_level: str
    risk_drivers: list[dict[str, Any]]
    recommended_actions: list[str]
    supporting_evidence: dict[str, Any]
    source_tables: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniversityMarketAlignment:
    program_id: int
    program_name: str
    alignment_score: float
    alignment_level: str
    current_alignment: float
    projected_alignment_if_added: float
    missing_skills: list[str]
    emerging_skills: list[str]
    company_demand_score: float
    labor_demand_score: float
    forecasted_demand_score: float
    emerging_technology_score: float
    explanation: str
    supporting_evidence: dict[str, Any]
    source_tables: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketForecastRecord:
    entity_type: str
    entity_name: str
    horizon_months: int
    growth_velocity: float
    forecast_confidence: float
    market_phase: str
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmergingSkillSignal:
    skill_name: str
    growth_rate: float
    confidence_score: float
    first_seen_date: str | None
    last_seen_date: str | None
    supporting_companies: list[str]
    supporting_roles: list[str]
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CareerTransitionInsight:
    source_role: str
    target_role: str
    required_skills: list[str]
    difficulty_score: float
    estimated_salary_progression: float
    transition_probability: float
    source_family: str
    target_family: str
    supporting_evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecommendationV2:
    recommendation_type: str
    target_entity: str
    target_company: str
    recommendation_score: float
    priority: str
    business_justification: str
    expected_impact: str
    confidence: float
    estimated_alignment_increase: float
    recommendation_evidence: dict[str, Any]
    recommendation_reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutiveMetric:
    metric_name: str
    metric_category: str
    metric_value: float
    metric_period: str
    confidence_score: float
    source_tables: list[str]
    supporting_evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fetch_program_row(program_id: int, *, db_name: str | None = None) -> dict[str, Any]:
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=db_name)
    programs = {int(row.get("especializacion_id") or 0): row for row in dashboard_service.list_programs_base(db_name=db_name)}
    program = programs.get(resolved_id) or programas_repository.fetch_program_base_row(resolved_id, db_name=db_name)
    if not program:
        raise KeyError(f"programa {program_id} not found")
    program = dict(program)
    program["especializacion_id"] = resolved_id
    program.setdefault("nombre_especializacion", program.get("nombre", ""))
    program.setdefault("rol", program.get("rol", ""))
    return program


def _fetch_program_skills(program_id: int, *, db_name: str | None = None) -> list[dict[str, Any]]:
    rows = programas_repository.fetch_program_skill_rows(program_id, db_name=db_name)
    result: list[dict[str, Any]] = []
    for row in rows:
        skill_name = str(row.get("nombre") or row.get("skill") or row.get("skill_name") or "").strip()
        if skill_name:
            result.append({"skill_id": int(row.get("skill_id") or row.get("id") or 0), "nombre": skill_name, "skill_category": row.get("skill_category")})
    return result


def _fetch_market_skill_map() -> Any:
    return build_market_skill_intelligence_map(include_database=True, write_output=False)


def _skill_names(rows: Iterable[dict[str, Any]]) -> list[str]:
    return [str(row.get("nombre") or "").strip() for row in rows if str(row.get("nombre") or "").strip()]


def _related_market_skills(skill_names: Iterable[str], market_map: Any) -> list[str]:
    normalized_targets = {normalize_key(name) for name in skill_names if name}
    matches: list[str] = []
    for item in market_map.market_skills:
        normalized_skill = normalize_key(item.skill)
        if normalized_skill in normalized_targets:
            matches.append(item.skill)
    return sorted(set(matches))


def _market_forecast_rows(*, db_name: str | None = None, entity_type: str | None = None) -> list[dict[str, Any]]:
    if not relation_exists("market_forecasts", db_name=db_name):
        return []
    horizon_exists = bool(
        fetch_one(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'market_forecasts'
                  AND column_name = 'horizon_months'
            ) AS exists
            """,
            db_name=db_name,
        )
    )
    clauses = []
    params: list[Any] = []
    if entity_type:
        clauses.append("entity_type = %s")
        params.append(entity_type)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    select_horizon = "horizon_months," if horizon_exists else "12 AS horizon_months,"
    order_sql = "ORDER BY horizon_months ASC, growth_velocity DESC NULLS LAST, forecast_confidence DESC NULLS LAST" if horizon_exists else "ORDER BY growth_velocity DESC NULLS LAST, forecast_confidence DESC NULLS LAST"
    return fetch_all(
        f"""
        SELECT entity_type, entity_name, {select_horizon} growth_velocity, forecast_confidence,
               market_phase, first_seen_at, last_seen_at, evidence, updated_at
        FROM market_forecasts
        {where_sql}
        {order_sql}
        """,
        tuple(params),
        db_name=db_name,
    )


def _forecast_rows_to_map(rows: list[dict[str, Any]]) -> dict[str, dict[int, dict[str, Any]]]:
    grouped: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        entity_name = str(row.get("entity_name") or "").strip()
        if not entity_name:
            continue
        horizon = int(row.get("horizon_months") or 12)
        grouped[entity_name][horizon] = dict(row)
    return grouped


def _persistent_metric(metric_name: str, metric_category: str, metric_value: float, metric_period: str, confidence_score: float, payload: dict[str, Any], *, db_name: str | None = None) -> None:
    if not relation_exists("observatory_metrics", db_name=db_name):
        return
    with cursor(db_name=db_name) as cur:
        cur.execute(
            """
            INSERT INTO observatory_metrics
                (metric_name, metric_category, metric_value, metric_period, confidence_score, source_payload, generated_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now(), now())
            ON CONFLICT (metric_name, metric_period) DO UPDATE SET
                metric_category = EXCLUDED.metric_category,
                metric_value = EXCLUDED.metric_value,
                confidence_score = EXCLUDED.confidence_score,
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            (metric_name, metric_category, metric_value, metric_period, confidence_score, payload),
        )


def build_curriculum_risk_index(program_id: int, *, db_name: str | None = None, persist: bool = False) -> CurriculumRiskIndex:
    program = _fetch_program_row(program_id, db_name=db_name)
    program_skills = _fetch_program_skills(program_id, db_name=db_name)
    program_skill_names = _skill_names(program_skills)
    market_map = _fetch_market_skill_map()
    market_signals = {normalize_key(item.skill): item for item in market_map.market_skills}
    covered = [skill for skill in program_skill_names if normalize_key(skill) in {normalize_key(item.skill) for item in market_map.covered_skills}]
    partial = [skill for skill in program_skill_names if normalize_key(skill) in {normalize_key(item.skill) for item in market_map.partial_skills}]
    missing = [skill for skill in program_skill_names if normalize_key(skill) not in {normalize_key(item.skill) for item in market_map.covered_skills + market_map.partial_skills}]

    forecasts = _market_forecast_rows(db_name=db_name)
    related_forecasts = [
        row
        for row in forecasts
        if normalize_key(str(row.get("entity_name") or "")) in {normalize_key(skill) for skill in program_skill_names}
        or normalize_key(str(row.get("entity_name") or "")) in {normalize_key(skill) for skill in missing}
    ]
    emerging_tech = fetch_all(
        """
        SELECT technology, emergence_score, growth_velocity, adoption_trend, forecast_confidence
        FROM emerging_technology_observatory
        ORDER BY growth_velocity DESC NULLS LAST, emergence_score DESC NULLS LAST
        LIMIT 50
        """,
        db_name=db_name,
    ) if relation_exists("emerging_technology_observatory", db_name=db_name) else []

    coverage_ratio = (
        (len(covered) + 0.5 * len(partial)) / max(len(program_skill_names), 1)
        if program_skill_names
        else 0.0
    )
    missing_ratio = len(missing) / max(len(program_skill_names), 1)
    emerging_growth = mean([_safe_float(row.get("growth_velocity")) for row in related_forecasts]) if related_forecasts else 0.0
    forecast_risk = mean([_safe_float(row.get("growth_velocity")) for row in forecasts[:20]]) if forecasts else 0.0
    tech_disruption = mean([_safe_float(row.get("emergence_score")) for row in emerging_tech[:20]]) if emerging_tech else 0.0
    company_demand = 0.0
    if relation_exists("company_observatory", db_name=db_name):
        company_rows = fetch_all(
            """
            SELECT company, dominant_stack, dominant_cluster, top_skills, top_clusters, hiring_velocity
            FROM company_observatory
            ORDER BY hiring_velocity DESC NULLS LAST
            LIMIT 50
            """,
            db_name=db_name,
        )
        for row in company_rows:
            company_text = " ".join(
                _as_list(row.get("top_skills"))
                + _as_list(row.get("dominant_stack"))
                + _as_list(row.get("top_clusters"))
            )
            if any(normalize_key(skill) in normalize_key(company_text) for skill in program_skill_names[:8]):
                company_demand += 1
        company_demand = min(company_demand / 10.0, 1.0)

    labor_demand = min(
        1.0,
        (_safe_float(program.get("promedio_match_mercado")) / 100.0 if program.get("promedio_match_mercado") is not None else 0.0)
        or min(len(program_skill_names) / 12.0, 1.0)
    )
    forecast_score = clamp((emerging_growth + forecast_risk + company_demand) / 3.0)
    risk_score = clamp(
        0.32 * (1.0 - coverage_ratio)
        + 0.22 * missing_ratio
        + 0.18 * clamp(emerging_growth)
        + 0.15 * clamp(forecast_risk)
        + 0.13 * clamp(tech_disruption)
    )
    risk_score_100 = round(risk_score * 100, 2)
    if risk_score_100 >= 80:
        risk_level = "critical"
    elif risk_score_100 >= 60:
        risk_level = "high"
    elif risk_score_100 >= 35:
        risk_level = "moderate"
    else:
        risk_level = "low"

    risk_drivers = [
        {
            "driver": "curriculum_coverage",
            "value": round(coverage_ratio, 4),
            "impact": round((1.0 - coverage_ratio) * 100, 2),
            "evidence": covered[:5],
        },
        {
            "driver": "missing_skills",
            "value": round(missing_ratio, 4),
            "impact": round(missing_ratio * 100, 2),
            "evidence": missing[:8],
        },
        {
            "driver": "emerging_skill_growth",
            "value": round(emerging_growth, 4),
            "impact": round(emerging_growth * 100, 2),
            "evidence": [row.get("entity_name") for row in related_forecasts[:5]],
        },
        {
            "driver": "forecasted_labor_demand",
            "value": round(forecast_risk, 4),
            "impact": round(forecast_risk * 100, 2),
            "evidence": [row.get("entity_name") for row in forecasts[:5]],
        },
        {
            "driver": "technology_disruption",
            "value": round(tech_disruption, 4),
            "impact": round(tech_disruption * 100, 2),
            "evidence": [row.get("technology") for row in emerging_tech[:5]],
        },
    ]
    actions: list[str] = []
    if missing:
        actions.append(f"Fortalecer: {', '.join(missing[:5])}.")
    if emerging_growth > 0.2:
        actions.append("Incorporar competencias emergentes con evaluacion aplicada y no solo teorica.")
    if tech_disruption > 0.2:
        actions.append("Actualizar resultados de aprendizaje frente a tecnologias disruptivas del mercado.")
    if labor_demand < 0.5:
        actions.append("Revisar pertinencia laboral y reforzar vinculos con empresas con mayor demanda.")
    if not actions:
        actions.append("Mantener la cobertura actual y seguir monitoreando el mercado.")

    result = CurriculumRiskIndex(
        program_id=int(program.get("especializacion_id") or program_id),
        program_name=str(program.get("nombre_especializacion") or program.get("nombre") or ""),
        risk_score=risk_score_100,
        risk_level=risk_level,
        risk_drivers=risk_drivers,
        recommended_actions=actions,
        supporting_evidence={
            "skills": program_skill_names,
            "program_skills": program_skill_names,
            "covered_skills": covered,
            "partial_skills": partial,
            "missing_skills": missing,
            "forecast_rows": [row.get("entity_name") for row in related_forecasts[:10]],
            "source_tables": [
                "especializaciones",
                "especializacion_skills",
                "skills",
                "labor_program_skill_matches",
                "market_forecasts",
                "emerging_technology_observatory",
                "company_observatory",
            ],
        },
        source_tables=[
            "especializaciones",
            "especializacion_skills",
            "skills",
            "labor_program_skill_matches",
            "market_forecasts",
            "emerging_technology_observatory",
            "company_observatory",
        ],
        confidence=round(clamp((coverage_ratio + (1.0 - missing_ratio) + labor_demand + forecast_score) / 4.0), 4),
    )
    if persist:
        _persistent_metric(
            "curriculum_risk_index",
            "program_risk",
            result.risk_score,
            f"program:{result.program_id}",
            result.confidence,
            result.to_dict(),
            db_name=db_name,
        )
    return result


def build_university_market_alignment(program_id: int, *, db_name: str | None = None, persist: bool = False) -> UniversityMarketAlignment:
    program = _fetch_program_row(program_id, db_name=db_name)
    program_skills = _fetch_program_skills(program_id, db_name=db_name)
    skill_names = _skill_names(program_skills)
    market_map = _fetch_market_skill_map()
    market_skill_names = {normalize_key(item.skill) for item in market_map.market_skills}
    covered = [skill for skill in skill_names if normalize_key(skill) in {normalize_key(item.skill) for item in market_map.covered_skills}]
    partial = [skill for skill in skill_names if normalize_key(skill) in {normalize_key(item.skill) for item in market_map.partial_skills}]
    missing = [skill for skill in skill_names if normalize_key(skill) not in market_skill_names]
    emerging = [item.skill for item in market_map.emerging_skills[:10]]

    match_rows = []
    if relation_exists("labor_program_skill_matches", db_name=db_name):
        relation = matches_repository.match_relation_name(db_name=db_name)
        if relation:
            match_rows = matches_repository.fetch_match_rows_for_program(
                relation,
                int(program.get("especializacion_id") or program_id),
                limit=20,
                db_name=db_name,
            )
    labor_demand = mean([_safe_float(row.get("porcentaje_match")) / 100.0 for row in match_rows]) if match_rows else 0.0
    company_rows = fetch_all(
        """
        SELECT company, dominant_stack, dominant_cluster, top_skills, top_clusters, hiring_velocity, ai_adoption_score, bi_maturity_score, cloud_maturity_score
        FROM company_observatory
        ORDER BY hiring_velocity DESC NULLS LAST
        LIMIT 50
        """,
        db_name=db_name,
    ) if relation_exists("company_observatory", db_name=db_name) else []
    program_key = {normalize_key(skill) for skill in skill_names}
    company_matches = [
        row for row in company_rows
        if program_key.intersection(
            {
                normalize_key(item)
                for item in _as_list(row.get("top_skills")) + _as_list(row.get("dominant_stack")) + _as_list(row.get("top_clusters"))
            }
        )
    ]
    company_demand = min(len(company_matches) / 10.0, 1.0)
    forecast_rows = _market_forecast_rows(db_name=db_name)
    relevant_forecasts = [
        row for row in forecast_rows
        if normalize_key(str(row.get("entity_name") or "")) in program_key
        or normalize_key(str(row.get("entity_name") or "")) in {normalize_key(skill) for skill in missing}
    ]
    forecasted_demand = mean([_safe_float(row.get("growth_velocity")) for row in relevant_forecasts]) if relevant_forecasts else 0.0
    emerging_tech_rows = fetch_all(
        """
        SELECT technology, emergence_score, growth_velocity, forecast_confidence, adoption_trend
        FROM emerging_technology_observatory
        ORDER BY emergence_score DESC NULLS LAST, growth_velocity DESC NULLS LAST
        LIMIT 50
        """,
        db_name=db_name,
    ) if relation_exists("emerging_technology_observatory", db_name=db_name) else []
    emerging_technology_score = mean([_safe_float(row.get("emergence_score")) for row in emerging_tech_rows[:10]]) if emerging_tech_rows else 0.0
    current_alignment = (
        0.42 * ((len(covered) + 0.5 * len(partial)) / max(len(skill_names), 1) if skill_names else 0.0)
        + 0.18 * labor_demand
        + 0.16 * company_demand
        + 0.14 * clamp(forecasted_demand)
        + 0.10 * clamp(emerging_technology_score)
    )
    alignment_score = round(clamp(current_alignment) * 100, 2)
    projected_alignment = round(min(100.0, alignment_score + min(len(missing) * 1.8 + len(emerging) * 0.8, 18.0)), 2)
    if alignment_score >= 80:
        alignment_level = "strong"
    elif alignment_score >= 60:
        alignment_level = "healthy"
    elif alignment_score >= 40:
        alignment_level = "watch"
    else:
        alignment_level = "at_risk"

    explanation_parts = []
    if covered:
        explanation_parts.append(f"comparte {', '.join(covered[:5])}")
    if missing:
        explanation_parts.append(f"faltan {', '.join(missing[:5])}")
    if emerging:
        explanation_parts.append(f"se proyectan {', '.join(emerging[:5])}")
    explanation = (
        f"Alineacion actual: {alignment_score:.1f}%. "
        f"El programa {('muestra' if covered else 'no muestra')} cobertura relevante; "
        + "; ".join(explanation_parts)
        + "."
    )

    result = UniversityMarketAlignment(
        program_id=int(program.get("especializacion_id") or program_id),
        program_name=str(program.get("nombre_especializacion") or program.get("nombre") or ""),
        alignment_score=alignment_score,
        alignment_level=alignment_level,
        current_alignment=round(current_alignment * 100, 2),
        projected_alignment_if_added=projected_alignment,
        missing_skills=missing,
        emerging_skills=emerging,
        company_demand_score=round(clamp(company_demand), 4),
        labor_demand_score=round(clamp(labor_demand), 4),
        forecasted_demand_score=round(clamp(forecasted_demand), 4),
        emerging_technology_score=round(clamp(emerging_technology_score), 4),
        explanation=explanation,
        supporting_evidence={
            "skills": skill_names,
            "program_skills": skill_names,
            "covered_skills": covered,
            "partial_skills": partial,
            "missing_skills": missing,
            "market_forecasts": [row.get("entity_name") for row in relevant_forecasts[:10]],
            "company_matches": [row.get("company") for row in company_matches[:10]],
            "source_tables": [
                "especializaciones",
                "especializacion_skills",
                "skills",
                "labor_program_skill_matches",
                "company_observatory",
                "market_forecasts",
                "emerging_technology_observatory",
            ],
        },
        source_tables=[
            "especializaciones",
            "especializacion_skills",
            "skills",
            "labor_program_skill_matches",
            "company_observatory",
            "market_forecasts",
            "emerging_technology_observatory",
        ],
        confidence=round(clamp((current_alignment + labor_demand + company_demand + forecasted_demand) / 4.0), 4),
    )
    if persist:
        _persistent_metric(
            "university_market_alignment",
            "program_alignment",
            result.alignment_score,
            f"program:{result.program_id}",
            result.confidence,
            result.to_dict(),
            db_name=db_name,
        )
    return result


def build_market_demand_forecasts(*, db_name: str | None = None, persist: bool = False, limit: int = 30) -> list[MarketForecastRecord]:
    forecast_rows: list[dict[str, Any]] = []
    if relation_exists("jobs", db_name=db_name) and relation_exists("job_skills", db_name=db_name):
        forecast_rows.extend(
            fetch_all(
                """
                SELECT
                    'skill' AS entity_type,
                    js.canonical_skill AS entity_name,
                    DATE_TRUNC('month', COALESCE(j.created_at, j.updated_at, now())) AS month_bucket,
                    COUNT(DISTINCT j.id)::int AS count,
                    COUNT(DISTINCT j.company_id)::int AS company_count,
                    AVG(COALESCE(j.job_probability_score, 0.6)) AS avg_probability,
                    MIN(COALESCE(j.created_at, j.updated_at, now())) AS first_seen_at,
                    MAX(COALESCE(j.created_at, j.updated_at, now())) AS last_seen_at
                FROM jobs j
                INNER JOIN job_skills js ON js.job_id = j.id
                WHERE COALESCE(j.document_type, 'job_posting') = 'job_posting'
                  AND COALESCE(j.is_real_job_posting, true) = true
                  AND COALESCE(js.canonical_skill, '') <> ''
                GROUP BY 1, 2, 3
                ORDER BY entity_name, month_bucket
                """,
                db_name=db_name,
            )
        )
        forecast_rows.extend(
            fetch_all(
                """
                SELECT
                    'role' AS entity_type,
                    COALESCE(NULLIF(j.semantic_title_family, ''), NULLIF(j.occupational_role_inference, ''), NULLIF(j.title, '')) AS entity_name,
                    DATE_TRUNC('month', COALESCE(j.created_at, j.updated_at, now())) AS month_bucket,
                    COUNT(DISTINCT j.id)::int AS count,
                    COUNT(DISTINCT j.company_id)::int AS company_count,
                    AVG(COALESCE(j.job_probability_score, 0.6)) AS avg_probability,
                    MIN(COALESCE(j.created_at, j.updated_at, now())) AS first_seen_at,
                    MAX(COALESCE(j.created_at, j.updated_at, now())) AS last_seen_at
                FROM jobs j
                WHERE COALESCE(j.document_type, 'job_posting') = 'job_posting'
                  AND COALESCE(j.is_real_job_posting, true) = true
                  AND COALESCE(NULLIF(j.semantic_title_family, ''), NULLIF(j.occupational_role_inference, ''), NULLIF(j.title, '')) IS NOT NULL
                GROUP BY 1, 2, 3
                ORDER BY entity_name, month_bucket
                """,
                db_name=db_name,
            )
        )
        forecast_rows.extend(
            fetch_all(
                """
                SELECT
                    'technology' AS entity_type,
                    cs.canonical_skill AS entity_name,
                    DATE_TRUNC('month', COALESCE(j.created_at, j.updated_at, now())) AS month_bucket,
                    COUNT(DISTINCT j.id)::int AS count,
                    COUNT(DISTINCT j.company_id)::int AS company_count,
                    AVG(COALESCE(j.job_probability_score, 0.6)) AS avg_probability,
                    MIN(COALESCE(j.created_at, j.updated_at, now())) AS first_seen_at,
                    MAX(COALESCE(j.created_at, j.updated_at, now())) AS last_seen_at
                FROM jobs j
                INNER JOIN job_skills js ON js.job_id = j.id
                INNER JOIN canonical_skills cs ON cs.id = js.canonical_skill_id
                WHERE COALESCE(j.document_type, 'job_posting') = 'job_posting'
                  AND COALESCE(j.is_real_job_posting, true) = true
                  AND COALESCE(cs.skill_category, '') IN ('tool', 'platform', 'cloud', 'language')
                GROUP BY 1, 2, 3
                ORDER BY entity_name, month_bucket
                """,
                db_name=db_name,
            )
        )
    if relation_exists("jobs", db_name=db_name):
        forecast_rows.extend(
            fetch_all(
                """
                SELECT
                    'industry' AS entity_type,
                    COALESCE(NULLIF(j.industry, ''), i.industry) AS entity_name,
                    DATE_TRUNC('month', COALESCE(j.created_at, j.updated_at, now())) AS month_bucket,
                    COUNT(DISTINCT j.id)::int AS count,
                    COUNT(DISTINCT j.company_id)::int AS company_count,
                    AVG(COALESCE(j.job_probability_score, 0.6)) AS avg_probability,
                    MIN(COALESCE(j.created_at, j.updated_at, now())) AS first_seen_at,
                    MAX(COALESCE(j.created_at, j.updated_at, now())) AS last_seen_at
                FROM jobs j
                LEFT JOIN industries i ON i.id = j.industry_id
                WHERE COALESCE(j.document_type, 'job_posting') = 'job_posting'
                  AND COALESCE(j.is_real_job_posting, true) = true
                  AND COALESCE(NULLIF(j.industry, ''), i.industry) IS NOT NULL
                GROUP BY 1, 2, 3
                ORDER BY entity_name, month_bucket
                """,
                db_name=db_name,
            )
        )

    series = _normalize_series(forecast_rows, entity_key="entity_name")
    series_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in forecast_rows:
        entity_type = str(row.get("entity_type") or "").strip()
        entity_name = str(row.get("entity_name") or "").strip()
        if entity_type and entity_name:
            series_by_type[entity_type].append(row)

    records: list[MarketForecastRecord] = []
    for entity_type, rows in series_by_type.items():
        entity_metrics = _aggregate_monthly_metrics(_normalize_series(rows, entity_key="entity_name"))
        top_entities = sorted(entity_metrics.items(), key=lambda item: (item[1]["total_mentions"], item[1]["growth_velocity"]), reverse=True)[:TREND_ENTITY_LIMITS.get(entity_type, limit)]
        for entity_name, metrics in top_entities:
            for horizon in FUTURE_HORIZONS:
                growth_velocity = round(_projected_growth(metrics["growth_velocity"], horizon), 4)
                confidence = round(clamp(metrics["forecast_confidence"] - (horizon / 40.0)), 4)
                record = MarketForecastRecord(
                    entity_type=entity_type,
                    entity_name=entity_name,
                    horizon_months=horizon,
                    growth_velocity=growth_velocity,
                    forecast_confidence=confidence,
                    market_phase=_market_phase(growth_velocity, metrics["total_mentions"]),
                    first_seen_at=metrics["first_seen_at"],
                    last_seen_at=metrics["last_seen_at"],
                    evidence={
                        "monthly_counts": metrics["counts"][-12:],
                        "total_mentions": metrics["total_mentions"],
                        "total_companies": metrics["total_companies"],
                        "recent_mentions": metrics["recent_mentions"],
                        "previous_mentions": metrics["previous_mentions"],
                        "base_growth_velocity": round(metrics["growth_velocity"], 4),
                        "slope": round(metrics["slope"], 4),
                        "horizon_months": horizon,
                        "source_tables": ["jobs", "job_skills", "canonical_skills", "industries"],
                    },
                )
                records.append(record)
    records = sorted(records, key=lambda item: (item.entity_type, item.horizon_months, item.growth_velocity, item.forecast_confidence), reverse=True)
    if persist and records:
        persist_market_forecasts(records, db_name=db_name)
    return records


def persist_market_forecasts(records: list[MarketForecastRecord], *, db_name: str | None = None) -> int:
    if not records or not relation_exists("market_forecasts", db_name=db_name):
        return 0
    horizon_exists = bool(
        fetch_one(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'market_forecasts'
                  AND column_name = 'horizon_months'
            ) AS exists
            """,
            db_name=db_name,
        )
    )
    records_to_store = records if horizon_exists else [record for record in records if record.horizon_months == 12]
    if not records_to_store:
        records_to_store = [record for record in records if record.horizon_months == 12] or records[:1]
    with cursor(db_name=db_name) as cur:
        from psycopg2.extras import execute_values, Json

        if horizon_exists:
            rows = [
                (
                    record.entity_type,
                    record.entity_name,
                    record.horizon_months,
                    record.growth_velocity,
                    record.forecast_confidence,
                    record.market_phase,
                    record.first_seen_at,
                    record.last_seen_at,
                    Json(_json_safe(record.evidence)),
                )
                for record in records_to_store
            ]
            execute_values(
                cur,
                """
                INSERT INTO market_forecasts
                    (entity_type, entity_name, horizon_months, growth_velocity, forecast_confidence, market_phase, first_seen_at, last_seen_at, evidence)
                VALUES %s
                ON CONFLICT (entity_type, entity_name, horizon_months) DO UPDATE SET
                    growth_velocity = EXCLUDED.growth_velocity,
                    forecast_confidence = EXCLUDED.forecast_confidence,
                    market_phase = EXCLUDED.market_phase,
                    first_seen_at = LEAST(COALESCE(market_forecasts.first_seen_at, EXCLUDED.first_seen_at), COALESCE(EXCLUDED.first_seen_at, market_forecasts.first_seen_at)),
                    last_seen_at = GREATEST(COALESCE(market_forecasts.last_seen_at, EXCLUDED.last_seen_at), COALESCE(EXCLUDED.last_seen_at, market_forecasts.last_seen_at)),
                    evidence = EXCLUDED.evidence,
                    updated_at = now()
                """,
                rows,
                page_size=min(len(rows), 500),
            )
        else:
            rows = [
                (
                    record.entity_type,
                    record.entity_name,
                    record.growth_velocity,
                    record.forecast_confidence,
                    record.market_phase,
                    record.first_seen_at,
                    record.last_seen_at,
                    Json(_json_safe(record.evidence)),
                )
                for record in records_to_store
            ]
            execute_values(
                cur,
                """
                INSERT INTO market_forecasts
                    (entity_type, entity_name, growth_velocity, forecast_confidence, market_phase, first_seen_at, last_seen_at, evidence)
                VALUES %s
                ON CONFLICT (entity_type, entity_name) DO UPDATE SET
                    growth_velocity = EXCLUDED.growth_velocity,
                    forecast_confidence = EXCLUDED.forecast_confidence,
                    market_phase = EXCLUDED.market_phase,
                    first_seen_at = LEAST(COALESCE(market_forecasts.first_seen_at, EXCLUDED.first_seen_at), COALESCE(EXCLUDED.first_seen_at, market_forecasts.first_seen_at)),
                    last_seen_at = GREATEST(COALESCE(market_forecasts.last_seen_at, EXCLUDED.last_seen_at), COALESCE(EXCLUDED.last_seen_at, market_forecasts.last_seen_at)),
                    evidence = EXCLUDED.evidence,
                    updated_at = now()
                """,
                rows,
                page_size=min(len(rows), 500),
            )
    return len(records_to_store)


def detect_emerging_skills(*, db_name: str | None = None, limit: int = 50) -> list[EmergingSkillSignal]:
    signals: dict[str, dict[str, Any]] = {}
    if relation_exists("jobs", db_name=db_name):
        rows = fetch_all(
            """
            SELECT
                candidate.skill_name,
                COUNT(DISTINCT j.id)::int AS mention_count,
                COUNT(DISTINCT j.company_id)::int AS company_count,
                MIN(COALESCE(j.created_at, j.updated_at, now())) AS first_seen_at,
                MAX(COALESCE(j.created_at, j.updated_at, now())) AS last_seen_at,
                ARRAY_AGG(DISTINCT COALESCE(NULLIF(j.semantic_title_family, ''), NULLIF(j.occupational_role_inference, ''), NULLIF(j.title, ''))) FILTER (WHERE COALESCE(NULLIF(j.semantic_title_family, ''), NULLIF(j.occupational_role_inference, ''), NULLIF(j.title, '')) IS NOT NULL) AS roles
            FROM jobs j
            CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(j.unknown_skill_candidates, '[]'::jsonb)) AS candidate(skill_name)
            WHERE COALESCE(j.document_type, 'job_posting') = 'job_posting'
              AND COALESCE(j.is_real_job_posting, true) = true
              AND COALESCE(candidate.skill_name, '') <> ''
            GROUP BY candidate.skill_name
            ORDER BY mention_count DESC, company_count DESC, candidate.skill_name
            LIMIT %s
            """,
            (limit * 2,),
            db_name=db_name,
        )
        for row in rows:
            skill_name = str(row.get("skill_name") or "").strip()
            if not skill_name:
                continue
            if normalize_key(skill_name) in {"sql", "python", "power bi", "tableau", "azure", "aws", "gcp", "bi", "etl"}:
                continue
            mention_count = int(row.get("mention_count") or 0)
            company_count = int(row.get("company_count") or 0)
            growth_rate = clamp((mention_count / 10.0) + (company_count / 20.0), 0.0, 1.0)
            confidence = _confidence(mention_count, company_count, mention_count)
            signals[skill_name] = {
                "skill_name": skill_name,
                "growth_rate": round(growth_rate, 4),
                "confidence_score": round(confidence, 4),
                "first_seen_date": row.get("first_seen_at").date().isoformat() if row.get("first_seen_at") else None,
                "last_seen_date": row.get("last_seen_at").date().isoformat() if row.get("last_seen_at") else None,
                "supporting_companies": _top_items(Counter(_as_list(row.get("company_name"))), 5),
                "supporting_roles": [str(item) for item in _as_list(row.get("roles"))[:5]],
                "evidence": {
                    "mention_count": mention_count,
                    "company_count": company_count,
                    "source_tables": ["jobs", "job_skills", "unknown_skill_candidates"],
                },
            }
    if relation_exists("market_forecasts", db_name=db_name):
        rows = fetch_all(
            """
            SELECT entity_name, growth_velocity, forecast_confidence, first_seen_at, last_seen_at, evidence
            FROM market_forecasts
            WHERE entity_type = 'skill'
              AND market_phase IN ('emerging', 'expanding')
            ORDER BY growth_velocity DESC NULLS LAST, forecast_confidence DESC NULLS LAST
            LIMIT %s
            """,
            (limit,),
            db_name=db_name,
        )
        for row in rows:
            skill_name = str(row.get("entity_name") or "").strip()
            if not skill_name:
                continue
            if skill_name not in signals:
                signals[skill_name] = {
                    "skill_name": skill_name,
                    "growth_rate": round(_safe_float(row.get("growth_velocity")), 4),
                    "confidence_score": round(_safe_float(row.get("forecast_confidence")), 4),
                    "first_seen_date": row.get("first_seen_at").date().isoformat() if row.get("first_seen_at") else None,
                    "last_seen_date": row.get("last_seen_at").date().isoformat() if row.get("last_seen_at") else None,
                    "supporting_companies": [],
                    "supporting_roles": [],
                    "evidence": row.get("evidence") or {},
                }
    items = sorted(signals.values(), key=lambda item: (item["growth_rate"], item["confidence_score"]), reverse=True)
    return [EmergingSkillSignal(**item) for item in items[:limit]]


def build_career_intelligence(*, source_role: str | None = None, db_name: str | None = None, limit: int = 12) -> dict[str, Any]:
    role_rows = fetch_all(
        """
        SELECT source_role, target_role, similarity_score, transition_probability, shared_skills, cluster_affinity, centrality_score, evidence
        FROM semantic_role_graph
        ORDER BY similarity_score DESC NULLS LAST, transition_probability DESC NULLS LAST
        LIMIT %s
        """,
        (limit * 5,),
        db_name=db_name,
    ) if relation_exists("semantic_role_graph", db_name=db_name) else []
    transition_rows = fetch_all(
        """
        SELECT source_role, target_role, role_progression_probability, transition_skill_gaps, recommended_next_skills
        FROM career_transitions
        ORDER BY role_progression_probability DESC NULLS LAST
        LIMIT %s
        """,
        (limit * 5,),
        db_name=db_name,
    ) if relation_exists("career_transitions", db_name=db_name) else []

    salaries = fetch_all(
        """
        SELECT COALESCE(NULLIF(semantic_title_family, ''), NULLIF(occupational_role_inference, ''), NULLIF(title, '')) AS role_name,
               AVG(COALESCE(salary_max, salary_min, 0)) AS avg_salary,
               COUNT(*)::int AS job_count
        FROM jobs
        WHERE COALESCE(document_type, 'job_posting') = 'job_posting'
          AND COALESCE(is_real_job_posting, true) = true
          AND COALESCE(NULLIF(semantic_title_family, ''), NULLIF(occupational_role_inference, ''), NULLIF(title, '')) IS NOT NULL
        GROUP BY 1
        """,
        db_name=db_name,
    ) if relation_exists("jobs", db_name=db_name) else []
    salary_map = {str(row.get("role_name") or "").strip(): _safe_float(row.get("avg_salary")) for row in salaries if str(row.get("role_name") or "").strip()}

    paths: list[CareerTransitionInsight] = []
    for row in transition_rows:
        source = str(row.get("source_role") or "").strip()
        target = str(row.get("target_role") or "").strip()
        if not source or not target:
            continue
        transition_probability = _safe_float(row.get("role_progression_probability"))
        gaps = _as_list(row.get("transition_skill_gaps"))
        recommended = _as_list(row.get("recommended_next_skills"))
        source_salary = salary_map.get(source, 0.0)
        target_salary = salary_map.get(target, source_salary * 1.1 if source_salary else 0.0)
        salary_progression = round(max(target_salary - source_salary, 0.0), 2)
        difficulty = round(clamp(1.0 - transition_probability + len(gaps) / 10.0), 4)
        family_source = next((str(item.get("source_role") or item.get("role_title") or "") for item in role_rows if str(item.get("source_role") or "").strip() == source), "")
        family_target = next((str(item.get("target_role") or item.get("role_title") or "") for item in role_rows if str(item.get("target_role") or "").strip() == target), "")
        paths.append(
            CareerTransitionInsight(
                source_role=source,
                target_role=target,
                required_skills=recommended or gaps,
                difficulty_score=difficulty,
                estimated_salary_progression=salary_progression,
                transition_probability=round(transition_probability, 4),
                source_family=family_source or source,
                target_family=family_target or target,
                supporting_evidence={
                    "shared_skills": _as_list(row.get("shared_skills")),
                    "cluster_affinity": _safe_float(row.get("cluster_affinity")),
                    "centrality_score": _safe_float(row.get("centrality_score")),
                    "source_tables": ["semantic_role_graph", "career_transitions", "jobs"],
                },
            )
        )

    if source_role:
        normalized_source = normalize_key(source_role)
        paths = [path for path in paths if normalize_key(path.source_role) == normalized_source or normalize_key(path.target_role) == normalized_source or normalized_source in normalize_key(path.source_family)]

    transitions = [path.to_dict() for path in paths[:limit]]
    return {
        "source_role": source_role or "",
        "transitions": transitions,
        "role_network": [row for row in role_rows[:limit * 2]],
        "source_tables": ["semantic_role_graph", "career_transitions", "jobs"],
        "confidence": round(clamp(len(transitions) / max(len(paths), 1) if paths else 0.5), 4),
    }


def build_recommendation_v2(*, program_id: int | None = None, db_name: str | None = None, limit: int = 8) -> list[RecommendationV2]:
    alignment = build_university_market_alignment(program_id, db_name=db_name, persist=False) if program_id else None
    risk = build_curriculum_risk_index(program_id, db_name=db_name, persist=False) if program_id else None
    market_map = _fetch_market_skill_map()
    top_company_rows = fetch_all(
        """
        SELECT company, dominant_stack, dominant_cluster, hiring_velocity, ai_adoption_score, bi_maturity_score, cloud_maturity_score, technology_maturity, top_skills
        FROM company_observatory
        ORDER BY hiring_velocity DESC NULLS LAST, cloud_maturity_score DESC NULLS LAST
        LIMIT 20
        """,
        db_name=db_name,
    ) if relation_exists("company_observatory", db_name=db_name) else []

    recommendations: list[RecommendationV2] = []
    if alignment:
        key = f"program:{alignment.program_id}"
        recommendations.append(
            RecommendationV2(
                recommendation_type="curriculum",
                target_entity=alignment.program_name,
                target_company="curriculum",
                recommendation_score=round(clamp(alignment.alignment_score / 100.0), 4),
                priority="high" if alignment.alignment_score < 65 else "medium",
                business_justification=f"La alineacion actual es {alignment.alignment_score:.1f}% y el programa muestra brechas en {', '.join(alignment.missing_skills[:5]) or 'skills emergentes'}.",
                expected_impact=f"Podria aumentar la alineacion proyectada hasta {alignment.projected_alignment_if_added:.1f}%.",
                confidence=alignment.confidence,
                estimated_alignment_increase=round(max(alignment.projected_alignment_if_added - alignment.alignment_score, 0), 2),
                recommendation_evidence={
                    "missing_skills": alignment.missing_skills[:8],
                    "emerging_skills": alignment.emerging_skills[:8],
                    "source_tables": alignment.source_tables,
                    "metric_period": key,
                },
                recommendation_reasoning=alignment.explanation,
            )
        )
    if risk:
        recommendations.append(
            RecommendationV2(
                recommendation_type="risk_mitigation",
                target_entity=risk.program_name,
                target_company="program",
                recommendation_score=round(clamp(1.0 - risk.risk_score / 100.0), 4),
                priority="high" if risk.risk_score >= 60 else "medium",
                business_justification=f"El indice de riesgo es {risk.risk_score:.1f}/100 y el nivel es {risk.risk_level}.",
                expected_impact="Reducir brechas y mejorar pertinencia laboral en el corto plazo.",
                confidence=risk.confidence,
                estimated_alignment_increase=round(max(100.0 - risk.risk_score - (alignment.alignment_score if alignment else 0), 0), 2),
                recommendation_evidence={
                    "risk_drivers": risk.risk_drivers,
                    "recommended_actions": risk.recommended_actions,
                    "source_tables": risk.source_tables,
                },
                recommendation_reasoning=" ".join(risk.recommended_actions),
            )
        )

    for row in top_company_rows[:limit]:
        company = str(row.get("company") or "").strip()
        if not company:
            continue
        dominant_skills = _as_list(row.get("top_skills")) or _as_list(row.get("dominant_stack"))
        if program_id and alignment and alignment.missing_skills:
            recommended_skills = [skill for skill in alignment.missing_skills if skill not in dominant_skills][:4]
        else:
            recommended_skills = [skill.skill for skill in market_map.emerging_skills[:4]]
        recommendations.append(
            RecommendationV2(
                recommendation_type="company_fit",
                target_entity=row.get("dominant_cluster") or row.get("technology_maturity") or "career_path",
                target_company=company,
                recommendation_score=round(clamp((_safe_float(row.get("hiring_velocity")) + _safe_float(row.get("cloud_maturity_score")) + _safe_float(row.get("bi_maturity_score")) + _safe_float(row.get("ai_adoption_score"))) / 4.0), 4),
                priority="high" if _safe_float(row.get("hiring_velocity")) >= 0.5 else "medium",
                business_justification=f"{company} muestra demanda en {row.get('dominant_cluster') or 'analytics'} y madurez {row.get('technology_maturity') or 'n/a'}.",
                expected_impact=f"Fortalecer {', '.join(recommended_skills or dominant_skills[:3]) or 'skills clave'} para mejorar empleabilidad y encaje por empresa.",
                confidence=round(clamp((_safe_float(row.get("hiring_velocity")) + _safe_float(row.get("cloud_maturity_score"))) / 2.0), 4),
                estimated_alignment_increase=round(min(12.0, len(recommended_skills) * 2.5), 2),
                recommendation_evidence={
                    "dominant_skills": dominant_skills[:8],
                    "dominant_cluster": row.get("dominant_cluster"),
                    "source_tables": ["company_observatory"],
                },
                recommendation_reasoning=f"Alta afinidad con {row.get('dominant_cluster') or 'la demanda laboral'} en {company}.",
            )
        )
    return sorted(recommendations, key=lambda item: (item.recommendation_score, item.confidence), reverse=True)[:limit]


def build_executive_metrics(
    *,
    db_name: str | None = None,
    program_rows: list[dict[str, Any]] | None = None,
    emerging_skills: list[Any] | None = None,
    market_forecasts: list[Any] | None = None,
    top_skills: list[dict[str, Any]] | None = None,
    top_companies: list[dict[str, Any]] | None = None,
) -> list[ExecutiveMetric]:
    if program_rows is None:
        program_rows = dashboard_service.list_programs_base(db_name=db_name)
    alignment_scores = [clamp(_safe_float(row.get("promedio_match_mercado")) / 100.0) for row in program_rows]
    risk_indexes: list[float] = []
    if program_rows and any("risk_score" in row for row in program_rows):
        risk_indexes = [_safe_float(row.get("risk_score")) for row in program_rows[:20] if row.get("risk_score") is not None]
    elif relation_exists("program_intelligence", db_name=db_name):
        risk_rows = fetch_all(
            """
            SELECT program_id, risk_score
            FROM program_intelligence
            ORDER BY risk_score DESC NULLS LAST, program_id
            LIMIT 20
            """,
            db_name=db_name,
        )
        risk_indexes = [_safe_float(row.get("risk_score")) for row in risk_rows]
    elif program_rows:
        risk_indexes = [round((1.0 - score) * 100.0, 2) for score in alignment_scores[:20]]
    if emerging_skills is None:
        emerging_skills = detect_emerging_skills(db_name=db_name, limit=20)
    if market_forecasts is None:
        market_forecasts = _market_forecast_rows(db_name=db_name)
    if top_skills is None:
        top_skills = fetch_all(
        """
        SELECT js.canonical_skill AS skill_name, COUNT(DISTINCT j.id)::int AS demand_count
        FROM jobs j
        INNER JOIN job_skills js ON js.job_id = j.id
        WHERE COALESCE(j.document_type, 'job_posting') = 'job_posting'
          AND COALESCE(j.is_real_job_posting, true) = true
          AND COALESCE(js.canonical_skill, '') <> ''
        GROUP BY js.canonical_skill
        ORDER BY demand_count DESC, skill_name
        LIMIT 10
        """,
            db_name=db_name,
        ) if relation_exists("jobs", db_name=db_name) and relation_exists("job_skills", db_name=db_name) else []
    if top_companies is None:
        top_companies = fetch_all(
        """
        SELECT company, hiring_velocity, technology_maturity, cloud_maturity_score, bi_maturity_score
        FROM company_observatory
        ORDER BY hiring_velocity DESC NULLS LAST, cloud_maturity_score DESC NULLS LAST
        LIMIT 10
        """,
            db_name=db_name,
        ) if relation_exists("company_observatory", db_name=db_name) else []
    metrics = [
        ExecutiveMetric(
            metric_name="programs_at_risk",
            metric_category="executive",
            metric_value=round(sum(1 for score in alignment_scores if score < 0.60), 2),
            metric_period=datetime.now(UTC).strftime("%Y-%m"),
            confidence_score=0.90,
            source_tables=["especializaciones", "especializacion_skills", "labor_program_skill_matches"],
            supporting_evidence={"alignment_scores": alignment_scores[:20], "risk_indexes": risk_indexes[:20]},
        ),
        ExecutiveMetric(
            metric_name="emerging_technologies",
            metric_category="executive",
            metric_value=round(len(emerging_skills), 2),
            metric_period=datetime.now(UTC).strftime("%Y-%m"),
            confidence_score=0.88,
            source_tables=["jobs", "market_forecasts", "emerging_technology_observatory"],
            supporting_evidence={"skills": [_item_text(item, "skill_name", "entity_name") for item in emerging_skills[:10]]},
        ),
        ExecutiveMetric(
            metric_name="top_demanded_skills",
            metric_category="executive",
            metric_value=round(len(top_skills), 2),
            metric_period=datetime.now(UTC).strftime("%Y-%m"),
            confidence_score=0.86,
            source_tables=["jobs", "job_skills", "skills"],
            supporting_evidence={"top_skills": [row.get("skill_name") for row in top_skills]},
        ),
        ExecutiveMetric(
            metric_name="top_hiring_companies",
            metric_category="executive",
            metric_value=round(len(top_companies), 2),
            metric_period=datetime.now(UTC).strftime("%Y-%m"),
            confidence_score=0.84,
            source_tables=["company_observatory"],
            supporting_evidence={"companies": [row.get("company") for row in top_companies]},
        ),
        ExecutiveMetric(
            metric_name="alignment_trend",
            metric_category="executive",
            metric_value=round(mean(alignment_scores) * 100 if alignment_scores else 0.0, 2),
            metric_period=datetime.now(UTC).strftime("%Y-%m"),
            confidence_score=0.82,
            source_tables=["especializaciones", "labor_program_skill_matches"],
            supporting_evidence={"alignment_scores": alignment_scores[:20]},
        ),
        ExecutiveMetric(
            metric_name="forecast_trend",
            metric_category="executive",
            metric_value=round(mean([_safe_float(row.get("growth_velocity")) for row in market_forecasts]) if market_forecasts else 0.0, 4),
            metric_period=datetime.now(UTC).strftime("%Y-%m"),
            confidence_score=0.80,
            source_tables=["market_forecasts"],
            supporting_evidence={"forecast_count": len(market_forecasts)},
        ),
        ExecutiveMetric(
            metric_name="skill_volatility_index",
            metric_category="executive",
            metric_value=round((max(alignment_scores) - min(alignment_scores)) * 100 if alignment_scores else 0.0, 2),
            metric_period=datetime.now(UTC).strftime("%Y-%m"),
            confidence_score=0.78,
            source_tables=["observatory_metrics", "market_forecasts"],
            supporting_evidence={"alignment_scores": alignment_scores[:20], "forecast_rows": len(market_forecasts)},
        ),
    ]
    return metrics


def persist_executive_metrics(metrics: list[ExecutiveMetric], *, db_name: str | None = None) -> int:
    if not metrics or not relation_exists("observatory_metrics", db_name=db_name):
        return 0
    rows = [
        (
            metric.metric_name,
            metric.metric_category,
            metric.metric_value,
            metric.metric_period,
            metric.confidence_score,
            metric.supporting_evidence,
        )
        for metric in metrics
    ]
    with cursor(db_name=db_name) as cur:
        from psycopg2.extras import execute_values, Json

        execute_values(
            cur,
            """
            INSERT INTO observatory_metrics
                (metric_name, metric_category, metric_value, metric_period, confidence_score, source_payload)
            VALUES %s
            ON CONFLICT (metric_name, metric_period) DO UPDATE SET
                metric_category = EXCLUDED.metric_category,
                metric_value = EXCLUDED.metric_value,
                confidence_score = EXCLUDED.confidence_score,
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            [(name, category, value, period, confidence, Json(payload)) for name, category, value, period, confidence, payload in rows],
            page_size=min(len(rows), 100),
        )
    return len(rows)
