"""
Motor de pertinencia académica de 3 capas.

CAPA 1 — Embeddings semánticos (sentence-transformers all-MiniLM-L6-v2, CPU)
CAPA 2 — Matching híbrido: cosine×0.60 + BM25×0.40, con filtro de dominio
CAPA 3 — Pertinencia académica: coverage_score, gap_score, pertinence_score (F1)

Thresholds: pertinente si score ≥ 65.
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
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
# DB connection
# ---------------------------------------------------------------------------

def _get_db_url() -> Optional[str]:
    for key in ("RAILWAY_DATABASE_URL", "DATABASE_URL"):
        val = os.getenv(key)
        if val:
            return val
    return None


def connect():
    url = _get_db_url()
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
# CAPA 1 — Embeddings
# ---------------------------------------------------------------------------

_EMBED_MODEL: Any = None  # lazy-loaded


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _EMBED_MODEL


def embed_texts(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    model = _get_embed_model()
    vecs = model.encode(texts, batch_size=64, show_progress_bar=False,
                        convert_to_numpy=True, normalize_embeddings=True)
    return vecs.astype(np.float32)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Both vectors assumed L2-normalised (sentence-transformers default)."""
    return float(np.clip(np.dot(a, b), 0.0, 1.0))


# ---------------------------------------------------------------------------
# CAPA 2 — BM25 (pure Python, no GPU needed)
# ---------------------------------------------------------------------------

class BM25:
    """Okapi BM25 over a static corpus."""

    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.n = len(corpus)
        dl = [len(d) for d in corpus]
        self.avgdl = sum(dl) / max(self.n, 1)
        self.dl = dl
        self._build_idf(corpus)

    def _build_idf(self, corpus: List[List[str]]) -> None:
        df: Dict[str, int] = defaultdict(int)
        for doc in corpus:
            for term in set(doc):
                df[term] += 1
        self.idf: Dict[str, float] = {}
        for term, freq in df.items():
            self.idf[term] = math.log((self.n - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query_tokens: List[str], doc_idx: int) -> float:
        doc = self.corpus[doc_idx]
        tf_map: Dict[str, int] = defaultdict(int)
        for t in doc:
            tf_map[t] += 1
        dl = self.dl[doc_idx]
        score = 0.0
        for term in query_tokens:
            if term not in self.idf:
                continue
            tf = tf_map.get(term, 0)
            num = self.idf[term] * tf * (self.k1 + 1)
            den = tf + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1))
            score += num / den
        return score

    def scores_for_query(self, query_tokens: List[str]) -> np.ndarray:
        out = np.array([self.score(query_tokens, i) for i in range(self.n)], dtype=np.float32)
        mx = out.max()
        if mx > 0:
            out /= mx
        return out


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProgramProfile:
    especializacion_id: int
    program_name: str
    skills: List[str]          # normalised
    domain: str
    text: str                  # for embedding
    embedding: Optional[np.ndarray] = None
    tokens: List[str] = field(default_factory=list)


@dataclass
class JobProfile:
    job_id: str
    title: str
    company: str
    skills: List[str]          # normalised
    domain: str
    text: str                  # for embedding
    embedding: Optional[np.ndarray] = None
    tokens: List[str] = field(default_factory=list)


@dataclass
class MatchResult:
    especializacion_id: int
    job_id: str
    program_name: str
    job_title: str
    company: str
    semantic_score: float      # 0-100
    bm25_score: float          # 0-100
    hybrid_score: float        # 0-100  (sem×0.60 + bm25×0.40)
    coverage_score: float      # 0-100  % skills programa cubiertos
    gap_score: float           # 0-100  skills demandados no en programa
    pertinence_score: float    # 0-100  F1(coverage, density)
    final_score: float         # 0-100
    relevance_label: str       # high/medium/low/no_match
    common_skills: List[str]
    missing_skills: List[str]  # en job pero no en programa
    program_skills: List[str]
    job_skills: List[str]
    explanation: str
    content_hash: str


# ---------------------------------------------------------------------------
# CAPA 1 — load & embed
# ---------------------------------------------------------------------------

def load_programs(conn) -> List[ProgramProfile]:
    profiles: List[ProgramProfile] = []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                e.id AS especializacion_id,
                e.nombre AS program_name,
                COALESCE(e.campo_laboral, '') AS campo_laboral,
                COALESCE(e.plan_estudios, '') AS plan_estudios,
                array_agg(
                    DISTINCT COALESCE(NULLIF(ms.skill_normalized,''), NULLIF(ms.skill_original,''))
                ) FILTER (WHERE ms.id IS NOT NULL) AS skills
            FROM especializaciones e
            LEFT JOIN microcurriculos mc ON mc.specialization_id = e.id
            LEFT JOIN microcurriculo_skills ms ON ms.microcurriculo_id = mc.id
            GROUP BY e.id, e.nombre, e.campo_laboral, e.plan_estudios
        """)
        rows = cur.fetchall()
    for row in rows:
        raw_skills = row["skills"] or []
        skills = [s for s in (_normalize(s) for s in raw_skills if s) if s]
        text = " ".join([row["program_name"] or "", row["campo_laboral"] or "",
                         row["plan_estudios"] or "", " ".join(raw_skills)])[:800]
        domain = _infer_domain(text)
        p = ProgramProfile(
            especializacion_id=row["especializacion_id"],
            program_name=row["program_name"] or "",
            skills=skills,
            domain=domain,
            text=text,
            tokens=_tokenize(text),
        )
        profiles.append(p)
    return profiles


def load_jobs(conn) -> List[JobProfile]:
    # Dynamic UNION ALL depending on which tables exist
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' AND table_name IN ('empleos','jobs')
        """)
        existing = {r["table_name"] for r in cur.fetchall()}

    parts: List[str] = []
    if "empleos" in existing:
        parts.append("""
            SELECT
                e.id::text AS job_id,
                COALESCE(e.titulo,'') AS title,
                COALESCE(e.empresa,'') AS company,
                COALESCE(e.descripcion,'') AS description,
                COALESCE(es.skill_nombre,'') AS skill_nombre
            FROM empleos e
            LEFT JOIN empleo_skills es ON es.empleo_id = e.id
        """)
    if "jobs" in existing:
        parts.append("""
            SELECT
                j.id::text AS job_id,
                COALESCE(j.title,'') AS title,
                COALESCE(j.company,'') AS company,
                COALESCE(j.description,'') AS description,
                '' AS skill_nombre
            FROM jobs j
        """)

    if not parts:
        logger.warning("No job tables found (empleos / jobs).")
        return []

    union_sql = " UNION ALL ".join(parts)
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT job_id, title, company, description,
                   array_agg(DISTINCT skill_nombre) FILTER (WHERE skill_nombre <> '') AS db_skills
            FROM ({union_sql}) sub
            GROUP BY job_id, title, company, description
        """)
        rows = cur.fetchall()

    profiles: List[JobProfile] = []
    for row in rows:
        db_skills = [_normalize(s) for s in (row["db_skills"] or []) if s]
        text = " ".join([row["title"], row["company"], row["description"]])[:800]
        skills = db_skills or _extract_skills_from_text(text)
        domain = _infer_domain(text)
        profiles.append(JobProfile(
            job_id=row["job_id"],
            title=row["title"],
            company=row["company"],
            skills=skills,
            domain=domain,
            text=text,
            tokens=_tokenize(text),
        ))
    return profiles


# ---------------------------------------------------------------------------
# Domain filter helpers
# ---------------------------------------------------------------------------

_DOMAIN_BUCKETS: Dict[str, List[str]] = {
    "datos": ["datos", "data", "analitica", "analitics", "analytics", "sql", "python",
               "machine learning", "tableau", "power bi", "bigquery"],
    "software": ["software", "desarrollo", "developer", "programacion", "backend",
                 "frontend", "fullstack", "devops", "cloud", "api", "java", "javascript"],
    "gestion": ["gestion", "gerencia", "administracion", "pmo", "proyecto", "liderazgo"],
    "seguridad": ["seguridad", "ciberseguridad", "cybersecurity", "forense", "pentest"],
    "redes": ["redes", "networking", "infraestructura", "cisco", "telecomunicaciones"],
    "criminologia": ["criminologia", "criminalistica", "policia", "fiscal", "penal",
                     "victimologia", "derecho penal"],
    "finanzas": ["finanzas", "contabilidad", "financiero", "tesoreria", "presupuesto"],
}


def _infer_domain(text: str) -> str:
    n = _normalize(text)
    best = ("general", 0)
    for domain, kws in _DOMAIN_BUCKETS.items():
        hits = sum(1 for kw in kws if kw in n)
        if hits > best[1]:
            best = (domain, hits)
    return best[0]


def _domains_compatible(d1: str, d2: str) -> bool:
    if d1 == "general" or d2 == "general":
        return True
    return d1 == d2


# ---------------------------------------------------------------------------
# Lightweight skill extraction from free text
# ---------------------------------------------------------------------------

_SKILL_PATTERNS = re.compile(
    r"\b(python|sql|r\b|java(?:script)?|typescript|scala|c\+\+|c#|"
    r"power\s*bi|tableau|qlik|looker|metabase|"
    r"pandas|numpy|scikit[- ]learn|tensorflow|pytorch|keras|"
    r"excel|word|powerpoint|outlook|"
    r"spark|hadoop|airflow|kafka|dbt|"
    r"aws|azure|gcp|docker|kubernetes|terraform|"
    r"postgresql|mysql|mongodb|redis|elasticsearch|"
    r"machine\s*learning|deep\s*learning|nlp|"
    r"git|jira|confluence|scrum|agile|"
    r"analisis\s*de\s*datos?|visualizacion|estadistica|"
    r"gestion\s*de\s*proyectos?|liderazgo)\b",
    re.IGNORECASE,
)


def _extract_skills_from_text(text: str) -> List[str]:
    found = set()
    for m in _SKILL_PATTERNS.finditer(text):
        found.add(_normalize(m.group(0)))
    return list(found)


# ---------------------------------------------------------------------------
# CAPA 3 — Pertinence scores
# ---------------------------------------------------------------------------

def _compute_skill_scores(
    program_skills: List[str],
    job_skills: List[str],
) -> Tuple[float, float, float, List[str], List[str]]:
    """
    Returns: coverage, density, pertinence (F1), common, missing.
    All scores in 0-100 range.
    """
    ps = set(program_skills)
    js = set(job_skills)
    common = ps & js
    missing = js - ps  # demanded but not in program

    coverage = len(common) / max(len(ps), 1) * 100  # recall
    density = len(common) / max(len(js), 1) * 100   # precision

    if coverage + density > 0:
        pertinence = 2 * coverage * density / (coverage + density)
    else:
        pertinence = 0.0

    return coverage, density, pertinence, sorted(common), sorted(missing)


# ---------------------------------------------------------------------------
# Main matching function
# ---------------------------------------------------------------------------

SEMANTIC_WEIGHT = 0.60
BM25_WEIGHT = 0.40

SCORE_HIGH = 75.0
SCORE_MEDIUM = 55.0
SCORE_LOW = 35.0
PERTINENCE_THRESHOLD = 65.0


def _label(score: float, common_count: int) -> str:
    if score >= SCORE_HIGH and common_count >= 2:
        return "high"
    if score >= SCORE_MEDIUM and common_count >= 1:
        return "medium"
    if score >= SCORE_LOW and common_count >= 1:
        return "low"
    return "no_match"


def _build_explanation(
    program_name: str,
    job_title: str,
    semantic: float,
    bm25: float,
    coverage: float,
    gap: float,
    pertinence: float,
    common: List[str],
    missing: List[str],
) -> str:
    parts = [
        f"Programa: {program_name}  →  Empleo: {job_title}",
        f"Score semántico: {semantic:.1f}  |  BM25: {bm25:.1f}  |  Híbrido: {semantic*SEMANTIC_WEIGHT + bm25*BM25_WEIGHT:.1f}",
        f"Cobertura (skills micro cubiertos): {coverage:.1f}%",
        f"Skills demandados sin cobertura: {gap:.1f}%  ({len(missing)} skills faltantes)",
        f"Pertinencia F1: {pertinence:.1f}%",
    ]
    if common:
        parts.append(f"Skills comunes: {', '.join(common[:10])}")
    if missing:
        parts.append(f"Gap crítico: {', '.join(missing[:10])}")
    return "\n".join(parts)


def run_matching(
    programs: Optional[List[ProgramProfile]] = None,
    jobs: Optional[List[JobProfile]] = None,
    *,
    min_score: float = PERTINENCE_THRESHOLD,
    domain_filter: bool = True,
    batch_size: int = 512,
) -> List[MatchResult]:
    """
    Full 3-layer matching.  If programs/jobs are not passed, loads from DB.
    """
    conn = connect()
    try:
        if programs is None:
            logger.info("Cargando programas desde DB...")
            programs = load_programs(conn)
        if jobs is None:
            logger.info("Cargando empleos desde DB...")
            jobs = load_jobs(conn)

        if not programs or not jobs:
            logger.warning("Sin programas o empleos — nada que procesar.")
            return []

        logger.info("Generando embeddings programas (%d)...", len(programs))
        prog_vecs = embed_texts([p.text for p in programs])
        for i, p in enumerate(programs):
            p.embedding = prog_vecs[i]

        logger.info("Generando embeddings empleos (%d)...", len(jobs))
        # Process in batches to manage memory
        all_job_vecs: List[np.ndarray] = []
        for start in range(0, len(jobs), batch_size):
            batch = jobs[start: start + batch_size]
            vecs = embed_texts([j.text for j in batch])
            for i, j in enumerate(batch):
                j.embedding = vecs[i]
            all_job_vecs.extend(list(vecs))

        # BM25 — one corpus per program domain for efficiency
        # For scalability: build a single BM25 corpus over all job tokens
        job_corpus = [j.tokens for j in jobs]
        bm25_index = BM25(job_corpus)

        results: List[MatchResult] = []
        for prog in programs:
            if prog.embedding is None:
                continue
            bm25_scores = bm25_index.scores_for_query(prog.tokens)

            for j_idx, job in enumerate(jobs):
                if domain_filter and not _domains_compatible(prog.domain, job.domain):
                    continue
                if job.embedding is None:
                    continue

                sem = cosine_sim(prog.embedding, job.embedding) * 100
                bm25_norm = float(bm25_scores[j_idx]) * 100
                hybrid = sem * SEMANTIC_WEIGHT + bm25_norm * BM25_WEIGHT

                # CAPA 3
                coverage, density, pertinence, common, missing = _compute_skill_scores(
                    prog.skills, job.skills)

                # Gap score: % job skills not in program (capped at 100)
                gap = min(len(missing) / max(len(job.skills), 1) * 100, 100.0)

                # Weighted final score
                final = hybrid * 0.55 + pertinence * 0.45

                if final < min_score and _label(final, len(common)) == "no_match":
                    continue

                explanation = _build_explanation(
                    prog.program_name, job.title, sem, bm25_norm,
                    coverage, gap, pertinence, common, missing,
                )
                content_hash = hashlib.md5(
                    f"{prog.especializacion_id}|{job.job_id}".encode()
                ).hexdigest()

                results.append(MatchResult(
                    especializacion_id=prog.especializacion_id,
                    job_id=job.job_id,
                    program_name=prog.program_name,
                    job_title=job.title,
                    company=job.company,
                    semantic_score=round(sem, 2),
                    bm25_score=round(bm25_norm, 2),
                    hybrid_score=round(hybrid, 2),
                    coverage_score=round(coverage, 2),
                    gap_score=round(gap, 2),
                    pertinence_score=round(pertinence, 2),
                    final_score=round(final, 2),
                    relevance_label=_label(final, len(common)),
                    common_skills=common,
                    missing_skills=sorted(missing)[:20],
                    program_skills=prog.skills[:50],
                    job_skills=job.skills[:50],
                    explanation=explanation,
                    content_hash=content_hash,
                ))

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Persist results
# ---------------------------------------------------------------------------

_ENSURE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS microcurriculo_embeddings (
    id            BIGSERIAL PRIMARY KEY,
    especializacion_id INTEGER NOT NULL,
    model_name    TEXT NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    embedding     BYTEA NOT NULL,
    text_hash     TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (especializacion_id, model_name)
);

CREATE TABLE IF NOT EXISTS job_embeddings (
    id            BIGSERIAL PRIMARY KEY,
    job_id        TEXT NOT NULL,
    job_table     TEXT NOT NULL DEFAULT 'jobs',
    model_name    TEXT NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    embedding     BYTEA NOT NULL,
    text_hash     TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, job_table, model_name)
);
"""


def ensure_embedding_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(_ENSURE_TABLES_SQL)
    conn.commit()


def persist_embeddings(programs: List[ProgramProfile], jobs: List[JobProfile], conn) -> None:
    ensure_embedding_tables(conn)
    model_name = "all-MiniLM-L6-v2"
    with conn.cursor() as cur:
        for p in programs:
            if p.embedding is None:
                continue
            text_hash = hashlib.md5(p.text.encode()).hexdigest()
            vec_bytes = p.embedding.astype(np.float32).tobytes()
            cur.execute("""
                INSERT INTO microcurriculo_embeddings
                    (especializacion_id, model_name, embedding, text_hash)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (especializacion_id, model_name) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        text_hash = EXCLUDED.text_hash,
                        created_at = now()
            """, (p.especializacion_id, model_name, psycopg2.Binary(vec_bytes), text_hash))

        for j in jobs:
            if j.embedding is None:
                continue
            text_hash = hashlib.md5(j.text.encode()).hexdigest()
            vec_bytes = j.embedding.astype(np.float32).tobytes()
            cur.execute("""
                INSERT INTO job_embeddings
                    (job_id, job_table, model_name, embedding, text_hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (job_id, job_table, model_name) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        text_hash = EXCLUDED.text_hash,
                        created_at = now()
            """, (j.job_id, "jobs", model_name, psycopg2.Binary(vec_bytes), text_hash))
    conn.commit()


def save_matches(results: List[MatchResult], run_id: int, conn) -> int:
    saved = 0
    with conn.cursor() as cur:
        for r in results:
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
                    %(run_id)s,
                    0, 0,
                    %(especializacion_id)s, %(job_id)s,
                    %(program_name)s, %(job_title)s, %(company)s,
                    'hybrid_v1', 'all-MiniLM-L6-v2+BM25',
                    %(final_score)s, %(relevance_label)s,
                    %(semantic_score)s, %(pertinence_score)s, %(coverage_score)s,
                    %(skills_en_comun)s::jsonb, %(skills_faltantes)s::jsonb,
                    %(skills_programa)s::jsonb, %(skills_empleo)s::jsonb,
                    %(explanation)s, %(content_hash)s, %(raw_features)s::jsonb
                )
                ON CONFLICT (run_id, program_document_id, job_document_id, match_method)
                DO UPDATE SET
                    score_match      = EXCLUDED.score_match,
                    relevance_label  = EXCLUDED.relevance_label,
                    role_alignment   = EXCLUDED.role_alignment,
                    skill_overlap_score = EXCLUDED.skill_overlap_score,
                    job_skill_density   = EXCLUDED.job_skill_density,
                    skills_en_comun  = EXCLUDED.skills_en_comun,
                    skills_faltantes = EXCLUDED.skills_faltantes,
                    explanation      = EXCLUDED.explanation,
                    content_hash     = EXCLUDED.content_hash,
                    raw_features     = EXCLUDED.raw_features
            """, {
                "run_id": run_id,
                "especializacion_id": r.especializacion_id,
                "job_id": r.job_id,
                "program_name": r.program_name,
                "job_title": r.job_title,
                "company": r.company,
                "final_score": r.final_score,
                "relevance_label": r.relevance_label,
                "semantic_score": r.semantic_score,
                "pertinence_score": r.pertinence_score,
                "coverage_score": r.coverage_score,
                "skills_en_comun": json.dumps(r.common_skills),
                "skills_faltantes": json.dumps(r.missing_skills),
                "skills_programa": json.dumps(r.program_skills),
                "skills_empleo": json.dumps(r.job_skills),
                "explanation": r.explanation,
                "content_hash": r.content_hash,
                "raw_features": json.dumps({
                    "semantic_score": r.semantic_score,
                    "bm25_score": r.bm25_score,
                    "hybrid_score": r.hybrid_score,
                    "coverage_score": r.coverage_score,
                    "gap_score": r.gap_score,
                    "pertinence_score": r.pertinence_score,
                }),
            })
            saved += 1
    conn.commit()
    return saved


def ensure_run(conn, *, dataset_version: str = "hybrid_v1") -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ml_training_runs (run_name, task_name, dataset_version, notes)
            VALUES ('academic_relevance_engine', 'program_job_match', %s,
                    'Motor híbrido: all-MiniLM-L6-v2 + BM25')
            ON CONFLICT (task_name, dataset_version) DO UPDATE
                SET run_name = EXCLUDED.run_name
            RETURNING id
        """, (dataset_version,))
        return cur.fetchone()["id"]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Motor de pertinencia académica 3 capas")
    parser.add_argument("--min-score", type=float, default=PERTINENCE_THRESHOLD,
                        help="Score mínimo para guardar un match (default 65)")
    parser.add_argument("--no-domain-filter", action="store_true",
                        help="Desactivar filtro de dominio")
    parser.add_argument("--persist-embeddings", action="store_true",
                        help="Guardar embeddings en DB para reusar")
    parser.add_argument("--dry-run", action="store_true",
                        help="No escribir en DB")
    parser.add_argument("--limit-jobs", type=int, default=0,
                        help="Limitar número de empleos (0=todos)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    conn = connect()
    try:
        programs = load_programs(conn)
        jobs = load_jobs(conn)
        if args.limit_jobs:
            jobs = jobs[: args.limit_jobs]

        logger.info("Programas: %d  |  Empleos: %d", len(programs), len(jobs))
    finally:
        conn.close()

    results = run_matching(
        programs=programs,
        jobs=jobs,
        min_score=args.min_score,
        domain_filter=not args.no_domain_filter,
    )

    logger.info("Matches generados: %d", len(results))
    for r in results[:10]:
        logger.info("  [%s] %.1f  %s → %s",
                    r.relevance_label, r.final_score, r.program_name[:40], r.job_title[:40])

    if not args.dry_run and results:
        conn2 = connect()
        try:
            if args.persist_embeddings:
                persist_embeddings(programs, jobs, conn2)
            run_id = ensure_run(conn2)
            saved = save_matches(results, run_id, conn2)
            logger.info("Guardados: %d matches en run_id=%d", saved, run_id)
        finally:
            conn2.close()

    # Write summary report
    report_path = ROOT_DIR / "outputs" / "academic_relevance_report.md"
    report_path.parent.mkdir(exist_ok=True)
    high = sum(1 for r in results if r.relevance_label == "high")
    medium = sum(1 for r in results if r.relevance_label == "medium")
    low = sum(1 for r in results if r.relevance_label == "low")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Reporte Motor de Pertinencia Académica\n")
        f.write(f"**Fecha:** {__import__('datetime').date.today()}\n\n")
        f.write(f"## Resumen\n")
        f.write(f"- Programas procesados: {len(programs)}\n")
        f.write(f"- Empleos procesados: {len(jobs)}\n")
        f.write(f"- Matches totales: {len(results)}\n")
        f.write(f"  - Alta pertinencia: {high}\n")
        f.write(f"  - Media pertinencia: {medium}\n")
        f.write(f"  - Baja pertinencia: {low}\n\n")
        f.write(f"## Arquitectura\n")
        f.write(f"- CAPA 1: sentence-transformers all-MiniLM-L6-v2 (CPU), peso 0.60\n")
        f.write(f"- CAPA 2: BM25 léxico, peso 0.40\n")
        f.write(f"- CAPA 3: F1(coverage, density) = pertinence_score, umbral {PERTINENCE_THRESHOLD}%\n")
        f.write(f"- Score final = híbrido×0.55 + pertinencia×0.45\n\n")
        if results:
            f.write(f"## Top 10 matches\n")
            f.write(f"| Programa | Empleo | Score | Label |\n|---|---|---|---|\n")
            for r in results[:10]:
                f.write(f"| {r.program_name[:35]} | {r.job_title[:35]} | {r.final_score:.1f} | {r.relevance_label} |\n")
    logger.info("Reporte: %s", report_path)


if __name__ == "__main__":
    main()
