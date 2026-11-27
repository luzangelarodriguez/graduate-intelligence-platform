"""Tests para el cálculo de cobertura en skills_programa (_market_analysis_for_program).

Verifica que `cobertura` cuenta asignaturas DISTINTAS (via ARRAY_AGG DISTINCT),
no filas de microcurriculo_skills (COUNT(*)).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── La lógica de producción que se prueba ────────────────────────────────────
# Replica la expresión de api/main.py línea ~1045-1047:
#
#   "asignaturas": list(r["asignaturas"]) if r["asignaturas"] else [],
#   "cobertura":   (
#       len(list(r["asignaturas"])) if r["asignaturas"]
#       else (1 if int(r["cobertura"]) > 0 else 0)
#   ),

def _cobertura(row: dict) -> int:
    """Replica la expresión de main.py para calcular cobertura desde una fila SQL."""
    asignaturas = row.get("asignaturas")
    raw_count = int(row.get("cobertura", 0))
    if asignaturas:
        return len(list(asignaturas))
    return 1 if raw_count > 0 else 0


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCoberturaDistintaAsignaturas:
    def test_una_asignatura_distincts_1(self):
        """Un skill presente en 3 filas pero la misma asignatura → cobertura 1."""
        row = {"skill_name": "python", "cobertura": 3, "asignaturas": ["Programación I"]}
        assert _cobertura(row) == 1

    def test_dos_asignaturas_distincts_2(self):
        """Un skill en 2 asignaturas distintas → cobertura 2."""
        row = {
            "skill_name": "sql",
            "cobertura": 5,
            "asignaturas": ["Base de Datos", "Almacenes de Datos"],
        }
        assert _cobertura(row) == 2

    def test_count_mayor_que_distincts(self):
        """
        COUNT(*) = 4 filas pero solo 2 asignaturas distintas → cobertura 2, no 4.
        Este es el bug que se corrigió: usar len(asignaturas) en vez de int(cobertura).
        """
        row = {
            "skill_name": "machine learning",
            "cobertura": 4,
            "asignaturas": ["Modelos Predictivos", "Deep Learning"],
        }
        assert _cobertura(row) == 2
        # Verifica explícitamente que NO usa COUNT(*)
        assert _cobertura(row) != int(row["cobertura"])


class TestCoberturaEdgeCaseAsignaturasNulas:
    def test_asignaturas_none_count_0_es_0(self):
        """ARRAY_REMOVE devuelve NULL y COUNT(*) = 0 → cobertura 0."""
        row = {"skill_name": "skill_x", "cobertura": 0, "asignaturas": None}
        assert _cobertura(row) == 0

    def test_asignaturas_lista_vacia_count_positivo_es_1(self):
        """
        ARRAY_REMOVE elimina todos los NULLs → asignaturas = [].
        Si COUNT(*) > 0 (hay filas pero todas con asignatura NULL), cobertura = 1
        para no perder la skill del análisis.
        """
        row = {"skill_name": "skill_y", "cobertura": 2, "asignaturas": []}
        assert _cobertura(row) == 1

    def test_asignaturas_lista_vacia_count_cero_es_0(self):
        """Sin filas y sin asignaturas → cobertura 0 (skill fantasma)."""
        row = {"skill_name": "skill_z", "cobertura": 0, "asignaturas": []}
        assert _cobertura(row) == 0

    def test_asignaturas_none_count_positivo_es_1(self):
        """ARRAY_REMOVE devuelve NULL pero COUNT(*) > 0 → cobertura 1."""
        row = {"skill_name": "skill_w", "cobertura": 3, "asignaturas": None}
        assert _cobertura(row) == 1
