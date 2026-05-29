from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_conn  # noqa: E402
from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    extract_visual_analytics_skills,
    normalize_text,
)

CONFIG_DIR = ROOT_DIR / "config"
OUTPUT_DIR = ROOT_DIR / "outputs"
RAW_DIR = OUTPUT_DIR / "visual_analytics_labor_raw"
GOLD_THRESHOLD = 0.65
PERSIST_QUALITY_THRESHOLD = 0.70

ROLE_TERMS = {
    "data_analyst": ("analista de datos", "data analyst", "reporting analyst"),
    "bi_analyst": ("analista bi", "bi analyst", "business intelligence analyst"),
    "bi_developer": ("power bi developer", "tableau developer", "desarrollador bi"),
    "data_engineer": ("ingeniero de datos", "data engineer", "analytics engineer"),
    "analytics_consultant": ("consultor bi", "analytics consultant", "data visualization specialist"),
}

RELATED_TERMS = (
    "data",
    "datos",
    "analytics",
    "analitica",
    "bi",
    "business intelligence",
    "visualization",
    "visualizacion",
    "big data",
    "power bi",
    "tableau",
    "sql",
    "python",
    "etl",
    "dashboard",
    "governance",
)

REJECT_TERMS = (
    "curso",
    "diplomado",
    "bootcamp",
    "categoria",
    "blog",
    "publicidad",
    "marketing page",
    "trabajos en",
)


@dataclass(frozen=True)
class LaborSource:
    name: str
    url: str
    country: str
    priority: str
    source_type: str
    access_mode: str
    enabled: bool
    rate_limit_seconds: int
    max_pages: int
    max_jobs: int
    allowed_paths: list[str]
    blocked_reason: str | None = None


@dataclass
class ExtractedJob:
    portal: str
    titulo: str
    empresa: str
    ciudad: str
    modalidad: str
    salario: str
    descripcion: str
    seniority: str
    sector: str
    dominio: str
    fecha_publicacion: str | None
    url: str
    role_class: str
    job_relevance_score: float
    skills: list[str]
    raw: dict[str, Any]

    @property
    def content_hash(self) -> str:
        base = f"{self.portal}|{self.titulo}|{self.empresa}|{self.ciudad}|{self.descripcion}"
        return hashlib.sha256(normalize_text(base).encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_environment() -> None:
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def load_sources(path: Path = CONFIG_DIR / "labor_sources_visual_analytics.yaml") -> list[LaborSource]:
    data = load_yaml(path)
    return [LaborSource(**item) for item in data.get("sources", [])]


def with_runtime_limits(sources: list[LaborSource], *, max_pages: int | None, max_jobs: int | None) -> list[LaborSource]:
    if max_pages is None and max_jobs is None:
        return sources
    limited: list[LaborSource] = []
    for source in sources:
        limited.append(
            LaborSource(
                name=source.name,
                url=source.url,
                country=source.country,
                priority=source.priority,
                source_type=source.source_type,
                access_mode=source.access_mode,
                enabled=source.enabled,
                rate_limit_seconds=source.rate_limit_seconds,
                max_pages=min(source.max_pages, max_pages) if max_pages is not None else source.max_pages,
                max_jobs=min(source.max_jobs, max_jobs) if max_jobs is not None else source.max_jobs,
                allowed_paths=source.allowed_paths,
                blocked_reason=source.blocked_reason,
            )
        )
    return limited


def load_queries(path: Path = CONFIG_DIR / "visual_analytics_job_queries.yaml") -> dict[str, list[str]]:
    data = load_yaml(path)
    return {
        "roles": list(data.get("roles", {}).get("primary", [])),
        "skills": list(data.get("skills", {}).get("technologies", [])),
    }


def classify_role(title: str) -> str:
    text = normalize_text(title)
    for role_class, terms in ROLE_TERMS.items():
        if any(normalize_text(term) in text for term in terms):
            return role_class
    return "analytics_related"


def source_weight(priority: str) -> float:
    normalized = normalize_text(priority)
    if normalized == "alta":
        return 1.0
    if normalized in {"media alta", "media-alta"}:
        return 0.85
    if normalized == "media":
        return 0.70
    return 0.55


def recency_score(value: str | None) -> float:
    if not value:
        return 0.50
    text = normalize_text(value)
    if any(term in text for term in ("hoy", "ayer", "today", "recent", "reciente")):
        return 1.0
    if re.search(r"202[5-6]", text):
        return 0.85
    return 0.55


def calculate_job_relevance_score(job: dict[str, Any], source: LaborSource) -> float:
    title = normalize_text(str(job.get("titulo") or job.get("title") or ""))
    description = normalize_text(str(job.get("descripcion") or job.get("description") or ""))
    skills = [skill.normalized for skill in extract_visual_analytics_skills(f"{title} {description}")]
    title_related = 1.0 if any(term in title for term in RELATED_TERMS) else 0.0
    skill_related = min(len(skills) / 5, 1.0)
    description_related = min(sum(1 for term in RELATED_TERMS if term in description) / 6, 1.0)
    score = (
        title_related * 0.30
        + skill_related * 0.35
        + description_related * 0.20
        + source_weight(source.priority) * 0.10
        + recency_score(str(job.get("fecha_publicacion") or job.get("published_at") or "")) * 0.05
    )
    return round(score, 4)


def should_discard_job(job: dict[str, Any]) -> tuple[bool, str]:
    title = normalize_text(str(job.get("titulo") or job.get("title") or ""))
    description = normalize_text(str(job.get("descripcion") or job.get("description") or ""))
    url = normalize_text(str(job.get("url") or ""))
    if not title:
        return True, "missing_title"
    if not description or len(description) < 80:
        return True, "missing_or_short_description"
    if any(term in f"{title} {description} {url}" for term in REJECT_TERMS):
        return True, "seo_course_or_advertising"
    if not any(term in f"{title} {description}" for term in RELATED_TERMS):
        return True, "outside_visual_analytics_scope"
    location = normalize_text(str(job.get("ciudad") or job.get("location") or ""))
    if location and not any(term in location for term in ("colombia", "bogota", "medellin", "cali", "remoto", "remote", "latam")):
        return True, "outside_colombia_or_remote_latam"
    return False, "accepted"


def parse_job_cards(html: str, source: LaborSource) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("[data-testid*=job], article, .job, .oferta, .card")
    jobs: list[dict[str, Any]] = []
    for card in cards[: source.max_jobs]:
        text = " ".join(card.get_text(" ", strip=True).split())
        if len(text) < 100:
            continue
        link = card.find("a", href=True)
        title_node = card.find(["h1", "h2", "h3", "a"])
        title = title_node.get_text(" ", strip=True) if title_node else text[:90]
        url = link["href"] if link else source.url
        if url.startswith("/"):
            url = source.url.rstrip("/") + url
        jobs.append(
            {
                "titulo": title,
                "empresa": "",
                "ciudad": "Colombia",
                "modalidad": "",
                "salario": "",
                "descripcion": text,
                "fecha_publicacion": "",
                "url": url,
            }
        )
    return jobs


def fetch_source_jobs(source: LaborSource, queries: dict[str, list[str]], *, execute_network: bool) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    if not source.enabled:
        return [], [{"source": source.name, "error_type": "disabled", "error_message": "source_disabled"}]
    if "restricted" in source.access_mode:
        return [], [{"source": source.name, "error_type": "restricted_manual", "error_message": source.blocked_reason or "manual_or_api_fallback_required"}]
    if not execute_network:
        return [], [{"source": source.name, "error_type": "network_not_executed", "error_message": "run_with_execute_network_to_fetch_live_jobs"}]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    jobs: list[dict[str, Any]] = []
    headers = {"User-Agent": "GraduateIntelligenceBot/1.0 controlled pilot contact=academic-research"}
    for page in range(1, source.max_pages + 1):
        try:
            response = requests.get(source.url, headers=headers, timeout=20)
            response.raise_for_status()
            raw_path = RAW_DIR / f"{normalize_text(source.name).replace(' ', '_')}_page_{page}.html"
            raw_path.write_text(response.text, encoding="utf-8")
            jobs.extend(parse_job_cards(response.text, source))
            break
        except Exception as exc:  # pragma: no cover - network failures are environment-dependent
            errors.append({"source": source.name, "error_type": type(exc).__name__, "error_message": str(exc)[:500]})
            time.sleep(source.rate_limit_seconds)
    return jobs[: source.max_jobs], errors


def normalize_job(raw_job: dict[str, Any], source: LaborSource) -> ExtractedJob:
    score = calculate_job_relevance_score(raw_job, source)
    text = f"{raw_job.get('titulo', '')} {raw_job.get('descripcion', '')}"
    skills = [skill.normalized for skill in extract_visual_analytics_skills(text)]
    return ExtractedJob(
        portal=source.name,
        titulo=str(raw_job.get("titulo") or raw_job.get("title") or "").strip(),
        empresa=str(raw_job.get("empresa") or raw_job.get("company") or "").strip(),
        ciudad=str(raw_job.get("ciudad") or raw_job.get("location") or "Colombia").strip(),
        modalidad=str(raw_job.get("modalidad") or raw_job.get("modality") or "").strip(),
        salario=str(raw_job.get("salario") or raw_job.get("salary") or "").strip(),
        descripcion=str(raw_job.get("descripcion") or raw_job.get("description") or "").strip(),
        seniority=str(raw_job.get("seniority") or "").strip(),
        sector="tecnologia_datos_analitica",
        dominio="analitica_visual_big_data",
        fecha_publicacion=str(raw_job.get("fecha_publicacion") or raw_job.get("published_at") or "").strip() or None,
        url=str(raw_job.get("url") or "").strip(),
        role_class=classify_role(str(raw_job.get("titulo") or raw_job.get("title") or "")),
        job_relevance_score=score,
        skills=skills,
        raw=raw_job,
    )


def deduplicate_jobs(jobs: list[ExtractedJob]) -> list[ExtractedJob]:
    seen: set[str] = set()
    unique: list[ExtractedJob] = []
    for job in jobs:
        key = hashlib.sha256(normalize_text(f"{job.portal}|{job.titulo}|{job.empresa}|{job.ciudad}|{job.url}").encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique


def upsert_sources_and_jobs(run_id: str, sources: list[LaborSource], jobs: list[ExtractedJob], errors: list[dict[str, str]]) -> None:
    load_environment()
    migration = ROOT_DIR / "database" / "migrations" / "010_visual_analytics_labor_pilot.sql"
    with get_conn() as conn:
        with conn.cursor() as cur:
            if migration.exists():
                cur.execute(migration.read_text(encoding="utf-8"))
            execute_values(
                cur,
                """
                INSERT INTO labor_market_sources
                    (name, url, country, priority, source_type, access_mode, enabled, rate_limit_seconds, max_pages, max_jobs, allowed_paths, blocked_reason, updated_at)
                VALUES %s
                ON CONFLICT (name) DO UPDATE SET
                    url = EXCLUDED.url,
                    country = EXCLUDED.country,
                    priority = EXCLUDED.priority,
                    source_type = EXCLUDED.source_type,
                    access_mode = EXCLUDED.access_mode,
                    enabled = EXCLUDED.enabled,
                    rate_limit_seconds = EXCLUDED.rate_limit_seconds,
                    max_pages = EXCLUDED.max_pages,
                    max_jobs = EXCLUDED.max_jobs,
                    allowed_paths = EXCLUDED.allowed_paths,
                    blocked_reason = EXCLUDED.blocked_reason,
                    updated_at = NOW()
                """,
                [
                    (
                        source.name,
                        source.url,
                        source.country,
                        source.priority,
                        source.source_type,
                        source.access_mode,
                        source.enabled,
                        source.rate_limit_seconds,
                        source.max_pages,
                        source.max_jobs,
                        json.dumps(source.allowed_paths),
                        source.blocked_reason,
                    )
                    for source in sources
                ],
            )
            cur.execute(
                """
                INSERT INTO labor_extraction_runs (run_id, pilot, status, sources_requested, jobs_extracted, jobs_discarded, gold_jobs, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    finished_at = NOW(),
                    jobs_extracted = EXCLUDED.jobs_extracted,
                    jobs_discarded = EXCLUDED.jobs_discarded,
                    gold_jobs = EXCLUDED.gold_jobs,
                    metadata = EXCLUDED.metadata
                """,
                (
                    run_id,
                    "visual_analytics_big_data",
                    "completed",
                    len(sources),
                    len(jobs),
                    0,
                    len([job for job in jobs if job.job_relevance_score >= GOLD_THRESHOLD]),
                    json.dumps({"threshold": GOLD_THRESHOLD}),
                ),
            )
            if errors:
                execute_values(
                    cur,
                    """
                    INSERT INTO labor_extraction_errors (run_id, source, error_type, error_message)
                    VALUES %s
                    """,
                    [(run_id, item["source"], item["error_type"], item["error_message"]) for item in errors],
                )
            if jobs:
                execute_values(
                    cur,
                    """
                    INSERT INTO empleos
                        (id, portal, titulo, titulo_normalizado, empresa, ciudad, modalidad, salario, descripcion, seniority, sector, dominio,
                         fecha_publicacion, url, hash_contenido, role_class, job_relevance_score, extraction_run_id, gold_publishable, created_at)
                    VALUES %s
                    ON CONFLICT (hash_contenido) DO UPDATE SET
                        job_relevance_score = EXCLUDED.job_relevance_score,
                        role_class = EXCLUDED.role_class,
                        extraction_run_id = EXCLUDED.extraction_run_id,
                        gold_publishable = EXCLUDED.gold_publishable
                    RETURNING id, hash_contenido
                    """,
                    [
                        (
                            f"va_{job.content_hash[:24]}",
                            job.portal,
                            job.titulo,
                            normalize_text(job.titulo),
                            job.empresa,
                            job.ciudad,
                            job.modalidad,
                            job.salario,
                            job.descripcion,
                            job.seniority,
                            job.sector,
                            job.dominio,
                            job.fecha_publicacion,
                            job.url,
                            job.content_hash,
                            job.role_class,
                            job.job_relevance_score,
                            run_id,
                            job.job_relevance_score >= GOLD_THRESHOLD,
                            datetime.now(UTC),
                        )
                        for job in jobs
                    ],
                )
                cur.execute(
                    "SELECT id, hash_contenido FROM empleos WHERE hash_contenido = ANY(%s)",
                    ([job.content_hash for job in jobs],),
                )
                id_by_hash = {row["hash_contenido"]: row["id"] for row in cur.fetchall()}
                skill_rows = []
                for job in jobs:
                    empleo_id = id_by_hash.get(job.content_hash)
                    if not empleo_id:
                        continue
                    for skill in extract_visual_analytics_skills(f"{job.titulo} {job.descripcion}"):
                        skill_rows.append(
                            (
                                empleo_id,
                                skill.original,
                                skill.normalized,
                                "analitica",
                                skill.skill_type,
                                skill.confidence,
                            )
                        )
                if skill_rows:
                    execute_values(
                        cur,
                        """
                        INSERT INTO empleo_skills
                            (empleo_id, skill_original, skill_normalized, skill_domain, tipo_skill, confianza_extraccion)
                        VALUES %s
                        ON CONFLICT ON CONSTRAINT ux_empleo_skills_job_skill_type
                        DO UPDATE SET
                            skill_original = EXCLUDED.skill_original,
                            skill_domain = EXCLUDED.skill_domain,
                            confianza_extraccion = GREATEST(empleo_skills.confianza_extraccion, EXCLUDED.confianza_extraccion)
                        """,
                        skill_rows,
                    )
        conn.commit()


def calculate_quality_score(sources: list[LaborSource], jobs: list[ExtractedJob], discarded: list[dict[str, str]], errors: list[dict[str, str]]) -> float:
    attempted_sources = [source for source in sources if source.enabled and "restricted" not in source.access_mode]
    hard_errors = [error for error in errors if error["error_type"] not in {"restricted_manual", "network_not_executed"}]
    source_success = 1 - min(len(hard_errors) / max(len(attempted_sources), 1), 1)
    accepted = len(jobs)
    total_reviewed = accepted + len(discarded)
    relevance_rate = accepted / total_reviewed if total_reviewed else 0.0
    avg_relevance = sum(job.job_relevance_score for job in jobs) / accepted if accepted else 0.0
    skill_density = sum(len(job.skills) for job in jobs) / max(accepted * 5, 1) if accepted else 0.0
    quality = source_success * 0.20 + relevance_rate * 0.25 + avg_relevance * 0.35 + min(skill_density, 1.0) * 0.20
    return round(quality, 4)


def write_reports(run_id: str, sources: list[LaborSource], jobs: list[ExtractedJob], discarded: list[dict[str, str]], errors: list[dict[str, str]]) -> float:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    skill_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    for job in jobs:
        role_counts[job.role_class] = role_counts.get(job.role_class, 0) + 1
        for skill in job.skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    quality_score = calculate_quality_score(sources, jobs, discarded, errors)
    duplicates = 0
    quality = {
        "run_id": run_id,
        "sources_configured": len(sources),
        "jobs_extracted": len(jobs),
        "jobs_discarded": len(discarded),
        "duplicates": duplicates,
        "gold_jobs": len([job for job in jobs if job.job_relevance_score >= GOLD_THRESHOLD]),
        "quality_score": quality_score,
        "publishable": quality_score >= PERSIST_QUALITY_THRESHOLD,
        "errors": errors,
        "discard_reasons": discarded,
        "top_skills": sorted(skill_counts.items(), key=lambda item: item[1], reverse=True)[:20],
        "top_roles": sorted(role_counts.items(), key=lambda item: item[1], reverse=True)[:20],
    }
    (OUTPUT_DIR / "visual_analytics_labor_quality_report.json").write_text(json.dumps(quality, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Visual Analytics Labor Extraction Report",
        "",
        f"- Run ID: `{run_id}`",
        f"- Fuentes configuradas: {len(sources)}",
        f"- Empleos extraidos: {len(jobs)}",
        f"- Empleos descartados: {len(discarded)}",
        f"- Duplicados suprimidos: {duplicates}",
        f"- Gold jobs validos: {quality['gold_jobs']}",
        f"- Quality score: {quality_score:.4f}",
        f"- Publicable a Gold: {'si' if quality['publishable'] else 'no'}",
        "",
        "## Fuentes",
    ]
    for source in sources:
        lines.append(f"- {source.name}: {source.priority}, {source.access_mode}, enabled={source.enabled}")
    lines.extend(["", "## Skills Mas Frecuentes"])
    lines.extend([f"- {skill}: {count}" for skill, count in quality["top_skills"]] or ["- Sin corrida de red o sin empleos aceptados."])
    lines.extend(["", "## Errores Por Fuente"])
    lines.extend([f"- {item['source']}: {item['error_type']} - {item['error_message']}" for item in errors] or ["- Sin errores registrados."])
    (OUTPUT_DIR / "visual_analytics_labor_extraction_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    review_lines = [
        "# Visual Analytics Live Extraction Review",
        "",
        f"- Run ID: `{run_id}`",
        f"- Quality score: {quality_score:.4f}",
        f"- Umbral de persistencia: {PERSIST_QUALITY_THRESHOLD:.2f}",
        f"- Decision: {'persistir permitido' if quality_score >= PERSIST_QUALITY_THRESHOLD else 'no persistir'}",
        "",
        "## Resumen Por Fuente",
    ]
    for source in sources:
        source_jobs = [job for job in jobs if job.portal == source.name]
        source_discards = [item for item in discarded if item["source"] == source.name]
        source_errors = [item for item in errors if item["source"] == source.name]
        review_lines.extend(
            [
                f"### {source.name}",
                f"- Empleos extraidos aceptados: {len(source_jobs)}",
                f"- Empleos descartados: {len(source_discards)}",
                f"- Errores: {len(source_errors)}",
            ]
        )
        if source_errors:
            review_lines.extend([f"- Error: {item['error_type']} - {item['error_message']}" for item in source_errors[:5]])
        if source_discards:
            reasons: dict[str, int] = {}
            for item in source_discards:
                reasons[item["reason"]] = reasons.get(item["reason"], 0) + 1
            review_lines.extend([f"- Descarte `{reason}`: {count}" for reason, count in sorted(reasons.items())])
    review_lines.extend(["", "## Skills Extraidas"])
    review_lines.extend([f"- {skill}: {count}" for skill, count in quality["top_skills"]] or ["- Sin skills aceptadas."])
    review_lines.extend(["", "## Roles Detectados"])
    review_lines.extend([f"- {role}: {count}" for role, count in quality["top_roles"]] or ["- Sin roles aceptados."])
    (OUTPUT_DIR / "visual_analytics_live_extraction_review.md").write_text("\n".join(review_lines) + "\n", encoding="utf-8")
    return quality_score


def run_pipeline(*, execute_network: bool = False, persist: bool = False, max_jobs: int | None = None, max_pages: int | None = None) -> dict[str, Any]:
    run_id = f"visual-analytics-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    sources = with_runtime_limits(load_sources(), max_pages=max_pages, max_jobs=max_jobs)
    queries = load_queries()
    accepted: list[ExtractedJob] = []
    discarded: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for source in sources:
        raw_jobs, source_errors = fetch_source_jobs(source, queries, execute_network=execute_network)
        errors.extend(source_errors)
        for raw_job in raw_jobs:
            discard, reason = should_discard_job(raw_job)
            if discard:
                discarded.append({"source": source.name, "title": str(raw_job.get("titulo") or raw_job.get("title") or ""), "reason": reason})
                continue
            job = normalize_job(raw_job, source)
            if job.job_relevance_score < GOLD_THRESHOLD:
                discarded.append({"source": source.name, "title": job.titulo, "reason": "below_gold_relevance_threshold"})
                continue
            accepted.append(job)
        if execute_network:
            time.sleep(source.rate_limit_seconds)
    before_dedup = len(accepted)
    jobs = deduplicate_jobs(accepted)
    duplicate_count = before_dedup - len(jobs)
    if duplicate_count:
        discarded.append({"source": "deduplication", "title": "duplicate_jobs", "reason": f"duplicates_suppressed:{duplicate_count}"})
    quality_score = write_reports(run_id, sources, jobs, discarded, errors)
    if persist and quality_score < PERSIST_QUALITY_THRESHOLD:
        errors.append(
            {
                "source": "release_gate",
                "error_type": "quality_gate_blocked",
                "error_message": f"quality_score {quality_score:.4f} below {PERSIST_QUALITY_THRESHOLD:.2f}",
            }
        )
        write_reports(run_id, sources, jobs, discarded, errors)
        return {"run_id": run_id, "quality_score": quality_score, "persisted": False, "jobs": [asdict(job) for job in jobs], "discarded": discarded, "errors": errors}
    if persist:
        upsert_sources_and_jobs(run_id, sources, jobs, errors)
    return {"run_id": run_id, "quality_score": quality_score, "persisted": persist, "jobs": [asdict(job) for job in jobs], "discarded": discarded, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract controlled Visual Analytics labor evidence.")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration and reports without network or persistence.")
    parser.add_argument("--execute-network", action="store_true", help="Fetch live job portals. Disabled by default.")
    parser.add_argument("--persist", action="store_true", help="Persist accepted jobs to PostgreSQL.")
    parser.add_argument("--max-jobs", type=int, default=None, help="Runtime cap per source.")
    parser.add_argument("--max-pages", type=int, default=None, help="Runtime cap per source.")
    args = parser.parse_args()
    result = run_pipeline(
        execute_network=args.execute_network and not args.dry_run,
        persist=args.persist and not args.dry_run,
        max_jobs=args.max_jobs,
        max_pages=args.max_pages,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "jobs"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
