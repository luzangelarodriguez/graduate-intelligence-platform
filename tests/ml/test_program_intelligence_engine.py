from __future__ import annotations

from intelligence import program_intelligence_engine as engine


def test_build_program_intelligence_from_observatory_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        engine.dashboard_service,
        "list_programs_base",
        lambda db_name=None: [
            {
                "especializacion_id": 1,
                "nombre_especializacion": "Especialización en Visual Analytics y Big Data",
                "rol": "BI Analyst",
                "promedio_match_mercado": 72.0,
                "porcentaje_match": 72.0,
            }
        ],
    )
    monkeypatch.setattr(
        engine.programas_repository,
        "fetch_program_skill_rows",
        lambda program_id, db_name=None: [{"skill_id": 1, "nombre": "Power BI"}, {"skill_id": 2, "nombre": "dbt"}, {"skill_id": 3, "nombre": "RAG"}],
    )
    monkeypatch.setattr(
        engine,
        "relation_exists",
        lambda name, db_name=None: True,
    )
    observatory_rows = {
        "curriculum_gap_observatory": [
            {
                "specialization": "Especialización en Visual Analytics y Big Data",
                "missing_skill": "dbt",
                "market_demand_score": 88.0,
                "curriculum_coverage_score": 0.35,
                "urgency_score": 82.0,
                "emergence_score": 63.0,
                "recommendation": "Fortalecer dbt",
                "evidence": {"source_tables": ["curriculum_gap_observatory"]},
                "generated_at": "2026-05-01T00:00:00Z",
            }
        ],
        "recommendation_observatory": [
            {
                "recommendation_type": "curriculum",
                "target_role": "BI Analyst",
                "target_company": "curriculum",
                "recommendation_payload": {"recommended_skills": ["dbt"]},
                "recommendation_reasoning": "Actualizar dbt",
                "recommendation_confidence": 0.91,
                "recommendation_evidence": {"source_tables": ["recommendation_observatory"]},
                "metric_period": "2026-05",
                "generated_at": "2026-05-01T00:00:00Z",
            }
        ],
        "market_forecasts": [
            {
                "entity_type": "skill",
                "entity_name": "dbt",
                "horizon_months": 12,
                "growth_velocity": 0.72,
                "forecast_confidence": 0.9,
                "market_phase": "emerging",
                "first_seen_at": None,
                "last_seen_at": None,
                "evidence": {"source": "market_forecasts"},
            }
        ],
        "semantic_role_graph": [
            {
                "source_role": "BI Analyst",
                "target_role": "Analytics Engineer",
                "similarity_score": 0.81,
                "transition_probability": 0.62,
                "shared_skills": ["Power BI"],
                "cluster_affinity": "BI & Visualization",
                "centrality_score": 0.44,
                "evidence": {"source_tables": ["semantic_role_graph"]},
                "metric_period": "2026-05",
            }
        ],
        "emerging_technology_observatory": [
            {
                "technology": "Microsoft Fabric",
                "emergence_score": 0.85,
                "growth_velocity": 0.76,
                "adoption_trend": "rising",
                "forecast_confidence": 0.88,
                "source_payload": {"source_tables": ["emerging_technology_observatory"]},
                "metric_period": "2026-05",
            }
        ],
    }

    def fake_fetch_all(sql: str, params=(), db_name=None):
        if "curriculum_gap_observatory" in sql:
            return observatory_rows["curriculum_gap_observatory"]
        if "recommendation_observatory" in sql:
            return observatory_rows["recommendation_observatory"]
        if "market_forecasts" in sql:
            return observatory_rows["market_forecasts"]
        if "semantic_role_graph" in sql:
            return observatory_rows["semantic_role_graph"]
        if "emerging_technology_observatory" in sql:
            return observatory_rows["emerging_technology_observatory"]
        return []

    monkeypatch.setattr(engine, "fetch_all", fake_fetch_all)

    items = engine.build_program_intelligence()

    assert len(items) == 1
    item = items[0]
    assert item.program_id == 1
    assert item.risk_score > 0
    assert item.gap_count == 1
    assert any(gap["missing_skill"] == "dbt" for gap in item.top_gaps)
    assert "dbt" in item.recommended_actions[0]
    assert "curriculum_gap_observatory" in item.source_tables
    assert item.supporting_evidence["program_skills"]


def test_build_program_intelligence_deduplicates_program_names(monkeypatch) -> None:
    monkeypatch.setattr(
        engine.dashboard_service,
        "list_programs_base",
        lambda db_name=None: [
            {
                "especializacion_id": 18,
                "nombre_especializacion": "Especialización en Derechos Humanos",
                "rol": "Human Rights Specialist",
                "promedio_match_mercado": 61.0,
                "porcentaje_match": 61.0,
                "total_skills_programa": 4,
                "source_url": "https://example.edu/a",
                "plan_estudios": "pdf-a",
            },
            {
                "especializacion_id": 99,
                "nombre_especializacion": "especialización en derechos humanos",
                "rol": "Human Rights Specialist",
                "promedio_match_mercado": 59.0,
                "porcentaje_match": 59.0,
                "total_skills_programa": 2,
                "source_url": "",
                "plan_estudios": "",
            },
        ],
    )
    monkeypatch.setattr(
        engine.programas_repository,
        "fetch_program_skill_rows",
        lambda program_id, db_name=None: [{"skill_id": 1, "nombre": "DD.HH."}],
    )
    monkeypatch.setattr(engine, "relation_exists", lambda name, db_name=None: False)
    monkeypatch.setattr(engine, "fetch_all", lambda *args, **kwargs: [])

    items = engine.build_program_intelligence()

    assert len(items) == 1
    assert items[0].program_id == 18
    assert items[0].program_name == "Especialización en Derechos Humanos"


def test_persist_program_intelligence_uses_upsert(monkeypatch) -> None:
    monkeypatch.setattr(engine, "relation_exists", lambda name, db_name=None: True)

    class DummyCursor:
        def __init__(self) -> None:
            self.executed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def __init__(self) -> None:
            self.cursor_obj = DummyCursor()

        def cursor(self):
            return self.cursor_obj

        def commit(self) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    captured = {}

    def fake_execute_values(cur, sql, rows):
        captured["sql"] = sql
        captured["rows"] = rows

    monkeypatch.setattr(engine, "get_conn", lambda: DummyConn())
    monkeypatch.setattr(engine, "execute_values", fake_execute_values)

    record = engine.ProgramIntelligenceItem(
        program_id=1,
        program_name="Visual Analytics",
        program_role="BI Analyst",
        alignment_score=72.0,
        risk_score=28.0,
        risk_level="low",
        gap_count=1,
        top_gaps=[{"missing_skill": "dbt"}],
        top_recommendations=[],
        forecast_signals=[],
        role_signals=[],
        emerging_technologies=[],
        recommended_actions=["Fortalecer dbt"],
        business_justification="Alineación positiva.",
        supporting_evidence={"program_skills": ["Power BI"]},
        source_tables=["curriculum_gap_observatory"],
        confidence=0.9,
        generated_at="2026-05-01T00:00:00Z",
    )

    count = engine.persist_program_intelligence([record])

    assert count == 1
    assert "INSERT INTO program_intelligence" in captured["sql"]
    assert captured["rows"][0][0] == 1
