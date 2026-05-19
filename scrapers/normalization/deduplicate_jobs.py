from __future__ import annotations

import hashlib
from difflib import SequenceMatcher
from typing import Any, Iterable

try:
    from scrapers.taxonomy.domain_taxonomy import normalize_text
except ModuleNotFoundError:
    from taxonomy.domain_taxonomy import normalize_text


def job_content_hash(job: dict[str, Any]) -> str:
    content = " ".join(
        normalize_text(str(job.get(key, "")))
        for key in ("portal", "titulo", "empresa", "ciudad", "descripcion", "url")
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def title_company_key(job: dict[str, Any]) -> str:
    return "|".join(normalize_text(str(job.get(key, ""))) for key in ("titulo", "empresa", "ciudad"))


def skill_overlap(left: Iterable[str], right: Iterable[str]) -> float:
    a = {normalize_text(item) for item in left if item}
    b = {normalize_text(item) for item in right if item}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def are_probable_duplicates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("hash_contenido") and left.get("hash_contenido") == right.get("hash_contenido"):
        return True
    if title_company_key(left) == title_company_key(right):
        return True
    text_ratio = SequenceMatcher(
        None,
        normalize_text(str(left.get("descripcion", ""))),
        normalize_text(str(right.get("descripcion", ""))),
    ).ratio()
    return text_ratio >= 0.92 and skill_overlap(left.get("skills", []), right.get("skills", [])) >= 0.55


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    seen_keys: set[str] = set()
    for job in jobs:
        enriched = dict(job)
        enriched.setdefault("hash_contenido", job_content_hash(enriched))
        key = title_company_key(enriched)
        if enriched["hash_contenido"] in seen_hashes or key in seen_keys:
            continue
        if any(are_probable_duplicates(enriched, existing) for existing in unique):
            continue
        seen_hashes.add(enriched["hash_contenido"])
        seen_keys.add(key)
        unique.append(enriched)
    return unique

