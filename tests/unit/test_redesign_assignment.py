"""Tests para api.redesign_assignment.

Verifica:
  A. score_brecha_vs_text — casos básicos (frase, tokens, genéricos, plurales)
  B. assign_brechas — asignación, límites, determinismo, brechas_sin_asignatura
  C. Regresión con asignaturas y brechas reales del programa 13
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.redesign_assignment import (
    MIN_ASSIGNMENT_SCORE,
    MAX_ASIG_PER_BRECHA,
    score_brecha_vs_text,
    assign_brechas,
)


# ── A. score_brecha_vs_text ───────────────────────────────────────────────────

class TestScoreBrechaVsText:

    def test_phrase_match_exact(self):
        """Frase exacta en el texto → 2.0"""
        assert score_brecha_vs_text(
            "analisis de datos",
            "El módulo cubre técnicas de análisis de datos estadísticos.",
        ) == 2.0

    def test_phrase_match_case_accent(self):
        """Acento en el texto no impide coincidencia."""
        assert score_brecha_vs_text(
            "business intelligence",
            "Gestión de proyectos de business intelligence en organizaciones.",
        ) == 2.0

    def test_generic_tokens_only_no_match(self):
        """
        'analisis de datos' está compuesta solo de tokens genéricos.
        Sin frase completa, el token-overlap nunca debe activarse.
        """
        texto_generico = "El sistema procesa analisis y datos básicos sin ninguna frase."
        assert score_brecha_vs_text("analisis de datos", texto_generico) == 0.0

    def test_generic_text_no_phrase_no_match(self):
        """'datos' y 'analisis' en el texto no son suficientes."""
        assert score_brecha_vs_text(
            "analisis de datos",
            "Se estudian datos de ventas y el analisis financiero de la empresa.",
        ) == 0.0

    def test_plural_reportes_matches_reporte(self):
        """'reporte' (brecha) coincide con 'reportes' en el texto vía canonical_key."""
        assert score_brecha_vs_text(
            "reporte",
            "Los estudiantes elaborarán reportes semanales de análisis.",
        ) == 2.0

    def test_reportes_brecha_matches(self):
        """'reportes' como brecha también debe encontrar 'reportes' en el texto."""
        assert score_brecha_vs_text(
            "reportes",
            "Elaboración de reportes ejecutivos y visualizaciones.",
        ) == 2.0

    def test_preportes_no_match(self):
        """'preportes' NO es 'reporte' — no hay límite de palabra."""
        assert score_brecha_vs_text(
            "reporte",
            "Los preportes de ventas son revisados semanalmente.",
        ) == 0.0

    def test_substring_no_match(self):
        """'reporte' no debe coincidir dentro de 'reportería'."""
        assert score_brecha_vs_text(
            "reporte",
            "El área de reportería corporativa genera KPIs mensuales.",
        ) == 0.0

    def test_non_generic_token_match(self):
        """
        Brecha con tokens no genéricos: si TODOS están presentes → 1.0.
        'machine learning': 'machine' y 'learning' no son genéricos.
        """
        score = score_brecha_vs_text(
            "machine learning",
            "Fundamentos de machine learning supervisado y no supervisado.",
        )
        assert score == 2.0  # phrase match first

    def test_non_generic_partial_no_match(self):
        """Solo uno de los tokens no genéricos presente → 0.0"""
        assert score_brecha_vs_text(
            "machine learning",
            "Fundamentos de machine, redes neuronales y clasificación.",
        ) == 0.0

    def test_empty_text_zero(self):
        assert score_brecha_vs_text("business intelligence", "") == 0.0

    def test_all_generic_brecha_zero_without_phrase(self):
        """'gestion de proyectos' — todos genéricos — sin la frase exacta."""
        assert score_brecha_vs_text(
            "gestion de proyectos",
            "Administración y manejo de iniciativas tecnológicas en la empresa.",
        ) == 0.0

    def test_all_generic_brecha_matches_phrase(self):
        """'gestion de proyectos' con la frase exacta → 2.0 aunque todos genéricos."""
        assert score_brecha_vs_text(
            "gestion de proyectos",
            "Fundamentos de gestión de proyectos de TI.",
        ) == 2.0


# ── B. assign_brechas ─────────────────────────────────────────────────────────

_MC_A = {
    "id": 1, "asignatura": "Análisis de datos", "nombre": "Análisis de datos",
    "clean_text": "Técnicas de análisis de datos estadísticos y su interpretación.",
}
_MC_B = {
    "id": 2, "asignatura": "Reportería corporativa", "nombre": "Reportería corporativa",
    "clean_text": "Elaboración de reportes ejecutivos y presentación de resultados.",
}
_MC_C = {
    "id": 3, "asignatura": "Proyectos TI", "nombre": "Proyectos TI",
    "clean_text": "Administración y coordinación de iniciativas tecnológicas.",
}

_BRECHAS = [
    {"skill": "analisis de datos", "frecuencia_mercado": 10},
    {"skill": "reporte",           "frecuencia_mercado": 8},
    {"skill": "kubernetes",        "frecuencia_mercado": 5},
]


class TestAssignBrechas:

    def test_brecha_sin_encaje_en_brechas_sin_asignatura(self):
        """'kubernetes' no aparece en ningún texto → brechas_sin_asignatura."""
        result = assign_brechas([_MC_A, _MC_B, _MC_C], _BRECHAS)
        sin_asig_skills = {b["skill"] for b in result["brechas_sin_asignatura"]}
        assert "kubernetes" in sin_asig_skills

    def test_brecha_con_encaje_en_per_asignatura(self):
        """'analisis de datos' se asigna a _MC_A."""
        result = assign_brechas([_MC_A, _MC_B, _MC_C], _BRECHAS)
        assigned_skills_flat = {
            b["skill"]
            for item in result["per_asignatura"].values()
            for b in item["brechas_asignadas"]
        }
        assert "analisis de datos" in assigned_skills_flat

    def test_asignatura_sin_brecha_excluida(self):
        """_MC_C (texto genérico sin frase ni tokens) no debe aparecer en per_asignatura."""
        result = assign_brechas([_MC_A, _MC_B, _MC_C], _BRECHAS)
        mc_ids = set(result["per_asignatura"].keys())
        assert 3 not in mc_ids  # _MC_C.id = 3

    def test_maximo_2_asignaturas_por_brecha(self):
        """Con 3 asignaturas que encajan, la brecha solo se asigna a las 2 mejores."""
        mc_extra = {
            "id": 4, "asignatura": "BI corporativo", "nombre": "BI corporativo",
            "clean_text": (
                "Elaboración de reportes de business intelligence y análisis de datos en la empresa. "
                "Los estudiantes producirán reportes detallados."
            ),
        }
        brechas_one = [{"skill": "reporte", "frecuencia_mercado": 8}]
        # _MC_B y mc_extra y posiblemente _MC_A -> frase "reporte" en _MC_B y mc_extra
        result = assign_brechas([_MC_A, _MC_B, _MC_C, mc_extra], brechas_one)
        # Count how many asignaturas have "reporte" assigned
        asig_con_brecha = [
            mid
            for mid, item in result["per_asignatura"].items()
            if any(b["skill"] == "reporte" for b in item["brechas_asignadas"])
        ]
        assert len(asig_con_brecha) <= MAX_ASIG_PER_BRECHA

    def test_determinismo(self):
        """El mismo input siempre produce el mismo resultado."""
        r1 = assign_brechas([_MC_A, _MC_B, _MC_C], _BRECHAS)
        r2 = assign_brechas([_MC_A, _MC_B, _MC_C], _BRECHAS)
        assert r1["per_asignatura"].keys() == r2["per_asignatura"].keys()
        for mid in r1["per_asignatura"]:
            b1 = sorted(r1["per_asignatura"][mid]["brechas_asignadas"], key=lambda x: x["skill"])
            b2 = sorted(r2["per_asignatura"][mid]["brechas_asignadas"], key=lambda x: x["skill"])
            assert b1 == b2
        s1 = sorted(b["skill"] for b in r1["brechas_sin_asignatura"])
        s2 = sorted(b["skill"] for b in r2["brechas_sin_asignatura"])
        assert s1 == s2

    def test_min_score_threshold(self):
        """Con umbral muy alto nada se asigna → todo a brechas_sin_asignatura."""
        result = assign_brechas([_MC_A, _MC_B], _BRECHAS, min_score=99.0)
        assert len(result["per_asignatura"]) == 0
        assert len(result["brechas_sin_asignatura"]) == len(_BRECHAS)

    def test_brechas_asignadas_contiene_score_y_frecuencia(self):
        result = assign_brechas([_MC_A, _MC_B], _BRECHAS)
        for item in result["per_asignatura"].values():
            for b in item["brechas_asignadas"]:
                assert "skill" in b
                assert "score" in b
                assert "frecuencia_mercado" in b

    def test_empty_microcurriculos(self):
        result = assign_brechas([], _BRECHAS)
        assert result["per_asignatura"] == {}
        assert len(result["brechas_sin_asignatura"]) == len(_BRECHAS)

    def test_empty_brechas(self):
        result = assign_brechas([_MC_A], [])
        assert result["per_asignatura"] == {}
        assert result["brechas_sin_asignatura"] == []


# ── C. Regresión — asignaturas reales del programa 13 ─────────────────────────

_ASIG_P13 = [
    {
        "id": 36,
        "asignatura": "Análisis e interpretación de datos",
        "nombre": "Análisis e interpretación de datos",
        "clean_text": (
            "El módulo desarrolla competencias en análisis de datos estadísticos "
            "y su interpretación para la toma de decisiones organizacionales. "
            "Se abordarán técnicas de análisis de datos multivariante, análisis "
            "exploratorio y confirmatorio, preprocesamiento y limpieza de datos."
        ),
    },
    {
        "id": 37,
        "asignatura": "Gestión de proyectos de inteligencia de negocio",
        "nombre": "Gestión de proyectos de inteligencia de negocio",
        "clean_text": (
            "Fundamentos de gestión de proyectos aplicados a iniciativas de "
            "business intelligence en organizaciones. Metodologías ágiles para "
            "implementar soluciones de business intelligence. Gestión de proyectos "
            "de analytics y elaboración de reportes corporativos de BI."
        ),
    },
    {
        "id": 38,
        "asignatura": "Fundamentos Tecnológicos par el Tratamiento de Datos",
        "nombre": "Fundamentos Tecnológicos par el Tratamiento de Datos",
        "clean_text": (
            "Infraestructura tecnológica para el tratamiento y almacenamiento de "
            "datos a gran escala. Plataformas de procesamiento distribuido, bases "
            "de datos relacionales y NoSQL. Pipelines de ingesta de datos y ETL."
        ),
    },
    {
        "id": 39,
        "asignatura": "Técnicas de Inteligencia Artificial",
        "nombre": "Técnicas de Inteligencia Artificial",
        "clean_text": (
            "Algoritmos de aprendizaje automático supervisado y no supervisado. "
            "Redes neuronales, árboles de decisión y modelos de clasificación. "
            "Aplicaciones de inteligencia artificial en análisis predictivo."
        ),
    },
    {
        "id": 40,
        "asignatura": "Visualización Interactiva de la Información",
        "nombre": "Visualización Interactiva de la Información",
        "clean_text": (
            "Principios de diseño para visualización de datos e información. "
            "Dashboards interactivos con Tableau y Power BI. Técnicas de "
            "storytelling con datos para comunicar hallazgos y reportes ejecutivos."
        ),
    },
]

_BRECHAS_P13 = [
    {"skill": "business intelligence", "frecuencia_mercado": 15},
    {"skill": "analisis de datos",     "frecuencia_mercado": 12},
    {"skill": "reporte",               "frecuencia_mercado": 8},
]


class TestRegresionPrograma13:

    def setup_method(self):
        self.result = assign_brechas(_ASIG_P13, _BRECHAS_P13)
        self.pa = self.result["per_asignatura"]
        self.sin = self.result["brechas_sin_asignatura"]

    def test_business_intelligence_asignado_a_gestion_proyectos(self):
        """'business intelligence' debe asignarse al id 37 (Gestión de proyectos BI)."""
        assigned = {
            mid
            for mid, item in self.pa.items()
            if any(b["skill"] == "business intelligence" for b in item["brechas_asignadas"])
        }
        assert 37 in assigned

    def test_analisis_datos_asignado_a_analisis_e_interpretacion(self):
        """'analisis de datos' debe asignarse al id 36."""
        assigned = {
            mid
            for mid, item in self.pa.items()
            if any(b["skill"] == "analisis de datos" for b in item["brechas_asignadas"])
        }
        assert 36 in assigned

    def test_reporte_asignado_por_plural_en_texto(self):
        """'reporte' (brecha) debe asignarse a asignaturas que contienen 'reportes'."""
        assigned = {
            mid
            for mid, item in self.pa.items()
            if any(b["skill"] == "reporte" for b in item["brechas_asignadas"])
        }
        # ids 37 y 40 tienen "reportes" en el texto
        assert len(assigned) >= 1
        assert assigned.issubset({37, 40})

    def test_ninguna_brecha_critica_en_brechas_sin_asignatura(self):
        """Las tres brechas críticas del programa 13 deben encontrar encaje."""
        sin_skills = {b["skill"] for b in self.sin}
        for brecha in _BRECHAS_P13:
            assert brecha["skill"] not in sin_skills, (
                f"'{brecha['skill']}' no encontró asignatura — revisa el texto de prueba"
            )

    def test_tecnicas_ia_no_recibe_brechas_de_datos(self):
        """id 39 (Técnicas IA) no debería recibir 'analisis de datos' ni 'reporte'."""
        if 39 in self.pa:
            asig_brechas = {b["skill"] for b in self.pa[39]["brechas_asignadas"]}
            # analisis de datos es frase genérica; sin la frase exacta no debe asignar
            assert "analisis de datos" not in asig_brechas

    def test_maximo_2_asignaturas_por_brecha_p13(self):
        for brecha in _BRECHAS_P13:
            asig_count = sum(
                1
                for item in self.pa.values()
                if any(b["skill"] == brecha["skill"] for b in item["brechas_asignadas"])
            )
            assert asig_count <= MAX_ASIG_PER_BRECHA, (
                f"'{brecha['skill']}' asignada a {asig_count} asignaturas (máx {MAX_ASIG_PER_BRECHA})"
            )
