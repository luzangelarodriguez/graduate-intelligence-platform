from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.relevance.contextual_job_relevance_engine import (  # noqa: E402
    ContextualRelevanceResult,
    result_to_dict,
    score_contextual_relevance,
)
from scrapers.connectors.base import absolute_url, compact_text  # noqa: E402
from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    extract_visual_analytics_skills,
    normalize_text,
)

GOLD_CONTEXTUAL_THRESHOLD = 0.62
GOLD_ANALYTICS_DENSITY_THRESHOLD = 0.40
GOLD_SEMANTIC_THRESHOLD = 0.40
PROBABLE_JOB_THRESHOLD = 0.30
CURATED_JOB_THRESHOLD = 0.55
GOLD_JOB_THRESHOLD = 0.75
INVALID_TITLES = {
    "skills",
    "lugar de trabajo",
    "buscar ofertas",
    "search",
    "filtros",
    "categorias",
    "categorías",
    "ofertas de empleo",
}
JOB_POSTING_SIGNALS = {
    "responsable",
    "debe",
    "construir",
    "responsabilidades",
    "requisitos",
    "experiencia",
    "contrato",
    "salario",
    "empresa",
    "modalidad",
    "funciones",
    "postulacion",
    "postulación",
    "aplicar",
}
SUPPORT_NEGATIVE_SIGNALS = {
    "helpdesk",
    "mesa de ayuda",
    "soporte tecnico",
    "soporte técnico",
    "soporte en sitio",
    "hardware",
    "impresoras",
    "cableado",
    "active directory",
    "networking",
}
FILTER_TAXONOMY_SIGNALS = {
    "filtrar",
    "filtros",
    "skills",
    "categorias",
    "categorías",
    "ubicaciones",
    "lugar de trabajo",
    "areas",
    "áreas",
    "cargo",
    "ofertas encontradas",
}


@dataclass(frozen=True)
class BronzeEvidence:
    source_name: str
    source_url: str
    raw_html: str
    raw_text: str
    raw_json: dict[str, Any]
    extraction_timestamp: str
    page_title: str
    http_status: int | None
    extraction_method: str
    content_hash: str
    detected_language: str


@dataclass(frozen=True)
class SilverEvidence:
    source_name: str
    source_url: str
    normalized_title: str
    normalized_company: str
    normalized_location: str
    normalized_description: str
    extracted_skills: list[str]
    extracted_tools: list[str]
    extracted_cloud: list[str]
    extracted_frameworks: list[str]
    analytics_density: float
    contextual_relevance_score: float
    semantic_score: float
    rejection_reason: str
    accepted_for_gold: bool
    parser_version: str
    content_hash: str
    contextual: dict[str, Any]
    document_type: str = "unknown"
    evidence_source_type: str = "unknown"
    is_real_job_posting: bool = False
    invalid_job_reason: str = ""
    job_evidence_skills: list[str] | None = None
    portal_taxonomy_skills: list[str] | None = None
    job_probability_score: float = 0.0
    curation_level: str = "rejected"
    semantic_evidence_count: int = 0
    top_acceptance_reasons: list[str] | None = None
    unknown_skill_candidates: list[str] | None = None


@dataclass(frozen=True)
class GoldEvidence:
    curated_title: str
    curated_description: str
    evidence_summary: str
    normalized_skills: list[str]
    market_role: str
    analytics_relevance: float
    ai_confidence: float
    approved_by_agent: bool
    approved_timestamp: str
    source_name: str
    source_url: str
    content_hash: str


@dataclass(frozen=True)
class AgentExtractionResult:
    bronze: BronzeEvidence
    silver: SilverEvidence
    gold: GoldEvidence | None


def content_hash(*parts: str) -> str:
    return hashlib.sha256(normalize_text(" ".join(parts)).encode("utf-8")).hexdigest()


def detect_language(text: str) -> str:
    normalized = normalize_text(text)
    spanish_markers = {" de ", " para ", " con ", " analitica ", " datos ", " experiencia "}
    english_markers = {" the ", " with ", " data ", " analytics ", " experience "}
    spanish = sum(marker in f" {normalized} " for marker in spanish_markers)
    english = sum(marker in f" {normalized} " for marker in english_markers)
    return "es" if spanish >= english else "en"


def extract_candidate_cards(html: str, *, source_name: str, source_url: str, max_jobs: int) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    selectors = [
        "article",
        "[class*='job']",
        "[class*='vacante']",
        "[class*='oferta']",
        "a[href*='job']",
        "a[href*='empleo']",
        "a[href*='oferta']",
        "a[href*='it-job-openings']",
    ]
    cards = []
    for selector in selectors:
        cards.extend(soup.select(selector))
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for card in cards:
        text = compact_text(card.get_text(" ", strip=True))
        if len(text) < 60:
            continue
        title_node = card.select_one("h1,h2,h3,[class*='title'],[class*='cargo'],a")
        link = card if card.name == "a" else card.select_one("a[href]")
        title = compact_text(title_node.get_text(" ", strip=True) if title_node else text[:90])
        href = absolute_url(source_url, link.get("href") if link else source_url)
        if href.lower().startswith("javascript:"):
            continue
        key = content_hash(source_name, title, href, text[:240])
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"title": title, "url": href, "text": text})
        if len(candidates) >= max_jobs:
            break
    return candidates


def _json_ld_objects(soup: BeautifulSoup) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for node in soup.select("script[type='application/ld+json']"):
        try:
            payload = json.loads(node.string or node.get_text(" ", strip=True) or "{}")
        except Exception:
            continue
        stack = payload if isinstance(payload, list) else [payload]
        for item in stack:
            if isinstance(item, dict):
                if isinstance(item.get("@graph"), list):
                    objects.extend([graph_item for graph_item in item["@graph"] if isinstance(graph_item, dict)])
                objects.append(item)
    return objects


def _company_from_json_ld(soup: BeautifulSoup) -> str:
    for item in _json_ld_objects(soup):
        org = item.get("hiringOrganization") or item.get("organization") or item.get("publisher")
        if isinstance(org, dict):
            value = org.get("name") or org.get("legalName")
            if value:
                return compact_text(str(value))
        if isinstance(org, str):
            return compact_text(org)
    return ""


def _company_from_metadata(soup: BeautifulSoup) -> str:
    selectors = [
        ("meta[property='og:site_name']", "content"),
        ("meta[property='og:article:author']", "content"),
        ("meta[name='author']", "content"),
        ("meta[name='company']", "content"),
        ("meta[itemprop='hiringOrganization']", "content"),
    ]
    for selector, attr in selectors:
        node = soup.select_one(selector)
        value = compact_text(node.get(attr, "") if node else "")
        if value and value.casefold() not in {"ticjob", "elempleo", "linkedin", "indeed"}:
            return value
    return ""


def _company_from_text(raw_text: str, title: str) -> str:
    patterns = [
        r"(?:empresa|compa[nñ]ia|company|contratante)\s*[:\-]\s*([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ&.,\- ]{2,70})",
        r"(?:en|para)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ0-9&.,\- ]{2,55})\s+(?:buscamos|requiere|solicita)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text)
        if match:
            candidate = compact_text(match.group(1)).strip(" .,-")
            if candidate and candidate.casefold() not in title.casefold():
                return candidate[:80]
    return ""


def classify_document_type(payload: dict[str, Any], *, source_url: str) -> dict[str, Any]:
    title = compact_text(str(payload.get("title") or ""))
    company = compact_text(str(payload.get("company") or ""))
    description = compact_text(str(payload.get("description") or ""))
    normalized_title = normalize_text(title)
    normalized_description = normalize_text(description)
    normalized_url = (source_url or "").strip().casefold()
    reasons: list[str] = []

    if not title:
        reasons.append("empty_title")
    if normalized_title in {normalize_text(item) for item in INVALID_TITLES}:
        reasons.append("invalid_catalog_title")
    if not company:
        reasons.append("empty_company")
    if not normalized_url.startswith(("http://", "https://")):
        reasons.append("invalid_source_url")
    if normalized_url.startswith("javascript:"):
        reasons.append("javascript_source_url")

    job_signal_hits = [signal for signal in JOB_POSTING_SIGNALS if normalize_text(signal) in normalized_description]
    taxonomy_hits = [signal for signal in FILTER_TAXONOMY_SIGNALS if normalize_text(signal) in normalized_description or normalize_text(signal) in normalized_title]
    support_negative_hits = [signal for signal in SUPPORT_NEGATIVE_SIGNALS if normalize_text(signal) in normalized_description or normalize_text(signal) in normalized_title]
    extracted = extract_visual_analytics_skills(f"{title} {description} {' '.join(payload.get('tags', []) or [])}")
    text_length = len(description)
    title_quality = 0.0
    if title and normalized_title not in {normalize_text(item) for item in INVALID_TITLES}:
        title_quality += 0.30
    if 3 <= len(title.split()) <= 14:
        title_quality += 0.15
    if company:
        title_quality += 0.10
    source_quality = 0.10 if normalized_url.startswith(("http://", "https://")) and not normalized_url.startswith("javascript:") else 0.0
    signal_score = min(len(job_signal_hits) / 3, 1.0) * 0.20
    semantic_score = min(len(extracted) / 6, 1.0) * 0.20
    text_score = min(text_length / 900, 1.0) * 0.15
    negative_penalty = min(len(support_negative_hits) * 0.15, 0.30)
    taxonomy_penalty = 0.0
    looks_like_catalog = len(extracted) >= 8 and len(job_signal_hits) < 1 and (not company or len(taxonomy_hits) >= 2)
    if looks_like_catalog:
        reasons.append("portal_taxonomy_catalog_detected")
    if not job_signal_hits:
        reasons.append("missing_job_posting_signals")
    if support_negative_hits:
        reasons.append("negative_support_signal")

    hard_invalid = "javascript_source_url" in reasons or "invalid_catalog_title" in reasons or looks_like_catalog
    if hard_invalid:
        taxonomy_penalty = 0.60
    job_probability_score = round(
        min(1.0, max(0.0, title_quality + source_quality + signal_score + semantic_score + text_score - negative_penalty - taxonomy_penalty)),
        4,
    )
    if "empty_company" in reasons and job_probability_score >= PROBABLE_JOB_THRESHOLD:
        reasons = [reason for reason in reasons if reason != "empty_company"]
    if "missing_job_posting_signals" in reasons and (job_probability_score >= PROBABLE_JOB_THRESHOLD or extracted):
        reasons = [reason for reason in reasons if reason != "missing_job_posting_signals"]

    if hard_invalid:
        document_type = "portal_taxonomy"
    elif normalized_title in {"buscar ofertas", "search", "ofertas de trabajo", "ofertas de empleo"} or "ofertas encontradas" in normalized_description:
        document_type = "search_listing"
    elif "filtros" in normalized_title or "filtrar" in normalized_description:
        document_type = "filter_page"
    elif job_probability_score >= PROBABLE_JOB_THRESHOLD:
        document_type = "job_posting"
    else:
        document_type = "unknown"

    is_real = document_type == "job_posting" and job_probability_score >= CURATED_JOB_THRESHOLD and "negative_support_signal" not in reasons
    if job_probability_score >= GOLD_JOB_THRESHOLD:
        curation_level = "gold_job"
    elif job_probability_score >= CURATED_JOB_THRESHOLD:
        curation_level = "curated_job"
    elif job_probability_score >= PROBABLE_JOB_THRESHOLD:
        curation_level = "probable_job"
    else:
        curation_level = "rejected"
    if is_real:
        reasons = []
    acceptance_reasons: list[str] = []
    if extracted:
        acceptance_reasons.append("semantic_skills")
    if job_signal_hits:
        acceptance_reasons.append("job_signals")
    if title_quality >= 0.30:
        acceptance_reasons.append("title_quality")
    if text_score >= 0.08:
        acceptance_reasons.append("text_completeness")
    return {
        "document_type": document_type,
        "is_real_job_posting": is_real,
        "invalid_job_reason": ";".join(reasons),
        "job_signal_hits": job_signal_hits,
        "taxonomy_signal_hits": taxonomy_hits,
        "support_negative_hits": support_negative_hits,
        "job_probability_score": job_probability_score,
        "curation_level": curation_level,
        "semantic_evidence_count": len(extracted),
        "top_acceptance_reasons": acceptance_reasons,
    }


def parse_detail_html(html: str, *, source_name: str, source_url: str, fallback_title: str = "") -> tuple[BronzeEvidence, dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    page_title = compact_text(soup.title.get_text(" ", strip=True) if soup.title else fallback_title)
    raw_text = compact_text(soup.get_text(" ", strip=True))
    title_node = soup.select_one("h1,h2,[class*='title'],[class*='cargo']")
    title = compact_text(title_node.get_text(" ", strip=True) if title_node else fallback_title or page_title)
    company_node = soup.select_one(
        "[class*='company'],[class*='empresa'],[data-testid*='company'],[itemprop*='hiringOrganization'],[class*='employer']"
    )
    location_node = soup.select_one("[class*='location'],[class*='ubicacion'],[class*='ciudad']")
    description_nodes = soup.select("main,article,[class*='description'],[class*='descripcion'],[class*='detalle'],[class*='content']")
    description = compact_text(" ".join(node.get_text(" ", strip=True) for node in description_nodes)) or raw_text
    tags = [compact_text(node.get_text(" ", strip=True)) for node in soup.select("[class*='tag'],[class*='skill'],[class*='badge']")]
    company = compact_text(company_node.get_text(" ", strip=True) if company_node else "")
    if not company:
        company = _company_from_json_ld(soup) or _company_from_metadata(soup) or _company_from_text(raw_text, title)
    payload = {
        "title": title,
        "company": company,
        "location": compact_text(location_node.get_text(" ", strip=True) if location_node else "Colombia"),
        "description": description,
        "tags": tags,
    }
    hsh = content_hash(source_name, source_url, title, description)
    bronze = BronzeEvidence(
        source_name=source_name,
        source_url=source_url,
        raw_html=html,
        raw_text=raw_text,
        raw_json=payload,
        extraction_timestamp=datetime.now(UTC).isoformat(),
        page_title=page_title,
        http_status=None,
        extraction_method="agentic_browser_detail",
        content_hash=hsh,
        detected_language=detect_language(raw_text),
    )
    return bronze, payload


def build_evidence_summary(payload: dict[str, Any], contextual: ContextualRelevanceResult) -> str:
    if contextual.contextual_evidence:
        return contextual.contextual_evidence
    signals = contextual.detected_signals[:8]
    stack = contextual.detected_stack[:8]
    if not signals and not stack:
        return ""
    bullets = [*signals, *[item for item in stack if item not in signals]]
    return (
        "Vacante relevante para Visual Analytics y Big Data porque evidencia: "
        + ", ".join(bullets[:10])
        + "."
    )


def normalize_to_silver(bronze: BronzeEvidence, payload: dict[str, Any]) -> SilverEvidence:
    title = payload.get("title", "")
    description = payload.get("description", "")
    tags = payload.get("tags", [])
    classification = classify_document_type(payload, source_url=bronze.source_url)
    extracted = extract_visual_analytics_skills(f"{title} {description} {' '.join(tags)}")
    can_use_as_job_evidence = (
        classification["curation_level"] in {"probable_job", "curated_job", "gold_job"}
        and classification["document_type"] == "job_posting"
        and "portal_taxonomy_catalog_detected" not in str(classification["invalid_job_reason"])
    )
    job_extracted = extracted if can_use_as_job_evidence else []
    portal_taxonomy_skills = [] if can_use_as_job_evidence else [item.normalized for item in extracted]
    contextual = score_contextual_relevance(
        title=title,
        description=description,
        tags=tags,
        skills=[item.normalized for item in job_extracted],
        technologies=[item.normalized for item in job_extracted],
        document_type=str(classification["document_type"]),
        evidence_source_type="job_evidence" if can_use_as_job_evidence else "portal_taxonomy",
        is_real_job_posting=bool(classification["is_real_job_posting"] or can_use_as_job_evidence),
    )
    tools = [item.normalized for item in job_extracted if item.skill_type == "tool"]
    cloud = [item.normalized for item in job_extracted if item.skill_type == "cloud"]
    frameworks = [item.normalized for item in job_extracted if item.skill_type in {"platform", "framework", "emerging_skill"}]
    evidence_summary = build_evidence_summary(payload, contextual)
    accepted = (
        float(classification["job_probability_score"]) >= GOLD_JOB_THRESHOLD
        and contextual.contextual_relevance_score >= GOLD_CONTEXTUAL_THRESHOLD
        and contextual.analytics_density >= GOLD_ANALYTICS_DENSITY_THRESHOLD
        and contextual.semantic_similarity >= GOLD_SEMANTIC_THRESHOLD
        and bool(evidence_summary)
    )
    if classification["document_type"] != "job_posting" or not can_use_as_job_evidence:
        accepted = False
    if contextual.curriculum_gold_tier in {"Gold A", "Gold B"}:
        accepted = (
            bool(can_use_as_job_evidence)
            and contextual.gold_score >= 0.65
            and contextual.curriculum_alignment_score >= 0.50
            and bool(evidence_summary)
            and not contextual.detected_negative_signals
        )
    if not accepted and contextual.hybrid_tier in {"Gold A", "Gold B"}:
        accepted = (
            bool(can_use_as_job_evidence)
            and contextual.analytics_density >= GOLD_ANALYTICS_DENSITY_THRESHOLD
            and contextual.final_semantic_relevance_score >= 0.65
            and bool(evidence_summary)
            and not contextual.detected_negative_signals
        )
    reason = "accepted_for_gold" if accepted else (str(classification["invalid_job_reason"]) or contextual.decision_reason)
    return SilverEvidence(
        source_name=bronze.source_name,
        source_url=bronze.source_url,
        normalized_title=compact_text(title),
        normalized_company=compact_text(payload.get("company", "")),
        normalized_location=compact_text(payload.get("location", "Colombia")),
        normalized_description=compact_text(description),
        extracted_skills=[item.normalized for item in job_extracted],
        extracted_tools=tools,
        extracted_cloud=cloud,
        extracted_frameworks=frameworks,
        analytics_density=contextual.analytics_density,
        contextual_relevance_score=contextual.contextual_relevance_score,
        semantic_score=contextual.semantic_similarity,
        rejection_reason=reason,
        accepted_for_gold=accepted,
        parser_version="agentic_visual_analytics_v1",
        content_hash=bronze.content_hash,
        contextual={
            **result_to_dict(contextual),
            **classification,
            "job_evidence_skills": [item.normalized for item in job_extracted],
            "portal_taxonomy_skills": portal_taxonomy_skills,
            "evidence_source_type": "job_evidence" if can_use_as_job_evidence else "portal_taxonomy",
            "why_accepted": {
                "job_probability_score": classification["job_probability_score"],
                "accepted_as": classification["curation_level"],
                "top_acceptance_reasons": classification["top_acceptance_reasons"],
            },
        },
        document_type=str(classification["document_type"]),
        evidence_source_type="job_evidence" if can_use_as_job_evidence else "portal_taxonomy",
        is_real_job_posting=bool(classification["is_real_job_posting"]),
        invalid_job_reason=str(classification["invalid_job_reason"]),
        job_evidence_skills=[item.normalized for item in job_extracted],
        portal_taxonomy_skills=portal_taxonomy_skills,
        job_probability_score=float(classification["job_probability_score"]),
        curation_level=str(classification["curation_level"]),
        semantic_evidence_count=int(classification["semantic_evidence_count"]),
        top_acceptance_reasons=list(classification["top_acceptance_reasons"]),
        unknown_skill_candidates=[],
    )


def promote_to_gold(silver: SilverEvidence) -> GoldEvidence | None:
    if not silver.accepted_for_gold:
        return None
    if (
        silver.document_type != "job_posting"
        or not silver.is_real_job_posting
        or not silver.normalized_company
        or not silver.source_url.startswith(("http://", "https://"))
        or silver.invalid_job_reason
        or not (silver.job_evidence_skills or [])
    ):
        return None
    contextual = silver.contextual
    summary = str(contextual.get("contextual_evidence") or "")
    curriculum_explanation = str(contextual.get("curriculum_explanation") or "")
    if curriculum_explanation and curriculum_explanation not in summary:
        summary = f"{summary} {curriculum_explanation}".strip()
    if not summary:
        summary = (
            "Vacante relevante para Visual Analytics porque requiere: "
            + ", ".join((contextual.get("detected_signals") or [])[:8])
            + "."
        )
    if not summary.strip().endswith("."):
        summary += "."
    return GoldEvidence(
        curated_title=silver.normalized_title,
        curated_description=silver.normalized_description,
        evidence_summary=summary,
        normalized_skills=silver.job_evidence_skills or [],
        market_role=str(contextual.get("role_class", "analytics")),
        analytics_relevance=silver.contextual_relevance_score,
        ai_confidence=min(max((silver.contextual_relevance_score + silver.analytics_density + silver.semantic_score) / 3, 0), 1),
        approved_by_agent=True,
        approved_timestamp=datetime.now(UTC).isoformat(),
        source_name=silver.source_name,
        source_url=silver.source_url,
        content_hash=silver.content_hash,
    )


class VisualAnalyticsLaborAgent:
    def __init__(self, *, headless: bool = True, max_jobs: int = 10, navigation_timeout_ms: int = 20000) -> None:
        self.headless = headless
        self.max_jobs = max_jobs
        self.navigation_timeout_ms = navigation_timeout_ms

    def inspect_static_html(self, *, html: str, source_name: str, source_url: str, fallback_title: str = "") -> AgentExtractionResult:
        bronze, payload = parse_detail_html(html, source_name=source_name, source_url=source_url, fallback_title=fallback_title)
        silver = normalize_to_silver(bronze, payload)
        gold = promote_to_gold(silver)
        return AgentExtractionResult(bronze=bronze, silver=silver, gold=gold)

    def run_source(self, *, source_name: str, source_url: str) -> list[AgentExtractionResult]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on optional runtime
            raise RuntimeError("Playwright is required for agentic browser extraction") from exc

        results: list[AgentExtractionResult] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.goto(source_url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
            page.wait_for_timeout(1200)
            html = page.content()
            candidates = extract_candidate_cards(html, source_name=source_name, source_url=source_url, max_jobs=self.max_jobs)
            for candidate in candidates:
                try:
                    page.goto(candidate["url"], wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
                    page.wait_for_timeout(900)
                    detail_html = page.content()
                    results.append(
                        self.inspect_static_html(
                            html=detail_html,
                            source_name=source_name,
                            source_url=candidate["url"],
                            fallback_title=candidate["title"],
                        )
                    )
                except Exception:
                    results.append(
                        self.inspect_static_html(
                            html=f"<html><title>{candidate['title']}</title><body>{candidate['text']}</body></html>",
                            source_name=source_name,
                            source_url=candidate["url"],
                            fallback_title=candidate["title"],
                        )
                    )
            browser.close()
        return results


def evidence_to_dict(result: AgentExtractionResult) -> dict[str, Any]:
    return {
        "bronze": asdict(result.bronze),
        "silver": asdict(result.silver),
        "gold": asdict(result.gold) if result.gold else None,
    }
