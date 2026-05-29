# Agentic Labor Hybrid Engine Validation

## Comparacion Modelo Anterior vs Hibrido

- Antes reportado: Bronze 6, Silver 6, Gold 0, Contextual recovered 4.
- Despues: Bronze 6, Silver 6, Gold A 0, Gold B 0, Rejected 6, Contextual recovered 1.

## Skills Frecuentes
- Sin skills detectadas.

## Tipos de Documento
- unknown: 5
- portal_taxonomy: 1

## Skills validas de vacantes reales
- Sin skills de vacante real.

## Skills descartadas por venir de taxonomia/filtros
- KPIs: 4
- Python: 4
- BI: 4
- SQL: 3
- ETL: 2
- Power BI: 2
- data governance: 2
- AI: 1
- machine learning: 1
- Hadoop: 1
- Spark: 1
- Tableau: 1
- estadistica: 1

## Tiers Hibridos
- Rejected: 6

## Vacantes Recuperadas y Evidencia
### Lugar de trabajo
- Fuente: Ticjob
- Score final: 0.0
- Curriculum alignment: 0.0
- Gold score: 0.3085
- Curriculum tier: Rejected
- Gold tier: Rejected
- Aprobada Gold: False
- Document type: portal_taxonomy
- Real job posting: False
- Invalid reason: invalid_catalog_title;empty_company;negative_support_signal
- Job evidence skills: []
- Portal taxonomy skills blocked: ["AI", "machine learning", "KPIs", "Python", "SQL", "ETL", "Hadoop", "Spark", "BI", "Power BI", "Tableau"]
- Clusters: {}
- Gaps mercado: []
- Alineacion curricular: No se usa para alineacion curricular porque el documento no es una vacante laboral real.
- Evidencia: 
- Motivo: invalid_catalog_title;empty_company;negative_support_signal
### Administrador de Servidores de Aplicaciones
- Fuente: Ticjob
- Score final: 0.0
- Curriculum alignment: 0.0
- Gold score: 0.1322
- Curriculum tier: Rejected
- Gold tier: Rejected
- Aprobada Gold: False
- Document type: unknown
- Real job posting: False
- Invalid reason: negative_support_signal
- Job evidence skills: []
- Portal taxonomy skills blocked: ["KPIs", "Python", "data governance", "BI"]
- Clusters: {}
- Gaps mercado: []
- Alineacion curricular: No se usa para alineacion curricular porque el documento no es una vacante laboral real.
- Evidencia: 
- Motivo: negative_support_signal
### SETI S.A.S.
- Fuente: Ticjob
- Score final: 0.0
- Curriculum alignment: 0.0
- Gold score: 0.1362
- Curriculum tier: Rejected
- Gold tier: Rejected
- Aprobada Gold: False
- Document type: unknown
- Real job posting: False
- Invalid reason: negative_support_signal
- Job evidence skills: []
- Portal taxonomy skills blocked: ["Python", "SQL"]
- Clusters: {}
- Gaps mercado: []
- Alineacion curricular: No se usa para alineacion curricular porque el documento no es una vacante laboral real.
- Evidencia: 
- Motivo: negative_support_signal
### Administrador Linux
- Fuente: Ticjob
- Score final: 0.0
- Curriculum alignment: 0.0
- Gold score: 0.095
- Curriculum tier: Rejected
- Gold tier: Rejected
- Aprobada Gold: False
- Document type: unknown
- Real job posting: False
- Invalid reason: negative_support_signal
- Job evidence skills: []
- Portal taxonomy skills blocked: ["KPIs", "Python", "data governance", "BI"]
- Clusters: {}
- Gaps mercado: []
- Alineacion curricular: No se usa para alineacion curricular porque el documento no es una vacante laboral real.
- Evidencia: 
- Motivo: negative_support_signal
### Ofertas de trabajo - Mayo 2026 | elempleo.com Colombia
- Fuente: Elempleo
- Score final: 0.0
- Curriculum alignment: 0.0
- Gold score: 0.2466
- Curriculum tier: Rejected
- Gold tier: Rejected
- Aprobada Gold: False
- Document type: unknown
- Real job posting: False
- Invalid reason: empty_title;negative_support_signal
- Job evidence skills: []
- Portal taxonomy skills blocked: ["KPIs", "estadistica", "SQL", "ETL", "BI", "Power BI"]
- Clusters: {}
- Gaps mercado: []
- Alineacion curricular: No se usa para alineacion curricular porque el documento no es una vacante laboral real.
- Evidencia: 
- Motivo: empty_title;negative_support_signal
### Autorizado por la Unidad Administrativa Especial del Servicio Público de Empleo, según Res
- Fuente: Elempleo
- Score final: 0.0
- Curriculum alignment: 0.0
- Gold score: 0.0933
- Curriculum tier: Rejected
- Gold tier: Rejected
- Aprobada Gold: False
- Document type: unknown
- Real job posting: False
- Invalid reason: empty_company;missing_job_posting_signals
- Job evidence skills: []
- Portal taxonomy skills blocked: []
- Clusters: {}
- Gaps mercado: []
- Alineacion curricular: No se usa para alineacion curricular porque el documento no es una vacante laboral real.
- Evidencia: 
- Motivo: empty_company;missing_job_posting_signals

## Recomendaciones de Calibracion
- Mantener Helpdesk/Networking puro bloqueado por senales negativas.
- Revisar manualmente Gold B antes de alimentar KPIs institucionales.
- Priorizar detail pages con descripcion completa para mejorar evidencia contextual.
