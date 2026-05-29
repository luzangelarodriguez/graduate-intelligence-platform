from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from typing import Any

from intelligence.common import clamp, normalize_key, token_set, jaccard


DEFAULT_COMPANY_ALIASES = {
    "international business machines": "IBM",
    "ibm colombia": "IBM",
    "ibm corp": "IBM",
    "ibm": "IBM",
    "seti sas": "SETI",
    "seti": "SETI",
    "ginko financial solutions sas": "GINKO FINANCIAL SOLUTIONS",
    "ginko financial solutions": "GINKO FINANCIAL SOLUTIONS",
    "indra colombia ltda": "Indra",
    "indra colombia": "Indra",
    "indra": "Indra",
    "cs3 sas": "CS3",
    "cs3": "CS3",
    "talento solido": "TALENTO SOLIDO",
    "venta equipos": "Venta Equipos",
}

NOISE_PATTERNS = re.compile(
    r"\b(rol:|requisitos:|responsabilidades:?|condiciones laborales|modalidad de trabajo|salario:|experiencia laboral)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CompanyResolution:
    original_company: str
    canonical_company_name: str
    company_resolution_confidence: float
    inferred_company: str
    resolution_method: str
    company_aliases: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_company(value: str | None) -> str:
    value = re.sub(r"\s+", " ", value or "").strip(" .,-|")
    value = re.sub(r"\b(s\.?a\.?s\.?|s\.?a\.?|ltda\.?|inc\.?|corp\.?|colombia|latam)\b", "", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip(" .,-|")


def _extract_from_context(text: str) -> str:
    patterns = (
        r"\b(?:en|para)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ0-9&.,\- ]{2,55})\s+(?:buscamos|requiere|solicita|nos encontramos)",
        r"\b([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ0-9&.,\- ]{2,55})\s+(?:requiere|busca|solicita)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text or "")
        if match:
            candidate = _clean_company(match.group(1))
            if candidate and len(candidate) <= 70 and not NOISE_PATTERNS.search(candidate):
                return candidate
    return ""


def resolve_company(
    value: str | None,
    *,
    context_text: str = "",
    known_aliases: dict[str, str] | None = None,
    known_companies: list[str] | None = None,
) -> CompanyResolution:
    aliases = {**DEFAULT_COMPANY_ALIASES, **(known_aliases or {})}
    original = re.sub(r"\s+", " ", value or "").strip()
    if not original or normalize_key(original) in {"no especificada", "unknown", "na", "n a"}:
        inferred = _extract_from_context(context_text)
        if inferred:
            return CompanyResolution(original, inferred, 0.58, inferred, "contextual_inference", [inferred])
        return CompanyResolution(original, "No especificada", 0.0, "", "missing", [])
    if len(original) > 90 or len(original.split()) > 10 or NOISE_PATTERNS.search(original):
        inferred = _extract_from_context(context_text)
        canonical = inferred or "No especificada"
        return CompanyResolution(original, canonical, 0.45 if inferred else 0.1, inferred, "sanitized_contextual" if inferred else "sanitized_noise", [canonical] if inferred else [])

    cleaned = _clean_company(original)
    key = normalize_key(cleaned)
    if key in aliases:
        return CompanyResolution(original, aliases[key], 0.95, "", "alias_exact", [cleaned])

    candidates = known_companies or list(set(aliases.values()))
    best_company = ""
    best_score = 0.0
    for company in candidates:
        score = max(
            SequenceMatcher(None, normalize_key(company), key).ratio(),
            jaccard(token_set(company), token_set(key)),
        )
        if score > best_score:
            best_company = company
            best_score = score
    if best_company and best_score >= 0.82:
        return CompanyResolution(original, best_company, clamp(best_score), "", "fuzzy_match", [cleaned, best_company])
    return CompanyResolution(original, cleaned or original, 0.72, "", "normalized", [cleaned or original])


def resolve_companies(rows: list[dict[str, Any]]) -> list[CompanyResolution]:
    known = [row.get("company") or row.get("canonical_company_name") or "" for row in rows]
    return [
        resolve_company(
            row.get("company") or row.get("normalized_company"),
            context_text=" ".join([str(row.get("title") or ""), str(row.get("description") or "")]),
            known_companies=known,
        )
        for row in rows
    ]
