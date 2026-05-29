from __future__ import annotations

from ml.inference.domain_classifier import confidence_level, predict_domain


def test_inference_classifies_environmental_vs_ti() -> None:
    environmental = predict_domain(
        title="Especialista en sostenibilidad ESG",
        description="Gestion ambiental ISO 14001 huella de carbono eficiencia energetica energias renovables",
        skills=["sostenibilidad", "esg", "iso 14001"],
    )
    ti = predict_domain(
        title="Backend developer",
        description="Desarrollo de APIs, backend, Python, DevOps y arquitectura cloud",
        skills=["backend", "python", "devops"],
    )
    assert environmental.domain in {"ambiental", "energia"}
    assert ti.domain == "ti"
    assert environmental.domain != ti.domain


def test_inference_classifies_analytics_vs_management() -> None:
    analytics = predict_domain(
        title="Analista BI Visual Analytics",
        description="SQL Power BI Python Big Data visual analytics business intelligence",
        skills=["sql", "power bi", "python", "big data"],
    )
    management = predict_domain(
        title="Director de alta gerencia",
        description="Estrategia liderazgo gestion de proyectos transformacion organizacional",
        skills=["liderazgo", "gestion de proyectos"],
    )
    assert analytics.domain == "analitica"
    assert management.domain == "management"


def test_low_confidence_inference_is_blocked() -> None:
    prediction = predict_domain(title="Rol generico", description="texto ambiguo sin evidencia suficiente", skills=[])
    assert prediction.confidence < 0.65
    assert prediction.blocked is True
    assert prediction.confidence_level == "low"


def test_confidence_level_thresholds() -> None:
    assert confidence_level(0.90) == "high"
    assert confidence_level(0.65) == "medium"
    assert confidence_level(0.40) == "low"
