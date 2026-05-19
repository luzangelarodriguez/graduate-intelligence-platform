# FastAPI Migration Phase 1

## Objetivo

Convertir el prototipo FastAPI en una API oficial PostgreSQL-first que coexiste con Flask sin romper dashboard, scrapers, pipeline ML ni templates actuales.

## Cambios realizados

- `graduate_intelligence_platform/backend/app/main.py` ya no inicializa `InMemoryStore`.
- Se agrego `graduate_intelligence_platform/backend/app/api.py` con rutas productivas.
- Se agrego `graduate_intelligence_platform/backend/app/schemas.py` con modelos basicos de request/response.
- FastAPI ahora consume `backend.repositories` y `backend.services`.
- Se agrego CORS configurable por `CORS_ORIGINS`.
- Se preparo ejecucion uvicorn por variables `FASTAPI_HOST`, `FASTAPI_PORT` y `FASTAPI_RELOAD`.
- `requirements/backend.txt` incluye `fastapi` y `uvicorn`.
- `requirements/dev.txt` incluye `httpx` para habilitar `fastapi.testclient.TestClient`.

## Endpoints creados

```text
GET  /api/health
GET  /api/bootstrap
GET  /api/programas
GET  /api/programas/{program_id}
GET  /api/empleos
GET  /api/empleos/{empleo_id}
GET  /api/matches
GET  /api/matches/programa/{program_id}
GET  /api/dashboard/kpis
POST /api/alumni/register
GET  /api/recommendations/programs
GET  /api/recommendations/jobs
```

## Que consume PostgreSQL real

- Programas: `dashboard_service.list_programs_base`, `programas_repository`.
- KPIs: `dashboard_service.global_kpis`.
- Empleos: `empleos_repository`, `skills_repository`.
- Matches: `matches_repository`, priorizando `vw_latest_ml_program_job_matches`.
- Alumni: `alumni_service.save_mentor_registration`, tabla `mentor_registros`.
- Recomendaciones: `recommendation_service` y matches reales por programa.

## Que sigue en Flask

- Dashboard HTML actual.
- Templates Jinja desacoplados.
- Render de `/`, `/dashboard`, `/dashboard/programa/<id>` y `/registro`.
- Componentes visuales que aun se arman como HTML dinamico desde Python.

## Estrategia de coexistencia

- Flask permanece como legacy UI estable.
- FastAPI queda como backend JSON oficial para frontend moderno.
- Ambos usan el mismo `DB_NAME`, default `cliente_a_db`.
- La capa compartida es `backend/repositories` + `backend/services`.

## Plan de migracion React

1. Consumir primero `GET /api/dashboard/kpis`, `GET /api/programas` y `GET /api/matches/programa/{id}`.
2. Migrar KPI cards, tablas y filtros a React/Vite usando respuestas JSON estables.
3. Mantener Flask como fallback visual hasta que React cubra dashboard y registro.
4. Promover FastAPI a backend unico cuando las rutas UI dependan solo de APIs.

## Riesgos tecnicos

- `engine.py` conserva el prototipo in-memory como legado, pero ya no es usado por `main.py`.
- Algunas recomendaciones siguen dependiendo de contratos de datos heredados del dashboard.
- `POST /api/alumni/register` escribe en PostgreSQL; las pruebas automaticas deben usar una base temporal o rollback.
- El entorno local no tenia `httpx`; por eso `TestClient` requiere instalar dependencias de desarrollo.

## Verificacion realizada

- Compilacion Python de `main.py`, `api.py` y `schemas.py`.
- Import de FastAPI OK.
- Listado de endpoints oficiales OK.
- Health contra PostgreSQL OK, base `cliente_a_db`.
- Handlers directos OK para programas, KPIs, empleos y matches.

## Comando uvicorn recomendado

```powershell
uvicorn graduate_intelligence_platform.backend.app.main:app --host 0.0.0.0 --port 8000
```
