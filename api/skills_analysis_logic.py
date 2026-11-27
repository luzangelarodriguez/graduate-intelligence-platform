"""
Pure-logic module for dashboard_skills_analysis.

No database access — all functions operate on plain Python data structures
so they can be unit-tested without a live database.

Terminology
-----------
market_skill   : skill extracted from job postings for a given program
prog_skill     : skill extracted from that program's microcurrículum
transversal    : generic soft/management skill present in virtually every curriculum;
                 counted separately and excluded from cobertura_pct and brechas_criticas
fortaleza      : non-transversal market skill that is covered by at least one prog skill
brecha         : non-transversal market skill with no prog coverage
brecha_crítica : brecha whose frecuencia_mercado >= p66 of brecha frequencies
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import NamedTuple

from api.skill_aliases import SKILL_ALIASES


# ── Normalisation ──────────────────────────────────────────────────────────────

def norm(s: str) -> str:
    """
    Lowercase, strip combining diacritics, normalise separators
    (hyphen / dot / underscore) → single space, collapse whitespace.
    """
    text = unicodedata.normalize("NFD", s.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[-._]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ── norm_match helpers ─────────────────────────────────────────────────────────

_QUALIFIER_RE = re.compile(
    r"\b(avanzado|avanzada|basico|basica|intermedio|intermedia|nivel|experto|experta)\b"
)


def _depluralize(word: str) -> str:
    """
    Strip trailing 's' only for English-style plurals (consonant + s).
    Leaves Spanish vowel-stem plurals (redes, sociales) intact.
    """
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        if word[-2] not in "aeiou":
            return word[:-1]
    return word


SINONIMOS: dict[str, str] = {
    "mercadeo": "marketing",
    "redes sociales": "social media",
    "e commerce": "e commerce",
    "ecommerce": "e commerce",
    "comercio electronico": "e commerce",
    "indicadores": "metricas",
    "kpis": "metricas",
}

PARAGUAS: dict[str, frozenset[str]] = {
    "marketing digital": frozenset({
        "seo",
        "sem",
        "email marketing",
        "google ads",
        "social media",
        "google analytics",
        "community manager",
    }),
}


def norm_match(s: str) -> str:
    """
    Normalise for MATCHING only — never use for display.

    Steps on top of norm():
    1. Strip level qualifiers (avanzado, basico, intermedio, nivel, experto…)
    2. Depluralize English-style plurals word-by-word (dashboards → dashboard)
    3. Apply SINONIMOS map (mercadeo → marketing, redes sociales → social media…)
    """
    text = norm(s)
    text = _QUALIFIER_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = " ".join(_depluralize(w) for w in text.split())
    return SINONIMOS.get(text, text)


def canonical_key(skill: str) -> str:
    """
    Grouping key for frequency counting in process_job_skill_rows.

    Applies norm_match() (strips level qualifiers, English plurals, synonyms)
    then looks up SKILL_ALIASES for any remaining explicit mappings (e.g.
    Spanish plurals that _depluralize does not handle).
    """
    k = norm_match(skill)
    return SKILL_ALIASES.get(k, k)


# ── Transversal skills ─────────────────────────────────────────────────────────

TRANSVERSALES: frozenset[str] = frozenset({
    "gestion",
    "estrategia",
    "comunicacion",
    "evaluacion",
    "administracion",
    "trabajo en equipo",
    "liderazgo",
    "toma de decisiones",
    "pensamiento critico",
    "resolucion de problemas",
    "organizacion",
    "planificacion",
    "adaptabilidad",
    "innovacion",
    "creatividad",
    "negociacion",
    "servicio al cliente",
    "atencion al cliente",
    "trabajo bajo presion",
})


def is_transversal(skill: str) -> bool:
    """True if the normalised skill name is in the TRANSVERSALES set."""
    return norm(skill) in TRANSVERSALES


# ── Always-discard noise skills ───────────────────────────────────────────────
# Audit of 50 matches containing "sas" across programs 13/20/109/146 (last run):
# 49 of 50 were the S.A.S. legal suffix in a company name or a job-board noise
# block; only 1 was SAS the statistical software. The analytics-context filter
# (sas_has_analytics_context) is not reliable enough — discard "sas" universally.
RUIDO_SIEMPRE: frozenset[str] = frozenset({
    norm("sas"),    # "sas" — almost always S.A.S. legal suffix in Colombian job ads
    norm("s a s"),  # "S.A.S." normalises to "s a s"
})


def sas_has_analytics_context(job_skills: frozenset[str]) -> bool:
    """Kept for external callers; always returns False — SAS is universally discarded."""
    return False


# ── Phrase matching ────────────────────────────────────────────────────────────

def _phrase_re(phrase: str) -> re.Pattern[str]:
    """Compile a whole-word regex for a normalised phrase."""
    return re.compile(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])")


def phrase_covers(market_skill: str, prog_skill: str) -> bool:
    """
    Return True if prog_skill CONTAINS market_skill as a whole-word phrase
    AND market_skill satisfies the minimum-specificity guard:
        - has >= 2 words, OR
        - has >= 6 non-space letters.

    This replaces the old bidirectional startswith() rule, which inflated
    coverage by allowing short generic tokens like 'gestion' to absorb
    anything starting with those letters.
    """
    nm = norm(market_skill)
    np = norm(prog_skill)
    if nm == np:
        return True
    words = nm.split()
    letters = len(nm.replace(" ", ""))
    if len(words) < 2 and letters < 6:
        # Too short and single-word → only exact match counts
        return False
    return bool(_phrase_re(nm).search(np))


# ── Within-job subsunción ──────────────────────────────────────────────────────

def subsume_job_skills(skills: list[str]) -> list[str]:
    """
    For one job: if skill A appears as a whole-word phrase inside skill B,
    drop A and keep B (the more specific form wins).
    E.g. ['redes', 'redes sociales'] → ['redes sociales']
    """
    normed = [(s, norm(s)) for s in skills]
    dominated: set[int] = set()
    for i, (_, n_i) in enumerate(normed):
        if i in dominated:
            continue
        for j, (_, n_j) in enumerate(normed):
            if i == j or j in dominated:
                continue
            # Is i a phrase inside j?  (i dominated by j)
            if n_i != n_j and bool(_phrase_re(n_i).search(n_j)):
                dominated.add(i)
                break
    return [s for idx, (s, _) in enumerate(normed) if idx not in dominated]


# ── Frequency threshold ────────────────────────────────────────────────────────

HARD_CAP: int = 60  # maximum number of market skills returned


def frequency_threshold(n_matches: int) -> int:
    """
    A skill must appear in at least this many job matches to be included.
    Scales with corpus size: max(2, ceil(0.15 × n_matches)).
    """
    return max(2, math.ceil(0.15 * n_matches))


# ── Per-job skill processing (subsunción + SAS filter) ────────────────────────

def process_job_skill_rows(
    rows: list[dict],
    min_freq: int | None = None,
    hard_cap: int | None = HARD_CAP,
) -> tuple[list[dict], int]:
    """
    Given rows of {match_id, skill} from the per-job query:
      1. Group by match_id.
      2. Apply subsunción within each job.
      3. Discard skills in RUIDO_SIEMPRE (e.g. "sas" / "s a s").
      4. Count per-skill frequencies (how many jobs mention the skill).
      5. Apply min_freq (default: frequency_threshold(n_matches)) and hard_cap.

    Parameters:
        min_freq:  minimum frequency a skill must reach to be included.
                   None → use frequency_threshold(n_matches) = max(2, ceil(0.15·n)).
        hard_cap:  maximum number of skills returned.
                   None → no cap.  Default: HARD_CAP (60).

    Returns:
        (skills_mercado_raw, n_matches)
    where skills_mercado_raw is a list of {skill, frecuencia} dicts,
    sorted descending by frecuencia, len <= hard_cap (if set).
    """
    # Build per-job skill sets
    jobs: dict[str, list[str]] = {}
    for row in rows:
        mid = str(row["match_id"])
        skill = row.get("skill") or ""
        if skill and "skillmatch" not in skill.lower():
            jobs.setdefault(mid, []).append(skill)

    n_matches = len(jobs)
    threshold = min_freq if min_freq is not None else frequency_threshold(n_matches)

    # Apply subsunción, alias dedup, noise filter per job; accumulate frequencies.
    # Each canonical key is counted at most once per vacancy (set-based dedup),
    # so no frequency can exceed n_matches.
    freq: dict[str, int] = {}
    for job_skills_raw in jobs.values():
        job_skills = subsume_job_skills(job_skills_raw)
        seen_keys: set[str] = set()
        for skill in job_skills:
            if norm(skill) in RUIDO_SIEMPRE:
                continue
            key = canonical_key(skill)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            if key not in freq:
                freq[key] = 0
            freq[key] += 1

    # Build display-name map: alias destination if skill has an explicit alias,
    # else first-seen raw form (unchanged from previous behaviour).
    display: dict[str, str] = {}
    for row in rows:
        skill = row.get("skill") or ""
        if not skill or "skillmatch" in skill.lower():
            continue
        key = canonical_key(skill)
        if key not in display:
            nm = norm_match(skill)
            display[key] = SKILL_ALIASES.get(nm, skill)

    # Filter by threshold and sort
    candidates = [
        {"skill": display[k], "frecuencia": v}
        for k, v in freq.items()
        if v >= threshold and k in display
    ]
    candidates.sort(key=lambda x: -x["frecuencia"])
    return (candidates[:hard_cap] if hard_cap is not None else candidates), n_matches


# ── Cross analysis ─────────────────────────────────────────────────────────────

class MatchDetail(NamedTuple):
    prog_skill: str
    rule: str  # "exacta" | "frase" | "sinonimo_o_nivel" | "paraguas: ..." | "ninguna"


def find_prog_match(market_skill: str, prog_skills: list[dict]) -> MatchDetail:
    """
    Find which program skill covers market_skill (and by what rule).

    Uses canonical_key() for comparison so that level qualifiers (avanzado/basico),
    English plurals (dashboards→dashboard), synonyms (mercadeo→marketing), and
    explicit aliases (reportes→reporte, analista de datos→analisis de datos) are
    unified before comparing.  Rule labels:
        "exacta"          : surface-identical after norm()
        "frase"           : prog contains market as whole-word phrase (no transformation)
        "sinonimo_o_nivel": match required synonym mapping, qualifier stripping, or alias
        "paraguas: ..."   : umbrella skill covered by ≥3 of its components
        "ninguna"         : no coverage found
    """
    nm = canonical_key(market_skill)
    n_orig_m = norm(market_skill)
    transformed_m = nm != n_orig_m

    # 1. Try exact match via canonical_key
    for p in prog_skills:
        np = canonical_key(p["skill"])
        if nm == np:
            if transformed_m or np != norm(p["skill"]):
                return MatchDetail(p["skill"], "sinonimo_o_nivel")
            return MatchDetail(p["skill"], "exacta")

    # 2. Try phrase match via canonical_key (prog contains market phrase)
    words = nm.split()
    letters = len(nm.replace(" ", ""))
    if len(words) >= 2 or letters >= 6:
        for p in prog_skills:
            np = canonical_key(p["skill"])
            if nm != np and bool(_phrase_re(nm).search(np)):
                if transformed_m or canonical_key(p["skill"]) != norm(p["skill"]):
                    return MatchDetail(p["skill"], "sinonimo_o_nivel")
                return MatchDetail(p["skill"], "frase")

    # 3. Try PARAGUAS umbrella rule
    if nm in PARAGUAS:
        components = PARAGUAS[nm]
        matched = [
            comp
            for comp in components
            if any(canonical_key(p["skill"]) == comp for p in prog_skills)
        ]
        if len(matched) >= 3:
            rule = "paraguas: " + ", ".join(sorted(matched))
            return MatchDetail("<paraguas>", rule)

    return MatchDetail("", "ninguna")


def compute_brechas_criticas(brechas: list[dict]) -> list[dict]:
    """
    Return brechas whose frecuencia_mercado >= p66 of brecha frequencies
    (same percentile used by the old KPI header 'brechasAlta' in the TSX).
    """
    if not brechas:
        return []
    freqs = sorted(b["frecuencia_mercado"] for b in brechas)
    idx66 = max(0, math.floor(len(freqs) * 2 / 3))
    threshold = freqs[idx66]
    return [b for b in brechas if b["frecuencia_mercado"] >= threshold]


def cross_analyze(
    market_skills: list[dict],
    prog_skills: list[dict],
    n_matches: int = 0,
) -> dict:
    """
    Core cross-analysis.

    Returns a dict with:
        fortalezas         : non-transversal market skills covered by curriculum
        brechas            : non-transversal market skills NOT covered
        transversales      : generic/management skills (excluded from cobertura_pct)
        cobertura_pct      : fortalezas / (fortalezas + brechas) × 100
        exclusivas_programa: program skills not matched by any market skill
        brechas_criticas   : brechas with frecuencia >= p66 of brecha frequencies
        evidencia_baja     : True when n_matches < 15 (small corpus warning)
    """
    transversales: list[dict] = []
    fortalezas: list[dict] = []
    brechas: list[dict] = []
    matched_prog_skills: set[str] = set()

    for m in market_skills:
        if is_transversal(m["skill"]):
            transversales.append({
                "skill": m["skill"],
                "frecuencia_mercado": m["frecuencia"],
            })
            continue

        detail = find_prog_match(m["skill"], prog_skills)
        prog_cobertura = next(
            (p["cobertura"] for p in prog_skills if p["skill"] == detail.prog_skill), 0
        ) if detail.prog_skill else 0

        if detail.rule != "ninguna":
            fortalezas.append({
                "skill": m["skill"],
                "frecuencia_mercado": m["frecuencia"],
                "cobertura_programa": prog_cobertura,
                "prog_skill_match": detail.prog_skill,
                "regla": detail.rule,
            })
            matched_prog_skills.add(detail.prog_skill)
        else:
            brechas.append({
                "skill": m["skill"],
                "frecuencia_mercado": m["frecuencia"],
            })

    total_non_transversal = len(fortalezas) + len(brechas)
    cobertura_pct = (
        round(len(fortalezas) / total_non_transversal * 100, 1)
        if total_non_transversal else 0.0
    )

    exclusivas_programa = [
        {"skill": s["skill"], "cobertura": s["cobertura"]}
        for s in prog_skills
        if s["skill"] not in matched_prog_skills
    ]

    brechas_criticas = compute_brechas_criticas(brechas)

    return {
        "fortalezas": fortalezas,
        "brechas": brechas,
        "transversales": transversales,
        "cobertura_pct": cobertura_pct,
        "exclusivas_programa": exclusivas_programa,
        "brechas_criticas": brechas_criticas,
        "evidencia_baja": n_matches < 15,
    }


def build_matriz_completa(
    market_skills: list[dict],
    prog_skills: list[dict],
    fortaleza_norms: set[str],
    transversal_norms: set[str],
) -> list[dict]:
    """
    Build the union matrix of market + program skills.

    Each entry carries a 'tipo' tag:
        fortaleza     : market skill covered by curriculum
        brecha        : market skill NOT covered (and not transversal)
        transversal   : generic skill excluded from cobertura_pct
        solo_programa : program skill with no market demand (demanda_mercado = 0)

    'solo_programa' entries are explicitly excluded from "competencias analizadas"
    in the frontend (demanda_mercado == 0 guard).
    """
    matriz: dict[str, dict] = {}

    for m in market_skills:
        key = norm(m["skill"])
        if key in transversal_norms:
            tipo = "transversal"
        elif key in fortaleza_norms:
            tipo = "fortaleza"
        else:
            tipo = "brecha"
        matriz[key] = {
            "skill": m["skill"],
            "demanda_mercado": m["frecuencia"],
            "oferta_programa": 0,
            "tipo": tipo,
        }

    for p in prog_skills:
        # Find a market entry that this prog skill covers
        matched_key = next(
            (k for k in matriz if phrase_covers(matriz[k]["skill"], p["skill"])),
            None,
        )
        if matched_key:
            matriz[matched_key]["oferta_programa"] = p["cobertura"]
        else:
            key = norm(p["skill"])
            if key not in matriz:
                matriz[key] = {
                    "skill": p["skill"],
                    "demanda_mercado": 0,
                    "oferta_programa": p["cobertura"],
                    "tipo": "solo_programa",
                }

    return sorted(matriz.values(), key=lambda x: -x["demanda_mercado"])
