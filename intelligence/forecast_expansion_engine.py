from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from statistics import mean
import json
from typing import Any

from psycopg2.extras import Json, execute_values

from backend.repositories.base import cursor, fetch_all, relation_exists
from intelligence.common import clamp, normalize_key
from intelligence.predictive_intelligence_engine import MarketForecastRecord, build_market_demand_forecasts, persist_market_forecasts
from intelligence.skill_normalization_engine import normalize_skill


FORECAST_HORIZONS = (3, 6, 12, 24)


@dataclass(frozen=True)
class ForecastExpansionBundle:
    skill: list[MarketForecastRecord] = field(default_factory=list)
    technology: list[MarketForecastRecord] = field(default_factory=list)
    company: list[MarketForecastRecord] = field(default_factory=list)
    role: list[MarketForecastRecord] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill": [item.to_dict() for item in self.skill],
            "technology": [item.to_dict() for item in self.technology],
            "company": [item.to_dict() for item in self.company],
            "role": [item.to_dict() for item in self.role],
            "generated_at": self.generated_at,
        }


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
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def _market_phase(velocity: float, confidence: float) -> str:
    if velocity >= 0.8 and confidence >= 0.65:
        return "emerging"
    if velocity >= 0.55:
        return "growing"
    if velocity <= 0.2:
        return "stable"
    return "expanding"


def _horizon_adjustment(horizon: int) -> float:
    return {3: 1.04, 6: 1.0, 12: 0.96, 24: 0.9}.get(int(horizon), 1.0)


def _horizon_confidence_adjustment(horizon: int) -> float:
    return {3: 0.95, 6: 1.0, 12: 0.96, 24: 0.92}.get(int(horizon), 1.0)


def _records_by_horizon(
    *,
    entity_type: str,
    entity_name: str,
    base_growth_velocity: float,
    base_confidence: float,
    first_seen_at: datetime | None,
    last_seen_at: datetime | None,
    evidence: dict[str, Any],
) -> list[MarketForecastRecord]:
    records: list[MarketForecastRecord] = []
    for horizon in FORECAST_HORIZONS:
        velocity = clamp(base_growth_velocity * _horizon_adjustment(horizon))
        confidence = clamp(base_confidence * _horizon_confidence_adjustment(horizon), 0.0, 1.0)
        records.append(
            MarketForecastRecord(
                entity_type=entity_type,
                entity_name=entity_name,
                horizon_months=horizon,
                growth_velocity=round(velocity, 4),
                forecast_confidence=round(confidence, 4),
                market_phase=_market_phase(velocity, confidence),
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                evidence=evidence,
            )
        )
    return records


def _build_technology_forecasts(*, db_name: str | None = None) -> list[MarketForecastRecord]:
    if not relation_exists("emerging_technology_observatory", db_name=db_name):
        return []
    rows = fetch_all(
        """
        SELECT technology, emergence_score, growth_velocity, adoption_trend, forecast_confidence,
               generated_at
        FROM emerging_technology_observatory
        ORDER BY growth_velocity DESC NULLS LAST, emergence_score DESC NULLS LAST
        """,
        db_name=db_name,
    )
    records: list[MarketForecastRecord] = []
    for row in rows:
        technology = str(row.get("technology") or "").strip()
        if not technology:
            continue
        growth_velocity = max(_safe_float(row.get("growth_velocity")), _safe_float(row.get("emergence_score")) / 100.0)
        confidence = _safe_float(row.get("forecast_confidence")) or max(0.35, growth_velocity * 0.9)
        evidence = {
            "source_table": "emerging_technology_observatory",
            "adoption_trend": row.get("adoption_trend"),
            "emergence_score": row.get("emergence_score"),
            "generated_at": row.get("generated_at"),
        }
        records.extend(
            _records_by_horizon(
                entity_type="technology",
                entity_name=technology,
                base_growth_velocity=growth_velocity,
                base_confidence=confidence,
                first_seen_at=row.get("generated_at"),
                last_seen_at=row.get("generated_at"),
                evidence=evidence,
            )
        )
    return records


def _build_company_forecasts(*, db_name: str | None = None) -> list[MarketForecastRecord]:
    if not relation_exists("company_observatory", db_name=db_name):
        return []
    rows = fetch_all(
        """
        SELECT company, dominant_stack, dominant_cluster, hiring_velocity,
               ai_adoption_score, cloud_maturity_score, bi_maturity_score,
               technology_maturity, top_skills, top_clusters, evidence
        FROM company_observatory
        ORDER BY hiring_velocity DESC NULLS LAST, cloud_maturity_score DESC NULLS LAST
        """,
        db_name=db_name,
    )
    records: list[MarketForecastRecord] = []
    for row in rows:
        company = str(row.get("company") or "").strip()
        if not company:
            continue
        hiring_velocity = clamp(_safe_float(row.get("hiring_velocity")) / 100.0)
        maturity = mean([
            _safe_float(row.get("ai_adoption_score")),
            _safe_float(row.get("cloud_maturity_score")),
            _safe_float(row.get("bi_maturity_score")),
        ]) / 100.0
        growth_velocity = clamp(max(hiring_velocity, maturity))
        confidence = clamp(0.45 + growth_velocity * 0.4, 0.35, 0.95)
        evidence = {
            "source_table": "company_observatory",
            "dominant_stack": row.get("dominant_stack"),
            "dominant_cluster": row.get("dominant_cluster"),
            "technology_maturity": row.get("technology_maturity"),
            "top_skills": row.get("top_skills"),
            "top_clusters": row.get("top_clusters"),
            "evidence": row.get("evidence"),
        }
        records.extend(
            _records_by_horizon(
                entity_type="company",
                entity_name=company,
                base_growth_velocity=growth_velocity,
                base_confidence=confidence,
                first_seen_at=None,
                last_seen_at=None,
                evidence=evidence,
            )
        )
    return records


def _build_role_forecasts(*, db_name: str | None = None) -> list[MarketForecastRecord]:
    records: list[MarketForecastRecord] = []
    if relation_exists("semantic_role_graph", db_name=db_name):
        rows = fetch_all(
            """
            SELECT source_role, target_role, similarity_score, transition_probability,
                   shared_skills, cluster_affinity, updated_at
            FROM semantic_role_graph
            ORDER BY transition_probability DESC NULLS LAST, similarity_score DESC NULLS LAST
            """,
            db_name=db_name,
        )
        for row in rows:
            target_role = str(row.get("target_role") or "").strip()
            source_role = str(row.get("source_role") or "").strip()
            if not target_role:
                continue
            growth_velocity = clamp(max(_safe_float(row.get("transition_probability")), _safe_float(row.get("similarity_score"))))
            confidence = clamp(0.45 + growth_velocity * 0.4, 0.35, 0.95)
            records.extend(
                _records_by_horizon(
                    entity_type="role",
                    entity_name=target_role,
                    base_growth_velocity=growth_velocity,
                    base_confidence=confidence,
                    first_seen_at=row.get("updated_at"),
                    last_seen_at=row.get("updated_at"),
                    evidence={
                        "source_table": "semantic_role_graph",
                        "source_role": source_role,
                        "shared_skills": row.get("shared_skills"),
                        "cluster_affinity": row.get("cluster_affinity"),
                    },
                )
            )
    if relation_exists("career_transitions", db_name=db_name):
        rows = fetch_all(
            """
            SELECT source_role, target_role, role_progression_probability,
                   transition_skill_gaps, recommended_next_skills, created_at
            FROM career_transitions
            ORDER BY role_progression_probability DESC NULLS LAST, source_role ASC
            """,
            db_name=db_name,
        )
        for row in rows:
            target_role = str(row.get("target_role") or "").strip()
            if not target_role:
                continue
            growth_velocity = clamp(_safe_float(row.get("role_progression_probability")))
            confidence = clamp(0.4 + growth_velocity * 0.5, 0.35, 0.98)
            records.extend(
                _records_by_horizon(
                    entity_type="role",
                    entity_name=target_role,
                    base_growth_velocity=growth_velocity,
                    base_confidence=confidence,
                    first_seen_at=row.get("created_at"),
                    last_seen_at=row.get("created_at"),
                    evidence={
                        "source_table": "career_transitions",
                        "source_role": row.get("source_role"),
                        "transition_skill_gaps": row.get("transition_skill_gaps"),
                        "recommended_next_skills": row.get("recommended_next_skills"),
                    },
                )
            )
    return records


def _skill_forecast_records(*, db_name: str | None = None, limit: int = 50) -> list[MarketForecastRecord]:
    records = build_market_demand_forecasts(db_name=db_name, persist=False, limit=limit)
    return list(records)


def _dedupe_records(records: list[MarketForecastRecord]) -> list[MarketForecastRecord]:
    best: dict[tuple[str, str, int], MarketForecastRecord] = {}
    for record in records:
        key = (record.entity_type, normalize_key(record.entity_name), int(record.horizon_months))
        current = best.get(key)
        if not current:
            best[key] = record
            continue
        if (record.growth_velocity, record.forecast_confidence) >= (current.growth_velocity, current.forecast_confidence):
            best[key] = record
    return sorted(best.values(), key=lambda item: (item.entity_type, item.horizon_months, item.growth_velocity, item.forecast_confidence), reverse=True)


def _persist_skill_trend_forecasts(records: list[MarketForecastRecord], *, db_name: str | None = None) -> int:
    if not records or not relation_exists("skill_trend_forecast", db_name=db_name):
        return 0
    normalized_rows: list[tuple[Any, ...]] = []
    for record in records:
        normalized = normalize_skill(record.entity_name, db_name=db_name, source_payload={"source": "forecast_expansion"})
        growth_score = round(clamp(record.growth_velocity) * 100.0, 4)
        decline_score = round(max(0.0, 100.0 - growth_score), 4)
        normalized_rows.append(
            (
                normalized.canonical_skill_id,
                normalized.canonical_skill or record.entity_name,
                record.horizon_months,
                growth_score,
                decline_score,
                record.forecast_confidence,
                record.first_seen_at,
                record.last_seen_at,
                Json(
                    {
                        "entity_type": record.entity_type,
                        "market_phase": record.market_phase,
                        "evidence": record.evidence,
                        "normalized_skill": normalized.to_dict(),
                    }
                ),
            )
        )
    with cursor(db_name=db_name) as cur:
        execute_values(
            cur,
            """
            INSERT INTO skill_trend_forecast
                (canonical_skill_id, skill_name, horizon_months, growth_score, decline_score,
                 confidence_score, first_seen_at, last_seen_at, source_payload)
            VALUES %s
            ON CONFLICT (skill_name, horizon_months) DO UPDATE SET
                canonical_skill_id = EXCLUDED.canonical_skill_id,
                growth_score = EXCLUDED.growth_score,
                decline_score = EXCLUDED.decline_score,
                confidence_score = EXCLUDED.confidence_score,
                first_seen_at = LEAST(COALESCE(skill_trend_forecast.first_seen_at, EXCLUDED.first_seen_at), COALESCE(EXCLUDED.first_seen_at, skill_trend_forecast.first_seen_at)),
                last_seen_at = GREATEST(COALESCE(skill_trend_forecast.last_seen_at, EXCLUDED.last_seen_at), COALESCE(EXCLUDED.last_seen_at, skill_trend_forecast.last_seen_at)),
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            normalized_rows,
        )
    return len(normalized_rows)


def _persist_generic_forecasts(records: list[MarketForecastRecord], *, db_name: str | None = None) -> int:
    if not records:
        return 0
    return persist_market_forecasts(records, db_name=db_name)


def _persist_named_forecasts(table_name: str, records: list[MarketForecastRecord], *, db_name: str | None = None) -> int:
    if not records or not relation_exists(table_name, db_name=db_name):
        return 0
    rows: list[tuple[Any, ...]] = []
    for record in records:
        rows.append(
            (
                record.entity_name,
                record.horizon_months,
                record.growth_velocity,
                record.forecast_confidence,
                record.market_phase,
                record.first_seen_at,
                record.last_seen_at,
                Json(_json_safe(record.evidence), dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
            )
        )
    with cursor(db_name=db_name) as cur:
        execute_values(
            cur,
            f"""
            INSERT INTO {table_name}
                (entity_name, horizon_months, growth_velocity, forecast_confidence, market_phase,
                 first_seen_at, last_seen_at, source_payload)
            VALUES %s
            ON CONFLICT (entity_name, horizon_months) DO UPDATE SET
                growth_velocity = EXCLUDED.growth_velocity,
                forecast_confidence = EXCLUDED.forecast_confidence,
                market_phase = EXCLUDED.market_phase,
                first_seen_at = LEAST(COALESCE({table_name}.first_seen_at, EXCLUDED.first_seen_at), COALESCE(EXCLUDED.first_seen_at, {table_name}.first_seen_at)),
                last_seen_at = GREATEST(COALESCE({table_name}.last_seen_at, EXCLUDED.last_seen_at), COALESCE(EXCLUDED.last_seen_at, {table_name}.last_seen_at)),
                source_payload = EXCLUDED.source_payload,
                updated_at = now()
            """,
            rows,
        )
    return len(rows)


def build_forecast_expansion(*, db_name: str | None = None, persist: bool = True, limit: int = 50) -> ForecastExpansionBundle:
    skill_records = _dedupe_records(_skill_forecast_records(db_name=db_name, limit=limit))
    technology_records = _dedupe_records(_build_technology_forecasts(db_name=db_name))
    company_records = _dedupe_records(_build_company_forecasts(db_name=db_name))
    role_records = _dedupe_records(_build_role_forecasts(db_name=db_name))
    bundle = ForecastExpansionBundle(
        skill=skill_records,
        technology=technology_records,
        company=company_records,
        role=role_records,
        generated_at=datetime.now(UTC).isoformat(),
    )
    if persist:
        _persist_generic_forecasts(skill_records + technology_records + company_records + role_records, db_name=db_name)
        _persist_skill_trend_forecasts(skill_records, db_name=db_name)
        _persist_named_forecasts("technology_forecasts", technology_records, db_name=db_name)
        _persist_named_forecasts("company_forecasts", company_records, db_name=db_name)
        _persist_named_forecasts("role_forecasts", role_records, db_name=db_name)
    return bundle


def build_forecast_summary(*, db_name: str | None = None, persist: bool = True, limit: int = 50) -> dict[str, Any]:
    bundle = build_forecast_expansion(db_name=db_name, persist=persist, limit=limit)
    records_by_type: dict[str, list[MarketForecastRecord]] = {
        "skill": bundle.skill,
        "technology": bundle.technology,
        "company": bundle.company,
        "role": bundle.role,
    }
    summary: dict[str, Any] = {
        "generated_at": bundle.generated_at,
        "source_tables": [
            "market_forecasts",
            "skill_trend_forecast",
            "technology_forecasts",
            "company_forecasts",
            "role_forecasts",
            "emerging_technology_observatory",
            "company_observatory",
            "semantic_role_graph",
            "career_transitions",
        ],
        "total_records": sum(len(records) for records in records_by_type.values()),
        "counts": {entity_type: len(records) for entity_type, records in records_by_type.items()},
        "top_skills": [record.to_dict() for record in sorted(bundle.skill, key=lambda item: (item.growth_velocity, item.forecast_confidence), reverse=True)[:10]],
        "top_technologies": [record.to_dict() for record in sorted(bundle.technology, key=lambda item: (item.growth_velocity, item.forecast_confidence), reverse=True)[:10]],
        "top_companies": [record.to_dict() for record in sorted(bundle.company, key=lambda item: (item.growth_velocity, item.forecast_confidence), reverse=True)[:10]],
        "top_roles": [record.to_dict() for record in sorted(bundle.role, key=lambda item: (item.growth_velocity, item.forecast_confidence), reverse=True)[:10]],
    }
    summary["coverage"] = {
        "skill": round(len(bundle.skill) / max(summary["total_records"], 1), 4),
        "technology": round(len(bundle.technology) / max(summary["total_records"], 1), 4),
        "company": round(len(bundle.company) / max(summary["total_records"], 1), 4),
        "role": round(len(bundle.role) / max(summary["total_records"], 1), 4),
    }
    return summary
