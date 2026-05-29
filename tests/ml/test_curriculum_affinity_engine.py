from ml.clustering.labor_cluster_engine import LaborJobSignal, build_labor_occupational_clusters
from ml.recommendations.curriculum_recommendation_engine import recommendations_from_cluster


def test_cluster_affinity_supports_multiple_specializations_and_gaps() -> None:
    job = LaborJobSignal(
        job_id="cloud-analytics-1",
        title="Cloud Analytics Engineer",
        description="Desarrolla pipelines analytics en Azure, Synapse, Databricks, reporting y KPIs.",
        company="Analytics Cloud SAS",
        source_url="https://jobs.example.com/cloud-analytics-1",
        skills=["SQL", "ETL", "dashboarding", "Azure Synapse", "Databricks", "data governance"],
        tools=["Databricks"],
        technologies=["Azure Synapse", "Databricks"],
        contextual_evidence="Alineada por SQL, ETL, reporting, KPIs, Azure Synapse y Databricks.",
        curriculum_alignment_score=0.77,
        gold_score=0.79,
        semantic_clusters={"cloud_data": ["Azure Synapse", "Databricks"]},
        responsibilities=["Integrar datos y construir capacidades de analitica cloud."],
    )

    clusters = build_labor_occupational_clusters([job], write_outputs=False)

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.specialization_affinity["Especializacion en Visual Analytics y Big Data"] > 0
    assert cluster.specialization_affinity["Especializacion en Big Data"] >= cluster.specialization_affinity["Especializacion en Visual Analytics y Big Data"]
    assert any(gap["emerging_skill"] in {"Azure Synapse", "Databricks", "data governance"} for gap in cluster.market_gaps)


def test_recommendation_engine_generates_curricular_actions_from_cluster() -> None:
    job = LaborJobSignal(
        job_id="ai-analytics-1",
        title="AI Analytics Specialist",
        description="Modelos predictivos, machine learning, notebooks, MLOps y visualizacion ejecutiva.",
        company="IA Aplicada SAS",
        source_url="https://jobs.example.com/ai-analytics-1",
        skills=["machine learning", "Python", "MLOps", "dashboarding"],
        tools=[],
        technologies=[],
        contextual_evidence="Vacante exige Python, MLOps, modelos predictivos y visualizacion.",
        curriculum_alignment_score=0.71,
        gold_score=0.73,
        semantic_clusters={"ai_analytics": ["machine learning", "MLOps"]},
        responsibilities=["Diseñar modelos y traducir resultados a decisiones ejecutivas."],
    )

    cluster = build_labor_occupational_clusters([job], write_outputs=False)[0]
    recommendations = recommendations_from_cluster(cluster)

    assert recommendations
    assert recommendations[0].suggested_module
    assert recommendations[0].curricular_action
    assert recommendations[0].evidence
