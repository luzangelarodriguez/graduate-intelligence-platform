from __future__ import annotations

import argparse
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from scrapers.normalization.classify_domains import is_domain_compatible
    from scrapers.taxonomy.domain_taxonomy import SKILL_BY_CANONICAL, iter_alias_rows, normalize_text
except ModuleNotFoundError:
    from normalization.classify_domains import is_domain_compatible
    from taxonomy.domain_taxonomy import SKILL_BY_CANONICAL, iter_alias_rows, normalize_text


@dataclass(frozen=True)
class SkillMatch:
    skill_original: str
    skill_normalized: str
    skill_domain: str
    tipo_skill: str
    confianza_extraccion: float


@dataclass(frozen=True)
class RejectedSkill:
    skill_original: str
    skill_normalized: str
    skill_domain: str
    rejected_reason: str


ALIAS_TO_CANONICAL = {normalize_text(alias): canonical for alias, canonical in iter_alias_rows()}


def normalize_skill(value: str) -> str:
    key = normalize_text(value)
    return ALIAS_TO_CANONICAL.get(key, key)


def _contains_alias(text: str, alias: str) -> bool:
    if not alias:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def extract_skills(text: str, *, domain_hint: str | None = None) -> list[SkillMatch]:
    accepted, _ = extract_skills_with_rejections(text, domain_hint=domain_hint)
    return accepted


def extract_skills_with_rejections(
    text: str,
    *,
    domain_hint: str | None = None,
) -> tuple[list[SkillMatch], list[RejectedSkill]]:
    normalized_text = normalize_text(text)
    matches: dict[str, SkillMatch] = {}
    rejected: dict[str, RejectedSkill] = {}
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        if not _contains_alias(normalized_text, alias):
            continue
        definition = SKILL_BY_CANONICAL.get(canonical)
        if not definition:
            continue
        if domain_hint and not is_domain_compatible(domain_hint, definition.domain):
            rejected[canonical] = RejectedSkill(
                alias,
                canonical,
                definition.domain,
                f"incompatible_with_{domain_hint}",
            )
            continue
        confidence = 0.94 if alias == normalize_text(canonical) else 0.82
        current = matches.get(canonical)
        candidate = SkillMatch(alias, canonical, definition.domain, definition.tipo, confidence)
        if current is None or candidate.confianza_extraccion > current.confianza_extraccion:
            matches[canonical] = candidate
    return (
        sorted(matches.values(), key=lambda item: (item.skill_domain, item.skill_normalized)),
        sorted(rejected.values(), key=lambda item: (item.skill_domain, item.skill_normalized)),
    )


def split_tools_and_skills(matches: list[SkillMatch]) -> tuple[list[SkillMatch], list[SkillMatch]]:
    tools = [match for match in matches if match.tipo_skill == "herramienta"]
    skills = [match for match in matches if match.tipo_skill != "herramienta"]
    return tools, skills


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract canonical skills from text with domain guardrails.")
    parser.add_argument("text")
    parser.add_argument("--domain", default=None)
    args = parser.parse_args()
    print([asdict(match) for match in extract_skills(args.text, domain_hint=args.domain)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
