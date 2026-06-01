from __future__ import annotations

from typing import Any

from intelligence.domain_benchmark_layer import DomainBenchmarkProfile
from intelligence.domain_taxonomy_layer import DomainTaxonomyResult


def _focus_sentence(domain: DomainTaxonomyResult, benchmark: DomainBenchmarkProfile) -> str:
    if benchmark.narrative_focus:
        return benchmark.narrative_focus
    return f"enfoque ejecutivo para {domain.domain_label}"


def build_domain_system_prompt(*, task: str, domain: DomainTaxonomyResult, benchmark: DomainBenchmarkProfile) -> str:
    domain_label = domain.domain_label or "Academic Intelligence"
    focus = _focus_sentence(domain, benchmark)
    core_competencies = ", ".join(benchmark.core_competencies[:5]) or "competencias académicas y laborales"
    priority_skills = ", ".join(benchmark.priority_skills[:6]) or "skills priorizadas por el observatorio"
    institutions = ", ".join(
        str(item.get("institution") or "")
        for item in (benchmark.benchmark_institutions or [])[:4]
        if str(item.get("institution") or "").strip()
    )
    occupational_profile = ", ".join(benchmark.occupational_profile[:5]) or "perfil ocupacional benchmark"
    return (
        "Eres un asistente ejecutivo académico para un observatorio de pertinencia. "
        "Responde SOLO en JSON válido, breve y verificable. No inventes métricas ni fuentes. "
        f"Dominio académico: {domain_label}. Subdominio: {domain.subdomain or 'general'}. "
        f"Enfoque: {focus}. "
        f"Competencias benchmark: {core_competencies}. "
        f"Skills prioritarias benchmark: {priority_skills}. "
        f"Instituciones benchmark: {institutions or 'no especificadas'}. "
        f"Perfil ocupacional benchmark: {occupational_profile}. "
        f"Tarea: {task}. "
        "Si un dato no existe, indícalo explícitamente y conserva la evidencia disponible."
    )


def build_domain_prompt_payload(*, task: str, domain: DomainTaxonomyResult, benchmark: DomainBenchmarkProfile, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": task,
        "domain_taxonomy": domain.to_dict(),
        "domain_benchmark": benchmark.to_dict(),
        "evidence": evidence,
    }
