from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

try:
    from scrapers.discovery.anti_seo_filter import seo_noise_score, vacancy_signal_score
except ModuleNotFoundError:
    from anti_seo_filter import seo_noise_score, vacancy_signal_score


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def flatten_payload(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str).casefold()


def richness_score(payload: Any) -> float:
    if payload is None:
        return 0.0
    if isinstance(payload, list):
        return _clamp(len(payload) / 30)
    if isinstance(payload, dict):
        keys = set(payload.keys())
        depth_bonus = 0.2 if any(isinstance(value, (dict, list)) for value in payload.values()) else 0
        return _clamp((len(keys) / 18) + depth_bonus)
    return 0.1


def freshness_score(payload: Any) -> float:
    blob = flatten_payload(payload)
    if re.search(r"20\d{2}-\d{2}-\d{2}", blob):
        return 0.85
    if any(term in blob for term in ("today", "hoy", "ayer", "semana", "published", "publicado")):
        return 0.65
    return 0.25


def semantic_density_score(payload: Any) -> float:
    blob = flatten_payload(payload)
    labor_terms = (
        "skill",
        "habilidad",
        "requisito",
        "funcion",
        "experiencia",
        "salary",
        "salario",
        "empresa",
        "company",
        "ciudad",
        "modalidad",
    )
    hits = sum(blob.count(term) for term in labor_terms)
    return _clamp(hits / 40)


def extraction_completeness_score(payload: Any) -> float:
    blob = flatten_payload(payload)
    fields = ("title", "titulo", "description", "descripcion", "company", "empresa", "city", "ciudad", "salary", "salario", "url")
    hits = sum(1 for field in fields if field in blob)
    return _clamp(hits / 7)


def rank_endpoint(endpoint: str, payload: Any | None = None) -> dict[str, float | bool]:
    factors = {
        "richness": richness_score(payload),
        "freshness": freshness_score(payload),
        "semantic_density": semantic_density_score(payload),
        "vacancy_quality": vacancy_signal_score(endpoint, payload),
        "extraction_completeness": extraction_completeness_score(payload),
        "seo_noise": seo_noise_score(endpoint, payload),
    }
    score = (
        factors["richness"] * 0.18
        + factors["freshness"] * 0.12
        + factors["semantic_density"] * 0.20
        + factors["vacancy_quality"] * 0.25
        + factors["extraction_completeness"] * 0.20
        - factors["seo_noise"] * 0.25
    )
    return {
        **{key: round(float(value), 4) for key, value in factors.items()},
        "rank_score": round(_clamp(score), 4),
        "seo_noise_flag": bool(factors["seo_noise"] >= 0.55 and factors["vacancy_quality"] < 0.45),
    }

