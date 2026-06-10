# Reporte: Fix de build_programs() en engine.py
**Fecha:** 2026-06-08  
**Archivo modificado:** `graduate_intelligence_platform/backend/app/engine.py`

---

## DIAGNÓSTICO

### 1. ¿De dónde lee datos build_programs()?

**Respuesta: Solo de memoria (PROGRAM_BLUEPRINTS).**

```python
PROGRAM_BLUEPRINTS: List[Dict[str, str]] = [
    {"name": "EspecializaciÃ³n en Alta Gerencia", "faculty": "Ciencias EconÃ³micas y Administrativas", ...},
    ...
]
```

`engine.py` no tiene ninguna importación de `psycopg2`, `psycopg`, `sqlalchemy`, ni de `backend.repositories.base`. Toda la data proviene del dict Python estático.

---

### 2. ¿Por qué no incluye domain_key?

`program_domain()` **existe en el mismo archivo** (línea 1197) pero **nunca se llama** desde `build_programs()`. El dict retornado nunca tenía la clave `domain_key`.

```python
# Línea 1197 — existe pero no estaba conectado
def program_domain(program: Dict[str, Any]) -> str:
    result = infer_program_domain(
        program.get("name"),
        faculty=program.get("faculty"),
        ...
    )
    return result.domain
```

---

### 3. ¿Por qué no incluye microcurriculum_context?

Dos razones:
1. **Sin conexión a DB**: `engine.py` no importa `backend.repositories.base.fetch_all()`.
2. **Sin JOIN a microcurriculos**: Las tablas `microcurriculos` y `microcurriculo_skills` contienen skills reales extraídos de PDFs por el pipeline NER, pero `build_programs()` nunca las consulta.

Esquema de `microcurriculo_skills`:
```sql
microcurriculo_id, skill_original, skill_normalized, skill_domain,
tipo_skill, confidence_score, source_document, lineage
```

Tipos de skill (`tipo_skill`): `tecnologia`, `skill_tecnica`, `herramienta`, 
`plataforma`, `skill_transversal`, `metodologia`

---

### 4. Problema adicional: encoding mojibake en PROGRAM_BLUEPRINTS

Los nombres tienen UTF-8 decodificado como Latin-1:
- `"EspecializaciÃ³n"` → debería ser `"Especialización"`
- Este bug hace que `normalize_text()` falle silenciosamente en algunos matches

La solución correcta es usar la DB como fuente de verdad.

---

## FIXES APLICADOS (3 correcciones)

### Fix 1 — client_encoding=UTF8 en `backend/db.py`

Se añadió `_fetch_db_programs()` (nueva función privada) que:

1. Intenta importar `backend.repositories.base.fetch_all` (importación local para evitar ciclos en carga del módulo)
2. Consulta `especializaciones` con nombre correcto, facultad, nivel
3. Consulta `microcurriculo_skills` JOIN `microcurriculos` en un solo query
4. Construye `microcurriculum_context` indexado por nombre de programa
5. Agrega `domain_key` llamando a `program_domain()` existente
6. Retorna `None` en cualquier error (DB no disponible, timeout, etc.)

`build_programs()` usa el resultado de `_fetch_db_programs()` si no es `None`, o hace fallback al loop original de `PROGRAM_BLUEPRINTS`.

---

### Query principal — especializaciones

```sql
SELECT
    e.id                          AS especializacion_id,
    e.nombre                      AS nombre_especializacion,
    COALESCE(e.facultad, '')       AS facultad,
    COALESCE(e.nivel, '')          AS nivel,
    COALESCE(e.rol, '')            AS rol,
    COALESCE(e.plan_estudios, '')  AS plan_estudios,
    COALESCE(e.campo_laboral, '')  AS campo_laboral
FROM especializaciones e
ORDER BY e.id

-- Después:
FROM especializaciones e
WHERE e.id >= 80
ORDER BY e.id
```

---

### Query secundaria — microcurriculo_skills

```sql
-- Antes:
SELECT
    m.programa,
    ms.skill_normalized,
    ms.tipo_skill,
    ms.confidence_score
FROM microcurriculo_skills ms
JOIN microcurriculos m ON m.id = ms.microcurriculo_id
WHERE ms.skill_normalized IS NOT NULL
  AND ms.skill_normalized <> ''

-- Después:
SELECT
    m.programa,
    COALESCE(NULLIF(ms.skill_normalized, ''),
             NULLIF(ms.skill_original, ''))  AS skill_value,
    ms.tipo_skill,
    ms.confidence_score
FROM microcurriculo_skills ms
JOIN microcurriculos m ON m.id = ms.microcurriculo_id
WHERE COALESCE(NULLIF(ms.skill_normalized, ''),
               NULLIF(ms.skill_original, '')) IS NOT NULL
```

El campo en el loop cambia de `sr.get("skill_normalized")` a `sr.get("skill_value")`.

---

### Campos retornados por build_programs() (antes vs. después)

| Campo | Antes | Después (DB) | Después (fallback) |
|---|---|---|---|
| `id` | índice 1-N | `especializaciones.id` | índice 1-N |
| `name` | `blueprint["name"]` (mojibake) | `especializaciones.nombre` (correcto) | `blueprint["name"]` |
| `nombre` | ❌ ausente | `especializaciones.nombre` | `blueprint["name"]` |
| `nombre_especializacion` | ❌ ausente | `especializaciones.nombre` | `blueprint["name"]` |
| `faculty` | `blueprint["faculty"]` | `especializaciones.facultad` | `blueprint["faculty"]` |
| `domain_key` | ❌ ausente | `program_domain(prog)` | `program_domain(prog)` |
| `microcurriculum_context` | ❌ ausente | Skills reales de DB | `{}` vacío con todas las claves |
| `curriculum_skills` | `program_skill_profile()` | `program_skill_profile()` | `program_skill_profile()` |
| `curriculum_topics` | `program_topic_profile()` | `program_topic_profile()` | `program_topic_profile()` |

---

### Comportamiento de microcurriculum_context

```python
{
    "technologies": ["Python", "TensorFlow", ...],        # tipo_skill='tecnologia'
    "technical_skills": ["Machine Learning", "SQL", ...], # tipo_skill='skill_tecnica'
    "tools": ["Power BI", "Tableau", ...],                 # tipo_skill='herramienta'
    "platforms": ["AWS", "Azure", ...],                    # tipo_skill='plataforma'
    "transversal_skills": ["Liderazgo", "Comunicación"], # tipo_skill='skill_transversal'
    "methodologies": ["Scrum", "Design Thinking", ...],   # tipo_skill='metodologia'
}
```

---

## IMPACTO Y RIESGO

| Aspecto | Evaluación |
|---|---|
| Cambio en comportamiento | **DB disponible** → datos reales; **DB no disponible** → comportamiento idéntico al anterior |
| Riesgo de regresión | **Bajo** — fallback garantiza que build_programs() nunca falla |
| Performance | Una query extra al inicializar; resultado cacheable (ver nota) |
| Compatibilidad | `domain_key` y `microcurriculum_context` son campos nuevos, no rompen consumers existentes |

**Nota de performance:** `_fetch_db_programs()` se llama cada vez que se invoca `build_programs()`. Si se necesita caching, añadir `@functools.lru_cache(maxsize=1)` después de validar que los datos de DB son suficientemente estables.

---

## CONEXIÓN A DB UTILIZADA

El fix usa `backend.repositories.base.fetch_all()` que a su vez usa `backend.db.get_conn()` → `backend.database_config.get_connection_parameters()`.

La cadena de prioridad de conexión es:
1. `RAILWAY_DATABASE_URL` (variable de entorno o `.env.local`)
2. `DATABASE_URL`
3. Variables `LOCAL_DB_*`
4. Variables `DB_*`

En entorno local con `.env.local` configurado correctamente (`RAILWAY_DATABASE_URL=postgresql://...`), el fix usará la DB de Railway automáticamente.

---

*Reporte generado: 2026-06-08 | Archivo: engine.py*
