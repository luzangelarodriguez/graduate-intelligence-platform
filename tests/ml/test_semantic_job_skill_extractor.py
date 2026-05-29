from ml.labor.semantic_job_skill_extractor import extract_semantic_job_skills


def test_semantic_skill_confidence_is_high_in_requirements() -> None:
    skills = extract_semantic_job_skills(
        title="Analista BI",
        requirements=["Requisitos: experiencia en SQL, Power BI, Python y ETL."],
        responsibilities=["Responsabilidades: construir dashboards y KPIs ejecutivos."],
        evidence_source_type="job_evidence",
    )

    by_skill = {item.skill: item for item in skills}
    assert by_skill["SQL"].confidence > 0.8
    assert by_skill["Power BI"].section == "requirements"
    assert by_skill["KPIs"].confidence > 0.7


def test_portal_taxonomy_skills_have_low_confidence() -> None:
    skills = extract_semantic_job_skills(
        title="Skills",
        tags=["Power BI SQL Tableau Python filtros categorias ubicaciones"],
        evidence_source_type="portal_taxonomy",
    )

    assert skills
    assert all(item.confidence <= 0.1 for item in skills)
    assert all(item.evidence_source_type == "portal_taxonomy" for item in skills)
