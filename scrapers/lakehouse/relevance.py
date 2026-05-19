from __future__ import annotations

from typing import Any

try:
    from scrapers.normalization.classify_domains import classify_text_domain
    from scrapers.taxonomy.domain_taxonomy import normalize_text
except ModuleNotFoundError:
    from normalization.classify_domains import classify_text_domain
    from taxonomy.domain_taxonomy import normalize_text


SOURCE_WEIGHTS = {
    "magneto_api": 0.78,
    "magneto": 0.55,
    "elempleo": 0.62,
    "computrabajo": 0.45,
    "servicio_publico_empleo": 0.35,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def evidence_weight(job: dict[str, Any]) -> float:
    score = 0.0
    if job.get("titulo"):
        score += 0.15
    if job.get("empresa"):
        score += 0.12
    if job.get("descripcion") and len(normalize_text(job.get("descripcion")).split()) >= 30:
        score += 0.25
    if job.get("url"):
        score += 0.10
    if job.get("fecha_publicacion"):
        score += 0.08
    if job.get("skills"):
        score += min(0.20, len(job.get("skills", [])) * 0.04)
    if job.get("ciudad") or job.get("modalidad"):
        score += 0.10
    return _clamp(score)


def semantic_density(job: dict[str, Any]) -> float:
    words = max(1, len(normalize_text(job.get("descripcion") or "").split()))
    skill_count = len(set(job.get("skills") or []))
    title_tokens = len(normalize_text(job.get("titulo") or "").split())
    return _clamp((skill_count * 0.18) + min(0.35, words / 240) + min(0.15, title_tokens / 40))


def calculate_relevance_scores(job: dict[str, Any]) -> dict[str, float]:
    domain = classify_text_domain(f"{job.get('titulo','')} {job.get('descripcion','')}")
    scores = {
        "source_weight": SOURCE_WEIGHTS.get(job.get("source") or job.get("portal"), 0.4),
        "evidence_weight": evidence_weight(job),
        "domain_confidence": domain.confidence,
        "semantic_density": semantic_density(job),
    }
    scores["overall_score"] = round(
        scores["source_weight"] * 0.25
        + scores["evidence_weight"] * 0.30
        + scores["domain_confidence"] * 0.25
        + scores["semantic_density"] * 0.20,
        4,
    )
    return {key: round(value, 4) for key, value in scores.items()}

