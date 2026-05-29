from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from microcurriculum_engine.ingestion.document_loader import extract_text
from scrapers.normalization.visual_analytics_skill_taxonomy import extract_visual_analytics_skills, normalize_text

VISUAL_ANALYTICS_ROOT = ROOT_DIR / "storage" / "test_microcurriculos" / "especialización en visual analytics y big data"
GRAPH_JSON = ROOT_DIR / "outputs" / "specialization_curriculum_graph_visual_analytics.json"

PROFILE_TERMS = {
    "perfil de egreso",
    "competencias",
    "resultados de aprendizaje",
    "business intelligence",
    "visual analytics",
    "big data",
    "analitica",
    "visualizacion",
    "bases de datos",
    "inteligencia artificial",
    "toma de decisiones",
}


@dataclass(frozen=True)
class CurriculumSkillNode:
    skill: str
    frequency: int
    source_documents: list[str]
    evidence_fragments: list[str]
    node_type: str
    curricular_weight: float


@dataclass(frozen=True)
class SpecializationCurriculumGraph:
    specialization_id: str
    specialization_name: str
    source_root: str
    documents_processed: int
    skills: list[CurriculumSkillNode]
    profile_concepts: dict[str, int]
    raw_concept_frequency: dict[str, int]


def _documents(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in {".pdf", ".docx", ".txt"})


def _fragments(text: str, skill: str) -> list[str]:
    normalized_skill = normalize_text(skill)
    values = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if len(line) < 24:
            continue
        if normalized_skill in normalize_text(line):
            values.append(line[:260])
    return values[:3]


def build_specialization_curriculum_graph(
    specialization_id: str = "visual-analytics-big-data",
    specialization_name: str = "Especialización en Visual Analytics y Big Data",
    root: Path = VISUAL_ANALYTICS_ROOT,
    *,
    write_output: bool = True,
) -> SpecializationCurriculumGraph:
    skill_counts: Counter[str] = Counter()
    source_docs: dict[str, set[str]] = {}
    fragments: dict[str, list[str]] = {}
    concept_counts: Counter[str] = Counter()

    docs = _documents(root)
    for path in docs:
        raw_text, _method = extract_text(path)
        text = raw_text or ""
        normalized_text = normalize_text(text)
        for term in PROFILE_TERMS:
            count = normalized_text.count(normalize_text(term))
            if count:
                concept_counts[term] += count
        for skill in extract_visual_analytics_skills(text):
            skill_counts[skill.normalized] += 1
            source_docs.setdefault(skill.normalized, set()).add(path.name)
            fragments.setdefault(skill.normalized, []).extend(_fragments(text, skill.original or skill.normalized))

    doc_count = max(len(docs), 1)
    nodes = [
        CurriculumSkillNode(
            skill=skill,
            frequency=count,
            source_documents=sorted(source_docs.get(skill, set())),
            evidence_fragments=fragments.get(skill, [])[:5],
            node_type="skill",
            curricular_weight=round(min(0.35 + (count / doc_count) * 0.55, 1.0), 4),
        )
        for skill, count in sorted(skill_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    graph = SpecializationCurriculumGraph(
        specialization_id=specialization_id,
        specialization_name=specialization_name,
        source_root=str(root),
        documents_processed=len(docs),
        skills=nodes,
        profile_concepts=dict(concept_counts.most_common(30)),
        raw_concept_frequency=dict(concept_counts),
    )
    if write_output:
        GRAPH_JSON.parent.mkdir(parents=True, exist_ok=True)
        GRAPH_JSON.write_text(json.dumps(asdict(graph), indent=2, ensure_ascii=False), encoding="utf-8")
    return graph


def graph_to_dict(graph: SpecializationCurriculumGraph) -> dict[str, Any]:
    return asdict(graph)

