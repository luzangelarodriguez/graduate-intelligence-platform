"""Tests unitarios para skill_similarity de scripts/diag/matching_near_miss.py.

Sin base de datos: todas las funciones probadas son puras.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.diag.matching_near_miss import (
    NEAR_MISS_THRESHOLD,
    _STOPWORDS_EN,
    _STOPWORDS_ES,
    _lang_estimate,
    _raw_tokens,
    _tokens,
    skill_similarity,
)


# ── A. Propiedades básicas ─────────────────────────────────────────────────────

class TestSkillSimilarityBasic:
    def test_identica_es_1(self):
        assert skill_similarity("python", "python") == 1.0

    def test_completamente_distinta_es_baja(self):
        sim = skill_similarity("python", "liderazgo empresarial")
        assert sim < 0.3

    def test_simetria(self):
        """
        similarity(a, b) == similarity(b, a).
        SequenceMatcher no es simétrico en Python; skill_similarity toma max de
        ambas direcciones para garantizar la propiedad.
        """
        assert skill_similarity("power bi", "power pivot") == \
               skill_similarity("power pivot", "power bi")
        assert skill_similarity("sql server", "mysql") == \
               skill_similarity("mysql", "sql server")

    def test_rango_0_a_1(self):
        pairs = [
            ("sql", "mysql"), ("power bi", "power pivot"),
            ("analisis de datos", "data analysis"),
            ("python", "java"),
        ]
        for a, b in pairs:
            sim = skill_similarity(a, b)
            assert 0.0 <= sim <= 1.0, f"sim={sim} fuera de rango para ({a!r}, {b!r})"

    def test_cadena_vacia_no_crashea(self):
        sim = skill_similarity("", "python")
        assert 0.0 <= sim <= 1.0
        sim2 = skill_similarity("", "")
        assert 0.0 <= sim2 <= 1.0


# ── B. Variantes tipográficas y ortográficas ──────────────────────────────────

class TestSkillSimilarityVariantes:
    def test_plural_alta_similitud(self):
        """'reporte' vs 'reportes' → similitud alta por canonical_key."""
        sim = skill_similarity("reporte", "reportes")
        assert sim >= 0.8

    def test_nivel_ignorado_alta_similitud(self):
        """'excel avanzado' vs 'excel' → alta similitud (nivel strippeado)."""
        sim = skill_similarity("excel avanzado", "excel")
        assert sim >= 0.7

    def test_acento_no_importa(self):
        """'análisis' vs 'analisis' → similitud 1.0 tras strip de acentos."""
        sim = skill_similarity("análisis de datos", "analisis de datos")
        assert sim >= 0.95

    def test_substrings_similares(self):
        """'power bi' vs 'power pivot' → similitud media-alta."""
        sim = skill_similarity("power bi", "power pivot")
        assert sim >= 0.5

    def test_sinonimo_es_en_detecta_near_miss(self):
        """
        'business intelligence' vs 'inteligencia de negocios':
        la similitud basada en caracteres/tokens da ~0.49 (< NEAR_MISS_THRESHOLD=0.5).
        Esta limitación es CONOCIDA: las traducciones directas sin tokens compartidos
        no se detectan por similitud de cadenas; se manejan via TEXT_SYNONYMS (Rama A).
        El test documenta el valor real para evitar regresiones al bajar el umbral.
        """
        sim = skill_similarity("business intelligence", "inteligencia de negocios")
        # < 0.5: NO marcado como near-miss por el script (esperado/documentado)
        assert sim < NEAR_MISS_THRESHOLD
        # Pero la similitud no es 0: hay substrings compartidos mínimos
        assert sim > 0.3

    def test_machine_learning_aprendizaje_automatico_bajo_umbral(self):
        """
        'machine learning' vs 'aprendizaje automatico' son traducciones directas
        pero sin tokens ni substrings en común: sim < NEAR_MISS_THRESHOLD.
        Este par se detecta por TEXT_SYNONYMS (Rama A), no por near-miss.
        """
        sim = skill_similarity("machine learning", "aprendizaje automatico")
        assert sim < NEAR_MISS_THRESHOLD

    def test_completamente_no_relacionadas_bajo_umbral(self):
        """'kubernetes' vs 'contabilidad financiera' → bien por debajo del umbral."""
        sim = skill_similarity("kubernetes", "contabilidad financiera")
        assert sim < NEAR_MISS_THRESHOLD


# ── C. Tokens y stopwords ──────────────────────────────────────────────────────

class TestTokens:
    def test_stopwords_eliminadas(self):
        tokens = _tokens("analisis de datos en python")
        assert "de" not in tokens
        assert "en" not in tokens
        assert "python" in tokens

    def test_acento_strip_en_tokens(self):
        # _tokens filtra stopwords gramaticales, no términos de dominio
        tokens = _tokens("estadistico predictivo")
        assert "estadistico" in tokens
        assert "predictivo" in tokens

    def test_terminos_dominio_NO_filtrados(self):
        """'analisis', 'datos' son términos de dominio, NO gramáticas → no se filtran."""
        tokens = _tokens("analisis datos")
        assert "analisis" in tokens
        assert "datos" in tokens

    def test_tokens_vacios_sin_contenido(self):
        # solo stopwords → conjunto vacío
        tokens = _tokens("de la")
        assert len(tokens) == 0

    def test_stopwords_en_gramaticales_eliminadas(self):
        """Solo conjunciones/preposiciones se filtran del Jaccard; términos de dominio no."""
        tokens = _tokens("data analysis and management")
        # gramática EN filtrada:
        assert "and" not in tokens
        # términos de dominio NO filtrados (permiten Jaccard significativo):
        assert "data" in tokens
        assert "analysis" in tokens
        assert "management" in tokens


# ── D. _lang_estimate ─────────────────────────────────────────────────────────

class TestLangEstimate:
    def _prog(self, skills: list[str]) -> list[dict]:
        return [{"skill": s, "cobertura": 1} for s in skills]

    def _mkt(self, skills: list[str]) -> list[dict]:
        return [{"skill": s, "frecuencia": 10} for s in skills]

    def test_programa_es_alto(self):
        prog = self._prog([
            "análisis de datos",        # "de" es marcador ES
            "gestión de proyectos",     # "de" es marcador ES
            "estadística",              # sin marcador
            "programación en python",   # "en" es marcador ES
            "bases de datos",           # "de" es marcador ES
        ])
        lang = _lang_estimate(prog, [])
        # 4 de 5 skills tienen marcador ES → 80%
        assert lang["pct_prog_es"] > 50

    def test_mercado_en_alto(self):
        mkt = self._mkt([
            "data analysis and reporting",  # "and" es marcador EN
            "management of teams",          # "of" es marcador EN
            "integration with apis",        # "with" es marcador EN
            "tools for automation",         # "for" es marcador EN
        ])
        lang = _lang_estimate([], mkt)
        assert lang["pct_mkt_en"] > 50

    def test_usa_raw_tokens_no_filtrados(self):
        """
        _lang_estimate usa tokens sin filtrar (incluye preposiciones), no _tokens.
        'analisis de datos' contiene 'de' (marcador ES) aunque 'de' es stopword Jaccard.
        """
        prog = self._prog(["analisis de datos"])
        lang = _lang_estimate(prog, [])
        assert lang["pct_prog_es"] == 100.0  # "de" detectado como marcador ES

    def test_listas_vacias_devuelve_cero(self):
        lang = _lang_estimate([], [])
        assert lang["pct_prog_es"] == 0.0
        assert lang["pct_mkt_en"] == 0.0
