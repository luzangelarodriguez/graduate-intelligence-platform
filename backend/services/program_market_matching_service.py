from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MultiLabelBinarizer

from backend.queries import ensure_program_market_matching_objects
from backend.repositories.base import fetch_all, relation_exists
from backend.repositories.microcurriculum_context_repository import fetch_program_context
from backend.services.dashboard_service import list_programs_base
from backend.services.normalization_service import basic_text_key
from graduate_intelligence_platform.backend.app.engine import build_programs
from ml.curriculum.curriculum_market_gap_engine import build_curriculum_market_gap_map
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map


REPORT_PATH = Path("outputs/program_market_alignment_report.md")


@dataclass(frozen=True)
class SkillProfile:
    program_id: int
    program_name: str
    program_level: str
    faculty: str
    skills: list[str]
    skill_keys: list[str]
    labels_by_key: dict[str, str]
    source_breakdown: dict[str, int]


@dataclass(frozen=True)
class JobProfile:
    job_id: str
    job_title: str
    company: str
    location: str
    source: str
    job_url: str
    posted_at: str
    skills: list[str]
    skill_keys: list[str]
    labels_by_key: dict[str, str]


def _normalize_key(value: str) -> str:
    return basic_text_key(value)


def _unique_terms(terms: Iterable[str]) -> tuple[list[str], dict[str, str]]:
    ordered: list[str] = []
    labels: dict[str, str] = {}
    seen: set[str] = set()
    for term in terms:
        value = str(term or "").strip()
        if not value:
            continue
        key = _normalize_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(value)
        labels[key] = value
    return ordered, labels


def _program_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for item in build_programs():
        catalog[_normalize_key(str(item.get("name") or ""))] = dict(item)
    return catalog


def _program_base_rows(db_name: str | None = None) -> list[dict[str, Any]]:
    rows = list_programs_base(db_name=db_name)
    catalog = _program_catalog()
    enriched: list[dict[str, Any]] = []
    for row in rows:
        key = _normalize_key(str(row.get("nombre_especializacion") or ""))
        blueprint = catalog.get(key, {})
        merged = dict(row)
        if blueprint:
            merged.setdefault("nivel", blueprint.get("level") or blueprint.get("nivel") or "Especialización")
            merged.setdefault("facultad", blueprint.get("faculty") or blueprint.get("facultad") or "")
            merged.setdefault("rol", blueprint.get("role") or blueprint.get("rol") or "")
        merged.setdefault("nivel", "Especialización")
        merged.setdefault("facultad", "")
        merged.setdefault("rol", "")
        enriched.append(merged)
    return enriched


def _program_skill_rows(db_name: str | None = None) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            especializacion_id,
            especializacion,
            skill_id,
            skill,
            nombre,
            categoria,
            source_kind,
            source_table,
            skill_key
        FROM vw_programa_skills
        ORDER BY especializacion_id, skill_key, source_kind, skill_id
        """,
        db_name=db_name,
    )


def _job_skill_rows(db_name: str | None = None) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            e.id AS job_id,
            COALESCE(e.titulo, '') AS job_title,
            COALESCE(e.empresa, '') AS company,
            COALESCE(e.ubicacion, e.ciudad, '') AS location,
            COALESCE(e.fuente, e.portal, '') AS source,
            COALESCE(e.url, '') AS job_url,
            COALESCE(e.fecha_publicacion::text, '') AS posted_at,
            s.nombre AS skill
        FROM empleos e
        LEFT JOIN empleo_skills es
            ON es.empleo_id = e.id
        LEFT JOIN skills s
            ON s.id = es.skill_id
        ORDER BY e.id, s.nombre
        """,
        db_name=db_name,
    )


def _collect_program_profiles(db_name: str | None = None) -> list[SkillProfile]:
    base_rows = _program_base_rows(db_name=db_name)
    rows_by_program: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in _program_skill_rows(db_name=db_name):
        rows_by_program[int(row.get("especializacion_id") or 0)].append(row)

    profiles: list[SkillProfile] = []
    for program in base_rows:
        program_id = int(program.get("especializacion_id") or 0)
        labels: list[str] = []
        source_breakdown: Counter[str] = Counter()

        for row in rows_by_program.get(program_id, []):
            value = str(row.get("nombre") or row.get("skill") or "").strip()
            if not value:
                continue
            labels.append(value)
            source_breakdown[str(row.get("source_kind") or "skill")] += 1

        context = None
        try:
            context = fetch_program_context(
                program_id,
                specialization_name=str(program.get("nombre_especializacion") or ""),
                db_name=db_name,
            )
        except Exception:
            context = None

        if context:
            for key in ("technical_skills", "transversal_skills", "methodologies", "tools", "platforms", "technologies", "keywords", "occupational_profiles", "labor_roles", "benchmarking", "real_market_gaps", "strengthening_areas"):
                values = context.get(key) or []
                if isinstance(values, (list, tuple, set)):
                    for item in values:
                        if isinstance(item, dict):
                            candidate = str(item.get("name") or item.get("skill") or item.get("title") or item.get("value") or "").strip()
                        else:
                            candidate = str(item or "").strip()
                        if candidate:
                            labels.append(candidate)
                            source_breakdown[f"microcurriculum:{key}"] += 1

        if program.get("rol"):
            labels.append(str(program.get("rol")))
            source_breakdown["program_role"] += 1

        ordered, labels_by_key = _unique_terms(labels)
        profiles.append(
            SkillProfile(
                program_id=program_id,
                program_name=str(program.get("nombre_especializacion") or ""),
                program_level=str(program.get("nivel") or "Especialización"),
                faculty=str(program.get("facultad") or ""),
                skills=ordered,
                skill_keys=[_normalize_key(item) for item in ordered if _normalize_key(item)],
                labels_by_key=labels_by_key,
                source_breakdown=dict(source_breakdown),
            )
        )
    return profiles


def _collect_job_profiles(db_name: str | None = None) -> list[JobProfile]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _job_skill_rows(db_name=db_name):
        grouped[str(row.get("job_id") or "")].append(row)

    profiles: list[JobProfile] = []
    for job_id, rows in grouped.items():
        first = rows[0]
        labels: list[str] = []
        for row in rows:
            value = str(row.get("skill") or "").strip()
            if value:
                labels.append(value)
        ordered, labels_by_key = _unique_terms(labels)
        profiles.append(
            JobProfile(
                job_id=job_id,
                job_title=str(first.get("job_title") or ""),
                company=str(first.get("company") or ""),
                location=str(first.get("location") or ""),
                source=str(first.get("source") or ""),
                job_url=str(first.get("job_url") or ""),
                posted_at=str(first.get("posted_at") or ""),
                skills=ordered,
                skill_keys=[_normalize_key(item) for item in ordered if _normalize_key(item)],
                labels_by_key=labels_by_key,
            )
        )

    # Preserve jobs without skills in the profile set.
    skills_job_ids = {profile.job_id for profile in profiles}
    if relation_exists("public.empleos", db_name=db_name):
        extra_jobs = fetch_all(
            """
            SELECT
                e.id AS job_id,
                COALESCE(e.titulo, '') AS job_title,
                COALESCE(e.empresa, '') AS company,
                COALESCE(e.ubicacion, e.ciudad, '') AS location,
                COALESCE(e.fuente, e.portal, '') AS source,
                COALESCE(e.url, '') AS job_url,
                COALESCE(e.fecha_publicacion::text, '') AS posted_at
            FROM empleos e
            ORDER BY e.id
            """,
            db_name=db_name,
        )
        for row in extra_jobs:
            job_id = str(row.get("job_id") or "")
            if job_id in skills_job_ids:
                continue
            profiles.append(
                JobProfile(
                    job_id=job_id,
                    job_title=str(row.get("job_title") or ""),
                    company=str(row.get("company") or ""),
                    location=str(row.get("location") or ""),
                    source=str(row.get("source") or ""),
                    job_url=str(row.get("job_url") or ""),
                    posted_at=str(row.get("posted_at") or ""),
                    skills=[],
                    skill_keys=[],
                    labels_by_key={},
                )
            )

    return sorted(profiles, key=lambda item: item.job_id)


def _pair_scores(left_keys: Sequence[str], right_keys: Sequence[str]) -> dict[str, float | int]:
    left = {key for key in left_keys if key}
    right = {key for key in right_keys if key}
    common = left & right
    common_count = len(common)
    left_count = len(left)
    right_count = len(right)
    union_count = len(left | right)
    coverage = (common_count / left_count) if left_count else 0.0
    gap = 1.0 - coverage if left_count else 1.0
    jaccard = (common_count / union_count) if union_count else 0.0
    cosine = (common_count / math.sqrt(left_count * right_count)) if left_count and right_count else 0.0
    match_score = (jaccard + cosine) / 2.0
    return {
        "matched_skills": common_count,
        "coverage_score": round(coverage * 100, 2),
        "gap_score": round(gap * 100, 2),
        "jaccard_score": round(jaccard * 100, 2),
        "cosine_score": round(cosine * 100, 2),
        "match_score": round(match_score * 100, 2),
    }


def _fit_knn(profiles: list[SkillProfile | JobProfile]) -> tuple[NearestNeighbors | None, MultiLabelBinarizer | None, list[int]]:
    non_empty_indices = [index for index, profile in enumerate(profiles) if getattr(profile, "skill_keys", [])]
    if not non_empty_indices:
        return None, None, []
    vocab = sorted({key for profile in profiles for key in getattr(profile, "skill_keys", []) if key})
    mlb = MultiLabelBinarizer(classes=vocab)
    feature_rows = mlb.fit_transform([getattr(profile, "skill_keys", []) for profile in profiles])
    active_rows = feature_rows[non_empty_indices]
    model = NearestNeighbors(metric="cosine")
    model.fit(active_rows)
    return model, mlb, non_empty_indices


def _knn_neighbors(
    source_profiles: list[SkillProfile],
    target_profiles: list[JobProfile] | list[SkillProfile],
    *,
    k: int,
) -> dict[int, list[dict[str, Any]]]:
    neighbors: dict[int, list[dict[str, Any]]] = {}
    if not source_profiles or not target_profiles:
        return neighbors

    vocab = sorted({key for profile in [*source_profiles, *target_profiles] for key in getattr(profile, "skill_keys", []) if key})
    if not vocab:
        return neighbors

    mlb = MultiLabelBinarizer(classes=vocab)
    source_matrix = mlb.fit_transform([profile.skill_keys for profile in source_profiles])
    target_matrix = mlb.transform([profile.skill_keys for profile in target_profiles])
    target_non_empty = [index for index, profile in enumerate(target_profiles) if getattr(profile, "skill_keys", [])]
    if not target_non_empty:
        return neighbors

    model = NearestNeighbors(metric="cosine")
    model.fit(target_matrix[target_non_empty])
    query_k = min(max(k, 1), len(target_non_empty))
    distances, indices = model.kneighbors(source_matrix, n_neighbors=query_k)

    for source_index, (dist_row, idx_row) in enumerate(zip(distances, indices)):
        items: list[dict[str, Any]] = []
        for distance, target_index in zip(dist_row, idx_row):
            real_index = target_non_empty[target_index]
            target = target_profiles[real_index]
            items.append(
                {
                    "id": getattr(target, "job_id", getattr(target, "program_id", "")),
                    "title": getattr(target, "job_title", getattr(target, "program_name", "")),
                    "similarity_score": round((1.0 - float(distance)) * 100, 2),
                    "coverage_score": _pair_scores(getattr(source_profiles[source_index], "skill_keys", []), getattr(target, "skill_keys", []))["coverage_score"],
                    "gap_score": _pair_scores(getattr(source_profiles[source_index], "skill_keys", []), getattr(target, "skill_keys", []))["gap_score"],
                }
            )
        neighbors[source_index] = items
    return neighbors


def _program_market_rows(
    program: SkillProfile,
    jobs: list[JobProfile],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in jobs:
        scores = _pair_scores(program.skill_keys, job.skill_keys)
        if scores["matched_skills"] <= 0:
            continue
        common_keys = sorted(set(program.skill_keys) & set(job.skill_keys))
        rows.append(
            {
                "program_id": program.program_id,
                "program_name": program.program_name,
                "program_level": program.program_level,
                "faculty": program.faculty,
                "job_id": job.job_id,
                "job_title": job.job_title,
                "company": job.company,
                "location": job.location,
                "source": job.source,
                "job_url": job.job_url,
                "posted_at": job.posted_at,
                **scores,
                "matched_skills": [program.labels_by_key.get(key) or job.labels_by_key.get(key) or key for key in common_keys],
                "missing_skills": [
                    program.labels_by_key.get(key) or key
                    for key in sorted(set(program.skill_keys) - set(job.skill_keys))
                ],
            }
        )
    rows.sort(key=lambda item: (item["match_score"], item["coverage_score"], item["matched_skills"]), reverse=True)
    return rows


def _program_summary(
    program: SkillProfile,
    jobs: list[JobProfile],
    *,
    knn_jobs: dict[int, list[dict[str, Any]]],
    knn_programs: dict[int, list[dict[str, Any]]],
    k_values: Sequence[int],
) -> dict[str, Any]:
    scored_jobs = _program_market_rows(program, jobs)
    matched_jobs = len(scored_jobs)
    avg_match = round(sum(item["match_score"] for item in scored_jobs) / matched_jobs, 2) if matched_jobs else 0.0
    avg_coverage = round(sum(item["coverage_score"] for item in scored_jobs) / matched_jobs, 2) if matched_jobs else 0.0
    avg_gap = round(sum(item["gap_score"] for item in scored_jobs) / matched_jobs, 2) if matched_jobs else 100.0
    demand_counter: Counter[str] = Counter()
    for item in scored_jobs:
        for skill in item["matched_skills"]:
            demand_counter[skill] += 1
    missing_skills = sorted(
        (
            {
                "skill": program.labels_by_key.get(key) or key,
                "gap_frequency": count,
            }
            for key, count in demand_counter.items()
            if key not in set(program.skill_keys)
        ),
        key=lambda item: (-item["gap_frequency"], item["skill"]),
    )
    taught_not_demanded = sorted(
        (
            {
                "skill": program.labels_by_key.get(key) or key,
                "gap_frequency": demand_counter.get(key, 0),
            }
            for key in program.skill_keys
            if demand_counter.get(key, 0) == 0
        ),
        key=lambda item: item["skill"],
    )
    recommended_jobs = [item for item in scored_jobs[:20]]
    nearest_jobs = {}
    for k in k_values:
        nearest_jobs[str(k)] = knn_jobs.get(program.program_id, [])[: min(k, len(knn_jobs.get(program.program_id, [])))]
    nearest_programs = {}
    for k in k_values:
        raw_neighbors = knn_programs.get(program.program_id, [])
        nearest_programs[str(k)] = raw_neighbors[: min(k, len(raw_neighbors))]

    return {
        "program_id": program.program_id,
        "program_name": program.program_name,
        "program_level": program.program_level,
        "faculty": program.faculty,
        "program_skill_count": len(program.skill_keys),
        "market_alignment_score": avg_match,
        "coverage_score": avg_coverage,
        "gap_score": avg_gap,
        "matched_jobs": matched_jobs,
        "missing_skills": missing_skills[:25],
        "taught_not_demanded": taught_not_demanded[:25],
        "recommended_jobs": recommended_jobs[:20],
        "nearest_jobs": nearest_jobs,
        "nearest_programs": nearest_programs,
        "source_breakdown": program.source_breakdown,
    }


def build_program_market_alignment_report(
    *,
    program_id: int | None = None,
    k_values: Sequence[int] = (5, 10, 20),
    db_name: str | None = None,
    write_output: bool = True,
) -> dict[str, Any]:
    ensure_program_market_matching_objects()

    programs = _collect_program_profiles(db_name=db_name)
    jobs = _collect_job_profiles(db_name=db_name)
    market_intelligence = build_market_skill_intelligence_map(include_database=True, write_output=False)
    curriculum_gaps = build_curriculum_market_gap_map(write_output=False)

    program_model = [profile for profile in programs if profile.skill_keys]
    job_model = [profile for profile in jobs if profile.skill_keys]
    knn_jobs: dict[int, list[dict[str, Any]]] = {}
    knn_programs: dict[int, list[dict[str, Any]]] = {}

    if program_model and job_model:
        vocab = sorted({key for profile in [*program_model, *job_model] for key in profile.skill_keys})
        mlb = MultiLabelBinarizer(classes=vocab)
        program_matrix = mlb.fit_transform([profile.skill_keys for profile in program_model])
        job_matrix = mlb.transform([profile.skill_keys for profile in job_model])

        job_nn = NearestNeighbors(metric="cosine")
        job_nn.fit(job_matrix)
        k_jobs = min(max(k_values), len(job_model))
        distances, indices = job_nn.kneighbors(program_matrix, n_neighbors=k_jobs)
        for program_index, (dist_row, idx_row) in enumerate(zip(distances, indices)):
            items: list[dict[str, Any]] = []
            source_profile = program_model[program_index]
            for distance, target_index in zip(dist_row, idx_row):
                target_profile = job_model[target_index]
                scores = _pair_scores(source_profile.skill_keys, target_profile.skill_keys)
                items.append(
                    {
                        "job_id": target_profile.job_id,
                        "job_title": target_profile.job_title,
                        "company": target_profile.company,
                        "location": target_profile.location,
                        "source": target_profile.source,
                        "job_url": target_profile.job_url,
                        "similarity_score": round((1.0 - float(distance)) * 100, 2),
                        "coverage_score": scores["coverage_score"],
                        "gap_score": scores["gap_score"],
                        "match_score": scores["match_score"],
                    }
                )
            knn_jobs[source_profile.program_id] = items

        program_nn = NearestNeighbors(metric="cosine")
        program_nn.fit(program_matrix)
        k_programs = min(max(k_values) + 1, len(program_model))
        distances, indices = program_nn.kneighbors(program_matrix, n_neighbors=k_programs)
        for program_index, (dist_row, idx_row) in enumerate(zip(distances, indices)):
            items: list[dict[str, Any]] = []
            source_profile = program_model[program_index]
            for distance, target_index in zip(dist_row, idx_row):
                if target_index == program_index:
                    continue
                target_profile = program_model[target_index]
                scores = _pair_scores(source_profile.skill_keys, target_profile.skill_keys)
                items.append(
                    {
                        "program_id": target_profile.program_id,
                        "program_name": target_profile.program_name,
                        "program_level": target_profile.program_level,
                        "faculty": target_profile.faculty,
                        "similarity_score": round((1.0 - float(distance)) * 100, 2),
                        "coverage_score": scores["coverage_score"],
                        "gap_score": scores["gap_score"],
                        "match_score": scores["match_score"],
                    }
                )
            knn_programs[source_profile.program_id] = items

    program_summaries: list[dict[str, Any]] = []
    for index, program in enumerate(programs):
        summary = _program_summary(
            program,
            jobs,
            knn_jobs=knn_jobs,
            knn_programs=knn_programs,
            k_values=k_values,
        )
        program_summaries.append(summary)

    if program_id is not None:
        program_summaries = [item for item in program_summaries if int(item["program_id"]) == int(program_id)]

    all_programs_sorted = sorted(
        program_summaries,
        key=lambda item: (item["market_alignment_score"], item["coverage_score"], item["matched_jobs"]),
        reverse=True,
    )
    specializations_sorted = [item for item in all_programs_sorted if str(item.get("program_level") or "").lower().startswith("especial")]
    if not specializations_sorted:
        specializations_sorted = all_programs_sorted

    overall_program_alignment = round(
        sum(item["market_alignment_score"] for item in program_summaries) / len(program_summaries), 2
    ) if program_summaries else 0.0
    overall_specialization_alignment = round(
        sum(item["market_alignment_score"] for item in specializations_sorted) / len(specializations_sorted), 2
    ) if specializations_sorted else 0.0

    gap_counter = Counter()
    for item in program_summaries:
        for skill in item["missing_skills"]:
            gap_counter[skill["skill"]] += int(skill["gap_frequency"])

    market_emerging = [item.skill for item in market_intelligence.emerging_skills[:15]]
    market_missing = [item.skill for item in market_intelligence.missing_skills[:15]]
    market_top = [item.skill for item in market_intelligence.market_skills[:20]]
    curriculum_emerging = [item.skill for item in curriculum_gaps.emerging_skills[:15]]
    top_missing_skills = [
        {"skill": skill, "gap_frequency": count}
        for skill, count in gap_counter.most_common(20)
    ]
    if not top_missing_skills:
        top_missing_skills = [
            {"skill": skill, "gap_frequency": index + 1}
            for index, skill in enumerate(market_missing[:20])
        ]
    top_emerging_skills = market_emerging or curriculum_emerging or market_missing[:10]

    report = {
        "methodology": {
            "vector_space": "multi-hot skills built from specializations, competencies, tools, soft skills, microcurriculum signals and labor skills",
            "similarity_metrics": ["jaccard", "cosine"],
            "knn_library": "scikit-learn NearestNeighbors",
            "k_values": list(k_values),
        },
        "summary": {
            "program_count": len(program_summaries),
            "job_count": len(jobs),
            "average_program_alignment": overall_program_alignment,
            "average_specialization_alignment": overall_specialization_alignment,
            "matched_jobs_total": int(sum(item["matched_jobs"] for item in program_summaries)),
            "top_missing_skills": top_missing_skills,
            "top_emerging_skills": top_emerging_skills[:10] if isinstance(top_emerging_skills, list) else top_emerging_skills,
            "top_market_skills": market_top[:20],
            "top_market_missing_skills": market_missing[:10],
            "curriculum_emerging_skills": curriculum_emerging[:10],
        },
        "programs": all_programs_sorted,
        "specializations": specializations_sorted,
        "knn": {
            "program_to_job": knn_jobs,
            "program_to_program": knn_programs,
        },
    }

    if write_output:
        write_program_market_alignment_report(report)
    return report


def write_program_market_alignment_report(report: dict[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.extend(
        [
            "# Program Market Alignment Report",
            "",
            "## Methodology",
            "- Matching explicable basado en skills.",
            "- Vectores multi-hot por programa y por empleo.",
            "- Similitud calculada con Jaccard y Cosine.",
            "- Vecinos cercanos calculados con `scikit-learn NearestNeighbors`.",
            "",
            "## Formulas",
            "- Coverage = shared_skills / program_skills.",
            "- Gap = 1 - coverage.",
            "- Jaccard = shared_skills / union_skills.",
            "- Cosine = shared_skills / sqrt(program_skills * job_skills).",
            "- Match score = average(Jaccard, Cosine).",
            "",
            "## Summary",
            f"- Programs analyzed: {report['summary']['program_count']}",
            f"- Jobs analyzed: {report['summary']['job_count']}",
            f"- Average program alignment: {report['summary']['average_program_alignment']}",
            f"- Average specialization alignment: {report['summary']['average_specialization_alignment']}",
            f"- Matched jobs total: {report['summary']['matched_jobs_total']}",
            "",
            "## Top Programs",
            "",
        ]
    )
    for item in report["programs"][:10]:
        lines.extend(
            [
                f"### {item['program_name']}",
                f"- Level: {item['program_level']}",
                f"- Faculty: {item['faculty'] or 'n/a'}",
                f"- Market alignment score: {item['market_alignment_score']}",
                f"- Coverage score: {item['coverage_score']}",
                f"- Gap score: {item['gap_score']}",
                f"- Matched jobs: {item['matched_jobs']}",
                f"- Missing skills: {', '.join(skill['skill'] for skill in item['missing_skills'][:8]) or 'none'}",
                f"- Top jobs: {', '.join(job['job_title'] for job in item['recommended_jobs'][:5]) or 'none'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Top Specializations",
            "",
        ]
    )
    for item in report["specializations"][:10]:
        lines.extend(
            [
                f"### {item['program_name']}",
                f"- Market alignment score: {item['market_alignment_score']}",
                f"- Coverage score: {item['coverage_score']}",
                f"- Gap score: {item['gap_score']}",
                f"- Matched jobs: {item['matched_jobs']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Top Missing Skills",
            "",
        ]
    )
    for item in report["summary"]["top_missing_skills"][:20]:
        lines.append(f"- {item['skill']} ({item['gap_frequency']})")

    lines.extend(
        [
            "",
            "## Top Emerging Skills",
            "",
        ]
    )
    for skill in report["summary"]["top_emerging_skills"][:20]:
        lines.append(f"- {skill}")

    lines.extend(
        [
            "",
            "## KNN Results",
            "",
        ]
    )
    for item in report["programs"][:5]:
        lines.extend(
            [
                f"### {item['program_name']}",
                f"- K=5 jobs: {', '.join(job['job_title'] for job in item['nearest_jobs'].get('5', [])[:5]) or 'none'}",
                f"- K=10 jobs: {', '.join(job['job_title'] for job in item['nearest_jobs'].get('10', [])[:10]) or 'none'}",
                f"- K=20 jobs: {', '.join(job['job_title'] for job in item['nearest_jobs'].get('20', [])[:20]) or 'none'}",
                f"- K=5 programs: {', '.join(peer['program_name'] for peer in item['nearest_programs'].get('5', [])[:5]) or 'none'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Risks",
            "- If the skill taxonomy remains shallow, coverage can be inflated by a narrow canonical set.",
            "- Jobs without skills remain low-signal and may understate market alignment.",
            "- KNN is only as good as the current vocabulary; no supervised labels are used yet.",
            "",
            "## Limitations",
            "- Current DB materializes programs mostly at specialization grain.",
            "- Faculty metadata is not fully materialized in the operational schema.",
            "- Microcurriculum context is used opportunistically when available.",
            "",
            "## Next Steps",
            "- Promote the alignment views to Power BI and Deneb dashboards.",
            "- Re-run the report after extending canonical skills and aliases.",
            "- Add longitudinal trend views for market skill growth once historical snapshots are available.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
