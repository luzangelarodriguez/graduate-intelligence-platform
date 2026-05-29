from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from ml.embeddings.embedding_service import DEFAULT_EMBEDDING_MODEL, encode_texts
from scrapers.taxonomy.domain_taxonomy import normalize_text


@dataclass(frozen=True)
class SemanticEntityCandidate:
    text_fragment: str
    entity: str
    entity_type: str
    normalized_skill: str
    domain: str
    confidence: float


SEMANTIC_REFERENCES: tuple[tuple[str, str, str, str, str], ...] = (
    ("desarrollo de aplicaciones moviles nativas android", "android", "technical_skill", "android", "ti"),
    ("arquitectura backend servicios servidor logica de negocio software", "backend", "technical_skill", "backend", "ti"),
    ("interfaces web experiencia usuario frontend aplicaciones cliente", "frontend", "technical_skill", "frontend", "ti"),
    ("servicios rest integracion api peticiones respuestas endpoints", "api", "technical_skill", "api", "ti"),
    ("computacion en la nube servicios cloud infraestructura escalable", "cloud", "technical_skill", "cloud", "ti"),
    ("integracion continua despliegue continuo automatizacion devops ci cd", "ci cd", "methodology", "ci cd", "ti"),
    ("visualizacion inteligencia de negocios tableros analitica power bi", "power bi", "tool", "power bi", "analitica"),
    ("procesos etl integracion transformacion carga datos", "etl", "technical_skill", "etl", "analitica"),
)

ANCHORS: dict[str, tuple[str, ...]] = {
    "android": ("movil", "moviles", "android", "aplicaciones"),
    "backend": ("software", "arquitectura", "servidor", "servicios"),
    "frontend": ("interfaz", "interfaces", "web", "cliente"),
    "api": ("api", "apis", "servicios", "peticiones", "respuestas", "integracion"),
    "cloud": ("nube", "cloud", "infraestructura", "servicios"),
    "ci cd": ("continua", "despliegue", "integracion", "automatizacion"),
    "power bi": ("tableros", "visualizacion", "bi", "power"),
    "etl": ("etl", "datos", "transformacion", "carga"),
}


def _chunks(text: str, *, max_words: int = 72) -> list[str]:
    normalized = normalize_text(text)
    sentences = [chunk.strip() for chunk in re.split(r"[\n.;:]+", normalized) if chunk.strip()]
    expanded: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= max_words:
            expanded.append(sentence)
            continue
        for index in range(0, len(words), max_words):
            expanded.append(" ".join(words[index : index + max_words]))
    return expanded[:80]


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    if math.isclose(denom, 0):
        return 0.0
    return float(np.dot(left, right) / denom)


def _has_anchor(fragment: str, skill: str) -> bool:
    anchors = ANCHORS.get(skill, ())
    return any(anchor in fragment for anchor in anchors)


def infer_semantic_entities(
    text: str,
    *,
    existing_skills: Iterable[str] = (),
    threshold: float = 0.56,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[SemanticEntityCandidate]:
    chunks = _chunks(text)
    if not chunks:
        return []
    existing = set(existing_skills)
    references = [item[0] for item in SEMANTIC_REFERENCES]
    try:
        vectors = np.asarray(encode_texts([*chunks, *references], model_name=model_name), dtype=float)
    except Exception:
        return []
    chunk_vectors = vectors[: len(chunks)]
    reference_vectors = vectors[len(chunks) :]
    candidates: dict[str, SemanticEntityCandidate] = {}
    for chunk_index, chunk_vector in enumerate(chunk_vectors):
        fragment = chunks[chunk_index]
        for ref_index, ref_vector in enumerate(reference_vectors):
            _, entity, entity_type, normalized_skill, domain = SEMANTIC_REFERENCES[ref_index]
            if normalized_skill in existing or not _has_anchor(fragment, normalized_skill):
                continue
            similarity = _cosine(chunk_vector, ref_vector)
            if similarity < threshold:
                continue
            confidence = round(min(0.88, 0.62 + (similarity - threshold) * 0.65), 4)
            current = candidates.get(normalized_skill)
            candidate = SemanticEntityCandidate(fragment, entity, entity_type, normalized_skill, domain, confidence)
            if current is None or candidate.confidence > current.confidence:
                candidates[normalized_skill] = candidate
    return sorted(candidates.values(), key=lambda item: (item.domain, item.entity_type, item.normalized_skill))
