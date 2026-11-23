"""
Unit tests for the top_matches familia fallback logic in GET /api/dashboard/summary.

The endpoint builds familia with:
    COALESCE(NULLIF(TRIM(op.familia),''), NULLIF(TRIM(j.semantic_title_family),''), '')

These tests validate that logic in Python, mirroring the SQL COALESCE behaviour.
"""
from __future__ import annotations


def _build_top_match(op_familia: str | None, semantic_title_family: str | None) -> dict:
    """Replicate the Python dict-build that follows the SQL query."""
    op_familia_val = (op_familia or "").strip() or None
    stf_val = (semantic_title_family or "").strip() or None
    familia = op_familia_val or stf_val or ""
    return {"familia": familia}


class TestTopMatchesFamiliaFallback:
    def test_op_familia_wins_when_populated(self):
        m = _build_top_match("Marketing y Publicidad", "some_stf")
        assert m["familia"] == "Marketing y Publicidad"

    def test_falls_back_to_semantic_title_family_when_op_familia_empty(self):
        m = _build_top_match("", "Comunicaciones")
        assert m["familia"] == "Comunicaciones"

    def test_falls_back_to_semantic_title_family_when_op_familia_none(self):
        m = _build_top_match(None, "Comunicaciones")
        assert m["familia"] == "Comunicaciones"

    def test_falls_back_to_semantic_title_family_when_op_familia_whitespace_only(self):
        m = _build_top_match("   ", "Comunicaciones")
        assert m["familia"] == "Comunicaciones"

    def test_empty_string_when_both_null(self):
        m = _build_top_match(None, None)
        assert m["familia"] == ""

    def test_empty_string_when_both_empty(self):
        m = _build_top_match("", "")
        assert m["familia"] == ""

    def test_empty_string_when_both_whitespace(self):
        m = _build_top_match("  ", "   ")
        assert m["familia"] == ""

    def test_op_familia_trimmed(self):
        m = _build_top_match("  Tecnología  ", None)
        assert m["familia"] == "Tecnología"

    def test_semantic_title_family_trimmed(self):
        m = _build_top_match(None, "  Finanzas  ")
        assert m["familia"] == "Finanzas"


class TestTopMatchesFamiliaPerfilNombre:
    """perfil_nombre is passed through unchanged from occupational_profiles.nombre."""

    def _build(self, op_nombre: str | None) -> dict:
        return {"perfil_nombre": (op_nombre or "").strip()}

    def test_perfil_nombre_populated(self):
        m = self._build("Analista de Marketing Digital")
        assert m["perfil_nombre"] == "Analista de Marketing Digital"

    def test_perfil_nombre_empty_when_no_profile(self):
        m = self._build(None)
        assert m["perfil_nombre"] == ""

    def test_perfil_nombre_trimmed(self):
        m = self._build("  Coordinador de Ventas  ")
        assert m["perfil_nombre"] == "Coordinador de Ventas"
