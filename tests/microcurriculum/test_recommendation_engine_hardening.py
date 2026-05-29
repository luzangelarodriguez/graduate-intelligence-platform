from __future__ import annotations

from microcurriculum_engine.matching.market_matching import MarketComparison
from microcurriculum_engine.recommendations.recommendation_engine import generate_recommendations


def comparison_for(*, market: list[str], shared: list[str] | None = None, obsolete: list[str] | None = None) -> MarketComparison:
    shared = shared or []
    obsolete = obsolete or []
    missing = [skill for skill in market if skill not in shared]
    return MarketComparison(
        market_skills=market,
        shared_skills=shared,
        missing_skills=missing,
        weak_skills=[],
        obsolete_skills=obsolete,
        demand_counts={skill: 2 for skill in market},
        evidence_jobs=[],
        coverage=len(shared) / max(1, len(market)),
    )


def assert_enterprise_recommendation_shape(recommendations: list[dict]) -> None:
    assert recommendations
    generic_fragments = ("Incorporar Python", "Incorporar Docker", "Revisar tecnologias")
    for item in recommendations:
        assert item["gap_detectado"]
        assert item["accion_curricular"]
        assert item["justificacion"]
        assert item["explanation"]
        assert item["asignatura_o_modulo_sugerido"]
        assert item["confidence"] >= 0.7
        assert not any(fragment in item["recommendation_text"] for fragment in generic_fragments)


def test_ai_recommendations_are_specific_and_actionable() -> None:
    recommendations = generate_recommendations(
        domain="analitica",
        comparison=comparison_for(
            market=["python", "scikit-learn", "mlops", "notebooks", "visual analytics"],
            shared=["machine learning"],
            obsolete=["ia", "machine learning"],
        ),
    )

    assert_enterprise_recommendation_shape(recommendations)
    text = " ".join(item["recommendation_text"].casefold() for item in recommendations)
    assert "mlops" in text or "ciclo de vida" in text
    assert "evaluacion" in text or "validacion" in text


def test_innovation_recommendations_do_not_prioritize_ti_stack() -> None:
    recommendations = generate_recommendations(
        domain="management",
        comparison=comparison_for(
            market=["react", "docker", "kubernetes", "devops", "design thinking", "gestion de proyectos"],
            shared=["innovacion", "vigilancia tecnologica"],
            obsolete=["innovacion", "vigilancia tecnologica", "inteligencia competitiva"],
        ),
    )

    assert_enterprise_recommendation_shape(recommendations)
    text = " ".join([item["recommendation_text"].casefold() for item in recommendations])
    assert "react" not in text
    assert "docker" not in text
    assert "kubernetes" not in text
    assert any(item["subdomain"] == "management/innovacion" for item in recommendations)


def test_finance_recommendations_do_not_prioritize_ti_stack() -> None:
    recommendations = generate_recommendations(
        domain="finanzas",
        comparison=comparison_for(
            market=["react", "docker", "modelacion financiera", "analisis de escenarios", "power bi financiero"],
            shared=["excel avanzado"],
            obsolete=["excel avanzado"],
        ),
    )

    assert_enterprise_recommendation_shape(recommendations)
    text = " ".join([item["recommendation_text"].casefold() for item in recommendations])
    assert "react" not in text
    assert "docker" not in text
    assert "modelacion financiera" in text or "escenarios" in text or "dashboard" in text
    assert any(item["subdomain"] == "management/finanzas" for item in recommendations)
