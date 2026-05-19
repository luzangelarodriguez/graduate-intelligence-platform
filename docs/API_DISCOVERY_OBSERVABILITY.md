# API Discovery & Labor Intelligence Observability

## Objetivo

Crear una capa enterprise para descubrir, registrar y priorizar APIs laborales reales antes de alimentar el observatorio institucional. Esta fase reduce dependencia de scraping visual y bloquea ruido SEO/marketing antes de entrar a Silver o KPI.

## Estructura creada

```text
scrapers/discovery/
  anti_seo_filter.py
  api_registry.py
  bundle_inspector.py
  endpoint_ranker.py
  graphql_detector.py
  run_api_discovery.py
  xhr_capture.py
```

## Capacidades

### Bundle Inspection

Archivo:

```text
scrapers/discovery/bundle_inspector.py
```

Detecta en HTML y bundles JS:

- `_next/static`
- `fetch()`
- `axios.get/post`
- `XMLHttpRequest`
- WebSocket URLs
- literales API
- GraphQL operations

### XHR Capture

Archivo:

```text
scrapers/discovery/xhr_capture.py
```

Captura:

- requests
- payloads
- headers
- responses
- status
- resource type
- duration
- muestras JSON

### GraphQL Detector

Archivo:

```text
scrapers/discovery/graphql_detector.py
```

Detecta:

- `/graphql`
- `query`
- `mutation`
- Apollo
- urql
- GraphQLClient

### API Registry

Archivo:

```text
scrapers/discovery/api_registry.py
```

Registra endpoints en:

```text
public.api_sources_registry
```

Campos:

- source
- endpoint
- method
- response_type
- confidence
- seo_noise
- auth_required
- pagination
- discovered_at

### Endpoint Ranking

Archivo:

```text
scrapers/discovery/endpoint_ranker.py
```

Calcula:

- richness
- freshness
- semantic density
- vacancy quality
- extraction completeness
- seo noise
- rank score

### Anti SEO Filter

Archivo:

```text
scrapers/discovery/anti_seo_filter.py
```

Bloquea o penaliza:

- category pages
- SEO pages
- generic listings
- marketing content
- analytics/adtech endpoints
- `_next/static` assets sin valor laboral

## Tablas nuevas

Agregadas a:

```text
database/enterprise_labor_intelligence_schema.sql
```

Tablas:

- `api_sources_registry`
- `api_discovery_runs`
- `api_request_logs`
- `api_response_snapshots`
- `api_extraction_metrics`

## Portales priorizados

- Magneto
- Computrabajo
- El Empleo
- Torre
- SPE

## Ejecucion

Fase completa:

```powershell
python scrapers\discovery\run_api_discovery.py --sources magneto computrabajo elempleo torre spe --write-db
```

Solo bundles:

```powershell
python scrapers\discovery\bundle_inspector.py --sources magneto --write-db
```

Solo XHR:

```powershell
python scrapers\discovery\xhr_capture.py --sources magneto --write-db
```

Importar resultados previos:

```powershell
python scrapers\discovery\api_registry.py --input outputs\labor_intelligence_stabilization\xhr_endpoint_discovery.json
```

## Gobierno de datos

Un endpoint no debe alimentar KPI ni Silver productivo si:

- `seo_noise = true`
- `rank_score < 0.55`
- `auth_required = true` sin estrategia autorizada
- no hay paginacion detectable para busquedas
- no contiene señales de vacante real

## Resultado esperado

La plataforma puede registrar y observar endpoints candidatos sin usarlos productivamente. Esto permite priorizar API-first con evidencia, no con intuicion visual.

## Corrida de verificacion

Se ejecuto una corrida reducida:

```powershell
python scrapers\discovery\run_api_discovery.py --sources magneto elempleo --max-bundles 8 --wait-ms 6000 --write-db
```

Resultado:

- Bundle findings: `679`
- XHR hits: `221`
- Registry total despues de la corrida: `838`

Hallazgos principales:

- El Empleo expone endpoints laborales reales en bundle:
  - `https://www.elempleo.com/co/api/joboffers/findbyfilter`
  - `https://www.elempleo.com/co/api/joboffers/getjoboffer`
- Magneto sigue mostrando endpoint util de metadata/localidades:
  - `https://api.magneto365.com/jobs/v1/public/locations?term=all&country_id=47`
- Magneto aun requiere endpoint exacto de busqueda/detalle de vacantes; lo detectado de mayor volumen sigue mezclado con SEO/categorias.

Prioridad recomendada tras discovery:

1. Implementar extractor API-first para El Empleo usando `findbyfilter` y `getjoboffer`.
2. Seguir inspeccionando bundles de Magneto para ubicar vacantes reales.
3. Mantener `seo_noise` y `rank_score` como compuerta antes de Silver.
4. No conectar ningun endpoint al KPI hasta que `rank_score`, Gold y precision superen umbrales.

