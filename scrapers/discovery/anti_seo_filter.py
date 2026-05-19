from __future__ import annotations

import json
import re
from typing import Any


SEO_TERMS = (
    "mega-menu",
    "canonical",
    "ogtitle",
    "ogdescription",
    "trabajos en ",
    "empleos en ",
    "ofertas-empleo-de-",
    "seo/v1",
    "_next/static",
    "google-analytics",
    "googletagmanager",
    "doubleclick",
    "permutive",
    "scorecardresearch",
    "facebook.com/tr",
    "pinterest.com",
    "snapchat.com",
    "sentry.io",
)

VACANCY_TERMS = (
    "vacancy",
    "vacante",
    "job",
    "jobs",
    "empleo",
    "offer",
    "oferta",
    "salary",
    "salario",
    "company",
    "empresa",
    "description",
    "descripcion",
    "requirements",
    "requisitos",
)


def normalize_blob(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.casefold()
    return json.dumps(value, ensure_ascii=False, default=str).casefold()


def seo_noise_score(endpoint: str, payload: Any | None = None) -> float:
    blob = f"{endpoint} {normalize_blob(payload)}"
    hits = sum(1 for term in SEO_TERMS if term in blob)
    marketing_density = len(re.findall(r"\b(title|description|canonical|og|seo|menu|landing)\b", blob))
    return min(1.0, (hits * 0.18) + min(0.35, marketing_density * 0.03))


def vacancy_signal_score(endpoint: str, payload: Any | None = None) -> float:
    blob = f"{endpoint} {normalize_blob(payload)}"
    hits = sum(1 for term in VACANCY_TERMS if term in blob)
    structural = 0.0
    if isinstance(payload, dict):
        keys = {str(key).casefold() for key in payload.keys()}
        structural += 0.2 if keys & {"data", "items", "results", "vacancies", "jobs"} else 0
        structural += 0.2 if keys & {"pagination", "page", "total", "total_pages"} else 0
    if isinstance(payload, list) and payload:
        structural += 0.25
    return min(1.0, (hits * 0.06) + structural)


def is_seo_noise(endpoint: str, payload: Any | None = None, *, threshold: float = 0.55) -> bool:
    return seo_noise_score(endpoint, payload) >= threshold and vacancy_signal_score(endpoint, payload) < 0.45

