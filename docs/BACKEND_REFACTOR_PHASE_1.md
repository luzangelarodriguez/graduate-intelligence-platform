# Backend Refactor Phase 1

Fecha: 2026-05-15

## Objetivo

Iniciar la separacion enterprise de `app.py` sin romper compatibilidad Flask ni las rutas actuales del dashboard.

## Nuevo Mapa Backend

```text
backend/
  db.py
  repositories/
    base.py
    programas_repository.py
    empleos_repository.py
    matches_repository.py
    skills_repository.py
  services/
    normalization_service.py
    scoring_service.py
    dashboard_service.py
  routes/
    programas.py
    empleos.py
    matches.py
    recommendations.py
    dashboard.py
```

## App Flask Actual

`app.py` se mantiene como entrypoint principal y conserva las rutas legacy:

- `/`
- `/dashboard`
- `/dashboard/programa/<int:especializacion_id>`
- `/registro`

Se agregaron rutas API paralelas, sin eliminar ni cambiar las rutas existentes:

- `/api/programas`
- `/api/empleos`
- `/api/matches/status`
- `/api/recommendations/health`

## Repositories Creados

### `backend/repositories/base.py`

- `cursor`
- `fetch_all`
- `fetch_one`
- `relation_exists`
- `pick_relation`
- `relation_has_rows`

Responsabilidad: acceso PostgreSQL comun, deteccion de vistas/tablas y fetches base.

### `backend/repositories/programas_repository.py`

- Resolucion canonica de `especializacion_id`.
- Consulta de programas base.
- Consulta de programas con metricas.
- Consulta de skills curriculares por programa.

Dominio: `especializaciones`, relaciones curriculares y vistas dashboard.

### `backend/repositories/empleos_repository.py`

- Metadata de empleos.
- Listado basico de empleos.
- Empleos preparados para scoring.

Dominio: `empleos`.

### `backend/repositories/matches_repository.py`

- Deteccion de la relacion oficial de matching.
- Lectura de metricas ML.
- Lectura de matches por programa.
- Conteo de empleos relacionados.

Dominio: `vw_latest_ml_program_job_matches`, `vw_match_empleo_especializacion_positivo`.

### `backend/repositories/skills_repository.py`

- Skills por empleo.
- Conteo de skills de mercado.
- Top skills de mercado desde relacion de matching.

Dominio: `skills`, `empleo_skills`.

## Services Creados

### `backend/services/normalization_service.py`

- Normalizacion de texto.
- `row_value`.
- `safe_float`.
- Normalizacion de filas de programa y skill.

Este service ya es usado por `app.py`.

### `backend/services/scoring_service.py`

- Tokenizacion reusable.
- Afinidad de titulo/rol.
- Calculo base de pertinencia empleo-programa.

Todavia no sustituye todo el scoring legacy; queda preparado para migracion gradual.

### `backend/services/dashboard_service.py`

- KPIs globales.
- Mapa de metricas ML por programa.
- Listado base de programas.
- Normalizacion de skills.

Queda preparado para alimentar FastAPI y reemplazar gradualmente funciones de `app.py`.

## Routes Creadas

### `backend/routes/programas.py`

`GET /api/programas`

### `backend/routes/empleos.py`

`GET /api/empleos`

### `backend/routes/matches.py`

`GET /api/matches/status`

### `backend/routes/recommendations.py`

`GET /api/recommendations/health`

### `backend/routes/dashboard.py`

Blueprint preparado para futura separacion del dashboard Flask. No se registra aun para evitar colision con `/dashboard`.

## Cambios Aplicados En `app.py`

`app.py` ahora delega:

- Conexion y cursores a `backend.repositories.base`.
- Fetches SQL genericos a `backend.repositories.base`.
- Deteccion de tablas/vistas a `backend.repositories.base`.
- Resolucion canonica de programa a `backend.repositories.programas_repository`.
- Deteccion de vista oficial de matching a `backend.repositories.matches_repository`.
- Normalizacion de texto/filas/float a `backend.services.normalization_service`.

## Dependencias Detectadas

- `app.py` sigue dependiendo de `build_unir_especializaciones_db.py` para mapas curados.
- `app.py` carga `graduate_intelligence_platform/backend/app/engine.py` para catalogo de skills.
- Los queries de dashboard dependen de:
  - `especializaciones`
  - `skills`
  - `especializacion_skills`
  - `empleos`
  - `empleo_skills`
  - `vw_dashboard_especializacion` o `mv_dashboard_especializacion`
  - `vw_latest_ml_program_job_matches` o `vw_match_empleo_especializacion_positivo`
- Las rutas API nuevas dependen de PostgreSQL cuando se invocan.

## Riesgos Encontrados

- `app.py` sigue conteniendo HTML/CSS/JS inline, registro, scoring y armado de dashboard.
- Hay SQL dinamico con nombres de vistas interpolados; por ahora se limita a relaciones internas detectadas por repository.
- La ruta `/registro` sigue escribiendo directamente en `mentor_registros`.
- `dashboard_service.list_programs_base` es una interfaz base; no reproduce todavia todos los enriquecimientos de `app.py`.
- El dashboard Flask todavia es la fuente funcional completa; las APIs nuevas son superficie de transicion.

## Plan De Transicion FastAPI

1. Crear `backend/app/main.py` FastAPI productivo.
2. Mover config/env/logging a `backend/app/core`.
3. Convertir repositories a dependencias inyectables.
4. Crear schemas Pydantic para Program, Skill, Job, Match, KPI y MentorRegistration.
5. Migrar endpoints API desde blueprints Flask a routers FastAPI.
6. Conectar React/Vite a endpoints FastAPI.
7. Mantener `app.py` como `dashboard-legacy` hasta paridad funcional.
8. Eliminar Flask legacy solo despues de pruebas de paridad.

## Recomendaciones Produccion

- Introducir pool de conexiones (`psycopg_pool` o SQLAlchemy Core).
- Mover SQL largo a archivos versionados o query builders controlados.
- Crear tests de contrato para cada repository.
- Hacer idempotentes los jobs que actualizan vistas y tablas.
- Separar Docker en `api`, `dashboard-legacy`, `worker-scraper`, `worker-ml`, `frontend`, `db`.
- No registrar endpoints experimentales sin auth cuando se exponga SaaS publicamente.

## Verificacion

Comandos ejecutados:

```powershell
python -m py_compile app.py backend\repositories\*.py backend\services\*.py backend\routes\*.py
python -c "import app; print(len(app.app.url_map._rules)); print('\n'.join(sorted(str(r) for r in app.app.url_map.iter_rules())))"
```

Resultado:

- Compilacion Python: OK.
- Flask importa correctamente: OK.
- Rutas registradas: 9.
