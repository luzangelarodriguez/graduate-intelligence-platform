from __future__ import annotations

from microcurriculum_engine.normalization.skill_extractor import extract_microcurriculum_skills
from ml.ner import extract_curriculum_entities


def test_curriculum_ner_detects_modern_ti_entities_and_transversal_skills() -> None:
    entities = extract_curriculum_entities(
        "Desarrollo de aplicaciones moviles con Java, Android Studio, APIs REST y Google Cloud. "
        "Trabajo en equipo y liderazgo."
    )
    by_skill = {str(item["normalized_skill"]): item for item in entities}

    assert by_skill["java"]["entity_type"] == "programming_language"
    assert by_skill["android studio"]["entity_type"] == "tool"
    assert by_skill["google cloud"]["entity_type"] == "cloud_provider"
    assert by_skill["api"]["entity_type"] == "technical_skill"
    assert by_skill["liderazgo"]["domain"] == "transversal"
    assert by_skill["trabajo en equipo"]["domain"] == "transversal"


def test_microcurriculum_extractor_infers_mobile_and_keeps_transversal_out_of_ti() -> None:
    extracted = extract_microcurriculum_skills(
        "Competencias: desarrollo de aplicaciones moviles, arquitectura de software, "
        "servicios en la nube, pensamiento critico y liderazgo.",
        title="Ingenieria de Software",
    )
    by_skill = {item["skill_normalized"]: item for item in extracted["skills"]}

    assert by_skill["android"]["source"] == "contextual_inference"
    assert by_skill["backend"]["skill_domain"] == "ti"
    assert by_skill["cloud"]["skill_domain"] == "ti"
    assert by_skill["liderazgo"]["skill_domain"] == "transversal"
    assert by_skill["pensamiento critico"]["tipo_skill"] == "transversal_skill"
