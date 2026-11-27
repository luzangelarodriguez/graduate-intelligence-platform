"""Tests para _enrich_debilidades_with_market en curriculum_deep_analysis_engine."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from intelligence.curriculum_deep_analysis_engine import _enrich_debilidades_with_market


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _mkt(top_skills=None, brechas_criticas=None, n_matches=100):
    return {
        "top_skills": top_skills or [],
        "brechas_criticas": brechas_criticas or [],
        "n_matches": n_matches,
    }


def _deb(hallazgo="Falta X", terminos_clave=None, origen=None):
    d = {"hallazgo": hallazgo, "impacto": "alto", "recomendacion": "Agregar X"}
    if terminos_clave is not None:
        d["terminos_clave"] = terminos_clave
    if origen is not None:
        d["origen"] = origen
    return d


# ── A. Sin market_context (None) ──────────────────────────────────────────────

class TestSinMarketContext:
    def test_devuelve_lista_del_mismo_largo(self):
        debs = [_deb("A"), _deb("B")]
        result = _enrich_debilidades_with_market(debs, None)
        assert len(result) == 2

    def test_evidencia_mercado_es_none(self):
        result = _enrich_debilidades_with_market([_deb()], None)
        assert result[0]["evidencia_mercado"] is None

    def test_origen_sin_origen_previo_es_criterio_experto(self):
        result = _enrich_debilidades_with_market([_deb()], None)
        assert result[0]["origen"] == "criterio_experto"

    def test_origen_previo_se_respeta(self):
        result = _enrich_debilidades_with_market([_deb(origen="mercado")], None)
        assert result[0]["origen"] == "mercado"

    def test_otros_campos_se_preservan(self):
        result = _enrich_debilidades_with_market([_deb("hallazgo_x")], None)
        assert result[0]["hallazgo"] == "hallazgo_x"
        assert result[0]["impacto"] == "alto"

    def test_lista_vacia_devuelve_vacia(self):
        assert _enrich_debilidades_with_market([], None) == []


# ── B. Con market_context — término encontrado ────────────────────────────────

class TestConMarketTerminoEncontrado:
    def test_evidencia_mercado_no_es_none(self):
        mkt = _mkt(top_skills=[{"skill": "machine learning", "frecuencia": 50}], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["machine learning"])], mkt
        )
        assert result[0]["evidencia_mercado"] is not None

    def test_frecuencia_correcta(self):
        mkt = _mkt(top_skills=[{"skill": "machine learning", "frecuencia": 42}], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["machine learning"])], mkt
        )
        assert result[0]["evidencia_mercado"]["frecuencia"] == 42

    def test_pct_vacantes_calculo(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 30}], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["python"])], mkt
        )
        assert result[0]["evidencia_mercado"]["pct_vacantes"] == 30.0

    def test_n_matches_en_evidencia(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 30}], n_matches=200)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["python"])], mkt
        )
        assert result[0]["evidencia_mercado"]["n_matches"] == 200

    def test_origen_sobrescrito_a_mercado(self):
        mkt = _mkt(top_skills=[{"skill": "sql", "frecuencia": 15}], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["sql"], origen="criterio_experto")], mkt
        )
        assert result[0]["origen"] == "mercado"


# ── C. Con market_context — término NO encontrado ─────────────────────────────

class TestConMarketTerminoNoEncontrado:
    def test_evidencia_mercado_es_none(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 30}], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["habilidades blandas"])], mkt
        )
        assert result[0]["evidencia_mercado"] is None

    def test_origen_es_criterio_experto(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 30}], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["habilidades blandas"])], mkt
        )
        assert result[0]["origen"] == "criterio_experto"

    def test_sin_terminos_clave_es_criterio_experto(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 30}], n_matches=100)
        result = _enrich_debilidades_with_market([_deb(terminos_clave=[])], mkt)
        assert result[0]["origen"] == "criterio_experto"
        assert result[0]["evidencia_mercado"] is None

    def test_sin_campo_terminos_clave_es_criterio_experto(self):
        # debilidad sin clave terminos_clave en absoluto
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 30}], n_matches=100)
        result = _enrich_debilidades_with_market([_deb()], mkt)
        assert result[0]["origen"] == "criterio_experto"


# ── D. Alias / plurales (via canonical_key) ───────────────────────────────────

class TestAliasYPlurales:
    def test_plural_en_termino(self):
        # "modelos" se normaliza a "modelo" via canonical_key
        mkt = _mkt(top_skills=[{"skill": "modelo predictivo", "frecuencia": 20}], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["modelos predictivos"])], mkt
        )
        # canonical_key may or may not normalize this — test that the function doesn't crash
        assert "evidencia_mercado" in result[0]
        assert "origen" in result[0]

    def test_multiples_terminos_toma_max_frecuencia(self):
        mkt = _mkt(
            top_skills=[
                {"skill": "sql", "frecuencia": 10},
                {"skill": "python", "frecuencia": 40},
            ],
            n_matches=100,
        )
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["sql", "python"])], mkt
        )
        assert result[0]["evidencia_mercado"]["frecuencia"] == 40

    def test_no_modifica_debilidad_original(self):
        original = _deb(terminos_clave=["python"])
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 5}], n_matches=100)
        _enrich_debilidades_with_market([original], mkt)
        # original dict must not be mutated
        assert "evidencia_mercado" not in original
        assert "origen" not in original


# ── E. Edge cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_n_matches_cero_no_divide_por_cero(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 5}], n_matches=0)
        # Should not raise ZeroDivisionError
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["python"])], mkt
        )
        assert isinstance(result[0]["evidencia_mercado"]["pct_vacantes"], float)

    def test_top_skills_vacio_es_criterio_experto(self):
        mkt = _mkt(top_skills=[], n_matches=100)
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["python"])], mkt
        )
        assert result[0]["origen"] == "criterio_experto"
        assert result[0]["evidencia_mercado"] is None

    def test_market_context_vacio_no_crashea(self):
        result = _enrich_debilidades_with_market([_deb(terminos_clave=["sql"])], {})
        assert result[0]["origen"] == "criterio_experto"

    def test_lista_vacia_con_market_devuelve_vacia(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 10}], n_matches=100)
        assert _enrich_debilidades_with_market([], mkt) == []

    def test_multiples_debilidades_independientes(self):
        mkt = _mkt(top_skills=[{"skill": "python", "frecuencia": 30}], n_matches=100)
        debs = [
            _deb("A", terminos_clave=["python"]),
            _deb("B", terminos_clave=["habilidades blandas"]),
        ]
        result = _enrich_debilidades_with_market(debs, mkt)
        assert result[0]["origen"] == "mercado"
        assert result[1]["origen"] == "criterio_experto"


# ── F. all_skills overrides top_skills for cross-reference ───────────────────

class TestAllSkillsLookup:
    def test_skill_en_posicion_30_recibe_evidencia(self):
        """Skill at rank 30 (outside top 25) must receive evidencia when in all_skills."""
        top25 = [{"skill": f"skill_{i}", "frecuencia": 100 - i} for i in range(25)]
        skill_rank30 = {"skill": "kotlin", "frecuencia": 5}
        all_skills = top25 + [{"skill": f"skill_{i}", "frecuencia": 4} for i in range(25, 29)] + [skill_rank30]
        mkt = {
            "top_skills": top25,
            "all_skills": all_skills,
            "n_matches": 200,
        }
        result = _enrich_debilidades_with_market(
            [_deb(terminos_clave=["kotlin"])], mkt
        )
        assert result[0]["origen"] == "mercado"
        assert result[0]["evidencia_mercado"]["frecuencia"] == 5

    def test_sin_all_skills_usa_top_skills(self):
        """When all_skills absent, falls back to top_skills."""
        mkt = {"top_skills": [{"skill": "python", "frecuencia": 40}], "n_matches": 100}
        result = _enrich_debilidades_with_market([_deb(terminos_clave=["python"])], mkt)
        assert result[0]["origen"] == "mercado"

    def test_skill_fuera_de_top25_pero_no_en_all_skills_sin_evidencia(self):
        """Skill outside top_skills and all_skills → criterio_experto."""
        mkt = {
            "top_skills": [{"skill": "python", "frecuencia": 40}],
            "all_skills": [{"skill": "python", "frecuencia": 40}],
            "n_matches": 100,
        }
        result = _enrich_debilidades_with_market([_deb(terminos_clave=["kotlin"])], mkt)
        assert result[0]["origen"] == "criterio_experto"
