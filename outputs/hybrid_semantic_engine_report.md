# Hybrid Semantic Engine Report

## Objetivo

El motor de relevancia laboral para la Especializacion en Visual Analytics y Big Data fue refactorizado para pasar de un matcher centrado en titulos y keywords a un ranking semantico hibrido basado en clusters, familias ocupacionales, evidencia contextual y moderacion de senales negativas.

## Cambios implementados

- Nuevo motor: `ml/relevance/hybrid_semantic_relevance_engine.py`.
- Nuevo generador de evidencia: `ml/relevance/job_contextual_evidence_engine.py`.
- Integracion con el motor previo `contextual_job_relevance_engine.py` sin bajar quality gates.
- Dataset de entrenamiento ampliado con `hybrid_role`, `semantic_label`, `gold_tier`, `contextual_evidence`, `cluster_signals` y `final_semantic_relevance_score`.
- Memoria semantica de mercado preparada en `ml/datasets/semantic_market_memory.json`.

## Diferencias frente al modelo anterior

| Dimension | Modelo anterior | Motor hibrido |
|---|---|---|
| Titulos ambiguos | Penalizacion alta | Evalua contexto completo antes de rechazar |
| Backend/cloud mixto | Frecuentemente descartado | Acepta si existe evidencia analytics/BI/data |
| Soporte tecnico | Penalizacion simple | Rechazo explicable si es soporte puro |
| Evidencia contextual | Limitada | Resume senales BI, analytics, cloud, governance y data engineering |
| Trazabilidad | Score compacto | Tier, clusters, evidencia y explicacion de aceptacion/rechazo |

## Roles hibridos recuperados

- Backend Developer con Power BI, SQL, dashboards, ETL y KPIs: aceptado como `Gold B`.
- ETL Developer con dashboards, SQL, data warehouse y reporting: aceptado como `Silver`.
- Azure Analytics Engineer con KPIs, reporting, Power BI y cloud analytics: aceptado como `Silver`.
- DataOps Engineer con analytics, pipelines, data quality y cloud analytics: aceptado como `Silver`.

## Senales contextuales detectadas

- Visualizacion: Power BI, Tableau, dashboards.
- Business intelligence: BI, reporting, KPIs.
- Ingenieria de datos: ETL, pipelines, data warehouse.
- Cloud data: Azure, cloud analytics.
- Gobierno y calidad: data quality.
- DataOps: data observability y operaciones de datos.

## Control de contaminacion

Se mantiene rechazo para:

- Helpdesk puro.
- Soporte tecnico puro.
- Hardware, impresoras, cableado y mantenimiento fisico.
- Networking puro sin evidencia analytics/BI/data.

## Top skill clusters

1. `business_intelligence`
2. `visualization`
3. `analytics`
4. `data_engineering`
5. `cloud_data`
6. `reporting`
7. `governance`
8. `dataops`

## Readiness

El motor queda listo para integrarse en pipelines Bronze/Silver/Gold como capa semantica de scoring. Gold no se contamina automaticamente: las reglas de persistencia siguen requiriendo score, evidencia contextual y quality gates.
