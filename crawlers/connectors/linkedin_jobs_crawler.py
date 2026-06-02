from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from graduate_intelligence_platform.backend.app.academic_job_acquisition import get_academic_search_intelligence, source_plan_for  # noqa: E402
from agents.agentic_job_extractor import EnterpriseAgenticJobExtractor  # noqa: E402
from agents.visual_analytics_labor_agent import AgentExtractionResult  # noqa: E402
from backend.queries import fetch_program_skills, fetch_specialization_options  # noqa: E402
from backend.repositories.microcurriculum_context_repository import fetch_program_context  # noqa: E402
from backend.repositories.programas_repository import fetch_related_virtual_programs  # noqa: E402
from backend.services.dashboard_service import list_programs_base  # noqa: E402
from intelligence.career_path_engine import build_career_paths  # noqa: E402
from intelligence.domain_benchmark_layer import build_domain_benchmark  # noqa: E402
from intelligence.domain_taxonomy_layer import benchmark_terms_for_domain  # noqa: E402
from ml.curriculum.curriculum_market_gap_engine import build_curriculum_market_gap_map  # noqa: E402
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map  # noqa: E402

SESSION_STATE_PATH = ROOT_DIR / ".local_sessions" / "linkedin_storage_state.json"
LINKEDIN_OUTPUT_REPORT = ROOT_DIR / "outputs" / "linkedin_jobs_crawler_report.md"
DEFAULT_LOCATION = "Colombia"
DEFAULT_MAX_JOBS = 100
DEFAULT_MAX_PAGES = 10
DEFAULT_KEYWORD_LIMIT = 80
DEFAULT_CRAWL_MODE = "academic_alignment"

SECTOR_DISCOVERY_KEYWORDS: dict[str, list[str]] = {
    "technology": ["software engineer", "platform engineer", "cloud engineer", "devops", "site reliability engineer", "solutions architect"],
    "analytics": ["business intelligence", "analytics engineer", "data analyst", "reporting analyst", "data engineer", "power bi"],
    "science_data": ["data scientist", "machine learning engineer", "ml engineer", "ai engineer", "research scientist", "applied scientist"],
    "ai": ["artificial intelligence", "generative ai", "llm engineer", "prompt engineer", "mlops", "llmops"],
    "bi": ["business intelligence", "power bi", "tableau", "qlik", "dashboard analyst", "kpi analyst"],
    "engineering": ["industrial engineer", "process engineer", "project engineer", "quality engineer", "systems engineer", "continuous improvement"],
    "administration": ["operations analyst", "business analyst", "process analyst", "administrative analyst", "office manager"],
    "finance": ["financial analyst", "risk analyst", "compliance analyst", "treasury analyst", "credit analyst", "controller"],
    "health": ["health analyst", "clinical operations", "health informatics", "public health", "epidemiology", "quality in healthcare"],
    "education": ["instructional designer", "academic coordinator", "learning analytics", "curriculum specialist", "education analyst"],
    "logistics": ["supply chain analyst", "logistics coordinator", "inventory analyst", "operations planner", "distribution analyst"],
    "operations": ["operations manager", "process improvement", "service operations", "continuous improvement", "performance analyst"],
    "human_resources": ["talent acquisition", "hr analyst", "people analytics", "organizational development", "compensation analyst"],
    "commercial": ["sales analyst", "commercial analyst", "account executive", "business development", "revenue operations"],
    "marketing": ["marketing analyst", "growth marketing", "digital marketing", "brand analyst", "trade marketing", "performance marketing"],
    "public_sector": ["public sector analyst", "policy analyst", "program analyst", "government analyst", "public administration"],
    "security": ["security analyst", "risk analyst", "safety analyst", "compliance officer", "security operations"],
    "criminology": ["criminal investigation", "forensic analyst", "victimology", "criminal intelligence", "cybercrime", "public safety"],
    "law": ["compliance", "legal analyst", "regulatory analyst", "contracts analyst", "privacy analyst"],
    "industry": ["plant manager", "production analyst", "quality manager", "industrial analyst", "manufacturing engineer"],
    "manufacturing": ["manufacturing engineer", "production planner", "quality assurance", "process engineer", "factory operations"],
}

SOURCE_PRIORITY = {
    "manual": 900,
    "academic_program": 860,
    "microcurriculum": 840,
    "program_skill": 820,
    "program_related": 800,
    "market_skill": 780,
    "market_cluster": 760,
    "domain_benchmark": 740,
    "domain_terms": 720,
    "career_path": 700,
    "sector_discovery": 680,
    "exploratory": 640,
}


@dataclass(frozen=True)
class LinkedInCrawlerConfig:
    storage_state_path: Path = SESSION_STATE_PATH
    keywords: list[str] | None = None
    location: str = DEFAULT_LOCATION
    max_jobs: int = DEFAULT_MAX_JOBS
    max_pages: int = DEFAULT_MAX_PAGES
    keyword_limit: int = DEFAULT_KEYWORD_LIMIT
    crawl_mode: str = DEFAULT_CRAWL_MODE
    headless: bool = True


@dataclass(frozen=True)
class KeywordCandidate:
    keyword: str
    source: str
    weight: float


def storage_state_message(path: Path = SESSION_STATE_PATH) -> str:
    return f"Ejecuta primero scripts/linkedin_manual_login.py. No se encontro sesion local en {path}."


def _job_search_url(keyword: str, location: str, page: int = 0) -> str:
    start = max(page, 0) * 25
    return "https://www.linkedin.com/jobs/search/" f"?keywords={quote_plus(keyword)}&location={quote_plus(location)}&start={start}"


def _is_security_checkpoint(page: Any) -> bool:
    url = str(getattr(page, "url", "") or "").casefold()
    try:
        text = page.locator("body").inner_text(timeout=1500).casefold()
    except Exception:
        text = ""
    markers = (
        "captcha",
        "checkpoint",
        "security verification",
        "verificacion de seguridad",
        "verificaciÃ³n de seguridad",
        "unusual activity",
    )
    return any(marker in url or marker in text for marker in markers)


def _extract_detail_payload(page: Any, job_url: str) -> dict[str, Any]:
    title = ""
    company = ""
    location = ""
    date_posted = ""
    description = ""
    modality = ""
    try:
        title = page.locator("h1").first.inner_text(timeout=3000)
    except Exception:
        title = ""
    for selector in (".job-details-jobs-unified-top-card__company-name", ".jobs-unified-top-card__company-name", "[class*='company-name']"):
        try:
            company = page.locator(selector).first.inner_text(timeout=1500)
            if company:
                break
        except Exception:
            continue
    for selector in (".job-details-jobs-unified-top-card__primary-description-container", ".jobs-unified-top-card__bullet", "[class*='location']"):
        try:
            location = page.locator(selector).first.inner_text(timeout=1500)
            if location:
                break
        except Exception:
            continue
    for selector in ("time", "[class*='posted']", "[class*='listed']"):
        try:
            date_posted = page.locator(selector).first.inner_text(timeout=1200)
            if date_posted:
                break
        except Exception:
            continue
    for selector in (".jobs-description-content__text", "#job-details", "[class*='description']"):
        try:
            description = page.locator(selector).first.inner_text(timeout=3000)
            if description:
                break
        except Exception:
            continue
    lowered = description.casefold()
    if "remote" in lowered or "remoto" in lowered:
        modality = "remote"
    elif "hybrid" in lowered or "hibrido" in lowered or "hÃ­brido" in lowered:
        modality = "hybrid"
    elif "presencial" in lowered or "onsite" in lowered:
        modality = "onsite"
    return {
        "title": title,
        "company": company,
        "location": location or DEFAULT_LOCATION,
        "modality": modality,
        "description": description,
        "requirements": [],
        "responsibilities": [],
        "date_posted": date_posted,
        "job_url": job_url,
        "source_name": "linkedin",
    }


def _normalize_keyword(value: str) -> str:
    return " ".join(str(value).strip().split()).casefold()


def _add_candidate(store: dict[str, KeywordCandidate], keyword: str, source: str, weight: float) -> None:
    normalized = _normalize_keyword(keyword)
    if not normalized:
        return
    if len(normalized) < 2:
        return
    if normalized in {"job", "jobs", "work", "empleo", "vacante", "vacancies", "career", "professional"}:
        return
    existing = store.get(normalized)
    if existing is None or weight > existing.weight or (weight == existing.weight and SOURCE_PRIORITY.get(source, 0) > SOURCE_PRIORITY.get(existing.source, 0)):
        store[normalized] = KeywordCandidate(keyword=str(keyword).strip(), source=source, weight=round(weight, 4))


def _extend_keywords(store: dict[str, KeywordCandidate], values: Iterable[str], *, source: str, weight: float) -> None:
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        _add_candidate(store, text, source, weight)


def _program_display_name(row: dict[str, Any]) -> str:
    for key in ("program_name", "nombre_programa", "nombre", "name", "programa", "specialization_name"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _program_role(row: dict[str, Any]) -> str:
    for key in ("program_role", "perfil_egreso", "perfil de egreso", "role", "rol"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _as_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values] if values.strip() else []
    if isinstance(values, dict):
        return _as_text_list(list(values.values()))
    if isinstance(values, (list, tuple, set)):
        result: list[str] = []
        for item in values:
            result.extend(_as_text_list(item))
        return result
    return [str(values)]


def _load_program_sources() -> list[dict[str, Any]]:
    programs = list_programs_base()
    if programs:
        return programs
    options = fetch_specialization_options()
    return [dict(option) for option in options]


def _market_skill_candidates(limit: int) -> list[KeywordCandidate]:
    store: dict[str, KeywordCandidate] = {}
    try:
        intelligence = build_market_skill_intelligence_map(include_database=True, write_output=False)
        _extend_keywords(
            store,
            (
                signal.skill
                for signal in intelligence.market_skills[:limit]
                if getattr(signal, "skill", "")
            ),
            source="market_skill",
            weight=92.0,
        )
        _extend_keywords(
            store,
            (
                signal.occupational_cluster
                for signal in intelligence.market_skills[:limit]
                if getattr(signal, "occupational_cluster", "")
            ),
            source="market_cluster",
            weight=88.0,
        )
        _extend_keywords(
            store,
            (
                getattr(signal, "skill", "")
                for signal in intelligence.emerging_skills[: max(5, limit // 5)]
                if getattr(signal, "skill", "")
            ),
            source="market_skill",
            weight=95.0,
        )
    except Exception:
        pass
    return list(store.values())


def _gap_candidates(limit: int) -> list[KeywordCandidate]:
    store: dict[str, KeywordCandidate] = {}
    try:
        gap_map = build_curriculum_market_gap_map(write_output=False)
        for item in (gap_map.emerging_skills[:limit] + gap_map.missing_skills[:limit]):
            skill = getattr(item, "skill", "")
            cluster_name = getattr(item, "cluster_name", "")
            recommendation = getattr(item, "recommendation", "")
            if skill:
                _add_candidate(store, skill, "market_skill", 90.0)
            if cluster_name:
                _add_candidate(store, cluster_name, "market_cluster", 82.0)
            for term in recommendation.split():
                if len(term) > 3:
                    _add_candidate(store, term, "exploratory", 55.0)
        for update in gap_map.recommended_curriculum_updates[:limit]:
            _extend_keywords(
                store,
                [str(update.get("skill") or ""), str(update.get("cluster_name") or ""), str(update.get("action") or "")],
                source="exploratory",
                weight=58.0,
            )
    except Exception:
        pass
    return list(store.values())


def _academic_candidates(limit: int) -> list[KeywordCandidate]:
    store: dict[str, KeywordCandidate] = {}
    programs = _load_program_sources()
    ranking = sorted(
        programs,
        key=lambda row: (
            float(row.get("promedio_match_mercado", 0) or 0),
            int(row.get("total_skills_programa", 0) or 0),
        ),
        reverse=True,
    )
    for program in ranking[:limit]:
        program_name = _program_display_name(program)
        program_role = _program_role(program)
        program_id = int(program.get("especializacion_id") or program.get("id") or 0)
        if program_name:
            _add_candidate(store, program_name, "academic_program", 100.0)
        if program_role:
            _add_candidate(store, program_role, "academic_program", 99.0)
        try:
            skills_payload = fetch_program_skills(program_id) if program_id else {}
        except Exception:
            skills_payload = {}
        for source_name, weight in (
            ("skills", 95.0),
            ("herramientas", 94.0),
            ("competencias", 93.0),
            ("habilidades_blandas", 88.0),
        ):
            _extend_keywords(store, _as_text_list(skills_payload.get(source_name)), source="program_skill", weight=weight)
        try:
            context = fetch_program_context(program_id, specialization_name=program_name or None)
        except Exception:
            context = None
        if context:
            for field_name, weight in (
                ("subjects", 90.0),
                ("technical_skills", 96.0),
                ("transversal_skills", 85.0),
                ("methodologies", 82.0),
                ("tools", 98.0),
                ("platforms", 80.0),
                ("technologies", 99.0),
                ("keywords", 94.0),
                ("occupational_profiles", 92.0),
                ("real_market_gaps", 91.0),
                ("strengthening_areas", 89.0),
                ("labor_roles", 93.0),
                ("benchmarking", 86.0),
            ):
                _extend_keywords(store, _as_text_list(context.get(field_name)), source="microcurriculum", weight=weight)
        try:
            related_programs = fetch_related_virtual_programs(program_name, limit=5) if program_name else []
        except Exception:
            related_programs = []
        for related in related_programs or []:
            related_name = _program_display_name(dict(related))
            if related_name:
                _add_candidate(store, related_name, "program_related", 84.0)
        try:
            domain = build_domain_benchmark(str(program.get("domain_key") or program.get("detected_domain") or "data_analytics"))
        except Exception:
            domain = build_domain_benchmark("data_analytics")
        _extend_keywords(store, domain.core_competencies, source="domain_benchmark", weight=87.0)
        _extend_keywords(store, domain.priority_skills, source="domain_benchmark", weight=89.0)
        _extend_keywords(store, domain.market_skills, source="domain_benchmark", weight=91.0)
        _extend_keywords(store, domain.market_signals, source="domain_benchmark", weight=83.0)
        _extend_keywords(store, domain.labor_roles, source="domain_benchmark", weight=86.0)
        _extend_keywords(store, benchmark_terms_for_domain(domain.domain_key), source="domain_terms", weight=85.0)
        try:
            career_paths = build_career_paths([], [*domain.market_skills, *domain.priority_skills, *benchmark_terms_for_domain(domain.domain_key)])
        except Exception:
            career_paths = []
        for transition in career_paths[:5]:
            _extend_keywords(
                store,
                [transition.source_role, transition.target_role, *transition.recommended_next_skills],
                source="career_path",
                weight=78.0,
            )
    return list(store.values())


def _sector_discovery_candidates() -> list[KeywordCandidate]:
    store: dict[str, KeywordCandidate] = {}
    for sector, values in SECTOR_DISCOVERY_KEYWORDS.items():
        _extend_keywords(store, values, source="sector_discovery", weight=75.0)
        _add_candidate(store, sector.replace("_", " "), "sector_discovery", 70.0)
    return list(store.values())


def _exploratory_candidates() -> list[KeywordCandidate]:
    values = [
        "vacante junior",
        "vacante senior",
        "talent acquisition specialist",
        "business operations",
        "process excellence",
        "market research",
        "customer insights",
        "service delivery",
        "risk and compliance",
        "continuous improvement",
    ]
    return [KeywordCandidate(keyword=item, source="exploratory", weight=60.0) for item in values]


def _dedupe_sort_candidates(candidates: Iterable[KeywordCandidate], *, limit: int) -> list[KeywordCandidate]:
    deduped: dict[str, KeywordCandidate] = {}
    for candidate in candidates:
        _add_candidate(deduped, candidate.keyword, candidate.source, candidate.weight)
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            -item.weight,
            -SOURCE_PRIORITY.get(item.source, 0),
            item.keyword.casefold(),
        ),
    )
    return ordered[:limit]


def _build_keyword_plan(config: LinkedInCrawlerConfig, search_intelligence: dict[str, Any] | None = None) -> list[KeywordCandidate]:
    intelligence = search_intelligence or get_academic_search_intelligence(mode=config.crawl_mode, manual_keywords=config.keywords, keyword_limit=config.keyword_limit, role_limit=max(12, config.keyword_limit // 2))
    source_plan = source_plan_for(intelligence.get("crawler_plans"), "linkedin")
    manual = [item.strip() for item in (config.keywords or []) if item and item.strip()]
    if config.crawl_mode == "focused":
        base_terms = manual or source_plan.get("keywords") or ["data analyst", "business intelligence", "power bi", "analytics engineer", "data visualization", "big data", "data engineer"]
        return _dedupe_sort_candidates([KeywordCandidate(keyword=item, source="manual" if manual else "academic_plan", weight=100.0) for item in base_terms], limit=config.keyword_limit)

    candidates: list[KeywordCandidate] = []
    for keyword in source_plan.get("keywords", []):
        candidates.append(KeywordCandidate(keyword=str(keyword), source="academic_program", weight=100.0))
    for role in source_plan.get("roles", []):
        candidates.append(KeywordCandidate(keyword=str(role), source="career_path", weight=95.0))
    for family in source_plan.get("families", []):
        candidates.append(KeywordCandidate(keyword=str(family), source="sector_discovery", weight=90.0))
    for skill in intelligence.get("keywords_generated", [])[: config.keyword_limit]:
        candidates.append(KeywordCandidate(keyword=str(skill), source="market_skill", weight=88.0))
    if manual:
        candidates = [*([KeywordCandidate(keyword=item, source="manual", weight=100.0) for item in manual]), *candidates]
    if config.crawl_mode == "market_discovery":
        candidates.extend([KeywordCandidate(keyword=str(item), source="exploratory", weight=80.0) for item in intelligence.get("keywords_generated", []) if str(item)])
    return _dedupe_sort_candidates(candidates, limit=config.keyword_limit)


def _collect_job_links(page: Any, *, min_rounds: int = 3, max_rounds: int = 6) -> list[str]:
    seen: set[str] = set()
    stable_rounds = 0
    for round_index in range(max_rounds):
        try:
            links = page.locator("a[href*='/jobs/view/']").evaluate_all(
                "(els) => [...new Set(els.map((a) => a.href).filter(Boolean))]"
            )
        except Exception:
            links = []
        before = len(seen)
        for link in links or []:
            seen.add(str(link).split("?")[0])
        if len(seen) == before:
            stable_rounds += 1
        else:
            stable_rounds = 0
        if round_index + 1 >= max_rounds:
            break
        try:
            page.mouse.wheel(0, random.randint(700, 1400))
        except Exception:
            pass
        try:
            page.wait_for_timeout(random.randint(900, 1600))
        except Exception:
            pass
        if round_index + 1 >= min_rounds and stable_rounds >= 2:
            break
    return sorted(seen)


class LinkedInJobsCrawler:
    def __init__(self, config: LinkedInCrawlerConfig | None = None) -> None:
        self.config = config or LinkedInCrawlerConfig()
        self.extractor = EnterpriseAgenticJobExtractor()
        self.search_intelligence = get_academic_search_intelligence(mode=self.config.crawl_mode, manual_keywords=self.config.keywords, keyword_limit=self.config.keyword_limit, role_limit=max(12, self.config.keyword_limit // 2))
        self.source_plan = source_plan_for(self.search_intelligence.get("crawler_plans"), "linkedin")
        self.keyword_plan = _build_keyword_plan(self.config, self.search_intelligence)
        self.keywords = [item.keyword for item in self.keyword_plan]

    def ensure_storage_state(self) -> tuple[bool, str]:
        path = self.config.storage_state_path
        if not path.exists():
            return False, storage_state_message(path)
        return True, "storage_state_available"

    def run(self, *, execute_network: bool = False) -> tuple[list[AgentExtractionResult], list[dict[str, str]]]:
        ready, message = self.ensure_storage_state()
        if not ready:
            return [], [{"source": "linkedin", "error_type": "missing_storage_state", "error_message": message}]
        if not execute_network:
            return [], [{"source": "linkedin", "error_type": "dry_run", "error_message": "network_not_executed"}]
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - optional runtime
            return [], [{"source": "linkedin", "error_type": "playwright_missing", "error_message": str(exc)}]

        results: list[AgentExtractionResult] = []
        errors: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            context = browser.new_context(
                storage_state=str(self.config.storage_state_path),
                viewport={"width": 1366, "height": 850},
                locale="es-CO",
            )
            page = context.new_page()
            for candidate in self.keyword_plan:
                for page_index in range(self.config.max_pages):
                    if len(results) >= self.config.max_jobs:
                        break
                    search_url = _job_search_url(candidate.keyword, self.config.location, page_index)
                    try:
                        page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
                        page.wait_for_timeout(random.randint(1600, 3200))
                        links = _collect_job_links(page, min_rounds=3, max_rounds=6)
                        if _is_security_checkpoint(page):
                            errors.append({"source": "linkedin", "error_type": "security_checkpoint", "error_message": "captcha_or_checkpoint_detected"})
                            browser.close()
                            write_linkedin_report(results, errors, self.keyword_plan, self.config.crawl_mode)
                            return results, errors
                        for link in links:
                            job_url = str(link).split("?")[0]
                            if job_url in seen_urls or len(results) >= self.config.max_jobs:
                                continue
                            seen_urls.add(job_url)
                            detail = context.new_page()
                            try:
                                detail.goto(job_url, wait_until="domcontentloaded", timeout=35000)
                                detail.wait_for_timeout(random.randint(1800, 3600))
                                if _is_security_checkpoint(detail):
                                    errors.append({"source": "linkedin", "error_type": "security_checkpoint", "error_message": "captcha_or_checkpoint_detected"})
                                    detail.close()
                                    browser.close()
                                    write_linkedin_report(results, errors, self.keyword_plan, self.config.crawl_mode)
                                    return results, errors
                                payload = _extract_detail_payload(detail, job_url)
                                html = "<html><body><main>"
                                html += f"<h1>{payload['title']}</h1>"
                                html += f"<div class='company'>{payload['company']}</div>"
                                html += f"<div class='location'>{payload['location']}</div>"
                                html += f"<article class='description'>{payload['description']}</article>"
                                html += "</main></body></html>"
                                result = self.extractor.inspect_detail_html(
                                    html=html,
                                    source_name="linkedin",
                                    source_url=job_url,
                                    fallback_title=payload["title"],
                                )
                                curation_level = str(getattr(result.silver, "curation_level", "curated_job") or "curated_job")
                                contextual = dict(result.silver.contextual)
                                contextual.update(
                                    {
                                        "crawl_mode": self.config.crawl_mode,
                                        "search_keyword": candidate.keyword,
                                        "search_keyword_source": candidate.source,
                                        "search_keyword_weight": candidate.weight,
                                        "modality": payload["modality"],
                                        "date_posted": payload["date_posted"],
                                        "requirements": payload["requirements"],
                                        "responsibilities": payload["responsibilities"],
                                        "candidate_job": True,
                                        "probable_job": curation_level in {"probable_job", "curated_job", "gold_job"},
                                        "curated_job": curation_level in {"curated_job", "gold_job"},
                                        "gold_job": bool(getattr(result, "gold", None)),
                                        "curation_level": curation_level,
                                        "search_plan": self.source_plan,
                                    }
                                )
                                result.silver.contextual.update(contextual)
                                results.append(result)
                            except Exception as exc:
                                errors.append({"source": "linkedin", "error_type": type(exc).__name__, "error_message": str(exc)[:400]})
                            finally:
                                try:
                                    detail.close()
                                except Exception:
                                    pass
                            time.sleep(random.uniform(1.2, 2.8))
                    except Exception as exc:
                        errors.append({"source": "linkedin", "error_type": type(exc).__name__, "error_message": str(exc)[:400]})
                if len(results) >= self.config.max_jobs:
                    break
            browser.close()
        write_linkedin_report(results, errors, self.keyword_plan, self.config.crawl_mode)
        return results, errors


def _curation_counts(results: list[AgentExtractionResult]) -> dict[str, int]:
    counts = Counter(str(getattr(result.silver, "curation_level", "unknown") or "unknown") for result in results)
    return dict(sorted(counts.items()))


def write_linkedin_report(
    results: list[AgentExtractionResult],
    errors: list[dict[str, str]],
    keyword_plan: list[KeywordCandidate] | None = None,
    crawl_mode: str = DEFAULT_CRAWL_MODE,
) -> None:
    LINKEDIN_OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    keyword_plan = keyword_plan or []
    lines = [
        "# LinkedIn Jobs Crawler Report",
        "",
        f"- Crawl mode: {crawl_mode}",
        f"- Resultados: {len(results)}",
        f"- Errores: {len(errors)}",
        f"- Curacion: {json.dumps(_curation_counts(results), ensure_ascii=False)}",
        f"- Storage state: local file used, contents never printed.",
        "",
        "## Plan de busqueda",
    ]
    for candidate in keyword_plan[:40]:
        lines.append(f"- {candidate.keyword} | {candidate.source} | {candidate.weight}")
    lines.extend(["", "## Vacantes"])
    for result in results[:40]:
        contextual = dict(getattr(result.silver, "contextual", {}) or {})
        lines.extend(
            [
                f"- {result.silver.normalized_title} | {result.silver.normalized_company} | {result.silver.normalized_location}",
                f"  - URL: {result.silver.source_url}",
                f"  - Curation: {getattr(result.silver, 'curation_level', 'unknown')}",
                f"  - Search keyword: {contextual.get('search_keyword', 'N/A')} ({contextual.get('search_keyword_source', 'N/A')})",
                f"  - Source plan: {contextual.get('search_plan', {}).get('mode', crawl_mode)}",
                f"  - Skills: {', '.join(result.silver.job_evidence_skills or []) or 'N/A'}",
            ]
        )
    lines.extend(["", "## Errores"])
    lines.extend([f"- {error['error_type']}: {error['error_message']}" for error in errors] or ["- Sin errores."])
    LINKEDIN_OUTPUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LinkedIn labor acquisition crawler")
    parser.add_argument("--crawl-mode", choices=("focused", "academic_alignment", "market_discovery"), default=DEFAULT_CRAWL_MODE)
    parser.add_argument("--keyword", action="append", dest="keywords", default=None, help="Manual keyword override. Repeatable.")
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    parser.add_argument("--max-jobs", type=int, default=DEFAULT_MAX_JOBS)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--keyword-limit", type=int, default=DEFAULT_KEYWORD_LIMIT)
    parser.add_argument("--storage-state-path", type=Path, default=SESSION_STATE_PATH)
    parser.add_argument("--headless", dest="headless", action="store_true")
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.set_defaults(headless=False)
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without running Playwright.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    config = LinkedInCrawlerConfig(
        storage_state_path=args.storage_state_path,
        keywords=args.keywords,
        location=args.location,
        max_jobs=max(1, int(args.max_jobs)),
        max_pages=max(1, int(args.max_pages)),
        keyword_limit=max(1, int(args.keyword_limit)),
        crawl_mode=str(args.crawl_mode),
        headless=bool(args.headless),
    )
    crawler = LinkedInJobsCrawler(config)
    if args.dry_run:
        payload = {
            "crawl_mode": config.crawl_mode,
            "location": config.location,
            "max_jobs": config.max_jobs,
            "max_pages": config.max_pages,
            "keyword_limit": config.keyword_limit,
            "keywords": [candidate.__dict__ for candidate in crawler.keyword_plan],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    results, errors = crawler.run(execute_network=True)
    print(
        json.dumps(
            {
                "crawl_mode": config.crawl_mode,
                "results": len(results),
                "errors": errors,
                "keyword_plan_size": len(crawler.keyword_plan),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if results or errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
