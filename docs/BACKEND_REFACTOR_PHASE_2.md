# Backend Refactor Phase 2

Fecha: 2026-05-15

## Objetivo

Extraer logica de negocio pesada desde `app.py` hacia services reutilizables, manteniendo `app.py` como entrypoint Flask funcional y sin mover HTML/CSS embebido.

## Que Se Extrajo

### `backend/services/dashboard_service.py`

Se agregaron funciones de negocio para dashboard:

- `alignment_level`
- `match_band`
- `global_kpis`
- `ml_program_metric_map`
- `list_programs_base`
- `normalize_skill_rows`

`app.py` ahora delega:

- `get_global_kpis`
- `_alignment_level`
- `_match_band`

### `backend/services/scoring_service.py`

Se consolido logica reusable de scoring:

- `normalize_tokens`
- `normalize_text_key`
- `title_affinity_score`
- `job_pertinence_score`

`app.py` ahora delega:

- `_normalize_tokens`
- `_title_affinity_score`
- parte final de `_job_pertinence_score`

La funcion `_job_role_match_score` permanece en `app.py` porque todavia depende de catalogos y heuristicas definidos alli.

### `backend/services/recommendation_service.py`

Nuevo service para recomendaciones de programas:

- `text_hits`
- `recommended_program_cards`

Se diseno con callbacks para evitar dependencias circulares con `app.py`:

- `get_program_skill_rows`
- `_skill_identity_key`
- `_program_role_candidates`

`app.py` ahora delega:

- `_registration_text_hits`
- `_recommended_program_cards`

### `backend/services/alumni_service.py`

Nuevo service para onboarding/registro de egresados:

- `ensure_mentor_registration_schema`
- `program_lookup`
- `split_name`
- `csv_values`
- `csv_text`
- `skill_priority`
- `diagnostic_copy`
- `priority_step`
- `initial_step`
- `save_mentor_registration`

`app.py` ahora delega:

- `ensure_mentor_registration_schema`
- `_registration_program_lookup`
- `_registration_split_name`
- `_registration_csv_values`
- `_registration_csv_text`
- `_registration_skill_priority`
- `_registration_diagnostic_copy`
- `_registration_priority_step`
- `_registration_initial_step`
- `_save_mentor_registration`

## Que Queda En `app.py`

`app.py` sigue conteniendo:

- Entry point Flask.
- Registro de blueprints API paralelos.
- Rutas Flask legacy:
  - `/`
  - `/dashboard`
  - `/dashboard/programa/<int:especializacion_id>`
  - `/registro`
- HTML/CSS/JS embebido.
- Render final con `render_template_string`.
- Orquestacion del dashboard.
- Funciones de carga del catalogo curado y skill engine.
- Enriquecimiento de empleos sugeridos.
- Brechas y mercado cuando dependen de callbacks internos.
- Recomendaciones de roles, parcialmente por dependencia de constantes locales.

## Compatibilidad Preservada

No se eliminaron rutas ni se cambio el entrypoint.

Rutas verificadas:

- `/`
- `/dashboard`
- `/dashboard/programa/<int:especializacion_id>`
- `/registro`
- `/api/programas`
- `/api/empleos`
- `/api/matches/status`
- `/api/recommendations/health`

## PostgreSQL-First

Se mantiene el comportamiento actual:

- Preferencia por `vw_latest_ml_program_job_matches` cuando existe y tiene filas.
- Fallback a `vw_match_empleo_especializacion_positivo`.
- Fallback adicional por `empleo_skills` y consultas SQL existentes.
- `mentor_registros` sigue siendo creado/actualizado idempotentemente en PostgreSQL.

## Riesgos

- `app.py` aun concentra templates y armado visual completo.
- `recommendation_service` usa callbacks porque parte del dominio sigue en `app.py`.
- `alumni_service.save_mentor_registration` escribe directamente en PostgreSQL; falta repository dedicado para `mentor_registros`.
- El scoring de roles aun depende de `ROLE_KEYWORDS`, `PROGRAM_ROLE_HINTS` y funciones locales.
- No hay pruebas unitarias formales todavia; la verificacion actual es smoke test.

## Proximos Pasos

1. Crear `backend/repositories/alumni_repository.py` para encapsular `mentor_registros`.
2. Extraer `ROLE_KEYWORDS` y `PROGRAM_ROLE_HINTS` a `backend/services/scoring_service.py` o config.
3. Mover `get_brechas`, `get_match` y `get_related_jobs` a services con repositories.
4. Convertir `_build_registration_preview` en service puro que reciba URLs ya resueltas desde Flask.
5. Separar templates sin cambiar comportamiento.

## Plan Para Separar Templates

1. Crear `backend/templates/dashboard/base.html`.
2. Mover `BASE_TEMPLATE` sin modificar markup.
3. Crear partials para:
   - KPIs
   - selector de programa
   - dashboard general
   - dashboard programa
   - registro alumni
4. Cambiar `render_template_string` por `render_template`.
5. Mantener snapshot visual/manual antes de cada extraccion.

## Plan Para Migrar A FastAPI

1. Mantener Flask como `dashboard-legacy`.
2. Crear `backend/app/main.py` FastAPI productivo.
3. Reutilizar services y repositories actuales.
4. Crear schemas Pydantic:
   - Program
   - Skill
   - Job
   - Match
   - KPI
   - AlumniRegistration
5. Migrar primero endpoints API paralelos:
   - `/api/programas`
   - `/api/empleos`
   - `/api/matches/status`
   - `/api/recommendations/health`
6. Conectar React/Vite al API FastAPI.
7. Mantener Flask hasta paridad completa del dashboard.

## Verificacion Ejecutada

```powershell
python -m py_compile app.py backend\services\alumni_service.py backend\services\recommendation_service.py backend\services\dashboard_service.py backend\services\scoring_service.py backend\services\normalization_service.py backend\repositories\base.py
python -c "import app; print(len(app.app.url_map._rules)); print('\n'.join(sorted(str(r) for r in app.app.url_map.iter_rules())))"
python -c "import app; client=app.app.test_client(); r=client.get('/api/recommendations/health'); print(r.status_code); print(r.get_json())"
```

Resultados:

- Compilacion Python: OK.
- Import de `app`: OK.
- Rutas Flask registradas: 9.
- `/api/recommendations/health`: `200 OK`.
