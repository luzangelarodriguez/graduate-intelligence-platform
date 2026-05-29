from ml.curriculum.curriculum_market_gap_engine import build_curriculum_market_gap_map
from ml.labor.labor_market_skill_extraction_engine import LaborMarketSkill, LaborSkillEvidence, build_labor_market_skill_universe
from ml.labor.occupational_skill_cluster_engine import build_occupational_skill_clusters


def _evidence(skill: str, source: str, weight: float, title: str = "BI Analyst") -> LaborSkillEvidence:
    return LaborSkillEvidence(
        skill=skill,
        normalized_skill=skill,
        skill_type="tool",
        evidence_source=source,
        evidence_weight=weight,
        document_type="job_posting" if source != "portal_taxonomy" else "portal_taxonomy",
        source_name="UnitTest",
        source_url="https://jobs.example.com/1",
        title=title,
        company="Empresa",
        role=title,
        content_hash=f"{source}-{skill}",
    )


def test_labor_skill_universe_preserves_evidence_weights() -> None:
    universe = build_labor_market_skill_universe(
        [
            _evidence("Power BI", "gold_job_posting", 1.0),
            _evidence("Power BI", "silver_job_posting", 0.7),
            _evidence("Tableau", "portal_taxonomy", 0.1),
        ],
        include_database=False,
        write_output=False,
    )

    by_skill = {item.skill: item for item in universe}
    assert by_skill["Power BI"].total_weight == 1.7
    assert by_skill["Power BI"].source_breakdown == {"gold_job_posting": 1, "silver_job_posting": 1}
    assert by_skill["Tableau"].total_weight == 0.1
    assert by_skill["Tableau"].source_breakdown == {"portal_taxonomy": 1}


def test_occupational_skill_clusters_group_market_skills() -> None:
    universe = build_labor_market_skill_universe(
        [
            _evidence("Power BI", "gold_job_posting", 1.0),
            _evidence("SQL", "silver_job_posting", 0.7),
            _evidence("Databricks", "silver_job_posting", 0.7, title="Data Engineer"),
        ],
        include_database=False,
        write_output=False,
    )

    clusters = build_occupational_skill_clusters(universe, write_output=False)

    assert {cluster.cluster_name for cluster in clusters} & {"BI & Visualization", "Data Engineering"}
    assert any(cluster.is_strong_market_signal for cluster in clusters)


def test_gap_map_classifies_covered_missing_and_emerging_skills() -> None:
    universe = [
        LaborMarketSkill(
            skill="Power BI",
            skill_type="tool",
            total_weight=1.0,
            evidence_count=1,
            source_breakdown={"gold_job_posting": 1},
            roles=["BI Analyst"],
            companies=["Empresa"],
            source_urls=["https://jobs.example.com/powerbi"],
            evidence=[_evidence("Power BI", "gold_job_posting", 1.0)],
        ),
        LaborMarketSkill(
            skill="Microsoft Fabric",
            skill_type="cloud",
            total_weight=0.9,
            evidence_count=1,
            source_breakdown={"silver_job_posting": 1},
            roles=["Cloud Analytics Engineer"],
            companies=["Empresa"],
            source_urls=["https://jobs.example.com/fabric"],
            evidence=[_evidence("Microsoft Fabric", "silver_job_posting", 0.7, title="Cloud Analytics Engineer")],
        ),
        LaborMarketSkill(
            skill="Cableado estructurado",
            skill_type="technical_skill",
            total_weight=0.1,
            evidence_count=1,
            source_breakdown={"portal_taxonomy": 1},
            roles=[],
            companies=[],
            source_urls=["https://jobs.example.com/filter"],
            evidence=[_evidence("Cableado estructurado", "portal_taxonomy", 0.1, title="Skills")],
        ),
    ]

    gap_map = build_curriculum_market_gap_map(universe=universe, write_output=False)

    covered = {item.skill for item in gap_map.covered_skills}
    emerging = {item.skill for item in gap_map.emerging_skills}
    irrelevant = {item.skill for item in gap_map.irrelevant_skills}
    assert "Power BI" in covered
    assert "Microsoft Fabric" in emerging
    assert "Cableado estructurado" in irrelevant
    assert gap_map.recommended_curriculum_updates
