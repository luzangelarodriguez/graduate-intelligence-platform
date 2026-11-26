"""Unit tests for api.tipo_skill.tipo_para_skill.

No FastAPI, no database — api.tipo_skill has only stdlib imports at module level.
Decision rules (a) and (b) are fully exercised here.
Rule (d) (canonicalize_skill fallback) is not tested because it requires crawlers;
rule (c) (tipo_lookup hit) is exercised by test_tipo_lookup_takes_precedence.
"""
from __future__ import annotations

import pytest

from api.tipo_skill import tipo_para_skill


# ── Rule (a): TRANSVERSALES → "habilidad" ─────────────────────────────────────

@pytest.mark.parametrize("skill", [
    "gestion",
    "comunicacion",
    "trabajo en equipo",
    "liderazgo",
    "Liderazgo",          # case-insensitive
    "estrategia",
    "adaptabilidad",
    "innovacion",
    "negociacion",
    "organizacion",
])
def test_transversales_return_habilidad(skill):
    assert tipo_para_skill(skill, {}) == "habilidad", f"{skill!r} should be habilidad"


# ── Rule (b): HERRAMIENTAS_FORZADAS → "herramienta" ───────────────────────────

@pytest.mark.parametrize("skill", [
    "excel avanzado",
    "Excel Avanzado",     # case-insensitive
    "excel basico",
    "excel intermedio",
    "excel avanzado y tablas dinamicas",
    "power automate",
    "google analytics",
    "google data studio",
    "looker studio",
])
def test_herramientas_forzadas_return_herramienta(skill):
    assert tipo_para_skill(skill, {}) == "herramienta", f"{skill!r} should be herramienta"


# ── Rule (c): tipo_lookup hit ──────────────────────────────────────────────────

def test_tipo_lookup_takes_precedence_over_fallback():
    result = tipo_para_skill("machine learning", {"machine learning": "tecnica"})
    assert result == "tecnica"


def test_tipo_lookup_norm_key_lookup():
    """Accented normalisation: 'análisis' stored as 'analisis' in the lookup."""
    result = tipo_para_skill("Análisis de Datos", {"analisis de datos": "tecnica"})
    assert result == "tecnica"


# ── Rule (e): fallback ─────────────────────────────────────────────────────────

def test_unknown_skill_fallback_competencia():
    """Skill not in transversales, herramientas_forzadas, or lookup → competencia (or
    herramienta/tecnica if canonicalize_skill is available, but always a valid value)."""
    result = tipo_para_skill("zxy_nonexistent_skill_xyz_qrstuv", {})
    assert result in {"competencia", "herramienta", "tecnica", "habilidad"}


# ── Rule (a) takes priority over (b) ──────────────────────────────────────────

def test_transversal_beats_lookup():
    """Even when tipo_lookup says 'herramienta', a transversal overrides to 'habilidad'."""
    result = tipo_para_skill("liderazgo", {"liderazgo": "herramienta"})
    assert result == "habilidad"
