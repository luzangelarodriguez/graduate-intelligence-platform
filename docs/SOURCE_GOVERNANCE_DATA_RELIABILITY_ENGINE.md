# Source Governance & Data Reliability Engine

## Objetivo

Convertir las fuentes laborales en activos gobernados, medibles y auditables antes de alimentar KPIs institucionales.

## Capa creada

`scrapers/governance/`

Modulos:

- `source_reliability.py`: reliability score, tiering y metricas base por fuente.
- `freshness_scoring.py`: frescura de extracciones por antiguedad de runs.
- `evidence_quality.py`: calidad de evidencia, contaminacion y densidad de datos.
- `access_strategy.py`: estrategia de acceso por fuente.
- `source_sla.py`: uptime, estabilidad de respuesta, estabilidad de schema y volatilidad auth.
- `governance_dashboard.py`: orquestador y dashboard tecnico interno.

## KPIs gobernados

- `reliability_score`
- `freshness_score`
- `contamination_rate`
- `blocked_auth_rate`
- `semantic_density`
- `evidence_quality`
- `extraction_completeness`
- `source_stability`

## Clasificacion de fuente

- `Gold`: alta confiabilidad, baja contaminacion, sin bloqueo auth relevante y lista para pruebas KPI.
- `Silver`: evidencia util pero aun no suficientemente validada.
- `Bronze`: evidencia parcial o fuente con estabilidad limitada.
- `Experimental`: fuente descubierta o bloqueada sin evidencia productiva.

## Estrategia de acceso

Valores soportados:

- `API`
- `scraping`
- `partnership`
- `licensed`
- `blocked_auth`

Cuando una fuente queda como `blocked_auth`, no debe alimentar KPIs productivos hasta resolver token, convenio, sesion autorizada o licencia.

## Tablas nuevas

- `source_governance`
- `source_quality_history`
- `source_access_strategy`
- `source_sla_metrics`

## Ejecucion

Generar dashboard local:

```powershell
python scrapers\governance\governance_dashboard.py
```

Generar dashboard y persistir en PostgreSQL:

```powershell
python scrapers\governance\governance_dashboard.py --write-db
```

Filtrar fuentes:

```powershell
python scrapers\governance\governance_dashboard.py --sources elempleo magneto_api --write-db
```

## Outputs

- `outputs/source_governance/source_governance_dashboard.json`
- `outputs/source_governance/source_governance_dashboard.md`

## Regla de gobierno

Una fuente no debe alimentar KPIs institucionales si:

- `blocked_auth_rate > 0.05`
- `contamination_rate > 0.12`
- `evidence_quality < 0.62`
- `freshness_score < 0.45`
- `extraction_completeness < 0.55`

## Relacion con Gold Pipeline

El pipeline de El Empleo puede dejar runs `blocked_auth`. Esta capa convierte ese estado en un indicador de gobierno y evita que una API real pero no accesible sea tratada como fuente Gold.
