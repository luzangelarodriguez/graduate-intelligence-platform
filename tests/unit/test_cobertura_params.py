"""Tests para los nuevos parámetros min_freq y hard_cap de process_job_skill_rows,
y para las funciones puras cobertura_ponderada y pct_menciones_fuera_del_corte
del script scripts/diag/cobertura_sin_tope.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.skills_analysis_logic import HARD_CAP, frequency_threshold, process_job_skill_rows
from scripts.diag.cobertura_sin_tope import cobertura_ponderada, pct_menciones_fuera_del_corte


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rows(skill_counts: dict[str, int]) -> list[dict]:
    """
    Build synthetic rows from {skill: n_jobs_that_mention_it}.
    Each job is a separate match_id so n_matches == total unique jobs.
    """
    rows: list[dict] = []
    match_id = 0
    for skill, count in skill_counts.items():
        for _ in range(count):
            rows.append({"match_id": str(match_id), "skill": skill})
            match_id += 1
    return rows


# ── A. Comportamiento por defecto no ha cambiado (regresión) ──────────────────

class TestDefaultBehaviorUnchanged:
    """Regresión: sin argumentos, process_job_skill_rows se comporta igual que antes."""

    def test_sin_argumentos_usa_frequency_threshold(self):
        # 10 jobs, umbral = max(2, ceil(0.15*10)) = 2
        rows = _rows({"python": 5, "sql": 3, "excel": 1})
        skills, n_matches = process_job_skill_rows(rows)
        nombres = {s["skill"] for s in skills}
        assert n_matches == 9  # 5 + 3 + 1 jobs (cada aparición es un job distinto)
        assert "python" in nombres
        assert "sql" in nombres
        # excel aparece solo 1 vez, umbral = max(2, ceil(0.15*9)) = 2 → excluido
        assert "excel" not in nombres

    def test_sin_argumentos_aplica_hard_cap(self):
        # 70 skills distintas cada una con frecuencia alta, resultado <= HARD_CAP=60
        skill_counts = {f"skill_{i}": 10 for i in range(70)}
        rows = _rows(skill_counts)
        skills, _ = process_job_skill_rows(rows)
        assert len(skills) <= HARD_CAP

    def test_retorno_es_tupla_skills_n_matches(self):
        rows = _rows({"python": 5})
        result = process_job_skill_rows(rows)
        assert isinstance(result, tuple) and len(result) == 2
        skills, n_matches = result
        assert isinstance(skills, list)
        assert isinstance(n_matches, int)


# ── B. Parámetro min_freq ─────────────────────────────────────────────────────

class TestMinFreq:
    """min_freq sobreescribe frequency_threshold cuando se pasa explícitamente."""

    def test_min_freq_1_incluye_skills_de_frecuencia_1(self):
        rows = _rows({"python": 5, "excel": 1})
        skills, _ = process_job_skill_rows(rows, min_freq=1)
        nombres = {s["skill"] for s in skills}
        assert "excel" in nombres

    def test_min_freq_2_excluye_frecuencia_1(self):
        rows = _rows({"python": 5, "excel": 1})
        skills, _ = process_job_skill_rows(rows, min_freq=2)
        nombres = {s["skill"] for s in skills}
        assert "excel" not in nombres
        assert "python" in nombres

    def test_min_freq_none_usa_frequency_threshold(self):
        # Con 20 jobs, umbral = max(2, ceil(0.15*20)) = 3
        # skill_raro aparece 2 veces → por debajo del umbral
        rows = _rows({"python": 10, "sql": 8, "skill_raro": 2})
        skills_default, _ = process_job_skill_rows(rows, min_freq=None)
        skills_explicit, _ = process_job_skill_rows(rows)
        assert {s["skill"] for s in skills_default} == {s["skill"] for s in skills_explicit}

    def test_min_freq_mayor_que_frecuencia_maxima_devuelve_vacio(self):
        rows = _rows({"python": 5})
        skills, _ = process_job_skill_rows(rows, min_freq=100)
        assert skills == []


# ── C. Parámetro hard_cap ─────────────────────────────────────────────────────

class TestHardCap:
    """hard_cap controla el máximo de skills devueltas."""

    def test_hard_cap_none_devuelve_todos_los_candidatos(self):
        # 70 skills con alta frecuencia; sin tope debe devolver más que HARD_CAP
        skill_counts = {f"skill_{i}": 10 for i in range(70)}
        rows = _rows(skill_counts)
        skills, _ = process_job_skill_rows(rows, min_freq=1, hard_cap=None)
        # Puede que no lleguen a 70 exactas por aliases/subsunción, pero > 60
        assert len(skills) > HARD_CAP

    def test_hard_cap_10_limita_resultado(self):
        skill_counts = {f"skill_{i}": 10 for i in range(30)}
        rows = _rows(skill_counts)
        skills, _ = process_job_skill_rows(rows, min_freq=1, hard_cap=10)
        assert len(skills) <= 10

    def test_hard_cap_toma_las_mas_frecuentes(self):
        # skill_a más frecuente que skill_b; con cap=1 solo debe quedar skill_a
        rows = _rows({"skill_a": 20, "skill_b": 5})
        skills, _ = process_job_skill_rows(rows, min_freq=1, hard_cap=1)
        assert len(skills) == 1
        assert skills[0]["frecuencia"] == 20


# ── D. cobertura_ponderada (función pura del script de diagnóstico) ───────────

class TestCoberturaPonderada:
    """Prueba la función pura cobertura_ponderada sin base de datos."""

    def _f(self, skill: str, freq: int) -> dict:
        return {"skill": skill, "frecuencia_mercado": freq}

    def _b(self, skill: str, freq: int) -> dict:
        return {"skill": skill, "frecuencia_mercado": freq}

    def test_cobertura_total_100(self):
        """Todas las menciones cubiertas → 100%."""
        fortalezas = [self._f("python", 50), self._f("sql", 30)]
        brechas: list[dict] = []
        assert cobertura_ponderada(fortalezas, brechas) == 100.0

    def test_cobertura_cero(self):
        """Ninguna mención cubierta → 0%."""
        fortalezas: list[dict] = []
        brechas = [self._b("ml", 40), self._b("spark", 20)]
        assert cobertura_ponderada(fortalezas, brechas) == 0.0

    def test_cobertura_ponderada_difiere_de_simple(self):
        """
        Simple: 1 fortaleza / 2 skills = 50%.
        Ponderada: si la fortaleza tiene más frecuencia → ponderada > 50%.
        """
        fortalezas = [self._f("python", 80)]
        brechas = [self._b("ml", 20)]
        pond = cobertura_ponderada(fortalezas, brechas)
        assert pond == 80.0
        assert pond != 50.0  # difiere de la cobertura simple (1/2)

    def test_ambas_listas_vacias_devuelve_cero(self):
        assert cobertura_ponderada([], []) == 0.0

    def test_calculo_exacto(self):
        """Cálculo manual: sum_fortalezas=30, sum_total=50 → 60.0%."""
        fortalezas = [self._f("sql", 20), self._f("excel", 10)]
        brechas = [self._b("ml", 15), self._b("spark", 5)]
        assert cobertura_ponderada(fortalezas, brechas) == 60.0


# ── E. pct_menciones_fuera_del_corte (función pura del script) ────────────────

class TestPctMencionesFuera:
    def _s(self, skill: str, freq: int) -> dict:
        return {"skill": skill, "frecuencia": freq}

    def test_sin_corte_fuera_es_cero(self):
        """A == D → no se deja nada fuera."""
        skills = [self._s("python", 50), self._s("sql", 30)]
        assert pct_menciones_fuera_del_corte(skills, skills) == 0.0

    def test_a_vacio_fuera_es_100(self):
        """Corte A descarta todo → 100% fuera."""
        d = [self._s("python", 50)]
        assert pct_menciones_fuera_del_corte([], d) == 100.0

    def test_d_vacio_devuelve_cero(self):
        """D vacío → 0% (evita división por cero)."""
        assert pct_menciones_fuera_del_corte([], []) == 0.0

    def test_calculo_exacto(self):
        """A cubre 60/100 de menciones → 40% fuera."""
        a = [self._s("python", 60)]
        d = [self._s("python", 60), self._s("ml", 40)]
        assert pct_menciones_fuera_del_corte(a, d) == 40.0
