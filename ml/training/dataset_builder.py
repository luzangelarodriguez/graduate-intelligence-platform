from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

from scrapers.taxonomy.domain_taxonomy import DOMAIN_DEFINITIONS, SKILL_DEFINITIONS


@dataclass(frozen=True)
class DomainTrainingExample:
    text: str
    domain: str
    source: str
    label_quality: str = "taxonomy_seed"


DOMAIN_TEMPLATES = (
    "{name}: {description}. Competencias: {terms}.",
    "Vacante para especialista en {terms}. Responsabilidades: {description}.",
    "Programa academico de {name} orientado a {terms}.",
)


def taxonomy_examples() -> list[DomainTrainingExample]:
    examples: list[DomainTrainingExample] = []
    skills_by_domain: dict[str, list[str]] = {}
    for skill in SKILL_DEFINITIONS:
        skills_by_domain.setdefault(skill.domain, []).append(skill.canonical_name)
    for domain in DOMAIN_DEFINITIONS:
        terms = ", ".join((*domain.terms[:8], *skills_by_domain.get(domain.code, [])[:8]))
        for template in DOMAIN_TEMPLATES:
            examples.append(
                DomainTrainingExample(
                    text=template.format(name=domain.name, description=domain.description, terms=terms),
                    domain=domain.code,
                    source="taxonomy_domains",
                )
            )
        for skill in skills_by_domain.get(domain.code, []):
            examples.append(
                DomainTrainingExample(
                    text=f"{domain.name} requiere {skill}. {domain.description}",
                    domain=domain.code,
                    source="skills_master",
                )
            )
    return examples


def build_initial_dataset(output_path: Path | None = None) -> list[dict[str, str]]:
    rows = [asdict(example) for example in taxonomy_examples()]
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() == ".json":
            output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            with output_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=["text", "domain", "source", "label_quality"])
                writer.writeheader()
                writer.writerows(rows)
    return rows


def load_dataset(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return build_initial_dataset(path)
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
