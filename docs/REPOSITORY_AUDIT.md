# Auditoria y Refactoring Enterprise

Fecha: 2026-05-15

## Diagnostico Tecnico

El proyecto combinaba en la raiz dashboard Flask, scrapers, pipelines ML, SQL, logs, bases SQLite, JSON/CSV y multiples prototipos. La consolidacion realizada separa responsabilidades sin eliminar informacion critica.

## Clasificacion Principal

| Categoria | Archivos/carpetas |
| --- | --- |
| CORE | `app.py`, `build_unir_especializaciones_db.py`, `graduate_intelligence_platform/backend/app/engine.py` |
| BACKEND | `app.py`, `backend/db.py`, `backend/queries.py`, `graduate_intelligence_platform/backend/` |
| FRONTEND | `graduate_intelligence_platform/frontend/`, `frontend/`, prototipos HTML archivados |
| SCRAPER | `scrapers/scraper.py`, `scrapers/scrape_unir_especializaciones_pg.py`, `scrapers/extract_job_offers_and_skills.py`, `scrapers/ticjob_scraper.py`, `scrapers/unir_market_scraper.py` |
| ML | `ml/ml_match_program_jobs.py`, `ml/ml_training_schema.sql`, `data/ml/*.jsonl` |
| DATASET | `data/raw/*.csv`, `data/raw/*.json`, `data/raw/*.db`, `data/raw/extract_especializacion/*.pdf` |
| OUTPUT TEMPORAL | `archive/outputs/job_extraction_output*` |
| LEGACY | `archive/legacy/apps/*.py`, `archive/legacy/apps/*.html` |
| LOG | `logs/*` |
| CONFIG | `scrapers/config/*.json`, `.dockerignore`, `docker-compose.yml`, `Dockerfile` |
| DEPLOY | `Dockerfile`, `docker-compose.yml`, `crontab` |

## Componentes Principales Detectados

- Backend principal actual: `app.py`, Flask + PostgreSQL, servido por `gunicorn` en Docker.
- App principal: dashboard Flask `app.py`.
- Pipeline ML principal: `ml/ml_match_program_jobs.py`.
- Scraper principal: `scrapers/scraper.py`; scraper especializado activo: `scrapers/scrape_unir_especializaciones_pg.py`.
- Esquema PostgreSQL principal de ML: `ml/ml_training_schema.sql`.
- Motor curricular reutilizable: `graduate_intelligence_platform/backend/app/engine.py`.

## Duplicados y Redundancias

- Outputs repetidos de extraccion laboral: `job_extraction_output_real_test`, `job_extraction_output_real_test2`, `job_extraction_output_real_final`.
- Variantes publicas/agresivas/browser probe del mismo pipeline: `job_extraction_output_public*`, `job_extraction_output_browser_probe`.
- JSONL duplicado o versionado por puerto: `program_training_profiles.chat.jsonl` y `program_training_profiles_5433.chat.jsonl`.
- Scrapers paralelos por fuente: `ticjob_*`, `unir_market_scraper.py`, `public_jobs_scraper.py`, `extract_job_offers_and_skills.py`.
- Apps paralelas/prototipos: `asturias_bi_app.py`, `curriculum_intelligence_platform.py`, `unir_alumni_alerts_app.py`, `video_creator_app.py`, `main.py`.
- Dependencias vendorizadas: `vendor/`, `selenium_deps/`, `graduate_intelligence_platform/backend/vendor/`, `graduate_intelligence_platform/backend/deps/`.

## Archivos Criticos

- `app.py`
- `Dockerfile`
- `docker-compose.yml`
- `build_unir_especializaciones_db.py`
- `scrapers/scraper.py`
- `scrapers/scrape_unir_especializaciones_pg.py`
- `scrapers/extract_job_offers_and_skills.py`
- `ml/ml_match_program_jobs.py`
- `ml/ml_training_schema.sql`
- `data/ml/*.jsonl`
- `data/raw/extract_especializacion/*.pdf`
- `graduate_intelligence_platform/backend/app/engine.py`
- `graduate_intelligence_platform/frontend/src/App.tsx`

## Archivos a Conservar

- Todo `data/ml/` por contener entrenamiento, matches y JSONL.
- Todo `data/raw/` hasta validar linaje de datos.
- `archive/outputs/` hasta comparar conteos, hashes y calidad de extraccion.
- `archive/legacy/apps/` hasta migrar funcionalidades utiles al backend/frontend principal.
- `vendor/` y `selenium_deps/` temporalmente, aunque no deben vivir versionados a largo plazo.

## Archivos Candidatos a Eliminar con Confirmacion

- `__pycache__/`
- Logs vacios en `logs/`
- Outputs de prueba con CSV de pocos bytes en `archive/outputs/*browser_probe*`, `*public_now*`, `crawl_elempleo_bogota`.
- Dependencias vendorizadas despues de validar `requirements/*.txt`.
- Prototipos legacy que no aporten funcionalidades: `archive/legacy/apps/main.py`, `run_video_creator_5050.py`, `start_preview.py`.

## Riesgos Tecnicos

- El dashboard principal aun esta en un `app.py` grande, con SQL embebido y logica de UI/backend mezclada.
- No hay migraciones formales tipo Alembic; los SQL son scripts sueltos.
- Hay datos generados y datos fuente mezclados historicamente.
- Existen credenciales por defecto para PostgreSQL en scripts y Docker.
- Dependencias vendorizadas complican builds reproducibles.
- Flask y el frontend React/Vite coexisten sin contrato API estable.

## Arquitectura Recomendada

```text
backend/
  app/
    api/
    core/
    db/
    services/
    schemas/
frontend/
  src/
ml/
  pipelines/
  features/
  evaluation/
scrapers/
  sources/
  extractors/
  config/
database/
  migrations/
  views/
data/
  raw/
  processed/
  ml/
scripts/
logs/
archive/
tests/
```

## Plan de Limpieza

1. Validar que Docker sigue levantando el dashboard principal.
2. Ejecutar wrappers: `python scraper.py --help`, `python public_jobs_scraper.py --help`, `python ml_match_program_jobs.py --help`.
3. Comparar hashes y conteos entre outputs repetidos.
4. Promover un solo dataset canonico a `data/processed/`.
5. Migrar SQL a `database/migrations/` y `database/views/`.
6. Separar `app.py` en paquetes backend cuando exista cobertura minima.
7. Eliminar solo con confirmacion los logs vacios, caches y outputs redundantes.

## Estrategia de Produccion

- Backend API: FastAPI con capas `routers`, `services`, `repositories`, `schemas`.
- Base de datos: PostgreSQL con Alembic, backups, indices y vistas materializadas para dashboards.
- Scraping: workers programados, retries, rate limits, trazabilidad por `run_id`.
- ML: registro de datasets, versionado de features, metricas y evaluacion por batch.
- Frontend: React/Vite consumiendo API versionada.
- Deploy: Docker Compose para local; contenedores separados para API, workers y frontend.

## Estrategia IA y ML

- Mantener PostgreSQL como fuente auditable.
- Guardar cada ejecucion ML en tablas `ml_training_runs`, documentos, labels y ejemplos.
- Versionar JSONL en `data/ml/` con metadata de origen.
- Separar reglas actuales (`local_rules_v1`) de futuros modelos entrenados.
- Medir precision de extraccion de skills y calidad de matching antes de automatizar decisiones.
