from __future__ import annotations

from scrapers.normalization.classify_domains import classify_program_domain
from microcurriculum_engine.normalization.skill_extractor import extract_microcurriculum_skills
from microcurriculum_engine.recommendations.recommendation_engine import generate_recommendations
from microcurriculum_engine.matching.market_matching import MarketComparison
from intelligence.domain_benchmark_layer import build_domain_benchmark
from intelligence.domain_taxonomy_layer import build_domain_taxonomy_from_program


def test_criminology_domain_supports_domain_specific_benchmarking() -> None:
    taxonomy = build_domain_taxonomy_from_program(
        program_name="Especialización en Criminología",
        program_role="Forensic Analyst",
        microcurriculum_context={},
    )
    benchmark = build_domain_benchmark("criminology")

    assert taxonomy.domain_label == "Criminology"
    assert taxonomy.confidence >= 0.35
    assert benchmark.benchmark_institutions
    assert "criminal investigation" in {skill.lower() for skill in benchmark.market_skills}
    assert "criminologia" in benchmark.narrative_focus.lower()


def test_criminology_skill_extraction_preserves_domain_identity() -> None:
    text = (
        "La asignatura aborda investigacion criminal, victimologia, criminalistica, cadena de custodia, "
        "analisis forense, inteligencia criminal y prevencion del delito."
    )
    result = extract_microcurriculum_skills(text, title="Criminología Aplicada")

    assert result["domain_prediction"]["domain"] == "criminology"
    skills = {item["skill_normalized"] for item in result["skills"]}
    assert "criminal investigation" in skills
    assert "victimology" in skills
    assert "forensic analysis" in skills


def test_criminology_recommendations_use_criminology_templates() -> None:
    comparison = MarketComparison(
        market_skills=["criminal investigation", "victimology", "cybercrime", "forensic analysis", "public security"],
        shared_skills=["criminal investigation"],
        missing_skills=["victimology", "cybercrime", "forensic analysis"],
        weak_skills=[],
        obsolete_skills=[],
        demand_counts={"victimology": 4, "cybercrime": 3, "forensic analysis": 5},
        evidence_jobs=[{"title": "Técnico investigador criminalístico", "company": "Fiscalía General"}],
        coverage=0.2,
    )

    recommendations = generate_recommendations(domain="criminology", comparison=comparison, max_items=4)

    assert recommendations
    assert any("criminalistica" in item["asignatura_o_modulo_sugerido"].lower() or "forens" in item["asignatura_o_modulo_sugerido"].lower() for item in recommendations)
    assert any(item["subdomain"].startswith("criminology/") for item in recommendations)


def test_program_domain_classifier_prioritizes_criminology() -> None:
    classification = classify_program_domain(
        "Especialización en Criminología",
        "Investigación criminal, victimología, criminalística y cadena de custodia",
    )

    assert classification.primary_domain == "criminology"
    assert classification.confidence >= 0.9
