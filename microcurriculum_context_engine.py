from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from psycopg2.extras import Json, RealDictCursor, execute_values

from microcurriculum_engine.pipelines.process_microcurriculum import process_microcurriculum
from sync_to_railway import connect, get_local_config, get_railway_config, load_dotenv_files


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = ROOT / "storage" / "test_microcurriculos" / "especialización en visual analytics y big data"
MIGRATION = ROOT / "database" / "migrations" / "009_microcurriculum_program_context.sql"
OUTPUTS = ROOT / "outputs"

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

VISUAL_ANALYTICS_MARKET_SKILLS = [
    "power bi",
    "tableau",
    "sql",
    "python",
    "r",
    "big data",
    "etl",
    "machine learning",
    "data visualization",
    "dashboards",
    "storytelling with data",
    "data governance",
    "data warehousing",
    "lakehouse",
    "cloud analytics",
    "azure",
    "aws",
    "google cloud",
    "spark",
    "hadoop",
    "databricks",
    "snowflake",
    "power platform",
    "mlops",
    "dataops",
    "ia generativa",
]

VISUAL_ANALYTICS_ROLES = [
    "Data Analyst",
    "BI Specialist",
    "Analytics Engineer",
    "Data Visualization Consultant",
    "Business Intelligence Architect",
]

MARKET_SKILL_ALIASES = {
    "dashboards": ("dashboard", "dashboards", "tablero", "tableros", "cuadro de mando", "cuadros de mando"),
    "data visualization": ("visualizacion de datos", "visualización de datos", "visualizacion interactiva", "visual analytics"),
    "data governance": ("gobierno del dato", "gobierno de datos", "data governance", "calidad del dato", "linaje"),
    "data warehousing": ("data warehouse", "data warehousing", "almacen de datos", "almacenes de datos"),
    "storytelling with data": ("storytelling", "narrativa de datos", "comunicacion de datos", "visualizacion ejecutiva"),
    "cloud analytics": ("cloud analytics", "analitica cloud", "analitica en la nube", "nube", "cloud"),
    "lakehouse": ("lakehouse", "data lakehouse", "data lake", "lago de datos"),
    "mlops": ("mlops", "ciclo de vida de modelos", "despliegue de modelos", "monitoreo de modelos"),
    "dataops": ("dataops", "operaciones de datos", "automatizacion de datos", "pipeline de datos"),
    "ia generativa": ("ia generativa", "inteligencia artificial generativa", "generative ai"),
    "power platform": ("power platform", "power apps", "power automate"),
}

BENCHMARKING_REFERENCES = [
    {
        "source": "SNIES",
        "institution": "UNIR Colombia",
        "program": "Especialización en Visual Analytics y Big Data",
        "modality": "Virtual",
        "score": 78,
    },
    {
        "source": "SNIES",
        "institution": "Areandina",
        "program": "Especialización en Analítica de Datos",
        "modality": "Virtual",
        "score": 74,
    },
    {
        "source": "SNIES",
        "institution": "UNAD",
        "program": "Especialización en Big Data",
        "modality": "Virtual",
        "score": 70,
    },
    {
        "source": "Coursera",
        "institution": "Google / Coursera",
        "program": "Business Intelligence Professional Certificate",
        "modality": "Online",
        "score": 68,
    },
    {
        "source": "edX",
        "institution": "IBM / edX",
        "program": "Data Analytics and Visualization",
        "modality": "Online",
        "score": 66,
    },
]

STOPWORDS = {
    "para",
    "como",
    "con",
    "los",
    "las",
    "del",
    "una",
    "por",
    "que",
    "datos",
    "asignatura",
    "programa",
    "aprendizaje",
    "competencia",
    "competencias",
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    return " ".join(text.split())


def unique_sorted(counter: Counter[str], *, limit: int = 40) -> list[dict[str, Any]]:
    return [
        {"name": name, "frequency": count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
        if name
    ]


def apply_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(MIGRATION.read_text(encoding="utf-8"))


def configure_backend_db_env(config) -> None:
    os.environ["DB_HOST"] = config.host
    os.environ["DB_PORT"] = str(config.port)
    os.environ["DB_NAME"] = config.dbname
    os.environ["DB_USER"] = config.user
    os.environ["DB_PASSWORD"] = config.password
    os.environ["DB_SSLMODE"] = config.sslmode


def fetch_all(conn, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def resolve_specialization(conn, specialization_name: str) -> dict[str, Any]:
    candidates = fetch_all(
        conn,
        """
        SELECT id, nombre
        FROM public.especializaciones
        ORDER BY similarity(lower(unaccent(nombre)), lower(unaccent(%s))) DESC, id
        LIMIT 1
        """,
        (specialization_name,),
    )
    if not candidates:
        raise RuntimeError(f"No se encontró especialización para: {specialization_name}")
    return candidates[0]


def list_documents(source_dir: Path) -> list[Path]:
    return sorted(
        path for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def classify_bucket(skill: dict[str, Any]) -> str:
    kind = str(skill.get("tipo_skill") or "").lower()
    name = normalize_text(str(skill.get("skill_normalized") or skill.get("skill_original") or ""))
    if kind in {"transversal_skill", "habilidad_blanda"}:
        return "transversal_skills"
    if kind in {"methodology", "metodologia"}:
        return "methodologies"
    if kind in {"platform", "plataforma", "cloud_provider"}:
        return "platforms"
    if kind in {"tool", "herramienta", "framework", "database", "programming_language"}:
        return "tools"
    if any(term in name for term in ("aws", "azure", "cloud", "spark", "hadoop", "databricks", "snowflake", "power bi", "tableau")):
        return "tools"
    return "technical_skills"


def extract_keywords(text: str, skills: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    normalized = normalize_text(text)
    for phrase in VISUAL_ANALYTICS_MARKET_SKILLS:
        if normalize_text(phrase) in normalized:
            counter[phrase] += 2
    for canonical, aliases in MARKET_SKILL_ALIASES.items():
        if any(normalize_text(alias) in normalized for alias in aliases):
            counter[canonical] += 2
    for skill in skills:
        counter[skill] += 2
    for token in normalized.split():
        if len(token) >= 5 and token not in STOPWORDS:
            counter[token] += 1
    return counter


def detect_redundancies(subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skill_to_subjects: dict[str, set[str]] = defaultdict(set)
    for subject in subjects:
        for skill in subject.get("skills", []):
            skill_to_subjects[skill].add(subject["asignatura"])
    return [
        {"skill": skill, "subjects": sorted(names), "count": len(names)}
        for skill, names in sorted(skill_to_subjects.items())
        if len(names) >= 4
    ]


def build_narrative(shared: set[str], gaps: list[str], documents_count: int) -> str:
    strengths = []
    if {"power bi", "tableau", "data visualization", "dashboards"} & shared:
        strengths.append("visualización de datos y tableros ejecutivos")
    if {"sql", "etl", "big data"} & shared:
        strengths.append("tratamiento, integración y análisis de datos")
    if {"machine learning", "python", "r"} & shared:
        strengths.append("analítica avanzada e inteligencia artificial aplicada")
    if not strengths:
        strengths.append("analítica descriptiva y fundamentos de inteligencia de negocio")
    gap_text = ", ".join(gaps[:4]) if gaps else "profundización metodológica y evidencia aplicada"
    return (
        f"El programa fue analizado a partir de {documents_count} microcurrículos reales. "
        f"Presenta una orientación fuerte hacia {', '.join(strengths)}. "
        f"Se identifican oportunidades de fortalecimiento en {gap_text}, manteniendo una lectura contextual "
        "centrada en Visual Analytics, Big Data y toma de decisiones basada en datos."
    )


def persist_context(conn, specialization: dict[str, Any], source_dir: Path, context: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        for subject in context["subjects"]:
            document = subject.get("document") or {}
            cur.execute(
                """
                INSERT INTO public.microcurriculos (
                    programa, asignatura, semestre, creditos, source_document,
                    stored_path, document_hash, extraction_method, clean_text,
                    detected_domain, domain_confidence, confidence_score,
                    specialization_id, specialization_name, lineage, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_hash) DO UPDATE SET
                    programa = EXCLUDED.programa,
                    asignatura = EXCLUDED.asignatura,
                    semestre = EXCLUDED.semestre,
                    creditos = EXCLUDED.creditos,
                    source_document = EXCLUDED.source_document,
                    stored_path = EXCLUDED.stored_path,
                    extraction_method = EXCLUDED.extraction_method,
                    clean_text = EXCLUDED.clean_text,
                    detected_domain = EXCLUDED.detected_domain,
                    domain_confidence = EXCLUDED.domain_confidence,
                    confidence_score = EXCLUDED.confidence_score,
                    specialization_id = EXCLUDED.specialization_id,
                    specialization_name = EXCLUDED.specialization_name,
                    lineage = EXCLUDED.lineage,
                    metadata = EXCLUDED.metadata,
                    updated_at = now()
                RETURNING id
                """,
                (
                    subject.get("programa"),
                    subject.get("asignatura"),
                    subject.get("semestre"),
                    subject.get("creditos"),
                    subject.get("source_document"),
                    document.get("stored_path") or subject.get("source_document"),
                    document.get("content_hash"),
                    document.get("extraction_method"),
                    document.get("clean_text"),
                    subject.get("domain"),
                    subject.get("confidence") or 0,
                    subject.get("score") or 0,
                    specialization["id"],
                    specialization["nombre"],
                    Json({"pipeline": "microcurriculum_context_engine", "source_directory": str(source_dir)}),
                    Json({"document_name": subject.get("document_name"), "contextualized": True}),
                ),
            )
            micro_id = int(cur.fetchone()[0])
            subject["microcurriculo_id"] = micro_id
            cur.execute("DELETE FROM public.microcurriculo_asignaturas WHERE microcurriculo_id = %s", (micro_id,))
            cur.execute("DELETE FROM public.microcurriculo_competencias WHERE microcurriculo_id = %s", (micro_id,))
            cur.execute("DELETE FROM public.microcurriculo_skills WHERE microcurriculo_id = %s", (micro_id,))
            cur.execute("DELETE FROM public.microcurriculo_plataformas WHERE microcurriculo_id = %s", (micro_id,))
            cur.execute("DELETE FROM public.microcurriculo_herramientas WHERE microcurriculo_id = %s", (micro_id,))
            cur.execute("DELETE FROM public.microcurriculo_market_gaps WHERE microcurriculo_id = %s", (micro_id,))
            cur.execute("DELETE FROM public.microcurriculo_keywords WHERE microcurriculo_id = %s", (micro_id,))
            cur.execute(
                """
                INSERT INTO public.microcurriculo_asignaturas (
                    microcurriculo_id, nombre, semestre, creditos, contenidos,
                    metodologias, bibliografia, source_document, confidence_score, lineage
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    micro_id,
                    subject.get("asignatura") or subject.get("document_name"),
                    subject.get("semestre"),
                    subject.get("creditos"),
                    Json(subject.get("contenidos") or []),
                    Json(subject.get("metodologias") or []),
                    Json(subject.get("bibliografia") or []),
                    subject.get("source_document"),
                    subject.get("confidence") or 0,
                    Json({"pipeline": "microcurriculum_context_engine"}),
                ),
            )
            for competencia in [*(subject.get("competencias") or []), *(subject.get("resultados_aprendizaje") or [])]:
                cur.execute(
                    """
                    INSERT INTO public.microcurriculo_competencias (
                        microcurriculo_id, competencia_text, competencia_type,
                        confidence_score, source_document, lineage
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (micro_id, competencia, "competencia", 0.78, subject.get("source_document"), Json({"pipeline": "microcurriculum_context_engine"})),
                )
            for skill in subject.get("skill_details") or []:
                cur.execute(
                    """
                    INSERT INTO public.microcurriculo_skills (
                        microcurriculo_id, skill_original, skill_normalized, skill_domain,
                        tipo_skill, confidence_score, source_document, lineage
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (microcurriculo_id, skill_normalized, tipo_skill) DO NOTHING
                    """,
                    (
                        micro_id,
                        skill.get("skill_original"),
                        skill.get("skill_normalized"),
                        skill.get("skill_domain"),
                        skill.get("tipo_skill"),
                        skill.get("confianza_extraccion") or 0,
                        subject.get("source_document"),
                        Json({"pipeline": "microcurriculum_context_engine"}),
                    ),
                )
                if skill.get("tipo_skill") in {"plataforma", "platform", "cloud_provider"}:
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculo_plataformas (
                            microcurriculo_id, plataforma, plataforma_normalized,
                            confidence_score, source_document, lineage
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (microcurriculo_id, plataforma_normalized) DO NOTHING
                        """,
                        (
                            micro_id,
                            skill.get("skill_original"),
                            skill.get("skill_normalized"),
                            skill.get("confianza_extraccion") or 0,
                            subject.get("source_document"),
                            Json({"pipeline": "microcurriculum_context_engine"}),
                        ),
                    )
                if skill.get("tipo_skill") in {"herramienta", "tool", "framework", "database", "programming_language", "metodologia", "methodology"}:
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculo_herramientas (
                            microcurriculo_id, herramienta, herramienta_normalized,
                            tipo, confidence_score, source_document, lineage
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (microcurriculo_id, herramienta_normalized) DO NOTHING
                        """,
                        (
                            micro_id,
                            skill.get("skill_original"),
                            skill.get("skill_normalized"),
                            skill.get("tipo_skill"),
                            skill.get("confianza_extraccion") or 0,
                            subject.get("source_document"),
                            Json({"pipeline": "microcurriculum_context_engine"}),
                        ),
                    )
            for gap in context.get("real_market_gaps") or []:
                cur.execute(
                    """
                    INSERT INTO public.microcurriculo_market_gaps (
                        microcurriculo_id, gap_type, skill_normalized, severity,
                        demand_count, confidence_score, evidence, source_document, lineage
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        micro_id,
                        "missing_skill",
                        gap["name"],
                        "high" if gap.get("priority") == "alta" else "medium",
                        1,
                        0.76,
                        Json({"source": "visual_analytics_market_context"}),
                        subject.get("source_document"),
                        Json({"pipeline": "microcurriculum_context_engine"}),
                    ),
                )

        cur.execute(
            """
            INSERT INTO public.microcurriculum_program_contexts (
                specialization_id, specialization_name, source_directory, documents_processed,
                detected_domain, detected_subdomain, confidence, subjects, technical_skills,
                transversal_skills, methodologies, tools, platforms, technologies,
                bibliography, keywords, occupational_profiles, real_market_gaps,
                strengthening_areas, redundancies, labor_roles, benchmarking, scores,
                executive_narrative, raw_context, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
            )
            ON CONFLICT (specialization_id) DO UPDATE SET
                specialization_name = EXCLUDED.specialization_name,
                source_directory = EXCLUDED.source_directory,
                documents_processed = EXCLUDED.documents_processed,
                detected_domain = EXCLUDED.detected_domain,
                detected_subdomain = EXCLUDED.detected_subdomain,
                confidence = EXCLUDED.confidence,
                subjects = EXCLUDED.subjects,
                technical_skills = EXCLUDED.technical_skills,
                transversal_skills = EXCLUDED.transversal_skills,
                methodologies = EXCLUDED.methodologies,
                tools = EXCLUDED.tools,
                platforms = EXCLUDED.platforms,
                technologies = EXCLUDED.technologies,
                bibliography = EXCLUDED.bibliography,
                keywords = EXCLUDED.keywords,
                occupational_profiles = EXCLUDED.occupational_profiles,
                real_market_gaps = EXCLUDED.real_market_gaps,
                strengthening_areas = EXCLUDED.strengthening_areas,
                redundancies = EXCLUDED.redundancies,
                labor_roles = EXCLUDED.labor_roles,
                benchmarking = EXCLUDED.benchmarking,
                scores = EXCLUDED.scores,
                executive_narrative = EXCLUDED.executive_narrative,
                raw_context = EXCLUDED.raw_context,
                updated_at = now()
            """,
            (
                specialization["id"],
                specialization["nombre"],
                str(source_dir),
                context["documents_processed"],
                context["detected_domain"],
                context["detected_subdomain"],
                context["confidence"],
                Json(context["subjects"]),
                Json(context["technical_skills"]),
                Json(context["transversal_skills"]),
                Json(context["methodologies"]),
                Json(context["tools"]),
                Json(context["platforms"]),
                Json(context["technologies"]),
                Json(context["bibliography"]),
                Json(context["keywords"]),
                Json(context["occupational_profiles"]),
                Json(context["real_market_gaps"]),
                Json(context["strengthening_areas"]),
                Json(context["redundancies"]),
                Json(context["labor_roles"]),
                Json(context["benchmarking"]),
                Json(context["scores"]),
                context["executive_narrative"],
                Json(context),
            ),
        )

        keyword_rows = []
        for subject in context["subjects"]:
            micro_id = subject.get("microcurriculo_id")
            if not micro_id:
                continue
            for item in subject.get("keywords", [])[:30]:
                keyword_rows.append(
                    (
                        micro_id,
                        specialization["id"],
                        item["name"],
                        "keyword",
                        item["frequency"],
                        0.72,
                        subject.get("source_document"),
                    )
                )
        if keyword_rows:
            execute_values(
                cur,
                """
                INSERT INTO public.microcurriculo_keywords (
                    microcurriculo_id, specialization_id, keyword, keyword_type,
                    frequency, confidence_score, source_document
                )
                VALUES %s
                ON CONFLICT (microcurriculo_id, keyword, keyword_type)
                DO UPDATE SET
                    frequency = EXCLUDED.frequency,
                    confidence_score = EXCLUDED.confidence_score
                """,
                keyword_rows,
            )


def index_specialization(source_dir: Path, specialization_name: str, *, target: str, persist: bool) -> dict[str, Any]:
    config = get_local_config() if target == "local" else get_railway_config()
    configure_backend_db_env(config)
    documents = list_documents(source_dir)
    if not documents:
        raise RuntimeError(f"No hay documentos soportados en {source_dir}")

    with connect(config) as conn:
        conn.autocommit = False
        apply_schema(conn)
        specialization = resolve_specialization(conn, specialization_name)

    subjects: list[dict[str, Any]] = []
    counters = {
        "technical_skills": Counter(),
        "transversal_skills": Counter(),
        "methodologies": Counter(),
        "tools": Counter(),
        "platforms": Counter(),
        "technologies": Counter(),
        "bibliography": Counter(),
        "keywords": Counter(),
    }
    domain_counter: Counter[str] = Counter()
    confidence_values: list[float] = []

    for path in documents:
        result = process_microcurriculum(
            path,
            db_name=config.dbname,
            persist=False,
            persist_original=False,
            market_skills=VISUAL_ANALYTICS_MARKET_SKILLS,
        )
        parsed = result["parsed"]
        skills = result["skills"]
        skill_names = [str(skill["skill_normalized"]) for skill in skills]
        buckets: dict[str, list[str]] = defaultdict(list)
        for skill in skills:
            bucket = classify_bucket(skill)
            name = str(skill["skill_normalized"])
            buckets[bucket].append(name)
            counters[bucket][name] += 1
            counters["technologies"][name] += 1
        for item in parsed.get("bibliografia") or []:
            counters["bibliography"][item[:180]] += 1
        keywords = extract_keywords(result["document"]["clean_text"], skill_names)
        counters["keywords"].update(keywords)
        for canonical in VISUAL_ANALYTICS_MARKET_SKILLS:
            if keywords.get(canonical, 0) > 0:
                counters["technologies"][canonical] += 1
        domain = result["domain_prediction"]["domain"]
        domain_counter[domain] += 1
        confidence_values.append(float(result["domain_prediction"].get("confidence", 0) or 0))
        subjects.append(
            {
                "document_name": path.name,
                "source_document": str(path),
                "microcurriculo_id": result.get("microcurriculo_id"),
                "asignatura": parsed.get("asignatura") or path.stem,
                "programa": parsed.get("programa") or specialization_name,
                "semestre": parsed.get("semestre"),
                "creditos": parsed.get("creditos"),
                "competencias": parsed.get("competencias") or [],
                "resultados_aprendizaje": parsed.get("resultados_aprendizaje") or [],
                "contenidos": parsed.get("contenidos") or [],
                "metodologias": parsed.get("metodologias") or [],
                "herramientas": parsed.get("herramientas") or [],
                "bibliografia": parsed.get("bibliografia") or [],
                "skills": sorted(set(skill_names)),
                "technical_skills": sorted(set(buckets.get("technical_skills", []))),
                "tools": sorted(set(buckets.get("tools", []))),
                "platforms": sorted(set(buckets.get("platforms", []))),
                "methodologies": sorted(set(buckets.get("methodologies", []))),
                "domain": domain,
                "confidence": result["domain_prediction"].get("confidence", 0),
                "keywords": unique_sorted(keywords, limit=20),
                "skill_details": skills,
                "document": result["document"],
                "score": result["scores"].get("pertinencia_curricular", 0),
            }
        )

    detected = {item["name"] for item in unique_sorted(counters["technologies"], limit=200)}
    market = set(VISUAL_ANALYTICS_MARKET_SKILLS)
    shared = detected & market
    gaps = sorted(market - detected)
    strengthening = sorted(skill for skill in shared if counters["technologies"][skill] <= 2)
    real_gaps = [
        {"name": gap, "priority": "alta" if gap in {"mlops", "dataops", "ia generativa", "lakehouse"} else "media"}
        for gap in gaps
    ]
    context = {
        "specialization_id": specialization["id"],
        "specialization_name": specialization["nombre"],
        "source_directory": str(source_dir),
        "documents_processed": len(subjects),
        "detected_domain": domain_counter.most_common(1)[0][0] if domain_counter else "analitica",
        "detected_subdomain": "visual_analytics_big_data",
        "confidence": round(sum(confidence_values) / max(1, len(confidence_values)), 4),
        "subjects": subjects,
        "technical_skills": unique_sorted(counters["technical_skills"], limit=60),
        "transversal_skills": unique_sorted(counters["transversal_skills"], limit=40),
        "methodologies": unique_sorted(counters["methodologies"], limit=40),
        "tools": unique_sorted(counters["tools"], limit=60),
        "platforms": unique_sorted(counters["platforms"], limit=40),
        "technologies": unique_sorted(counters["technologies"], limit=80),
        "bibliography": unique_sorted(counters["bibliography"], limit=30),
        "keywords": unique_sorted(counters["keywords"], limit=80),
        "occupational_profiles": VISUAL_ANALYTICS_ROLES,
        "real_market_gaps": real_gaps,
        "strengthening_areas": [{"name": item, "reason": "Detectado en el currículo, requiere mayor profundidad aplicada"} for item in strengthening],
        "redundancies": detect_redundancies(subjects),
        "labor_roles": VISUAL_ANALYTICS_ROLES,
        "benchmarking": BENCHMARKING_REFERENCES,
        "scores": {
            "curricular_relevance": round((len(shared) / max(1, len(market))) * 100, 2),
            "market_skill_coverage": round((len(shared) / max(1, len(market))) * 100, 2),
            "documents_processed": len(subjects),
            "detected_market_skills": len(shared),
            "real_gap_count": len(real_gaps),
        },
        "executive_narrative": build_narrative(shared, gaps, len(subjects)),
    }

    if persist:
        with connect(config) as conn:
            conn.autocommit = False
            try:
                apply_schema(conn)
                persist_context(conn, specialization, source_dir, context)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "visual_analytics_microcurriculum_context.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (OUTPUTS / "visual_analytics_microcurriculum_context.md").write_text(
        "# Contexto curricular Visual Analytics y Big Data\n\n"
        f"Documentos procesados: {context['documents_processed']}\n\n"
        f"{context['executive_narrative']}\n\n"
        "## Skills detectadas\n\n"
        + "\n".join(f"- {item['name']} ({item['frequency']})" for item in context["technologies"][:25])
        + "\n\n## Brechas reales\n\n"
        + "\n".join(f"- {item['name']} ({item['priority']})" for item in context["real_market_gaps"]),
        encoding="utf-8",
    )
    return context


def main() -> int:
    load_dotenv_files()
    parser = argparse.ArgumentParser(description="Indexa microcurrículos reales por especialización.")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--specialization", default="Especialización en Visual Analytics y Big Data")
    parser.add_argument("--target", choices=["railway", "local"], default=os.getenv("MICRO_CONTEXT_DB_TARGET", "railway"))
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()
    context = index_specialization(
        Path(args.source_dir),
        args.specialization,
        target=args.target,
        persist=not args.no_persist,
    )
    print(json.dumps({
        "specialization_id": context["specialization_id"],
        "documents_processed": context["documents_processed"],
        "detected_domain": context["detected_domain"],
        "real_market_gaps": len(context["real_market_gaps"]),
        "output": "outputs/visual_analytics_microcurriculum_context.json",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
