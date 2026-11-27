"""Tests para los nuevos parámetros min_freq y hard_cap de process_job_skill_rows."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.skills_analysis_logic import HARD_CAP, frequency_threshold, process_job_skill_rows


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
