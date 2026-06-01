from __future__ import annotations

from intelligence.curriculum_analysis_engine import build_curriculum_analysis
from intelligence.domain_benchmark_layer import build_domain_benchmark
from intelligence.domain_prompt_layer import build_domain_system_prompt
from intelligence.domain_taxonomy_layer import build_domain_taxonomy_from_program


def test_domain_taxonomy_infers_expected_domains() -> None:
    cases = [
        ("Especialización en Visual Analytics y Big Data", "BI Analyst", "Data Analytics"),
        ("Maestría en Inteligencia Artificial", "AI Engineer", "AI"),
        ("Especialización en Criminología", "Forensic Analyst", "Criminology"),
        ("Especialización en Derecho Digital", "Legal Analyst", "Law"),
        ("Especialización en Psicología Organizacional", "Org Psychologist", "Psychology"),
    ]

    for program_name, role, expected in cases:
        result = build_domain_taxonomy_from_program(program_name=program_name, program_role=role, microcurriculum_context={})
        assert result.domain_label == expected
        assert result.confidence >= 0.35


def test_domain_benchmark_and_prompt_reflect_domain_focus() -> None:
    benchmark = build_domain_benchmark("law")
    taxonomy = build_domain_taxonomy_from_program(program_name="Derecho", program_role="Analyst", microcurriculum_context={})
    prompt = build_domain_system_prompt(task="program_summary", domain=taxonomy, benchmark=benchmark)

    assert "Law" in prompt
    assert "cumplimiento normativo" in prompt.lower() or "cumplimiento" in prompt.lower()
    assert benchmark.priority_skills
    assert benchmark.analysis_weights["coverage"] > 0


def test_curriculum_analysis_combines_domain_layers(monkeypatch) -> None:
    monkeypatch.setattr(
        "intelligence.curriculum_analysis_engine.programas_repository.fetch_program_base_row",
        lambda program_id, db_name=None: {
            "especializacion_id": program_id,
            "nombre_especializacion": "Especialización en Derecho Digital",
            "rol": "Legal Analyst",
        },
    )
    monkeypatch.setattr(
        "intelligence.curriculum_analysis_engine.microcurriculum_context_repository.fetch_program_context",
        lambda program_id, specialization_name=None, db_name=None: {
            "detected_domain": "law",
            "detected_subdomain": "legal_compliance",
            "technical_skills": ["Compliance", "Regulation"],
            "transversal_skills": ["Ethics"],
            "subjects": ["Derecho Digital"],
            "tools": [],
            "technologies": [],
            "keywords": ["legal"],
            "labor_roles": ["Legal Analyst"],
            "real_market_gaps": ["Data Protection"],
            "strengthening_areas": ["Legal Tech"],
        },
    )
    monkeypatch.setattr(
        "intelligence.curriculum_analysis_engine.build_program_intelligence_for_program",
        lambda program_id, db_name=None: type("Dummy", (), {"to_dict": lambda self: {"program_id": program_id, "risk_score": 65.0, "alignment_score": 35.0, "top_gaps": [{"missing_skill": "Data Protection"}], "top_recommendations": []}})(),
    )
    monkeypatch.setattr(
        "intelligence.curriculum_analysis_engine.build_curriculum_risk_index",
        lambda program_id, persist=False, db_name=None: type("Dummy", (), {"to_dict": lambda self: {"risk_score": 65.0, "risk_level": "observation", "risk_drivers": []}})(),
    )
    monkeypatch.setattr(
        "intelligence.curriculum_analysis_engine.build_university_market_alignment",
        lambda program_id, persist=False, db_name=None: type("Dummy", (), {"to_dict": lambda self: {"alignment_score": 35.0}})(),
    )
    monkeypatch.setattr(
        "intelligence.curriculum_analysis_engine.build_forecast_summary",
        lambda db_name=None, persist=False, limit=20: {"top_skills": [], "top_technologies": [], "top_companies": [], "top_roles": []},
    )

    result = build_curriculum_analysis(7)

    assert result["domain_taxonomy"]["domain_label"] == "Law"
    assert result["domain_benchmark"]["reference_program"]
    assert result["program_intelligence"]["program_id"] == 7
