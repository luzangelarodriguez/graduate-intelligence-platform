"""
Verifica que dashboard_skills_analysis enriquece brechas, brechas_criticas,
fortalezas y transversales con tipo_skill proveniente del backend.

Patrón: stubs de sys.modules para evitar dependencias de FastAPI/BD.
  1. Instalar stubs → importar api.main → extraer función → restaurar sys.modules.
  2. En cada test: reinstalar stubs temporalmente (el endpoint usa dynamic imports)
     → llamar la función → quitar stubs.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


# ── Stubs ─────────────────────────────────────────────────────────────────────

def _build_stubs() -> dict[str, types.ModuleType]:
    stubs: dict[str, types.ModuleType] = {}

    def stub(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        stubs[name] = m
        return m

    fa = stub("fastapi")
    # Route decorators must be pass-throughs so the real function body is preserved.
    _passthrough = lambda path, **kw: (lambda func: func)
    _app_mock = MagicMock()
    for _method in ("get", "post", "put", "delete", "patch"):
        setattr(_app_mock, _method, _passthrough)
    fa.FastAPI = MagicMock(return_value=_app_mock)
    fa.BackgroundTasks = MagicMock()
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

    # tipo_skill: returns "herramienta" for every skill
    tipo = stub("api.tipo_skill")
    tipo.tipo_para_skill = lambda skill, lookup: "herramienta"

    # backend hierarchy: _clean_tipo_skill passes through the raw category
    stub("backend")
    stub("backend.repositories")
    emp = stub("backend.repositories.empleos_repository")
    emp._clean_tipo_skill = lambda _, cat: (cat or "competencia").lower()

    # crawlers hierarchy: canonicalize_skill returns a mock with .category
    stub("crawlers")
    stub("crawlers.storage")
    pg = stub("crawlers.storage.postgres_warehouse")
    _cat = MagicMock()
    _cat.category = "Tool"
    pg.canonicalize_skill = lambda _: _cat

    return stubs


@pytest.fixture(scope="session")
def enriquecimiento_symbols():
    """
    Import dashboard_skills_analysis with stubs in place, then restore sys.modules.
    Yields {"fn": <function>, "stubs": <dict>}.
    """
    stubs = _build_stubs()
    keys_to_touch = list(stubs.keys()) + ["api.main"]
    originals = {k: sys.modules.get(k) for k in keys_to_touch}

    for name, mod in stubs.items():
        sys.modules[name] = mod
    sys.modules.pop("api.main", None)

    try:
        import api.main as _main  # noqa: PLC0415
        fn      = _main.dashboard_skills_analysis
        sql_mkt  = _main._SQL_MARKET_SKILLS
        sql_size = _main._SQL_MARKET_SIZE
        sql_prog = _main._SQL_PROG_SKILLS
    finally:
        for name, orig in originals.items():
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig

    yield {"fn": fn, "stubs": stubs,
           "sql_mkt": sql_mkt, "sql_size": sql_size, "sql_prog": sql_prog}


# ── Helper data ────────────────────────────────────────────────────────────────

_N_JOBS = 10


def _market_rows() -> list[dict]:
    rows = []
    for i in range(1, _N_JOBS + 1):
        for skill in ("Python", "Excel", "trabajo en equipo"):
            rows.append({"match_id": i, "empleo_id": f"e{i}", "skill": skill})
    return rows


def _prog_rows() -> list[dict]:
    return [{"skill_name": "Python", "cobertura": 3, "asignaturas": ["Programación"]}]


def _tipo_rows() -> list[dict]:
    return [
        {"skill_key": "python", "tipo_skill_raw": "herramienta"},
        {"skill_key": "excel",  "tipo_skill_raw": "herramienta"},
    ]


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestEnriquecimientoTipoSkill:
    """
    Verifica que el endpoint de enriquecimiento agrega tipo_skill a todas
    las listas del resultado.

    Datos de prueba:
      Mercado  : Python (10), Excel (10), "trabajo en equipo" (10, transversal)
      Programa : Python → 1 fortaleza, Excel → 1 brecha (y brecha_crítica),
                 "trabajo en equipo" → transversal
    """

    def _run(self, enriquecimiento_symbols: dict) -> dict:
        fn       = enriquecimiento_symbols["fn"]
        stubs    = enriquecimiento_symbols["stubs"]
        sql_mkt  = enriquecimiento_symbols["sql_mkt"]
        sql_size = enriquecimiento_symbols["sql_size"]
        sql_prog = enriquecimiento_symbols["sql_prog"]

        def fake_fetch_all(sql: str, params: tuple) -> list[dict]:
            if sql is sql_mkt:
                return _market_rows()
            if sql is sql_size:
                return [{"n_vacantes_muestra": _N_JOBS}]
            if sql is sql_prog:
                return _prog_rows()
            # tipo_rows SQL (job_skills join — identified by content)
            return _tipo_rows()

        stubs["api.database"].fetch_all = fake_fetch_all

        originals = {k: sys.modules.get(k) for k in stubs}
        for name, mod in stubs.items():
            sys.modules[name] = mod
        try:
            return fn(program_id=13)
        finally:
            for name, orig in originals.items():
                if orig is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = orig

    def test_brechas_tienen_tipo_skill(self, enriquecimiento_symbols):
        result = self._run(enriquecimiento_symbols)
        brechas = result.get("brechas", [])
        assert len(brechas) > 0, "Se esperaba al menos una brecha"
        for b in brechas:
            assert "tipo_skill" in b, f"brecha {b!r} no tiene tipo_skill"
            assert b["tipo_skill"] is not None

    def test_brechas_criticas_tienen_tipo_skill(self, enriquecimiento_symbols):
        result = self._run(enriquecimiento_symbols)
        bc = result.get("brechas_criticas", [])
        assert len(bc) > 0, "Se esperaba al menos una brecha_crítica"
        for b in bc:
            assert "tipo_skill" in b, f"brecha_crítica {b!r} no tiene tipo_skill"
            assert b["tipo_skill"] is not None

    def test_fortalezas_tienen_tipo_skill(self, enriquecimiento_symbols):
        result = self._run(enriquecimiento_symbols)
        fort = result.get("fortalezas", [])
        assert len(fort) > 0, "Se esperaba al menos una fortaleza"
        for f in fort:
            assert "tipo_skill" in f, f"fortaleza {f!r} no tiene tipo_skill"
            assert f["tipo_skill"] is not None

    def test_transversales_tienen_tipo_skill(self, enriquecimiento_symbols):
        result = self._run(enriquecimiento_symbols)
        trans = result.get("transversales", [])
        assert len(trans) > 0, "Se esperaba al menos un transversal"
        for t in trans:
            assert "tipo_skill" in t, f"transversal {t!r} no tiene tipo_skill"
            assert t["tipo_skill"] is not None
