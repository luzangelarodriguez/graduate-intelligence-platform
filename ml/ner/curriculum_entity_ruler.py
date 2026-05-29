from __future__ import annotations

import importlib.util
import re
from dataclasses import asdict, dataclass
from typing import Iterable

from ml.ner.semantic_matcher import infer_semantic_entities
from scrapers.taxonomy.domain_taxonomy import normalize_text


@dataclass(frozen=True)
class CurriculumEntity:
    text_fragment: str
    entity: str
    entity_type: str
    normalized_skill: str
    domain: str
    confidence: float
    source: str = "curriculum_entity_ruler"

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


ENTITY_PATTERNS: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("java", "programming_language", "java", "ti", ("java", "java se", "java ee")),
    ("spring boot", "framework", "spring boot", "ti", ("spring boot", "springboot", "spring framework")),
    (".net", "framework", ".net", "ti", (".net", "dotnet", "asp.net", "visual studio .net")),
    ("c#", "programming_language", "c#", "ti", ("c#", "c sharp", "csharp")),
    ("php", "programming_language", "php", "ti", ("php",)),
    ("android", "technical_skill", "android", "ti", ("android", "desarrollo android", "desarrollo movil")),
    ("kotlin", "programming_language", "kotlin", "ti", ("kotlin",)),
    ("swift", "programming_language", "swift", "ti", ("swift",)),
    ("javascript", "programming_language", "javascript", "ti", ("javascript", "js", "ecmascript")),
    ("react", "framework", "react", "ti", ("react", "reactjs", "react.js")),
    ("angular", "framework", "angular", "ti", ("angular", "angularjs")),
    ("vue", "framework", "vue", "ti", ("vue", "vue.js", "vuejs")),
    ("node.js", "framework", "node.js", "ti", ("node.js", "nodejs", "node js")),
    ("express", "framework", "express", "ti", ("express", "express.js", "expressjs")),
    ("django", "framework", "django", "ti", ("django",)),
    ("flask", "framework", "flask", "ti", ("flask",)),
    ("backend", "technical_skill", "backend", "ti", ("backend", "back end", "server side")),
    ("frontend", "technical_skill", "frontend", "ti", ("frontend", "front end", "interfaces web")),
    ("api", "technical_skill", "api", "ti", ("api", "apis", "rest api", "api rest", "restful", "servicios web")),
    ("postgresql", "database", "postgresql", "ti", ("postgresql", "postgres", "postgres sql")),
    ("mysql", "database", "mysql", "ti", ("mysql", "my sql")),
    ("mariadb", "database", "mariadb", "ti", ("mariadb", "maria db")),
    ("mongodb", "database", "mongodb", "ti", ("mongodb", "mongo db", "mongo")),
    ("firebase", "database", "firebase", "ti", ("firebase", "google firebase")),
    ("docker", "tool", "docker", "ti", ("docker", "contenedores docker")),
    ("kubernetes", "tool", "kubernetes", "ti", ("kubernetes", "k8s")),
    ("jenkins", "tool", "jenkins", "ti", ("jenkins",)),
    ("github actions", "tool", "github actions", "ti", ("github actions", "github action", "gh actions")),
    ("terraform", "tool", "terraform", "ti", ("terraform",)),
    ("aws", "cloud_provider", "aws", "ti", ("aws", "amazon web services")),
    ("azure", "cloud_provider", "azure", "ti", ("azure", "microsoft azure")),
    ("google cloud", "cloud_provider", "google cloud", "ti", ("google cloud", "google cloud platform", "gcp")),
    ("cloud", "technical_skill", "cloud", "ti", ("cloud", "cloud computing", "computacion en la nube", "nube")),
    ("kafka", "tool", "kafka", "ti", ("kafka", "apache kafka")),
    ("redis", "database", "redis", "ti", ("redis",)),
    ("rabbitmq", "tool", "rabbitmq", "ti", ("rabbitmq", "rabbit mq")),
    ("eclipse", "tool", "eclipse", "ti", ("eclipse", "eclipse ide")),
    ("netbeans", "tool", "netbeans", "ti", ("netbeans", "netbeans ide")),
    ("android studio", "tool", "android studio", "ti", ("android studio",)),
    ("power bi", "tool", "power bi", "analitica", ("power bi", "powerbi", "microsoft power bi", "pbi")),
    ("tableau", "tool", "tableau", "analitica", ("tableau",)),
    ("etl", "technical_skill", "etl", "analitica", ("etl", "extract transform load", "procesos etl")),
    ("machine learning", "technical_skill", "machine learning", "analitica", ("machine learning", "aprendizaje automatico", "aprendizaje automático", "aprendizaje supervisado", "aprendizaje no supervisado", "random forest", "naive bayes", "redes neuronales")),
    ("ia", "technical_skill", "ia", "analitica", ("inteligencia artificial", "ia", "artificial intelligence")),
    ("scikit-learn", "tool", "scikit-learn", "analitica", ("scikit-learn", "scikit learn", "sklearn")),
    ("notebooks", "tool", "notebooks", "analitica", ("jupyter", "jupyter notebook", "notebooks", "cuadernos")),
    ("mlops", "methodology", "mlops", "analitica", ("mlops", "machine learning operations")),
    ("ci cd", "methodology", "ci cd", "ti", ("ci/cd", "ci cd", "cicd", "integracion continua", "despliegue continuo")),
    ("scrum", "methodology", "scrum", "management", ("scrum",)),
    ("agile", "methodology", "agile", "management", ("agile", "agil", "metodologias agiles")),
    ("moodle", "platform", "moodle", "educacion", ("moodle",)),
    ("excel avanzado", "tool", "excel avanzado", "finanzas", ("microsoft excel", "excel", "analisis financiero con microsoft excel")),
    ("modelacion financiera", "technical_skill", "modelacion financiera", "finanzas", ("modelacion financiera", "valoracion de inversiones", "valoración de inversiones", "van", "tir", "wacc", "capm")),
    ("analisis de escenarios", "technical_skill", "analisis de escenarios", "finanzas", ("analisis de sensibilidad", "análisis de sensibilidad", "escenarios financieros")),
    ("indicadores financieros", "technical_skill", "indicadores financieros", "finanzas", ("indicadores financieros", "flujos de caja", "rentabilidad", "riesgo financiero")),
    ("innovacion", "technical_skill", "innovacion", "management", ("innovacion", "innovación", "i+d+i", "gestion de la innovacion", "gestión de la innovación")),
    ("design thinking", "methodology", "design thinking", "management", ("design thinking", "pensamiento de diseño")),
    ("vigilancia tecnologica", "technical_skill", "vigilancia tecnologica", "management", ("vigilancia tecnologica", "vigilancia tecnológica", "prospectiva tecnologica", "prospectiva tecnológica")),
    ("inteligencia competitiva", "technical_skill", "inteligencia competitiva", "management", ("inteligencia competitiva", "competitive intelligence")),
    ("liderazgo", "transversal_skill", "liderazgo", "transversal", ("liderazgo", "leadership")),
    ("pensamiento critico", "transversal_skill", "pensamiento critico", "transversal", ("pensamiento critico", "pensamiento crítico", "critical thinking")),
    ("trabajo en equipo", "transversal_skill", "trabajo en equipo", "transversal", ("trabajo en equipo", "teamwork", "colaboracion")),
)

CONTEXTUAL_PATTERNS: tuple[tuple[str, str, str, str, str, tuple[str, ...], float], ...] = (
    (
        "desarrollo de aplicaciones moviles",
        "android",
        "technical_skill",
        "android",
        "ti",
        ("desarrollo de aplicaciones moviles", "aplicaciones moviles", "programacion movil", "desarrollo movil"),
        0.78,
    ),
    (
        "arquitectura de software",
        "backend",
        "technical_skill",
        "backend",
        "ti",
        ("arquitectura de software", "capas de software", "logica de negocio", "servidor"),
        0.76,
    ),
    (
        "servicios e integracion",
        "api",
        "technical_skill",
        "api",
        "ti",
        ("peticiones y respuestas", "protocolos de aplicacion", "integracion de sistemas", "apis"),
        0.74,
    ),
    (
        "computacion en la nube",
        "cloud",
        "technical_skill",
        "cloud",
        "ti",
        ("plataformas de desarrollo en la nube", "servicios en la nube", "infraestructura en la nube", "computacion en la nube"),
        0.78,
    ),
    (
        "entornos de desarrollo integrados",
        "ide",
        "tool",
        "ide",
        "ti",
        ("entornos de desarrollo integrados", "ambientes de desarrollo", "ide"),
        0.7,
    ),
    (
        "integracion y despliegue continuo",
        "ci cd",
        "methodology",
        "ci cd",
        "ti",
        ("integracion continua", "despliegue continuo", "automatizacion de despliegues"),
        0.77,
    ),
)


def spacy_available() -> bool:
    return importlib.util.find_spec("spacy") is not None


def _contains_alias(normalized_text: str, alias: str) -> bool:
    normalized_alias = normalize_text(alias)
    if not normalized_alias:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])", normalized_text) is not None


def _window(original_text: str, alias: str, *, width: int = 110) -> str:
    normalized_original = normalize_text(original_text)
    normalized_alias = normalize_text(alias)
    index = normalized_original.find(normalized_alias)
    if index < 0:
        return alias
    return normalized_original[max(0, index - width // 2) : index + len(normalized_alias) + width // 2].strip()


def _regex_entities(text: str) -> list[CurriculumEntity]:
    normalized = normalize_text(text)
    entities: dict[str, CurriculumEntity] = {}
    for entity, entity_type, normalized_skill, domain, aliases in ENTITY_PATTERNS:
        for alias in aliases:
            if not _contains_alias(normalized, alias):
                continue
            confidence = 0.95 if normalize_text(alias) == normalize_text(entity) else 0.86
            key = f"{normalized_skill}:{entity_type}"
            candidate = CurriculumEntity(
                text_fragment=_window(text, alias),
                entity=entity,
                entity_type=entity_type,
                normalized_skill=normalized_skill,
                domain=domain,
                confidence=confidence,
            )
            current = entities.get(key)
            if current is None or candidate.confidence > current.confidence:
                entities[key] = candidate
    return list(entities.values())


def _contextual_entities(text: str, existing: Iterable[CurriculumEntity]) -> list[CurriculumEntity]:
    normalized = normalize_text(text)
    existing_keys = {item.normalized_skill for item in existing}
    inferred: list[CurriculumEntity] = []
    for fragment, entity, entity_type, normalized_skill, domain, aliases, confidence in CONTEXTUAL_PATTERNS:
        if normalized_skill in existing_keys:
            continue
        if any(_contains_alias(normalized, alias) for alias in aliases):
            inferred.append(
                CurriculumEntity(
                    text_fragment=fragment,
                    entity=entity,
                    entity_type=entity_type,
                    normalized_skill=normalized_skill,
                    domain=domain,
                    confidence=confidence,
                    source="contextual_inference",
                )
            )
    return inferred


def _spacy_entities(text: str) -> list[CurriculumEntity]:
    if not spacy_available():
        return []
    try:
        import spacy
        from spacy.pipeline import EntityRuler
    except Exception:
        return []

    nlp = spacy.blank("es")
    ruler = nlp.add_pipe("entity_ruler") if "entity_ruler" not in nlp.pipe_names else nlp.get_pipe("entity_ruler")
    if isinstance(ruler, EntityRuler):
        ruler.add_patterns(
            [
                {
                    "label": entity_type.upper(),
                    "pattern": [{"LOWER": token} for token in normalize_text(alias).split()],
                    "id": f"{normalized_skill}|{domain}",
                }
                for _, entity_type, normalized_skill, domain, aliases in ENTITY_PATTERNS
                for alias in aliases
                if normalize_text(alias)
            ]
        )
    doc = nlp(text[:200000])
    entities: list[CurriculumEntity] = []
    for ent in doc.ents:
        if "|" not in ent.ent_id_:
            continue
        normalized_skill, domain = ent.ent_id_.split("|", 1)
        entities.append(
            CurriculumEntity(
                text_fragment=ent.text,
                entity=ent.text,
                entity_type=ent.label_.lower(),
                normalized_skill=normalized_skill,
                domain=domain,
                confidence=0.84,
                source="spacy_entity_ruler",
            )
        )
    return entities


def extract_curriculum_entities(text: str) -> list[dict[str, str | float]]:
    regex = _regex_entities(text)
    contextual = _contextual_entities(text, regex)
    existing = {item.normalized_skill for item in [*regex, *contextual]}
    semantic = [
        CurriculumEntity(
            text_fragment=item.text_fragment,
            entity=item.entity,
            entity_type=item.entity_type,
            normalized_skill=item.normalized_skill,
            domain=item.domain,
            confidence=item.confidence,
            source="semantic_embedding_matcher",
        )
        for item in infer_semantic_entities(text, existing_skills=existing)
    ]
    spacy_entities = _spacy_entities(text)
    by_key: dict[str, CurriculumEntity] = {}
    for item in [*regex, *contextual, *semantic, *spacy_entities]:
        key = f"{item.normalized_skill}:{item.entity_type}"
        current = by_key.get(key)
        if current is None or item.confidence > current.confidence:
            by_key[key] = item
    return [
        item.to_dict()
        for item in sorted(by_key.values(), key=lambda value: (value.domain, value.entity_type, value.normalized_skill))
    ]
