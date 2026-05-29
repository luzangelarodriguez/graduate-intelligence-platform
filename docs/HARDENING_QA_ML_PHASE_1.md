# Hardening QA/ML Phase 1

## Objetivo

Crear una capa automatica de validacion antes de staging institucional para backend, calidad de datos, taxonomia, matching disciplinar, scraping lakehouse y release gates.

## Estructura creada

```text
tests/
  backend/
  data_quality/
  ml/
  scrapers/
  frontend_optional/
```

Comando unico:

```powershell
python -m pytest tests
```

## Pruebas backend

Archivo:

`tests/backend/test_api_endpoints.py`

Cobertura:

- `GET /api/health`
- `GET /api/programas`
- `GET /api/dashboard/kpis`
- `GET /api/matches`
- `GET /api/recommendations/programs`
- `GET /api/recommendations/jobs`

Las pruebas protegidas requieren:

- `TEST_API_BASE_URL`, por defecto `http://127.0.0.1:8010`
- `TEST_ACCESS_TOKEN` para endpoints con JWT

Si no hay token, esas pruebas se saltan explicitamente. Esto evita crear usuarios o modificar datos productivos.

## Pruebas de calidad de datos

Archivo:

`tests/data_quality/test_program_skill_coherence.py`

Validaciones:

- Alta Gerencia rechaza contaminacion TI/ciberseguridad: `backend`, `sql`, `visual analytics`, `iso 27001`.
- Ambiental/Energia acepta `sostenibilidad`, `ESG`, `ISO 14001` y rechaza `backend`, `fullstack`, `devops`.
- Visual Analytics acepta `SQL`, `Power BI`, `Python`, `Big Data`, `visual analytics`.
- Derecho Digital acepta `proteccion de datos`, `habeas data`, `compliance`, `legaltech`.

## Pruebas ML

Archivo:

`tests/ml/test_taxonomy_matching_pipeline.py`

Validaciones:

- clasificacion disciplinar estable por programa;
- filtrado de dominios incompatibles;
- normalizacion de aliases de skills;
- deduplicacion por empleo repetido;
- score minimo de pertinencia para empleo completo y coherente.

## Pruebas scraping/lakehouse

Archivo:

`tests/scrapers/test_lakehouse_quality_gates.py`

Validaciones:

- Bronze escribe payload raw en lakehouse;
- Silver rechaza paginas SEO/categorias como empleos reales;
- Silver acepta evidencia real de vacante;
- Gold solo publica si supera `min_relevance`;
- release gates bloquean datos contaminados o insuficientemente validados.

## Ajustes de taxonomia

Se agrego `big data` como skill canonica del dominio `analitica`, con aliases:

- `bigdata`
- `datos masivos`
- `procesamiento masivo de datos`

Esto permite que Visual Analytics cumpla la regla de dominio sin contaminar programas no TI.

## Criterios de aceptacion

- `python -m pytest tests` debe ejecutar sin fallos criticos.
- Las pruebas backend protegidas pueden aparecer como `skipped` si no existe `TEST_ACCESS_TOKEN`.
- Ninguna prueba debe tocar Railway ni datos productivos.
- Ninguna prueba debe conectar scraping nuevo al dashboard.
- Los filtros disciplinarios deben bloquear contaminacion entre TI, ciberseguridad, ambiental, legal y management.

## Problemas encontrados

- Visual Analytics no tenia `big data` en la taxonomia canonica. Se agrego para cubrir el dominio de analitica.
- Los endpoints FastAPI protegidos requieren JWT; se dejaron como pruebas de integracion opcional con `TEST_ACCESS_TOKEN`.

## Riesgos antes de produccion

- La precision real de scraping depende de fuentes externas y debe validarse con gold dataset humano.
- El backend necesita un token de prueba institucional para CI/CD.
- Los release gates todavia dependen de datos Gold suficientes para calcular precision real.
- La suite frontend visual queda pendiente hasta estabilizar datos, scraping y taxonomia.

## Proximos pasos

1. Crear usuario/token de QA para CI.
2. Agregar fixture Gold revisado manualmente por dominio.
3. Ejecutar pruebas por cada corrida de scraping antes de publicar Silver/Gold.
4. Agregar pruebas E2E frontend solo cuando el motor laboral pase gates.
5. Incluir esta suite en GitHub Actions antes del deploy a Railway.
