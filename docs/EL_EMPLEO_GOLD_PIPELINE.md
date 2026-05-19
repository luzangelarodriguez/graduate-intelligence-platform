# El Empleo Gold Pipeline

## Objetivo

Esta fase convierte los endpoints API-first de El Empleo en una fuente Gold candidata para el motor de inteligencia laboral longitudinal.

Endpoints objetivo:

- `https://www.elempleo.com/co/api/joboffers/findbyfilter`
- `https://www.elempleo.com/co/api/joboffers/getjoboffer`

El pipeline no publica evidencia en KPIs institucionales si la API no entrega datos verificables o si la fuente requiere autenticacion no resuelta.

## Archivo principal

`scrapers/pipelines/elempleo_gold_pipeline.py`

Ejecucion base:

```powershell
python scrapers\pipelines\elempleo_gold_pipeline.py --query "analista de datos" --pages 1 --page-size 20
```

Publicacion Gold con compuerta automatica:

```powershell
python scrapers\pipelines\elempleo_gold_pipeline.py --query "analista de datos" --pages 2 --page-size 20 --auto-validate --min-relevance 0.64
```

## Flujo

1. Bootstrap de sesion desde la pagina publica de resultados.
2. Descubrimiento via `/api/joboffers/findbyfilter`.
3. Paginacion controlada.
4. Enriquecimiento via `/api/joboffers/getjoboffer`.
5. Persistencia Bronze de request, response, status code y endpoint.
6. Normalizacion Silver al esquema canonico.
7. Clasificacion disciplinar.
8. Extraccion de skills con guardrails por dominio.
9. Calculo de relevancia.
10. Deduplicacion por `title + company + location` y similitud semantica.
11. Publicacion en `canonical_jobs` y `gold_validated_jobs` si pasa umbral.
12. Persistencia de lineage KPI -> Gold -> Silver -> Bronze -> API endpoint.
13. Calculo de senales temporales por skill/dominio.

## Esquema canonico

Campos normalizados:

- `role_title`
- `canonical_role`
- `domain`
- `seniority`
- `modality`
- `salary`
- `location`
- `company`
- `skills`
- `evidence_text`

## Tablas nuevas

- `canonical_jobs`: empleo canonico longitudinal.
- `job_skill_trends`: conteos historicos por skill y dominio.
- `source_lineage`: trazabilidad completa desde KPI hasta payload API.
- `temporal_market_signals`: senales de crecimiento, aceleracion y declive.

Tambien reutiliza:

- `extraction_runs`
- `bronze_job_payloads`
- `silver_normalized_jobs`
- `gold_validated_jobs`
- `relevance_scores`
- `api_sources_registry`

## Relevance y validacion

El score combina:

- calidad de fuente
- densidad de evidencia
- coherencia disciplinar
- densidad semantica
- skills detectadas

La publicacion Gold queda como `candidate` por defecto. Para marcar validacion automatica se debe usar `--auto-validate`; aun asi, solo se publica si supera `--min-relevance`.

## Manejo de API protegida

Si El Empleo responde `401` o `403`, el pipeline:

- guarda el intento en Bronze;
- marca el endpoint como `auth_required` en `api_sources_registry`;
- finaliza el run como `blocked_auth` si no hubo resultados;
- evita publicar datos Silver/Gold artificiales.

Esto mantiene auditabilidad sin contaminar el observatorio.

## Salidas Lakehouse

Bronze:

`scrapers/lakehouse/bronze/elempleo/YYYYMMDD/<run_id>/`

Silver:

`scrapers/lakehouse/silver/elempleo/YYYYMMDD/<run_id>/normalized_jobs.json`

Gold:

`scrapers/lakehouse/gold/elempleo/YYYYMMDD/<run_id>/gold_publication_summary.json`

## Proximos pasos

1. Capturar payload y headers reales desde navegador autenticado si la API exige token de sesion.
2. Agregar fixture Gold manual por dominio para validar precision.
3. Comparar precision El Empleo vs Magneto antes de conectar a KPI institucional.
4. Programar snapshots diarios o semanales con scheduler.
5. Activar alertas de drift para skills emergentes por dominio.
