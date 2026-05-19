from __future__ import annotations

import argparse
import csv
import importlib
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from scrapers.normalization.classify_domains import classify_text_domain
    from scrapers.normalization.deduplicate_jobs import deduplicate_jobs, job_content_hash
    from scrapers.normalization.normalize_roles import normalize_role
    from scrapers.normalization.normalize_skills import extract_skills_with_rejections
    from scrapers.quality.confidence_score import calculate_confidence_score
    from scrapers.taxonomy.skills_master_loader import load_taxonomy
except ModuleNotFoundError:
    from normalization.classify_domains import classify_text_domain
    from normalization.deduplicate_jobs import deduplicate_jobs, job_content_hash
    from normalization.normalize_roles import normalize_role
    from normalization.normalize_skills import extract_skills_with_rejections
    from quality.confidence_score import calculate_confidence_score
    from taxonomy.skills_master_loader import load_taxonomy


LOGGER = logging.getLogger("jobs_pipeline")

SOURCES = {
    "computrabajo": "scrapers.sources.computrabajo_scraper",
    "elempleo": "scrapers.sources.elempleo_scraper",
    "magneto": "scrapers.sources.magneto_scraper",
    "spe": "scrapers.sources.spe_scraper",
    "torre": "scrapers.sources.torre_scraper",
}


def configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )


def normalize_job(job: dict[str, Any]) -> dict[str, Any]:
    text = f"{job.get('titulo', '')} {job.get('descripcion', '')}"
    domain_classification = classify_text_domain(text)
    domain = job.get("dominio") or domain_classification.primary_domain
    matches, rejected_matches = extract_skills_with_rejections(text, domain_hint=domain)
    normalized = {
        "portal": job.get("portal") or job.get("portal_origen") or "",
        "titulo": job.get("titulo") or "",
        "titulo_normalizado": normalize_role(job.get("titulo") or ""),
        "empresa": job.get("empresa") or "",
        "ciudad": job.get("ciudad") or "",
        "modalidad": job.get("modalidad") or "",
        "salario": job.get("salario") or "",
        "descripcion": job.get("descripcion") or "",
        "seniority": job.get("seniority") or "",
        "sector": job.get("sector") or "",
        "dominio": domain,
        "fecha_publicacion": job.get("fecha_publicacion"),
        "url": job.get("url") or "",
        "embedding": job.get("embedding"),
        "timestamp_extraccion": job.get("timestamp_extraccion") or datetime.now(timezone.utc).isoformat(),
        "skill_matches": matches,
        "rejected_skill_matches": rejected_matches,
        "score_disciplinar": domain_classification.confidence,
        "skills": [match.skill_normalized for match in matches],
        "skills_rechazadas": [match.skill_normalized for match in rejected_matches],
    }
    normalized["hash_contenido"] = job.get("hash_contenido") or job_content_hash(normalized)
    normalized["id"] = f"{normalized['portal']}:{normalized['hash_contenido'][:24]}"
    confidence_score, confidence_factors = calculate_confidence_score(normalized)
    normalized["confidence_score"] = confidence_score
    normalized["confidence_factors"] = confidence_factors
    return normalized


def scrape_sources(source_names: list[str], query: str, location: str, limit: int, headless: bool) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    per_source_limit = max(1, limit // max(1, len(source_names)))
    for source in source_names:
        module_path = SOURCES[source]
        LOGGER.info("scraping source=%s query=%s limit=%s", source, query, per_source_limit)
        module = importlib.import_module(module_path)
        try:
            jobs.extend(module.scrape_jobs(query=query, location=location, limit=per_source_limit, headless=headless))
        except Exception:
            LOGGER.exception("source=%s failed", source)
    return jobs


def read_fixture(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        if path.suffix.lower() == ".json":
            data = json.load(fh)
            return data if isinstance(data, list) else data.get("jobs", [])
        reader = csv.DictReader(fh)
        return list(reader)


def export_csv(jobs: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "portal",
        "titulo",
        "titulo_normalizado",
        "empresa",
        "ciudad",
        "modalidad",
        "salario",
        "seniority",
        "sector",
        "dominio",
        "fecha_publicacion",
        "url",
        "hash_contenido",
        "skills",
        "skills_rechazadas",
        "score_disciplinar",
        "confidence_score",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for job in jobs:
            row = {field: job.get(field, "") for field in fields}
            row["skills"] = "; ".join(job.get("skills", []))
            row["skills_rechazadas"] = "; ".join(job.get("skills_rechazadas", []))
            writer.writerow(row)


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def apply_schema(conn: psycopg2.extensions.connection, schema_path: Path) -> None:
    with schema_path.open("r", encoding="utf-8") as fh, conn.cursor() as cur:
        cur.execute(fh.read())


def upsert_jobs(jobs: list[dict[str, Any]], *, apply_schema_first: bool = True) -> None:
    if not jobs:
        return
    root = Path(__file__).resolve().parents[2]
    with get_connection() as conn:
        if apply_schema_first:
            apply_schema(conn, root / "database" / "enterprise_labor_intelligence_schema.sql")
            conn.commit()
            load_taxonomy()
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO public.empleos (
                    id, portal, titulo, titulo_normalizado, empresa, ciudad, modalidad,
                    salario, descripcion, seniority, sector, dominio, fecha_publicacion,
                    url, hash_contenido, embedding, confidence_score, confidence_factors, created_at
                )
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    portal = EXCLUDED.portal,
                    titulo = EXCLUDED.titulo,
                    titulo_normalizado = EXCLUDED.titulo_normalizado,
                    empresa = EXCLUDED.empresa,
                    ciudad = EXCLUDED.ciudad,
                    modalidad = EXCLUDED.modalidad,
                    salario = EXCLUDED.salario,
                    descripcion = EXCLUDED.descripcion,
                    seniority = EXCLUDED.seniority,
                    sector = EXCLUDED.sector,
                    dominio = EXCLUDED.dominio,
                    fecha_publicacion = EXCLUDED.fecha_publicacion,
                    url = EXCLUDED.url,
                    hash_contenido = EXCLUDED.hash_contenido,
                    embedding = EXCLUDED.embedding,
                    confidence_score = EXCLUDED.confidence_score,
                    confidence_factors = EXCLUDED.confidence_factors
                """,
                [
                    (
                        job["id"],
                        job["portal"],
                        job["titulo"],
                        job["titulo_normalizado"],
                        job["empresa"],
                        job["ciudad"],
                        job["modalidad"],
                        job["salario"],
                        job["descripcion"],
                        job["seniority"],
                        job["sector"],
                        job["dominio"],
                        job["fecha_publicacion"],
                        job["url"],
                        job["hash_contenido"],
                        Json(job["embedding"]) if job.get("embedding") is not None else None,
                        job.get("confidence_score"),
                        Json(job.get("confidence_factors") or {}),
                    )
                    for job in jobs
                ],
            )
            skill_rows = [
                (
                    job["id"],
                    match.skill_original,
                    match.skill_normalized,
                    match.skill_domain,
                    match.tipo_skill,
                    match.confianza_extraccion,
                )
                for job in jobs
                for match in job.get("skill_matches", [])
            ]
            if skill_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO public.empleo_skills (
                        empleo_id, skill_original, skill_normalized, skill_domain,
                        tipo_skill, confianza_extraccion
                    )
                    VALUES %s
                    ON CONFLICT ON CONSTRAINT ux_empleo_skills_job_skill_type
                    DO UPDATE SET
                        skill_original = EXCLUDED.skill_original,
                        skill_domain = EXCLUDED.skill_domain,
                        confianza_extraccion = EXCLUDED.confianza_extraccion
                    """,
                    skill_rows,
                )


def run_pipeline(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.fixture:
        raw_jobs = read_fixture(Path(args.fixture))
    else:
        raw_jobs = scrape_sources(args.sources, args.query, args.location, args.limit, args.headless)
    jobs = deduplicate_jobs([normalize_job(job) for job in raw_jobs])
    export_csv(jobs, Path(args.csv_output))
    if not args.skip_db:
        upsert_jobs(jobs)
    return jobs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enterprise labor jobs extraction and normalization pipeline.")
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCES), default=["spe", "computrabajo", "elempleo"])
    parser.add_argument("--query", default="sostenibilidad ESG eficiencia energetica")
    parser.add_argument("--location", default="Colombia")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fixture", default=None, help="Optional CSV/JSON fixture to normalize instead of live scraping.")
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--csv-output", default="outputs/labor_jobs_normalized.csv")
    parser.add_argument("--log-file", default="logs/jobs_pipeline.log")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(Path(args.log_file))
    jobs = run_pipeline(args)
    LOGGER.info("pipeline finished jobs=%s output=%s", len(jobs), args.csv_output)
    print(json.dumps({"jobs": len(jobs), "csv_output": args.csv_output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
