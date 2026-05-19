from __future__ import annotations

import math
from typing import Any

try:
    from scrapers.normalization.classify_domains import classify_text_domain, is_domain_compatible
    from scrapers.taxonomy.domain_taxonomy import normalize_text
except ModuleNotFoundError:
    from normalization.classify_domains import classify_text_domain, is_domain_compatible
    from taxonomy.domain_taxonomy import normalize_text


DEFAULT_SOURCE_QUALITY = {
    "elempleo": 0.72,
    "computrabajo": 0.45,
    "magneto": 0.55,
    "torre": 0.55,
    "servicio_publico_empleo": 0.35,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def description_score(description: str) -> float:
    length = len(normalize_text(description).split())
    if length <= 20:
        return 0.15
    if length >= 180:
        return 1.0
    return _clamp((length - 20) / 160)


def skill_density_score(skills: list[str], description: str) -> float:
    word_count = max(1, len(normalize_text(description).split()))
    density = len(set(skills)) / math.sqrt(word_count)
    return _clamp(density / 1.25)


def alias_score(skill_matches: list[Any]) -> float:
    if not skill_matches:
        return 0.0
    total = len(skill_matches)
    canonical_hits = sum(1 for item in skill_matches if getattr(item, "skill_original", "") == getattr(item, "skill_normalized", ""))
    return _clamp(0.55 + (canonical_hits / total) * 0.45)


def domain_coherence_score(job: dict[str, Any], expected_domain: str | None = None) -> float:
    text = f"{job.get('titulo', '')} {job.get('descripcion', '')}"
    classification = classify_text_domain(text)
    job_domain = job.get("dominio") or classification.primary_domain
    if expected_domain and not is_domain_compatible(expected_domain, job_domain):
        return 0.0
    return classification.confidence


def embedding_similarity_score(job: dict[str, Any]) -> float:
    # Placeholder for a real program/job embedding similarity when contextual program
    # text is available. If an embedding exists, the item is more trustworthy than
    # pure DOM evidence, but it is not treated as semantic relevance by itself.
    return 0.65 if job.get("embedding") else 0.45


def calculate_confidence_score(
    job: dict[str, Any],
    *,
    source_quality: dict[str, float] | None = None,
    expected_domain: str | None = None,
) -> tuple[float, dict[str, float]]:
    source_quality = source_quality or DEFAULT_SOURCE_QUALITY
    skills = list(job.get("skills") or [])
    factors = {
        "source_quality": _clamp(float(source_quality.get(job.get("portal"), 0.4))),
        "skill_density": skill_density_score(skills, job.get("descripcion") or ""),
        "domain_coherence": domain_coherence_score(job, expected_domain=expected_domain),
        "embedding_similarity": embedding_similarity_score(job),
        "description_length": description_score(job.get("descripcion") or ""),
        "alias_strength": alias_score(job.get("skill_matches") or []),
    }
    score = (
        factors["source_quality"] * 0.20
        + factors["skill_density"] * 0.20
        + factors["domain_coherence"] * 0.25
        + factors["embedding_similarity"] * 0.10
        + factors["description_length"] * 0.15
        + factors["alias_strength"] * 0.10
    )
    return round(_clamp(score), 4), {key: round(value, 4) for key, value in factors.items()}

