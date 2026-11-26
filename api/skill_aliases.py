"""
Explicit alias map for skill canonicalization in process_job_skill_rows.

Keys are the norm_match() outputs (lowercase, diacritics removed, qualifiers
stripped, English plurals depluralized).  Values are the canonical display form
to use when grouping frequencies across job vacancies.

Do NOT add stemming or broad plural rules here — only explicit, audited pairs.
"""
from __future__ import annotations

# Keys = norm_match(raw_skill); values = canonical display form.
SKILL_ALIASES: dict[str, str] = {
    # Spanish plurals not handled by _depluralize (which only strips consonant+'s').
    "reportes":           "reporte",
    # English plural already handled by norm_match (dashboards → dashboard via
    # _depluralize); explicit entry ensures the display name is "dashboard"
    # rather than the raw "dashboards" when first seen in that form.
    "dashboard":          "dashboard",
    # Role-title vs. function name: "analista de datos" is a job title;
    # "analisis de datos" is the skill domain.  Grouped intentionally.
    "analista de datos":  "analisis de datos",
    # "bases de datos" is NOT unified with "sql" — keep separate (pending decision).
}
