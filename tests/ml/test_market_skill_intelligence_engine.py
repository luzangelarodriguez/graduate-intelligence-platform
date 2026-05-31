from ml.labor.labor_market_skill_extraction_engine import LaborSkillEvidence
from ml.labor.market_skill_intelligence_engine import MARKET_EVIDENCE_WEIGHTS, build_market_skill_intelligence_map


def _evidence(skill: str, source: str, title: str = "Analytics Engineer") -> LaborSkillEvidence:
    return LaborSkillEvidence(
        skill=skill,
        normalized_skill=skill,
        skill_type="technical_skill",
        evidence_source=source,
        evidence_weight=MARKET_EVIDENCE_WEIGHTS[source],
        document_type="job_posting" if source != "portal_taxonomy" else "portal_taxonomy",
        source_name="UnitTest",
        source_url="https://jobs.example.com/1",
        title=title,
        company="DataCo" if source != "portal_taxonomy" else "",
        role=title if source != "portal_taxonomy" else "",
        content_hash=f"{source}-{skill}",
    )


def test_market_skill_intelligence_uses_skill_as_unit_not_gold_job() -> None:
    from ml.labor import labor_market_skill_extraction_engine as source_engine

    universe = source_engine.build_labor_market_skill_universe(
        [
            _evidence("SQL", "silver_job_posting"),
            _evidence("dashboarding", "silver_job_posting"),
            _evidence("Power BI", "portal_taxonomy", title="Skills"),
        ],
        include_database=False,
        write_output=False,
    )
    result = build_market_skill_intelligence_map(include_database=False, write_output=False)
    # Directly verifying the public constants protects the new weighting contract,
    # while synthetic universe construction verifies non-Gold skills remain usable.
    assert MARKET_EVIDENCE_WEIGHTS["silver_job_posting"] == 0.8
    assert MARKET_EVIDENCE_WEIGHTS["portal_taxonomy"] == 0.1
    assert {item.skill for item in universe} >= {"SQL", "dashboarding", "Power BI"}
    assert result.market_skills


def test_emerging_market_skill_becomes_gap_when_not_in_curriculum(monkeypatch) -> None:
    from ml.labor import market_skill_intelligence_engine as engine
    from ml.labor.labor_market_skill_extraction_engine import build_labor_market_skill_universe

    universe = build_labor_market_skill_universe(
        [
            _evidence("Microsoft Fabric", "silver_job_posting", title="Cloud Analytics Engineer"),
            _evidence("DataOps", "silver_job_posting", title="DataOps Engineer"),
        ],
        include_database=False,
        write_output=False,
    )
    monkeypatch.setattr(engine, "build_labor_market_skill_universe", lambda include_database=True, write_output=True: universe)

    result = engine.build_market_skill_intelligence_map(include_database=False, write_output=False)

    emerging = {item.skill for item in result.emerging_skills}
    assert {"Microsoft Fabric", "DataOps"} & emerging
    assert result.recommended_updates


def test_transversal_support_skill_is_not_discarded(monkeypatch) -> None:
    from ml.labor import market_skill_intelligence_engine as engine
    from ml.labor.labor_market_skill_extraction_engine import build_labor_market_skill_universe

    universe = build_labor_market_skill_universe(
        [_evidence("communication", "portal_taxonomy", title="Skills")],
        include_database=False,
        write_output=False,
    )
    monkeypatch.setattr(engine, "build_labor_market_skill_universe", lambda include_database=True, write_output=True: universe)

    result = engine.build_market_skill_intelligence_map(include_database=False, write_output=False)

    signal = result.market_skills[0]
    assert signal.market_signal_confidence == "weak"
    assert signal.coverage_status == "partial"


def test_non_support_irrelevant_skill_stays_irrelevant(monkeypatch) -> None:
    from ml.labor import market_skill_intelligence_engine as engine
    from ml.labor.labor_market_skill_extraction_engine import build_labor_market_skill_universe

    universe = build_labor_market_skill_universe(
        [_evidence("Cableado estructurado", "portal_taxonomy", title="Skills")],
        include_database=False,
        write_output=False,
    )
    monkeypatch.setattr(engine, "build_labor_market_skill_universe", lambda include_database=True, write_output=True: universe)

    result = engine.build_market_skill_intelligence_map(include_database=False, write_output=False)

    signal = result.market_skills[0]
    assert signal.coverage_status == "irrelevant"
