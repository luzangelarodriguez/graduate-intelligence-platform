# API-First Labor Extraction Engine

## Objetivo

Migrar progresivamente desde scraping DOM hacia extraccion laboral API-first, escalable y enterprise-grade, sin eliminar la arquitectura actual ni conectar aun el motor al KPI institucional.

## Fuente prioritaria

Fuente implementada en esta fase:

```text
api.magneto365.com
```

Modulo:

```text
scrapers/lakehouse/magneto_api_extractor.py
```

Wrapper compatible:

```text
scrapers/sources/magneto_api_scraper.py
```

## Lakehouse

Estructura creada:

```text
scrapers/lakehouse/
  bronze/
  silver/
  gold/
  magneto_api_extractor.py
  relevance.py
  release_gates.py
```

### Bronze

Guarda payloads raw:

- response JSON
- endpoint
- parametros
- hash
- snapshot por corrida

Tabla:

```text
public.bronze_job_payloads
```

Archivos:

```text
scrapers/lakehouse/bronze/magneto_api/<YYYYMMDD>/<run_id>/
```

### Silver

Guarda empleos normalizados:

- titulo
- descripcion
- skills
- empresa
- ciudad
- modalidad
- seniority
- salario
- fecha publicacion
- dominio
- metadata
- confidence/relevance

Tabla:

```text
public.silver_normalized_jobs
```

Archivos:

```text
scrapers/lakehouse/silver/magneto_api/<YYYYMMDD>/<run_id>/normalized_jobs.json
scrapers/lakehouse/silver/magneto_api/<YYYYMMDD>/<run_id>/normalized_jobs.csv
```

### Gold

Capa preparada para revision humana:

```text
public.gold_validated_jobs
```

No se auto-valida evidencia. La promocion a Gold requiere reviewer.

## Nuevas tablas

Incluidas en:

```text
database/enterprise_labor_intelligence_schema.sql
```

Tablas:

- `extraction_runs`
- `bronze_job_payloads`
- `silver_normalized_jobs`
- `gold_validated_jobs`
- `relevance_scores`

## Relevance weighting

Modulo:

```text
scrapers/lakehouse/relevance.py
```

Calcula:

- `source_weight`
- `evidence_weight`
- `domain_confidence`
- `semantic_density`
- `overall_score`

Formula inicial:

- source weight: 25%
- evidence weight: 30%
- domain confidence: 25%
- semantic density: 20%

## KPI release gates

Modulo:

```text
scrapers/lakehouse/release_gates.py
```

Comando:

```powershell
python scrapers\lakehouse\release_gates.py --source magneto_api
```

Regla:

No permitir conexion al KPI productivo si:

- `precision_rate < threshold`
- `confidence_avg < threshold`
- `gold_validation < threshold`

Umbrales default:

- precision: `0.70`
- confidence promedio: `0.68`
- gold validado: `30`

## Ejecucion

Corrida API-first Magneto:

```powershell
python scrapers\lakehouse\magneto_api_extractor.py --query "analista de datos" --pages 1 --page-size 20
```

Modo exploratorio:

```powershell
python scrapers\lakehouse\magneto_api_extractor.py --query "sostenibilidad ESG" --pages 1 --page-size 20 --dry-run
```

## Coexistencia incremental

La arquitectura DOM previa sigue existiendo:

- `scrapers/sources/magneto_scraper.py`
- `scrapers/pipelines/jobs_pipeline.py`

La nueva ruta API-first convive en lakehouse y no reemplaza automaticamente el pipeline legacy.

## Estado operativo

El discovery previo detecto endpoints utiles de Magneto, principalmente:

- `api.magneto365.com/jobs/v1/public/locations`
- `api.magneto365.com/seo/v1/mega-menu/by-occupation`
- `api.magneto365.com/seo/v1/mega-menu/by-company`
- `api.magneto365.com/seo/v1/mega-menu/by-sector`

El extractor prueba estos endpoints y varios patrones candidatos de vacantes. Todo payload queda en Bronze, incluso cuando el endpoint no devuelve vacantes normalizables, para facilitar trazabilidad.

## Corridas de verificacion

Se ejecutaron dos corridas pequenas con query:

```text
analista de datos
```

### Corrida 1

```text
run_id: magneto_api_20260519_160154_05dc78d3
raw_count: 114
silver_count: 114
error_count: 4
```

Hallazgo: los endpoints SEO de Magneto devuelven categorias/landing pages con metadata laboral, pero no necesariamente vacantes reales. Esa corrida quedo como evidencia QA inicial.

### Corrida 2

Despues de endurecer el filtro Silver:

```text
run_id: magneto_api_20260519_160245_b0478959
raw_count: 99
silver_count: 0
error_count: 4
```

Interpretacion: Bronze captura payloads API correctamente, pero ningun registro supero el criterio de evidencia laboral real. Esto es preferible a contaminar Silver con categorias SEO.

## Gate KPI

Evaluacion:

```powershell
python scrapers\lakehouse\release_gates.py --source magneto_api
```

Resultado:

```json
{
  "allowed": false,
  "precision_rate": 0.0,
  "confidence_avg": 0.2582,
  "gold_validation": 0,
  "threshold_precision": 0.7,
  "threshold_confidence": 0.68,
  "threshold_gold": 30,
  "reason": "blocked_until_precision_confidence_and_gold_thresholds_pass"
}
```

Conclusion: Magneto API-first queda implementado, pero bloqueado para KPI productivo hasta encontrar endpoint de vacantes reales y poblar Gold.

## Siguiente ajuste recomendado

Inspeccionar los bundles Next.js de Magneto para ubicar el endpoint exacto de busqueda de vacantes. El motor ya esta preparado para agregarlo en `endpoint_candidates()` sin cambiar Bronze/Silver/Gold ni tablas.
