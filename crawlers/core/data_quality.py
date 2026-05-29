from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any

from agents.visual_analytics_labor_agent import AgentExtractionResult
from ml.labor.semantic_job_skill_extractor import extract_semantic_job_skills
from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text


def canonical_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def canonical_job_key(*, title: str, company: str, location: str) -> str:
    return normalize_text(f"{title}|{company}|{location}")


def job_fingerprint(*, title: str, company: str, location: str, description: str) -> str:
    payload = normalize_text(f"{title}|{company}|{location}|{description[:2000]}")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_salary(value: str | None) -> dict[str, Any]:
    text = canonical_text(value)
    numbers = [int(item.replace(".", "").replace(",", "")) for item in re.findall(r"\d[\d.,]*", text)]
    currency = "COP" if "$" in text or "cop" in text.casefold() else ""
    return {
        "raw": text,
        "min": min(numbers) if numbers else None,
        "max": max(numbers) if numbers else None,
        "currency": currency,
    }


def normalize_location(value: str | None) -> dict[str, str]:
    text = canonical_text(value)
    lowered = normalize_text(text)
    country = "Colombia" if "colombia" in lowered or not text else ""
    city = ""
    for candidate in ("Bogota", "Medellin", "Cali", "Barranquilla", "Bucaramanga", "Remoto"):
        if normalize_text(candidate) in lowered:
            city = candidate
            break
    return {"raw": text, "city": city, "country": country}


def completeness_score(job: dict[str, Any]) -> float:
    fields = ("title", "company", "location", "description", "source_url")
    present = sum(1 for field in fields if canonical_text(str(job.get(field, ""))))
    description_bonus = 1 if len(canonical_text(str(job.get("description", "")))) >= 120 else 0
    return round((present + description_bonus) / (len(fields) + 1), 4)


def validate_minimum_fields(job: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = [field for field in ("title", "company", "description", "source_url") if not canonical_text(str(job.get(field, "")))]
    if len(canonical_text(str(job.get("description", "")))) < 40:
        missing.append("description_min_length")
    return not missing, missing


def unified_skill_taxonomy(text: str) -> list[str]:
    return sorted({item.skill for item in extract_semantic_job_skills(description=text, evidence_source_type="job_evidence")})


@dataclass(frozen=True)
class QualityEnvelope:
    content_hash: str
    canonical_key: str
    completeness_score: float
    valid_minimum_fields: bool
    validation_errors: list[str]
    normalized_salary: dict[str, Any]
    normalized_location: dict[str, str]
    unified_skills: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_quality_envelope(result: AgentExtractionResult) -> QualityEnvelope:
    job = {
        "title": result.silver.normalized_title,
        "company": result.silver.normalized_company,
        "location": result.silver.normalized_location,
        "description": result.silver.normalized_description,
        "source_url": result.silver.source_url,
    }
    valid, errors = validate_minimum_fields(job)
    return QualityEnvelope(
        content_hash=job_fingerprint(
            title=job["title"],
            company=job["company"],
            location=job["location"],
            description=job["description"],
        ),
        canonical_key=canonical_job_key(title=job["title"], company=job["company"], location=job["location"]),
        completeness_score=completeness_score(job),
        valid_minimum_fields=valid,
        validation_errors=errors,
        normalized_salary=normalize_salary(str(result.silver.contextual.get("salary", ""))),
        normalized_location=normalize_location(job["location"]),
        unified_skills=unified_skill_taxonomy(job["description"]),
    )


def deduplicate_cross_source(results: list[AgentExtractionResult]) -> list[AgentExtractionResult]:
    seen: set[str] = set()
    unique: list[AgentExtractionResult] = []
    for result in results:
        envelope = build_quality_envelope(result)
        if envelope.content_hash in seen:
            continue
        seen.add(envelope.content_hash)
        unique.append(result)
    return unique
