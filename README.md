# Graduate Intelligence Platform

Plataforma de inteligencia curricular, scraping laboral, extraccion de skills y matching programa-empleo sobre PostgreSQL.

## Estado Actual

El repositorio fue consolidado en una estructura monorepo segura. No se eliminaron datasets, modelos, JSONL, outputs ni scripts historicos; los artefactos se clasificaron y movieron a carpetas de trabajo o archivo.

## Arquitectura

```text
backend/          servicios backend nuevos o modulos API
frontend/         frontend React/Vite objetivo
ml/               pipelines de matching, esquemas y entrenamiento ML
scrapers/         scrapers y extractores activos
data/raw/         datasets fuente, SQLite, CSV, JSON, PDFs
data/processed/   datasets curados
data/ml/          JSONL y artefactos de entrenamiento
database/         SQL, vistas, migraciones y esquemas
docs/             diagnosticos, reportes y decisiones tecnicas
scripts/          utilidades operativas y jobs manuales
logs/             logs de ejecucion local
archive/          prototipos, outputs temporales y legacy
tests/            pruebas automatizadas
```

## Entry Points Actuales

- Dashboard principal Flask: `app.py`, servido por Docker como `app:app`.
- Scraper curricular PostgreSQL: `scrapers/scraper.py` con wrapper compatible `scraper.py`.
- Scraper UNIR PostgreSQL: `scrapers/scrape_unir_especializaciones_pg.py` con wrapper compatible.
- Extraccion de ofertas y skills: `scrapers/extract_job_offers_and_skills.py`.
- Matching ML/rules: `ml/ml_match_program_jobs.py` con wrapper compatible.
- Esquema ML PostgreSQL: `ml/ml_training_schema.sql`.

## Docker

La configuracion actual mantiene `docker-compose.yml` y `Dockerfile` en raiz para no romper el despliegue existente. En una segunda iteracion conviene separar imagenes:

- `backend-api`: FastAPI/Flask API.
- `worker-scraper`: jobs de scraping.
- `worker-ml`: matching, export JSONL, scoring.
- `frontend`: React/Vite estatico.
- `db`: PostgreSQL 16.

## Desarrollo

```powershell
python -m pip install -r requirements.txt
docker compose up --build
```

## Reportes

Ver [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md) para el mapa, diagnostico, riesgos, plan de limpieza y estrategia de produccion.
