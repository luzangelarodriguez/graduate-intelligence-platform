# Project Structure Final

Fecha: 2026-05-25

## Backend Productivo

Backend oficial:

`graduate_intelligence_platform/backend/app/main.py`

Componentes activos:

- `graduate_intelligence_platform/backend/app/api.py`: endpoints FastAPI.
- `graduate_intelligence_platform/backend/app/auth.py`: JWT/auth.
- `backend/repositories/`: acceso PostgreSQL y consultas de dominio.
- `backend/services/`: lógica de dashboard, recomendaciones, alumni y normalización.

## Frontend Productivo

Frontend oficial:

`graduate_intelligence_platform/frontend`

La carpeta raíz `frontend/` fue archivada porque era un placeholder sin app Vite productiva.

## Motores Activos

- `microcurriculum_engine/`: ingesta, parsing, extracción, scoring, recomendaciones y reescritura curricular.
- `microcurriculum_context_engine.py`: indexación contextual por especialización.
- `ml/`: clasificación disciplinar, NER curricular, datasets y modelos.
- `scrapers/`: fuentes, pipelines, normalización, taxonomía, lakehouse y gobernanza.
- `build_labor_program_matches.py`: construcción de matches programa-empleo.
- `diagnose_labor_matching.py`: diagnóstico de matching laboral.

## Base De Datos

Migraciones y schema:

- `database/migrations/002_curricular_core_schema.sql`
- `database/migrations/003_enterprise_labor_intelligence_schema.sql`
- `database/migrations/004_mineducacion_programas_virtuales_schema.sql`
- `database/migrations/005_ml_training_schema.sql`
- `database/migrations/006_microcurriculum_ai_validation_schema.sql`
- `database/migrations/007_curricular_market_compatibility.sql`
- `database/migrations/008_labor_matching_bridge.sql`
- `database/migrations/009_microcurriculum_program_context.sql`

Scripts operativos:

- `apply_railway_migrations.py`
- `sync_to_railway.py`
- `verify_railway_data.py`

## Datos Y Evidencia

- `storage/test_microcurriculos/`: documentos reales de validación/piloto.
- `outputs/`: reportes, matrices y resultados exportados.
- `scrapers/lakehouse/`: snapshots Bronze/Silver/Gold de evidencia laboral.
- `logs/`: logs y capturas de ejecución.

Estos directorios no deben mezclarse con código productivo ni publicarse sin política de retención y anonimización.

## Estructura Recomendable Para La Siguiente Fase

```text
graduate_intelligence_platform/
  backend/
    app/
  frontend/
backend/
  repositories/
  services/
database/
  migrations/
microcurriculum_engine/
ml/
scrapers/
scripts/
tests/
docs/
storage/
outputs/
_archive_cleanup/
```

## Deuda Técnica Que Permanece

- Consolidar scripts raíz en `scripts/`.
- Decidir retiro definitivo de Flask legacy (`app.py`, `templates/`, `static/`).
- Reemplazar dependencias vendorizadas por instalación reproducible.
- Definir política de retención para `outputs/`, `logs/` y lakehouse snapshots.
- Evitar nuevos mocks en frontend salvo que estén marcados como fallback temporal y documentados.

## Validación De Release Local

La estructura posterior a limpieza fue validada con:

- Import del backend oficial FastAPI.
- Compilación de scripts operativos principales.
- Build productivo del frontend React/Vite.
- Suite completa `pytest`.

Resultado: backend importable, frontend compilable y tests verdes.
