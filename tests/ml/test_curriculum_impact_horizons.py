from __future__ import annotations

from types import SimpleNamespace

from intelligence import curriculum_impact_simulator as cis


class _ProgramIntelligence(SimpleNamespace):
    def to_dict(self):
        return dict(self.__dict__)


def test_curriculum_impact_changes_by_horizon(monkeypatch) -> None:
    monkeypatch.setattr(cis.programas_repository, "fetch_program_base_row", lambda program_id, db_name=None: {
        "especializacion_id": program_id,
        "nombre_especializacion": "Ingeniería de Datos",
        "rol": "Data Engineer",
        "promedio_match_mercado": 52.0,
    })
    monkeypatch.setattr(cis, "build_program_intelligence_for_program", lambda program_id, db_name=None: _ProgramIntelligence(
        program_id=program_id,
        program_name="Ingeniería de Datos",
        program_role="Data Engineer",
        alignment_score=52.0,
        risk_score=48.0,
        top_gaps=[{"missing_skill": "AWS", "urgency_score": 82, "market_demand_score": 91, "curriculum_coverage_score": 22}],
        top_recommendations=[{"recommended_skills": ["AWS", "Databricks"]}],
    ))
    monkeypatch.setattr(cis, "relation_exists", lambda table, db_name=None: table in {"program_intelligence", "curriculum_gap_observatory", "market_forecasts"})

    def fake_fetch_all(sql, params=None, db_name=None):
        sql_text = str(sql).lower()
        if "from curriculum_gap_observatory" in sql_text:
            return [
                {
                    "specialization": "Ingeniería de Datos",
                    "missing_skill": "AWS",
                    "market_demand_score": 91,
                    "curriculum_coverage_score": 22,
                    "urgency_score": 82,
                    "emergence_score": 70,
                    "recommendation": "Fortalecer AWS",
                    "evidence": {"source_tables": ["curriculum_gap_observatory"]},
                    "generated_at": "2026-05-31T00:00:00Z",
                }
            ]
        if "from recommendation_observatory" in sql_text:
            return [
                {
                    "recommendation_type": "curriculum_gap",
                    "target_role": "Data Engineer",
                    "target_company": "Globant",
                    "recommendation_payload": {"recommended_skills": ["AWS", "Databricks"]},
                    "recommendation_reasoning": "Se requiere cloud analytics",
                    "recommendation_confidence": 0.93,
                    "recommendation_evidence": {"source_tables": ["recommendation_observatory"]},
                    "metric_period": "2026-05",
                    "generated_at": "2026-05-31T00:00:00Z",
                    "estimated_alignment_increase": 12.0,
                    "estimated_employability_gain": 10.0,
                    "estimated_risk_reduction": 8.0,
                }
            ]
        if "from market_forecasts" in sql_text:
            return [
                {
                    "entity_type": "skill",
                    "entity_name": "AWS",
                    "horizon_months": 6,
                    "growth_velocity": 18.0,
                    "forecast_confidence": 0.91,
                    "market_phase": "emerging",
                    "first_seen_at": "2026-01-01T00:00:00Z",
                    "last_seen_at": "2026-05-31T00:00:00Z",
                    "evidence": {"source_tables": ["market_forecasts"]},
                    "generated_at": "2026-05-31T00:00:00Z",
                }
            ]
        return []

    monkeypatch.setattr(cis, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(
        cis,
        "fetch_one",
        lambda sql, params=None, db_name=None: {
            "program_id": 42,
            "program_name": "Ingeniería de Datos",
            "program_role": "Data Engineer",
            "alignment_score": 52.0,
            "risk_score": 48.0,
            "top_gaps": [{"missing_skill": "AWS", "urgency_score": 82, "market_demand_score": 91, "curriculum_coverage_score": 22}],
            "top_recommendations": [{"recommended_skills": ["AWS", "Databricks"]}],
            "generated_at": "2026-05-31T00:00:00Z",
        }
        if "from program_intelligence" in str(sql).lower()
        else None,
    )
    monkeypatch.setattr(cis, "normalize_skill_batch", lambda skills, db_name=None, persist=True, source=None: [SimpleNamespace(to_dict=lambda skill=s: {"canonical_skill_id": idx + 1, "canonical_skill": skill, "confidence_score": 0.9}) for idx, s in enumerate(skills)])

    result_6 = cis.build_curriculum_impact_simulation(42, proposed_skills=["AWS"], horizon_months=6, persist=False)
    result_12 = cis.build_curriculum_impact_simulation(42, proposed_skills=["AWS"], horizon_months=12, persist=False)
    result_24 = cis.build_curriculum_impact_simulation(42, proposed_skills=["AWS"], horizon_months=24, persist=False)

    assert result_6.projected_alignment_score < result_12.projected_alignment_score < result_24.projected_alignment_score
    assert result_6.projected_risk_score > result_12.projected_risk_score > result_24.projected_risk_score
    assert result_6.projected_employability_gain < result_12.projected_employability_gain < result_24.projected_employability_gain
