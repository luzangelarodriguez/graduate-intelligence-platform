# -*- coding: utf-8 -*-
import os
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime
from html import escape

from flask import g, redirect, request, url_for


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "alumni_alerts.db")
CATALOG_DATABASE = os.path.join(BASE_DIR, "unir_especializaciones.db")
TICJOB_BI_JOBS_PATH = os.path.join(BASE_DIR, "ticjob_deep_bi_jobs.json")
MARKET_DATA_PATH = os.path.join(BASE_DIR, "unir_market_jobs.json")
UNIR_LOGO_URL = "https://unir.edu.co/wp-content/uploads/sites/2/2022/09/Unir_negativo_blanco.svg"
UNIR_SITE_LABEL = "FundaciÃƒÂ³n UNIR Colombia"
from main import app

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

DEFAULT_PROGRAMS = [
    {"name": "Especializacion en Inteligencia Artificial", "area": "Tecnologia", "description": "IA, machine learning, Python, estadistica y evaluacion de modelos.", "skills": ["machine learning", "python", "estadistica", "deep learning", "nlp", "ciencia de datos"]},
    {"name": "Especializacion en Ingenieria de Software", "area": "Tecnologia", "description": "Arquitectura, testing, APIs, Git y metodologias agiles.", "skills": ["programacion", "arquitectura de software", "testing", "apis", "git", "metodologias agiles", "bases de datos"]},
    {"name": "Especializacion en Visual Analytics y Big Data", "area": "Datos y BI", "description": "Power BI, Tableau, SQL, dashboards y analitica de negocio.", "skills": ["power bi", "tableau", "visualizacion de datos", "sql", "big data", "dashboards", "analitica de negocio"]},
    {"name": "Especializacion en Pedagogia y Docencia", "area": "Educacion", "description": "Didactica, curriculo, evaluacion, inclusion y gestion educativa.", "skills": ["didactica", "curriculo", "evaluacion", "inclusion", "gestion educativa", "diseno instruccional"]},
    {"name": "Especializacion en TIC para la EnseÃƒÂ±anza", "area": "Educacion", "description": "LMS, aprendizaje virtual, herramientas digitales y evaluacion en linea.", "skills": ["lms", "aprendizaje virtual", "herramientas digitales", "diseno instruccional", "evaluacion en linea"]},
]

ALIASES = {
    "machine learning": ["aprendizaje automatico", "aprendizaje automÃƒÂ¡tico", "ml"],
    "python": ["python"],
    "estadistica": ["estadistica", "estadÃƒÂ­stica", "statistics"],
    "deep learning": ["deep learning", "redes neuronales profundas"],
    "nlp": ["nlp", "pln", "procesamiento de lenguaje natural"],
    "ciencia de datos": ["ciencia de datos", "data science"],
    "programacion": ["programacion", "programaciÃƒÂ³n", "development", "coding"],
    "arquitectura de software": ["arquitectura de software", "software architecture"],
    "testing": ["testing", "pruebas de software", "qa"],
    "apis": ["api", "apis", "integracion"],
    "git": ["git", "control de versiones"],
    "metodologias agiles": ["agile", "scrum", "kanban", "metodologias agiles", "metodologÃƒÂ­as agiles"],
    "bases de datos": ["bases de datos", "database"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "visualizacion de datos": ["visualizacion", "visualizaciÃƒÂ³n", "dataviz"],
    "sql": ["sql", "consultas sql"],
    "big data": ["big data"],
    "dashboards": ["dashboards", "tableros"],
    "analitica de negocio": ["business intelligence", "bi", "analitica de negocio", "analÃƒÂ­tica de negocio", "inteligencia de negocios"],
    "data analyst": ["data analyst", "analista de datos"],
    "data engineer": ["data engineer", "ingeniero de datos"],
    "etl": ["etl"],
    "elt": ["elt"],
    "data lake": ["data lake", "data lakes"],
    "python": ["python"],
    "pyspark": ["pyspark"],
    "azure data factory": ["azure data factory", "data factory"],
    "azure databricks": ["azure databricks", "databricks"],
    "azure data lake": ["azure data lake"],
    "azure fabric": ["azure fabric"],
    "didactica": ["didactica", "didÃƒÂ¡ctica"],
    "curriculo": ["curriculo", "currÃƒÂ­culo"],
    "evaluacion": ["evaluacion", "evaluaciÃƒÂ³n"],
    "inclusion": ["inclusion", "inclusiÃƒÂ³n"],
    "gestion educativa": ["gestion educativa", "gestiÃƒÂ³n educativa"],
    "diseno instruccional": ["diseno instruccional", "diseÃƒÂ±o instruccional", "instructional design"],
    "lms": ["lms", "moodle", "canvas", "blackboard"],
    "aprendizaje virtual": ["aprendizaje virtual", "e-learning", "elearning", "virtual learning"],
    "herramientas digitales": ["herramientas digitales", "digital tools"],
    "evaluacion en linea": ["evaluacion en linea", "evaluaciÃƒÂ³n en linea", "online assessment"],
    "liderazgo": ["liderazgo", "leadership"],
    "gestion de equipos": ["gestion de equipos", "gestiÃƒÂ³n de equipos"],
    "planeacion": ["planeacion", "planeaciÃƒÂ³n", "planning"],
    "marketing": ["marketing"],
    "marketing digital": ["marketing digital", "digital marketing"],
    "seo": ["seo"],
    "sem": ["sem"],
    "analitica web": ["analitica web", "analÃƒÂ­tica web", "web analytics"],
}

ROLE_HINTS = {
    "analista de datos": ["sql", "power bi", "estadistica", "visualizacion de datos", "analitica de negocio"],
    "data analyst": ["sql", "power bi", "estadistica", "visualizacion de datos", "analitica de negocio"],
    "data scientist": ["machine learning", "python", "estadistica", "ciencia de datos", "deep learning"],
    "ingeniero de software": ["programacion", "arquitectura de software", "testing", "apis", "git", "metodologias agiles"],
    "desarrollador": ["programacion", "arquitectura de software", "testing", "apis", "git"],
    "docente": ["didactica", "curriculo", "evaluacion", "lms", "diseno instruccional"],
    "profesor": ["didactica", "curriculo", "evaluacion", "lms", "diseno instruccional"],
    "coordinador": ["gestion de equipos", "liderazgo", "planeacion"],
    "gerente": ["liderazgo", "planeacion", "marketing", "gestion de equipos"],
    "marketing": ["marketing digital", "analitica web", "seo", "sem"],
}


def now():
    return datetime.now().isoformat(timespec="seconds")


def norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def uniq(items):
    out, seen = [], set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _clean_skill(value):
    return " ".join((value or "").strip().split())


def infer_area(name, skills):
    text = norm(name)
    skill_text = norm(" ".join(skills or []))
    combined = f"{text} {skill_text}"
    if any(term in combined for term in ["inteligencia artificial", "machine learning", "data science", "ciencia de datos"]):
        return "Tecnologia"
    if any(term in combined for term in ["software", "programacion", "desarrollo", "arquitectura"]):
        return "Tecnologia"
    if any(term in combined for term in ["visual analytics", "big data", "inteligencia de negocio", "business intelligence", "analitica", "datos"]):
        return "Datos y BI"
    if any(term in combined for term in ["marketing", "ecommerce", "comercio electronico", "digital"]):
        return "Negocios y Marketing"
    if any(term in combined for term in ["pedagog", "docencia", "educacion", "ensenanza", "enseÃƒÂ±anza"]):
        return "Educacion"
    if any(term in combined for term in ["salud", "sst", "seguridad y salud"]):
        return "Salud"
    if any(term in combined for term in ["derecho", "jurid", "legal"]):
        return "Derecho"
    if any(term in combined for term in ["financ", "contabilidad", "auditor"]):
        return "Finanzas"
    return "Gestion"


def infer_description(name, skills):
    cleaned = ", ".join(uniq([_clean_skill(skill) for skill in skills])[:6])
    if cleaned:
        return f"Programa orientado a {cleaned}."
    return f"Programa orientado a la especializacion en {name}."


def load_unir_catalog_programs():
    if not os.path.exists(CATALOG_DATABASE):
        return []

    conn = sqlite3.connect(CATALOG_DATABASE)
    try:
        rows = conn.execute("SELECT name, skills_json FROM programs ORDER BY name").fetchall()
    finally:
        conn.close()

    programs = []
    for name, skills_json in rows:
        try:
            skills = json.loads(skills_json or "[]")
        except json.JSONDecodeError:
            skills = []
        cleaned_skills = uniq([_clean_skill(skill) for skill in skills])
        programs.append(
            {
                "name": name,
                "area": infer_area(name, cleaned_skills),
                "description": infer_description(name, cleaned_skills),
                "skills": cleaned_skills,
            }
        )
    return programs


def load_ticjob_market():
    market_path = MARKET_DATA_PATH if os.path.exists(MARKET_DATA_PATH) else TICJOB_BI_JOBS_PATH
    if not os.path.exists(market_path):
        return {"metrics": {}, "summary": {}, "jobs": []}
    with open(market_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    jobs = data.get("jobs", []) or []
    return {
        "metrics": data.get("metrics", {}),
        "summary": data.get("summary", {}),
        "jobs": jobs,
        "source": data.get("source", ""),
    }


def market_skill_counter(jobs):
    counter = Counter()
    labels = {}
    for job in jobs:
        for skill in job.get("skills", []) or []:
            skill_name = _clean_skill(skill)
            if not skill_name:
                continue
            key = norm(canon(skill_name) or skill_name)
            if not key:
                continue
            counter[key] += 1
            labels.setdefault(key, canon(skill_name) or skill_name)
    return counter, labels


def compare_program_with_market(program, market_counter, market_labels):
    program_skills = program.get("skills", [])
    matched = []
    missing = []
    for skill in program_skills:
        skill_name = skill.get("skill") if isinstance(skill, dict) else skill
        skill_name = _clean_skill(skill_name)
        key = norm(canon(skill_name) or skill_name)
        if key and key in market_counter:
            matched.append(market_labels.get(key, skill_name))
        else:
            missing.append(skill_name)
    total = len(program_skills)
    score = round((len(matched) / total) * 100) if total else 0
    return {
        "program": program.get("name", ""),
        "area": program.get("area", ""),
        "description": program.get("description", ""),
        "score": score,
        "matched": matched,
        "missing": missing,
        "total_skills": total,
    }


def split_terms(text):
    return [x.strip() for x in re.split(r"[\n,;/|]+", text or "") if x.strip()]


def has_phrase(text, phrase):
    if not text or not phrase:
        return False
    if " " in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def canon(term):
    t = norm(term)
    for label, aliases in ALIASES.items():
        for alias in [label] + aliases:
            if has_phrase(t, norm(alias)):
                return label
    return t or None


def extract_skills(position="", skills_text="", raw_text=""):
    text = norm(" ".join([position or "", skills_text or "", raw_text or ""]))
    skills = [canon(term) for term in split_terms(skills_text)]
    for label, aliases in ALIASES.items():
        if any(has_phrase(text, norm(alias)) for alias in [label] + aliases):
            skills.append(label)
    for hint, items in ROLE_HINTS.items():
        if has_phrase(norm(position), norm(hint)):
            skills.extend(items)
    return uniq(skills)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def ensure_col(conn, table, coldef):
    col = coldef.split()[0]
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {coldef}")


def seed_programs(conn):
    source_programs = load_unir_catalog_programs()
    if not source_programs:
        source_programs = DEFAULT_PROGRAMS

    existing = {
        norm(row["name"])
        for row in conn.execute("SELECT name FROM programs").fetchall()
        if row["name"]
    }

    for program in source_programs:
        if norm(program["name"]) in existing:
            continue
        cur = conn.execute(
            "INSERT INTO programs (name, area, description, active, created_at) VALUES (?, ?, ?, 1, ?)",
            (program["name"], program["area"], program["description"], now()),
        )
        for skill in program["skills"]:
            conn.execute(
                "INSERT INTO program_skills (program_id, skill, weight) VALUES (?, ?, ?)",
                (cur.lastrowid, skill, 3),
            )


def init_db():
    conn = db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            linkedin_id TEXT,
            name TEXT,
            email TEXT,
            position TEXT,
            company TEXT,
            skills TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            recommendation TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            area TEXT NOT NULL,
            description TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS program_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            skill TEXT NOT NULL,
            weight INTEGER DEFAULT 3
        )
        """
    )
    for col in [
        "source_platform TEXT",
        "linkedin_url TEXT",
        "raw_text TEXT",
        "extracted_skills TEXT",
        "best_program TEXT",
        "best_score INTEGER DEFAULT 0",
        "last_analysis_at TEXT",
    ]:
        ensure_col(conn, "users", col)
    for col in [
        "matched_program TEXT",
        "score INTEGER DEFAULT 0",
        "old_company TEXT",
        "new_company TEXT",
        "skills_snapshot TEXT",
        "source_platform TEXT",
    ]:
        ensure_col(conn, "alerts", col)
    seed_programs(conn)
    conn.commit()


@app.before_request
def _before():
    init_db()


@app.teardown_appcontext
def _close(exc=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def load_programs():
    rows = db().execute(
        """
        SELECT p.id, p.name, p.area, p.description, ps.skill, ps.weight
        FROM programs p
        LEFT JOIN program_skills ps ON ps.program_id = p.id
        WHERE p.active = 1
        ORDER BY p.name, ps.weight DESC, ps.skill
        """
    ).fetchall()
    programs, cur = [], None
    for row in rows:
        if not cur or cur["id"] != row["id"]:
            cur = {"id": row["id"], "name": row["name"], "area": row["area"], "description": row["description"] or "", "skills": []}
            programs.append(cur)
        if row["skill"]:
            cur["skills"].append({"skill": row["skill"], "weight": row["weight"] or 0})
    return programs


def score_program(skills, program):
    have = {norm(s) for s in skills}
    matched, missing, good, total = [], [], 0, 0
    for item in program["skills"]:
        total += item["weight"]
        if norm(item["skill"]) in have:
            matched.append(item["skill"])
            good += item["weight"]
        else:
            missing.append(item["skill"])
    return {
        "program_id": program["id"],
        "program_name": program["name"],
        "area": program["area"],
        "description": program["description"],
        "score": round((good / total) * 100) if total else 0,
        "matched": matched,
        "missing": missing,
    }


def analyze(position="", skills_text="", raw_text=""):
    skills = extract_skills(position, skills_text, raw_text)
    results = [score_program(skills, p) for p in load_programs()]
    results.sort(key=lambda x: (-x["score"], x["program_name"]))
    best = results[0] if results else {"program_name": "", "score": 0, "matched": [], "missing": []}
    return {"skills": skills, "top": results[:3], "all": results, "best": best["program_name"], "best_score": best["score"]}


def chips(values, cls=""):
    return "".join(f'<span class="chip {cls}">{escape(v)}</span>' for v in values)


def page(title, body, active="home"):
    nav = [
        ("/", "Inicio", "home"),
        ("/platform", "Plataforma", "platform"),
        ("/market", "Mercado laboral", "market"),
        ("/profiles", "Perfiles", "profiles"),
        ("/programs", "Programas", "programs"),
        ("/alerts", "Alertas", "alerts"),
    ]
    nav_html = "".join(f'<a class="nav {"on" if a == active else ""}" href="{u}">{t}</a>' for u, t, a in nav)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)}</title>
    <style>
    :root{{--unir-red:#e31e24;--unir-blue:#0f2747;--unir-navy:#08162a;--unir-ink:#17212e;--unir-bg:#f3f5f8;--unir-line:#d9e0ea;--unir-soft:#f9fbfd;}}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:"Segoe UI",Arial,sans-serif;background:
      radial-gradient(circle at top right, rgba(227,30,36,.10), transparent 22%),
      radial-gradient(circle at top left, rgba(15,39,71,.08), transparent 25%),
      var(--unir-bg);color:var(--unir-ink)}}
    a{{color:inherit;text-decoration:none}}
    .wrap{{width:min(1180px,calc(100% - 32px));margin:0 auto;padding:20px 0 44px}}
    .top{{width:min(1180px,calc(100% - 32px));margin:16px auto 0;padding:16px 18px;border:1px solid var(--unir-line);background:linear-gradient(135deg,var(--unir-blue),#143d70);border-radius:22px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;box-shadow:0 18px 40px rgba(15,39,71,.18);position:relative;overflow:hidden}}
    .top:before{{content:"";position:absolute;inset:0;height:5px;background:linear-gradient(90deg,var(--unir-red),#ff6d72);top:0}}
    .brand{{display:flex;align-items:center;gap:12px;position:relative;z-index:1}}
    .brand img{{height:38px;width:auto;display:block;filter:drop-shadow(0 6px 12px rgba(0,0,0,.16))}}
    .brand strong{{display:block;color:#fff;font-size:1rem}}
    .brand .muted{{font-size:13px;color:rgba(255,255,255,.82)}}
    .brand-badge{{display:inline-flex;align-items:center;gap:8px;margin-top:6px;padding:5px 10px;border-radius:999px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.15);color:#fff;font-size:12px;font-weight:700;letter-spacing:.02em}}
    .nav{{padding:9px 13px;border-radius:999px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff;backdrop-filter:blur(8px)}} .nav.on,.nav:hover{{background:rgba(227,30,36,.92);border-color:rgba(255,255,255,.12)}} .grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}} .card{{background:#fff;border:1px solid var(--unir-line);border-radius:22px;padding:18px;box-shadow:0 10px 24px rgba(15,39,71,.06)}} .hero{{grid-column:1/-1;display:grid;grid-template-columns:1.4fr 1fr;gap:18px;align-items:center;border-top:4px solid var(--unir-red);background:linear-gradient(180deg,#fff 0%, #fbfcfe 100%)}}
    .hero h1{{font-size:2rem;line-height:1.15}}
    .ey{{display:inline-block;padding:6px 10px;border-radius:999px;background:rgba(227,30,36,.10);color:var(--unir-red);font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:800}} h1,h2,h3,h4,p,label{{margin:0 0 10px;line-height:1.4}} p{{color:#52606d}}
    .metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}} .m{{padding:14px;border-radius:16px;background:linear-gradient(180deg,#fff, var(--unir-soft));border:1px solid var(--unir-line);text-align:center}} .m b{{display:block;font-size:1.7rem;color:var(--unir-blue)}}
    .form{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}} .full{{grid-column:1/-1}} input,textarea,select{{width:100%;padding:11px 12px;border-radius:12px;border:1px solid var(--unir-line);background:#fff;color:var(--unir-ink)}} textarea{{min-height:120px}}
    .btn{{display:inline-block;padding:11px 14px;border-radius:12px;border:1px solid var(--unir-line);background:#fff;color:var(--unir-blue);cursor:pointer;transition:transform .12s ease, box-shadow .12s ease}} .btn:hover{{transform:translateY(-1px);box-shadow:0 10px 18px rgba(15,39,71,.08)}} .pri{{background:linear-gradient(135deg,var(--unir-red),#ff5b63);color:#fff;font-weight:800;border-color:transparent}} .row{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}} .score{{padding:10px 12px;border-radius:14px;background:rgba(227,30,36,.10);border:1px solid rgba(227,30,36,.18);color:var(--unir-red);font-weight:800;min-width:64px;text-align:center}}
    .chips{{display:flex;flex-wrap:wrap;gap:8px}} .chip{{padding:7px 10px;border-radius:999px;background:#f9fbfd;border:1px solid var(--unir-line);font-size:14px}} .ok{{background:rgba(34,197,94,.10);border-color:rgba(34,197,94,.20)}} .warn{{background:rgba(245,158,11,.10);border-color:rgba(245,158,11,.20)}} .muted{{color:#7a8696}} .sub{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}} .table{{width:100%;border-collapse:collapse}} .table th,.table td{{padding:10px 8px;border-bottom:1px solid var(--unir-line);text-align:left;vertical-align:top}} .stack{{display:grid;gap:16px}}
    .brand-rail{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:8px}}
    .brand-rail span{{display:inline-flex;align-items:center;padding:5px 10px;border-radius:999px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:12px}}
    .platform-shell{{grid-column:1/-1;display:grid;grid-template-columns:320px minmax(0,1fr) 360px;gap:16px;align-items:start}}
    .platform-panel{{background:#fff;border:1px solid var(--unir-line);border-radius:22px;padding:18px;box-shadow:0 10px 24px rgba(15,39,71,.05)}}
    .platform-panel.sticky{{position:sticky;top:18px}}
    .toolbar{{display:grid;gap:10px}}
    .toolbar input,.toolbar select{{width:100%;padding:12px 14px;border-radius:12px;border:1px solid var(--unir-line);background:#fff}}
    .stat-strip{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}}
    .mini-stat{{padding:12px;border-radius:16px;background:linear-gradient(180deg,#fff,var(--unir-soft));border:1px solid var(--unir-line)}}
    .mini-stat b{{display:block;font-size:1.5rem;color:var(--unir-blue)}}
    .program-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
    .program-card{{padding:14px;border:1px solid var(--unir-line);border-radius:18px;background:linear-gradient(180deg,#fff,#fbfcfe);cursor:pointer;transition:transform .12s ease, box-shadow .12s ease,border-color .12s ease}}
    .program-card:hover{{transform:translateY(-2px);box-shadow:0 14px 24px rgba(15,39,71,.08);border-color:rgba(227,30,36,.24)}}
    .program-card.active{{border-color:rgba(227,30,36,.45);box-shadow:0 18px 30px rgba(227,30,36,.10)}}
    .program-card h3{{margin-bottom:6px;font-size:1rem}}
    .program-card .meta{{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px}}
    .program-card .meta .ey{{font-size:11px}}
    .detail-hero{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px}}
    .detail-list{{display:grid;gap:12px}}
    .source-grid{{display:grid;gap:10px}}
    .source-item{{padding:10px 0;border-bottom:1px solid var(--unir-line)}}
    .market-list{{display:grid;gap:10px;max-height:500px;overflow:auto;padding-right:6px}}
    .market-item{{padding:10px 0;border-bottom:1px solid var(--unir-line)}}
    .hidden{{display:none !important}}
    .tag{{display:inline-flex;align-items:center;padding:5px 9px;border-radius:999px;background:rgba(15,39,71,.08);border:1px solid rgba(15,39,71,.10);font-size:12px;color:var(--unir-blue)}}
    @media(max-width:1100px){{.platform-shell{{grid-template-columns:1fr}}.platform-panel.sticky{{position:static}}.program-grid,.stat-strip{{grid-template-columns:1fr 1fr}}}}
    @media(max-width:720px){{.program-grid,.stat-strip{{grid-template-columns:1fr}}}}
    @media(max-width:960px){{.hero,.sub,.form{{grid-template-columns:1fr}}.metrics{{grid-template-columns:1fr}}.row{{flex-direction:column}}}}
    </style></head><body><header class="top"><div class="brand"><img src="{UNIR_LOGO_URL}" alt="UNIR"><div><strong>UNIR Pertinencia y Alertas</strong><div class="muted">Comparacion entre cargos laborales y programas academicos</div><div class="brand-rail"><span>{escape(UNIR_SITE_LABEL)}</span><span>Especializaciones</span><span>Mercado laboral</span></div></div></div><nav>{nav_html}</nav></header><main class="wrap">{body}</main></body></html>"""


def card(title, inner, badge=""):
    b = f'<span class="ey">{escape(badge)}</span>' if badge else ""
    return f'<section class="card">{b}<h2>{escape(title)}</h2>{inner}</section>'


def recommendation(best):
    if not best:
        return "Sin programa sugerido."
    matched = ", ".join(best["matched"][:5]) if best["matched"] else "Sin coincidencias"
    missing = ", ".join(best["missing"][:5]) if best["missing"] else "Sin brechas visibles"
    return f"Programa sugerido: {best['program_name']}. Coincidencia: {best['score']}%. Coincidencias: {matched}. Brechas: {missing}."


def render_market_rows(programs, market_counter, market_labels):
    rows = [compare_program_with_market(program, market_counter, market_labels) for program in programs]
    rows.sort(key=lambda item: (-item["score"], item["program"]))
    return rows


def render_home():
    conn = db()
    total_people = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    total_alerts = conn.execute("SELECT COUNT(*) c FROM alerts").fetchone()["c"]
    avg_score = round(conn.execute("SELECT AVG(best_score) a FROM users").fetchone()["a"] or 0)
    people = conn.execute("SELECT id,name,position,company,best_program,best_score,updated_at FROM users ORDER BY datetime(updated_at) DESC LIMIT 5").fetchall()
    alerts = conn.execute("SELECT a.*, u.name FROM alerts a LEFT JOIN users u ON u.id=a.user_id ORDER BY datetime(a.created_at) DESC LIMIT 5").fetchall()
    programs = load_programs()
    market = load_ticjob_market()
    market_counter, market_labels = market_skill_counter(market["jobs"])
    market_rows = render_market_rows(programs, market_counter, market_labels)[:4]
    top_market_skills = sorted(market_counter.items(), key=lambda item: (-item[1], item[0]))[:5]
    body = f"""
    <div class="grid">
      <section class="card hero">
        <div><span class="ey">MVP funcional</span><h1>Relaciona cargos con competencias y programas</h1><p>La app acepta texto de vacantes o perfiles, normaliza habilidades y compara la demanda con el catalogo academico.</p><p class="muted">No hace scraping directo de LinkedIn. Funciona con texto aportado por el usuario o datos cargados manualmente.</p></div>
        <div class="metrics"><div class="m"><b>{total_people}</b><span>Perfiles</span></div><div class="m"><b>{total_alerts}</b><span>Alertas</span></div><div class="m"><b>{avg_score}%</b><span>Promedio</span></div></div>
      </section>
      <div style="grid-column:1/-1;">{card("Mercado laboral", f'''<div class="metrics"><div class="m"><b>{market.get("summary", {}).get("jobs_total", len(market["jobs"]))}</b><span>Ofertas analizadas</span></div><div class="m"><b>{market.get("summary", {}).get("jobs_ticjob", len(market["jobs"]))}</b><span>TICJOB</span></div><div class="m"><b>{len(market_counter)}</b><span>Skills distintas</span></div></div><div style="margin-top:14px"><h3>Fuentes del mercado</h3><div class="chips">{"".join(f"<span class='chip ok'>{escape(name)} ({count})</span>" for name, count in sorted(market.get("summary", {}).get("source_counts", {}).items(), key=lambda item: (-item[1], item[0]))[:10]) or "<span class='muted'>Sin fuentes disponibles.</span>"}</div></div><div style="margin-top:14px"><h3>Skills mas repetidas</h3><div class="chips">{"".join(f"<span class='chip ok'>{escape(market_labels.get(key, key))} ({count})</span>" for key, count in top_market_skills) or "<span class='muted'>Sin datos de mercado.</span>"}</div></div><div style="margin-top:14px"><h3>Programas con mejor ajuste</h3><table class="table"><thead><tr><th>Programa</th><th>Cobertura</th><th>Brecha</th></tr></thead><tbody>{"".join(f"<tr><td>{escape(row['program'])}</td><td>{row['score']}%</td><td>{100 - row['score']}%</td></tr>" for row in market_rows) or "<tr><td colspan='3' class='muted'>No hay cruces disponibles.</td></tr>"}</tbody></table></div>''', 'Mercado')}</div>
      <div style="grid-column:1/8;">{card("Analisis rapido", '''
        <form method="post" action="/analyze"><div class="form">
          <div><label>Cargo o titulo</label><input name="position" placeholder="Analista de datos"></div>
          <div><label>Fuente</label><select name="source_platform"><option>LinkedIn</option><option>Portal de empleo</option><option>CV</option><option>Otro</option></select></div>
          <div class="full"><label>Skills manuales</label><input name="skills" placeholder="SQL, Power BI, Python"></div>
          <div class="full"><label>Texto libre</label><textarea name="raw_text" placeholder="Pega aqui la vacante o el perfil"></textarea></div>
        </div><p style="margin-top:12px"><button class="btn pri" type="submit">Analizar pertinencia</button></p></form>
      ''', 'Comparacion')}</div>
      <div style="grid-column:8/-1;">{card("Registrar perfil", '''
        <form method="post" action="/profiles/save"><div class="form">
          <div><label>Nombre</label><input name="name"></div><div><label>Correo</label><input name="email"></div>
          <div><label>Cargo actual</label><input name="position" placeholder="Analista de datos"></div><div><label>Empresa</label><input name="company"></div>
          <div><label>Fuente</label><select name="source_platform"><option>LinkedIn</option><option>Portal de empleo</option><option>CV</option><option>Otro</option></select></div><div><label>URL publica</label><input name="linkedin_url"></div>
          <div class="full"><label>Skills</label><input name="skills" placeholder="SQL, Power BI, Python"></div><div class="full"><label>Texto libre</label><textarea name="raw_text"></textarea></div>
        </div><p style="margin-top:12px"><button class="btn pri" type="submit">Guardar perfil</button></p></form>
      ''', 'Seguimiento')}</div>
      <div style="grid-column:1/7;">{card("Catalogo completo UNIR", ''.join(f'<article style="padding:12px 0;border-bottom:1px solid #ffffff12"><span class="ey">{escape(p["area"])}</span><h3>{escape(p["name"])}</h3><p>{escape(p["description"])}</p><div class="chips">{chips([s["skill"] for s in p["skills"][:4]])}</div></article>' for p in programs), 'Catalogo')}</div>
      <div style="grid-column:7/-1;">{card("Alertas recientes", ''.join(f'<article style="padding:12px 0;border-bottom:1px solid #ffffff12"><div class="row"><div><h3>{escape(r["name"] or "Sin nombre")}</h3><p>{escape(r["old_value"] or "")} -> {escape(r["new_value"] or "")}</p><p class="muted">{escape(r["recommendation"] or "")}</p></div><div class="score">{r["score"] or 0}%</div></div></article>' for r in alerts) or '<p class="muted">Aun no hay alertas.</p>', 'Alertas')}</div>
      <div style="grid-column:1/-1;">{card("Perfiles recientes", ''.join(f'<article style="padding:12px 0;border-bottom:1px solid #ffffff12"><div class="row"><div><a href="/profiles/{r["id"]}"><strong>{escape(r["name"] or "Sin nombre")}</strong></a><p>{escape(r["position"] or "")} | {escape(r["company"] or "")}</p><p class="muted">{escape(r["best_program"] or "Sin analisis")} ({r["best_score"] or 0}%)</p></div><div class="muted">{escape(r["updated_at"] or "")}</div></div></article>' for r in people) or '<p class="muted">No hay perfiles guardados.</p>', 'Base de datos')}</div>
    </div>"""
    return page("Inicio", body)


def build_platform_data():
    programs = load_programs()
    market = load_ticjob_market()
    market_counter, market_labels = market_skill_counter(market["jobs"])
    rankings = render_market_rows(programs, market_counter, market_labels)
    top_skills = sorted(market_counter.items(), key=lambda item: (-item[1], item[0]))[:18]
    top_jobs = sorted(
        market["jobs"],
        key=lambda item: (
            -float(item.get("match_score", 0) or 0),
            norm(item.get("job_title", "")),
            norm(item.get("company", "")),
        ),
    )[:18]
    source_counts = market.get("summary", {}).get("source_counts", {})
    return {
        "summary": market.get("summary", {}),
        "metrics": market.get("metrics", {}),
        "source": market.get("source", ""),
        "programs": rankings,
        "top_skills": [{"skill": market_labels.get(key, key), "count": count} for key, count in top_skills],
        "top_jobs": top_jobs,
        "source_counts": source_counts,
        "program_count": len(programs),
        "jobs_total": len(market.get("jobs", [])),
        "market_skill_count": len(market_counter),
    }


def render_platform():
    data = build_platform_data()
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    programs_html = []
    for index, program in enumerate(data["programs"]):
        matched_preview = ", ".join(program["matched"][:3]) if program["matched"] else "Sin coincidencias visibles"
        missing_preview = ", ".join(program["missing"][:3]) if program["missing"] else "Sin brechas visibles"
        programs_html.append(
            f"""
            <article class="program-card" data-index="{index}" data-name="{escape(program['program'])}" data-area="{escape(program['area'])}" data-text="{escape((program['program'] + ' ' + program['area'] + ' ' + program['description'] + ' ' + ' '.join(program['matched']) + ' ' + ' '.join(program['missing'])).lower())}">
              <div class="meta"><span class="ey">{escape(program['area'])}</span><span class="score">{program['score']}%</span></div>
              <h3>{escape(program['program'])}</h3>
              <p>{escape(program['description'])}</p>
              <div class="chips" style="margin-bottom:8px">{chips(program['matched'][:3], 'ok') or '<span class="muted">Sin coincidencias.</span>'}</div>
              <div class="muted">Coincidencias: {escape(matched_preview)}</div>
              <div class="muted">Brechas: {escape(missing_preview)}</div>
            </article>
            """
        )

    jobs_html = []
    for job in data["top_jobs"]:
        jobs_html.append(
            f"""
            <article class="market-item">
              <div class="row">
                <div>
                  <strong>{escape(job.get("job_title", "Sin titulo"))}</strong>
                  <p class="muted">{escape(job.get("company", ""))} | {escape(job.get("location", ""))}</p>
                </div>
                <div class="score">{job.get("match_score", 0)}%</div>
              </div>
              <div class="chips" style="margin-top:8px">{chips((job.get("skills", []) or [])[:5], 'ok')}</div>
            </article>
            """
        )

    source_html = "".join(
        f"<span class='chip'>{escape(name)} ({count})</span>"
        for name, count in sorted(data["source_counts"].items(), key=lambda item: (-item[1], item[0]))[:10]
    ) or "<span class='muted'>Sin fuentes.</span>"

    top_skills_html = "".join(
        f"<span class='chip ok'>{escape(item['skill'])} ({item['count']})</span>"
        for item in data["top_skills"]
    ) or "<span class='muted'>Sin skills.</span>"

    detail_first = data["programs"][0] if data["programs"] else {"program": "Sin programas", "area": "", "description": "", "score": 0, "matched": [], "missing": [], "total_skills": 0}

    body = f"""
    <div class="grid">
      <section class="card hero">
        <div>
          <span class="ey">Plataforma</span>
          <h1>Curriculum Intelligence Platform</h1>
          <p>Compara programas UNIR con el mercado laboral, identifica skills cubiertas y vacÃƒÂ­os, y entrega recomendaciones para rediseÃƒÂ±o curricular.</p>
          <p class="muted">Datos unificados desde TICJOB, Computrabajo y Elempleo, cruzados contra el catÃƒÂ¡logo acadÃƒÂ©mico de UNIR.</p>
        </div>
        <div class="metrics">
          <div class="m"><b>{data["program_count"]}</b><span>Programas</span></div>
          <div class="m"><b>{data["jobs_total"]}</b><span>Ofertas</span></div>
          <div class="m"><b>{data["market_skill_count"]}</b><span>Skills</span></div>
        </div>
      </section>

      <section class="platform-shell">
        <aside class="platform-panel sticky">
          <span class="ey">Filtros</span>
          <h2>Explorar</h2>
          <div class="toolbar">
            <input id="searchBox" type="search" placeholder="Buscar programa, skill o ÃƒÂ¡rea">
            <select id="areaFilter">
              <option value="all">Todas las ÃƒÂ¡reas</option>
              <option value="Tecnologia">Tecnologia</option>
              <option value="Datos y BI">Datos y BI</option>
              <option value="Negocios y Marketing">Negocios y Marketing</option>
              <option value="Educacion">Educacion</option>
              <option value="Salud">Salud</option>
              <option value="Derecho">Derecho</option>
              <option value="Finanzas">Finanzas</option>
              <option value="Gestion Humana y Liderazgo">Gestion Humana y Liderazgo</option>
              <option value="Gestion">Gestion</option>
            </select>
          </div>
          <div style="margin-top:14px">
            <h3>Fuentes del mercado</h3>
            <div class="chips">{source_html}</div>
          </div>
          <div style="margin-top:14px">
            <h3>Skills mÃƒÂ¡s repetidas</h3>
            <div class="chips">{top_skills_html}</div>
          </div>
        </aside>

        <section class="platform-panel">
          <div class="detail-hero">
            <div>
              <span class="ey">Programas</span>
              <h2>CatÃƒÂ¡logo comparado</h2>
              <p id="programCounter" class="muted">Mostrando {data["program_count"]} programas.</p>
            </div>
            <div class="score" id="selectedScore">{detail_first['score']}%</div>
          </div>
          <div class="program-grid" id="programGrid">
            {''.join(programs_html)}
          </div>
        </section>

        <aside class="platform-panel sticky" id="detailPanel">
          <span class="ey">Detalle</span>
          <h2 id="detailTitle">{escape(detail_first['program'])}</h2>
          <p id="detailArea" class="muted">{escape(detail_first['area'])}</p>
          <p id="detailDesc">{escape(detail_first['description'])}</p>
          <div class="detail-list">
            <div>
              <h3>Coincidencias</h3>
              <div class="chips" id="detailMatched">{chips(detail_first['matched'], 'ok') or '<span class="muted">Sin coincidencias.</span>'}</div>
            </div>
            <div>
              <h3>Brechas</h3>
              <div class="chips" id="detailMissing">{chips(detail_first['missing'], 'warn') or '<span class="muted">Sin brechas.</span>'}</div>
            </div>
            <div>
              <h3>RecomendaciÃƒÂ³n</h3>
              <p id="detailReco" class="muted">Programa sugerido con {detail_first['score']}% de ajuste relativo al mercado unificado.</p>
            </div>
          </div>
        </aside>
      </section>

      <div style="grid-column:1/7;">{card("Mercado laboral", '<div class="market-list">' + ''.join(jobs_html) + '</div>', "Datos")}</div>
      <div style="grid-column:7/-1;">{card("Lectura ejecutiva", f'''
        <div class="stat-strip">
          <div class="mini-stat"><b>{data["summary"].get("jobs_ticjob", 0)}</b><span>TICJOB</span></div>
          <div class="mini-stat"><b>{data["summary"].get("jobs_portal", 0)}</b><span>Portales</span></div>
          <div class="mini-stat"><b>{len(data["source_counts"])}</b><span>Fuentes</span></div>
          <div class="mini-stat"><b>{data["market_skill_count"]}</b><span>Skills</span></div>
        </div>
        <table class="table"><thead><tr><th>Programa</th><th>Score</th><th>Brecha</th></tr></thead><tbody>{''.join(f"<tr><td>{escape(item['program'])}</td><td>{item['score']}%</td><td>{100 - item['score']}%</td></tr>" for item in data['programs'][:8]) or '<tr><td colspan="3" class="muted">Sin datos.</td></tr>'}</tbody></table>
      ''', 'Resumen')}</div>
    </div>
    <script type="application/json" id="platform-data">{data_json}</script>
    <script>
    (function() {{
      const payload = JSON.parse(document.getElementById('platform-data').textContent);
      const cards = Array.from(document.querySelectorAll('.program-card'));
      const searchBox = document.getElementById('searchBox');
      const areaFilter = document.getElementById('areaFilter');
      const programCounter = document.getElementById('programCounter');
      const selectedScore = document.getElementById('selectedScore');
      const detailTitle = document.getElementById('detailTitle');
      const detailArea = document.getElementById('detailArea');
      const detailDesc = document.getElementById('detailDesc');
      const detailMatched = document.getElementById('detailMatched');
      const detailMissing = document.getElementById('detailMissing');
      const detailReco = document.getElementById('detailReco');
      let selectedIndex = 0;

      function renderChips(items, cls) {{
        if (!items || !items.length) {{
          return '<span class="muted">Sin datos.</span>';
        }}
        return items.map(item => `<span class="chip ${{cls}}">${{item}}</span>`).join('');
      }}

      function setActive(index) {{
        selectedIndex = index;
        cards.forEach((card, idx) => card.classList.toggle('active', idx === index));
        const program = payload.programs[index];
        if (!program) return;
        selectedScore.textContent = program.score + '%';
        detailTitle.textContent = program.program;
        detailArea.textContent = program.area;
        detailDesc.textContent = program.description;
        detailMatched.innerHTML = renderChips(program.matched, 'ok');
        detailMissing.innerHTML = renderChips(program.missing, 'warn');
        detailReco.textContent = `Revisar ${{program.program}}: ${{program.score}}% de ajuste sobre el mercado unificado.`;
      }}

      function applyFilters() {{
        const query = (searchBox.value || '').trim().toLowerCase();
        const area = areaFilter.value;
        let visible = 0;
        cards.forEach((card, idx) => {{
          const text = card.dataset.text || '';
          const cardArea = card.dataset.area || '';
          const matchesQuery = !query || text.includes(query);
          const matchesArea = area === 'all' || cardArea === area;
          const show = matchesQuery && matchesArea;
          card.classList.toggle('hidden', !show);
          if (show) visible += 1;
        }});
        programCounter.textContent = `Mostrando ${{visible}} programas.`;
      }}

      cards.forEach((card, idx) => card.addEventListener('click', () => setActive(idx)));
      searchBox.addEventListener('input', applyFilters);
      areaFilter.addEventListener('change', applyFilters);
      setActive(0);
      applyFilters();
    }})();
    </script>
    """
    return page("Curriculum Intelligence Platform", body, "platform")


@app.route("/")
def home():
    return render_home()


@app.route("/platform")
def platform():
    return render_platform()


@app.route("/market")
def market():
    market = load_ticjob_market()
    jobs = market["jobs"]
    market_counter, market_labels = market_skill_counter(jobs)
    programs = load_programs()
    rows = render_market_rows(programs, market_counter, market_labels)
    top_jobs = jobs[:9]
    top_skills = sorted(market_counter.items(), key=lambda item: (-item[1], item[0]))[:12]
    summary = market.get("summary", {})
    skills_html = "".join(
        f"""<article style="padding:10px 0;border-bottom:1px solid #ffffff12">
            <div class="row">
              <div>
                <strong>{escape(market_labels.get(key, key))}</strong>
                <p class="muted">Frecuencia: {count}</p>
              </div>
              <div class="score">{round((count / max(1, len(jobs))) * 100)}%</div>
            </div>
        </article>"""
        for key, count in top_skills
    ) or '<p class="muted">No hay skills disponibles.</p>'

    jobs_html = "".join(
        f"""<article style="padding:10px 0;border-bottom:1px solid #ffffff12">
            <strong>{escape(job.get("job_title", "Sin titulo"))}</strong>
            <p class="muted">{escape(job.get("company", ""))} | {escape(job.get("location", ""))}</p>
            <div class="chips">{chips(job.get("skills", [])[:6], "ok")}</div>
        </article>"""
        for job in top_jobs
    ) or '<p class="muted">No hay ofertas para mostrar.</p>'

    rows_html = "".join(
        f"""<tr>
            <td>{escape(row['program'])}</td>
            <td>{row['score']}%</td>
            <td>{100 - row['score']}%</td>
            <td>{escape(', '.join(row['matched'][:4]) or 'Sin coincidencias')}</td>
            <td>{escape(', '.join(row['missing'][:4]) or 'Sin brechas')}</td>
        </tr>"""
        for row in rows
    ) or '<tr><td colspan="5" class="muted">No hay datos para comparar.</td></tr>'

    body = f"""
    <div class="grid">
      <section class="card hero">
        <div><span class="ey">Mercado</span><h1>Extraccion y cruce de skills de mercado</h1><p>Esta vista usa el mercado ampliado generado por el scraper unificado para identificar skills, patrones de demanda y cobertura por programa UNIR.</p></div>
        <div class="metrics"><div class="m"><b>{summary.get("jobs_total", len(jobs))}</b><span>Ofertas analizadas</span></div><div class="m"><b>{summary.get("jobs_ticjob", len(jobs))}</b><span>TICJOB</span></div><div class="m"><b>{len(market_counter)}</b><span>Skills distintas</span></div></div>
      </section>
      <div style="grid-column:1/7;">{card("Skills del mercado", skills_html, "Mercado")}</div>
      <div style="grid-column:7/-1;">{card("Jobs destacados", jobs_html, "Jobs")}</div>
      <div style="grid-column:1/-1;">{card("Cobertura por programa UNIR", f'<table class="table"><thead><tr><th>Programa</th><th>Cobertura</th><th>Brecha</th><th>Coincidencias</th><th>Faltantes</th></tr></thead><tbody>{rows_html}</tbody></table>', "Match")}</div>
    </div>"""
    return page("Mercado laboral", body, "market")


@app.route("/analyze", methods=["POST"])
def analyze_route():
    position = request.form.get("position", "").strip()
    skills = request.form.get("skills", "").strip()
    raw_text = request.form.get("raw_text", "").strip()
    source = request.form.get("source_platform", "LinkedIn").strip()
    result = analyze(position, skills, raw_text)
    top = result["top"]
    detected_skills_html = chips(result["skills"], "ok") or '<span class="muted">Sin coincidencias.</span>'
    context_text = (raw_text[:500] + "...") if raw_text and len(raw_text) > 500 else raw_text or "Sin texto"
    context_html = (
        f"<p><strong>Cargo:</strong> {escape(position or 'N/D')}</p>"
        f"<p><strong>Skills:</strong> {escape(skills or 'N/D')}</p>"
        f"<p><strong>Texto:</strong> {escape(context_text)}</p>"
    )
    cards_html = ''.join(
        f'''<section class="card"><div class="row"><div><span class="ey">{escape(r["area"])}</span><h3>{escape(r["program_name"])}</h3><p>{escape(r["description"])}</p></div><div class="score">{r["score"]}%</div></div><div class="sub"><div><h4>Coincidencias</h4><div class="chips">{chips(r["matched"], "ok") or '<span class="muted">Sin coincidencias.</span>'}</div></div><div><h4>Brechas</h4><div class="chips">{chips(r["missing"][:8], "warn") or '<span class="muted">Sin brechas.</span>'}</div></div></div></section>'''
        for r in top
    ) or '<div class="card"><p class="muted">No hay programas para comparar.</p></div>'
    body = f"""
    <div class="grid">
      <section class="card hero">
        <div><span class="ey">Resultado</span><h1>{escape(position or "Analisis de pertinencia")}</h1><p>Fuente: {escape(source)}.</p></div>
        <div class="metrics"><div class="m"><b>{len(result["skills"])}</b><span>Competencias</span></div><div class="m"><b>{result["best_score"]}%</b><span>Mejor match</span></div><div class="m"><b>{len(top)}</b><span>Programas</span></div></div>
      </section>
      <div style="grid-column:1/7;">{card("Competencias detectadas", f'<div class="chips">{detected_skills_html}</div>', "Extraccion")}</div>
      <div style="grid-column:7/-1;">{card("Contexto", context_html, "Entrada")}</div>
      <div style="grid-column:1/-1;">{cards_html}</div>
    </div>"""


def save_profile(form):
    conn = db()
    pid = form.get("person_id", "").strip()
    name = form.get("name", "").strip()
    email = form.get("email", "").strip()
    position = form.get("position", "").strip()
    company = form.get("company", "").strip()
    skills = form.get("skills", "").strip()
    raw_text = form.get("raw_text", "").strip()
    source = form.get("source_platform", "LinkedIn").strip()
    url = form.get("linkedin_url", "").strip()
    result = analyze(position, skills, raw_text)
    best = result["top"][0] if result["top"] else {"program_name": "", "score": 0, "matched": [], "missing": []}
    extracted = ", ".join(result["skills"])

    if pid.isdigit() and conn.execute("SELECT 1 FROM users WHERE id=?", (int(pid),)).fetchone():
        old = conn.execute("SELECT position, company FROM users WHERE id=?", (int(pid),)).fetchone()
        conn.execute(
            """UPDATE users SET name=?, email=?, position=?, company=?, skills=?, updated_at=?, source_platform=?, linkedin_url=?, raw_text=?, extracted_skills=?, best_program=?, best_score=?, last_analysis_at=? WHERE id=?""",
            (name, email, position, company, skills, now(), source, url, raw_text, extracted, best["program_name"], best["score"], now(), int(pid)),
        )
        if norm(old["position"] or "") != norm(position or "") and position:
            conn.execute(
                """INSERT INTO alerts (user_id, old_value, new_value, recommendation, created_at, matched_program, score, old_company, new_company, skills_snapshot, source_platform) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(pid), old["position"], position, recommendation(best), now(), best["program_name"], best["score"], old["company"], company, extracted, source),
            )
        conn.commit()
        return int(pid)

    cur = conn.execute(
        """INSERT INTO users (linkedin_id, name, email, position, company, skills, updated_at, source_platform, linkedin_url, raw_text, extracted_skills, best_program, best_score, last_analysis_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (None, name, email, position, company, skills, now(), source, url, raw_text, extracted, best["program_name"], best["score"], now()),
    )
    conn.commit()
    return cur.lastrowid


@app.route("/profiles/save", methods=["POST"])
def save_profile_route():
    pid = save_profile(request.form)
    return redirect(url_for("profile_detail", person_id=pid))


@app.route("/profiles")
def profiles():
    rows = db().execute("SELECT id,name,position,company,source_platform,best_program,best_score,updated_at FROM users ORDER BY datetime(updated_at) DESC").fetchall()
    table = "<table class='table'><thead><tr><th>Nombre</th><th>Cargo</th><th>Empresa</th><th>Fuente</th><th>Programa</th><th>Score</th><th>Actualizacion</th></tr></thead><tbody>"
    if rows:
        for r in rows:
            table += f"<tr><td><a href='/profiles/{r['id']}'>{escape(r['name'] or 'Sin nombre')}</a></td><td>{escape(r['position'] or '')}</td><td>{escape(r['company'] or '')}</td><td>{escape(r['source_platform'] or '')}</td><td>{escape(r['best_program'] or '')}</td><td>{r['best_score'] or 0}%</td><td>{escape(r['updated_at'] or '')}</td></tr>"
    else:
        table += "<tr><td colspan='7' class='muted'>No hay perfiles.</td></tr>"
    table += "</tbody></table>"
    return page("Perfiles", card("Perfiles almacenados", table, "Gestor"), "profiles")


@app.route("/profiles/<int:person_id>")
def profile_detail(person_id):
    row = db().execute("SELECT * FROM users WHERE id=?", (person_id,)).fetchone()
    if not row:
        return page("No encontrado", card("Perfil no encontrado", "<p class='muted'>El registro no existe.</p>"), "profiles"), 404
    result = analyze(row["position"] or "", row["skills"] or "", row["raw_text"] or "")
    profile_skills_html = chips(result["skills"], "ok") or '<span class="muted">Sin competencias.</span>'
    top_cards_html = ''.join(
        f'''<section class="card"><div class="row"><div><span class="ey">{escape(r["area"])}</span><h3>{escape(r["program_name"])}</h3><p>{escape(r["description"])}</p></div><div class="score">{r["score"]}%</div></div><div class="sub"><div><h4>Coincidencias</h4><div class="chips">{chips(r["matched"], "ok") or '<span class="muted">Sin coincidencias.</span>'}</div></div><div><h4>Brechas</h4><div class="chips">{chips(r["missing"][:8], "warn") or '<span class="muted">Sin brechas.</span>'}</div></div></div></section>'''
        for r in result["top"]
    ) or '<div class="card"><p class="muted">No hay programas para comparar.</p></div>'
    form = f"""
    <form method="post" action="/profiles/save">
      <input type="hidden" name="person_id" value="{row['id']}">
      <div class="form">
        <div><label>Nombre</label><input name="name" value="{escape(row['name'] or '')}"></div>
        <div><label>Correo</label><input name="email" value="{escape(row['email'] or '')}"></div>
        <div><label>Cargo actual</label><input name="position" value="{escape(row['position'] or '')}"></div>
        <div><label>Empresa</label><input name="company" value="{escape(row['company'] or '')}"></div>
        <div><label>Fuente</label><input name="source_platform" value="{escape(row['source_platform'] or 'LinkedIn')}"></div>
        <div><label>URL publica</label><input name="linkedin_url" value="{escape(row['linkedin_url'] or '')}"></div>
        <div class="full"><label>Skills</label><input name="skills" value="{escape(row['skills'] or '')}"></div>
        <div class="full"><label>Texto libre</label><textarea name="raw_text">{escape(row['raw_text'] or '')}</textarea></div>
      </div>
      <p style="margin-top:12px"><button class="btn pri" type="submit">Guardar cambios</button></p>
    </form>
    """
    body = f"""
    <div class="grid">
      <section class="card hero">
        <div><span class="ey">Seguimiento</span><h1>{escape(row['name'] or 'Sin nombre')}</h1><p>{escape(row['position'] or 'Sin cargo')} | {escape(row['company'] or 'Sin empresa')}</p><p class="muted">{escape(row['email'] or '')}</p></div>
        <div class="metrics"><div class="m"><b>{row['best_score'] or 0}%</b><span>Score guardado</span></div><div class="m"><b>{escape(row['best_program'] or 'N/D')}</b><span>Mejor programa</span></div><div class="m"><b>{escape(row['source_platform'] or '')}</b><span>Fuente</span></div></div>
      </section>
      <div style="grid-column:1/7;">{card("Competencias detectadas", f'<div class="chips">{profile_skills_html}</div>', "Extraccion")}</div>
      <div style="grid-column:7/-1;">{card("Editar perfil", form, "Actualizar")}</div>
      <div style="grid-column:1/-1;">{top_cards_html}</div>
    </div>
    """


@app.route("/programs", methods=["GET", "POST"])
def programs():
    conn = db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        area = request.form.get("area", "").strip()
        description = request.form.get("description", "").strip()
        skills = request.form.get("skills", "").strip()
        if name and area:
            cur = conn.execute("INSERT INTO programs (name, area, description, active, created_at) VALUES (?, ?, ?, 1, ?)", (name, area, description, now()))
            for line in split_terms(skills):
                skill, weight = line, 3
                if ":" in line:
                    skill, weight_text = line.rsplit(":", 1)
                    try:
                        weight = max(1, int(weight_text.strip()))
                    except ValueError:
                        weight = 3
                conn.execute("INSERT INTO program_skills (program_id, skill, weight) VALUES (?, ?, ?)", (cur.lastrowid, skill.strip(), weight))
            conn.commit()
            return redirect(url_for("programs"))
    rows = load_programs()
    cards = "".join(f"""<section class="card"><span class="ey">{escape(p['area'])}</span><h3>{escape(p['name'])}</h3><p>{escape(p['description'])}</p><div class="chips">{chips([s['skill'] for s in p['skills'][:8]])}</div></section>""" for p in rows)
    form = """
    <form method="post">
      <div class="form">
        <div class="full"><label>Nombre</label><input name="name" placeholder="Programa nuevo"></div>
        <div class="full"><label>Area</label><input name="area" placeholder="Educacion / Tecnologia / Negocios"></div>
        <div class="full"><label>Descripcion</label><textarea name="description"></textarea></div>
        <div class="full"><label>Competencias (una por linea, opcional competencia:peso)</label><textarea name="skills" placeholder="SQL:4\nPower BI:5"></textarea></div>
      </div>
      <p style="margin-top:12px"><button class="btn pri" type="submit">Guardar programa</button></p>
    </form>
    """
    no_programs_html = '<p class="muted">No hay programas.</p>'
    body = f'''<div class="grid"><div style="grid-column:1/5;">{card("Agregar programa", form, "Catalogo")}</div><div style="grid-column:5/-1;">{card("Catalogo activo", cards or no_programs_html, "UNIR")}</div></div>'''
    return page("Programas", body, "programs")


@app.route("/alerts")
def alerts():
    rows = db().execute("SELECT a.*, u.name FROM alerts a LEFT JOIN users u ON u.id=a.user_id ORDER BY datetime(a.created_at) DESC").fetchall()
    inner = "".join(
        f"""<section class="card"><div class="row"><div><span class="ey">{escape(r['name'] or 'Sin nombre')}</span><h3>{escape(r['old_value'] or '')} -> {escape(r['new_value'] or '')}</h3><p>{escape(r['recommendation'] or '')}</p><div class="chips"><span class="chip ok">{escape(r['matched_program'] or 'Sin programa')}</span><span class="chip warn">{r['score'] or 0}%</span><span class="chip">{escape(r['source_platform'] or '')}</span></div></div><div class="score">{r['score'] or 0}%</div></div><p class="muted" style="margin-top:10px">{escape(r['created_at'] or '')}</p></section>"""
        for r in rows
    ) or '<p class="muted">No hay alertas registradas.</p>'
    return page("Alertas", card("Alertas generadas", inner, "Seguimiento"), "alerts")

