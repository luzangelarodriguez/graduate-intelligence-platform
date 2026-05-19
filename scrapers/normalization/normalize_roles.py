from __future__ import annotations

import re

try:
    from scrapers.taxonomy.domain_taxonomy import normalize_text
except ModuleNotFoundError:
    from taxonomy.domain_taxonomy import normalize_text


ROLE_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("coordinador sostenibilidad", ("coordinador de sostenibilidad", "lider sostenibilidad", "analista sostenibilidad")),
    ("especialista ambiental", ("especialista ambiental", "profesional ambiental", "consultor ambiental")),
    ("gestor energetico", ("gestor energetico", "especialista energia", "consultor energia")),
    ("analista legal digital", ("abogado digital", "abogado datos", "especialista derecho digital")),
    ("analista business intelligence", ("analista bi", "bi analyst", "business intelligence analyst")),
    ("gerente proyecto", ("project manager", "jefe proyecto", "coordinador proyecto")),
)


def normalize_role(title: str) -> str:
    normalized = normalize_text(title)
    for canonical, aliases in ROLE_ALIASES:
        candidates = (canonical, *aliases)
        for candidate in candidates:
            candidate_norm = normalize_text(candidate)
            if candidate_norm and re.search(rf"(?<![a-z0-9]){re.escape(candidate_norm)}(?![a-z0-9])", normalized):
                return canonical
    return normalized

