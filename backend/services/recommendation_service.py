from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.services.normalization_service import basic_text_key, safe_float


ProgramSkillsGetter = Callable[[int], list[dict[str, Any]]]
SkillKeyFunc = Callable[[str], str]
RoleCandidatesFunc = Callable[[dict[str, Any], int], list[str]]


def text_hits(haystack: str, labels: list[str]) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for label in labels:
        normalized = basic_text_key(label)
        if not normalized:
            continue
        matched = normalized in haystack
        if not matched:
            tokens = [token for token in normalized.split() if len(token) >= 5]
            if tokens:
                matched = sum(1 for token in tokens if token in haystack) >= max(1, min(2, len(tokens)))
        if matched and normalized not in seen:
            seen.add(normalized)
            hits.append(label)
    return hits


def recommended_program_cards(
    programas: list[dict[str, Any]],
    selected_program: dict[str, Any],
    area_actual: str,
    user_skills: list[str],
    role_interests: list[str],
    area_interests: list[str],
    goal: str,
    *,
    area_keywords_by_key: dict[str, tuple[str, ...]],
    get_program_skill_rows: ProgramSkillsGetter,
    skill_identity_key: SkillKeyFunc,
    program_role_candidates: RoleCandidatesFunc,
    limit: int = 2,
) -> list[dict[str, Any]]:
    selected_id = int(selected_program.get("especializacion_id", 0) or 0)
    selected_role_labels = program_role_candidates(selected_program, 4)
    selected_role = basic_text_key(str(selected_program.get("rol", "") or ""))
    area_key = basic_text_key(area_actual)
    area_keywords = area_keywords_by_key.get(area_key, ())
    user_skill_keys = {skill_identity_key(label) for label in user_skills if str(label).strip()}
    current_program_skill_keys = {
        skill_identity_key(str(row.get("nombre", "") or ""))
        for row in get_program_skill_rows(selected_id)
        if str(row.get("nombre", "") or "").strip()
    }
    explicit_interest_labels = [label for label in role_interests + area_interests if str(label).strip()]
    if area_actual:
        explicit_interest_labels.append(area_actual)
    if goal:
        explicit_interest_labels.append(goal)
    scored: list[dict[str, Any]] = []

    for program in programas:
        try:
            current_id = int(program.get("especializacion_id", 0) or 0)
        except (TypeError, ValueError):
            continue
        if current_id == selected_id:
            continue
        haystack = basic_text_key(f"{program.get('nombre_especializacion', '')} {program.get('rol', '')}")
        candidate_skill_rows = get_program_skill_rows(current_id)
        candidate_skill_keys = {
            skill_identity_key(str(row.get("nombre", "") or ""))
            for row in candidate_skill_rows
            if str(row.get("nombre", "") or "").strip()
        }
        skill_overlap = sorted(user_skill_keys & candidate_skill_keys)
        base_overlap = sorted(current_program_skill_keys & candidate_skill_keys)
        area_hits = [keyword for keyword in area_keywords if keyword and keyword in haystack]
        role_hits = text_hits(haystack, explicit_interest_labels + selected_role_labels)
        selected_role_hit = bool(selected_role and any(token and len(token) >= 5 and token in haystack for token in selected_role.split()))

        if not skill_overlap and not role_hits and not area_hits and len(base_overlap) < 2 and not selected_role_hit:
            continue

        score = len(skill_overlap) * 34.0
        score += len(role_hits) * 22.0
        score += len(base_overlap) * 8.5
        score += len(area_hits) * 14.0
        score += 6.0 if selected_role_hit else 0.0
        score += min(16.0, safe_float(program.get("promedio_match_mercado", 0)) * 0.12)
        score += min(8.0, safe_float(program.get("total_empleos_relacionados", 0)) * 0.08)

        overlap_labels: list[str] = []
        for row in candidate_skill_rows:
            label = str(row.get("nombre", "") or "").strip()
            if skill_identity_key(label) in skill_overlap and label not in overlap_labels:
                overlap_labels.append(label)

        reason = "Programa complementario cercano a tu perfil actual."
        if overlap_labels:
            reason = f"Comparte skills contigo: {', '.join(overlap_labels[:3])}."
        elif role_hits:
            reason = f"Se acerca a tus intereses en {', '.join(role_hits[:2])}."
        elif area_actual and area_hits:
            reason = f"Puede ampliar tu ruta en {area_actual.lower()}."
        elif len(base_overlap) >= 2:
            reason = "Mantiene cercanía con la base de tu programa de egreso."

        if score < 24.0:
            continue
        scored.append(
            {
                "nombre": program.get("nombre_especializacion", ""),
                "match": round(safe_float(program.get("promedio_match_mercado", 0)), 2),
                "reason": reason,
                "_score": score,
            }
        )

    scored.sort(key=lambda row: (-row["_score"], str(row["nombre"]).casefold()))
    return [{key: value for key, value in row.items() if key != "_score"} for row in scored[:limit]]
