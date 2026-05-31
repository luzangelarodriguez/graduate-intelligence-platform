from __future__ import annotations

from intelligence import executive_observatory_engine as engine


def test_build_executive_observatory_v2_from_program_intelligence(monkeypatch) -> None:
    monkeypatch.setattr(
        engine,
        "_fetch_program_intelligence_rows",
        lambda db_name=None: [
            {
                "program_id": 1,
                "program_name": "Visual Analytics",
                "program_role": "BI Analyst",
                "alignment_score": 72.0,
                "risk_score": 28.0,
                "risk_level": "low",
                "gap_count": 1,
                "top_gaps": [{"missing_skill": "dbt", "urgency_score": 82.0}],
                "top_recommendations": [
                    {
                        "recommendation_type": "curriculum",
                        "target_role": "BI Analyst",
                        "target_company": "curriculum",
                        "recommendation_confidence": 0.91,
                        "recommendation_reasoning": "Fortalecer dbt",
                    }
                ],
                "forecast_signals": [
                    {
                        "entity_type": "skill",
                        "entity_name": "dbt",
                        "horizon_months": 12,
                        "growth_velocity": 0.72,
                        "forecast_confidence": 0.9,
                        "market_phase": "emerging",
                    }
                ],
                "role_signals": [
                    {
                        "source_role": "BI Analyst",
                        "target_role": "Analytics Engineer",
                        "similarity_score": 0.81,
                        "transition_probability": 0.62,
                        "cluster_affinity": "BI & Visualization",
                    }
                ],
                "emerging_technologies": [
                    {
                        "technology": "Generative AI",
                        "growth_velocity": 0.76,
                        "forecast_confidence": 0.88,
                        "emergence_score": 0.85,
                    }
                ],
                "recommended_actions": ["Fortalecer dbt"],
                "business_justification": "Alineación positiva.",
                "supporting_evidence": {"program_skills": ["Power BI"]},
                "source_tables": ["curriculum_gap_observatory", "recommendation_observatory"],
                "confidence": 0.9,
            },
            {
                "program_id": 2,
                "program_name": "Data Engineering",
                "program_role": "Data Engineer",
                "alignment_score": 52.0,
                "risk_score": 62.0,
                "risk_level": "medium",
                "gap_count": 2,
                "top_gaps": [{"missing_skill": "Synapse", "urgency_score": 66.0}],
                "top_recommendations": [],
                "forecast_signals": [],
                "role_signals": [],
                "emerging_technologies": [
                    {
                        "technology": "AI Agents",
                        "growth_velocity": 0.84,
                        "forecast_confidence": 0.92,
                        "emergence_score": 0.9,
                    }
                ],
                "recommended_actions": ["Fortalecer Synapse"],
                "business_justification": "Alineación parcial.",
                "supporting_evidence": {"program_skills": ["Spark"]},
                "source_tables": ["program_intelligence"],
                "confidence": 0.8,
            },
        ],
    )
    monkeypatch.setattr(
        engine,
        "_fetch_observatory_summary_rows",
        lambda db_name=None: {
            "observatory_metrics": [
                {"metric_name": "alignment_average", "metric_value": 62.0},
                {"metric_name": "programs_at_risk", "metric_value": 1.0},
            ],
            "recommendation_observatory": [],
        },
    )
    monkeypatch.setattr(engine, "persist_executive_observatory_metrics", lambda metrics, db_name=None: len(metrics))

    result = engine.build_executive_observatory_v2(persist=False)

    assert result.programs_analyzed == 2
    assert result.alignment_average == 62.0
    assert result.high_risk_programs == []
    assert len(result.medium_risk_programs) == 1
    assert result.low_risk_programs[0]["program_name"] == "Visual Analytics"
    assert result.critical_gaps[0]["missing_skill"] == "dbt"
    assert result.top_emerging_skills[0]["skill_name"] in {"Generative AI", "AI Agents"}
    assert result.top_recommendations[0]["recommendation_type"] == "curriculum"
    assert result.top_programs[0]["program_name"] == "Visual Analytics"
    assert "moderate alignment" in result.executive_narrative
    assert "dbt" in result.executive_narrative
    assert result.source_tables == ["program_intelligence", "observatory_metrics", "recommendation_observatory"]


def test_persist_executive_observatory_metrics(monkeypatch) -> None:
    monkeypatch.setattr(engine, "relation_exists", lambda name, db_name=None: True)

    class DummyCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def cursor(self):
            return DummyCursor()

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

    count = engine.persist_executive_observatory_metrics(
        [
            {
                "metric_name": "alignment_average",
                "metric_category": "executive_v2",
                "metric_value": 62.0,
                "metric_period": "2026-05",
                "confidence_score": 0.92,
                "supporting_evidence": {"programs_analyzed": 2},
            }
        ]
    )

    assert count == 1
    assert "INSERT INTO observatory_metrics" in captured["sql"]
    assert captured["rows"][0][0] == "alignment_average"
