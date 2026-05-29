from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    classify_visual_analytics_skill,
    extract_visual_analytics_skills,
    normalize_text,
    normalize_visual_analytics_skill,
)


@dataclass(frozen=True)
class MatchScore:
    semantic_similarity: float
    skill_overlap: float
    role_alignment: float
    emerging_skill_weight: float
    final_match_score: float
    role_class: str
    confidence: float


ROLE_GROUPS = {
    "data_analyst": ("analista de datos", "data analyst", "reporting analyst"),
    "bi_analyst": ("analista bi", "bi analyst", "business intelligence analyst", "business intelligence"),
    "data_engineer": ("data engineer", "ingeniero de datos", "analytics engineer", "etl", "spark"),
    "visualization": ("visualization", "visualizacion", "tableau", "power bi", "dashboard"),
    "ai_analytics": ("machine learning", "mlops", "ai", "inteligencia artificial", "modelos predictivos"),
}

EMERGING_SKILLS = {"MLOps", "DataOps", "lakehouse", "Databricks", "Snowflake", "Azure Data", "AWS Analytics", "Google Cloud Analytics"}


def token_set_ratio(left: str, right: str) -> float:
    left_tokens = set(normalize_text(left).split())
    right_tokens = set(normalize_text(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    token_score = (2 * len(intersection)) / (len(left_tokens) + len(right_tokens))
    sequence_score = SequenceMatcher(None, " ".join(sorted(left_tokens)), " ".join(sorted(right_tokens))).ratio()
    return max(token_score, sequence_score) * 100


class VisualAnalyticsMatcher:
    """Hybrid matcher for the Visual Analytics and Big Data pilot.

    Uses deterministic fallbacks by default so tests and local runs do not require model downloads.
    If sentence-transformers are available in a future runtime, this class can be extended without
    changing its public scoring contract.
    """

    def semantic_similarity(self, left: str, right: str) -> float:
        left_norm = normalize_text(left)
        right_norm = normalize_text(right)
        if not left_norm or not right_norm:
            return 0.0
        try:
            matrix = TfidfVectorizer(ngram_range=(1, 2)).fit_transform([left_norm, right_norm])
            tfidf_score = float(cosine_similarity(matrix[0], matrix[1])[0][0])
        except ValueError:
            tfidf_score = 0.0
        fuzzy_score = token_set_ratio(left_norm, right_norm) / 100
        return round(max(tfidf_score, fuzzy_score * 0.85), 4)

    def classify_role(self, title: str, description: str) -> str:
        text = normalize_text(f"{title} {description}")
        best_role = "analytics_related"
        best_score = 0
        for role, terms in ROLE_GROUPS.items():
            score = sum(1 for term in terms if normalize_text(term) in text)
            if score > best_score:
                best_role = role
                best_score = score
        return best_role

    def skill_overlap(self, curriculum_skills: Iterable[str], job_skills: Iterable[str]) -> float:
        curriculum = {normalize_visual_analytics_skill(skill) for skill in curriculum_skills if skill}
        job = {normalize_visual_analytics_skill(skill) for skill in job_skills if skill}
        if not curriculum or not job:
            return 0.0
        direct = len(curriculum & job) / max(len(job), 1)
        fuzzy_hits = 0
        for job_skill in job:
            if any(token_set_ratio(normalize_text(job_skill), normalize_text(curriculum_skill)) >= 82 for curriculum_skill in curriculum):
                fuzzy_hits += 1
        fuzzy = fuzzy_hits / max(len(job), 1)
        return round(max(direct, fuzzy), 4)

    def emerging_weight(self, skills: Iterable[str]) -> float:
        normalized = {normalize_visual_analytics_skill(skill) for skill in skills}
        if not normalized:
            return 0.0
        hits = len(normalized & EMERGING_SKILLS)
        return round(min(hits / 3, 1.0), 4)

    def score_match(
        self,
        *,
        microcurriculum_text: str,
        job_title: str,
        job_description: str,
        job_skills: Iterable[str] | None = None,
    ) -> MatchScore:
        job_skill_list = list(job_skills or [])
        curriculum_skills = [skill.normalized for skill in extract_visual_analytics_skills(microcurriculum_text)]
        if not curriculum_skills:
            curriculum_skills = [normalize_visual_analytics_skill(microcurriculum_text)]
        if not job_skill_list:
            job_skill_list = [skill.normalized for skill in extract_visual_analytics_skills(f"{job_title} {job_description}")]

        semantic = self.semantic_similarity(microcurriculum_text, f"{job_title} {job_description} {' '.join(job_skill_list)}")
        overlap = self.skill_overlap(curriculum_skills, job_skill_list)
        role = self.classify_role(job_title, job_description)
        role_alignment = 0.88 if role != "analytics_related" else 0.62
        emerging = self.emerging_weight([*curriculum_skills, *job_skill_list])
        final = semantic * 0.15 + overlap * 0.50 + role_alignment * 0.25 + emerging * 0.10
        confidence = 1 / (1 + math.exp(-6 * (final - 0.5)))
        return MatchScore(
            semantic_similarity=round(semantic, 4),
            skill_overlap=round(overlap, 4),
            role_alignment=round(role_alignment, 4),
            emerging_skill_weight=round(emerging, 4),
            final_match_score=round(final, 4),
            role_class=role,
            confidence=round(confidence, 4),
        )


def evaluate_controlled_cases() -> dict[str, object]:
    matcher = VisualAnalyticsMatcher()
    cases = [
        {
            "name": "bi_power_bi",
            "expected": "high",
            "micro": "Power BI SQL visual analytics data governance storytelling with data",
            "title": "BI Analyst Power BI",
            "description": "Rol de analitica para dashboards, SQL, Power BI, gobierno de datos y visualizacion ejecutiva.",
            "skills": ["Power BI", "SQL", "data governance", "dashboarding"],
        },
        {
            "name": "data_engineering",
            "expected": "high",
            "micro": "ETL big data processing data warehouse lakehouse Spark",
            "title": "Data Engineer",
            "description": "Ingeniero de datos para ETL, Spark, lakehouse, data warehouse y pipelines analiticos.",
            "skills": ["ETL", "Spark", "lakehouse", "data warehouse"],
        },
        {
            "name": "irrelevant_accounting",
            "expected": "low",
            "micro": "Power BI SQL visual analytics data governance storytelling with data",
            "title": "Auxiliar contable",
            "description": "Registro contable, conciliaciones bancarias y facturacion.",
            "skills": ["contabilidad", "facturacion"],
        },
    ]
    scored = []
    passed = 0
    for case in cases:
        result = matcher.score_match(
            microcurriculum_text=case["micro"],
            job_title=case["title"],
            job_description=case["description"],
            job_skills=case["skills"],
        )
        ok = result.final_match_score >= 0.65 if case["expected"] == "high" else result.final_match_score < 0.45
        passed += int(ok)
        scored.append({**case, "score": result.__dict__, "passed": ok})
    summary = {
        "cases": len(cases),
        "passed": passed,
        "quality": round(passed / len(cases), 4),
        "results": scored,
    }
    output = ROOT_DIR / "outputs" / "visual_analytics_matcher_evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Visual Analytics semantic matcher.")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate controlled matching cases.")
    args = parser.parse_args()
    if args.evaluate:
        print(json.dumps(evaluate_controlled_cases(), indent=2, ensure_ascii=False))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
