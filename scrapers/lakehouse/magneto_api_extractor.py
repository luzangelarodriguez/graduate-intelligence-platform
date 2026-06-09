from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import psycopg2
import requests
from psycopg2.extras import Json, RealDictCursor, execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.lakehouse.paths import dated_layer_path
from scrapers.lakehouse.relevance import calculate_relevance_scores
from scrapers.normalization.classify_domains import classify_text_domain
from scrapers.normalization.deduplicate_jobs import job_content_hash
from scrapers.normalization.normalize_roles import normalize_role
from scrapers.normalization.normalize_skills import extract_skills_with_rejections


SOURCE = "magneto_api"
BASE_URL = "https://api.magneto365.com"


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
        cursor_factory=RealDictCursor,
    )


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def apply_schema() -> None:
    schema = ROOT_DIR / "database" / "enterprise_labor_intelligence_schema.sql"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(schema.read_text(encoding="utf-8"))


def create_run(run_id: str, query: str, metadata: dict[str, Any]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.extraction_runs (run_id, source, mode, query, status, metadata)
            VALUES (%s, %s, 'api_first', %s, 'started', %s)
            ON CONFLICT (run_id) DO NOTHING
            """,
            (run_id, SOURCE, query, Json(metadata)),
        )


def finish_run(run_id: str, status: str, raw_count: int, silver_count: int, error_count: int) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.extraction_runs
            SET status = %s,
                finished_at = now(),
                raw_count = %s,
                silver_count = %s,
                error_count = %s
            WHERE run_id = %s
            """,
            (status, raw_count, silver_count, error_count, run_id),
        )


def endpoint_candidates(query: str, page: int, page_size: int) -> list[str]:
    encoded = quote_plus(query)
    return [
        # Primary vacancy search endpoints (most likely formats for Magneto365)
        f"{BASE_URL}/jobs/v1/public/vacancies?q={encoded}&country_id=47&page={page}&per_page={page_size}",
        f"{BASE_URL}/jobs/v1/public/search?q={encoded}&country_id=47&page={page}&per_page={page_size}",
        f"{BASE_URL}/jobs/v1/public/vacancies/search?q={encoded}&country_id=47&page={page}&per_page={page_size}",
        # Fallback with search= param
        f"{BASE_URL}/jobs/v1/public/vacancies?search={encoded}&country_id=47&page={page}&per_page={page_size}",
        f"{BASE_URL}/jobs/v1/public/search?search={encoded}&country_id=47&page={page}&per_page={page_size}",
        # Alternative API versions
        f"{BASE_URL}/search/v1/vacancies?q={encoded}&country_id=47&page={page}&per_page={page_size}",
        f"{BASE_URL}/api/v1/jobs?search={encoded}&country_id=47&page={page}&per_page={page_size}",
    ]


def request_json(url: str) -> tuple[int, Any]:
    response = requests.get(
        url,
        timeout=25,
        headers={
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            "Origin": "https://www.magneto365.com",
            "Referer": "https://www.magneto365.com/co/trabajos/buscar",
        },
    )
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        return response.status_code, response.json()
    return response.status_code, {"non_json_response": response.text[:2000], "content_type": content_type}


def persist_bronze_payload(run_id: str, endpoint: str, params: dict[str, Any], status_code: int, payload: Any) -> int | None:
    payload_hash = stable_hash({"endpoint": endpoint, "payload": payload})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.bronze_job_payloads (
                run_id, source, endpoint, request_params, status_code, payload, payload_hash
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (payload_hash) DO UPDATE SET extracted_at = now()
            RETURNING id
            """,
            (run_id, SOURCE, endpoint, Json(params), status_code, Json(payload), payload_hash),
        )
        row = cur.fetchone()
        return int(row["id"]) if row else None


def write_bronze_file(run_id: str, endpoint: str, payload: Any) -> Path:
    path = dated_layer_path("bronze", SOURCE, run_id)
    filename = f"{stable_hash(endpoint)[:12]}.json"
    target = path / filename
    target.write_text(json.dumps({"endpoint": endpoint, "payload": payload}, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


JOB_KEY_HINTS = {
    "title",
    "titulo",
    "name",
    "job_title",
    "vacancy",
    "description",
    "company",
    "salary",
    "city",
    "location",
}

# Keys that belong to SEO/navigation records, not actual job listings
_NAV_ONLY_KEYS = frozenset({
    "_id", "id", "slug", "h1", "counter", "canonical", "ogtitle", "ogdescription",
    "ogimage", "iconurl", "imageurl", "landings", "type", "field", "slugifylabel", "label",
})


def looks_like_job_record(item: dict[str, Any]) -> bool:
    keys = {str(key).casefold() for key in item.keys()}
    # Exclude pure navigation/SEO records (no content beyond slug/counter/h1)
    if keys <= _NAV_ONLY_KEYS:
        return False
    text = json.dumps(item, ensure_ascii=False).casefold()
    if "mega-menu" in text or "canonical" in keys and "h1" in keys and "ogtitle" in keys:
        return False
    if len(keys & JOB_KEY_HINTS) >= 3:
        return True
    # Require "empresa" to appear as a field value, not just embedded in a URL slug.
    # Check that "empresa" appears outside of _id/slug values.
    empresa_in_content = any(
        "empresa" in json.dumps(v, ensure_ascii=False, default=str).casefold()
        for k, v in item.items()
        if str(k).casefold() not in {"_id", "id", "slug", "canonical"}
    )
    return ("vacante" in text or "empleo" in text or "salary" in text) and empresa_in_content


def find_job_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                if looks_like_job_record(item):
                    records.append(item)
                records.extend(find_job_records(item))
    elif isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and looks_like_job_record(item):
                        records.append(item)
            if isinstance(value, (dict, list)):
                records.extend(find_job_records(value))
    deduped: dict[str, dict[str, Any]] = {}
    for record in records:
        deduped.setdefault(stable_hash(record), record)
    return list(deduped.values())


def pick(record: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).casefold(): value for key, value in record.items()}
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
        value = lowered.get(key.casefold())
        if value not in (None, ""):
            return value
    return ""


def nested_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return " ".join(nested_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(nested_text(item) for item in value)
    return str(value)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def normalize_record(record: dict[str, Any], run_id: str, bronze_payload_id: int | None) -> dict[str, Any]:
    title = nested_text(pick(record, "title", "titulo", "name", "job_title", "position", "cargo"))
    company = nested_text(pick(record, "company", "empresa", "brand", "organization"))
    location = nested_text(pick(record, "city", "ciudad", "location", "locations", "department"))
    description = nested_text(pick(record, "description", "descripcion", "summary", "requirements", "functions", "responsibilities"))
    url_value = nested_text(pick(record, "url", "link", "slug", "canonical"))
    if url_value and not url_value.startswith("http"):
        url_value = f"https://www.magneto365.com/co/trabajos/{url_value.strip('/')}"
    text = f"{title} {description} {nested_text(record)}"
    domain_classification = classify_text_domain(text)
    matches, rejected = extract_skills_with_rejections(text, domain_hint=domain_classification.primary_domain)
    job = {
        "id": f"magneto_api:{stable_hash(record)[:24]}",
        "run_id": run_id,
        "bronze_payload_id": bronze_payload_id,
        "source": SOURCE,
        "portal": SOURCE,
        "titulo": title,
        "titulo_normalizado": normalize_role(title),
        "empresa": company,
        "ciudad": location,
        "modalidad": nested_text(pick(record, "modality", "modalidad", "workMode", "work_mode")),
        "salario": nested_text(pick(record, "salary", "salario", "salaryRange", "compensation")),
        "descripcion": description,
        "seniority": nested_text(pick(record, "seniority", "experience", "experienceLevel")),
        "sector": nested_text(pick(record, "sector", "industry", "category")),
        "dominio": domain_classification.primary_domain,
        "fecha_publicacion": parse_date(nested_text(pick(record, "published_at", "publicationDate", "created_at", "date"))),
        "url": url_value,
        "skills": [match.skill_normalized for match in matches],
        "skills_rechazadas": [match.skill_normalized for match in rejected],
        "metadata": record,
    }
    job["hash_contenido"] = job_content_hash(job)
    scores = calculate_relevance_scores(job)
    job["relevance_scores"] = scores
    return job


def is_real_job_evidence(job: dict[str, Any]) -> bool:
    title = (job.get("titulo") or "").strip().casefold()
    url = (job.get("url") or "").casefold()
    description_words = len((job.get("descripcion") or "").split())
    if not title:
        return False
    if title.startswith("trabajos en ") or title.startswith("empleos en "):
        return False
    if "ofertas-empleo-de-" in url or "/trabajos/trabajos-" in url:
        return False
    evidence_points = 0
    if job.get("empresa"):
        evidence_points += 1
    if description_words >= 25:
        evidence_points += 1
    if job.get("salario") or job.get("fecha_publicacion"):
        evidence_points += 1
    if job.get("skills"):
        evidence_points += 1
    if "/empleos/" in url or "/trabajos/" in url:
        evidence_points += 1
    return evidence_points >= 2


def persist_silver_jobs(jobs: list[dict[str, Any]]) -> None:
    if not jobs:
        return
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.silver_normalized_jobs (
                id, run_id, bronze_payload_id, source, titulo, titulo_normalizado,
                empresa, ciudad, modalidad, salario, descripcion, seniority, sector,
                dominio, fecha_publicacion, url, skills, metadata, hash_contenido,
                confidence_score
            )
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                run_id = EXCLUDED.run_id,
                bronze_payload_id = EXCLUDED.bronze_payload_id,
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
                skills = EXCLUDED.skills,
                metadata = EXCLUDED.metadata,
                hash_contenido = EXCLUDED.hash_contenido,
                confidence_score = EXCLUDED.confidence_score
            """,
            [
                (
                    job["id"],
                    job["run_id"],
                    job["bronze_payload_id"],
                    job["source"],
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
                    Json(job["skills"]),
                    Json(job["metadata"]),
                    job["hash_contenido"],
                    job["relevance_scores"]["overall_score"],
                )
                for job in jobs
            ],
        )
        execute_values(
            cur,
            """
            INSERT INTO public.relevance_scores (
                job_id, run_id, source_weight, evidence_weight, domain_confidence,
                semantic_density, overall_score, factors
            )
            VALUES %s
            ON CONFLICT (job_id, run_id) DO UPDATE SET
                source_weight = EXCLUDED.source_weight,
                evidence_weight = EXCLUDED.evidence_weight,
                domain_confidence = EXCLUDED.domain_confidence,
                semantic_density = EXCLUDED.semantic_density,
                overall_score = EXCLUDED.overall_score,
                factors = EXCLUDED.factors
            """,
            [
                (
                    job["id"],
                    job["run_id"],
                    job["relevance_scores"]["source_weight"],
                    job["relevance_scores"]["evidence_weight"],
                    job["relevance_scores"]["domain_confidence"],
                    job["relevance_scores"]["semantic_density"],
                    job["relevance_scores"]["overall_score"],
                    Json(job["relevance_scores"]),
                )
                for job in jobs
            ],
        )


def write_silver_files(run_id: str, jobs: list[dict[str, Any]]) -> None:
    path = dated_layer_path("silver", SOURCE, run_id)
    (path / "normalized_jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    with (path / "normalized_jobs.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = ["id", "titulo", "empresa", "ciudad", "modalidad", "dominio", "url", "skills", "overall_score"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for job in jobs:
            writer.writerow({
                "id": job["id"],
                "titulo": job["titulo"],
                "empresa": job["empresa"],
                "ciudad": job["ciudad"],
                "modalidad": job["modalidad"],
                "dominio": job["dominio"],
                "url": job["url"],
                "skills": "; ".join(job["skills"]),
                "overall_score": job["relevance_scores"]["overall_score"],
            })


def extract(query: str, *, pages: int, page_size: int, dry_run: bool = False) -> dict[str, Any]:
    apply_schema()
    run_id = f"magneto_api_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    create_run(run_id, query, {"pages": pages, "page_size": page_size})
    raw_count = 0
    error_count = 0
    normalized_jobs: list[dict[str, Any]] = []
    try:
        for page in range(1, pages + 1):
            for endpoint in endpoint_candidates(query, page, page_size):
                status_code, payload = request_json(endpoint)
                write_bronze_file(run_id, endpoint, payload)
                bronze_id = None if dry_run else persist_bronze_payload(run_id, endpoint, {"query": query, "page": page}, status_code, payload)
                if status_code >= 400:
                    error_count += 1
                    continue
                records = find_job_records(payload)
                raw_count += len(records)
                for record in records:
                    job = normalize_record(record, run_id, bronze_id)
                    if is_real_job_evidence(job):
                        normalized_jobs.append(job)
        deduped = {job["id"]: job for job in normalized_jobs}
        normalized_jobs = list(deduped.values())
        write_silver_files(run_id, normalized_jobs)
        if not dry_run:
            persist_silver_jobs(normalized_jobs)
        finish_run(run_id, "completed", raw_count, len(normalized_jobs), error_count)
        return {
            "run_id": run_id,
            "query": query,
            "raw_count": raw_count,
            "silver_count": len(normalized_jobs),
            "error_count": error_count,
            "bronze_dir": str(dated_layer_path("bronze", SOURCE, run_id)),
            "silver_dir": str(dated_layer_path("silver", SOURCE, run_id)),
            "jobs": normalized_jobs,
        }
    except Exception:
        finish_run(run_id, "failed", raw_count, len(normalized_jobs), error_count + 1)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="API-first Magneto labor extraction into Bronze/Silver lakehouse layers.")
    parser.add_argument("--query", default="analista de datos")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(extract(args.query, pages=args.pages, page_size=args.page_size, dry_run=args.dry_run), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
