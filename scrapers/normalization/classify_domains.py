from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from scrapers.taxonomy.domain_taxonomy import DOMAIN_BY_CODE, DOMAIN_DEFINITIONS, normalize_text
except ModuleNotFoundError:
    from taxonomy.domain_taxonomy import DOMAIN_BY_CODE, DOMAIN_DEFINITIONS, normalize_text


@dataclass(frozen=True)
class DomainClassification:
    primary_domain: str
    secondary_domains: tuple[str, ...]
    confidence: float
    evidence: tuple[str, ...]


def _term_score(text: str, term: str) -> float:
    normalized_term = normalize_text(term)
    if not normalized_term:
        return 0.0
    if normalized_term in text:
        return 2.5 if " " in normalized_term else 1.0
    tokens = normalized_term.split()
    if len(tokens) > 1 and all(token in text for token in tokens):
        return 1.4
    return 0.0


def classify_text_domain(text: str, *, default: str = "management") -> DomainClassification:
    normalized = normalize_text(text)
    if not normalized:
        return DomainClassification(default, (), 0.0, ())

    scored: list[tuple[str, float, list[str]]] = []
    for domain in DOMAIN_DEFINITIONS:
        hits: list[str] = []
        score = 0.0
        for term in domain.terms:
            value = _term_score(normalized, term)
            if value:
                hits.append(term)
                score += value
        if score:
            scored.append((domain.code, score, hits))

    if not scored:
        return DomainClassification(default, (), 0.25, ())

    scored.sort(key=lambda item: (-item[1], item[0]))
    primary, primary_score, evidence = scored[0]
    secondary = tuple(code for code, score, _ in scored[1:4] if score >= max(1.5, primary_score * 0.35))
    total = sum(score for _, score, _ in scored)
    confidence = round(min(0.98, max(0.35, primary_score / total if total else 0.35)), 3)
    return DomainClassification(primary, secondary, confidence, tuple(evidence[:6]))


def classify_program_domain(name: str, description: str = "") -> DomainClassification:
    joined = f"{name} {description}".strip()
    classification = classify_text_domain(joined)
    normalized = normalize_text(joined)

    # Strong business rule: environmental + energy programs must not fall through to TI
    # just because the labor text contains generic digital or analytics terms.
    if "ambiental" in normalized and ("energetic" in normalized or "energia" in normalized):
        evidence = tuple(dict.fromkeys(("gestion ambiental", "energia", *classification.evidence)))
        return DomainClassification("ambiental", ("energia",), max(classification.confidence, 0.9), evidence[:6])

    if "derecho digital" in normalized or "derecho informatico" in normalized:
        return DomainClassification("legal-tech", ("legal",), max(classification.confidence, 0.9), ("derecho digital",))

    return classification


def is_domain_compatible(source_domain: str | None, target_domain: str | None) -> bool:
    if not source_domain or not target_domain:
        return True
    if "transversal" in {source_domain, target_domain}:
        return True
    if source_domain == target_domain:
        return True
    source = DOMAIN_BY_CODE.get(source_domain)
    target = DOMAIN_BY_CODE.get(target_domain)
    if source and target_domain in source.excluded_domains:
        return False
    if target and source_domain in target.excluded_domains:
        return False
    compatible_groups = (
        {"ambiental", "energia"},
        {"legal", "legal-tech"},
        {"analitica", "ti"},
        {"management", "gestion_humana", "logistica", "finanzas", "marketing"},
    )
    return any({source_domain, target_domain}.issubset(group) for group in compatible_groups)


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify an academic or labor text into a disciplinary domain.")
    parser.add_argument("text")
    args = parser.parse_args()
    result = classify_program_domain(args.text)
    print(
        {
            "primary_domain": result.primary_domain,
            "secondary_domains": list(result.secondary_domains),
            "confidence": result.confidence,
            "evidence": list(result.evidence),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
