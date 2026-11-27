"""
Asignación de brechas curriculares a asignaturas por encaje semántico.

Reglas de puntuación (score_brecha_vs_text):
  2.0  — coincidencia de frase completa con límites de palabra (word boundary).
         Los plurales simples se manejan aplicando canonical_key a cada token
         del texto antes de comparar (p. ej. "reportes" → "reporte").
  1.0  — todos los tokens NO genéricos de la brecha están presentes en el
         texto con límite de palabra. Solo aplica si hay ≥ 1 token no genérico.
  0.0  — la brecha tiene solo tokens genéricos y no hay frase completa, o
         ningún token no genérico aparece en el texto.

Asignación (assign_brechas):
  - Cada brecha se asigna a las 1-2 asignaturas con mejor encaje (≥ MIN_ASSIGNMENT_SCORE).
  - Desempate determinista: score DESC → len(clean_text) DESC → mc_id ASC.
  - Asignaturas sin ninguna brecha asignada no se incluyen en el resultado.
  - Brechas sin asignatura se devuelven en "brechas_sin_asignatura".
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from api.skills_analysis_logic import canonical_key

# ── Constantes ────────────────────────────────────────────────────────────────

MIN_ASSIGNMENT_SCORE: float = 0.5
MAX_ASIG_PER_BRECHA: int = 2

# Tokens que por sí solos no discriminan una asignatura.
# Una brecha compuesta solo de estos tokens debe coincidir como frase completa
# para ser asignada; la coincidencia por tokens sueltos queda bloqueada.
GENERIC_TOKENS: frozenset[str] = frozenset({
    "datos", "analisis", "informacion", "gestion", "sistemas",
    "proyectos", "tecnologia", "digital", "empresarial", "negocio",
    "modelo", "proceso", "estrategia", "metodologia", "aplicacion",
    "herramienta", "basico", "avanzado", "general",
})

# Sinónimos de traducción: clave = canonical_key(brecha en inglés) → frases equivalentes en español.
# Cada sinónimo cuenta como coincidencia de frase completa (score 2.0).
# NO usar para modificar SKILL_ALIASES (cambiaría la cobertura de producción).
TEXT_SYNONYMS: dict[str, list[str]] = {
    "business intelligence": [
        "inteligencia de negocio",
        "inteligencia de negocios",
        "inteligencia empresarial",
    ],
    "reporte": [
        "informe",
        "informes",
    ],
    "dashboard": [
        "cuadro de mando",
        "cuadros de mando",
        "tablero de control",
        "tableros de control",
    ],
    "analisis de datos": [
        "analitica de datos",
        "analisis de informacion",
    ],
    "machine learning": [
        "aprendizaje automatico",
    ],
    "big data": [
        "datos masivos",
        "macrodatos",
    ],
    "visualizacion de datos": [
        "data visualization",
    ],
}

# ── Normalización ─────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Lowercase, strip diacritics, collapse whitespace."""
    n = unicodedata.normalize("NFD", s.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", n).strip()


def _norm_text_tokenwise(text: str) -> str:
    """
    Normalize text applying canonical_key to each token so plural forms
    (reportes → reporte) match the normalized brecha key before comparison.
    """
    tokens = _norm(text).split()
    return " ".join(canonical_key(t) for t in tokens)


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_brecha_vs_text(brecha_skill: str, clean_text: str) -> float:
    """
    Return a relevance score (≥ 0.0) for a brecha against a subject's clean_text.

    Scores:
      2.0 → exact phrase match (word boundary, with plural normalization)
      1.0 → all non-generic tokens of the brecha match (word boundary)
      0.0 → no match
    """
    brecha_norm = canonical_key(brecha_skill)
    text_norm   = _norm_text_tokenwise(clean_text)

    # 1. Exact phrase match (word boundaries)
    phrase_pat = r"\b" + re.escape(brecha_norm) + r"\b"
    if re.search(phrase_pat, text_norm):
        return 2.0

    # 2. Synonym phrase match — Spanish equivalents of English skill names (score 2.0)
    for syn in TEXT_SYNONYMS.get(brecha_norm, []):
        syn_norm = _norm_text_tokenwise(syn)
        if re.search(r"\b" + re.escape(syn_norm) + r"\b", text_norm):
            return 2.0

    # 3. All non-generic tokens present (word boundaries)
    tokens      = brecha_norm.split()
    non_generic = [t for t in tokens if t not in GENERIC_TOKENS and len(t) >= 3]

    if not non_generic:
        return 0.0

    all_present = all(
        bool(re.search(r"\b" + re.escape(t) + r"\b", text_norm))
        for t in non_generic
    )
    return 1.0 if all_present else 0.0


# ── Assignment ────────────────────────────────────────────────────────────────

def assign_brechas(
    microcurriculos: list[dict[str, Any]],
    brechas: list[dict[str, Any]],
    min_score: float = MIN_ASSIGNMENT_SCORE,
    max_asig_per_brecha: int = MAX_ASIG_PER_BRECHA,
) -> dict[str, Any]:
    """
    Assign each brecha to the top 1-2 asignaturas with the best fit.

    Parameters
    ----------
    microcurriculos : list of dicts with keys:
        id (int), asignatura (str|None), nombre (str|None), clean_text (str)
    brechas : list of dicts with keys:
        skill (str), frecuencia_mercado (int)
    min_score : minimum score threshold (default MIN_ASSIGNMENT_SCORE)
    max_asig_per_brecha : max asignaturas per brecha (default MAX_ASIG_PER_BRECHA)

    Returns
    -------
    {
        "per_asignatura": {
            mc_id (int): {
                "mc_id": int,
                "asignatura": str,
                "clean_text": str,
                "brechas_asignadas": [
                    {"skill": str, "score": float, "frecuencia_mercado": int}
                ],
            }
        },
        "brechas_sin_asignatura": [{"skill": str, "frecuencia_mercado": int}],
    }
    """
    per_asignatura: dict[int, dict[str, Any]] = {}
    brechas_sin_asignatura: list[dict[str, Any]] = []

    for brecha in brechas:
        skill = brecha["skill"]

        candidates: list[tuple[float, int, int, dict[str, Any]]] = []
        for mc in microcurriculos:
            text = (mc.get("clean_text") or "").strip()
            if not text:
                continue
            sc = score_brecha_vs_text(skill, text)
            if sc >= min_score:
                # Tie-break key: score DESC, text_len DESC, mc_id ASC
                candidates.append((sc, len(text), mc["id"], mc))

        if not candidates:
            brechas_sin_asignatura.append(brecha)
            continue

        candidates.sort(key=lambda x: (-x[0], -x[1], x[2]))
        top = candidates[:max_asig_per_brecha]

        for sc, _, mc_id, mc in top:
            nombre = mc.get("nombre") or mc.get("asignatura") or f"Asignatura {mc_id}"
            if mc_id not in per_asignatura:
                per_asignatura[mc_id] = {
                    "mc_id":             mc_id,
                    "asignatura":        nombre,
                    "clean_text":        mc.get("clean_text", ""),
                    "brechas_asignadas": [],
                }
            per_asignatura[mc_id]["brechas_asignadas"].append({
                "skill":              skill,
                "score":              sc,
                "frecuencia_mercado": brecha.get("frecuencia_mercado", 0),
            })

    return {
        "per_asignatura":         per_asignatura,
        "brechas_sin_asignatura": brechas_sin_asignatura,
    }


def compute_confianza(brechas_asignadas: list[dict[str, Any]]) -> str:
    """
    Returns 'alta' if any brecha was assigned by exact phrase or synonym match (score 2.0),
    'media' if only by token overlap (score 1.0).
    """
    if any(b.get("score", 0) >= 2.0 for b in brechas_asignadas):
        return "alta"
    return "media"
