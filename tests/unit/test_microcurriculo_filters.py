"""Tests para api.microcurriculo_filters.

Verifica:
  A. Predicado Python es_fila_de_prueba — casos positivos (prueba/sandbox)
  B. Predicado Python — casos negativos (microcurrículos V5 reales)
  C. Casos borde (None, "", mezcla mayúsculas/minúsculas)
  D. Estructura del SQL: el filtro aparece en las tres consultas de producción
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.microcurriculo_filters import (
    SQL_FILTRO_NO_PRUEBA,
    SQL_FILTRO_NO_PRUEBA_PARAMS,
    es_fila_de_prueba,
)


# ── A. Casos positivos (11 casos reales de prueba) ───────────────────────────

class TestEsFilaDePruebaPositivos:
    """Filas que deben ser identificadas como prueba."""

    def test_ruta_windows_unidad_c(self):
        assert es_fila_de_prueba(r"C:\Users\luzangela\storage\file.docx", None)

    def test_ruta_windows_unidad_d(self):
        assert es_fila_de_prueba(r"D:\projects\test.docx", None)

    def test_ruta_windows_unidad_e_slash_directo(self):
        assert es_fila_de_prueba(r"E:\storage\microcurriculos\prog13.pdf", "Estadística")

    def test_ruta_local_con_forward_slash(self):
        # Algunos sistemas Windows usan / en lugar de backslash
        assert es_fila_de_prueba("C:/Users/luzangela/storage/file.docx", None)

    def test_source_doc_contiene_test_microcurric_minuscula(self):
        assert es_fila_de_prueba("storage/test_microcurriculos/prog13.docx", None)

    def test_source_doc_contiene_test_microcurric_mayuscula(self):
        assert es_fila_de_prueba("storage/TEST_MICROCURRICULOS/prog13.docx", None)

    def test_source_doc_test_microcurric_mixto(self):
        assert es_fila_de_prueba("server/Test_Microcurric_v1.pdf", None)

    def test_asignatura_programa_academico_mayusculas(self):
        assert es_fila_de_prueba(None, "PROGRAMA ACADÉMICO")

    def test_asignatura_programa_acad_minusculas(self):
        assert es_fila_de_prueba(None, "programa académico de criminología")

    def test_asignatura_programa_acad_mixto(self):
        assert es_fila_de_prueba(None, "Programa Académico General")

    def test_ruta_windows_con_test_microcurric_combinado(self):
        # Fila id=1 real: ruta local Y contiene test_microcurric
        assert es_fila_de_prueba(
            r"C:\Users\luzangela\storage\test_microcurriculos\prog13_v1.docx",
            "PROGRAMA ACADÉMICO",
        )


# ── B. Casos negativos (9 microcurrículos V5 reales del programa 13) ─────────

class TestEsFilaDePruebaNegativosV5:
    """Microcurrículos reales que NO deben ser excluidos."""

    def test_v5_analisis_datos(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_Análisis de datos.docx",
            "Análisis e interpretación de datos",
        )

    def test_v5_visualizacion(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_Visualización.docx",
            "Visualización y comunicación de datos",
        )

    def test_v5_machine_learning(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_ML.docx",
            "Machine Learning aplicado",
        )

    def test_v5_estadistica(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_Estadística.docx",
            "Estadística para analítica",
        )

    def test_v5_programacion(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_Programación.docx",
            "Fundamentos de programación en Python",
        )

    def test_v5_bases_datos(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_BD.docx",
            "Bases de datos y SQL",
        )

    def test_v5_inteligencia_negocios(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_BI.docx",
            "Inteligencia de negocios",
        )

    def test_v5_etica(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_Ética.docx",
            "Ética en ciencia de datos",
        )

    def test_v5_proyecto_final(self):
        assert not es_fila_de_prueba(
            "Microcurrículos V5_Proyecto.docx",
            "Proyecto integrador",
        )


# ── C. Casos borde ────────────────────────────────────────────────────────────

class TestEsFilaDePruebaBorde:
    def test_ambos_none(self):
        assert not es_fila_de_prueba(None, None)

    def test_ambos_vacio(self):
        assert not es_fila_de_prueba("", "")

    def test_source_doc_none_asignatura_normal(self):
        assert not es_fila_de_prueba(None, "Estadística aplicada")

    def test_source_doc_normal_asignatura_none(self):
        assert not es_fila_de_prueba("server/docs/file.pdf", None)

    def test_ruta_relativa_sin_unidad(self):
        # "storage/..." sin letra de unidad no es ruta Windows local
        assert not es_fila_de_prueba("storage/microcurriculos/real.docx", "Asignatura normal")

    def test_asignatura_programa_acad_sin_espacio(self):
        # "PROGRAMAACAD" no cumple (falta espacio)
        assert not es_fila_de_prueba(None, "PROGRAMAACADEMICO")

    def test_source_doc_mayuscula_unidad(self):
        # Letra de unidad en mayúscula también debe detectarse
        assert es_fila_de_prueba("Z:/storage/file.pdf", None)

    def test_source_doc_minuscula_unidad(self):
        assert es_fila_de_prueba("a:/storage/file.pdf", None)

    def test_asignatura_es_programa_acad_con_tilde(self):
        # "PROGRAMA ACADÉMICO" con acento
        assert es_fila_de_prueba(None, "PROGRAMA ACADÉMICO")

    def test_source_doc_es_solo_letra_colon(self):
        # "C:" sin slash posterior — NO debe detectarse como ruta Windows
        assert not es_fila_de_prueba("C:archivo.docx", None)


# ── D. Estructura SQL: el filtro aparece en las tres consultas ────────────────

class TestSqlFiltroEstructura:
    """El fragmento SQL debe estar presente en cada consulta de producción."""

    def test_sql_filtro_no_prueba_es_string(self):
        assert isinstance(SQL_FILTRO_NO_PRUEBA, str)
        assert len(SQL_FILTRO_NO_PRUEBA) > 10

    def test_sql_filtro_params_es_vacio(self):
        assert SQL_FILTRO_NO_PRUEBA_PARAMS == ()

    def test_sql_filtro_contiene_test_microcurric(self):
        assert "test_microcurric" in SQL_FILTRO_NO_PRUEBA.lower()

    def test_sql_filtro_contiene_programa_acad(self):
        assert "programa acad" in SQL_FILTRO_NO_PRUEBA.lower()

    def test_sql_filtro_contiene_regex_unidad(self):
        # El patrón de ruta Windows debe estar en el SQL
        assert "[A-Za-z]:" in SQL_FILTRO_NO_PRUEBA

    def test_prog_skills_sql_contiene_filtro(self):
        """_SQL_PROG_SKILLS en api/main.py debe incluir el filtro."""
        source = Path(PROJECT_ROOT / "api" / "main.py").read_text(encoding="utf-8")
        # Encontrar la definición de _SQL_PROG_SKILLS
        start = source.find("_SQL_PROG_SKILLS =")
        assert start != -1, "_SQL_PROG_SKILLS no encontrado en api/main.py"
        block = source[start:start + 600]
        assert "SQL_FILTRO_NO_PRUEBA" in block or "test_microcurric" in block.lower(), (
            "_SQL_PROG_SKILLS no contiene el filtro SQL_FILTRO_NO_PRUEBA"
        )
        assert "programa acad" in block.lower() or "SQL_FILTRO_NO_PRUEBA" in block

    def test_redesign_sql_contiene_filtro(self):
        """La consulta de _run_redesign en api/main.py debe incluir el filtro."""
        source = Path(PROJECT_ROOT / "api" / "main.py").read_text(encoding="utf-8")
        # Buscar el bloque de _run_redesign y verificar que el filtro está ahí
        redesign_start = source.find("def _run_redesign")
        assert redesign_start != -1
        redesign_block = source[redesign_start:redesign_start + 2000]
        assert "SQL_FILTRO_NO_PRUEBA" in redesign_block or "test_microcurric" in redesign_block.lower(), (
            "_run_redesign no aplica el filtro de prueba"
        )

    def test_deep_analysis_engine_contiene_filtro(self):
        """_fetch_microcurriculos en curriculum_deep_analysis_engine.py debe incluir el filtro."""
        source = Path(PROJECT_ROOT / "intelligence" / "curriculum_deep_analysis_engine.py").read_text(encoding="utf-8")
        fetch_start = source.find("def _fetch_microcurriculos")
        assert fetch_start != -1
        fetch_block = source[fetch_start:fetch_start + 800]
        assert "SQL_FILTRO_NO_PRUEBA" in fetch_block or "test_microcurric" in fetch_block.lower(), (
            "_fetch_microcurriculos no aplica el filtro de prueba"
        )
