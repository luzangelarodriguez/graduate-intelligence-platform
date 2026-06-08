from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Sequence

from .engine import (
    DOMAIN_JOB_TERMS,
    DOMAIN_SKILL_PRIORITY,
    SKILL_CATALOG,
    as_skill_names,
    canonical_skill,
    clean_human_text,
    now_iso,
    normalize_text,
    program_domain,
    program_skill_profile,
    program_topic_profile,
    repair_text,
    skill_category,
    unique,
)

SEARCH_MODES = {"focused", "academic_alignment", "market_discovery"}

CRAWLER_TARGETS = (
    "linkedin",
    "elempleo",
    "ticjob",
    "indeed",
    "jooble",
    "hireline",
    "findjobit",
    "criminology",
    "computrabajo",
    "magneto",
    "torre",
    "spe",
)

_COLOMBIAN_PORTALS = frozenset({
    "elempleo", "ticjob", "hireline", "findjobit", "criminology",
    "computrabajo", "magneto", "torre", "spe",
})

ROLE_SIGNATURES: list[tuple[set[str], list[str]]] = [
    (
        {"power bi", "tableau", "dax", "sql", "etl", "dashboard", "business intelligence"},
        ["Data Analyst", "Business Intelligence Analyst", "Power BI Developer", "Analytics Consultant"],
    ),
    (
        {"python", "machine learning", "deep learning", "mlops", "prompt engineering", "ai"},
        ["Data Scientist", "Machine Learning Engineer", "AI Engineer", "MLOps Engineer"],
    ),
    (
        {"cybersecurity", "privacy", "security", "cloud", "testing"},
        ["Cybersecurity Analyst", "Security Engineer", "Privacy Officer", "SOC Analyst"],
    ),
    (
        {"compliance", "risk management", "aml/cft", "regulatory compliance", "corporate governance"},
        ["Compliance Analyst", "Risk Analyst", "AML Analyst", "Internal Control Analyst"],
    ),
    (
        {"curriculum design", "instructional design", "lms", "learning analytics", "education"},
        ["Instructional Designer", "Curriculum Designer", "Learning Analytics Specialist", "Academic Coordinator"],
    ),
    (
        {"health management", "public health", "occupational health", "risk management"},
        ["Health Manager", "Quality Analyst", "Risk Coordinator", "Patient Safety Specialist"],
    ),
    (
        {"legal analysis", "contract drafting", "corporate governance", "due diligence", "litigation"},
        ["Legal Analyst", "Contracts Analyst", "Corporate Governance Specialist", "Legal Risk Analyst"],
    ),
    (
        {"criminal investigation", "victimology", "forensic analysis", "cybercrime", "criminal intelligence", "chain of custody", "organized crime", "financial crime", "public safety"},
        ["Criminal Intelligence Analyst", "Investigative Analyst", "Forensic Analyst", "Fraud Investigator"],
    ),
]

DOMAIN_ROLE_TEMPLATES: dict[str, list[str]] = {
    "technology": [
        "Software Engineer",
        "Data Engineer",
        "BI Developer",
        "Cloud Engineer",
        "QA Engineer",
        "Solutions Architect",
        "Platform Engineer",
    ],
    "business": [
        "Business Analyst",
        "Financial Analyst",
        "Operations Analyst",
        "Commercial Analyst",
        "Marketing Analyst",
        "Project Manager",
        "PMO Analyst",
        "CRM Analyst",
        "Process Analyst",
    ],
    "law": [
        "Legal Analyst",
        "Compliance Officer",
        "Privacy Officer",
        "Corporate Governance Analyst",
        "Contract Analyst",
        "Risk Analyst",
    ],
    "education": [
        "Instructional Designer",
        "Curriculum Designer",
        "Learning Analyst",
        "Academic Coordinator",
        "Educational Technology Specialist",
    ],
    "health": [
        "Health Administrator",
        "Quality Analyst",
        "Risk Manager",
        "Patient Safety Analyst",
        "Healthcare Operations Coordinator",
    ],
}

DOMAIN_FAMILY_TEMPLATES: dict[str, list[str]] = {
    "technology": ["Data and Analytics", "Software Engineering", "Cloud and Platform", "AI and ML"],
    "business": ["Business Operations", "Finance and Control", "Commercial Growth", "Marketing and CRM"],
    "law": ["Legal and Compliance", "Regulatory Risk", "Corporate Governance"],
    "education": ["Learning Design", "Academic Management", "Educational Technology"],
    "health": ["Health Operations", "Quality and Safety", "Risk and Compliance"],
}


def _string_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for key in ("skill", "name", "title", "role", "label", "value", "term", "keyword", "tool", "cluster", "family", "category"):
            item = value.get(key)
            if isinstance(item, (str, int, float)) and item is not None:
                items.append(str(item))
        for nested_key in ("skills", "tools", "technical_skills", "transversal_skills", "platforms", "labor_roles", "benchmarking", "real_market_gaps", "strengthening_areas", "market_skills", "missing_market_skills", "top_skills", "emerging_skills", "clusters", "families"):
            nested = value.get(nested_key)
            if isinstance(nested, (list, tuple, set, dict, str)):
                items.extend(_string_items(nested))
        return items
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(_string_items(item))
        return items
    return [str(value)]


def _extract_terms(values: Any, *, canonicalize: bool = True) -> list[str]:
    terms: list[str] = []
    for raw in _string_items(values):
        cleaned = clean_human_text(raw).strip()
        if not cleaned:
            continue
        if canonicalize:
            cleaned = canonical_skill(cleaned) or cleaned
        marker = normalize_text(cleaned)
        if marker and marker not in {normalize_text(item) for item in terms}:
            terms.append(cleaned)
    return unique(terms)


def _extract_tools(values: Any) -> list[str]:
    terms = _extract_terms(values)
    tools: list[str] = []
    for term in terms:
        category = skill_category(term)
        normalized = normalize_text(term)
        if category == "tools" or normalized in {
            "sql",
            "power bi",
            "tableau",
            "etl",
            "dax",
            "dashboarding",
            "lms",
            "moodle",
            "canvas",
            "azure",
            "aws",
            "google cloud",
            "databricks",
            "snowflake",
            "crm",
            "git",
        }:
            tools.append(term)
    return unique(tools)


def _program_name(program: dict[str, Any]) -> str:
    return str(
        program.get("nombre_especializacion")
        or program.get("name")
        or program.get("nombre")
        or program.get("program_name")
        or ""
    ).strip()


def _program_faculty(program: dict[str, Any]) -> str:
    return str(program.get("facultad") or program.get("faculty") or program.get("area") or "").strip()


def _program_id(program: dict[str, Any]) -> str:
    return str(program.get("especializacion_id") or program.get("id") or program.get("program_id") or "").strip()


def _market_skill_terms(market_skill_intelligence: Any) -> list[str]:
    return _extract_terms(market_skill_intelligence, canonicalize=True)


def _gap_terms(curriculum_gap_map: Any) -> list[str]:
    return _extract_terms(curriculum_gap_map, canonicalize=True)


def _cluster_terms(clusters: Any) -> list[str]:
    terms = _extract_terms(clusters, canonicalize=False)
    return [clean_human_text(item).strip() for item in unique(terms) if item]


def _role_signatures(term_pool: Sequence[str]) -> list[str]:
    pool = {normalize_text(term) for term in term_pool if term}
    roles: list[str] = []
    for signature, candidates in ROLE_SIGNATURES:
        if pool & signature:
            roles.extend(candidates)
    return unique(roles)


def _domain_roles(domain: str) -> list[str]:
    return DOMAIN_ROLE_TEMPLATES.get(domain, [])


def _domain_families(domain: str) -> list[str]:
    return DOMAIN_FAMILY_TEMPLATES.get(domain, [])


def _build_query(terms: Sequence[str], limit: int = 12) -> str:
    selected = [term for term in unique([clean_human_text(item).strip() for item in terms]) if term][:limit]
    if not selected:
        return ""
    pieces = [f'"{term}"' if " " in term else term for term in selected]
    return " OR ".join(pieces)


def _source_payload(
    source: str,
    *,
    keywords: list[str],
    roles: list[str],
    families: list[str],
    mode: str,
    keyword_limit: int,
    role_limit: int,
    max_jobs: int,
    max_pages: int,
) -> dict[str, Any]:
    query = _build_query([*keywords[:keyword_limit], *roles[:role_limit], *families])
    payload = {
        "source": source,
        "mode": mode,
        "keywords": keywords[:keyword_limit],
        "roles": roles[:role_limit],
        "families": families,
        "query": query,
        "max_jobs": max_jobs,
        "max_pages": max_pages,
    }
    if source in {"linkedin", "indeed", "jooble"}:
        payload["query"] = query
    elif source in _COLOMBIAN_PORTALS:
        payload["search_terms"] = keywords[:keyword_limit]
        # Spanish-first query for Colombian portals: build from existing keywords (already in Spanish)
        payload["query_es"] = _build_query(keywords[:8])
    return payload


def build_program_search_profile(
    program: dict[str, Any],
    *,
    mode: str = "academic_alignment",
    market_skill_intelligence: Any = None,
    curriculum_gap_map: Any = None,
    occupational_clusters: Any = None,
    manual_keywords: Sequence[str] | None = None,
    keyword_limit: int = 24,
    role_limit: int = 12,
) -> dict[str, Any]:
    normalized_mode = mode if mode in SEARCH_MODES else "academic_alignment"
    domain = program_domain(
        {
            "name": _program_name(program),
            "faculty": _program_faculty(program),
        }
    )
    program_name = _program_name(program)
    faculty = _program_faculty(program)
    curriculum_skills = unique(as_skill_names(program.get("curriculum_skills") or program.get("skills") or []))
    curriculum_topics = unique([clean_human_text(item).strip() for item in _string_items(program.get("curriculum_topics")) if clean_human_text(item).strip()])

    microcurriculum_context = program.get("microcurriculum_context") or {}
    micro_skills = _extract_terms(
        [
            microcurriculum_context.get("technologies"),
            microcurriculum_context.get("technical_skills"),
            microcurriculum_context.get("tools"),
            microcurriculum_context.get("platforms"),
            microcurriculum_context.get("transversal_skills"),
            microcurriculum_context.get("labor_roles"),
            microcurriculum_context.get("benchmarking"),
            microcurriculum_context.get("real_market_gaps"),
            microcurriculum_context.get("strengthening_areas"),
        ]
    )
    micro_tools = _extract_tools(
        [
            microcurriculum_context.get("tools"),
            microcurriculum_context.get("platforms"),
            microcurriculum_context.get("technologies"),
        ]
    )

    market_terms = _market_skill_terms(market_skill_intelligence)
    gap_terms = _gap_terms(curriculum_gap_map)
    cluster_terms = _cluster_terms(occupational_clusters)

    seed_terms = unique(
        [
            *curriculum_skills,
            *curriculum_topics,
            *micro_skills,
            *market_terms,
            *gap_terms,
            *cluster_terms,
            *_domain_roles(domain),
            *DOMAIN_JOB_TERMS.get(domain, []),
            *_domain_families(domain),
            *([clean_human_text(item).strip() for item in (manual_keywords or [])]),
            program_name,
            faculty,
        ]
    )
    if normalized_mode == "focused" and manual_keywords:
        seed_terms = unique([*manual_keywords, *curriculum_skills, program_name, faculty])

    signature_roles = _role_signatures(seed_terms)
    role_candidates = unique(
        [
            *signature_roles,
            *_extract_terms(microcurriculum_context.get("labor_roles"), canonicalize=False),
            *(_domain_roles(domain)),
        ]
    )
    if normalized_mode == "market_discovery":
        role_candidates = unique(
            [
                *role_candidates,
                "Market Intelligence Analyst",
                "Occupational Analyst",
                "Labor Market Analyst",
                "Curriculum Analyst",
            ]
        )

    if normalized_mode == "focused":
        keyword_terms = unique([*curriculum_skills, *curriculum_topics, program_name, faculty, *(manual_keywords or [])])
    elif normalized_mode == "market_discovery":
        keyword_terms = unique([*seed_terms, *market_terms, *gap_terms, *cluster_terms])
    else:
        keyword_terms = unique([*curriculum_skills, *curriculum_topics, *micro_skills, *market_terms, *gap_terms, *cluster_terms, program_name, faculty])

    tools = _extract_tools([*curriculum_skills, *micro_tools, *market_terms, *gap_terms])
    keywords = keyword_terms[:keyword_limit]
    roles = role_candidates[:role_limit]
    families = unique([*_domain_families(domain), *cluster_terms])

    if normalized_mode == "market_discovery":
        discovery_pool = unique(
            [
                *keywords,
                *roles,
                *families,
                *[
                    canonical_skill(item["name"]) or item["name"]
                    for item in SKILL_CATALOG
                    if item["name"] not in keywords and skill_category(item["name"]) != "soft"
                ],
            ]
        )
        keywords = discovery_pool[:keyword_limit]

    query = _build_query([*keywords, *roles, *families])
    source_plans = {
        source: _source_payload(
            source,
            keywords=keywords,
            roles=roles,
            families=families,
            mode=normalized_mode,
            keyword_limit=keyword_limit,
            role_limit=role_limit,
            max_jobs=100 if normalized_mode != "market_discovery" else 1000,
            max_pages=10 if normalized_mode != "market_discovery" else 50,
        )
        for source in CRAWLER_TARGETS
    }

    return {
        "program_id": _program_id(program),
        "program_name": program_name,
        "faculty": faculty,
        "domain": domain,
        "mode": normalized_mode,
        "generated_at": now_iso(),
        "curriculum_skills": curriculum_skills,
        "curriculum_topics": curriculum_topics,
        "microcurriculum_skills": micro_skills,
        "microcurriculum_tools": micro_tools,
        "market_skills": market_terms,
        "gap_skills": gap_terms,
        "occupational_clusters": cluster_terms,
        "skills_extracted": unique([*curriculum_skills, *micro_skills, *market_terms, *gap_terms]),
        "tools_extracted": tools,
        "keywords_generated": keywords,
        "roles_generated": roles,
        "families_generated": families,
        "query": query,
        "source_plans": source_plans,
        "coverage_hint": {
            "expected_job_family_breadth": min(100.0, round(len(keywords) * 2.2 + len(roles) * 3.1 + len(families) * 1.8, 1)),
            "expected_role_expansion": min(100.0, round(len(role_candidates) * 4.2, 1)),
        },
    }


def build_academic_job_acquisition_intelligence(
    programs: Sequence[dict[str, Any]],
    *,
    mode: str = "academic_alignment",
    market_skill_intelligence: Any = None,
    curriculum_gap_map: Any = None,
    occupational_clusters: Any = None,
    manual_keywords: Sequence[str] | None = None,
    keyword_limit: int = 24,
    role_limit: int = 12,
) -> dict[str, Any]:
    normalized_mode = mode if mode in SEARCH_MODES else "academic_alignment"
    program_rows = [repair_text(program.get("name") or program.get("nombre") or "") for program in programs]
    enriched_programs = [
        build_program_search_profile(
            program,
            mode=normalized_mode,
            market_skill_intelligence=market_skill_intelligence,
            curriculum_gap_map=curriculum_gap_map,
            occupational_clusters=occupational_clusters,
            manual_keywords=manual_keywords,
            keyword_limit=keyword_limit,
            role_limit=role_limit,
        )
        for program in programs
    ]

    aggregate_skills = unique(
        [
            *[skill for item in enriched_programs for skill in item["skills_extracted"]],
            *[skill for item in enriched_programs for skill in item["tools_extracted"]],
        ]
    )
    aggregate_keywords = unique([keyword for item in enriched_programs for keyword in item["keywords_generated"]])
    aggregate_roles = unique([role for item in enriched_programs for role in item["roles_generated"]])
    aggregate_families = unique([family for item in enriched_programs for family in item["families_generated"]])
    aggregate_microcurricula = sum(1 for item in enriched_programs if item["microcurriculum_skills"] or item["microcurriculum_tools"])

    crawler_plans = {
        source: _source_payload(
            source,
            keywords=aggregate_keywords,
            roles=aggregate_roles,
            families=aggregate_families,
            mode=normalized_mode,
            keyword_limit=keyword_limit,
            role_limit=role_limit,
            max_jobs=100 if normalized_mode != "market_discovery" else 1000,
            max_pages=10 if normalized_mode != "market_discovery" else 50,
        )
        for source in CRAWLER_TARGETS
    }

    return {
        "generated_at": now_iso(),
        "mode": normalized_mode,
        "programs_analyzed": len(programs),
        "program_names": program_rows,
        "microcurricula_analyzed": aggregate_microcurricula,
        "specializations_analyzed": len({normalize_text(item["program_name"]) for item in enriched_programs if item["program_name"]}),
        "skills_extracted": aggregate_skills,
        "tools_extracted": unique([tool for item in enriched_programs for tool in item["tools_extracted"]]),
        "keywords_generated": aggregate_keywords,
        "roles_generated": aggregate_roles,
        "families_generated": aggregate_families,
        "programs": enriched_programs,
        "crawler_plans": crawler_plans,
        "risk_notes": [
            "LinkedIn may throttle aggressive multi-page discovery.",
            "Keyword expansion can increase duplicate listings across portals.",
            "Market discovery should be audited against curriculum alignment before promotion to production crawls.",
        ],
        "coverage_expectation": {
            "academic_alignment": "broadens search beyond static data/BI terms using curriculum and microcurriculum signals.",
            "market_discovery": "adds market and cluster expansion for new occupations, tools, and skills.",
        },
    }


def get_academic_search_intelligence(
    *,
    mode: str = "academic_alignment",
    manual_keywords: Sequence[str] | None = None,
    keyword_limit: int = 24,
    role_limit: int = 12,
) -> dict[str, Any]:
    from .engine import build_programs

    return build_academic_job_acquisition_intelligence(
        build_programs(),
        mode=mode,
        manual_keywords=manual_keywords,
        keyword_limit=keyword_limit,
        role_limit=role_limit,
    )


def source_plan_for(source_plans: dict[str, Any] | None, source: str) -> dict[str, Any]:
    payload = dict((source_plans or {}).get(source, {}) or {})
    payload.setdefault("source", source)
    payload.setdefault("keywords", [])
    payload.setdefault("roles", [])
    payload.setdefault("families", [])
    payload.setdefault("query", "")
    payload.setdefault("mode", "academic_alignment")
    payload.setdefault("max_jobs", 100)
    payload.setdefault("max_pages", 10)
    return payload
