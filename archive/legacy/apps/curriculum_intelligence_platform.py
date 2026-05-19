# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import io
import json
import math
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request


APP_NAME = "Curriculum Intelligence Platform"
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "asturias_scraped_comparison.json"
DB_PATH = BASE_DIR / "curriculum_intelligence.db"


DOMAIN_RULES = {
    "Analítica": ["analitica", "analisis", "data", "datos", "decision", "interpretacion", "metricas", "kpi"],
    "Business Intelligence": ["business intelligence", "inteligencia de negocios", "bi", "tablero", "dashboard"],
    "Visualización": ["visualizacion", "visualizacion de datos", "dashboard", "storytelling", "reportes"],
    "Big Data": ["big data", "etl", "data lake", "data warehouse", "pipelines", "cloud"],
    "Transformación digital": ["transformacion digital", "digital", "innovacion", "tecnologias disruptivas"],
    "Gobierno del dato": ["gobierno del dato", "gobernanza", "calidad", "seguridad", "etica", "lineage"],
    "Estrategia": ["estrategia", "negocio", "proyecto", "competitividad", "gerencia", "planeacion"],
    "Mercadeo / e-commerce": ["mercadeo", "marketing", "e-commerce", "comercio electronico", "segmentacion", "conversion"],
    "Tecnología": ["sql", "python", "bases de datos", "programacion", "arquitectura", "plataformas", "modelado"],
    "Investigación": ["investigacion", "seminario", "metodologia", "validacion", "hipotesis"],
    "Innovación": ["innovacion", "cultura organizativa", "cambio", "diseno", "emprendimiento"],
}

DOMAIN_ORDER = [
    "Analítica",
    "Business Intelligence",
    "Visualización",
    "Big Data",
    "Transformación digital",
    "Gobierno del dato",
    "Estrategia",
    "Mercadeo / e-commerce",
]

ALIAS_EXPANSIONS = {
    "bigdata": "big data",
    "businessintelligence": "business intelligence",
    "inteligenciadenegocios": "inteligencia de negocios",
    "transformaciondigital": "transformacion digital",
    "mercadedigital": "mercadeo digital",
    "comercioelectronico": "comercio electronico",
    "gobiernodato": "gobierno del dato",
}

BLOOM_VERBS = [
    "recordar",
    "comprender",
    "aplicar",
    "analizar",
    "evaluar",
    "crear",
    "interpretar",
    "diseñar",
    "proponer",
    "argumentar",
    "modelar",
    "validar",
    "comparar",
    "diagnosticar",
    "sintetizar",
]

MARKET_JOBS = [
    {
        "title": "Analista de Datos",
        "sector": "Tecnología / BI",
        "skills": ["SQL", "Power BI", "estadística", "dashboards", "storytelling", "visualización de datos"],
    },
    {
        "title": "Analista BI",
        "sector": "Inteligencia de Negocio",
        "skills": ["Business Intelligence", "modelado de datos", "ETL", "KPI", "dashboards", "SQL"],
    },
    {
        "title": "Analista de Marketing Digital",
        "sector": "Mercadeo",
        "skills": ["marketing digital", "analítica web", "segmentación", "SEO", "dashboards", "A/B testing"],
    },
    {
        "title": "Data Governance Analyst",
        "sector": "Gobierno del dato",
        "skills": ["gobierno del dato", "calidad de datos", "seguridad", "etica", "documentación"],
    },
    {
        "title": "Product Analyst",
        "sector": "Producto y negocio",
        "skills": ["SQL", "analítica de negocio", "storytelling", "experimentación", "métricas", "A/B testing"],
    },
    {
        "title": "Líder de Analítica",
        "sector": "Dirección",
        "skills": ["estrategia", "liderazgo", "planeación", "data storytelling", "Power BI", "comunicación ejecutiva"],
    },
    {
        "title": "Data Engineer",
        "sector": "Infraestructura de datos",
        "skills": ["ETL", "pipelines", "cloud", "data lake", "data warehouse", "bases de datos"],
    },
    {
        "title": "Analista Curricular EdTech",
        "sector": "Educación superior",
        "skills": ["benchmarking curricular", "analítica educativa", "reportes", "investigación", "dashboards"],
    },
]

SAAS_PLANS = [
    {
        "name": "Institucional Base",
        "price": "Suscripción anual",
        "features": ["1 universidad", "análisis de microcurrículo", "benchmark básico", "panel ejecutivo"],
    },
    {
        "name": "Bench Pro",
        "price": "Suscripción anual",
        "features": ["benchmark avanzado", "integración con mercado laboral", "simulador de impacto", "exportación para comité"],
    },
    {
        "name": "Enterprise",
        "price": "Contrato institucional",
        "features": ["multi-facultad", "módulos de acreditación", "capas vectoriales", "tenanting y trazabilidad"],
    },
]

ARCHITECTURE = [
    {"layer": "Frontend", "tech": "React + Tailwind", "why": "Interfaz ejecutiva, filtros, simulador y visualizaciones claras."},
    {"layer": "Backend", "tech": "FastAPI", "why": "APIs para ingestión, scoring, benchmarking y simulación en tiempo real."},
    {"layer": "Datos", "tech": "PostgreSQL + vector DB", "why": "Historial multiuniversidad, analítica y búsqueda semántica."},
    {"layer": "NLP", "tech": "Embeddings + clasificación semántica", "why": "Extracción de competencias, verbos Bloom y temas equivalentes."},
    {"layer": "Integraciones", "tech": "APIs de empleo + scraping estructurado", "why": "Cruce con skills demandadas por el mercado laboral."},
]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def repair_text(value):
    if not isinstance(value, str):
        return value
    if "Ã" not in value and "Â" not in value and "�" not in value:
        return value
    for encoding in ("latin1", "cp1252"):
        try:
            candidate = value.encode(encoding).decode("utf-8")
            if candidate.count("Ã") + candidate.count("Â") < value.count("Ã") + value.count("Â"):
                return candidate
        except Exception:
            pass
    return value


def repair_structure(value):
    if isinstance(value, dict):
        return {repair_text(k): repair_structure(v) for k, v in value.items()}
    if isinstance(value, list):
        return [repair_structure(item) for item in value]
    return repair_text(value)


def load_dataset():
    if DATA_PATH.exists():
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return repair_structure(data)
    return {
        "generatedAt": now_iso(),
        "localProgram": {
            "id": "demo",
            "university": "UniAsturias",
            "program": "Especialización en Inteligencia de Negocios",
            "url": "",
            "modality": "Virtual",
            "duration": "2 semestres",
            "credits": 26,
            "orientation": "Mixta",
            "practiceStyle": "Casos de análisis",
            "subjects": [],
            "skills": [],
            "themes": [],
            "summary": "Programa demo.",
        },
        "benchmarkPrograms": [],
        "skillCatalog": [],
        "errors": [],
    }


def normalize(text):
    text = repair_text(text or "")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for source, target in ALIAS_EXPANSIONS.items():
        text = text.replace(source, target)
    return text


def tokens(text):
    return [token for token in normalize(text).split() if token]


def contains_phrase(text, phrase):
    text_n = normalize(text)
    phrase_n = normalize(phrase)
    if not text_n or not phrase_n:
        return False
    if " " in phrase_n:
        return phrase_n in text_n
    return re.search(rf"\b{re.escape(phrase_n)}\b", text_n) is not None


def overlap_score(a, b):
    ta = set(tokens(a))
    tb = set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def vector_similarity(a, b):
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = sum(float(a.get(k, 0)) * float(b.get(k, 0)) for k in keys)
    na = math.sqrt(sum(float(v) * float(v) for v in a.values()))
    nb = math.sqrt(sum(float(v) * float(v) for v in b.values()))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def pick_domains(text):
    found = []
    for domain, phrases in DOMAIN_RULES.items():
        if any(contains_phrase(text, phrase) for phrase in phrases):
            found.append(domain)
    return found or ["General"]


def pick_bloom_verbs(text):
    text_n = normalize(text)
    return [verb for verb in BLOOM_VERBS if re.search(rf"\b{re.escape(verb)}\b", text_n)]


def infer_practice_style(text):
    n = normalize(text)
    flags = {
        "analytic": any(word in n for word in ["analisis", "analitica", "casos", "interpret", "decisi", "indicador"]),
        "technical": any(word in n for word in ["sql", "python", "program", "herramient", "bases de datos", "etl"]),
        "strategic": any(word in n for word in ["estrateg", "negocio", "liderazgo", "cambio", "direccion"]),
    }
    hits = sum(1 for value in flags.values() if value)
    if hits >= 2:
        return "Mixta"
    if flags["technical"]:
        return "Técnico aplicado"
    if flags["strategic"]:
        return "Estratégico"
    if flags["analytic"]:
        return "Analítico"
    return "Teórico"


def extract_topics(text):
    lines = []
    for raw_line in re.split(r"[\n\r]+", text or ""):
        line = raw_line.strip(" \t-•*")
        if not line:
            continue
        if re.match(r"^\d+[\).\:-]\s+", line):
            line = re.sub(r"^\d+[\).\:-]\s+", "", line)
        if len(line) < 4:
            continue
        lines.append(repair_text(line))
    return list(dict.fromkeys(lines[:10]))


def extract_title(text):
    for raw_line in re.split(r"[\n\r]+", text or ""):
        line = repair_text(raw_line).strip()
        if len(line) > 4 and len(line) < 130:
            if any(marker in normalize(line) for marker in ["asignatura", "curso", "modulo", "unidad", "sílabo", "silabo"]):
                return line
    first = next((repair_text(line).strip() for line in re.split(r"[\n\r]+", text or "") if line.strip()), "")
    return first[:120] if first else "Documento cargado"


def extract_credits(text):
    match = re.search(r"(\d+)\s*(?:cr[eé]ditos?|credits?)", text or "", flags=re.I)
    return int(match.group(1)) if match else None


def collect_strings(value):
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(collect_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(collect_strings(item))
        return out
    if value is None:
        return []
    return [repair_text(str(value))]


def infer_document(text, filename="documento"):
    title = extract_title(text)
    domains = pick_domains(text)
    blooms = pick_bloom_verbs(text)
    topics = extract_topics(text)
    credits = extract_credits(text)
    practice = infer_practice_style(text)
    return {
        "filename": filename,
        "title": title,
        "credits": credits,
        "practiceStyle": practice,
        "topics": topics,
        "bloomVerbs": blooms,
        "domains": domains,
        "excerpt": repair_text((text or "")[:900]),
        "wordCount": len(tokens(text)),
    }


def document_text_from_upload(file_storage):
    filename = file_storage.filename or "documento"
    ext = Path(filename).suffix.lower()
    raw = file_storage.read()
    if ext in {".txt", ".md", ".xml", ".html", ".htm"}:
        return filename, raw.decode("utf-8", errors="ignore")
    if ext in {".csv", ".tsv"}:
        delimiter = "\t" if ext == ".tsv" else ","
        text = raw.decode("utf-8", errors="ignore")
        rows = []
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        for row in reader:
            rows.append(" | ".join(cell.strip() for cell in row if cell))
        return filename, "\n".join(rows)
    if ext == ".json":
        try:
            parsed = json.loads(raw.decode("utf-8", errors="ignore"))
            return filename, "\n".join(collect_strings(parsed))
        except Exception:
            return filename, raw.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return filename, text
        except Exception as exc:
            raise ValueError("El análisis de PDF requiere la librería opcional `pypdf` o exportar el archivo a texto.") from exc
    if ext in {".xlsx", ".xls"}:
        try:
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
            rows = []
            for ws in wb.worksheets[:3]:
                for row in ws.iter_rows(values_only=True):
                    cells = [repair_text(str(cell)) for cell in row if cell is not None and str(cell).strip()]
                    if cells:
                        rows.append(" | ".join(cells))
            return filename, "\n".join(rows)
        except Exception as exc:
            raise ValueError("El análisis de Excel requiere la librería opcional `openpyxl` o exportar a CSV.") from exc
    return filename, raw.decode("utf-8", errors="ignore")


def build_skill_catalog(data):
    catalog = data.get("skillCatalog") or []
    out = []
    for item in catalog:
        out.append(
            {
                "name": repair_text(item.get("name") or item.get("label") or "Skill"),
                "terms": [repair_text(term) for term in item.get("terms") or []],
            }
        )
    return out


def subject_text(subject):
    return " ".join(
        repair_text(part)
        for part in [
            subject.get("title", ""),
            subject.get("type", ""),
            subject.get("semester", ""),
            subject.get("note", ""),
        ]
        if part
    )


def subject_domains(subject):
    return pick_domains(subject_text(subject))


def subject_profile(subject):
    text = subject_text(subject)
    return {"text": text, "domains": Counter(subject_domains(subject)), "blooms": Counter(pick_bloom_verbs(text))}


def program_text(program):
    chunks = [
        program.get("university", ""),
        program.get("program", ""),
        program.get("summary", ""),
        program.get("orientation", ""),
        program.get("practiceStyle", ""),
    ]
    chunks.extend(subject_text(subject) for subject in program.get("subjects") or [])
    chunks.extend(skill.get("skill") or skill.get("name") or "" for skill in program.get("skills") or [])
    chunks.extend(theme.get("theme") or theme.get("name") or "" for theme in program.get("themes") or [])
    return " ".join(repair_text(chunk) for chunk in chunks if chunk)


def guess_domain_from_label(label):
    n = normalize(label)
    if "big data" in n:
        return "Big Data"
    if "visual" in n:
        return "Visualización"
    if "gobierno" in n or "calidad" in n:
        return "Gobierno del dato"
    if "mercadeo" in n or "marketing" in n or "e commerce" in n or "comercio electronico" in n:
        return "Mercadeo / e-commerce"
    if "estrateg" in n or "negocio" in n:
        return "Estrategia"
    if "digital" in n or "innovacion" in n:
        return "Transformación digital"
    if "bi" in n or "inteligencia de negocios" in n:
        return "Business Intelligence"
    if "analit" in n or "analisis" in n or "datos" in n:
        return "Analítica"
    if "investig" in n:
        return "Investigación"
    return "General"


def program_profile(program):
    counter = Counter()
    skills = Counter()
    blooms = Counter()
    for subject in program.get("subjects") or []:
        profile = subject_profile(subject)
        counter.update(profile["domains"])
        blooms.update(profile["blooms"])
    for skill in program.get("skills") or []:
        label = repair_text(skill.get("skill") or skill.get("name") or "")
        if label:
            skills[label] += int(skill.get("count") or skill.get("weight") or 1)
    for theme in program.get("themes") or []:
        label = repair_text(theme.get("theme") or theme.get("name") or "")
        if label:
            counter[guess_domain_from_label(label)] += int(theme.get("count") or 1)
    text = program_text(program)
    for domain in pick_domains(text):
        counter[domain] += 2
    return {
        "domains": counter,
        "skills": skills,
        "blooms": blooms,
        "credits": int(program.get("credits") or 0),
        "orientation": repair_text(program.get("orientation") or ""),
        "practiceStyle": repair_text(program.get("practiceStyle") or ""),
        "summary": repair_text(program.get("summary") or ""),
    }


def market_profile(jobs):
    counter = Counter()
    skills = Counter()
    for job in jobs:
        title = repair_text(job["title"])
        counter.update(pick_domains(title))
        for skill in job.get("skills") or []:
            skill_name = repair_text(skill)
            skills[skill_name] += 1
            counter[guess_domain_from_label(skill_name)] += 1
    return {"domains": counter, "skills": skills}


def normalize_counter(counter):
    if not counter:
        return {}
    max_value = max(counter.values()) or 1
    return {key: round((value / max_value) * 100, 1) for key, value in counter.items()}


def program_similarity(base_program, other_program):
    base = program_profile(base_program)
    other = program_profile(other_program)
    domain_sim = vector_similarity(base["domains"], other["domains"])
    skill_sim = vector_similarity(base["skills"], other["skills"])
    credit_sim = 1 - abs(base["credits"] - other["credits"]) / max(base["credits"] or 1, other["credits"] or 1, 1)
    orientation_sim = 1.0 if normalize(base["orientation"]) == normalize(other["orientation"]) else 0.55
    practice_sim = 1.0 if normalize(base["practiceStyle"]) == normalize(other["practiceStyle"]) else 0.55
    return max(0.0, min(1.0, 0.38 * domain_sim + 0.22 * skill_sim + 0.18 * credit_sim + 0.11 * orientation_sim + 0.11 * practice_sim))


def subject_similarity(query, subject):
    qtext = query["text"] if isinstance(query, dict) else str(query)
    stxt = subject_text(subject)
    q_domains = Counter(pick_domains(qtext))
    s_domains = Counter(subject_domains(subject))
    q_blooms = Counter(pick_bloom_verbs(qtext))
    s_blooms = Counter(subject_profile(subject)["blooms"])
    return max(
        0.0,
        min(
            1.0,
            0.45 * overlap_score(qtext, stxt)
            + 0.2 * vector_similarity(q_domains, s_domains)
            + 0.15 * vector_similarity(q_blooms, s_blooms)
            + 0.2 * (1.0 if normalize(qtext) and normalize(qtext) in normalize(stxt) else 0.0),
        ),
    )


def query_kind(query):
    n = normalize(query)
    if any(token in n for token in ["programa", "especializacion", "especialización", "posgrado", "malla"]):
        return "program"
    if any(token in n for token in ["asignatura", "curso", "sílabo", "silabo", "materia", "modulo"]):
        return "subject"
    return "auto"


def derive_query_text(query, text):
    parts = [query or "", text or ""]
    return " ".join(part for part in parts if part).strip()


def local_subjects():
    return DATA.get("localProgram", {}).get("subjects") or []


def benchmark_programs():
    return DATA.get("benchmarkPrograms") or []


def all_benchmark_subjects():
    items = []
    for program in benchmark_programs():
        for subject in program.get("subjects") or []:
            items.append(
                {
                    "title": repair_text(subject.get("title") or ""),
                    "credits": subject.get("credits"),
                    "university": repair_text(program.get("university") or ""),
                    "program": repair_text(program.get("program") or ""),
                    "summary": repair_text(program.get("summary") or ""),
                    "raw": subject,
                }
            )
    return items


def detect_redundancies(subjects):
    pairs = []
    for i, a in enumerate(subjects):
        for b in subjects[i + 1 :]:
            title_a = repair_text(a.get("title") or "")
            title_b = repair_text(b.get("title") or "")
            score = overlap_score(title_a, title_b)
            a_norm = normalize(title_a)
            b_norm = normalize(title_b)
            if score >= 0.28 or (("innovacion" in a_norm and "transformacion" in b_norm) or ("innovacion" in b_norm and "transformacion" in a_norm)):
                pairs.append({"left": title_a, "right": title_b, "score": round(max(score, 0.5), 3)})
    return sorted(pairs, key=lambda item: item["score"], reverse=True)[:5]


def best_benchmark_profile():
    programs = benchmark_programs()
    if not programs:
        return None, 0.0
    ranked = sorted(
        ((program, program_similarity(DATA.get("localProgram", {}), program)) for program in programs),
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked[0]


def profile_to_domain_scores(profile):
    return {domain: round(profile["domains"].get(domain, 0) * 100, 1) for domain in DOMAIN_ORDER}


def market_demand():
    return normalize_counter(market_profile(MARKET_JOBS)["skills"])


def build_cci_components():
    local = DATA.get("localProgram", {})
    local_prof = program_profile(local)
    market_prof = market_profile(MARKET_JOBS)
    best_benchmark, benchmark_score = best_benchmark_profile()

    local_coverage = len([domain for domain in DOMAIN_ORDER if local_prof["domains"].get(domain)]) / max(len(DOMAIN_ORDER), 1)
    market_alignment = vector_similarity(local_prof["skills"], market_prof["skills"])
    if not market_alignment:
        market_alignment = vector_similarity(local_prof["domains"], market_prof["domains"])

    benchmark_fit = benchmark_score
    compactness = max(0.0, 1.0 - abs(int(local.get("credits") or 24) - 24) / 12)
    practice_readiness = 1.0 if "analisis" in normalize(local.get("practiceStyle") or "") else 0.8

    cci = round(
        100
        * (
            0.33 * market_alignment
            + 0.27 * benchmark_fit
            + 0.18 * local_coverage
            + 0.12 * compactness
            + 0.10 * practice_readiness
        )
    )
    cci = max(0, min(100, cci))

    benchmark_summary = {
        "name": repair_text(best_benchmark.get("university") if best_benchmark else "Sin referente"),
        "program": repair_text(best_benchmark.get("program") if best_benchmark else ""),
        "score": round(benchmark_fit * 100, 1),
    }
    return {
        "cci": cci,
        "marketAlignment": round(market_alignment * 100, 1),
        "benchmarkFit": round(benchmark_fit * 100, 1),
        "coverage": round(local_coverage * 100, 1),
        "compactness": round(compactness * 100, 1),
        "practiceReadiness": round(practice_readiness * 100, 1),
        "benchmark": benchmark_summary,
    }


def build_gap_list():
    local_prof = program_profile(DATA.get("localProgram", {}))
    market = market_profile(MARKET_JOBS)
    gaps = []
    local_skills = {repair_text(item.get("skill") or item.get("name") or "") for item in DATA.get("localProgram", {}).get("skills") or []}
    for skill, count in market["skills"].most_common(10):
        if skill not in local_skills:
            gaps.append({"label": repair_text(skill), "priority": "Alta" if count >= 2 else "Media", "demand": count})
    if not gaps:
        for domain in DOMAIN_ORDER:
            market_value = market["domains"].get(domain, 0)
            local_value = local_prof["domains"].get(domain, 0)
            if market_value > local_value:
                gaps.append({"label": domain, "priority": "Alta" if market_value - local_value > 1 else "Media", "demand": market_value - local_value})
    return gaps[:6]


def match_action_for_subject(subject):
    title = normalize(subject.get("title") or "")
    if "innovacion" in title and "transformacion" in title:
        return "Fusionar", "Comparte núcleo conceptual con transformación digital."
    if "transformacion" in title or "digital" in title:
        return "Actualizar", "Debe enfatizar cambio, adopción y decisión, no solo descripción del fenómeno."
    if "tendencias" in title:
        return "Actualizar", "Funciona mejor como vigilancia estratégica o electiva transversal."
    if "economia colaborativa" in title:
        return "Electiva", "Es periférica al núcleo BI y puede moverse a transversal."
    if "big data" in title or "analitica" in title or "inteligencia de negocios" in title:
        return "Conservar", "Es núcleo duro del programa y responde a demanda laboral."
    return "Actualizar", "Conviene ajustar temario y resultados de aprendizaje para reforzar el foco analítico."


def subject_matrix():
    rows = []
    for subject in local_subjects():
        action, reason = match_action_for_subject(subject)
        rows.append(
            {
                "subject": repair_text(subject.get("title") or ""),
                "credits": int(subject.get("credits") or 0),
                "semester": repair_text(subject.get("semester") or ""),
                "kind": repair_text(subject.get("type") or ""),
                "action": action,
                "reason": reason,
            }
        )
    return rows


def radar_profiles():
    local = program_profile(DATA.get("localProgram", {}))
    benchmark = program_profile(best_benchmark_profile()[0] or {})
    market = market_profile(MARKET_JOBS)
    return {
        "categories": DOMAIN_ORDER,
        "series": {
            "Programa local": profile_to_domain_scores(local),
            "Benchmark líder": profile_to_domain_scores(benchmark),
            "Mercado laboral": profile_to_domain_scores({"domains": market["domains"]}),
        },
    }


def simulate_scenario(credit_delta=0, market_bonus=0, benchmark_bonus=0, redundancy_cut=0):
    base = build_cci_components()
    credit_delta = int(credit_delta or 0)
    market_bonus = int(market_bonus or 0)
    benchmark_bonus = int(benchmark_bonus or 0)
    redundancy_cut = int(redundancy_cut or 0)

    adjusted = base["cci"]
    adjusted += market_bonus * 3
    adjusted += benchmark_bonus * 3
    adjusted += redundancy_cut * 2
    adjusted += max(0, -credit_delta) * 2
    adjusted -= max(0, credit_delta) * 2
    adjusted = max(0, min(100, adjusted))
    return {"baseline": base["cci"], "adjusted": adjusted, "delta": adjusted - base["cci"]}


def safe_json_dump(data):
    dumped = json.dumps(data, ensure_ascii=False)
    return dumped.replace("</", "<\\/")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant TEXT,
                query TEXT,
                mode TEXT,
                cci INTEGER,
                payload TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant TEXT,
                filename TEXT,
                source_kind TEXT,
                payload TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_analysis(tenant, query, mode, payload):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO analysis_runs (tenant, query, mode, cci, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (tenant, query, mode, int(payload.get("cci") or 0), json.dumps(payload, ensure_ascii=False), now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def save_ingest(tenant, filename, source_kind, payload):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO ingests (tenant, filename, source_kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant, filename, source_kind, json.dumps(payload, ensure_ascii=False), now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_history(limit=8):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT tenant, query, mode, cci, created_at FROM analysis_runs ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def build_skill_catalog(data):
    catalog = data.get("skillCatalog") or []
    out = []
    for item in catalog:
        out.append({"name": repair_text(item.get("name") or item.get("label") or "Skill"), "terms": [repair_text(term) for term in item.get("terms") or []]})
    return out


def build_bootstrap():
    local = DATA.get("localProgram", {})
    benchmarks = benchmark_programs()
    cci = build_cci_components()
    market = market_profile(MARKET_JOBS)
    return {
        "appName": APP_NAME,
        "generatedAt": DATA.get("generatedAt") or now_iso(),
        "localProgram": local,
        "benchmarkPrograms": benchmarks,
        "skillCatalog": build_skill_catalog(DATA),
        "marketJobs": MARKET_JOBS,
        "marketSkills": normalize_counter(market["skills"]),
        "architecture": ARCHITECTURE,
        "plans": SAAS_PLANS,
        "history": fetch_history(),
        "matrix": subject_matrix(),
        "cci": cci,
        "radar": radar_profiles(),
        "stats": {
            "localSubjects": len(local_subjects()),
            "benchmarks": len(benchmarks),
            "benchmarkSubjects": sum(len(program.get("subjects") or []) for program in benchmarks),
            "credits": int(local.get("credits") or 0),
        },
    }


DATA = load_dataset()
init_db()


APP_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{ app_name }}</title>
  <style>
    :root{--bg:#07111b;--panel:rgba(12,25,42,.92);--line:rgba(161,187,213,.16);--text:#edf4fa;--muted:#a8bbc9;--accent:#63d2c6;--accent2:#8fb8ff;--warn:#ffd27f;--radius:22px;--shadow:0 20px 50px rgba(0,0,0,.35);--font-display:"Bahnschrift","Aptos Display","Trebuchet MS",sans-serif;--font-body:"Trebuchet MS","Segoe UI",sans-serif}
    *{box-sizing:border-box} html{scroll-behavior:smooth}
    body{margin:0;color:var(--text);font-family:var(--font-body);background:radial-gradient(circle at top left, rgba(99,210,198,.12), transparent 28%),radial-gradient(circle at top right, rgba(143,184,255,.12), transparent 26%),linear-gradient(180deg,#07111b 0%,#0b1725 34%,#06111c 100%);min-height:100vh}
    body::before{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);background-size:52px 52px;opacity:.55;mask-image:linear-gradient(180deg, rgba(0,0,0,.92), transparent 100%)}
    .shell{width:min(1420px, calc(100% - 30px));margin:0 auto;padding:18px 0 44px}
    .topbar{display:flex;justify-content:space-between;align-items:center;gap:14px;position:sticky;top:0;z-index:12;padding:10px 0;backdrop-filter:blur(12px)}
    .brand{display:flex;flex-direction:column;gap:4px}.brand small{color:var(--muted);text-transform:uppercase;letter-spacing:.12em;font-size:.72rem}.brand strong{font-family:var(--font-display);font-size:1.08rem}
    .actions{display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end}
    .btn{border:1px solid var(--line);color:var(--text);background:rgba(255,255,255,.04);padding:10px 14px;border-radius:999px;cursor:pointer;text-decoration:none;font-size:.92rem}
    .btn:hover{background:rgba(255,255,255,.08)}
    .panel{background:linear-gradient(180deg, rgba(18,36,58,.93), rgba(8,18,30,.97));border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
    .hero{display:grid;grid-template-columns:1.5fr .95fr;gap:16px;margin:4px 0 18px}
    .hero-main{padding:26px;position:relative;overflow:hidden}
    .hero-main::after{content:"";position:absolute;inset:auto -80px -100px auto;width:300px;height:300px;border-radius:50%;background:radial-gradient(circle, rgba(99,210,198,.38), transparent 65%);filter:blur(6px);pointer-events:none}
    .eyebrow{display:inline-flex;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(99,210,198,.11);color:#d7fff8;border:1px solid rgba(99,210,198,.22);text-transform:uppercase;letter-spacing:.08em;font-size:.74rem}
    h1{margin:16px 0 12px;font-family:var(--font-display);font-size:clamp(2rem,4vw,3.75rem);line-height:.96;letter-spacing:-.045em;max-width:15ch}
    .lede{margin:0;max-width:72ch;color:#d9e5ef;line-height:1.65;font-size:1.02rem}
    .meta,.kpis,.pricing,.three,.two,.grid{display:grid;gap:12px}
    .meta{grid-template-columns:repeat(4,minmax(0,1fr));margin-top:22px}
    .kpis{grid-template-columns:repeat(4,minmax(0,1fr))}
    .pricing,.three{grid-template-columns:repeat(3,minmax(0,1fr))}
    .two{grid-template-columns:1.08fr .92fr}
    .grid{grid-template-columns:360px 1fr;align-items:start}
    .hero-side{padding:20px;display:grid;gap:12px;align-content:start}
    .mini,.card,.kpi,.stat{border:1px solid var(--line);background:rgba(255,255,255,.03);border-radius:18px;padding:14px}
    .mini strong,.card h3,.kpi span,.stat span{display:block}
    .mini p,.card p{margin:0;color:var(--muted);line-height:1.55}
    .sidebar{padding:16px;position:sticky;top:78px;height:max-content}
    .field{margin-bottom:12px}.field label{display:block;margin-bottom:6px;font-size:.92rem;color:#dbe8f4}
    input,select,textarea{width:100%;border-radius:14px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.05);color:var(--text);padding:11px 12px;font-family:var(--font-body)}
    textarea{min-height:140px;resize:vertical}
    .help{padding:12px 14px;border-radius:14px;border:1px solid rgba(244,184,96,.22);background:rgba(244,184,96,.08);color:#ffe8bf;line-height:1.55;font-size:.93rem}
    .row{display:flex;gap:10px;flex-wrap:wrap}
    .chip,.badge{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;font-size:.78rem;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.03)}
    .badge.good{border-color:rgba(141,224,172,.25);background:rgba(141,224,172,.08);color:#dcffe7}.badge.warn{border-color:rgba(244,184,96,.25);background:rgba(244,184,96,.08);color:#ffe7bb}.badge.info{border-color:rgba(143,184,255,.25);background:rgba(143,184,255,.08);color:#e3efff}
    .section{padding:18px}.section h2{margin:0 0 8px;font-family:var(--font-display);font-size:1.28rem}.section .sub{margin:0 0 16px;color:var(--muted);line-height:1.55}
    .score{display:flex;gap:14px;align-items:center;margin-top:10px}.ring{--p:0;width:92px;height:92px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--accent) calc(var(--p)*1%), rgba(255,255,255,.08) 0)}.ring span{width:68px;height:68px;border-radius:50%;display:grid;place-items:center;background:#0f1c2d;font-family:var(--font-display);font-size:1.15rem}
    .list{display:grid;gap:10px}.item{padding:12px 14px;border-radius:14px;background:rgba(255,255,255,.03);border-left:4px solid var(--accent);border:1px solid rgba(255,255,255,.08)}.item strong{display:block;margin-bottom:4px}.item span{color:var(--muted);font-size:.92rem;line-height:1.5}
    .table-wrap{overflow:auto;border-radius:16px;border:1px solid var(--line)}table{width:100%;min-width:980px;border-collapse:collapse;background:rgba(255,255,255,.02)}th,td{padding:12px 14px;border-bottom:1px solid rgba(161,187,213,.12);vertical-align:top;text-align:left;font-size:.94rem}th{background:rgba(255,255,255,.04)}
    .bar-list{display:grid;gap:12px}.bar-row{display:grid;grid-template-columns:180px 1fr 60px;gap:12px;align-items:center}.bar-track{position:relative;height:12px;border-radius:999px;background:rgba(255,255,255,.06);overflow:hidden;border:1px solid rgba(255,255,255,.08)}.bar-fill{position:absolute;inset:0 auto 0 0;border-radius:999px;background:linear-gradient(90deg, var(--accent), var(--accent2))}.bar-value{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
    .radar-wrap{display:grid;grid-template-columns:1fr 320px;gap:16px;align-items:center}.radar{width:100%;aspect-ratio:1 / 1;background:radial-gradient(circle at center, rgba(255,255,255,.03), transparent 68%);border-radius:20px;border:1px solid var(--line)}.legend{display:grid;gap:10px}
    .price{font-family:var(--font-display);font-size:1.3rem}.foot{padding:20px;margin-top:18px;color:var(--muted);line-height:1.6;font-size:.9rem}
    @media (max-width:1080px){.hero,.grid,.two,.radar-wrap,.pricing,.kpis,.meta,.three{grid-template-columns:1fr}.sidebar{position:relative;top:auto}.bar-row{grid-template-columns:1fr}.bar-value{text-align:left}.actions{justify-content:flex-start}}
    @media print{body{background:#fff;color:#000}body::before,.topbar,.actions,.sidebar .buttons{display:none !important}.panel{box-shadow:none !important}}
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <small>Curriculum intelligence para educación superior</small>
        <strong>{{ app_name }}</strong>
      </div>
      <div class="actions">
        <a class="btn" href="#analisis">Análisis</a>
        <a class="btn" href="#benchmark">Benchmark</a>
        <a class="btn" href="#saaS">SaaS</a>
        <button class="btn" id="printBtn">PDF</button>
      </div>
    </header>
    <section class="panel hero">
      <div class="hero-main">
        <div class="eyebrow">Microcurrículo · benchmark · mercado laboral · CCI</div>
        <h1>Convierte el microcurrículo en inteligencia accionable.</h1>
        <p class="lede">Esta plataforma compara asignaturas y programas entre universidades, integra señales del mercado laboral, detecta vacíos y redundancias, y genera recomendaciones estratégicas para fortalecer competitividad.</p>
        <div class="meta" id="metaCards"></div>
      </div>
      <aside class="panel hero-side">
        <div class="mini"><strong>Arquitectura objetivo</strong><p>Frontend React + Tailwind, backend FastAPI, PostgreSQL con capa vectorial y analítica semántica por embeddings.</p></div>
        <div class="mini"><strong>Modelo SaaS</strong><p>Suscripción anual por universidad con módulos premium de benchmarking avanzado, mercado laboral y acreditación.</p></div>
        <div class="mini"><strong>Estado actual</strong><p>Demo conectada al benchmark real de UniAsturias y a un catálogo de mercado laboral de referencia.</p></div>
      </aside>
    </section>
    <div class="grid">
      <aside class="panel sidebar">
        <div class="field"><label>Universidad / tenant</label><input id="tenantInput" value="UniAsturias"></div>
        <div class="field"><label>Buscar asignatura o programa</label><input id="queryInput" placeholder="Ejemplo: inteligencia de negocios"></div>
        <div class="field"><label>Modo de análisis</label><select id="modeSelect"><option value="auto">Auto</option><option value="subject">Asignatura</option><option value="program">Programa</option></select></div>
        <div class="field"><label>Ámbito</label><select id="scopeSelect"><option value="all">Todo</option><option value="local">Solo local</option><option value="benchmark">Solo universidades</option><option value="market">Solo mercado</option></select></div>
        <div class="field"><label>Pega un sílabo o microcurrículo</label><textarea id="textInput" placeholder="Título, créditos, resultados de aprendizaje, temas, bibliografía, notas metodológicas..."></textarea></div>
        <div class="field"><label>Archivo</label><input id="fileInput" type="file" accept=".txt,.md,.csv,.tsv,.json,.pdf,.xlsx,.xls"></div>
        <div class="row buttons"><button class="btn" id="analyzeBtn">Analizar y comparar</button><button class="btn" id="ingestBtn">Preanalizar sílabo</button><button class="btn" id="resetBtn">Limpiar</button></div>
        <div class="field" style="margin-top:14px">
          <label>Simulador de impacto</label>
          <div class="card">
            <div class="field"><label>Variación de créditos</label><input id="creditDelta" type="range" min="-6" max="4" step="1" value="-2"></div>
            <div class="field"><label>Mejora de mercado</label><input id="marketBonus" type="range" min="0" max="6" step="1" value="2"></div>
            <div class="field"><label>Mejora benchmark</label><input id="benchmarkBonus" type="range" min="0" max="6" step="1" value="2"></div>
            <div class="field"><label>Redundancia resuelta</label><input id="redundancyCut" type="range" min="0" max="4" step="1" value="1"></div>
            <div class="row buttons"><button class="btn" id="simulateBtn">Simular</button><button class="btn" data-preset="24">Llevar a 24</button><button class="btn" data-preset="merge">Fusionar</button></div>
          </div>
        </div>
        <div class="help"><strong>Ingesta multimodal:</strong> texto, CSV, JSON, PDF y Excel. Si un formato requiere librería opcional, la respuesta lo indicará sin romper la navegación.</div>
      </aside>
      <main class="content">
        <section class="panel section" id="analisis"><h2>Panorama ejecutivo</h2><p class="sub">Resumen operativo para vicerrectoría: CCI, compatibilidad con el mercado y cercanía con universidades benchmark.</p><div class="kpis" id="kpiCards"></div></section>
        <section class="panel section"><div class="two"><div class="card"><h3>Mejor coincidencia</h3><div id="bestMatch"></div></div><div class="card"><h3>Recomendaciones</h3><div class="list" id="recommendations"></div></div></div></section>
        <section class="panel section"><div class="radar-wrap"><div><h2>Radar de competencias</h2><p class="sub">Comparación entre programa local, benchmark líder y mercado laboral. El gráfico se actualiza con la búsqueda.</p><svg id="radarSvg" class="radar" viewBox="0 0 420 420" preserveAspectRatio="xMidYMid meet"></svg></div><div class="legend"><div class="mini"><strong>Lectura</strong><p>El polígono más amplio indica mayor cobertura. La meta es acercar el programa local al mercado sin perder la identidad académica.</p></div><div class="mini"><strong>Estado del CCI</strong><p id="cciNarrative">Cargando...</p></div></div></div></section>
        <section class="panel section" id="benchmark"><h2>Benchmarking inteligente</h2><p class="sub">Universidades y asignaturas más cercanas a la consulta. Útil para justificar actualización parcial, fusiones o paso a electiva.</p><div class="bar-list" id="programBars"></div></section>
