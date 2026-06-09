from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor, execute_values

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

_RAILWAY_URL = os.getenv("RAILWAY_DATABASE_URL")
if _RAILWAY_URL:
    DB_CONFIG = {"dsn": _RAILWAY_URL, "sslmode": "require"}
else:
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": os.getenv("DB_PORT", "5433"),
        "dbname": os.getenv("DB_NAME", "cliente_a_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }

TASK_NAME = "program_job_match"
MATCH_METHOD = "rules_v1"
MODEL_NAME = "local_rules_v1"

GENERIC_SKILL_KEYS = {
    "a",
    "al",
    "analisis",
    "atencion",
    "buenas practicas",
    "calidad",
    "cliente",
    "comunicacion",
    "conocimiento",
    "datos",
    "deseable",
    "experiencia",
    "gestion",
    "herramientas",
    "informacion",
    "liderazgo",
    "manejo",
    "office",
    "proceso",
    "procesos",
    "remota",
    "remoto",
    "requerido",
    "servicio",
    "usuario",
    "usuarios",
}

SKILL_ALIASES = {
    "analitica de datos": "analitica de datos",
    "analisis de datos": "analitica de datos",
    "análisis de datos": "analitica de datos",
    "business intelligence": "business intelligence",
    "inteligencia de negocios": "business intelligence",
    "inteligencia de negocio": "business intelligence",
    "bi": "business intelligence",
    "power bi": "power bi",
    "visual analytics": "visual analytics",
    "visualizacion": "visualizacion de datos",
    "visualización": "visualizacion de datos",
    "visualizacion de datos": "visualizacion de datos",
    "visualización de datos": "visualizacion de datos",
    "big data": "big data",
    "data modeling": "modelado de datos",
    "modelado de datos": "modelado de datos",
    "sql": "sql",
    "excel": "excel",
    "python": "python",
    "etl": "etl",
    "elt": "etl",
    "sql server": "sql",
    "bases de datos sql": "sql",
    "gobierno de datos": "gobierno de datos",
    "kpi": "kpis",
    "kpis": "kpis",
    "dashboard": "dashboards",
    "dashboards": "dashboards",
    "gestion de proyectos": "gestion de proyectos",
    "gestión de proyectos": "gestion de proyectos",
    "scrum": "scrum",
    "cloud": "cloud",
    "aws": "aws",
    "azure": "azure",
    "agile": "metodologias agiles",
    "metodologias agiles": "metodologias agiles",
    "metodologías ágiles": "metodologias agiles",
    "api": "apis",
    "apis": "apis",
    "apis rest": "apis",
    "rest": "apis",
    "git": "git",
    "github": "git",
    "programacion": "programacion",
    "programación": "programacion",
    "desarrollo de software": "programacion",
    "desarrollador": "programacion",
    "developer": "programacion",
    "arquitectura de software": "arquitectura de software",
    "arquitecto de software": "arquitectura de software",
    "testing": "testing",
    "pruebas": "testing",
    "qa": "testing",
    "node.js": "programacion",
    "nodejs": "programacion",
    ".net": "programacion",
}

ROLE_GROUPS = [
    ("datos", ["datos", "data", "analytics", "analitica", "business intelligence", "bi", "sql", "etl", "big data"]),
    ("software", ["software", "desarrollador", "programador", "developer", "backend", "frontend", "full stack"]),
    ("proyectos", ["proyecto", "project", "scrum", "agile", "product owner", "coordinador"]),
    ("calidad", ["calidad", "qa", "auditor", "auditoria", "cumplimiento", "compliance"]),
    ("comercial", ["comercial", "ventas", "sales", "cliente", "crm", "customer"]),
    ("educacion", ["docente", "pedagog", "educacion", "academico", "ensenanza", "curriculo"]),
    ("salud", ["salud", "clinico", "hospital", "sanitario", "eps"]),
    ("finanzas", ["financ", "contable", "tribut", "fiscal", "riesgo", "cartera"]),
    ("seguridad", ["seguridad", "ciber", "redes", "infraestructura", "soporte"]),
]


@dataclass(frozen=True)
class ProgramDocument:
    id: int
    especializacion_id: int | None
    name: str
    role_target: str
    description: str
    campo_laboral: str
    plan_estudios: str
    general_text: str
    skills: list[str]


@dataclass(frozen=True)
class JobDocument:
    id: int
    empleo_id: str
    title: str
    company: str
    location: str
    source: str
    url: str
    skills: list[str]


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("Ã¡", "a").replace("Ã©", "e").replace("Ã­", "i").replace("Ã³", "o").replace("Ãº", "u")
    text = text.replace("Ã±", "n").replace("Ã", "i")
    text = re.sub(r"[^a-zA-Z0-9+#.]+", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def canonical_skill(value: str) -> str:
    key = normalize_text(value)
    if key in SKILL_ALIASES:
        return SKILL_ALIASES[key]
    key = re.sub(r"\b(en|de|del|la|las|los|el|y|para|con)\b", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    if not key or key in GENERIC_SKILL_KEYS or len(key) < 2:
        return ""
    return SKILL_ALIASES.get(key, key)


def canonical_skill_candidates(value: str) -> list[str]:
    key = normalize_text(value)
    if not key:
        return []
    candidates: list[str] = []
    for alias_key, canonical in SKILL_ALIASES.items():
        alias_norm = normalize_text(alias_key)
        if alias_norm and re.search(rf"(?<![a-z0-9]){re.escape(alias_norm)}(?![a-z0-9])", key):
            candidates.append(canonical)
    direct = canonical_skill(value)
    if direct and len(direct) <= 42:
        candidates.append(direct)

    seen: set[str] = set()
    clean: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in GENERIC_SKILL_KEYS and candidate not in seen:
            seen.add(candidate)
            clean.append(candidate)
    return clean


def display_skill(value: str) -> str:
    candidates = canonical_skill_candidates(value)
    canonical = candidates[0] if candidates else canonical_skill(value)
    if not canonical:
        return ""
    acronyms = {"sql", "etl", "kpis", "aws", "bi", "crm", "qa"}
    return canonical.upper() if canonical in acronyms else canonical.title()


def unique_clean_skills(values: list[str]) -> list[str]:
    output: dict[str, str] = {}
    for value in values:
        for key in canonical_skill_candidates(value):
            label = key.upper() if key in {"sql", "etl", "kpis", "aws", "bi", "crm", "qa"} else key.title()
            if key and label:
                output.setdefault(key, label)
    return [output[key] for key in sorted(output)]


def token_set(value: str) -> set[str]:
    stopwords = {
        "a",
        "al",
        "como",
        "con",
        "de",
        "del",
        "el",
        "en",
        "la",
        "las",
        "los",
        "para",
        "por",
        "un",
        "una",
        "y",
    }
    return {token for token in normalize_text(value).split() if len(token) > 2 and token not in stopwords}


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, value)), 2)


def role_group_score(program_text: str, job_text: str) -> float:
    program_key = normalize_text(program_text)
    job_key = normalize_text(job_text)
    best = 0.0
    for _, keywords in ROLE_GROUPS:
        program_hits = sum(1 for keyword in keywords if normalize_text(keyword) in program_key)
        job_hits = sum(1 for keyword in keywords if normalize_text(keyword) in job_key)
        if program_hits and job_hits:
            best = max(best, min(100.0, 45.0 + (program_hits * 12.0) + (job_hits * 12.0)))
    return best


def text_affinity(program_text: str, job_text: str) -> float:
    program_tokens = token_set(program_text)
    job_tokens = token_set(job_text)
    if not program_tokens or not job_tokens:
        return 0.0
    overlap = len(program_tokens & job_tokens) / max(len(job_tokens), 1)
    sequence = SequenceMatcher(None, normalize_text(program_text)[:300], normalize_text(job_text)[:300]).ratio()
    grouped = role_group_score(program_text, job_text) / 100.0
    return clamp(((overlap * 0.45) + (sequence * 0.20) + (grouped * 0.35)) * 100.0)


def has_role_conflict(program_name: str, program_role: str, job_title: str) -> bool:
    title = normalize_text(job_title)
    program = normalize_text(f"{program_name} {program_role}")
    software_title = any(
        keyword in title
        for keyword in [
            "desarrollador",
            "developer",
            "frontend",
            "backend",
            "full stack",
            "mobile",
            ".net",
            "angular",
            "java",
        ]
    )
    software_program = any(
        keyword in program
        for keyword in [
            "software",
            "tecnologias de la informacion",
            "seguridad informatica",
            "ciber",
            "inteligencia artificial",
        ]
    )
    return software_title and not software_program


def relevance_label(score: float, common_count: int) -> str:
    if score >= 75 and common_count >= 2:
        return "high"
    if score >= 50 and common_count >= 1:
        return "medium"
    if score >= 30 and common_count >= 1:
        return "low"
    return "no_match"


def match_explanation(score: float, common: list[str], missing: list[str], role_score: float) -> str:
    if common:
        common_text = ", ".join(common[:4])
        missing_text = ", ".join(missing[:3])
        if missing_text:
            return f"Coincide por {common_text}; brechas principales: {missing_text}. Afinidad de rol: {role_score:.0f}%."
        return f"Coincide por {common_text}. Afinidad de rol: {role_score:.0f}%."
    return f"No hay skills compartidas suficientes; afinidad de rol estimada: {role_score:.0f}% y score total {score:.0f}%."


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def connect():
    if "dsn" in DB_CONFIG:
        return psycopg2.connect(DB_CONFIG["dsn"], sslmode=DB_CONFIG["sslmode"], cursor_factory=RealDictCursor)
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def ensure_match_schema(cur) -> None:
    schema_path = Path(__file__).with_name("ml_training_schema.sql")
    cur.execute(schema_path.read_text(encoding="utf-8"))


def create_run(cur, dataset_version: str, notes: str) -> int:
    cur.execute(
        """
        INSERT INTO ml_training_runs (run_name, task_name, dataset_version, source_config, notes)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (task_name, dataset_version)
        DO UPDATE SET
            run_name = EXCLUDED.run_name,
            source_config = EXCLUDED.source_config,
            notes = EXCLUDED.notes
        RETURNING id
        """,
        (
            f"program-job-match-{dataset_version}",
            TASK_NAME,
            dataset_version,
            Json({"method": MATCH_METHOD, "model": MODEL_NAME, "db": DB_CONFIG.get("dbname", DB_CONFIG.get("dsn", "")[:40])}),
            notes,
        ),
    )
    return int(cur.fetchone()["id"])


def load_latest_programs(cur) -> list[ProgramDocument]:
    cur.execute(
        """
        WITH latest_program_run AS (
            SELECT p.run_id
            FROM ml_program_documents p
            JOIN ml_training_runs r
                ON r.id = p.run_id
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT 1
        ),
        mapped_programs AS (
            SELECT DISTINCT ON (p.id)
                p.*,
                e.id AS especializacion_id
            FROM ml_program_documents p
            JOIN latest_program_run lpr
                ON lpr.run_id = p.run_id
            LEFT JOIN especializaciones e
                ON lower(e.nombre) = lower(p.program_name)
                OR lower(COALESCE(e.source_url, '')) = lower(COALESCE(p.source_url, p.external_program_id, ''))
            ORDER BY
                p.id,
                CASE WHEN e.plan_estudios IS NOT NULL AND e.plan_estudios <> '' THEN 0 ELSE 1 END,
                e.id DESC
        )
        SELECT
            mp.id,
            mp.especializacion_id,
            mp.program_name,
            COALESCE(mp.role_target, '') AS role_target,
            COALESCE(mp.description, '') AS description,
            COALESCE(mp.campo_laboral, '') AS campo_laboral,
            COALESCE(mp.plan_estudios, '') AS plan_estudios,
            COALESCE(mp.general_text, '') AS general_text,
            COALESCE(
                jsonb_agg(DISTINCT l.skill_name) FILTER (WHERE l.skill_name IS NOT NULL),
                '[]'::jsonb
            ) AS label_skills
        FROM mapped_programs mp
        LEFT JOIN ml_program_skill_labels l
            ON l.program_document_id = mp.id
            AND l.label_type = 'positive'
        GROUP BY
            mp.id,
            mp.especializacion_id,
            mp.program_name,
            mp.role_target,
            mp.description,
            mp.campo_laboral,
            mp.plan_estudios,
            mp.general_text
        ORDER BY mp.program_name
        """
    )
    programs: list[ProgramDocument] = []
    for row in cur.fetchall():
        skills = unique_clean_skills(list(row.get("label_skills") or []))
        programs.append(
            ProgramDocument(
                id=int(row["id"]),
                especializacion_id=int(row["especializacion_id"]) if row.get("especializacion_id") is not None else None,
                name=str(row["program_name"] or ""),
                role_target=str(row["role_target"] or ""),
                description=str(row["description"] or ""),
                campo_laboral=str(row["campo_laboral"] or ""),
                plan_estudios=str(row["plan_estudios"] or ""),
                general_text=str(row["general_text"] or ""),
                skills=skills,
            )
        )
    return programs


def load_jobs(cur) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            e.id,
            COALESCE(e.titulo, '') AS title,
            COALESCE(e.empresa, '') AS company,
            COALESCE(e.ubicacion, '') AS location,
            COALESCE(e.fuente, '') AS source,
            COALESCE(e.url, '') AS source_url,
            COALESCE(e.descripcion, '') AS description,
            COALESCE(e.matched_skills, '') AS matched_skills,
            COALESCE(e.missing_skills, '') AS missing_skills,
            COALESCE(e.skills_text, '') AS skills_text,
            COALESCE(
                jsonb_agg(DISTINCT s.nombre) FILTER (WHERE s.nombre IS NOT NULL),
                '[]'::jsonb
            ) AS skills
        FROM empleos e
        LEFT JOIN empleo_skills es
            ON es.empleo_id = e.id
        LEFT JOIN skills s
            ON s.id = es.skill_id
        GROUP BY
            e.id,
            e.titulo,
            e.empresa,
            e.ubicacion,
            e.fuente,
            e.url,
            e.descripcion,
            e.matched_skills,
            e.missing_skills,
            e.skills_text
        ORDER BY e.id
        """
    )
    return list(cur.fetchall())


def split_skill_text(value: str) -> list[str]:
    text = str(value or "")
    if not text:
        return []
    parts = re.split(r"[;,\n\r\t|]+", text)
    return [part.strip() for part in parts if part.strip()]


def upsert_job_documents(cur, run_id: int, jobs: list[dict[str, Any]]) -> list[JobDocument]:
    rows = []
    for job in jobs:
        raw_skill_values = list(job.get("skills") or [])
        raw_skill_values.extend(split_skill_text(str(job.get("matched_skills") or "")))
        raw_skill_values.extend(split_skill_text(str(job.get("missing_skills") or "")))
        raw_skill_values.extend(split_skill_text(str(job.get("skills_text") or "")))
        raw_skill_values.extend([str(job.get("title") or ""), str(job.get("description") or "")])
        skills = unique_clean_skills(raw_skill_values)
        normalized_text = " | ".join(
            part
            for part in [
                str(job.get("title") or ""),
                str(job.get("company") or ""),
                str(job.get("location") or ""),
                str(job.get("description") or "")[:1000],
                str(job.get("skills_text") or "")[:1000],
                ", ".join(skills),
            ]
            if part
        )
        external_id = str(job["id"])
        content_hash = stable_hash(
            {
                "id": external_id,
                "title": job.get("title"),
                "description": job.get("description"),
                "skills_text": job.get("skills_text"),
                "skills": skills,
            }
        )
        rows.append(
            (
                run_id,
                external_id,
                str(job.get("title") or ""),
                str(job.get("company") or ""),
                str(job.get("location") or ""),
                str(job.get("source") or ""),
                str(job.get("source_url") or ""),
                normalized_text,
                content_hash,
                Json(
                    {
                        "empleo_id": job["id"],
                        "skills": skills,
                        "description": job.get("description") or "",
                        "skills_text": job.get("skills_text") or "",
                    }
                ),
            )
        )
    execute_values(
        cur,
        """
        INSERT INTO ml_job_documents (
            run_id,
            external_job_id,
            title,
            company,
            location,
            source,
            source_url,
            normalized_text,
            content_hash,
            raw_payload
        )
        VALUES %s
        ON CONFLICT (run_id, external_job_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            location = EXCLUDED.location,
            source = EXCLUDED.source,
            source_url = EXCLUDED.source_url,
            normalized_text = EXCLUDED.normalized_text,
            content_hash = EXCLUDED.content_hash,
            raw_payload = EXCLUDED.raw_payload
        """,
        rows,
    )
    cur.execute(
        """
        SELECT id, external_job_id, title, company, location, source, source_url, raw_payload
        FROM ml_job_documents
        WHERE run_id = %s
        ORDER BY id
        """,
        (run_id,),
    )
    documents: list[JobDocument] = []
    for row in cur.fetchall():
        payload = row.get("raw_payload") or {}
        documents.append(
            JobDocument(
                id=int(row["id"]),
                empleo_id=str(row["external_job_id"]),
                title=str(row["title"] or ""),
                company=str(row["company"] or ""),
                location=str(row["location"] or ""),
                source=str(row["source"] or ""),
                url=str(row["source_url"] or ""),
                skills=unique_clean_skills(list(payload.get("skills") or [])),
            )
        )
    return documents


def compute_matches(programs: list[ProgramDocument], jobs: list[JobDocument], *, include_no_match: bool) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for program in programs:
        program_skills = unique_clean_skills(program.skills)
        program_skill_keys = {canonical_skill(skill): skill for skill in program_skills if canonical_skill(skill)}
        program_text = " ".join(
            [
                program.name,
                program.role_target,
                program.description,
                program.campo_laboral,
                program.plan_estudios,
                program.general_text[:1500],
            ]
        )
        for job in jobs:
            job_skills = unique_clean_skills(job.skills)
            job_skill_keys = {canonical_skill(skill): skill for skill in job_skills if canonical_skill(skill)}
            common_keys = sorted(set(program_skill_keys) & set(job_skill_keys))
            missing_keys = sorted(set(job_skill_keys) - set(program_skill_keys))
            common = [program_skill_keys[key] for key in common_keys]
            missing = [job_skill_keys[key] for key in missing_keys]

            program_coverage = (len(common_keys) / max(len(program_skill_keys), 1)) * 100.0 if program_skill_keys else 0.0
            job_density = (len(common_keys) / max(len(job_skill_keys), 1)) * 100.0 if job_skill_keys else 0.0
            skill_overlap_score = clamp((program_coverage * 0.70) + (job_density * 0.30))
            role_score = text_affinity(program_text, " ".join([job.title, job.company, job.location, ", ".join(job_skills)]))
            score = clamp((skill_overlap_score * 0.68) + (role_score * 0.32))
            conflict = has_role_conflict(program.name, program.role_target, job.title)
            if conflict:
                score = clamp(score * 0.55)
                role_score = clamp(role_score * 0.50)
            label = relevance_label(score, len(common_keys))

            if label == "no_match" and not include_no_match:
                continue

            features = {
                "program_coverage": round(program_coverage, 4),
                "job_skill_density": round(job_density, 4),
                "skill_overlap_score": skill_overlap_score,
                "role_alignment": role_score,
                "common_count": len(common_keys),
                "program_skill_count": len(program_skill_keys),
                "job_skill_count": len(job_skill_keys),
                "role_conflict": conflict,
            }
            matches.append(
                {
                    "program_document_id": program.id,
                    "job_document_id": job.id,
                    "especializacion_id": program.especializacion_id,
                    "empleo_id": job.empleo_id,
                    "program_name": program.name,
                    "job_title": job.title,
                    "company": job.company,
                    "score_match": score,
                    "relevance_label": label,
                    "role_alignment": role_score,
                    "skill_overlap_score": skill_overlap_score,
                    "job_skill_density": clamp(job_density),
                    "skills_en_comun": common,
                    "skills_faltantes": missing,
                    "skills_programa": program_skills,
                    "skills_empleo": job_skills,
                    "explanation": match_explanation(score, common, missing, role_score),
                    "content_hash": stable_hash(
                        {
                            "program": program.id,
                            "job": job.id,
                            "method": MATCH_METHOD,
                            "common": common_keys,
                            "score": score,
                        }
                    ),
                    "raw_features": features,
                }
            )
    matches.sort(key=lambda item: (-float(item["score_match"]), str(item["program_name"]), str(item["job_title"])))
    return matches


def save_matches(cur, run_id: int, matches: list[dict[str, Any]]) -> None:
    if not matches:
        return
    rows = [
        (
            run_id,
            match["program_document_id"],
            match["job_document_id"],
            match["especializacion_id"],
            match["empleo_id"],
            match["program_name"],
            match["job_title"],
            match["company"],
            MATCH_METHOD,
            MODEL_NAME,
            match["score_match"],
            match["relevance_label"],
            match["role_alignment"],
            match["skill_overlap_score"],
            match["job_skill_density"],
            Json(match["skills_en_comun"]),
            Json(match["skills_faltantes"]),
            Json(match["skills_programa"]),
            Json(match["skills_empleo"]),
            match["explanation"],
            match["content_hash"],
            Json(match["raw_features"]),
        )
        for match in matches
    ]
    execute_values(
        cur,
        """
        INSERT INTO ml_program_job_matches (
            run_id,
            program_document_id,
            job_document_id,
            especializacion_id,
            empleo_id,
            program_name,
            job_title,
            company,
            match_method,
            model_name,
            score_match,
            relevance_label,
            role_alignment,
            skill_overlap_score,
            job_skill_density,
            skills_en_comun,
            skills_faltantes,
            skills_programa,
            skills_empleo,
            explanation,
            content_hash,
            raw_features
        )
        VALUES %s
        ON CONFLICT (run_id, program_document_id, job_document_id, match_method)
        DO UPDATE SET
            score_match = EXCLUDED.score_match,
            relevance_label = EXCLUDED.relevance_label,
            role_alignment = EXCLUDED.role_alignment,
            skill_overlap_score = EXCLUDED.skill_overlap_score,
            job_skill_density = EXCLUDED.job_skill_density,
            skills_en_comun = EXCLUDED.skills_en_comun,
            skills_faltantes = EXCLUDED.skills_faltantes,
            skills_programa = EXCLUDED.skills_programa,
            skills_empleo = EXCLUDED.skills_empleo,
            explanation = EXCLUDED.explanation,
            content_hash = EXCLUDED.content_hash,
            raw_features = EXCLUDED.raw_features
        """,
        rows,
    )


def write_jsonl(path: Path, matches: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for match in matches:
            output.write(json.dumps(match, ensure_ascii=False, sort_keys=True) + "\n")


def summarize(matches: list[dict[str, Any]]) -> dict[str, Any]:
    by_label: dict[str, int] = defaultdict(int)
    by_program: dict[str, int] = defaultdict(int)
    for match in matches:
        by_label[str(match["relevance_label"])] += 1
        by_program[str(match["program_name"])] += 1
    return {
        "total_matches": len(matches),
        "labels": dict(sorted(by_label.items())),
        "programs_with_matches": sum(1 for count in by_program.values() if count > 0),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calcula matches ML/rules entre programas UNIR y empleos.")
    parser.add_argument("--dataset-version", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--notes", default="Match programa-vacante con baseline local reproducible.")
    parser.add_argument("--jsonl-path", default="program_job_matches.record.jsonl")
    parser.add_argument("--no-jsonl", action="store_true")
    parser.add_argument("--include-no-match", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                ensure_match_schema(cur)
                run_id = create_run(cur, args.dataset_version, args.notes)
                programs = load_latest_programs(cur)
                raw_jobs = load_jobs(cur)
                jobs = upsert_job_documents(cur, run_id, raw_jobs)
                matches = compute_matches(programs, jobs, include_no_match=args.include_no_match)
                save_matches(cur, run_id, matches)
                summary = summarize(matches)
        if not args.no_jsonl:
            write_jsonl(Path(args.jsonl_path), matches)
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "programs": len(programs),
                    "jobs": len(jobs),
                    **summary,
                    "jsonl_path": None if args.no_jsonl else str(Path(args.jsonl_path).resolve()),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
