# Visual Analytics Sources Extraction Report

- Run ID: `va-connectors-20260526161121`
- Extraccion con red: True
- Empleos aceptados: 6
- Empleos descartados: 90
- Duplicados: 0
- Final quality score: 0.5725
- Umbral Gold: 0.75
- Persistido: False
- Vacantes recuperadas por parsing contextual: 0

## Fuentes
- Ticjob: raw=50, accepted=3, discarded=47, errors=0
- Elempleo: raw=6, accepted=3, discarded=3, errors=0
- Hireline: raw=0, accepted=0, discarded=0, errors=0
- Buscador de Empleo: raw=0, accepted=0, discarded=0, errors=1
- Mi Futuro Empleo: raw=0, accepted=0, discarded=0, errors=0
- FindJobIT: raw=40, accepted=0, discarded=40, errors=0

## Razones De Descarte
- below_job_relevance_threshold: 27
- missing_title: 11
- missing_or_short_description: 12
- irrelevant_support_helpdesk: 4
- outside_visual_analytics_scope: 36

## Skills Extraidas
- Python: 6
- SQL: 6
- BI: 6
- dashboarding: 6
- Power BI: 6
- ETL: 5
- Google Cloud Analytics: 3
- KPIs: 3
- estadistica: 3
- visualizacion analitica: 3
- AI: 2
- data governance: 2
- Tableau: 2
- data quality: 1
- Databricks: 1
- AWS Analytics: 1
- Azure Data: 1
- Snowflake: 1
- lakehouse: 1

## Roles Detectados
- data_engineer: 6

## Errores
- Buscador de Empleo: ConnectionError - HTTPSConnectionPool(host='www.buscadordeempleo.gov.co', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.buscadordeempleo.gov.co', port=443): Failed to resolve 'www.buscadordeempleo.gov.co' ([Errno 11001] getaddrinfo failed)"))
