"""
Unit tests for the _SQL_MARKET_SKILLS constant and _market_analysis_for_program.

FastAPI is not installed in the unit-test environment.  To avoid polluting
sys.modules globally the `market_symbols` session fixture:
  1. Temporarily installs stubs for every module api/main.py imports.
  2. Imports api.main and extracts the two symbols we need.
  3. IMMEDIATELY restores sys.modules (removes stubs and api.main) before
     yielding.  Symbols remain valid — they are plain Python objects in memory.

No top-level import of api.main happens, so collection-time pollution is zero.
Other tests in the suite are not affected.

(a) Structural tests: verify _SQL_MARKET_SKILLS removed relevance_label /
    skills_en_comun and introduced RANK() OVER (PARTITION BY m.empleo_id).

(b) Integration stub tests: verify _market_analysis_for_program calls
    fetch_all_fn with (program_id,) and returns all expected keys.
"""
from __future__ import annotations

import re
import sys
import types
from unittest.mock import MagicMock

import pytest


# ── Session fixture: load symbols, then restore sys.modules ───────────────────

def _build_stubs() -> dict[str, types.ModuleType]:
    """Create stub modules for api.main's non-test-env dependencies."""
    stubs: dict[str, types.ModuleType] = {}

    def stub(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        stubs[name] = m
        return m

    fa = stub("fastapi")
    fa.BackgroundTasks = MagicMock()
    fa.FastAPI = MagicMock(return_value=MagicMock())
    fa.Query = MagicMock()

    stub("fastapi.middleware")
    cors = stub("fastapi.middleware.cors")
    cors.CORSMiddleware = MagicMock()

    jr = stub("fastapi.responses")
    jr.JSONResponse = MagicMock()

    contracts = stub("api.contracts")
    for cname in (
        "CareerIntelligenceResponse", "CriticalProgramPageResponse",
        "CurriculumSimulationResponse", "CurriculumRiskResponse",
        "ExecutiveNarrativeResponse", "ExecutiveObservatoryResponse",
        "ForecastSummaryResponse", "HealthResponse",
        "MarketForecastPageResponse", "ObservatoryStatusResponse",
        "PaginatedResponse", "ProgramIntelligenceItem",
        "ProgramIntelligencePageResponse", "Program",
        "ProgramDashboardResponse", "ProgramSummaryResponse",
        "ProgramPageResponse", "RecommendationV2PageResponse",
        "RecommendationExplanationResponse", "AskObservatoryRequest",
        "AskObservatoryResponse", "SearchResponse",
        "UniversityMarketAlignmentResponse",
    ):
        setattr(contracts, cname, MagicMock())

    log_mod = stub("api.logging")
    log_mod.RequestLoggingMiddleware = MagicMock()
    log_mod.configure_logging = MagicMock()

    auth = stub("api.auth")
    auth.auth_router = MagicMock()

    stub("api.services")
    stub("api.database")

    return stubs


@pytest.fixture(scope="session")
def market_symbols():
    """
    Provide _SQL_MARKET_SKILLS and _market_analysis_for_program without leaving
    any stub or api.main entry in sys.modules after the fixture is set up.

    Timeline:
      install stubs → import api.main → extract symbols → restore sys.modules
      → yield symbols to tests

    After restoration api.main is gone from sys.modules; the extracted objects
    (a str and a function) stay alive as ordinary Python objects.
    """
    stubs = _build_stubs()

    # Save originals for every key we touch (None means absent)
    keys_to_touch = list(stubs.keys()) + ["api.main"]
    originals = {k: sys.modules.get(k) for k in keys_to_touch}

    # Install stubs; ensure api.main is not cached from a prior import
    for name, mod in stubs.items():
        sys.modules[name] = mod
    sys.modules.pop("api.main", None)

    try:
        import api.main as _main  # noqa: PLC0415
        sql = _main._SQL_MARKET_SKILLS
        fn  = _main._market_analysis_for_program
    finally:
        # Restore sys.modules regardless of import success
        for name, orig in originals.items():
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig

    # Symbols are live Python objects; sys.modules is now pristine
    yield {"sql": sql, "fn": fn}


# ── (a) Structural tests on _SQL_MARKET_SKILLS ───────────────────────────────

class TestSqlStructure:
    def test_no_relevance_label_filter(self, market_symbols):
        # relevance_label is SELECTed for n_muestra_alta_media, but must not appear
        # in a WHERE / FILTER clause that narrows the market sample.
        sql = market_symbols["sql"]
        assert not re.search(
            r"relevance_label\s+IN\b", sql, re.IGNORECASE
        ), "_SQL_MARKET_SKILLS must not filter the sample by relevance_label IN (...)"

    def test_no_skills_en_comun_filter(self, market_symbols):
        sql = market_symbols["sql"]
        assert "skills_en_comun" not in sql, (
            "_SQL_MARKET_SKILLS must not filter by skills_en_comun"
        )

    def test_contains_rank_window_function(self, market_symbols):
        sql = market_symbols["sql"]
        assert re.search(r"\bRANK\s*\(\s*\)", sql, re.IGNORECASE), (
            "_SQL_MARKET_SKILLS must use RANK() window function"
        )

    def test_partitioned_by_empleo_id(self, market_symbols):
        sql = market_symbols["sql"]
        assert re.search(
            r"PARTITION\s+BY\s+m\.empleo_id", sql, re.IGNORECASE
        ), "_SQL_MARKET_SKILLS must PARTITION BY m.empleo_id"

    def test_ordered_by_role_alignment_desc(self, market_symbols):
        sql = market_symbols["sql"]
        assert re.search(
            r"ORDER\s+BY\s+m\.role_alignment\s+DESC", sql, re.IGNORECASE
        ), "_SQL_MARKET_SKILLS must ORDER BY m.role_alignment DESC"

    def test_single_program_id_placeholder(self, market_symbols):
        sql = market_symbols["sql"]
        placeholders = sql.count("%s")
        assert placeholders == 1, (
            f"_SQL_MARKET_SKILLS must have exactly 1 %s placeholder, found {placeholders}"
        )

    def test_excludes_null_role_alignment(self, market_symbols):
        sql = market_symbols["sql"]
        assert re.search(
            r"m\.role_alignment\s+IS\s+NOT\s+NULL", sql, re.IGNORECASE
        ), "_SQL_MARKET_SKILLS must exclude NULL role_alignment"

    def test_excludes_null_empleo_id(self, market_symbols):
        sql = market_symbols["sql"]
        assert re.search(
            r"m\.empleo_id\s+IS\s+NOT\s+NULL", sql, re.IGNORECASE
        ), "_SQL_MARKET_SKILLS must exclude NULL empleo_id"

    def test_skills_empleo_guard_present(self, market_symbols):
        sql = market_symbols["sql"]
        assert "skills_empleo" in sql, (
            "_SQL_MARKET_SKILLS must still guard skills_empleo"
        )
        assert "jsonb_typeof" in sql


# ── (b) _market_analysis_for_program call signature and return keys ───────────

EXPECTED_KEYS = {
    "fortalezas", "brechas", "transversales", "brechas_criticas",
    "cobertura_pct", "exclusivas_programa", "evidencia_baja",
    "skills_mercado_raw", "skills_mercado", "skills_programa",
    "n_matches", "n_muestra_alta_media",
}


def _make_mock_rows():
    return [
        {"match_id": 1, "relevance_label": "high",   "skill": "Python"},
        {"match_id": 1, "relevance_label": "high",   "skill": "SQL"},
        {"match_id": 2, "relevance_label": "medium", "skill": "Excel"},
        {"match_id": 3, "relevance_label": "low",    "skill": "Word"},
    ]


def _make_mock_prog_rows():
    return [
        {"skill_name": "Python", "cobertura": 3, "asignaturas": ["Programación"]},
    ]


class TestMarketAnalysisForProgram:
    def test_calls_market_sql_with_single_program_id(self, market_symbols):
        fn  = market_symbols["fn"]
        sql = market_symbols["sql"]
        program_id = 42
        calls: list[tuple] = []

        def fake_fetch(s: str, params: tuple) -> list[dict]:
            calls.append((s, params))
            if s is sql:
                assert params == (program_id,), (
                    f"Market SQL called with {params!r}, expected ({program_id},)"
                )
                return _make_mock_rows()
            return _make_mock_prog_rows()

        fn(program_id, fake_fetch)
        market_calls = [c for c in calls if c[0] is sql]
        assert len(market_calls) == 1, "Market SQL must be called exactly once"
        assert market_calls[0][1] == (program_id,)

    def test_result_contains_all_expected_keys(self, market_symbols):
        fn  = market_symbols["fn"]
        sql = market_symbols["sql"]

        def fake_fetch(s: str, params: tuple) -> list[dict]:
            if s is sql:
                return _make_mock_rows()
            return _make_mock_prog_rows()

        result = fn(99, fake_fetch)
        missing = EXPECTED_KEYS - result.keys()
        assert not missing, f"Missing keys in result: {missing}"

    def test_n_matches_is_int(self, market_symbols):
        fn  = market_symbols["fn"]
        sql = market_symbols["sql"]

        def fake_fetch(s: str, params: tuple) -> list[dict]:
            if s is sql:
                return _make_mock_rows()
            return _make_mock_prog_rows()

        result = fn(99, fake_fetch)
        assert isinstance(result["n_matches"], int)

    def test_empty_market_rows_gives_zero_n_matches(self, market_symbols):
        fn  = market_symbols["fn"]
        sql = market_symbols["sql"]

        def fake_fetch(s: str, params: tuple) -> list[dict]:
            if s is sql:
                return []
            return _make_mock_prog_rows()

        result = fn(99, fake_fetch)
        assert result["n_matches"] == 0
        assert result["evidencia_baja"] is True

    def test_n_muestra_alta_media_counts_high_medium_matches(self, market_symbols):
        fn  = market_symbols["fn"]
        sql = market_symbols["sql"]

        def fake_fetch(s: str, params: tuple) -> list[dict]:
            if s is sql:
                return _make_mock_rows()  # match_ids 1(high), 2(medium), 3(low)
            return _make_mock_prog_rows()

        result = fn(99, fake_fetch)
        # 2 distinct match_ids with high/medium (1 and 2); match_id 3 is low
        assert result["n_muestra_alta_media"] == 2

    def test_jobs_activo_guard_in_sql(self, market_symbols):
        sql = market_symbols["sql"]
        assert re.search(r"COALESCE\s*\(\s*j\.activo", sql, re.IGNORECASE), (
            "_SQL_MARKET_SKILLS must guard with COALESCE(j.activo, TRUE) = TRUE"
        )
