# Scraping Runtime Hardening

## Objetivo

Esta fase elimina la dependencia de `networkidle` en los scrapers laborales basados en Playwright. Portales modernos como El Empleo pueden mantener XHR, analytics, long polling, GraphQL o requests de tracking abiertos de forma permanente, por lo que esperar `networkidle` puede bloquear el pipeline aunque los resultados ya estén visibles.

## Cambios Implementados

- Se creó `safe_wait_for_results()` en `scrapers/sources/base.py`.
- La búsqueda, extracción de detalle y paginación ahora esperan evidencia DOM real mediante selectores.
- Se agregó fallback a `domcontentloaded` y esperas cortas con backoff.
- Se detectan señales de runtime moderno:
  - Next.js
  - React root
  - posible polling permanente
- Se agregaron logs por fuente:
  - selector encontrado
  - fase
  - tiempo de carga
  - retries
  - timeout real
  - runtime detectado
- Se agregaron guardrails de ejecución:
  - máximo de páginas por fuente
  - presupuesto máximo de runtime por fuente
  - máximo de detalles inspeccionados por fuente
- `jobs_pipeline.py` ahora registra `source_status` por fuente.
- Si una fuente falla o no entrega empleos, se marca como `degraded` y el pipeline continúa.

## Estrategia de Espera

Prioridad enterprise:

1. `wait_for_selector()` sobre job cards o selectores de detalle.
2. Fallback a `domcontentloaded`.
3. Espera corta incremental.
4. Retry con backoff.
5. Estado degradado si no hay evidencia suficiente.
6. Corte controlado por presupuesto de fuente para evitar corridas indefinidas.

## Comportamiento Esperado

El pipeline ya no queda bloqueado por El Empleo si el portal mantiene tráfico permanente. Si El Empleo falla:

- el error queda en logs,
- la fuente queda como `source_status=degraded`,
- SPE y Computrabajo continúan,
- el CSV y la normalización siguen ejecutándose con las fuentes disponibles.

## Comando de Validación

```powershell
python -m pytest tests
python scrapers\pipelines\jobs_pipeline.py --sources spe computrabajo elempleo --query "python data analyst" --limit 100
```

## Validación Ejecutada

- `python -m py_compile scrapers\sources\base.py scrapers\pipelines\jobs_pipeline.py`: OK.
- `python -m pytest tests`: `22 passed, 4 skipped`.
- Pipeline vivo con SPE, Computrabajo y El Empleo: finalizó en 111.7 segundos sin bloquear la ejecución completa.

Resultado observado:

```json
{
  "jobs": 0,
  "source_status": {
    "spe": {"source_status": "degraded", "reason": "no_jobs_extracted"},
    "computrabajo": {"source_status": "degraded", "reason": "no_jobs_extracted"},
    "elempleo": {"source_status": "degraded", "reason": "no_jobs_extracted"}
  }
}
```

Interpretación: el runtime ya no queda colgado por `networkidle`; las fuentes pueden quedar degradadas por selectores/resultados no disponibles o timeout de navegación, y el pipeline termina con reporte de estado.

## Riesgos Pendientes

- El scraping DOM sigue siendo más frágil que los endpoints API-first.
- El Empleo ya tiene endpoints confirmados (`findbyfilter`, `getjoboffer`), por lo que debe priorizarse el pipeline Gold API-first cuando se requiera volumen y estabilidad.
- Algunos portales pueden cambiar nombres de clases o estructura de cards; los selectores deben monitorearse con métricas de calidad por fuente.

## Próximos Pasos

1. Integrar `source_status` con `source_quality_metrics`.
2. Promover El Empleo API-first como fuente preferida frente al DOM scraper.
3. Guardar snapshots de timeout y selectors fallidos en observabilidad.
4. Añadir threshold por fuente para bloquear publicación Gold cuando una fuente esté degradada por demasiadas corridas.
