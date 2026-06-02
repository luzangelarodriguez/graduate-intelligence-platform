from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from intelligence.domain_benchmark_layer import build_domain_benchmark  # noqa: E402
from scrapers.connectors.criminology_labor_connector import criminology_source_profiles  # noqa: E402

OUTPUT_PATH = ROOT_DIR / "outputs" / "criminology_labor_intelligence_expansion.md"

CRIMINOLOGY_TAXONOMY = [
    "criminal investigation",
    "victimology",
    "forensic analysis",
    "cybercrime",
    "criminal intelligence",
    "compliance",
    "risk analysis",
    "chain of custody",
    "organized crime",
    "financial crime",
    "public safety",
]

FEED_TARGETS = [
    "skills_master",
    "skills_alias",
    "semantic_role_graph",
    "curriculum_gap_observatory",
    "recommendation_observatory",
]

EXTRACTION_CONTRACT = [
    "role title",
    "employer",
    "skills",
    "competencies",
    "requirements",
    "certifications",
    "responsibilities",
]


def _slug(value: str) -> str:
    return value.casefold().replace(" ", "_").replace("-", "_")


def _graph_edges(roles: list[str], skills: list[str]) -> list[tuple[str, str, list[str]]]:
    edge_specs = [
        ("Forensic Analyst", "Criminal Intelligence Analyst", ["forensic analysis", "chain of custody", "criminal intelligence"]),
        ("Criminal Intelligence Analyst", "Cybercrime Investigator", ["criminal intelligence", "cybercrime", "risk analysis"]),
        ("Cybercrime Investigator", "Financial Crime Specialist", ["cybercrime", "financial crime", "chain of custody"]),
        ("Compliance Analyst", "Risk Analyst", ["compliance", "risk analysis", "financial crime"]),
        ("Victim Assistance Specialist", "Public Security Advisor", ["victimology", "public safety", "crime prevention"]),
        ("Investigador Policia Judicial", "Analista Criminal", ["criminal investigation", "criminal analysis", "chain of custody"]),
        ("Profesional Penitenciario", "Public Security Advisor", ["penitentiary systems", "public safety", "risk analysis"]),
    ]
    role_lookup = {_slug(role): role for role in roles}
    skill_lookup = {_slug(skill): skill for skill in skills}
    edges: list[tuple[str, str, list[str]]] = []
    for source, target, shared in edge_specs:
        resolved_source = role_lookup.get(_slug(source), source)
        resolved_target = role_lookup.get(_slug(target), target)
        resolved_skills = [skill_lookup.get(_slug(skill), skill) for skill in shared]
        edges.append((resolved_source, resolved_target, resolved_skills))
    return edges


def _display_paths(base_url: str, paths: tuple[str, ...]) -> str:
    resolved: list[str] = []
    for path in paths:
        if not path:
            resolved.append(base_url)
        elif path.startswith(("http://", "https://")):
            resolved.append(path)
        else:
            resolved.append(f"{base_url.rstrip('/')}/{path.lstrip('/')}")
    return ", ".join(dict.fromkeys(resolved))


def build_report() -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    profiles = criminology_source_profiles()
    benchmark = build_domain_benchmark("criminology")
    roles = sorted({role for profile in profiles for role in profile.benchmark_roles} | set(benchmark.labor_roles))
    skills = list(dict.fromkeys([*CRIMINOLOGY_TAXONOMY, *benchmark.market_skills, *benchmark.priority_skills]))
    edges = _graph_edges(roles, skills)

    lines = [
        "# Criminology Labor Intelligence Expansion",
        "",
        f"- Generated at: {generated_at}",
        "- Platform decision: reuses the existing labor acquisition platform, `StructuredConnectorCrawler`, `BaseJobConnector`, and the current bronze/silver/gold observatory feed path.",
        "- New engines created: none.",
        f"- Extraction contract: {', '.join(EXTRACTION_CONTRACT)}.",
        f"- Feed targets: {', '.join(FEED_TARGETS)}.",
        "",
        "## New Sources",
        "",
    ]
    for profile in profiles:
        urls = _display_paths(profile.base_url, profile.search_paths) if profile.search_paths else profile.base_url
        lines.append(f"- {profile.source_name} (`{profile.key}`): {profile.base_url} | employer: {profile.employer} | priority: {profile.priority} | crawl paths: {urls}")

    lines.extend(["", "## New Roles", ""])
    for role in roles:
        lines.append(f"- {role}")

    lines.extend(["", "## New Skills", ""])
    for skill in skills:
        lines.append(f"- {skill}")

    lines.extend(["", "## New Graph Edges", ""])
    for source, target, shared in edges:
        lines.append(f"- {source} -> {target}: shared skills = {', '.join(shared)}")

    lines.extend(
        [
            "",
            "## New Benchmark Coverage",
            "",
            f"- Reference program: {benchmark.reference_program}",
            f"- Benchmark institutions covered: {len(benchmark.benchmark_institutions)}",
            f"- Core competencies covered: {', '.join(benchmark.core_competencies)}",
            f"- Priority skills covered: {', '.join(benchmark.priority_skills)}",
            f"- Market signals covered: {', '.join(benchmark.market_signals)}",
            "",
            "## Feed Mapping",
            "",
            "- `skills_master`: adds canonical criminology, forensic, cybercrime, risk, compliance, public safety, organized crime, and financial crime skills.",
            "- `skills_alias`: maps Spanish and English aliases such as investigacion criminal, victimologia, criminalistica, ciberdelito, cadena de custodia, lavado de activos, seguridad publica, and public safety.",
            "- `semantic_role_graph`: adds role transitions for forensic, investigative, cybercrime, compliance, penitentiary, victim assistance, and public safety profiles.",
            "- `curriculum_gap_observatory`: compares program 108 coverage against the expanded criminology benchmark and new labor evidence.",
            "- `recommendation_observatory`: prioritizes modules and career-path recommendations around evidence handling, cybercrime, victimology, intelligence analysis, risk, compliance, and public safety.",
            "",
            "## Impact On Program 108",
            "",
            "- Program 108 is treated as `criminology`, preserving its domain identity and avoiding analytics-only contamination.",
            "- The labor benchmark now observes international law-enforcement, multilateral, Colombian public-sector, and private security demand signals.",
            "- Expected curriculum pressure increases around cybercrime, forensic analysis, chain of custody, criminal intelligence, financial crime, organized crime, risk analysis, compliance, and victimology.",
            "- The expanded connector set improves employability evidence for roles such as Criminal Intelligence Analyst, Cybercrime Investigator, Forensic Analyst, Victim Assistance Specialist, Public Security Advisor, Compliance Analyst, Tecnico Investigador Criminalistico, Investigador Judicial, and Profesional Penitenciario.",
            "- Recommendations for program 108 can now be grounded in institutional labor evidence from Interpol, Europol, UN Careers, UNODC, Fiscalia Colombia, Policia Nacional Colombia, INPEC, Procuraduria, Defensoria, Securitas, G4S, and Prosegur.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_report() + "\n", encoding="utf-8")
    print(str(OUTPUT_PATH))


if __name__ == "__main__":
    main()
