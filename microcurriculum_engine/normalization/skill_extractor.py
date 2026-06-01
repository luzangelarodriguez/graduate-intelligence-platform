from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from ml.inference.domain_classifier import predict_domain, prediction_to_dict
from ml.ner import extract_curriculum_entities
from scrapers.normalization.normalize_skills import extract_skills_with_rejections, normalize_skill
from scrapers.taxonomy.domain_taxonomy import SKILL_BY_CANONICAL, normalize_text


GENERIC_PATTERNS = {
    "liderazgo": ("liderazgo", "leadership"),
    "pensamiento critico": ("pensamiento critico", "pensamiento crítico", "critical thinking"),
    "trabajo en equipo": ("trabajo en equipo", "teamwork"),
    "scrum": ("scrum",),
    "agile": ("agile", "agil", "ágil"),
    "moodle": ("moodle",),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure", "microsoft azure"),
    "docker": ("docker",),
    "react": ("react", "reactjs", "react.js"),
    "django": ("django",),
    "rest api": ("restful", "rest api", "api rest"),
    "javascript": ("javascript", "js"),
}

GENERIC_TYPES = {
    "liderazgo": "transversal_skill",
    "pensamiento critico": "transversal_skill",
    "trabajo en equipo": "transversal_skill",
    "scrum": "metodologia",
    "agile": "metodologia",
    "moodle": "plataforma",
    "aws": "plataforma",
    "azure": "plataforma",
    "docker": "herramienta",
    "react": "framework",
    "django": "framework",
    "rest api": "tecnica",
    "javascript": "herramienta",
}

CRIMINOLOGY_PATTERNS = {
    "criminal investigation": ("investigacion criminal", "criminal investigation", "investigacion criminalistica", "investigacion judicial"),
    "victimology": ("victimologia", "victimology", "victim assistance", "atencion a victimas"),
    "criminal profiling": ("perfilacion criminal", "perfilamiento criminal", "criminal profiling"),
    "criminal intelligence": ("inteligencia criminal", "criminal intelligence", "analisis de inteligencia criminal"),
    "criminal policy": ("politica criminal", "criminal policy"),
    "crime prevention": ("prevencion del delito", "crime prevention"),
    "public security": ("seguridad ciudadana", "seguridad publica", "public security", "public safety"),
    "cybercrime": ("ciberdelito", "delito informatico", "cybercrime", "computer crime"),
    "criminal analysis": ("analisis criminal", "analisis criminologico", "criminal analysis"),
    "forensic analysis": ("analisis forense", "criminalistica", "criminalistics", "forensic analysis", "forensic science", "forensics"),
    "chain of custody": ("cadena de custodia", "chain of custody", "custodia de evidencia"),
    "risk analysis": ("analisis de riesgo", "risk analysis", "risk assessment"),
    "penitentiary systems": ("sistemas penitenciarios", "penitentiary systems", "prison systems"),
    "organized crime": ("crimen organizado", "organized crime"),
    "financial crime": ("delito financiero", "financial crime", "fraude financiero", "money laundering"),
}

CRIMINOLOGY_TYPES = {
    "criminal investigation": "technical_skill",
    "victimology": "technical_skill",
    "criminal profiling": "technical_skill",
    "criminal intelligence": "technical_skill",
    "criminal policy": "technical_skill",
    "crime prevention": "technical_skill",
    "public security": "technical_skill",
    "cybercrime": "technical_skill",
    "criminal analysis": "technical_skill",
    "forensic analysis": "technical_skill",
    "chain of custody": "technical_skill",
    "risk analysis": "technical_skill",
    "penitentiary systems": "technical_skill",
    "organized crime": "technical_skill",
    "financial crime": "technical_skill",
}

ENTITY_TYPE_TO_SKILL_TYPE = {
    "technical_skill": "technical_skill",
    "transversal_skill": "transversal_skill",
    "methodology": "methodology",
    "platform": "platform",
    "framework": "framework",
    "cloud_provider": "cloud_provider",
    "programming_language": "programming_language",
    "database": "database",
    "tool": "tool",
}


def _contains(text: str, alias: str) -> bool:
    normalized_alias = normalize_text(alias)
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])", text) is not None


def extract_microcurriculum_skills(text: str, *, title: str = "") -> dict[str, Any]:
    prediction = predict_domain(title=title, description=text, skills=[])
    normalized_context = normalize_text(f"{title} {text[:2000]}")
    criminology_terms = (
        "criminologia",
        "criminalistica",
        "criminalistics",
        "investigacion criminal",
        "investigacion criminalistica",
        "forense",
        "forensic",
        "victimologia",
        "victimology",
        "inteligencia criminal",
        "criminal intelligence",
        "prevencion del delito",
        "crime prevention",
        "seguridad ciudadana",
        "public security",
        "ciberdelito",
        "cybercrime",
        "cadena de custodia",
        "chain of custody",
        "crimen organizado",
        "organized crime",
    )
    if any(term in normalized_context for term in criminology_terms):
        prediction = type(prediction)(
            domain="criminology",
            confidence=max(prediction.confidence, 0.91),
            confidence_level="high",
            blocked=False,
            model_name=f"microcurriculum_rule_{prediction.model_name}",
            scores={**prediction.scores, "criminology": max(prediction.scores.get("criminology", 0), 0.91)},
        )
    if any(term in normalized_context for term in ("ingenieria de software", "desarrollo de software", "arquitectura de software")):
        prediction = type(prediction)(
            domain="ti",
            confidence=max(prediction.confidence, 0.86),
            confidence_level="high",
            blocked=False,
            model_name=f"microcurriculum_rule_{prediction.model_name}",
            scores={**prediction.scores, "ti": max(prediction.scores.get("ti", 0), 0.86)},
        )
    if any(term in normalized_context for term in ("aprendizaje automatico", "inteligencia artificial", "machine learning")):
        prediction = type(prediction)(
            domain="analitica",
            confidence=max(prediction.confidence, 0.88),
            confidence_level="high",
            blocked=False,
            model_name=f"microcurriculum_rule_{prediction.model_name}",
            scores={**prediction.scores, "analitica": max(prediction.scores.get("analitica", 0), 0.88)},
        )
    if any(term in normalized_context for term in ("gerencia financiera", "finanzas corporativas", "valoracion de inversiones", "administracion financiera")):
        prediction = type(prediction)(
            domain="finanzas",
            confidence=max(prediction.confidence, 0.88),
            confidence_level="high",
            blocked=False,
            model_name=f"microcurriculum_rule_{prediction.model_name}",
            scores={**prediction.scores, "finanzas": max(prediction.scores.get("finanzas", 0), 0.88)},
        )
    if "innovacion" in normalized_context and any(term in normalized_context for term in ("proyecto", "proyectos", "i d i", "gestion de la innovacion")):
        prediction = type(prediction)(
            domain="management",
            confidence=max(prediction.confidence, 0.84),
            confidence_level="high",
            blocked=False,
            model_name=f"microcurriculum_rule_{prediction.model_name}",
            scores={**prediction.scores, "management": max(prediction.scores.get("management", 0), 0.84)},
        )
    domain = prediction.domain
    accepted, rejected = extract_skills_with_rejections(text, domain_hint=domain)
    skills: dict[str, dict[str, Any]] = {
        item.skill_normalized: {
            **asdict(item),
            "source": "taxonomy",
        }
        for item in accepted
    }
    normalized_text = normalize_text(text)
    for canonical, aliases in GENERIC_PATTERNS.items():
        normalized_canonical = normalize_skill(canonical)
        if normalized_canonical in skills:
            continue
        if any(_contains(normalized_text, alias) for alias in aliases):
            definition = SKILL_BY_CANONICAL.get(normalized_canonical)
            skills[normalized_canonical] = {
                "skill_original": canonical,
                "skill_normalized": normalized_canonical,
                "skill_domain": definition.domain if definition else domain,
                "tipo_skill": GENERIC_TYPES.get(canonical, "tecnica"),
                "confianza_extraccion": 0.74,
                "source": "microcurriculum_pattern",
            }
    for canonical, aliases in CRIMINOLOGY_PATTERNS.items():
        normalized_canonical = normalize_skill(canonical)
        if normalized_canonical in skills:
            continue
        if any(_contains(normalized_text, alias) for alias in aliases):
            skills[normalized_canonical] = {
                "skill_original": canonical,
                "skill_normalized": normalized_canonical,
                "skill_domain": "criminology",
                "tipo_skill": CRIMINOLOGY_TYPES.get(canonical, "technical_skill"),
                "confianza_extraccion": 0.86,
                "source": "microcurriculum_pattern",
            }
    for entity in extract_curriculum_entities(text):
        normalized_skill = normalize_skill(str(entity["normalized_skill"]))
        current = skills.get(normalized_skill)
        entity_confidence = float(entity["confidence"])
        if current is not None and current.get("confianza_extraccion", 0) >= entity_confidence:
            continue
        skills[normalized_skill] = {
            "skill_original": entity["entity"],
            "skill_normalized": normalized_skill,
            "skill_domain": entity["domain"],
            "tipo_skill": ENTITY_TYPE_TO_SKILL_TYPE.get(str(entity["entity_type"]), "technical_skill"),
            "confianza_extraccion": entity_confidence,
            "source": entity["source"],
            "text_fragment": entity["text_fragment"],
        }
    return {
        "domain_prediction": prediction_to_dict(prediction),
        "skills": sorted(skills.values(), key=lambda item: (item["tipo_skill"], item["skill_normalized"])),
        "rejected_skills": [asdict(item) for item in rejected],
    }
