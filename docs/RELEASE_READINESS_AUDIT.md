# Release Readiness Audit

## Staging Decision

Backend productivo oficial:

`graduate_intelligence_platform/backend/app/main.py`

Este entrypoint importa correctamente como `Graduate Intelligence Platform API` y concentra FastAPI, CORS, auth router, API router, security headers, trusted hosts, gzip y rate limiting.

Frontend productivo actual:

`graduate_intelligence_platform/frontend`

Esta carpeta contiene una app Vite/React valida con `package.json`, scripts `dev`, `build`, `preview`, Tailwind, Vite config y assets. La carpeta raiz `frontend/` solo contiene `README.md` y `package-lock.json`; se considera placeholder/no productiva para staging.

## Modulos Activos

- `backend/`: repositories, services y conexion PostgreSQL compartida.
- `graduate_intelligence_platform/backend/app/`: FastAPI productivo, auth, settings, middleware y API routes.
- `graduate_intelligence_platform/frontend/`: React/Vite productivo.
- `ml/`: clasificador disciplinar, embeddings, entrenamiento, evaluacion e inferencia.
- `microcurriculum_engine/`: motor de ingesta, parsing, matching, gaps, recomendaciones y embeddings de microcurriculos.
- `scrapers/pipelines/`: pipelines laborales, Gold, discovery, governance y validacion.
- `scrapers/sources/`: adaptadores Playwright por fuente.
- `database/`: schema enterprise PostgreSQL.
- `tests/`: hardening backend, data quality, ML, scrapers y microcurriculos.

## Legacy y Coexistencia

- `app.py`: Flask legacy fallback; no se mueve en esta fase.
- `templates/` y `static/`: presentation layer Flask legacy.
- Wrappers raiz movidos a `archive/legacy_root_scripts/`: scripts de compatibilidad que redirigen a implementaciones bajo `scrapers/`.
- `vendor/`, `selenium_deps/`, `graduate_intelligence_platform/backend/deps/`, `graduate_intelligence_platform/backend/vendor/`: dependencias vendorizadas, no aptas para GitHub/staging limpio.
- `outputs/`, `storage/microcurriculos/*.pdf`, `storage/microcurriculos/*.txt`, `data/raw/`, `archive/outputs/`: datos, documentos institucionales y artefactos generados.
- `estructura.txt` y `estructura_proyecto.csv`: inventarios generados de gran tamano; candidatos a archivar o regenerar bajo demanda.

## Riesgos

- `.env.development` y `.env.production` existen en el workspace. Quedan ignorados para commits futuros, pero si ya estan trackeados se debe revisar con `git ls-files` antes de publicar.
- El backend Flask legacy y FastAPI conviven; staging debe apuntar solo a FastAPI.
- Dependencias vendorizadas aumentan tamano y riesgo de publicar paquetes de terceros.
- Hay outputs y documentos reales generados localmente; no deben ir a GitHub.
- Algunas implementaciones legacy dentro de `scrapers/` siguen importandose entre si; no deben moverse sin una fase especifica de consolidacion.

## Candidatos A Mover O Eliminar Mas Adelante

No eliminar automaticamente.

- `app.py`, `templates/`, `static/`: mantener como legacy hasta retirar Flask.
- `frontend/`: placeholder raiz; eliminar o archivar cuando se confirme que nadie lo usa.
- `vendor/`, `selenium_deps/`, `graduate_intelligence_platform/backend/deps/`, `graduate_intelligence_platform/backend/vendor/`: reemplazar por instalacion desde requirements o build reproducible.
- `estructura.txt`, `estructura_proyecto.csv`: mover a `archive/reports/` o regenerar bajo demanda.
- `outputs/`: artefactos locales; limpiar antes de release.
- `logs/screenshots/*.png`: evidencia runtime local; no incluir en release.

## Wrappers Legacy Movidos

Se verifico con `rg` que no son importados por `backend`, `graduate_intelligence_platform`, `scrapers`, `ml` ni `microcurriculum_engine` como modulos productivos. Las implementaciones reales bajo `scrapers/` permanecen intactas.

- `extract_job_offers_and_skills.py`
- `linkedin_access_check.py`
- `linkedin_jobs_api.py`
- `linkedin_sync.py`
- `public_jobs_scraper.py`
- `scrape_unir_especializaciones_pg.py`
- `structured_job_html_extractor.py`
- `ticjob_bi_skills_job.py`
- `ticjob_deep_bi_scraper.py`
- `ticjob_scraper.py`
- `unir_market_scraper.py`

## Comandos Staging

- Ejecucion local: `.\run_local.ps1`
- Validacion release: `.\validate_release.ps1`
- Backend import check: `python -c "from graduate_intelligence_platform.backend.app.main import app; print(app.title)"`
