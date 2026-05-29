from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.labor.labor_skill_taxonomy_expanded import extract_expanded_labor_skills, merge_expanded_skills
from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text

SECTION_WEIGHTS = {
    "requirements": 0.96,
    "responsibilities": 0.93,
    "description": 0.78,
    "title": 0.62,
    "tags": 0.35,
    "portal_taxonomy": 0.10,
}

SECTION_HINTS = {
    "requirements": ("requisitos", "requirements", "experiencia", "conocimientos", "debes tener"),
    "responsibilities": ("responsabilidades", "funciones", "responsable", "actividades", "que haras"),
}


@dataclass(frozen=True)
class SemanticSkillEvidence:
    skill: str
    skill_type: str
    confidence: float
    section: str
    evidence_source_type: str
    evidence_fragment: str


def infer_section(fragment: str) -> str:
    text = normalize_text(fragment)
    for section, hints in SECTION_HINTS.items():
        if any(normalize_text(hint) in text for hint in hints):
            return section
    return "description"


def extract_semantic_job_skills(
    *,
    title: str = "",
    description: str = "",
    responsibilities: list[str] | None = None,
    requirements: list[str] | None = None,
    tags: list[str] | None = None,
    evidence_source_type: str = "job_evidence",
) -> list[SemanticSkillEvidence]:
    fragments: list[tuple[str, str]] = []
    if title:
        fragments.append(("title", title))
    for item in responsibilities or []:
        fragments.append(("responsibilities", item))
    for item in requirements or []:
        fragments.append(("requirements", item))
    if description:
        fragments.append((infer_section(description), description))
    if tags:
        fragments.append(("tags", " ".join(tags)))

    if evidence_source_type == "portal_taxonomy":
        fragments = [("portal_taxonomy", " ".join([text for _section, text in fragments]))]

    expanded = []
    for section, fragment in fragments:
        expanded.extend(extract_expanded_labor_skills(fragment, section=section))

    return [
        SemanticSkillEvidence(
            skill=item.normalized,
            skill_type=item.entity_type,
            confidence=item.confidence,
            section=item.section,
            evidence_source_type=evidence_source_type,
            evidence_fragment="",
        )
        for item in merge_expanded_skills(expanded)
    ]


def semantic_skills_to_dict(items: list[SemanticSkillEvidence]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
