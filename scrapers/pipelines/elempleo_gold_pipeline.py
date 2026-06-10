from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import psycopg2
import requests
from psycopg2.extras import Json, RealDictCursor, execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional local convenience
    load_dotenv = None

from scrapers.lakehouse.paths import dated_layer_path
from scrapers.lakehouse.relevance import calculate_relevance_scores
from scrapers.normalization.classify_domains import classify_text_domain
from scrapers.normalization.deduplicate_jobs import are_probable_duplicates, job_content_hash, title_company_key
from scrapers.normalization.normalize_roles import normalize_role
from scrapers.normalization.normalize_skills import extract_skills_with_rejections
from scrapers.taxonomy.domain_taxonomy import normalize_text


SOURCE = "elempleo"
MODE = "gold_pipeline"
BASE_URL = "https://www.elempleo.com"
LISTING_URL = f"{BASE_URL}/co/ofertas-empleo/trabajo-{{query}}"
FIND_ENDPOINT = f"{BASE_URL}/co/api/joboffers/findbyfilter"
DETAIL_ENDPOINT = f"{BASE_URL}/co/api/joboffers/getjoboffer"


def get_connection() -> psycopg2.extensions.connection:
    if load_dotenv:
        load_dotenv(ROOT_DIR / ".env.local")
    url = os.getenv("RAILWAY_DATABASE_URL")
    if url:
        return psycopg2.connect(url, sslmode="require", cursor_factory=RealDictCursor)
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


def text_hash(value: str) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def apply_schema() -> None:
    schema = ROOT_DIR / "database" / "enterprise_labor_intelligence_schema.sql"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(schema.read_text(encoding="utf-8"))


def create_run(run_id: str, query: str, metadata: dict[str, Any]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.extraction_runs (run_id, source, mode, query, status, metadata)
            VALUES (%s, %s, %s, %s, 'started', %s)
            ON CONFLICT (run_id) DO NOTHING
            """,
            (run_id, SOURCE, MODE, query, Json(metadata)),
        )


def finish_run(run_id: str, status: str, raw_count: int, silver_count: int, gold_count: int, error_count: int) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.extraction_runs
            SET status = %s,
                finished_at = now(),
                raw_count = %s,
                silver_count = %s,
                gold_count = %s,
                error_count = %s
            WHERE run_id = %s
            """,
            (status, raw_count, silver_count, gold_count, error_count, run_id),
        )


def mark_registry_auth_required(endpoint: str, method: str, status_code: int) -> None:
    if status_code not in {401, 403}:
        return
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.api_sources_registry (
                source, endpoint, method, response_type, confidence, auth_required, rank_score, ranking_factors
            )
            VALUES (%s, %s, %s, 'json', 0.92, true, 0.0, %s)
            ON CONFLICT (source, endpoint, method) DO UPDATE SET
                auth_required = true,
                last_seen_at = now(),
                ranking_factors = EXCLUDED.ranking_factors
            """,
            (SOURCE, endpoint, method, Json({"last_status_code": status_code, "pipeline": MODE})),
        )


def default_headers(referer: str) -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": BASE_URL,
        "Referer": referer,
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
    }


def extract_tokens(html: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    patterns = {
        "RequestVerificationToken": r'name="__RequestVerificationToken"\s+type="hidden"\s+value="([^"]+)"',
        "X-CSRF-TOKEN": r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']',
        "Authorization": r'(?:Bearer\s+|access_token["\']?\s*[:=]\s*["\'])([A-Za-z0-9._\-]+)',
    }
    for header, pattern in patterns.items():
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1)
        tokens[header] = f"Bearer {value}" if header == "Authorization" and not value.lower().startswith("bearer") else value
    return tokens


def bootstrap_session(query: str) -> tuple[requests.Session, str, dict[str, str]]:
    session = requests.Session()
    referer = LISTING_URL.format(query=quote_plus(query))
    headers = default_headers(referer)
    try:
        response = session.get(referer, timeout=30, headers=headers)
        if response.ok:
            headers.update(extract_tokens(response.text))
    except requests.RequestException:
        pass
    return session, referer, headers


def find_payload_variants(query: str, page: int, page_size: int) -> list[dict[str, Any]]:
    return [
        {"keyword": query, "page": page, "pageSize": page_size},
        {"Keyword": query, "Page": page, "PageSize": page_size},
        {"searchText": query, "page": page, "rows": page_size},
        {"filter": {"keyword": query, "text": query}, "page": page, "pageSize": page_size},
        {"filtros": {"trabajo": query}, "pagina": page, "tamanoPagina": page_size},
    ]


def detail_payload_variants(job_id: str | int) -> list[dict[str, Any]]:
    return [
        {"id": job_id},
        {"jobOfferId": job_id},
        {"offerId": job_id},
        {"codigo": job_id},
        {"idOferta": job_id},
    ]


def request_json(
    session: requests.Session,
    endpoint: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> tuple[int, Any]:
    try:
        response = session.post(endpoint, json=payload, headers=headers, timeout=35)
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.status_code, response.json()
        return response.status_code, {
            "non_json_response": response.text[:2500],
            "content_type": content_type,
        }
    except requests.RequestException as exc:
        return 0, {"request_error": str(exc)}


def persist_bronze_payload(
    run_id: str,
    endpoint: str,
    params: dict[str, Any],
    status_code: int,
    payload: Any,
) -> int | None:
    payload_hash = stable_hash({"endpoint": endpoint, "params": params, "payload": payload})
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


def write_layer_file(layer: str, run_id: str, filename: str, payload: Any) -> Path:
    path = dated_layer_path(layer, SOURCE, run_id)
    target = path / filename
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return target


JOB_HINTS = {
    "title",
    "titulo",
    "cargo",
    "jobtitle",
    "nombrecargo",
    "company",
    "empresa",
    "descripcion",
    "description",
    "ciudad",
    "city",
    "salary",
    "salario",
}


def looks_like_job_record(item: dict[str, Any]) -> bool:
    keys = {normalize_text(str(key)).replace(" ", "") for key in item.keys()}
    text = normalize_text(json.dumps(item, ensure_ascii=False))
    if len(keys & JOB_HINTS) >= 3:
        return True
    return ("oferta" in text or "vacante" in text or "cargo" in text) and ("empresa" in text or "company" in text)


def find_job_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                if looks_like_job_record(item):
                    records.append(item)
                records.extend(find_job_records(item))
    elif isinstance(payload, dict):
        if looks_like_job_record(payload):
            records.append(payload)
        for value in payload.values():
            if isinstance(value, (dict, list)):
                records.extend(find_job_records(value))
    deduped: dict[str, dict[str, Any]] = {}
    for record in records:
        deduped.setdefault(stable_hash(record), record)
    return list(deduped.values())


def pick(record: dict[str, Any], *keys: str) -> Any:
    lowered = {normalize_text(str(key)).replace(" ", ""): value for key, value in record.items()}
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
        value = lowered.get(normalize_text(key).replace(" ", ""))
        if value not in (None, ""):
            return value
    return ""


def nested_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"<[^>]+>", " ", value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return " ".join(nested_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(nested_text(item) for item in value)
    return str(value)


def parse_date(value: Any) -> date | None:
    text = nested_text(value).strip()[:10]
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def source_job_id(record: dict[str, Any]) -> str:
    value = pick(record, "id", "jobOfferId", "offerId", "codigo", "idOferta", "ofertaId", "code")
    return nested_text(value).strip()


def normalize_record(record: dict[str, Any], run_id: str, bronze_payload_id: int | None, endpoint: str) -> dict[str, Any]:
    title = nested_text(pick(record, "role_title", "title", "titulo", "cargo", "nombreCargo", "jobTitle"))
    company = nested_text(pick(record, "company", "empresa", "nombreEmpresa", "companyName"))
    location = nested_text(pick(record, "location", "ciudad", "city", "municipio", "departamento"))
    modality = nested_text(pick(record, "modality", "modalidad", "tipoTrabajo", "workMode"))
    salary = nested_text(pick(record, "salary", "salario", "rangoSalarial"))
    seniority = nested_text(pick(record, "seniority", "experiencia", "nivel", "experience"))
    sector = nested_text(pick(record, "sector", "industria", "area"))
    description = nested_text(
        pick(record, "description", "descripcion", "descripcionOferta", "detalle", "requirements", "funciones")
    )
    url = nested_text(pick(record, "url", "urlDetalle", "link", "slug"))
    if url and not url.startswith("http"):
        url = f"{BASE_URL}/{url.strip('/')}"
    evidence_text = f"{title} {company} {location} {modality} {seniority} {sector} {description} {nested_text(record)}"
    domain = classify_text_domain(evidence_text)
    accepted, rejected = extract_skills_with_rejections(evidence_text, domain_hint=domain.primary_domain)
    title_location_hash = hashlib.sha256(
        "|".join(normalize_text(str(value)) for value in (title, company, location)).encode("utf-8")
    ).hexdigest()
    job = {
        "id": f"elempleo:{title_location_hash[:24]}",
        "run_id": run_id,
        "bronze_payload_id": bronze_payload_id,
        "source": SOURCE,
        "source_job_id": source_job_id(record),
        "api_endpoint": endpoint,
        "titulo": title,
        "titulo_normalizado": normalize_role(title),
        "empresa": company,
        "ciudad": location,
        "modalidad": modality,
        "salario": salary,
        "descripcion": description,
        "seniority": seniority,
        "sector": sector,
        "dominio": domain.primary_domain,
        "domain_evidence": list(domain.evidence),
        "fecha_publicacion": parse_date(pick(record, "fechaPublicacion", "publishedAt", "publicationDate", "fecha")),
        "url": url,
        "skills": [match.skill_normalized for match in accepted],
        "skills_detail": [asdict(match) for match in accepted],
        "skills_rechazadas": [asdict(match) for match in rejected],
        "evidence_text": evidence_text,
        "metadata": record,
    }
    job["hash_contenido"] = job_content_hash(job)
    job["title_company_location_hash"] = title_location_hash
    job["semantic_hash"] = text_hash(evidence_text[:4000])
    job["relevance_scores"] = calculate_relevance_scores(job)
    return job


def has_real_evidence(job: dict[str, Any]) -> bool:
    if not job.get("titulo"):
        return False
    evidence_points = 0
    evidence_points += 1 if job.get("empresa") else 0
    evidence_points += 1 if job.get("ciudad") or job.get("modalidad") else 0
    evidence_points += 1 if len(normalize_text(job.get("descripcion") or "").split()) >= 25 else 0
    evidence_points += 1 if job.get("skills") else 0
    evidence_points += 1 if job.get("url") or job.get("source_job_id") else 0
    return evidence_points >= 2


def deduplicate_semantically(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for job in jobs:
        key = job["title_company_location_hash"]
        if key in seen_hashes:
            continue
        duplicate = False
        for existing in unique:
            if are_probable_duplicates(job, existing):
                duplicate = True
                break
            ratio = SequenceMatcher(None, normalize_text(job["evidence_text"]), normalize_text(existing["evidence_text"])).ratio()
            if ratio >= 0.94:
                duplicate = True
                break
        if duplicate:
            continue
        seen_hashes.add(key)
        unique.append(job)
    return unique


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
                    Json({**job["metadata"], "skills_detail": job["skills_detail"], "skills_rechazadas": job["skills_rechazadas"]}),
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


def publish_canonical_and_gold(jobs: list[dict[str, Any]], *, auto_validate: bool, min_relevance: float) -> int:
    if not jobs:
        return 0
    publishable = gold_publishable_jobs(jobs, min_relevance=min_relevance)
    if not publishable:
        return 0
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.canonical_jobs (
                id, source, source_job_id, run_id, silver_job_id, role_title, canonical_role,
                domain, seniority, modality, salary, location, company, skills,
                evidence_text, source_url, title_company_location_hash, semantic_hash,
                relevance_score, active, snapshot_date, metadata
            )
            VALUES %s
            ON CONFLICT (source, title_company_location_hash) DO UPDATE SET
                run_id = EXCLUDED.run_id,
                silver_job_id = EXCLUDED.silver_job_id,
                role_title = EXCLUDED.role_title,
                canonical_role = EXCLUDED.canonical_role,
                domain = EXCLUDED.domain,
                seniority = EXCLUDED.seniority,
                modality = EXCLUDED.modality,
                salary = EXCLUDED.salary,
                location = EXCLUDED.location,
                company = EXCLUDED.company,
                skills = EXCLUDED.skills,
                evidence_text = EXCLUDED.evidence_text,
                source_url = EXCLUDED.source_url,
                semantic_hash = EXCLUDED.semantic_hash,
                relevance_score = EXCLUDED.relevance_score,
                active = true,
                last_seen_at = now(),
                snapshot_date = CURRENT_DATE,
                metadata = EXCLUDED.metadata
            """,
            [
                (
                    job["id"],
                    SOURCE,
                    job["source_job_id"],
                    job["run_id"],
                    job["id"],
                    job["titulo"],
                    job["titulo_normalizado"],
                    job["dominio"],
                    job["seniority"],
                    job["modalidad"],
                    job["salario"],
                    job["ciudad"],
                    job["empresa"],
                    Json(job["skills"]),
                    job["evidence_text"],
                    job["url"],
                    job["title_company_location_hash"],
                    job["semantic_hash"],
                    job["relevance_scores"]["overall_score"],
                    True,
                    date.today(),
                    Json({"api_endpoint": job["api_endpoint"], "domain_evidence": job["domain_evidence"]}),
                )
                for job in publishable
            ],
        )
        execute_values(
            cur,
            """
            INSERT INTO public.gold_validated_jobs (
                silver_job_id, dominio, validado, reviewer, observaciones, evidence_grade
            )
            VALUES %s
            ON CONFLICT (silver_job_id, dominio) DO UPDATE SET
                validado = EXCLUDED.validado,
                reviewer = EXCLUDED.reviewer,
                observaciones = EXCLUDED.observaciones,
                evidence_grade = EXCLUDED.evidence_grade,
                fecha = now()
            """,
            [
                (
                    job["id"],
                    job["dominio"],
                    auto_validate,
                    "elempleo_gold_pipeline" if auto_validate else "pending",
                    "API-first El Empleo evidence; pending human review" if not auto_validate else "Auto-validated by relevance gate",
                    "gold" if auto_validate else "candidate",
                )
                for job in publishable
            ],
        )
    return len(publishable)


def gold_publishable_jobs(jobs: list[dict[str, Any]], *, min_relevance: float) -> list[dict[str, Any]]:
    return [job for job in jobs if float(job.get("relevance_scores", {}).get("overall_score") or 0) >= min_relevance]


def persist_lineage(jobs: list[dict[str, Any]], kpi_name: str = "labor_intelligence_evidence") -> None:
    if not jobs:
        return
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.source_lineage (
                kpi_name, canonical_job_id, silver_job_id, bronze_payload_id, run_id,
                source, api_endpoint, lineage_path
            )
            VALUES %s
            """,
            [
                (
                    kpi_name,
                    job["id"],
                    job["id"],
                    job["bronze_payload_id"],
                    job["run_id"],
                    SOURCE,
                    job["api_endpoint"],
                    Json(
                        {
                            "kpi": kpi_name,
                            "gold": "gold_validated_jobs",
                            "canonical": "canonical_jobs",
                            "silver": "silver_normalized_jobs",
                            "bronze": "bronze_job_payloads",
                            "endpoint": job["api_endpoint"],
                        }
                    ),
                )
                for job in jobs
            ],
        )


def persist_temporal_signals(jobs: list[dict[str, Any]]) -> None:
    if not jobs:
        return
    current: Counter[tuple[str, str]] = Counter()
    evidence: dict[tuple[str, str], list[str]] = defaultdict(list)
    for job in jobs:
        for skill in set(job.get("skills") or []):
            key = (job["dominio"], skill)
            current[key] += 1
            if len(evidence[key]) < 3:
                evidence[key].append(job["titulo"])

    with get_connection() as conn, conn.cursor() as cur:
        trend_rows = []
        signal_rows = []
        for (domain, skill), count in current.items():
            cur.execute(
                """
                SELECT job_count, growth_rate
                FROM public.job_skill_trends
                WHERE source = %s AND domain = %s AND skill_normalized = %s AND snapshot_date < CURRENT_DATE
                ORDER BY snapshot_date DESC
                LIMIT 1
                """,
                (SOURCE, domain, skill),
            )
            previous = cur.fetchone()
            previous_count = int(previous["job_count"]) if previous else 0
            previous_growth = float(previous["growth_rate"]) if previous else 0.0
            growth_rate = 1.0 if previous_count == 0 and count > 0 else (count - previous_count) / max(1, previous_count)
            acceleration = growth_rate - previous_growth
            payload = {"sample_roles": evidence[(domain, skill)]}
            trend_rows.append(
                (SOURCE, domain, skill, count, previous_count, growth_rate, acceleration, growth_rate >= 0.5, growth_rate <= -0.35, Json(payload))
            )
            if growth_rate >= 0.5 or growth_rate <= -0.35:
                signal_rows.append(
                    (
                        SOURCE,
                        "emerging_skill" if growth_rate >= 0.5 else "declining_skill",
                        domain,
                        skill,
                        count,
                        previous_count,
                        growth_rate,
                        acceleration,
                        min(0.95, 0.45 + abs(growth_rate) * 0.25),
                        Json(payload),
                    )
                )
        if trend_rows:
            execute_values(
                cur,
                """
                INSERT INTO public.job_skill_trends (
                    source, domain, skill_normalized, job_count, previous_job_count,
                    growth_rate, demand_acceleration, is_emerging, is_declining, evidence
                )
                VALUES %s
                ON CONFLICT (source, domain, skill_normalized, snapshot_date) DO UPDATE SET
                    job_count = EXCLUDED.job_count,
                    previous_job_count = EXCLUDED.previous_job_count,
                    growth_rate = EXCLUDED.growth_rate,
                    demand_acceleration = EXCLUDED.demand_acceleration,
                    is_emerging = EXCLUDED.is_emerging,
                    is_declining = EXCLUDED.is_declining,
                    evidence = EXCLUDED.evidence
                """,
                trend_rows,
            )
        if signal_rows:
            execute_values(
                cur,
                """
                INSERT INTO public.temporal_market_signals (
                    source, signal_type, domain, skill_normalized, current_count, previous_count,
                    growth_rate, demand_acceleration, confidence, evidence
                )
                VALUES %s
                ON CONFLICT (source, signal_type, domain, skill_normalized, period_end) DO UPDATE SET
                    current_count = EXCLUDED.current_count,
                    previous_count = EXCLUDED.previous_count,
                    growth_rate = EXCLUDED.growth_rate,
                    demand_acceleration = EXCLUDED.demand_acceleration,
                    confidence = EXCLUDED.confidence,
                    evidence = EXCLUDED.evidence
                """,
                signal_rows,
            )


def write_outputs(run_id: str, jobs: list[dict[str, Any]], gold_count: int) -> dict[str, str]:
    silver_path = dated_layer_path("silver", SOURCE, run_id)
    gold_path = dated_layer_path("gold", SOURCE, run_id)
    (silver_path / "normalized_jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (gold_path / "gold_publication_summary.json").write_text(
        json.dumps({"run_id": run_id, "candidate_jobs": len(jobs), "published_gold": gold_count}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (silver_path / "normalized_jobs.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = ["id", "role_title", "canonical_role", "company", "location", "modality", "domain", "skills", "overall_score", "url"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for job in jobs:
            writer.writerow(
                {
                    "id": job["id"],
                    "role_title": job["titulo"],
                    "canonical_role": job["titulo_normalizado"],
                    "company": job["empresa"],
                    "location": job["ciudad"],
                    "modality": job["modalidad"],
                    "domain": job["dominio"],
                    "skills": "; ".join(job["skills"]),
                    "overall_score": job["relevance_scores"]["overall_score"],
                    "url": job["url"],
                }
            )
    return {"silver_dir": str(silver_path), "gold_dir": str(gold_path)}


def discover_jobs(
    session: requests.Session,
    headers: dict[str, str],
    run_id: str,
    query: str,
    pages: int,
    page_size: int,
    dry_run: bool,
) -> tuple[list[tuple[dict[str, Any], int | None, str]], int, int, bool]:
    records: list[tuple[dict[str, Any], int | None, str]] = []
    error_count = 0
    auth_blocked = False
    for page in range(1, pages + 1):
        page_records: list[tuple[dict[str, Any], int | None, str]] = []
        for payload in find_payload_variants(query, page, page_size):
            status_code, response_payload = request_json(session, FIND_ENDPOINT, payload, headers)
            write_layer_file("bronze", run_id, f"find_page_{page}_{stable_hash(payload)[:10]}.json", {
                "endpoint": FIND_ENDPOINT,
                "request": payload,
                "status_code": status_code,
                "response": response_payload,
            })
            bronze_id = None if dry_run else persist_bronze_payload(run_id, FIND_ENDPOINT, payload, status_code, response_payload)
            mark_registry_auth_required(FIND_ENDPOINT, "POST", status_code)
            if status_code in {401, 403}:
                auth_blocked = True
                error_count += 1
                continue
            if status_code >= 400 or status_code == 0:
                error_count += 1
                continue
            found = find_job_records(response_payload)
            page_records.extend((record, bronze_id, FIND_ENDPOINT) for record in found)
            if found:
                break
        records.extend(page_records)
        if not page_records and auth_blocked:
            break
    return records, len(records), error_count, auth_blocked


def fetch_details(
    session: requests.Session,
    headers: dict[str, str],
    run_id: str,
    records: list[tuple[dict[str, Any], int | None, str]],
    dry_run: bool,
) -> tuple[list[tuple[dict[str, Any], int | None, str]], int]:
    enriched: list[tuple[dict[str, Any], int | None, str]] = []
    error_count = 0
    for record, bronze_id, endpoint in records:
        job_id = source_job_id(record)
        if not job_id:
            enriched.append((record, bronze_id, endpoint))
            continue
        detail_found = False
        for payload in detail_payload_variants(job_id):
            status_code, response_payload = request_json(session, DETAIL_ENDPOINT, payload, headers)
            write_layer_file("bronze", run_id, f"detail_{job_id}_{stable_hash(payload)[:10]}.json", {
                "endpoint": DETAIL_ENDPOINT,
                "request": payload,
                "status_code": status_code,
                "response": response_payload,
            })
            detail_bronze_id = None if dry_run else persist_bronze_payload(run_id, DETAIL_ENDPOINT, payload, status_code, response_payload)
            mark_registry_auth_required(DETAIL_ENDPOINT, "POST", status_code)
            if status_code in {401, 403}:
                error_count += 1
                break
            if status_code >= 400 or status_code == 0:
                error_count += 1
                continue
            detail_records = find_job_records(response_payload)
            detail = detail_records[0] if detail_records else response_payload if isinstance(response_payload, dict) else {}
            merged = {**record, **detail}
            enriched.append((merged, detail_bronze_id or bronze_id, DETAIL_ENDPOINT))
            detail_found = True
            break
        if not detail_found:
            enriched.append((record, bronze_id, endpoint))
    return enriched, error_count


def extract(
    query: str,
    *,
    pages: int,
    page_size: int,
    dry_run: bool = False,
    auto_validate: bool = False,
    min_relevance: float = 0.64,
) -> dict[str, Any]:
    apply_schema()
    run_id = f"elempleo_gold_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    create_run(run_id, query, {"pages": pages, "page_size": page_size, "auto_validate": auto_validate, "min_relevance": min_relevance})
    raw_count = 0
    error_count = 0
    gold_count = 0
    normalized_jobs: list[dict[str, Any]] = []
    try:
        session, referer, headers = bootstrap_session(query)
        records, raw_count, discover_errors, auth_blocked = discover_jobs(session, headers, run_id, query, pages, page_size, dry_run)
        error_count += discover_errors
        enriched_records, detail_errors = fetch_details(session, headers, run_id, records, dry_run)
        error_count += detail_errors
        for record, bronze_id, endpoint in enriched_records:
            job = normalize_record(record, run_id, bronze_id, endpoint)
            if has_real_evidence(job):
                normalized_jobs.append(job)
        normalized_jobs = deduplicate_semantically(normalized_jobs)
        paths = write_outputs(run_id, normalized_jobs, gold_count)
        if not dry_run and normalized_jobs:
            persist_silver_jobs(normalized_jobs)
            gold_count = publish_canonical_and_gold(normalized_jobs, auto_validate=auto_validate, min_relevance=min_relevance)
            persist_lineage([job for job in normalized_jobs if job["relevance_scores"]["overall_score"] >= min_relevance])
            persist_temporal_signals(normalized_jobs)
            paths = write_outputs(run_id, normalized_jobs, gold_count)
        status = "blocked_auth" if auth_blocked and raw_count == 0 else "completed"
        finish_run(run_id, status, raw_count, len(normalized_jobs), gold_count, error_count)
        return {
            "run_id": run_id,
            "source": SOURCE,
            "query": query,
            "status": status,
            "auth_blocked": auth_blocked and raw_count == 0,
            "raw_count": raw_count,
            "silver_count": len(normalized_jobs),
            "gold_count": gold_count,
            "error_count": error_count,
            "referer": referer,
            "find_endpoint": FIND_ENDPOINT,
            "detail_endpoint": DETAIL_ENDPOINT,
            **paths,
        }
    except Exception:
        finish_run(run_id, "failed", raw_count, len(normalized_jobs), gold_count, error_count + 1)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="El Empleo API-first Gold pipeline with lineage and temporal signals.")
    parser.add_argument("--query", default="analista de datos")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-validate", action="store_true")
    parser.add_argument("--min-relevance", type=float, default=0.64)
    args = parser.parse_args()
    result = extract(
        args.query,
        pages=args.pages,
        page_size=args.page_size,
        dry_run=args.dry_run,
        auto_validate=args.auto_validate,
        min_relevance=args.min_relevance,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
