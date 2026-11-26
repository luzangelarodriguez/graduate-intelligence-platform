"""
Unit tests for api/skills_analysis_logic.py — no database required.
Run with: pytest tests/unit/test_skills_analysis_logic.py -v
"""
from __future__ import annotations

import pytest

from api.skills_analysis_logic import (
    HARD_CAP,
    RUIDO_SIEMPRE,
    TRANSVERSALES,
    build_matriz_completa,
    compute_brechas_criticas,
    cross_analyze,
    find_prog_match,
    frequency_threshold,
    is_transversal,
    norm,
    norm_match,
    phrase_covers,
    process_job_skill_rows,
    sas_has_analytics_context,
    subsume_job_skills,
)


# ── norm() ─────────────────────────────────────────────────────────────────────

class TestNorm:
    def test_strips_accents(self):
        assert norm("comunicación") == "comunicacion"
        assert norm("métricas") == "metricas"
        assert norm("evaluación") == "evaluacion"

    def test_lowercase(self):
        assert norm("Excel") == "excel"
        assert norm("SAS") == "sas"

    def test_hyphen_to_space(self):
        assert norm("e-commerce") == "e commerce"
        assert norm("machine-learning") == "machine learning"

    def test_dot_to_space(self):
        # Dots become spaces, whitespace is collapsed and stripped
        assert norm("S.A.S.") == "s a s"

    def test_underscore_to_space(self):
        assert norm("redes_sociales") == "redes sociales"

    def test_collapses_whitespace(self):
        assert norm("  big   data  ") == "big data"


# ── is_transversal() ───────────────────────────────────────────────────────────

class TestIsTransversal:
    def test_known_transversals(self):
        for skill in ("gestion", "estrategia", "comunicacion", "evaluacion",
                      "administracion", "trabajo en equipo", "liderazgo",
                      "toma de decisiones"):
            assert is_transversal(skill), f"expected {skill!r} to be transversal"

    def test_accented_versions(self):
        assert is_transversal("gestión")
        assert is_transversal("evaluación")
        assert is_transversal("comunicación")
        assert is_transversal("administración")

    def test_non_transversal(self):
        assert not is_transversal("excel")
        assert not is_transversal("marketing digital")
        assert not is_transversal("seo")
        assert not is_transversal("community manager")

    def test_gestion_is_transversal_so_not_coverage(self):
        """
        'gestion' should be transversal and therefore NOT counted as coverage
        even if the curriculum has 'gestión de marca'.
        """
        result = cross_analyze(
            market_skills=[{"skill": "gestion", "frecuencia": 5}],
            prog_skills=[{"skill": "gestión de marca", "cobertura": 2, "asignaturas": []}],
        )
        assert len(result["fortalezas"]) == 0
        assert len(result["brechas"]) == 0
        assert len(result["transversales"]) == 1
        assert result["cobertura_pct"] == 0.0


# ── phrase_covers() ────────────────────────────────────────────────────────────

class TestPhraseCovers:
    def test_exact_match(self):
        assert phrase_covers("marketing digital", "marketing digital")
        assert phrase_covers("excel", "excel")

    def test_prog_contains_market_phrase(self):
        assert phrase_covers("marketing digital", "estrategia de marketing digital")

    def test_short_market_in_long_prog(self):
        # "seo" (3 chars, 1 word) only matches exactly
        assert not phrase_covers("seo", "especialista seo y sem")

    def test_exact_short(self):
        # exact match always works regardless of length
        assert phrase_covers("seo", "seo")

    def test_long_market_not_in_prog(self):
        # "marketing digital" is NOT contained in prog "marketing"
        assert not phrase_covers("marketing digital", "marketing")

    def test_redes_sociales_subsuncion(self):
        # prog has "redes sociales" — market "redes sociales" (2 words) → exact match
        assert phrase_covers("redes sociales", "redes sociales")

    def test_redes_alone_no_phrase_match(self):
        # "redes" is 5 letters, 1 word → only exact
        assert not phrase_covers("redes", "redes sociales")
        assert phrase_covers("redes", "redes")  # exact only

    def test_6_letter_single_word(self):
        # "mercado" (7 letters, 1 word) — phrase covered by longer prog skill
        assert phrase_covers("mercado", "investigacion de mercado")

    def test_accent_normalization(self):
        assert phrase_covers("mercadeo", "analista de mercadeo")
        assert phrase_covers("publicidad", "director de publicidad")


# ── subsume_job_skills() ───────────────────────────────────────────────────────

class TestSubsumeJobSkills:
    def test_redes_absorbed_by_redes_sociales(self):
        result = subsume_job_skills(["redes", "redes sociales", "excel"])
        assert "redes sociales" in result
        assert "redes" not in result
        assert "excel" in result

    def test_excel_absorbed_by_excel_avanzado(self):
        result = subsume_job_skills(["excel", "excel avanzado"])
        assert "excel avanzado" in result
        assert "excel" not in result

    def test_no_subsuncion_different_skills(self):
        result = subsume_job_skills(["python", "sql", "power bi"])
        assert set(result) == {"python", "sql", "power bi"}

    def test_empty_list(self):
        assert subsume_job_skills([]) == []

    def test_single_skill(self):
        assert subsume_job_skills(["marketing"]) == ["marketing"]


# ── RUIDO_SIEMPRE / sas_has_analytics_context() ───────────────────────────────
# Audit of 50 "sas" matches: 49 were S.A.S. legal suffix, 1 was the software.
# "sas" is now universally discarded via RUIDO_SIEMPRE.

class TestSasAnalyticsContext:
    def test_ruido_siempre_contains_sas(self):
        assert norm("sas") in RUIDO_SIEMPRE
        assert norm("S.A.S.") in RUIDO_SIEMPRE
        assert norm("SAS") in RUIDO_SIEMPRE

    def test_sas_always_returns_false(self):
        # sas_has_analytics_context is kept for external callers but always False
        assert not sas_has_analytics_context(frozenset({"sas", "sql", "excel"}))
        assert not sas_has_analytics_context(frozenset({"sas", "python"}))
        assert not sas_has_analytics_context(frozenset({"sas", "ventas"}))


# ── frequency_threshold() ─────────────────────────────────────────────────────

class TestFrequencyThreshold:
    def test_minimum_is_2(self):
        assert frequency_threshold(0) == 2
        assert frequency_threshold(1) == 2
        assert frequency_threshold(10) == 2  # ceil(0.15×10)=2

    def test_scales_with_matches(self):
        assert frequency_threshold(20) == 3   # ceil(0.15×20)=3
        assert frequency_threshold(100) == 15
        assert frequency_threshold(200) == 30

    def test_hard_cap_separate(self):
        # frequency_threshold itself does not cap; HARD_CAP is applied in process_job_skill_rows
        assert frequency_threshold(1000) == 150
        assert HARD_CAP == 60


# ── process_job_skill_rows() ──────────────────────────────────────────────────

class TestProcessJobSkillRows:
    def _rows(self, jobs: dict[str, list[str]]) -> list[dict]:
        return [
            {"match_id": mid, "skill": skill}
            for mid, skills in jobs.items()
            for skill in skills
        ]

    def test_basic_frequency_count(self):
        rows = self._rows({
            "1": ["python", "sql"],
            "2": ["python", "excel"],
            "3": ["python", "sql"],
        })
        result, n_matches = process_job_skill_rows(rows)
        assert n_matches == 3
        skills_dict = {r["skill"]: r["frecuencia"] for r in result}
        assert skills_dict["python"] == 3
        assert skills_dict["sql"] == 2
        # "excel" appears in only 1 job → below threshold max(2, ceil(0.15×3))=2 → excluded
        assert "excel" not in skills_dict

    def test_threshold_scales(self):
        # With 20 jobs, threshold = ceil(0.15×20) = 3
        jobs = {str(i): ["python", "sql"] for i in range(20)}
        jobs["0"].append("rare_skill")  # only 1 job → excluded
        rows = self._rows(jobs)
        result, n_matches = process_job_skill_rows(rows)
        assert n_matches == 20
        skills = {r["skill"] for r in result}
        assert "python" in skills
        assert "rare skill" not in skills  # norm converts underscore

    def test_sas_always_discarded(self):
        # "sas" is in RUIDO_SIEMPRE — discarded regardless of co-occurring skills
        rows = self._rows({
            "1": ["sas", "ventas"],
            "2": ["sas", "negociacion"],
            "3": ["sas", "servicio al cliente"],
        })
        result, _ = process_job_skill_rows(rows)
        assert all(r["skill"].lower() != "sas" for r in result)

    def test_sas_discarded_even_with_analytics(self):
        # Even with sql/python context, "sas" is universally discarded
        rows = self._rows({
            "1": ["sas", "sql", "estadistica"],
            "2": ["sas", "python"],
            "3": ["sas", "spss"],
        })
        result, _ = process_job_skill_rows(rows)
        assert all(r["skill"].lower() != "sas" for r in result)

    def test_sas_dot_notation_discarded(self):
        # "S.A.S." normalises to "s a s" which is also in RUIDO_SIEMPRE
        rows = self._rows({
            "1": ["S.A.S.", "ventas"],
            "2": ["S.A.S.", "marketing"],
            "3": ["S.A.S.", "finanzas"],
        })
        result, _ = process_job_skill_rows(rows)
        sas_variants = {"sas", "s.a.s.", "s a s"}
        assert all(r["skill"].lower() not in sas_variants for r in result)

    def test_subsuncion_applied(self):
        # "redes" and "redes sociales" in same job → only "redes sociales" survives
        rows = self._rows({
            "1": ["redes", "redes sociales"],
            "2": ["redes", "redes sociales"],
            "3": ["redes", "redes sociales"],
        })
        result, _ = process_job_skill_rows(rows)
        skills = {r["skill"] for r in result}
        assert "redes sociales" in skills
        assert "redes" not in skills

    def test_hard_cap(self):
        # Generate 100 unique skills, each appearing in 2+ jobs
        jobs = {str(i): [f"skill{j}" for j in range(100)] for i in range(5)}
        rows = self._rows(jobs)
        result, _ = process_job_skill_rows(rows)
        assert len(result) <= HARD_CAP


# ── Alias canonicalization (canonical_key + SKILL_ALIASES) ────────────────────

class TestAliasCanonicalisation:
    """
    Tests for the alias-based deduplication introduced in process_job_skill_rows.

    Four invariants (a)–(d) plus a cross-analysis coverage test (e).
    """

    def _rows(self, jobs: dict[str, list[str]]) -> list[dict]:
        return [
            {"match_id": mid, "skill": skill}
            for mid, skills in jobs.items()
            for skill in skills
        ]

    # (a) Same vacancy: "reporte" + "reportes" → counted once
    def test_dedupe_within_vacancy_reportes(self):
        rows = self._rows({
            "1": ["reporte", "reportes", "excel"],
            "2": ["reporte", "excel"],
            "3": ["reporte", "excel"],
        })
        result, n = process_job_skill_rows(rows)
        assert n == 3
        freq = {r["skill"]: r["frecuencia"] for r in result}
        # "reporte" and "reportes" collapse to one entry; must appear in all 3 jobs
        reporte_key = next((s for s in freq if "reporte" in s), None)
        assert reporte_key is not None, f"No reporte entry found; got: {list(freq)}"
        assert freq[reporte_key] == 3, (
            f"Expected freq=3 for reporte group, got {freq[reporte_key]}"
        )

    # (b) Same vacancy: "analista de datos" + "analisis de datos" → counted once
    def test_dedupe_within_vacancy_analista_analisis(self):
        rows = self._rows({
            "1": ["analista de datos", "analisis de datos", "python"],
            "2": ["analisis de datos", "python"],
            "3": ["analisis de datos", "python"],
        })
        result, n = process_job_skill_rows(rows)
        assert n == 3
        freq = {r["skill"]: r["frecuencia"] for r in result}
        analisis_key = next((s for s in freq if "analisis" in s or "analista" in s), None)
        assert analisis_key is not None, f"No analisis entry; got: {list(freq)}"
        assert freq[analisis_key] == 3

    # (c) General invariant: no frequency exceeds n_matches
    def test_no_frequency_exceeds_n_matches(self):
        rows = self._rows({
            "1": ["reporte", "reportes", "dashboard", "dashboards"],
            "2": ["reporte", "dashboard"],
            "3": ["reportes", "dashboards"],
            "4": ["reporte", "dashboards"],
            "5": ["reportes", "dashboard"],
        })
        result, n = process_job_skill_rows(rows)
        for entry in result:
            assert entry["frecuencia"] <= n, (
                f"freq={entry['frecuencia']} > n_matches={n} for skill '{entry['skill']}'"
            )

    # (d) Alias across different vacancies: sums into one entry
    def test_alias_sums_across_vacancies(self):
        # 4 jobs: 2 have "reportes", 2 have "reporte" → one entry with freq=4
        rows = self._rows({
            "1": ["reportes", "sql"],
            "2": ["reporte",  "sql"],
            "3": ["reportes", "sql"],
            "4": ["reporte",  "sql"],
        })
        result, n = process_job_skill_rows(rows)
        assert n == 4
        freq = {r["skill"]: r["frecuencia"] for r in result}
        reporte_entries = [v for k, v in freq.items() if "reporte" in k]
        assert len(reporte_entries) == 1, (
            f"Expected one merged entry for reporte group, got: {list(freq)}"
        )
        assert reporte_entries[0] == 4

    # (e) Cross-analysis: "reportes" in market covered by "reporte" in program
    def test_reportes_covered_by_reporte_in_program(self):
        rows = self._rows({
            str(i): ["reportes", "python"] for i in range(5)
        })
        result, n = process_job_skill_rows(rows)
        from api.skills_analysis_logic import cross_analyze
        prog = [
            {"skill": "reporte", "cobertura": 2, "asignaturas": []},
            {"skill": "Python",  "cobertura": 3, "asignaturas": []},
        ]
        analysis = cross_analyze(result, prog, n_matches=n)
        fortaleza_skills = {f["skill"] for f in analysis["fortalezas"]}
        brecha_skills    = {b["skill"] for b in analysis["brechas"]}
        assert any("reporte" in s for s in fortaleza_skills), (
            f"'reportes' should be covered by 'reporte'; brechas={brecha_skills}"
        )
        assert not any("reporte" in s for s in brecha_skills), (
            f"'reporte' group should not appear in brechas; got: {brecha_skills}"
        )

    # (e2) Cross-analysis: "dashboards" covered by "dashboard" in program
    def test_dashboards_covered_by_dashboard_in_program(self):
        rows = self._rows({
            str(i): ["dashboards", "sql"] for i in range(5)
        })
        result, n = process_job_skill_rows(rows)
        from api.skills_analysis_logic import cross_analyze
        prog = [
            {"skill": "dashboard", "cobertura": 2, "asignaturas": []},
            {"skill": "SQL",       "cobertura": 3, "asignaturas": []},
        ]
        analysis = cross_analyze(result, prog, n_matches=n)
        fortaleza_skills = {f["skill"] for f in analysis["fortalezas"]}
        brecha_skills    = {b["skill"] for b in analysis["brechas"]}
        assert any("dashboard" in s for s in fortaleza_skills), (
            f"'dashboards' should be covered by 'dashboard'; brechas={brecha_skills}"
        )

    # (f) Display name: without alias, first-seen form is preserved
    def test_display_name_no_alias_is_first_seen(self):
        # "Machine Learning" appears in 3 jobs — no alias for it
        rows = self._rows({
            "1": ["Machine Learning", "Python"],
            "2": ["machine learning", "Python"],
            "3": ["MACHINE LEARNING", "Python"],
        })
        result, _ = process_job_skill_rows(rows)
        freq = {r["skill"]: r["frecuencia"] for r in result}
        ml_key = next((s for s in freq if "machine" in s.lower()), None)
        assert ml_key is not None
        # Display form is the first-seen raw form
        assert ml_key == "Machine Learning", (
            f"Expected first-seen form 'Machine Learning', got '{ml_key}'"
        )

    # (g) Display name: with alias, canonical destination is used
    def test_display_name_with_alias_is_canonical(self):
        # Only "reportes" appears; display should be "reporte" (alias destination)
        rows = self._rows({str(i): ["reportes", "sql"] for i in range(5)})
        result, _ = process_job_skill_rows(rows)
        freq = {r["skill"]: r["frecuencia"] for r in result}
        assert "reporte" in freq, (
            f"Expected display name 'reporte' (alias destination), got: {list(freq)}"
        )
        assert "reportes" not in freq


# ── find_prog_match canonical_key coverage ────────────────────────────────────

class TestFindProgMatchCanonical:
    """
    Verify that find_prog_match uses canonical_key on both sides, so alias pairs
    (reportes↔reporte, analista de datos↔analisis de datos) cross-match correctly,
    while unrelated skills (sql vs bases de datos) do NOT.
    """

    def _prog(self, skills: list[str]) -> list[dict]:
        return [{"skill": s, "cobertura": 1, "asignaturas": []} for s in skills]

    def test_market_reporte_covered_by_prog_reportes(self):
        # canonical_key("reporte")="reporte", canonical_key("reportes")="reporte" → match
        detail = find_prog_match("reporte", self._prog(["reportes"]))
        assert detail.rule != "ninguna", (
            "market 'reporte' should be covered by prog 'reportes' via alias"
        )
        assert detail.rule == "sinonimo_o_nivel"

    def test_market_reportes_covered_by_prog_reporte(self):
        # canonical_key("reportes")="reporte", canonical_key("reporte")="reporte" → match
        detail = find_prog_match("reportes", self._prog(["reporte"]))
        assert detail.rule != "ninguna", (
            "market 'reportes' should be covered by prog 'reporte' via alias"
        )
        assert detail.rule == "sinonimo_o_nivel"

    def test_market_analisis_covered_by_prog_analista(self):
        # canonical_key("analisis de datos")="analisis de datos"
        # canonical_key("analista de datos")="analisis de datos" → match
        detail = find_prog_match("analisis de datos", self._prog(["analista de datos"]))
        assert detail.rule != "ninguna", (
            "market 'analisis de datos' should be covered by prog 'analista de datos' via alias"
        )
        assert detail.rule == "sinonimo_o_nivel"

    def test_sql_not_covered_by_bases_de_datos(self):
        # "sql" and "bases de datos" are intentionally NOT unified — must stay separate
        detail = find_prog_match("sql", self._prog(["bases de datos"]))
        assert detail.rule == "ninguna", (
            "'sql' must NOT be covered by 'bases de datos' — these are separate skills"
        )


# ── cross_analyze() ───────────────────────────────────────────────────────────

class TestCrossAnalyze:
    def _prog(self, skills: list[str]) -> list[dict]:
        return [{"skill": s, "cobertura": 1, "asignaturas": []} for s in skills]

    def test_exact_fortaleza(self):
        result = cross_analyze(
            market_skills=[{"skill": "python", "frecuencia": 5}],
            prog_skills=self._prog(["python"]),
        )
        assert len(result["fortalezas"]) == 1
        assert result["fortalezas"][0]["regla"] == "exacta"
        assert result["cobertura_pct"] == 100.0

    def test_phrase_fortaleza(self):
        result = cross_analyze(
            market_skills=[{"skill": "analisis de datos", "frecuencia": 4}],
            prog_skills=self._prog(["técnicas de análisis de datos"]),
        )
        assert len(result["fortalezas"]) == 1
        assert result["fortalezas"][0]["regla"] == "frase"

    def test_brecha(self):
        result = cross_analyze(
            market_skills=[{"skill": "tableau", "frecuencia": 3}],
            prog_skills=self._prog(["power bi"]),
        )
        assert len(result["brechas"]) == 1
        assert result["cobertura_pct"] == 0.0

    def test_transversal_excluded_from_cobertura(self):
        result = cross_analyze(
            market_skills=[
                {"skill": "python", "frecuencia": 5},
                {"skill": "gestion", "frecuencia": 4},
                {"skill": "trabajo en equipo", "frecuencia": 3},
            ],
            prog_skills=self._prog(["python", "gestión de proyectos"]),
        )
        # Only python counts; gestion and trabajo en equipo are transversales
        assert result["cobertura_pct"] == 100.0
        assert len(result["transversales"]) == 2
        assert len(result["fortalezas"]) == 1

    def test_cobertura_excludes_transversales(self):
        result = cross_analyze(
            market_skills=[
                {"skill": "seo", "frecuencia": 5},          # brecha
                {"skill": "marketing digital", "frecuencia": 4},  # brecha
                {"skill": "gestion", "frecuencia": 3},       # transversal
            ],
            prog_skills=self._prog(["excel"]),
        )
        # cobertura_pct = 0 / 2 (not counting transversal in denominator)
        assert result["cobertura_pct"] == 0.0
        assert len(result["brechas"]) == 2
        assert len(result["transversales"]) == 1

    def test_brechas_criticas_p66(self):
        # 3 brechas with freqs [1, 2, 10]: p66 index = floor(3×2/3) = 2 → threshold = freqs[2] = 10
        result = cross_analyze(
            market_skills=[
                {"skill": "meta ads", "frecuencia": 10},
                {"skill": "tiktok", "frecuencia": 2},
                {"skill": "instagram", "frecuencia": 1},
            ],
            prog_skills=[],
        )
        assert len(result["brechas_criticas"]) == 1
        assert result["brechas_criticas"][0]["skill"] == "meta ads"

    def test_redes_not_brecha_when_prog_has_redes_sociales(self):
        """
        market "redes" (5 chars, 1 word) → only exact; prog has "redes sociales".
        "redes" should remain a brecha because phrase_covers("redes", "redes sociales")=False.
        """
        result = cross_analyze(
            market_skills=[
                {"skill": "redes", "frecuencia": 3},
                {"skill": "redes sociales", "frecuencia": 5},
            ],
            prog_skills=self._prog(["redes sociales"]),
        )
        # "redes sociales" covered (exact), "redes" is a brecha
        fortaleza_skills = {f["skill"] for f in result["fortalezas"]}
        assert "redes sociales" in fortaleza_skills
        assert "redes" not in fortaleza_skills
        assert any(b["skill"] == "redes" for b in result["brechas"])


# ── compute_brechas_criticas() ────────────────────────────────────────────────

class TestBrechasCriticas:
    def test_empty(self):
        assert compute_brechas_criticas([]) == []

    def test_single_brecha_is_critical(self):
        brechas = [{"skill": "x", "frecuencia_mercado": 5}]
        result = compute_brechas_criticas(brechas)
        assert len(result) == 1

    def test_p66_selection(self):
        brechas = [
            {"skill": "a", "frecuencia_mercado": 10},
            {"skill": "b", "frecuencia_mercado": 5},
            {"skill": "c", "frecuencia_mercado": 2},
        ]
        # Sorted freqs: [2, 5, 10]; idx66 = floor(3×2/3) = 2; threshold = 10
        result = compute_brechas_criticas(brechas)
        assert len(result) == 1
        assert result[0]["skill"] == "a"


# ── build_matriz_completa() ───────────────────────────────────────────────────

class TestBuildMatrizCompleta:
    def _prog(self, skills):
        return [{"skill": s, "cobertura": 1, "asignaturas": []} for s in skills]

    def test_tipo_fortaleza(self):
        mkt = [{"skill": "python", "frecuencia": 5}]
        prog = self._prog(["python"])
        matriz = build_matriz_completa(mkt, prog, {"python"}, set())
        entry = next(e for e in matriz if e["skill"] == "python")
        assert entry["tipo"] == "fortaleza"
        assert entry["oferta_programa"] == 1

    def test_tipo_brecha(self):
        mkt = [{"skill": "tableau", "frecuencia": 3}]
        matriz = build_matriz_completa(mkt, [], set(), set())
        entry = next(e for e in matriz if e["skill"] == "tableau")
        assert entry["tipo"] == "brecha"

    def test_tipo_transversal(self):
        mkt = [{"skill": "gestion", "frecuencia": 4}]
        matriz = build_matriz_completa(mkt, [], set(), {norm("gestion")})
        entry = next(e for e in matriz if norm(e["skill"]) == "gestion")
        assert entry["tipo"] == "transversal"

    def test_tipo_solo_programa(self):
        mkt = [{"skill": "python", "frecuencia": 5}]
        prog = self._prog(["python", "comportamiento del consumidor"])
        matriz = build_matriz_completa(mkt, prog, {"python"}, set())
        solo = [e for e in matriz if e["tipo"] == "solo_programa"]
        assert any("comportamiento" in e["skill"] for e in solo)
        # solo_programa entries have demanda_mercado == 0
        for e in solo:
            assert e["demanda_mercado"] == 0


# ── norm_match() ───────────────────────────────────────────────────────────────

class TestNormMatch:
    def test_strips_level_qualifier(self):
        assert norm_match("excel avanzado") == "excel"
        assert norm_match("python intermedio") == "python"
        assert norm_match("sql basico") == "sql"

    def test_depluralize_english(self):
        assert norm_match("dashboards") == "dashboard"

    def test_no_depluralize_spanish_es(self):
        # "redes": prev char is 'e' (vowel) → keep "redes"
        assert norm_match("redes") == "redes"

    def test_sinonimo_mercadeo_marketing(self):
        assert norm_match("mercadeo") == "marketing"

    def test_sinonimo_redes_sociales(self):
        assert norm_match("redes sociales") == "social media"

    def test_sinonimo_ecommerce(self):
        assert norm_match("e-commerce") == "e commerce"
        assert norm_match("ecommerce") == "e commerce"
        assert norm_match("comercio electrónico") == "e commerce"

    def test_sinonimo_kpis(self):
        assert norm_match("KPIs") == "metricas"

    def test_no_change_no_synonym(self):
        assert norm_match("python") == "python"
        assert norm_match("marketing digital") == "marketing digital"


# ── Coverage via norm_match ────────────────────────────────────────────────────

class TestNormMatchCoverage:
    def _prog(self, skills):
        return [{"skill": s, "cobertura": 1, "asignaturas": []} for s in skills]

    def test_mercadeo_covered_by_marketing(self):
        """market 'mercadeo' → norm_match → 'marketing'; prog has 'marketing' → fortaleza."""
        result = cross_analyze(
            market_skills=[{"skill": "mercadeo", "frecuencia": 5}],
            prog_skills=self._prog(["marketing"]),
        )
        assert len(result["fortalezas"]) == 1

    def test_excel_avanzado_covered_by_excel(self):
        """market 'excel avanzado' → norm_match strips 'avanzado' → 'excel'; prog has 'excel' → fortaleza."""
        result = cross_analyze(
            market_skills=[{"skill": "excel avanzado", "frecuencia": 4}],
            prog_skills=self._prog(["excel"]),
        )
        assert len(result["fortalezas"]) == 1
        assert result["fortalezas"][0]["regla"] == "sinonimo_o_nivel"

    def test_dashboards_covered_by_dashboard(self):
        """market 'dashboards' → depluralize → 'dashboard'; prog has 'dashboard' → fortaleza."""
        result = cross_analyze(
            market_skills=[{"skill": "dashboards", "frecuencia": 3}],
            prog_skills=self._prog(["dashboard"]),
        )
        assert len(result["fortalezas"]) == 1

    def test_redes_sociales_covered_by_social_media(self):
        """market 'redes sociales' → synonym → 'social media'; prog has 'social media' → fortaleza."""
        result = cross_analyze(
            market_skills=[{"skill": "redes sociales", "frecuencia": 5}],
            prog_skills=self._prog(["social media"]),
        )
        assert len(result["fortalezas"]) == 1

    def test_no_false_coverage_different_skills(self):
        """norm_match should not invent coverage where none exists."""
        result = cross_analyze(
            market_skills=[{"skill": "tableau", "frecuencia": 3}],
            prog_skills=self._prog(["power bi"]),
        )
        assert len(result["brechas"]) == 1
        assert len(result["fortalezas"]) == 0


# ── PARAGUAS ──────────────────────────────────────────────────────────────────

class TestParaguas:
    def _prog(self, skills):
        return [{"skill": s, "cobertura": 1, "asignaturas": []} for s in skills]

    def test_paraguas_not_covered_with_2_components(self):
        """2 of 7 components → NOT covered (needs ≥ 3)."""
        result = cross_analyze(
            market_skills=[{"skill": "marketing digital", "frecuencia": 5}],
            prog_skills=self._prog(["seo", "sem"]),
        )
        assert len(result["brechas"]) == 1
        assert len(result["fortalezas"]) == 0

    def test_paraguas_covered_with_3_components(self):
        """3 of 7 components → covered."""
        result = cross_analyze(
            market_skills=[{"skill": "marketing digital", "frecuencia": 5}],
            prog_skills=self._prog(["seo", "sem", "email marketing"]),
        )
        assert len(result["fortalezas"]) == 1
        assert "paraguas" in result["fortalezas"][0]["regla"]

    def test_paraguas_covered_with_all_components(self):
        """All 7 components → covered."""
        result = cross_analyze(
            market_skills=[{"skill": "marketing digital", "frecuencia": 5}],
            prog_skills=self._prog([
                "seo", "sem", "email marketing", "google ads",
                "social media", "google analytics", "community manager",
            ]),
        )
        assert len(result["fortalezas"]) == 1
        assert "paraguas" in result["fortalezas"][0]["regla"]

    def test_evidencia_baja_true_when_few_matches(self):
        result = cross_analyze(
            market_skills=[{"skill": "python", "frecuencia": 2}],
            prog_skills=self._prog(["python"]),
            n_matches=10,
        )
        assert result["evidencia_baja"] is True

    def test_evidencia_baja_false_when_enough_matches(self):
        result = cross_analyze(
            market_skills=[{"skill": "python", "frecuencia": 2}],
            prog_skills=self._prog(["python"]),
            n_matches=20,
        )
        assert result["evidencia_baja"] is False
