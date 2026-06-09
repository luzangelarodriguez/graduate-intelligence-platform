"""
Motor de pertinencia académica de 3 capas.

CAPA 1 — Embeddings semánticos
    Modelo preferido: sentence-transformers all-MiniLM-L6-v2 (CPU)
    Fallback automático: TF-IDF + cosine (sin dependencias pesadas)

CAPA 2 — BM25 léxico (rank-bm25)
    Corpus: skills normalizados de cada empleo
    Query: skills del microcurrículo del programa
    Fallback: BM25 puro Python si rank-bm25 no está instalado

CAPA 3 — Pertinencia académica
    coverage_score = skills_microcurriculo cubiertos / total_skills_microcurriculo
    density_score  = skills_comunes / total_skills_job
    pertinence_score = F1(coverage, density) × 100
    gap_skills = skills_microcurriculo NO encontrados en el job

Score final = semántico×0.55 + pertinencia×0.45
Filtro de dominio OBLIGATORIO antes del matching.
Umbral mínimo: 65 para considerar pertinente.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env.local")
except ImportError:
    pass

import numpy as np
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEMANTIC_WEIGHT: float = 0.55
PERTINENCE_WEIGHT: float = 0.45
PERTINENCE_THRESHOLD: float = 65.0

SCORE_HIGH: float = 75.0
SCORE_MEDIUM: float = 55.0
SCORE_LOW: float = 35.0

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def _db_url() -> Optional[str]:
    for key in ("RAILWAY_DATABASE_URL", "DATABASE_URL"):
        v = os.getenv(key)
        if v:
            return v
    return None


def connect() -> psycopg2.extensions.connection:
    url = _db_url()
    if url:
        return psycopg2.connect(url, sslmode="require",
                                cursor_factory=psycopg2.extras.RealDictCursor)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "graduate_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _normalize(text: Any) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


def _tokenize(text: str) -> List[str]:
    return [t for t in _normalize(text).split() if len(t) > 1]


# ---------------------------------------------------------------------------
# CAPA 1 — Embeddings con fallback a TF-IDF
# ---------------------------------------------------------------------------

class _TFIDFEmbedder:
    """Lightweight TF-IDF cosine embedder — no GPU, no large models."""

    def __init__(self) -> None:
        self._vocab: Dict[str, int] = {}
        self._idf: np.ndarray = np.zeros(0, dtype=np.float32)
        self._fitted = False

    def fit(self, texts: List[str]) -> None:
        tokenized = [_tokenize(t) for t in texts]
        vocab: Dict[str, int] = {}
        df: Dict[str, int] = defaultdict(int)
        for doc in tokenized:
            for term in set(doc):
                if term not in vocab:
                    vocab[term] = len(vocab)
                df[term] += 1
        n = max(len(tokenized), 1)
        idf = np.zeros(len(vocab), dtype=np.float32)
        for term, idx in vocab.items():
            idf[idx] = math.log((n + 1) / (df[term] + 1)) + 1.0
        self._vocab = vocab
        self._idf = idf
        self._fitted = True

    def encode(self, texts: List[str]) -> np.ndarray:
        if not self._fitted:
            self.fit(texts)
        dim = len(self._vocab)
        out = np.zeros((len(texts), dim), dtype=np.float32)
        for i, text in enumerate(texts):
            tf: Dict[str, int] = defaultdict(int)
            tokens = _tokenize(text)
            for t in tokens:
                tf[t] += 1
            n = max(len(tokens), 1)
            for term, count in tf.items():
                if term in self._vocab:
                    idx = self._vocab[term]
                    out[i, idx] = (count / n) * self._idf[idx]
        # L2 normalise
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return out / norms


_ST_MODEL: Any = None       # sentence-transformers model (lazy)
_TFIDF: Optional[_TFIDFEmbedder] = None   # TF-IDF fallback (lazy)
_USE_ST: Optional[bool] = None           # resolved once


def _resolve_embedder() -> str:
    """Returns 'st' or 'tfidf'."""
    global _USE_ST
    if _USE_ST is not None:
        return "st" if _USE_ST else "tfidf"
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
        _USE_ST = True
        return "st"
    except Exception:
        logger.warning("sentence-transformers unavailable — usando TF-IDF como fallback.")
        _USE_ST = False
        return "tfidf"


def embed_texts(texts: List[str], *, fit_corpus: Optional[List[str]] = None) -> np.ndarray:
    """Encode texts to L2-normalised float32 vectors."""
    global _ST_MODEL, _TFIDF
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)

    mode = _resolve_embedder()

    if mode == "st":
        if _ST_MODEL is None:
            from sentence_transformers import SentenceTransformer
            _ST_MODEL = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")
        vecs = _ST_MODEL.encode(
            texts, batch_size=64, show_progress_bar=False,
            convert_to_numpy=True, normalize_embeddings=True,
        )
        return vecs.astype(np.float32)

    # TF-IDF fallback
    if _TFIDF is None:
        _TFIDF = _TFIDFEmbedder()
        corpus = fit_corpus if fit_corpus is not None else texts
        _TFIDF.fit(corpus)
    vecs = _TFIDF.encode(texts)
    # Pad/truncate to EMBED_DIM for a consistent shape
    dim = vecs.shape[1]
    if dim < EMBED_DIM:
        vecs = np.pad(vecs, ((0, 0), (0, EMBED_DIM - dim)))
    elif dim > EMBED_DIM:
        vecs = vecs[:, :EMBED_DIM]
    return vecs.astype(np.float32)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.clip(np.dot(a, b), 0.0, 1.0))


# ---------------------------------------------------------------------------
# CAPA 2 — BM25 con fallback puro Python
# ---------------------------------------------------------------------------

def _make_bm25(corpus: List[List[str]]) -> Any:
    """Returns a rank-bm25 BM25Okapi or our fallback."""
    try:
        from rank_bm25 import BM25Okapi
        return BM25Okapi(corpus)
    except ImportError:
        logger.warning("rank-bm25 no instalado — usando BM25 Python nativo.")
        return _PureBM25(corpus)


class _PureBM25:
    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.corpus = corpus
        n = len(corpus)
        dl = [len(d) for d in corpus]
        self.avgdl = sum(dl) / max(n, 1)
        self.dl = dl
        df: Dict[str, int] = defaultdict(int)
        for doc in corpus:
            for t in set(doc):
                df[t] += 1
        self.idf: Dict[str, float] = {
            t: math.log((n - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()
        }

    def get_scores(self, query: List[str]) -> np.ndarray:
        scores = np.zeros(len(self.corpus), dtype=np.float32)
        for i, doc in enumerate(self.corpus):
            tf: Dict[str, int] = defaultdict(int)
            for t in doc:
                tf[t] += 1
            for term in query:
                if term not in self.idf:
                    continue
                f = tf.get(term, 0)
                num = self.idf[term] * f * (self.k1 + 1)
                den = f + self.k1 * (1 - self.b + self.b * self.dl[i] / max(self.avgdl, 1))
                scores[i] += num / den
        return scores


def _bm25_normalised(index: Any, query_tokens: List[str]) -> np.ndarray:
    scores = index.get_scores(query_tokens).astype(np.float32)
    mx = scores.max()
    if mx > 0:
        scores /= mx
    return scores


# ---------------------------------------------------------------------------
# Domain filter
# ---------------------------------------------------------------------------

_DOMAIN_BUCKETS: Dict[str, List[str]] = {
    "datos": ["datos", "data", "analitica", "analytics", "sql", "python",
               "machine learning", "tableau", "power bi", "bigquery", "estadistica"],
    "software": ["software", "desarrollo", "developer", "programacion", "backend",
                 "frontend", "fullstack", "devops", "cloud", "api", "java", "javascript",
                 "react", "angular", "node"],
    "gestion": ["gestion", "gerencia", "administracion", "pmo", "proyecto", "liderazgo",
                 "estrategia", "negocios"],
    "seguridad": ["seguridad", "ciberseguridad", "cybersecurity", "forense", "pentest",
                  "soc", "siem"],
    "redes": ["redes", "networking", "infraestructura", "cisco", "telecomunicaciones",
               "wifi", "firewall"],
    "criminologia": ["criminologia", "criminalistica", "policia", "fiscal", "penal",
                     "victimologia", "derecho penal", "investigacion criminal"],
    "finanzas": ["finanzas", "contabilidad", "financiero", "tesoreria", "presupuesto",
                 "auditoria", "tributario"],
}


def _infer_domain(text: str) -> str:
    n = _normalize(text)
    best = ("general", 0)
    for dom, kws in _DOMAIN_BUCKETS.items():
        hits = sum(1 for kw in kws if kw in n)
        if hits > best[1]:
            best = (dom, hits)
    return best[0]


# Domains that are considered compatible with each other even when not equal.
# E.g. "datos" programs are relevant for "software" jobs and vice-versa.
_COMPATIBLE_DOMAINS: Dict[str, set] = {
    "datos":    {"datos", "software", "general"},
    "software": {"software", "datos", "general"},
    "gestion":  {"gestion", "general"},
    "seguridad":{"seguridad", "general"},
    "redes":    {"redes", "general"},
    "criminologia": {"criminologia", "general"},
    "finanzas": {"finanzas", "general"},
    "general":  set(_DOMAIN_BUCKETS.keys()) | {"general"},
}


def _domains_compatible(d1: str, d2: str) -> bool:
    return d2 in _COMPATIBLE_DOMAINS.get(d1, {d1, "general"})


# ---------------------------------------------------------------------------
# Skill extraction — lookup-based (more robust than regex for Spanish text)
# ---------------------------------------------------------------------------

# All terms are stored in their NORMALISED form (lowercase ASCII, no accents).
# _normalize() is applied to both the lookup terms and the input text, so
# accent/case differences between DB text and the lookup list are irrelevant.
SKILLS_LOOKUP: List[str] = [
    # --- Programming languages ---
    "python", "sql", "r", "java", "javascript", "typescript",
    "scala", "golang", "rust", "php", "ruby", "c++", "c#", "kotlin", "swift",
    # --- BI / Visualisation tools ---
    "power bi", "tableau", "qlik", "qliksense", "qlixview",
    "looker", "metabase", "superset", "grafana",
    "google data studio", "datastudio", "data studio",
    # --- Data / ML libraries ---
    "pandas", "numpy", "scikit learn", "sklearn",
    "tensorflow", "pytorch", "keras", "hugging face",
    "xgboost", "lightgbm", "transformers",
    # --- Office / Productivity ---
    "excel", "word", "powerpoint", "google sheets",
    # --- Big Data / ETL / Orchestration ---
    "spark", "hadoop", "airflow", "kafka", "dbt",
    "flink", "hive", "presto", "databricks", "nifi",
    "etl", "elt", "data pipeline",
    # --- Cloud ---
    "aws", "azure", "gcp", "google cloud",
    # --- DevOps / Infra ---
    "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "gitlab", "github", "devops", "ci cd",
    # --- Databases ---
    "postgresql", "mysql", "mariadb", "mongodb",
    "redis", "elasticsearch", "cassandra",
    "bigquery", "snowflake", "redshift", "oracle",
    "bases de datos", "base de datos",
    # --- Data warehouse / Lakehouse ---
    "data warehouse", "data lake", "lakehouse", "data mart",
    # --- ML / AI concepts ---
    "machine learning", "aprendizaje automatico",
    "deep learning", "redes neuronales",
    "nlp", "procesamiento de lenguaje",
    "inteligencia artificial",
    "mineria de datos", "data mining",
    "computer vision", "vision por computador",
    "modelos predictivos", "modelo predictivo",
    "algoritmos", "algoritmo",
    # --- Statistics / Math ---
    "estadistica", "estadisticas",
    "r studio", "rstudio", "spss", "sas", "stata",
    "regresion", "regresion lineal", "regresion logistica",
    "series de tiempo", "clustering", "clasificacion",
    "analisis estadistico", "inferencia estadistica",
    "probabilidad",
    # --- Analytics / Data Science ---
    "analisis de datos", "analitica de datos",
    "ciencia de datos", "data science",
    "ingenieria de datos", "data engineering",
    "analitica avanzada", "analitica descriptiva",
    "analitica predictiva", "analitica prescriptiva",
    "inteligencia de negocios", "business intelligence",
    "visualizacion", "visualizacion de datos",
    "dashboard", "dashboards", "reporte", "reportes",
    "kpi", "metricas", "indicadores",
    # --- APIs / Architecture ---
    "api rest", "restful", "api", "microservicios",
    "microservices", "arquitectura de datos",
    "arquitectura de software",
    # --- Project / Methodology ---
    "scrum", "agile", "kanban", "jira", "confluence", "trello",
    "gestion de proyectos", "project management",
    "metodologias agiles",
    # --- Security ---
    "ciberseguridad", "cybersecurity",
    "siem", "soc", "pentest", "seguridad informatica",
    "forense digital", "analisis forense",
    # --- Networks ---
    "redes", "networking", "cisco", "telecomunicaciones",
    # --- Soft / transferable skills (measurable) ---
    "liderazgo", "trabajo en equipo", "comunicacion",
    "pensamiento analitico", "pensamiento critico",
    "resolucion de problemas", "toma de decisiones",
    "orientacion a resultados",
    # --- Criminology / Law / Social (for criminologia domain) ---
    "criminologia", "criminalistica", "victimologia",
    "investigacion criminal", "perfilacion criminal",
    "psicologia forense", "psicologia criminal",
    "derecho penal", "proceso penal", "sistema penal",
    "investigacion judicial", "policia judicial",
    "delitos informaticos", "evidencia digital",
    "cadena de custodia",
    # --- Finance / Accounting ---
    "finanzas", "contabilidad", "financiero",
    "tesoreria", "presupuesto", "auditoria", "tributario",
    "estados financieros", "niif", "ifrs",
    # --- Management / Strategy ---
    "gestion", "gerencia", "administracion",
    "estrategia", "planeacion estrategica",
    "transformacion digital",
    # --- Version control ---
    "git", "control de versiones",
]

# Pre-normalise the lookup list once at import time.
_SKILLS_LOOKUP_NORM: List[str] = [_normalize(s) for s in SKILLS_LOOKUP]


def extract_skills_by_lookup(text: str) -> List[str]:
    """
    Substring lookup of SKILLS_LOOKUP terms inside normalised text.
    More robust than regex for Spanish descriptions because it handles
    accent stripping uniformly on both sides before comparison.
    """
    n = _normalize(text)
    return sorted({term for term in _SKILLS_LOOKUP_NORM if term in n})


def _skills_from_text(text: str) -> List[str]:
    """Alias kept for backward compatibility — delegates to lookup."""
    return extract_skills_by_lookup(text)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProgramProfile:
    especializacion_id: int
    program_name: str
    skills: List[str]          # normalised skill tokens
    domain: str
    text: str                  # full text for embedding
    embedding: Optional[np.ndarray] = None
    skill_tokens: List[str] = field(default_factory=list)  # tokenized skills for BM25 query


@dataclass
class JobProfile:
    job_id: str
    title: str
    company: str
    skills: List[str]          # normalised
    domain: str
    text: str
    embedding: Optional[np.ndarray] = None
    skill_tokens: List[str] = field(default_factory=list)  # tokenized skills for BM25 corpus


@dataclass
class MatchResult:
    especializacion_id: int
    job_id: str
    program_name: str
    job_title: str
    company: str
    # Layer scores (0-100)
    semantic_score: float
    bm25_score: float
    coverage_score: float
    density_score: float
    pertinence_score: float    # F1(coverage, density)
    gap_score: float           # % micro skills NOT found in job
    final_score: float         # sem×0.55 + pertinence×0.45
    relevance_label: str       # high / medium / low / no_match
    # Skill sets
    common_skills: List[str]
    gap_skills: List[str]      # micro skills missing from job
    program_skills: List[str]
    job_skills: List[str]
    explanation: str
    content_hash: str


# ---------------------------------------------------------------------------
# Load data from DB
# ---------------------------------------------------------------------------

def load_programs(conn) -> List[ProgramProfile]:
    # Join strategy:
    # 1. PRIMARY:  microcurriculos.specialization_id = especializaciones.id
    #    (set by load_microcurriculos.py via migration 009)
    # 2. FALLBACK: microcurriculos.programa ILIKE especializaciones.nombre
    #    (for rows where specialization_id is still NULL)
    # Both arms are UNION-ed so no skills are lost.
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                e.id                            AS especializacion_id,
                e.nombre                        AS program_name,
                COALESCE(e.campo_laboral, '')   AS campo_laboral,
                COALESCE(e.plan_estudios, '')   AS plan_estudios,
                array_agg(
                    DISTINCT COALESCE(
                        NULLIF(ms.skill_normalized, ''),
                        NULLIF(ms.skill_original, '')
                    )
                ) FILTER (WHERE ms.id IS NOT NULL) AS micro_skills
            FROM especializaciones e
            LEFT JOIN microcurriculos mc ON (
                mc.specialization_id = e.id
                OR (
                    mc.specialization_id IS NULL
                    AND mc.programa IS NOT NULL
                    AND lower(mc.programa) = lower(e.nombre)
                )
            )
            LEFT JOIN microcurriculo_skills ms ON ms.microcurriculo_id = mc.id
            GROUP BY e.id, e.nombre, e.campo_laboral, e.plan_estudios
        """)
        rows = cur.fetchall()

    profiles: List[ProgramProfile] = []
    for row in rows:
        raw_skills: List[str] = [s for s in (row["micro_skills"] or []) if s]
        skills = [_normalize(s) for s in raw_skills if _normalize(s)]
        text = " ".join([
            row["program_name"] or "",
            row["campo_laboral"] or "",
            row["plan_estudios"] or "",
            " ".join(raw_skills),
        ])[:800]
        skill_tokens = _tokenize(" ".join(skills))
        profiles.append(ProgramProfile(
            especializacion_id=row["especializacion_id"],
            program_name=row["program_name"] or "",
            skills=skills,
            domain=_infer_domain(text),
            text=text,
            skill_tokens=skill_tokens,
        ))

    # Debug: show skill counts per program so zero-skill cases are visible
    for p in profiles:
        logger.info("  programa %-45s  skills=%d  %s",
                    p.program_name[:45], len(p.skills),
                    str(p.skills[:3]) if p.skills else "(sin skills — pertinencia=0)")

    return profiles


def load_jobs(conn) -> List[JobProfile]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('empleos', 'jobs')
        """)
        existing = {r["table_name"] for r in cur.fetchall()}

    # empleos: skill columns are skill_normalized / skill_original (no skill_nombre)
    # jobs:    skill column is canonical_skill in job_skills (job_id BIGINT FK)
    parts: List[str] = []
    if "empleos" in existing:
        parts.append("""
            SELECT
                e.id::text                                          AS job_id,
                COALESCE(e.titulo, '')                              AS title,
                COALESCE(e.empresa, '')                             AS company,
                COALESCE(e.descripcion, '')                         AS description,
                COALESCE(
                    NULLIF(es.skill_normalized, ''),
                    NULLIF(es.skill_original, '')
                )                                                   AS skill_name
            FROM empleos e
            LEFT JOIN empleo_skills es ON es.empleo_id = e.id
        """)
    if "jobs" in existing:
        parts.append("""
            SELECT
                j.id::text                              AS job_id,
                COALESCE(j.title, '')                   AS title,
                COALESCE(j.company, '')                 AS company,
                COALESCE(j.description, '')             AS description,
                COALESCE(js.canonical_skill, '')        AS skill_name
            FROM jobs j
            LEFT JOIN job_skills js ON js.job_id = j.id
        """)

    if not parts:
        logger.warning("No se encontraron tablas de empleos (empleos / jobs).")
        return []

    union_sql = " UNION ALL ".join(parts)
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT
                job_id, title, company, description,
                array_agg(DISTINCT skill_name)
                    FILTER (WHERE skill_name IS NOT NULL AND skill_name <> '') AS db_skills
            FROM ({union_sql}) sub
            GROUP BY job_id, title, company, description
        """)
        rows = cur.fetchall()

    profiles: List[JobProfile] = []
    n_from_db = 0
    n_from_text = 0
    for row in rows:
        db_skills = [_normalize(s) for s in (row["db_skills"] or []) if s]
        text = " ".join([row["title"], row["company"], row["description"]])[:800]
        # Always extract from text AND merge with DB skills so jobs inserted
        # by run_acquisition.py (which may have empty job_skills rows) still
        # get meaningful skill coverage for pertinence scoring.
        text_skills = _skills_from_text(text)
        skills = sorted(set(db_skills) | set(text_skills))
        if db_skills:
            n_from_db += 1
        elif text_skills:
            n_from_text += 1
        skill_tokens = _tokenize(" ".join(skills))
        profiles.append(JobProfile(
            job_id=row["job_id"],
            title=row["title"],
            company=row["company"],
            skills=skills,
            domain=_infer_domain(text),
            text=text,
            skill_tokens=skill_tokens,
        ))

    logger.info(
        "load_jobs: %d empleos cargados  "
        "(con skills en DB: %d  |  solo extracción de texto: %d  |  sin skills: %d)",
        len(profiles), n_from_db, n_from_text,
        len(profiles) - n_from_db - n_from_text,
    )
    # Debug: show first 3 jobs with their skill counts
    for j in profiles[:3]:
        logger.info("  empleo %-45s  skills=%d  %s",
                    j.title[:45], len(j.skills),
                    str(j.skills[:5]) if j.skills else "(sin skills)")
    return profiles


# ---------------------------------------------------------------------------
# CAPA 3 — pertinence calculation
# ---------------------------------------------------------------------------

def _pertinence_scores(
    program_skills: List[str],
    job_skills: List[str],
) -> Tuple[float, float, float, float, List[str], List[str]]:
    """
    Returns: coverage, density, pertinence_f1, gap_pct, common_list, gap_list.
    All percentages in 0-100 range.
    """
    ps = set(program_skills)
    js = set(job_skills)
    common = sorted(ps & js)
    gap = sorted(ps - js)            # micro skills NOT covered by this job

    coverage = len(common) / max(len(ps), 1) * 100   # recall
    density = len(common) / max(len(js), 1) * 100    # precision

    if coverage + density > 0:
        pertinence = 2 * coverage * density / (coverage + density)
    else:
        pertinence = 0.0

    gap_pct = len(gap) / max(len(ps), 1) * 100

    return coverage, density, pertinence, gap_pct, common, gap


# ---------------------------------------------------------------------------
# Relevance label
# ---------------------------------------------------------------------------

def _label(score: float, n_common: int) -> str:
    if score >= SCORE_HIGH and n_common >= 2:
        return "high"
    if score >= SCORE_MEDIUM and n_common >= 1:
        return "medium"
    if score >= SCORE_LOW and n_common >= 1:
        return "low"
    return "no_match"


# ---------------------------------------------------------------------------
# Explanation builder
# ---------------------------------------------------------------------------

def _explanation(r: "MatchResult") -> str:
    lines = [
        f"Programa: {r.program_name}",
        f"Empleo: {r.job_title} @ {r.company}",
        f"",
        f"CAPA 1 (semántico):  {r.semantic_score:.1f}/100",
        f"CAPA 2 (BM25):       {r.bm25_score:.1f}/100",
        f"CAPA 3 cobertura:    {r.coverage_score:.1f}%  "
        f"(densidad {r.density_score:.1f}%  →  pertinencia F1 {r.pertinence_score:.1f}%)",
        f"Gap microcurrículo:  {r.gap_score:.1f}%  ({len(r.gap_skills)} skills no cubiertos)",
        f"Score final:         {r.final_score:.1f}  [{r.relevance_label}]",
    ]
    if r.common_skills:
        lines.append(f"Skills comunes: {', '.join(r.common_skills[:12])}")
    if r.gap_skills:
        lines.append(f"Gap crítico:    {', '.join(r.gap_skills[:12])}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main matching pipeline
# ---------------------------------------------------------------------------

def run_matching(
    programs: Optional[List[ProgramProfile]] = None,
    jobs: Optional[List[JobProfile]] = None,
    *,
    min_score: float = PERTINENCE_THRESHOLD,
    domain_filter: bool = True,
    batch_size: int = 512,
) -> List[MatchResult]:
    """
    Full 3-layer matching.
    Loads from DB when programs/jobs are None.
    Returns results sorted by final_score descending.
    """
    conn = connect()
    try:
        if programs is None:
            logger.info("Cargando programas desde DB...")
            programs = load_programs(conn)
        if jobs is None:
            logger.info("Cargando empleos desde DB...")
            jobs = load_jobs(conn)
    finally:
        conn.close()

    if not programs or not jobs:
        logger.warning("Sin programas o empleos — nada que procesar.")
        return []

    logger.info("Generando embeddings para %d programas...", len(programs))
    all_texts = [p.text for p in programs] + [j.text for j in jobs]
    prog_vecs = embed_texts([p.text for p in programs], fit_corpus=all_texts)
    for i, p in enumerate(programs):
        p.embedding = prog_vecs[i]

    logger.info("Generando embeddings para %d empleos...", len(jobs))
    for start in range(0, len(jobs), batch_size):
        batch = jobs[start: start + batch_size]
        vecs = embed_texts([j.text for j in batch], fit_corpus=all_texts)
        for i, j in enumerate(batch):
            j.embedding = vecs[i]

    # BM25 corpus: one list of skill tokens per job
    logger.info("Construyendo índice BM25 sobre %d empleos...", len(jobs))
    bm25_corpus = [j.skill_tokens or _tokenize(j.text) for j in jobs]
    bm25_index = _make_bm25(bm25_corpus)

    results: List[MatchResult] = []
    _debug_done = False  # one-shot debug for first program-with-skills × first job
    for prog in programs:
        if prog.embedding is None:
            continue

        # BM25 query = skill tokens of the program's microcurrículo
        bm25_query = prog.skill_tokens or _tokenize(prog.text)
        bm25_scores = _bm25_normalised(bm25_index, bm25_query)

        for j_idx, job in enumerate(jobs):
            # --- Domain filter (OBLIGATORIO) ---
            domain_ok = _domains_compatible(prog.domain, job.domain)
            if domain_filter and not domain_ok:
                if not _debug_done and prog.skills:
                    logger.info(
                        "[DEBUG-DOMAIN-BLOCK] prog='%s' domain=%s  job='%s' domain=%s  → BLOQUEADO",
                        prog.program_name[:40], prog.domain, job.title[:40], job.domain,
                    )
                    _debug_done = True
                continue
            if job.embedding is None:
                continue

            # CAPA 1 — semantic
            sem = cosine_sim(prog.embedding, job.embedding) * 100

            # CAPA 2 — BM25
            bm25_norm = float(bm25_scores[j_idx]) * 100

            # CAPA 3 — pertinence
            coverage, density, pertinence, gap_pct, common, gap = _pertinence_scores(
                prog.skills, job.skills
            )

            # One-shot debug for first valid pair
            if not _debug_done and prog.skills and j_idx == 0:
                logger.info(
                    "[DEBUG] prog='%s' domain=%s | job='%s' domain=%s",
                    prog.program_name[:40], prog.domain, job.title[:40], job.domain,
                )
                logger.info("[DEBUG] prog.skills[:5] = %s", prog.skills[:5])
                logger.info("[DEBUG] job.skills[:5]  = %s", job.skills[:5])
                logger.info("[DEBUG] common_skills   = %s", common[:5])
                logger.info("[DEBUG] coverage=%.1f  density=%.1f  pertinence=%.1f  sem=%.1f",
                            coverage, density, pertinence, sem)
                _debug_done = True

            # Final score
            final = sem * SEMANTIC_WEIGHT + pertinence * PERTINENCE_WEIGHT

            label = _label(final, len(common))
            if final < min_score and label == "no_match":
                continue

            content_hash = hashlib.md5(
                f"{prog.especializacion_id}|{job.job_id}".encode()
            ).hexdigest()

            r = MatchResult(
                especializacion_id=prog.especializacion_id,
                job_id=job.job_id,
                program_name=prog.program_name,
                job_title=job.title,
                company=job.company,
                semantic_score=round(sem, 2),
                bm25_score=round(bm25_norm, 2),
                coverage_score=round(coverage, 2),
                density_score=round(density, 2),
                pertinence_score=round(pertinence, 2),
                gap_score=round(gap_pct, 2),
                final_score=round(final, 2),
                relevance_label=label,
                common_skills=common,
                gap_skills=gap[:20],
                program_skills=prog.skills[:50],
                job_skills=job.skills[:50],
                explanation="",
                content_hash=content_hash,
            )
            r.explanation = _explanation(r)
            results.append(r)

    results.sort(key=lambda r: r.final_score, reverse=True)
    logger.info("Matches generados: %d", len(results))
    return results


# ---------------------------------------------------------------------------
# DB schema for embedding tables
# ---------------------------------------------------------------------------

_EMBEDDING_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS microcurriculo_embeddings (
    id                 BIGSERIAL PRIMARY KEY,
    especializacion_id INTEGER   NOT NULL,
    model_name         TEXT      NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    embedding          BYTEA     NOT NULL,
    text_hash          TEXT      NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (especializacion_id, model_name)
);

CREATE TABLE IF NOT EXISTS job_embeddings (
    id          BIGSERIAL PRIMARY KEY,
    job_id      TEXT      NOT NULL,
    job_table   TEXT      NOT NULL DEFAULT 'jobs',
    model_name  TEXT      NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    embedding   BYTEA     NOT NULL,
    text_hash   TEXT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, job_table, model_name)
);
"""


def ensure_embedding_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(_EMBEDDING_TABLES_SQL)
    conn.commit()


def persist_embeddings(
    programs: List[ProgramProfile],
    jobs: List[JobProfile],
    conn,
) -> None:
    ensure_embedding_tables(conn)
    model = EMBED_MODEL_NAME
    with conn.cursor() as cur:
        for p in programs:
            if p.embedding is None:
                continue
            th = hashlib.md5(p.text.encode()).hexdigest()
            cur.execute("""
                INSERT INTO microcurriculo_embeddings
                    (especializacion_id, model_name, embedding, text_hash)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (especializacion_id, model_name) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        text_hash = EXCLUDED.text_hash,
                        created_at = now()
            """, (p.especializacion_id, model,
                  psycopg2.Binary(p.embedding.astype(np.float32).tobytes()), th))

        for j in jobs:
            if j.embedding is None:
                continue
            th = hashlib.md5(j.text.encode()).hexdigest()
            cur.execute("""
                INSERT INTO job_embeddings
                    (job_id, job_table, model_name, embedding, text_hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (job_id, job_table, model_name) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        text_hash = EXCLUDED.text_hash,
                        created_at = now()
            """, (j.job_id, "jobs", model,
                  psycopg2.Binary(j.embedding.astype(np.float32).tobytes()), th))
    conn.commit()
    logger.info("Embeddings persistidos: %d programas, %d empleos.", len(programs), len(jobs))


# ---------------------------------------------------------------------------
# Persist matches
# ---------------------------------------------------------------------------

def _ensure_run(conn, dataset_version: str = "hybrid_v2") -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ml_training_runs
                (run_name, task_name, dataset_version, notes)
            VALUES (
                'academic_relevance_engine',
                'program_job_match',
                %s,
                'Motor 3 capas: all-MiniLM-L6-v2 + BM25 + pertinencia F1'
            )
            ON CONFLICT (task_name, dataset_version) DO UPDATE
                SET run_name = EXCLUDED.run_name
            RETURNING id
        """, (dataset_version,))
        conn.commit()
        return cur.fetchone()["id"]


def save_matches(results: List[MatchResult], run_id: int, conn) -> int:
    saved = 0
    with conn.cursor() as cur:
        for r in results:
            raw_features = {
                "semantic_score": r.semantic_score,
                "bm25_score": r.bm25_score,
                "coverage_score": r.coverage_score,
                "density_score": r.density_score,
                "pertinence_score": r.pertinence_score,
                "gap_score": r.gap_score,
            }
            cur.execute("""
                INSERT INTO ml_program_job_matches (
                    run_id, program_document_id, job_document_id,
                    especializacion_id, empleo_id,
                    program_name, job_title, company,
                    match_method, model_name,
                    score_match, relevance_label,
                    role_alignment, skill_overlap_score, job_skill_density,
                    skills_en_comun, skills_faltantes, skills_programa, skills_empleo,
                    explanation, content_hash, raw_features
                ) VALUES (
                    %(run_id)s, 0, 0,
                    %(especializacion_id)s, %(job_id)s,
                    %(program_name)s, %(job_title)s, %(company)s,
                    'hybrid_v2', %(model_name)s,
                    %(final_score)s, %(relevance_label)s,
                    %(semantic_score)s, %(pertinence_score)s, %(density_score)s,
                    %(skills_en_comun)s::jsonb, %(skills_faltantes)s::jsonb,
                    %(skills_programa)s::jsonb, %(skills_empleo)s::jsonb,
                    %(explanation)s, %(content_hash)s, %(raw_features)s::jsonb
                )
                ON CONFLICT (run_id, program_document_id, job_document_id, match_method)
                DO UPDATE SET
                    score_match         = EXCLUDED.score_match,
                    relevance_label     = EXCLUDED.relevance_label,
                    role_alignment      = EXCLUDED.role_alignment,
                    skill_overlap_score = EXCLUDED.skill_overlap_score,
                    job_skill_density   = EXCLUDED.job_skill_density,
                    skills_en_comun     = EXCLUDED.skills_en_comun,
                    skills_faltantes    = EXCLUDED.skills_faltantes,
                    explanation         = EXCLUDED.explanation,
                    raw_features        = EXCLUDED.raw_features
            """, {
                "run_id": run_id,
                "especializacion_id": r.especializacion_id,
                "job_id": r.job_id,
                "program_name": r.program_name,
                "job_title": r.job_title,
                "company": r.company,
                "model_name": f"{EMBED_MODEL_NAME}+BM25",
                "final_score": r.final_score,
                "relevance_label": r.relevance_label,
                "semantic_score": r.semantic_score,
                "pertinence_score": r.pertinence_score,
                "density_score": r.density_score,
                "skills_en_comun": json.dumps(r.common_skills),
                "skills_faltantes": json.dumps(r.gap_skills),
                "skills_programa": json.dumps(r.program_skills),
                "skills_empleo": json.dumps(r.job_skills),
                "explanation": r.explanation,
                "content_hash": r.content_hash,
                "raw_features": json.dumps(raw_features),
            })
            saved += 1
    conn.commit()
    return saved


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    import argparse
    from datetime import date

    parser = argparse.ArgumentParser(
        description="Motor de pertinencia académica — 3 capas (sem + BM25 + F1)",
    )
    parser.add_argument("--min-score", type=float, default=PERTINENCE_THRESHOLD,
                        help="Score mínimo para guardar un match (default 65)")
    parser.add_argument("--no-domain-filter", action="store_true",
                        help="Desactivar filtro de dominio obligatorio")
    parser.add_argument("--persist-embeddings", action="store_true",
                        help="Guardar embeddings en tablas microcurriculo_embeddings / job_embeddings")
    parser.add_argument("--dry-run", action="store_true",
                        help="No escribir nada en DB")
    parser.add_argument("--limit-jobs", type=int, default=0,
                        help="Limitar número de empleos procesados (0 = todos)")
    parser.add_argument("--limit-programs", type=int, default=0,
                        help="Limitar número de programas (0 = todos)")
    parser.add_argument("--dataset-version", default="hybrid_v2",
                        help="Versión del dataset para ml_training_runs")
    parser.add_argument("--report", default="outputs/academic_relevance_report.md",
                        help="Ruta del reporte de salida")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    conn = connect()
    try:
        programs = load_programs(conn)
        jobs = load_jobs(conn)
    finally:
        conn.close()

    if args.limit_programs:
        programs = programs[: args.limit_programs]
    if args.limit_jobs:
        jobs = jobs[: args.limit_jobs]

    logger.info("Programas: %d  |  Empleos: %d", len(programs), len(jobs))

    results = run_matching(
        programs=programs,
        jobs=jobs,
        min_score=args.min_score,
        domain_filter=not args.no_domain_filter,
    )

    if not args.dry_run and results:
        conn2 = connect()
        try:
            if args.persist_embeddings:
                persist_embeddings(programs, jobs, conn2)
            run_id = _ensure_run(conn2, args.dataset_version)
            saved = save_matches(results, run_id, conn2)
            logger.info("Guardados %d matches en run_id=%d", saved, run_id)
        finally:
            conn2.close()

    # Summary report
    report_path = ROOT_DIR / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {lbl: sum(1 for r in results if r.relevance_label == lbl)
              for lbl in ("high", "medium", "low", "no_match")}
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Reporte Motor de Pertinencia Académica\n")
        f.write(f"**Fecha:** {date.today()}  |  **Versión:** {args.dataset_version}\n\n")
        f.write(f"## Configuración\n")
        f.write(f"- Modelo semántico: `{EMBED_MODEL_NAME}` (CPU, fallback TF-IDF)\n")
        f.write(f"- BM25: `rank-bm25` (fallback Python nativo)\n")
        f.write(f"- Pesos: semántico×{SEMANTIC_WEIGHT} + pertinencia×{PERTINENCE_WEIGHT}\n")
        f.write(f"- Umbral mínimo: {args.min_score}%\n")
        f.write(f"- Filtro de dominio: {'sí' if not args.no_domain_filter else 'no'}\n\n")
        f.write(f"## Resumen\n")
        f.write(f"- Programas: {len(programs)}\n")
        f.write(f"- Empleos: {len(jobs)}\n")
        f.write(f"- Matches totales: {len(results)}\n")
        for lbl, cnt in counts.items():
            f.write(f"  - `{lbl}`: {cnt}\n")
        f.write(f"\n## Top 20 matches\n")
        f.write(f"| # | Programa | Empleo | Empresa | Score | Semántico | Pertinencia | Label |\n")
        f.write(f"|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(results[:20], 1):
            f.write(
                f"| {i} | {r.program_name[:35]} | {r.job_title[:35]} | {r.company[:20]} "
                f"| {r.final_score:.1f} | {r.semantic_score:.1f} | {r.pertinence_score:.1f} "
                f"| {r.relevance_label} |\n"
            )
        if results:
            f.write(f"\n## Detalles primer match\n```\n{results[0].explanation}\n```\n")
    logger.info("Reporte guardado en: %s", report_path)


if __name__ == "__main__":
    main()
