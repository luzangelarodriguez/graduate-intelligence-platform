from __future__ import annotations

from types import SimpleNamespace

from intelligence import curriculum_impact_simulator as cis


def _normalized_skill(canonical_skill: str, confidence: float = 0.92) -> SimpleNamespace:
    payload = {
        "raw_skill": canonical_skill,
        "raw_skill_normalized": canonical_skill.casefold(),
        "canonical_skill": canonical_skill,
        "canonical_skill_id": 1,
        "skill_category": "Cloud",
        "skill_family": "Platform",
        "match_method": "alias",
        "confidence_score": confidence,
        "source_payload": {"source": "test"},
    }
    return SimpleNamespace(**payload, to_dict=lambda payload=payload: dict(payload))


def test_curriculum_simulator_projects_positive_alignment(monkeypatch) -> None:
    monkeypatch.setattr(cis, "_load_program_base", lambda program_id, db_name=None: {"id": program_id, "nombre_especializacion": "Visual Analytics", "rol": "BI"})
    monkeypatch.setattr(
        cis,
        "_load_program_intelligence",
        lambda program_id, db_name=None: {
            "program_id": program_id,
            "program_name": "Visual Analytics",
            "program_role": "BI",
            "alignment_score": 62.0,
            "risk_score": 58.0,
            "top_gaps": [{"missing_skill": "AWS", "urgency_score": 82}],
            "recommended_actions": ["Fortalecer AWS"],
            "confidence": 0.8,
            "supporting_evidence": {},
            "source_tables": ["program_intelligence"],
        },
    )
    monkeypatch.setattr(
        cis,
        "_load_gap_rows",
        lambda program_name, db_name=None: [
            {
                "specialization": "Visual Analytics",
                "missing_skill": "AWS",
                "market_demand_score": 80,
                "curriculum_coverage_score": 35,
                "urgency_score": 82,
                "emergence_score": 65,
                "recommendation": "Agregar AWS",
                "evidence": {"source": "gap_observatory"},
            }
        ],
    )
    monkeypatch.setattr(cis, "_load_recommendation_rows", lambda program_name, db_name=None: [])
    monkeypatch.setattr(
        cis,
        "_load_skill_forecasts",
        lambda db_name=None: [
            {
                "entity_type": "skill",
                "entity_name": "AWS",
                "horizon_months": 12,
                "growth_velocity": 0.82,
                "forecast_confidence": 0.78,
                "market_phase": "emerging",
                "first_seen_at": None,
                "last_seen_at": None,
                "evidence": {"source": "market_forecasts"},
            }
        ],
    )
    monkeypatch.setattr(cis, "normalize_skill_batch", lambda skills, db_name=None, persist=False, source="curriculum_simulator": [_normalized_skill(skill) for skill in dict.fromkeys(skills)])
    monkeypatch.setattr(cis, "persist_curriculum_simulation", lambda result, db_name=None: 1)
    monkeypatch.setattr(cis, "_persist_gap_mappings", lambda **kwargs: 1)
    monkeypatch.setattr(cis, "_persist_program_market_pressure", lambda **kwargs: 1)
    monkeypatch.setattr(cis, "_persist_program_employability", lambda **kwargs: 1)
    monkeypatch.setattr(cis, "_persist_program_risk", lambda **kwargs: 3)

    result = cis.build_curriculum_impact_simulation(42, proposed_skills=["AWS"], persist=True)

    assert result.program_id == 42
    assert result.projected_alignment_score > result.current_alignment_score
    assert result.projected_risk_score < result.current_risk_score
    assert result.projected_gap_reduction > 0
    assert result.confidence_score > 0.4


def test_curriculum_simulator_uses_gap_skills_when_proposals_missing(monkeypatch) -> None:
    monkeypatch.setattr(cis, "_load_program_base", lambda program_id, db_name=None: {"id": program_id, "nombre_especializacion": "Data Engineering", "rol": "DE"})
    monkeypatch.setattr(
        cis,
        "_load_program_intelligence",
        lambda program_id, db_name=None: {
            "program_id": program_id,
            "program_name": "Data Engineering",
            "program_role": "DE",
            "alignment_score": 48.0,
            "risk_score": 76.0,
            "top_gaps": [{"missing_skill": "Databricks", "urgency_score": 90}],
            "recommended_actions": ["Incluir Databricks"],
            "confidence": 0.7,
            "supporting_evidence": {},
            "source_tables": ["program_intelligence"],
        },
    )
    monkeypatch.setattr(
        cis,
        "_load_gap_rows",
        lambda program_name, db_name=None: [
            {
                "specialization": "Data Engineering",
                "missing_skill": "Databricks",
                "market_demand_score": 91,
                "curriculum_coverage_score": 18,
                "urgency_score": 90,
                "emergence_score": 78,
                "recommendation": "Agregar Databricks",
                "evidence": {"source": "gap_observatory"},
            }
        ],
    )
    monkeypatch.setattr(cis, "_load_recommendation_rows", lambda program_name, db_name=None: [])
    monkeypatch.setattr(cis, "_load_skill_forecasts", lambda db_name=None: [])
    monkeypatch.setattr(cis, "normalize_skill_batch", lambda skills, db_name=None, persist=False, source="curriculum_simulator": [_normalized_skill(skill) for skill in dict.fromkeys(skills)])

    result = cis.build_curriculum_impact_simulation(7, proposed_skills=None, persist=False)

    assert result.proposed_skills == ["Databricks"]
    assert result.normalized_skills[0]["canonical_skill"] == "Databricks"
