# Visual Analytics Y Big Data Pilot

## Especialización Piloto

`Especialización en Visual Analytics y Big Data`

## Estado Del Selector

La especialización aparece en el selector desde PostgreSQL con:

- `id`: `94`
- `nombre`: `Especialización en Visual Analytics y Big Data`
- `nivel`: `Especialización`
- `estado`: `Activo`

## Carpeta Usada

El backend busca microcurrículos en:

- `storage/microcurriculos/Especialización en Visual Analytics y Big Data/`
- `storage/microcurriculos/Especializacion en Visual Analytics y Big Data/`
- `storage/microcurriculos/visual_analytics_big_data/`
- `storage/test_microcurriculos/especialización en visual analytics y big data/`
- nombres equivalentes normalizados sin tildes, mayúsculas, espacios ni caracteres especiales

También valida nombres de archivo cuando los documentos están planos en `storage/microcurriculos/`.

## Documentos Procesados

Estado actual: documentos piloto ubicados en `storage/test_microcurriculos/especialización en visual analytics y big data/`.

Documentos detectados:

- `aprendizaje automatico.docx`
- `Microcurrículos V5_Análisis e interpretación de datos.docx`
- `Microcurrículos V5_Electiva Innovación Tecnológica y Transformación Digital de las Empresas.docx`
- `Microcurrículos V5_Fundamentos tecnológicos para el tratamiento de datos.docx`
- `Microcurrículos V5_Gestión de proyectos de inteligencia de negocio.docx`
- `Microcurrículos V5_Gobierno del dato y toma de decisiones.docx`
- `Microcurrículos V5_Ingenieria para el procesado masivo de datos.docx`
- `Microcurrículos V5_Seguridad en Sistemas, Aplicaciones y el Big Data.docx`
- `Microcurrículos V5_Tecnicas de Inteligencia Artificial.docx`
- `Microcurrículos V5_Visualización Interactiva de la Información.docx`

## Dominio Esperado

- `analitica`
- `analitica/visual_analytics_big_data`

## Entidades Esperadas Para El Piloto

- Power BI
- Tableau
- SQL
- Python
- R
- Big Data
- ETL
- Machine Learning
- Data Visualization
- Dashboards
- Storytelling with Data
- Data Governance
- Data Warehousing
- Cloud Analytics
- Azure
- AWS
- Google Cloud
- Spark
- Hadoop
- Databricks
- Snowflake
- Power Platform

## Recomendaciones Esperadas

El endpoint consolidado agrega recomendaciones específicas para Visual Analytics y Big Data:

- fortalecer analítica avanzada con Python/R
- incorporar prácticas de visualización ejecutiva
- incluir gobierno de datos
- reforzar arquitectura lakehouse
- incluir herramientas cloud analytics
- incorporar modelos predictivos aplicados
- fortalecer storytelling y toma de decisiones basada en datos

## Brechas Y Áreas A Fortalecer

La regla semántica ya está activa:

- Si una entidad aparece en los microcurrículos, no puede mostrarse como brecha real.
- Si aparece en currículo y en señales de mercado, se clasifica como área a fortalecer.
- Si aparece en mercado y no aparece en currículo, se clasifica como brecha real.

## Estado Del Piloto

`listo_para_ejecucion_local`

El flujo técnico está implementado y la ruta de documentos piloto fue conectada como fuente local de prueba.

## Riesgos Pendientes

- El procesamiento completo de los 10 DOCX puede tardar más que una prueba unitaria normal.
- Se debe revisar manualmente si asignaturas de seguridad introducen señales TI que deban clasificarse como componente contextual y no como contaminación.
- Para validar manualmente:

```powershell
curl.exe http://127.0.0.1:8010/api/microcurriculum/specialization/94/documents
curl.exe -X POST http://127.0.0.1:8010/api/microcurriculum/specialization/94/analyze
```
