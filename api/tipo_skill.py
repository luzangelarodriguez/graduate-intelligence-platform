"""Pure helper: classify a skill into herramienta | tecnica | competencia | habilidad.

Extracted from dashboard_skills_analysis so the logic can be unit-tested without FastAPI.
"""
from __future__ import annotations

import logging
import unicodedata

logger = logging.getLogger(__name__)

HERRAMIENTAS_FORZADAS: frozenset[str] = frozenset({
    "excel avanzado",
    "excel basico",
    "excel intermedio",
    "excel avanzado y tablas dinamicas",
    "power automate",
    "google analytics",
    "google data studio",
    "looker studio",
})


def _norm_key(skill: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", skill.lower())
        if unicodedata.category(c) != "Mn"
    ).strip()


def tipo_para_skill(skill: str, tipo_lookup: dict[str, str]) -> str:
    """Classify a skill. Decision order:

      (a) TRANSVERSALES → "habilidad"
      (b) HERRAMIENTAS_FORZADAS → "herramienta"
      (c) tipo_lookup (DB-derived, keyed on normalised skill name) → result
      (d) canonicalize_skill taxonomy fallback
      (e) "competencia"
    """
    from api.skills_analysis_logic import is_transversal

    if is_transversal(skill):
        return "habilidad"

    norm = _norm_key(skill)
    if norm in HERRAMIENTAS_FORZADAS:
        return "herramienta"

    result = tipo_lookup.get(norm) or tipo_lookup.get(skill.lower().strip())
    if result is not None:
        return result

    try:
        from crawlers.storage.postgres_warehouse import canonicalize_skill
        from backend.repositories.empleos_repository import _clean_tipo_skill
        _UNCLASSIFIED = {"unknown", "unclassified", ""}
        taxonomy_cat = canonicalize_skill(skill).category
        if taxonomy_cat.lower() not in _UNCLASSIFIED:
            return _clean_tipo_skill(None, taxonomy_cat)
    except Exception as exc:
        logger.warning("tipo_para_skill taxonomy fallback failed for %r: %s", skill, exc)

    return "competencia"
