from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    extract_visual_analytics_skills,
    normalize_text,
)

VISUAL_ANALYTICS_TERMS = (
    "visual analytics",
    "visualizacion",
    "visualización",
    "business intelligence",
    "inteligencia de negocios",
    "analitica",
    "analítica",
    "analytics",
    "big data",
    "power bi",
    "tableau",
    "sql",
    "python",
    "data engineer",
    "ingeniero de datos",
    "data analyst",
    "analista de datos",
    "bi analyst",
    "analista bi",
    "etl",
    "dashboard",
    "cloud data",
)

IRRELEVANT_TERMS = (
    "helpdesk",
    "mesa de ayuda",
    "soporte tecnico",
    "soporte técnico",
    "service desk",
    "tecnico de soporte",
    "técnico de soporte",
    "call center",
)


@dataclass(frozen=True)
class ConnectorConfig:
    source_name: str
    base_url: str
    priority: str
    max_pages: int = 2
    max_jobs: int = 50
    rate_limit_seconds: int = 4


@dataclass
class ConnectorJob:
    title: str
    company: str
    location: str
    publication_date: str
    description: str
    tags: list[str]
    skills: list[str]
    technologies: list[str]
    seniority: str
    modality: str
    salary: str
    source_url: str
    source_name: str
    raw: dict[str, Any]

    @property
    def content_hash(self) -> str:
        base = f"{self.source_name}|{self.title}|{self.company}|{self.location}|{self.description}|{self.source_url}"
        return hashlib.sha256(normalize_text(base).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["content_hash"] = self.content_hash
        return data


class BaseJobConnector:
    source_name = "base"
    base_url = ""
    priority = "media"

    def __init__(self, *, max_pages: int = 2, max_jobs: int = 50, rate_limit_seconds: int = 4) -> None:
        self.config = ConnectorConfig(
            source_name=self.source_name,
            base_url=self.base_url,
            priority=self.priority,
            max_pages=max_pages,
            max_jobs=max_jobs,
            rate_limit_seconds=rate_limit_seconds,
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 GraduateIntelligence/1.0 controlled-academic-pilot",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.7",
            }
        )

    def search_urls(self) -> list[str]:
        return [self.base_url]

    def search_items(self) -> list[tuple[str, dict[str, Any]]]:
        return [(url, {}) for url in self.search_urls()]

    def fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=25)
        response.raise_for_status()
        return response.text

    def extract_from_html(self, html: str, url: str) -> list[ConnectorJob]:
        raise NotImplementedError

    def fetch_jobs(self, *, execute_network: bool = False) -> tuple[list[ConnectorJob], list[dict[str, str]]]:
        if not execute_network:
            return [], [{"source": self.source_name, "error_type": "dry_run", "error_message": "network_not_executed"}]
        jobs: list[ConnectorJob] = []
        errors: list[dict[str, str]] = []
        for url, search_context in self.search_items()[: self.config.max_pages]:
            try:
                html = self.fetch_html(url)
                page_jobs = self.extract_from_html(html, url)
                for job in page_jobs:
                    if search_context:
                        raw = dict(job.raw or {})
                        raw.setdefault("search_context", search_context)
                        job.raw = raw
                jobs.extend(page_jobs)
            except Exception as exc:  # pragma: no cover - network behavior changes by source
                errors.append({"source": self.source_name, "error_type": type(exc).__name__, "error_message": str(exc)[:500]})
            if len(jobs) >= self.config.max_jobs:
                break
            time.sleep(self.config.rate_limit_seconds)
        return deduplicate_jobs(jobs)[: self.config.max_jobs], errors


def compact_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def absolute_url(base_url: str, href: str | None) -> str:
    if not href:
        return base_url
    return urljoin(base_url, href)


def parse_json_ld_jobs(html: str, source_name: str, base_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    payloads: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.get_text(strip=True))
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            graph = item.get("@graph", []) if isinstance(item, dict) else []
            candidates = graph if graph else [item]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                if candidate.get("@type") not in {"JobPosting", "JobPostingSchema"}:
                    continue
                payloads.append(
                    {
                        "title": candidate.get("title", ""),
                        "company": (candidate.get("hiringOrganization") or {}).get("name", ""),
                        "location": json.dumps(candidate.get("jobLocation", ""), ensure_ascii=False),
                        "publication_date": candidate.get("datePosted", ""),
                        "description": BeautifulSoup(candidate.get("description", ""), "html.parser").get_text(" ", strip=True),
                        "source_url": candidate.get("url") or base_url,
                        "source_name": source_name,
                    }
                )
    return payloads


def build_job(
    *,
    source_name: str,
    base_url: str,
    title: str,
    company: str = "",
    location: str = "Colombia",
    publication_date: str = "",
    description: str = "",
    tags: Iterable[str] = (),
    seniority: str = "",
    modality: str = "",
    salary: str = "",
    source_url: str = "",
    raw: dict[str, Any] | None = None,
) -> ConnectorJob:
    full_text = f"{title} {description} {' '.join(tags)}"
    extracted = extract_visual_analytics_skills(full_text)
    skills = [item.normalized for item in extracted]
    technologies = [item.normalized for item in extracted if item.skill_type in {"tool", "platform", "cloud", "language", "emerging_skill"}]
    return ConnectorJob(
        title=compact_text(title),
        company=compact_text(company),
        location=compact_text(location) or "Colombia",
        publication_date=compact_text(publication_date),
        description=compact_text(description),
        tags=[compact_text(tag) for tag in tags if compact_text(tag)],
        skills=skills,
        technologies=technologies,
        seniority=compact_text(seniority),
        modality=compact_text(modality),
        salary=compact_text(salary),
        source_url=absolute_url(base_url, source_url),
        source_name=source_name,
        raw=raw or {},
    )


def deduplicate_jobs(jobs: Iterable[ConnectorJob]) -> list[ConnectorJob]:
    seen: set[str] = set()
    unique: list[ConnectorJob] = []
    for job in jobs:
        if job.content_hash in seen:
            continue
        seen.add(job.content_hash)
        unique.append(job)
    return unique


def is_visual_analytics_related(job: ConnectorJob) -> tuple[bool, str]:
    text = normalize_text(f"{job.title} {job.description} {' '.join(job.tags)} {' '.join(job.skills)}")
    irrelevant_hits = [term for term in IRRELEVANT_TERMS if normalize_text(term) in text]
    relevant_hits = [term for term in VISUAL_ANALYTICS_TERMS if normalize_text(term) in text]
    if irrelevant_hits and len(relevant_hits) < 2:
        return False, "irrelevant_support_helpdesk"
    if not job.title:
        return False, "missing_title"
    if len(normalize_text(job.description)) < 80:
        return False, "missing_or_short_description"
    if not relevant_hits:
        return False, "outside_visual_analytics_scope"
    return True, "accepted"


def job_relevance_score(job: ConnectorJob, *, source_priority: str = "media") -> float:
    text = normalize_text(f"{job.title} {job.description} {' '.join(job.tags)}")
    title_hits = sum(1 for term in VISUAL_ANALYTICS_TERMS if normalize_text(term) in normalize_text(job.title))
    description_hits = sum(1 for term in VISUAL_ANALYTICS_TERMS if normalize_text(term) in text)
    skill_density = min(len(job.skills) / 5, 1.0)
    priority_score = 1.0 if source_priority == "alta" else 0.85 if "media" in source_priority else 0.70
    recency = 0.75 if job.publication_date else 0.50
    score = min(title_hits, 2) / 2 * 0.30 + skill_density * 0.35 + min(description_hits, 6) / 6 * 0.20 + priority_score * 0.10 + recency * 0.05
    return round(score, 4)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()
