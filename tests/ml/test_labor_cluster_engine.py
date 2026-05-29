from ml.clustering.labor_cluster_engine import LaborJobSignal, build_labor_occupational_clusters


def _job(job_id: str, title: str, skills: list[str], description: str = "") -> LaborJobSignal:
    return LaborJobSignal(
        job_id=job_id,
        title=title,
        description=description or f"{title} requiere {', '.join(skills)} para analitica empresarial.",
        company="Empresa Datos SAS",
        source_url=f"https://jobs.example.com/{job_id}",
        skills=skills,
        tools=[skill for skill in skills if skill in {"Power BI", "Tableau", "Databricks", "Snowflake"}],
        technologies=[skill for skill in skills if skill in {"Spark", "Azure", "Databricks", "Snowflake"}],
        contextual_evidence=f"Evidencia laboral: {', '.join(skills)}.",
        curriculum_alignment_score=0.72,
        gold_score=0.74,
        semantic_clusters={},
        responsibilities=["Construir productos analiticos y tableros ejecutivos."],
    )


def test_clusters_only_use_valid_job_posting_inputs() -> None:
    jobs = [
        _job("bi-1", "BI Analyst", ["Power BI", "SQL", "dashboarding", "KPIs"]),
        _job("bi-2", "Reporting Analyst", ["Tableau", "SQL", "reporting", "KPIs"]),
        _job("de-1", "Data Engineer", ["ETL", "Spark", "data warehouse", "Databricks"]),
    ]

    clusters = build_labor_occupational_clusters(jobs, write_outputs=False)

    assert clusters
    assert sum(cluster.market_frequency for cluster in clusters) == len(jobs)
    assert any(cluster.cluster_name in {"BI & Visualization", "Reporting & KPI"} for cluster in clusters)
    assert any("Especializacion en Visual Analytics y Big Data" in cluster.specialization_affinity for cluster in clusters)


def test_invalid_url_jobs_are_excluded_from_clusters() -> None:
    jobs = [
        _job("valid", "Power BI Developer", ["Power BI", "SQL", "dashboarding"]),
        LaborJobSignal(
            job_id="taxonomy",
            title="Skills",
            description="Power BI SQL Python Tableau filtros y categorias",
            company="",
            source_url="javascript:;",
            skills=["Power BI", "SQL", "Python", "Tableau"],
            tools=[],
            technologies=[],
            contextual_evidence="Catalogo del portal.",
            curriculum_alignment_score=0.0,
            gold_score=0.0,
            semantic_clusters={},
            responsibilities=[],
        ),
    ]

    clusters = build_labor_occupational_clusters(jobs, write_outputs=False)

    assert sum(cluster.market_frequency for cluster in clusters) == 1
    assert clusters[0].jobs[0].job_id == "valid"
