"""
Unit tests for the unified market analysis shared by /skills-analysis and _run_redesign.
No database required — uses simulated rows.
Run with: pytest tests/unit/test_redesign_market_analysis.py -v
"""
from __future__ import annotations

import pytest

from api.skills_analysis_logic import (
    cross_analyze,
    frequency_threshold,
    process_job_skill_rows,
)


def _make_rows(match_skills: list[list[str]]) -> list[dict]:
    """Build fake fetch_all rows from a list of per-job skill lists."""
    rows = []
    for mid, skills in enumerate(match_skills):
        for skill in skills:
            rows.append({"match_id": mid, "skill": skill})
    return rows


# ── SAS filter ─────────────────────────────────────────────────────────────────

class TestSasFiltered:
    def test_sas_removed_from_market_skills(self):
        rows = _make_rows([
            ["Python", "SAS", "Data Analysis"],
            ["Python", "S.A.S.", "Machine Learning"],
            ["Python", "SAS", "SQL"],
        ])
        result, _ = process_job_skill_rows(rows)
        skill_names_lower = [r["skill"].lower() for r in result]
        assert "sas" not in skill_names_lower
        assert "s.a.s." not in skill_names_lower
        assert any("python" in s for s in skill_names_lower)

    def test_all_noise_returns_empty(self):
        rows = _make_rows([["SAS", "sas", "S.A.S."]] * 5)
        result, _ = process_job_skill_rows(rows)
        assert result == []


# ── Subsunción ─────────────────────────────────────────────────────────────────

class TestSubsuncion:
    def test_redes_dominated_by_redes_sociales(self):
        """When a job lists both 'redes' and 'redes sociales', only the qualified form survives."""
        rows = _make_rows([
            ["redes", "redes sociales", "marketing"],
            ["redes", "redes sociales", "analítica"],
            ["redes", "redes de datos", "networking"],
        ])
        result, _ = process_job_skill_rows(rows)
        skill_names = [r["skill"].lower() for r in result]
        assert "redes" not in skill_names, f"'redes' should be subsumed but found: {skill_names}"

    def test_specific_form_wins_over_short(self):
        """'machine learning' dominates bare 'machine'."""
        rows = _make_rows([
            ["machine", "machine learning", "python"],
            ["machine", "machine learning", "data"],
            ["machine", "machine learning", "statistics"],
        ])
        result, _ = process_job_skill_rows(rows)
        skill_names = [r["skill"].lower() for r in result]
        assert "machine" not in skill_names
        assert any("machine learning" in s for s in skill_names)

    def test_independent_skills_both_survive(self):
        """Skills with no phrase containment relationship both survive."""
        rows = _make_rows([
            ["python", "javascript", "react"],
            ["python", "javascript", "node"],
            ["python", "javascript", "sql"],
        ])
        result, _ = process_job_skill_rows(rows)
        skill_names = [r["skill"].lower() for r in result]
        assert "python" in skill_names
        assert "javascript" in skill_names


# ── Dynamic threshold ──────────────────────────────────────────────────────────

class TestDynamicThreshold:
    def test_threshold_values(self):
        assert frequency_threshold(10) == 2   # max(2, ceil(1.5))
        assert frequency_threshold(14) == 3   # max(2, ceil(2.1))
        assert frequency_threshold(100) == 15  # max(2, ceil(15.0))
        assert frequency_threshold(7) == 2    # max(2, ceil(1.05))

    def test_low_frequency_skill_excluded(self):
        """With 20 matches, threshold = max(2, ceil(3.0)) = 3; skill appearing twice is excluded."""
        jobs: list[list[str]] = [["python", "sql", "data"]] * 20
        jobs[0] = ["python", "sql", "niche_skill"]
        jobs[1] = ["python", "niche_skill", "data"]
        rows = _make_rows(jobs)
        result, n = process_job_skill_rows(rows)
        assert n == 20
        assert frequency_threshold(n) == 3
        skill_names = [r["skill"].lower() for r in result]
        assert "niche_skill" not in skill_names

    def test_high_frequency_skill_included(self):
        """Skill appearing in every job passes any threshold."""
        rows = _make_rows([["python", "sql"]] * 20)
        result, _ = process_job_skill_rows(rows)
        skill_names = [r["skill"].lower() for r in result]
        assert "python" in skill_names
        assert "sql" in skill_names

    def test_hard_cap_applied(self):
        """At most HARD_CAP (60) skills are returned."""
        from api.skills_analysis_logic import HARD_CAP
        # 70 distinct skills, each in 10 jobs
        skills_per_job = [f"skill_{i}" for i in range(70)]
        rows = _make_rows([skills_per_job] * 10)
        result, _ = process_job_skill_rows(rows)
        assert len(result) <= HARD_CAP


# ── evidencia_baja guard ───────────────────────────────────────────────────────

class TestEvidenciaBaja:
    def test_true_when_few_matches(self):
        market = [{"skill": "Python", "frecuencia": 8}]
        prog = [{"skill": "Python", "cobertura": 2, "asignaturas": []}]
        result = cross_analyze(market, prog, n_matches=10)
        assert result["evidencia_baja"] is True

    def test_false_at_threshold(self):
        market = [{"skill": "Python", "frecuencia": 20}]
        prog = [{"skill": "Python", "cobertura": 2, "asignaturas": []}]
        result = cross_analyze(market, prog, n_matches=15)
        assert result["evidencia_baja"] is False

    def test_false_above_threshold(self):
        market = [{"skill": "Python", "frecuencia": 30}]
        prog = [{"skill": "Python", "cobertura": 2, "asignaturas": []}]
        result = cross_analyze(market, prog, n_matches=50)
        assert result["evidencia_baja"] is False

    def test_evidencia_baja_does_not_affect_brechas_criticas_logic(self):
        """evidencia_baja is a flag only; brechas_criticas is still computed."""
        market = [
            {"skill": "Python",     "frecuencia": 8},
            {"skill": "JavaScript", "frecuencia": 5},
            {"skill": "SQL",        "frecuencia": 3},
        ]
        prog: list[dict] = []
        result = cross_analyze(market, prog, n_matches=5)
        assert result["evidencia_baja"] is True
        # brechas_criticas is still populated (p66 logic)
        assert len(result["brechas_criticas"]) > 0
