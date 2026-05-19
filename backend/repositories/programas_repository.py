from __future__ import annotations

import re
from typing import Any

from backend.repositories.base import cursor, fetch_all, fetch_one, pick_relation


PROGRAM_NAME_STOPWORDS = {
    "administracion",
    "alta",
    "analitica",
    "ciencias",
    "de",
    "del",
    "direccion",
    "educacion",
    "el",
    "en",
    "especializacion",
    "especialización",
    "gerencia",
    "gestion",
    "la",
    "las",
    "los",
    "maestria",
    "maestría",
    "para",
    "programa",
    "tecnologia",
    "universitaria",
    "y",
}


def _program_search_tokens(program_name: str) -> list[str]:
    tokens = re.findall(r"[a-záéíóúñü0-9]{4,}", program_name.lower())
    return [token for token in tokens if token not in PROGRAM_NAME_STOPWORDS][:5]


def ensure_pg_trgm(*, db_name: str | None = None) -> bool:
    try:
        with cursor(db_name=db_name) as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        return True
    except Exception:
        return False


def resolve_program_id(especializacion_id: int, *, db_name: str | None = None) -> int:
    row = fetch_one(
        """
        WITH skill_counts AS (
            SELECT especializacion_id, COUNT(DISTINCT skill_id)::int AS total_skills_programa
            FROM especializacion_skills
            GROUP BY especializacion_id
        ),
        selected_program AS (
            SELECT lower(nombre) AS nombre_key
            FROM especializaciones
            WHERE id = %s
        )
        SELECT s.id AS especializacion_id
        FROM especializaciones s
        LEFT JOIN skill_counts sc
            ON sc.especializacion_id = s.id
        WHERE lower(s.nombre) = (SELECT nombre_key FROM selected_program)
        ORDER BY
            CASE
                WHEN COALESCE(s.source_url, '') <> '' OR COALESCE(s.plan_estudios, '') <> '' THEN 0
                ELSE 1
            END,
            COALESCE(sc.total_skills_programa, 0) DESC,
            CASE WHEN COALESCE(s.rol, '') <> '' THEN 0 ELSE 1 END,
            CASE WHEN s.nombre ~ '^[A-Z]' THEN 0 ELSE 1 END,
            s.id DESC
        LIMIT 1
        """,
        (especializacion_id,),
        db_name=db_name,
    )
    return int(row.get("especializacion_id", especializacion_id) or especializacion_id) if row else especializacion_id


def fetch_fallback_program_rows(*, db_name: str | None = None) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            id AS especializacion_id,
            nombre AS nombre_especializacion,
            COALESCE(rol, '') AS rol
        FROM especializaciones
        ORDER BY nombre
        """,
        db_name=db_name,
    )


def fetch_program_base_row(especializacion_id: int, *, db_name: str | None = None) -> dict[str, Any] | None:
    return fetch_one(
        """
        WITH programa_skills AS (
            SELECT especializacion_id, COUNT(DISTINCT skill_id)::int AS total_skills_programa
            FROM especializacion_skills
            GROUP BY especializacion_id
        ),
        programa_herramientas AS (
            SELECT especializacion_id, COUNT(DISTINCT herramienta_id)::int AS total_herramientas
            FROM especializacion_herramientas
            GROUP BY especializacion_id
        ),
        programa_competencias AS (
            SELECT especializacion_id, COUNT(DISTINCT competencia_id)::int AS total_competencias
            FROM especializacion_competencias
            GROUP BY especializacion_id
        ),
        programa_habilidades_blandas AS (
            SELECT especializacion_id, COUNT(DISTINCT habilidad_id)::int AS total_habilidades_blandas
            FROM especializacion_habilidades_blandas
            GROUP BY especializacion_id
        )
        SELECT
            s.id AS especializacion_id,
            s.nombre AS nombre_especializacion,
            COALESCE(s.rol, '') AS rol,
            COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
            COALESCE(ph.total_herramientas, 0) AS total_herramientas,
            COALESCE(pc.total_competencias, 0) AS total_competencias,
            COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas,
            0 AS promedio_match_mercado,
            0 AS max_match_mercado,
            0 AS total_empleos_relacionados
        FROM especializaciones s
        LEFT JOIN programa_skills ps ON ps.especializacion_id = s.id
        LEFT JOIN programa_herramientas ph ON ph.especializacion_id = s.id
        LEFT JOIN programa_competencias pc ON pc.especializacion_id = s.id
        LEFT JOIN programa_habilidades_blandas pbl ON pbl.especializacion_id = s.id
        WHERE s.id = %s
        """,
        (especializacion_id,),
        db_name=db_name,
    )


def fetch_program_rows_with_metrics(
    *,
    metrics_relation: str | None,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    if metrics_relation:
        metrics_select = """
            COALESCE(v.promedio_match_mercado, 0) AS promedio_match_mercado,
            COALESCE(v.max_match_mercado, 0) AS max_match_mercado,
            COALESCE(v.total_empleos_relacionados, 0) AS total_empleos_relacionados
        """
        metrics_join = f"LEFT JOIN {metrics_relation} v ON v.especializacion_id = s.id"
    else:
        metrics_select = """
            0 AS promedio_match_mercado,
            0 AS max_match_mercado,
            0 AS total_empleos_relacionados
        """
        metrics_join = ""

    return fetch_all(
        f"""
        WITH programa_skills AS (
            SELECT especializacion_id, COUNT(DISTINCT skill_id)::int AS total_skills_programa
            FROM especializacion_skills
            GROUP BY especializacion_id
        ),
        programa_herramientas AS (
            SELECT especializacion_id, COUNT(DISTINCT herramienta_id)::int AS total_herramientas
            FROM especializacion_herramientas
            GROUP BY especializacion_id
        ),
        programa_competencias AS (
            SELECT especializacion_id, COUNT(DISTINCT competencia_id)::int AS total_competencias
            FROM especializacion_competencias
            GROUP BY especializacion_id
        ),
        programa_habilidades_blandas AS (
            SELECT especializacion_id, COUNT(DISTINCT habilidad_id)::int AS total_habilidades_blandas
            FROM especializacion_habilidades_blandas
            GROUP BY especializacion_id
        )
        SELECT DISTINCT ON (lower(s.nombre))
            s.id AS especializacion_id,
            s.nombre AS nombre_especializacion,
            COALESCE(s.rol, '') AS rol,
            COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
            COALESCE(ph.total_herramientas, 0) AS total_herramientas,
            COALESCE(pc.total_competencias, 0) AS total_competencias,
            COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas,
            {metrics_select}
        FROM especializaciones s
        LEFT JOIN programa_skills ps ON ps.especializacion_id = s.id
        LEFT JOIN programa_herramientas ph ON ph.especializacion_id = s.id
        LEFT JOIN programa_competencias pc ON pc.especializacion_id = s.id
        LEFT JOIN programa_habilidades_blandas pbl ON pbl.especializacion_id = s.id
        {metrics_join}
        ORDER BY
            lower(s.nombre),
            CASE
                WHEN COALESCE(s.source_url, '') <> '' OR COALESCE(s.plan_estudios, '') <> '' THEN 0
                ELSE 1
            END,
            COALESCE(ps.total_skills_programa, 0) DESC,
            CASE WHEN COALESCE(s.rol, '') <> '' THEN 0 ELSE 1 END,
            CASE WHEN s.nombre ~ '^[A-Z]' THEN 0 ELSE 1 END,
            s.id DESC
        """,
        db_name=db_name,
    )


def fetch_program_skill_rows(especializacion_id: int, *, db_name: str | None = None) -> list[dict[str, Any]]:
    relation = pick_relation(("vw_programa_skills",), db_name=db_name)
    if relation:
        rows = []
        for row in fetch_all(f"SELECT * FROM {relation}", db_name=db_name):
            if int(row.get("especializacion_id") or row.get("id") or row.get("programa_id") or 0) == especializacion_id:
                rows.append(row)
        if rows:
            return rows

    return fetch_all(
        """
        SELECT DISTINCT
            s.id AS skill_id,
            s.nombre AS nombre
        FROM especializacion_skills es
        JOIN skills s
            ON s.id = es.skill_id
        WHERE es.especializacion_id = %s
        ORDER BY s.nombre
        """,
        (especializacion_id,),
        db_name=db_name,
    )


def fetch_related_virtual_programs(
    program_name: str,
    *,
    limit: int = 10,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    if not program_name:
        return []

    relation = pick_relation(("public.mineducacion_programas_virtuales", "mineducacion_programas_virtuales"), db_name=db_name)
    if not relation:
        return []

    pg_trgm_enabled = ensure_pg_trgm(db_name=db_name)
    tokens = _program_search_tokens(program_name)
    token_where = ""
    token_params: list[Any] = []
    token_score_expr = "0"
    if tokens:
        token_where = " OR " + " OR ".join(["lower(nombre_programa) LIKE %s" for _ in tokens])
        token_params = [f"%{token}%" for token in tokens]
        token_score_expr = " + ".join(["CASE WHEN lower(nombre_programa) LIKE %s THEN 0.05 ELSE 0 END" for _ in tokens])

    competitor_case = """
        CASE
            WHEN lower(nombre_ies) LIKE '%%unad%%' OR lower(nombre_ies) LIKE '%%nacional abierta y a distancia%%' THEN 'UNAD'
            WHEN lower(nombre_ies) LIKE '%%asturias%%' THEN 'Asturias'
            WHEN lower(nombre_ies) LIKE '%%oberta%%' OR lower(nombre_ies) LIKE '%%catalunya%%' THEN 'UOC'
            WHEN lower(nombre_ies) LIKE '%%iberoamericana%%' THEN 'Iberoamericana'
            WHEN lower(nombre_ies) LIKE '%%politecnico grancolombiano%%' THEN 'Politécnico Grancolombiano'
            WHEN lower(nombre_ies) LIKE '%%area andina%%' OR lower(nombre_ies) LIKE '%%areandina%%' THEN 'Areandina'
            WHEN lower(nombre_ies) LIKE '%%universidad ean%%' THEN 'EAN'
            WHEN lower(nombre_ies) LIKE '%%catolica del norte%%' THEN 'Católica del Norte'
            ELSE NULL
        END
    """

    if pg_trgm_enabled:
        return fetch_all(
            f"""
            WITH candidates AS (
            SELECT
                {competitor_case} AS competidor,
                nombre_ies AS universidad,
                nombre_programa AS programa,
                COALESCE(municipio, departamento, '') AS ciudad,
                nivel_academico AS nivel,
                modalidad,
                estado_programa,
                duracion,
                creditos,
                ROUND(
                    LEAST(
                        1.0,
                        similarity(lower(nombre_programa), lower(%s)) + ({token_score_expr})
                    )::numeric,
                    4
                ) AS similitud
            FROM {relation}
            WHERE lower(COALESCE(modalidad, '')) = 'virtual'
              AND lower(COALESCE(estado_programa, '')) = 'activo'
              AND ({competitor_case}) IS NOT NULL
              AND (
                    similarity(lower(nombre_programa), lower(%s)) >= 0.12
                    {token_where}
              )
            ),
            ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (PARTITION BY competidor ORDER BY similitud DESC, programa) AS competitor_rank
                FROM candidates
            )
            SELECT
                competidor,
                universidad,
                programa,
                ciudad,
                nivel,
                modalidad,
                estado_programa,
                duracion,
                creditos,
                similitud,
                competitor_rank
            FROM ranked
            WHERE competitor_rank <= 2
            ORDER BY
                similitud DESC,
                competidor,
                programa
            LIMIT %s
            """,
            (
                program_name,
                *token_params,
                program_name,
                *token_params,
                limit,
            ),
            db_name=db_name,
        )

    fallback_where = " OR ".join(["lower(nombre_programa) LIKE %s" for _ in tokens]) or "lower(nombre_programa) LIKE %s"
    fallback_params = token_params or [f"%{program_name.lower()}%"]
    return fetch_all(
        f"""
        SELECT
            {competitor_case} AS competidor,
            nombre_ies AS universidad,
            nombre_programa AS programa,
            COALESCE(municipio, departamento, '') AS ciudad,
            nivel_academico AS nivel,
            modalidad,
            estado_programa,
            duracion,
            creditos,
            0.5::numeric AS similitud
        FROM {relation}
        WHERE lower(COALESCE(modalidad, '')) = 'virtual'
          AND lower(COALESCE(estado_programa, '')) = 'activo'
          AND ({competitor_case}) IS NOT NULL
          AND ({fallback_where})
        ORDER BY nombre_ies, nombre_programa
        LIMIT %s
        """,
        (*fallback_params, limit),
        db_name=db_name,
    )
