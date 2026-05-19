from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

try:
    from scrapers.normalization.classify_domains import classify_program_domain, is_domain_compatible
    from scrapers.normalization.normalize_skills import extract_skills
    from scrapers.taxonomy.domain_taxonomy import normalize_text
except ModuleNotFoundError:
    from normalization.classify_domains import classify_program_domain, is_domain_compatible
    from normalization.normalize_skills import extract_skills
    from taxonomy.domain_taxonomy import normalize_text


SCORING_WEIGHTS = {
    "semantic_similarity": 0.35,
    "skills_overlap": 0.20,
    "tools_overlap": 0.15,
    "market_demand": 0.10,
    "university_benchmark": 0.10,
    "emerging_trends": 0.10,
}


@dataclass(frozen=True)
class MatchResult:
    program_domain: str
    job_domain: str
    score: float
    semantic_similarity: float
    skills_overlap: float
    tools_overlap: float
    market_demand: float
    university_benchmark: float
    emerging_trends: float
    shared_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def fallback_semantic_similarity(left_text: str, right_text: str) -> float:
    return SequenceMatcher(None, normalize_text(left_text), normalize_text(right_text)).ratio()


def overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def score_program_job_match(program: dict[str, Any], job: dict[str, Any]) -> MatchResult:
    program_text = " ".join(str(program.get(key, "")) for key in ("nombre", "descripcion", "plan_estudios", "competencias"))
    job_text = " ".join(str(job.get(key, "")) for key in ("titulo", "descripcion", "skills"))
    program_domain = program.get("dominio") or classify_program_domain(program_text).primary_domain
    job_domain = job.get("dominio") or classify_program_domain(job_text).primary_domain

    if not is_domain_compatible(program_domain, job_domain):
        return MatchResult(program_domain, job_domain, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, (), ())

    program_skills = {match.skill_normalized for match in extract_skills(program_text, domain_hint=program_domain)}
    job_skills = set(job.get("skills") or []) or {match.skill_normalized for match in extract_skills(job_text, domain_hint=program_domain)}
    program_tools = {match.skill_normalized for match in extract_skills(program_text, domain_hint=program_domain) if match.tipo_skill == "herramienta"}
    job_tools = {match.skill_normalized for match in extract_skills(job_text, domain_hint=program_domain) if match.tipo_skill == "herramienta"}

    semantic = cosine_similarity(program.get("embedding"), job.get("embedding"))
    if not semantic:
        semantic = fallback_semantic_similarity(program_text, job_text)

    skills = overlap_score(program_skills, job_skills)
    tools = overlap_score(program_tools, job_tools)
    market = min(1.0, float(job.get("market_demand", 0.5) or 0.5))
    benchmark = min(1.0, float(program.get("benchmark_score", 0.5) or 0.5))
    trends = min(1.0, float(job.get("trend_score", 0.5) or 0.5))

    score = (
        semantic * SCORING_WEIGHTS["semantic_similarity"]
        + skills * SCORING_WEIGHTS["skills_overlap"]
        + tools * SCORING_WEIGHTS["tools_overlap"]
        + market * SCORING_WEIGHTS["market_demand"]
        + benchmark * SCORING_WEIGHTS["university_benchmark"]
        + trends * SCORING_WEIGHTS["emerging_trends"]
    )
    shared = tuple(sorted(program_skills & job_skills))
    missing = tuple(sorted(job_skills - program_skills))
    return MatchResult(
        program_domain,
        job_domain,
        round(score * 100, 2),
        round(semantic, 4),
        round(skills, 4),
        round(tools, 4),
        round(market, 4),
        round(benchmark, 4),
        round(trends, 4),
        shared,
        missing,
    )

