"""Filtros compartidos para excluir filas de prueba de la tabla microcurriculos.

Criterio "fila de prueba":
  1. source_document empieza por letra de unidad + ":" + "\" o "/"
     (rutas Windows/UNC locales, p. ej. C:\\Users\\...)
  2. source_document contiene "test_microcurric" (sin importar mayúsculas,
     backslash o forward-slash antes/después)
  3. asignatura empieza por "PROGRAMA ACAD" (sin importar mayúsculas)

Exporta:
  es_fila_de_prueba(source_document, asignatura) -> bool
  SQL_FILTRO_NO_PRUEBA   : fragmento SQL para usar con alias 'm' de microcurriculos
  SQL_FILTRO_NO_PRUEBA_PARAMS : tupla de parámetros para ese fragmento

Uso en SQL (psycopg2 — el fragmento ya incluye el AND inicial):

    cur.execute(
        f"SELECT ... FROM microcurriculos m WHERE m.specialization_id = %s"
        f"{SQL_FILTRO_NO_PRUEBA}",
        (prog_id,) + SQL_FILTRO_NO_PRUEBA_PARAMS,
    )
"""
from __future__ import annotations

import re

# ── Predicado Python ──────────────────────────────────────────────────────────

_RE_RUTA_LOCAL = re.compile(r"^[A-Za-z]:[/\\]", re.IGNORECASE)
_RE_TEST_DOC   = re.compile(r"test_microcurric", re.IGNORECASE)
_RE_PROG_ACAD  = re.compile(r"^PROGRAMA\s+ACAD", re.IGNORECASE)


def es_fila_de_prueba(source_document: str | None, asignatura: str | None) -> bool:
    """Devuelve True si la fila de microcurriculos es de prueba/sandbox."""
    sd = source_document or ""
    ag = asignatura or ""
    return (
        bool(_RE_RUTA_LOCAL.match(sd))
        or bool(_RE_TEST_DOC.search(sd))
        or bool(_RE_PROG_ACAD.match(ag))
    )


# ── Fragmento SQL equivalente (alias 'm' para microcurriculos) ────────────────
#
# Traducción de cada criterio a SQL (PostgreSQL):
#
#   1. m.source_document ~* '^[A-Za-z]:[/\\]'
#      Regex case-insensitive; \\ se escapa como \\\\ en SQL literal.
#      COALESCE evita NULL.
#
#   2. m.source_document ILIKE '%%test_microcurric%%'
#      ILIKE es case-insensitive. Los % se duplican para psycopg2 (%% → %).
#      Se usa en lugar de ~* para evitar falsos positivos por metacaracteres.
#
#   3. m.asignatura ILIKE 'PROGRAMA ACAD%%'
#
# La condición compuesta es NOT (1 OR 2 OR 3).

SQL_FILTRO_NO_PRUEBA = """
      AND NOT (
            COALESCE(m.source_document, '') ~* '^[A-Za-z]:[/\\\\]'
         OR COALESCE(m.source_document, '') ILIKE '%%test_microcurric%%'
         OR COALESCE(m.asignatura,      '') ILIKE 'PROGRAMA ACAD%%'
      )"""

# El fragmento no tiene parámetros variables: se expande directamente en f-string.
# Se expone como constante vacía para que el caller no necesite condicionar nada.
SQL_FILTRO_NO_PRUEBA_PARAMS: tuple[()] = ()
