from __future__ import annotations

import re

from backend.services.normalization_service import basic_text_key


def normalize_tokens(text: str) -> set[str]:
    cleaned = re.sub(r"[^a-záéíóúñü0-9\s]", " ", str(text or "").lower())
    return {
        token.strip()
        for token in cleaned.split()
        if token.strip()
        and len(token.strip()) >= 4
        and token.strip() not in {"para", "con", "del", "las", "los", "una", "uno", "esto", "esta", "este", "como", "sobre", "entre"}
    }


def normalize_text_key(text: str) -> str:
    return basic_text_key(text)


def title_affinity_score(program_role: str, title: str) -> float:
    role_key = basic_text_key(program_role)
    title_key = basic_text_key(title)
    if not role_key or not title_key:
        return 0.0
    if role_key == title_key:
        return 100.0
    role_tokens = normalize_tokens(program_role)
    title_tokens = normalize_tokens(title)
    shared_tokens = role_tokens & title_tokens
    if shared_tokens:
        return round((len(shared_tokens) * 100.0) / max(len(role_tokens), 1), 2)
    if role_key in title_key or title_key in role_key:
        return 60.0
    return 0.0


def job_pertinence_score(
    role_score: float,
    skills_en_comun: int,
    total_skills_programa: int,
    total_skills_empleo: int,
) -> tuple[float, float, float]:
    skill_overlap = (skills_en_comun * 100.0 / max(total_skills_programa, 1)) if total_skills_programa else 0.0
    skill_density = (skills_en_comun * 100.0 / max(total_skills_empleo, 1)) if total_skills_empleo else 0.0
    pertinence = round((role_score * 0.55) + (skill_overlap * 0.30) + (skill_density * 0.15), 2)
    return round(role_score, 2), round(skill_overlap, 2), pertinence
