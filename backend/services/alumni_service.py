from __future__ import annotations

from typing import Any

from backend.repositories.base import cursor
from backend.services.normalization_service import basic_text_key, safe_float


def ensure_mentor_registration_schema(*, db_name: str | None = None) -> None:
    with cursor(db_name=db_name) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mentor_registros (
                id BIGSERIAL PRIMARY KEY,
                nombres TEXT NOT NULL,
                apellidos TEXT NOT NULL,
                email TEXT NOT NULL,
                especializacion_id INTEGER,
                programa_nombre TEXT,
                objetivo_laboral TEXT,
                nivel_experiencia TEXT,
                skills_actuales TEXT,
                ia_nombre TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        alter_statements = [
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS nombre_completo TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS anio_graduacion TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS cargo_actual TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS area_actual TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS anios_experiencia TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS herramientas_dia_dia TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS roles_interes TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS areas_interes TEXT",
            "ALTER TABLE mentor_registros ADD COLUMN IF NOT EXISTS disponibilidad TEXT",
        ]
        for statement in alter_statements:
            cur.execute(statement)
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_mentor_registros_email
            ON mentor_registros (lower(email))
            """
        )


def program_lookup(programas: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for programa in programas:
        try:
            lookup[int(programa.get("especializacion_id", 0) or 0)] = programa
        except (TypeError, ValueError):
            continue
    return lookup


def split_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in str(full_name or "").split() if part.strip()]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    midpoint = max(1, len(parts) // 2)
    return " ".join(parts[:midpoint]), " ".join(parts[midpoint:])


def csv_values(raw: Any) -> list[str]:
    items = [item.strip() for item in str(raw or "").split(",")]
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not item:
            continue
        key = basic_text_key(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def csv_text(raw: Any) -> str:
    return ", ".join(csv_values(raw))


def skill_priority(count: int, top_count: int) -> tuple[str, str]:
    if count >= max(12, int(top_count * 0.72)):
        return "Alta demanda", "high"
    return "Demanda media", "medium"


def diagnostic_copy(match: float, gap_count: int) -> str:
    if match >= 70:
        if gap_count:
            return "Tu perfil tiene una buena alineación con el mercado, pero existen oportunidades claras de mejora."
        return "Tu perfil tiene una alta alineación con el mercado y ya cuenta con una base competitiva."
    if match >= 45:
        return "Tu perfil tiene una alineación media con el mercado y conviene priorizar algunas mejoras puntuales."
    return "Tu perfil todavía tiene una alineación limitada con el mercado y requiere acciones concretas para ganar tracción."


def priority_step(
    goal: str,
    missing_skills: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    programs: list[dict[str, Any]],
) -> dict[str, str]:
    top_gap = missing_skills[0] if missing_skills else None
    top_job = jobs[0] if jobs else None
    top_program = programs[0] if programs else None

    if top_gap and (goal != "Encontrar empleo" or int(top_gap.get("conteo", 0) or 0) >= 10):
        skill_name = str(top_gap.get("nombre", "")).strip()
        count = int(top_gap.get("conteo", 0) or 0)
        return {
            "title": f"Fortalece {skill_name}",
            "summary": f"Esta habilidad aparece en {count} vacantes relacionadas con tu perfil.",
            "impact": "Cerrar esta brecha aumentaría tu acceso a roles más demandados y mejoraría tu competitividad inmediata.",
            "tone": "priority",
        }

    if top_job:
        return {
            "title": f"Explora {top_job.get('titulo', 'las vacantes sugeridas')}",
            "summary": f"Ya tienes un primer rol con match de {round(safe_float(top_job.get('match', 0)), 0):.0f}% para revisar.",
            "impact": "Dar este paso te permite validar rápidamente qué tan cerca estás del mercado real y qué ajustes valen más la pena.",
            "tone": "opportunity",
        }

    if top_program:
        return {
            "title": f"Evalúa {top_program.get('nombre', 'un programa complementario')}",
            "summary": str(top_program.get("reason", "") or "Puede ayudarte a ampliar tu perfil actual."),
            "impact": "Solo vale la pena si respalda el siguiente movimiento profesional que quieres hacer.",
            "tone": "strategy",
        }

    return {
        "title": "Mantén tu perfil actualizado",
        "summary": "Con más señales de experiencia e intereses podremos darte una guía más precisa.",
        "impact": "Un perfil mejor descrito genera mejores matches, alertas y prioridades.",
        "tone": "strategy",
    }


def initial_step(form_data: dict[str, str]) -> int:
    checks = [
        (1, ("nombre_completo", "email", "especializacion_id", "anio_graduacion")),
        (2, ("cargo_actual", "nivel_experiencia", "area_actual", "anios_experiencia")),
        (3, ("skills_actuales", "herramientas_dia_dia")),
        (4, ("roles_interes", "areas_interes")),
        (5, ("objetivo_laboral", "disponibilidad")),
    ]
    for step, fields in checks:
        for field in fields:
            if not str(form_data.get(field, "") or "").strip():
                return step
    return 1


def save_mentor_registration(
    form: dict[str, str],
    programas: list[dict[str, Any]],
    *,
    db_name: str | None = None,
) -> int:
    ensure_mentor_registration_schema(db_name=db_name)
    lookup = program_lookup(programas)
    try:
        especializacion_id = int(str(form.get("especializacion_id") or "").strip())
    except (TypeError, ValueError):
        especializacion_id = None
    programa = lookup.get(especializacion_id or 0, {})
    programa_nombre = str(programa.get("nombre_especializacion", "") or "")
    nombre_completo = (form.get("nombre_completo") or "").strip()
    nombres, apellidos = split_name(nombre_completo)

    with cursor(db_name=db_name) as cur:
        cur.execute(
            """
            INSERT INTO mentor_registros (
                nombres,
                apellidos,
                email,
                especializacion_id,
                programa_nombre,
                objetivo_laboral,
                nivel_experiencia,
                skills_actuales,
                ia_nombre,
                nombre_completo,
                anio_graduacion,
                cargo_actual,
                area_actual,
                anios_experiencia,
                herramientas_dia_dia,
                roles_interes,
                areas_interes,
                disponibilidad
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                nombres,
                apellidos,
                (form.get("email") or "").strip().lower(),
                especializacion_id,
                programa_nombre,
                (form.get("objetivo_laboral") or "").strip(),
                (form.get("nivel_experiencia") or "").strip(),
                csv_text(form.get("skills_actuales")),
                "Alia",
                nombre_completo,
                (form.get("anio_graduacion") or "").strip(),
                (form.get("cargo_actual") or "").strip(),
                (form.get("area_actual") or "").strip(),
                (form.get("anios_experiencia") or "").strip(),
                (form.get("herramientas_dia_dia") or "").strip(),
                csv_text(form.get("roles_interes")),
                csv_text(form.get("areas_interes")),
                (form.get("disponibilidad") or "").strip(),
            ),
        )
        row = cur.fetchone() or {}
        return int(row.get("id") or 0)
