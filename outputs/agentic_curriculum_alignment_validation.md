# Agentic Curriculum Alignment Validation

## Alcance

Validacion del pipeline agentic para la Especializacion en Visual Analytics y Big Data usando:

- `curriculum_alignment_score`
- `curriculum_skill_graph`
- `curriculum_shared_skills` como skills cubiertas
- `curriculum_related_matches` como skills parcialmente cubiertas o extensiones naturales
- `market_gap_signal`
- `gold_score`
- `curriculum_gold_tier`

No se tocaron frontend, Vercel, auth, variables Railway ni diseno.

## Ejecuciones

### Dry-run

Comando:

```powershell
python pipelines/run_agentic_labor_intelligence.py --dry-run
```

Resultado:

- Bronze: 0
- Silver: 0
- Gold: 0
- Persistencia: 0
- Errores: 0

### Corrida controlada quality-review

Comando:

```powershell
python pipelines/run_agentic_labor_intelligence.py --execute-network --max-pages 2 --max-jobs 30 --quality-review
```

Resultado:

- Bronze: 9
- Silver: 9
- Gold A: 0
- Gold B: 1
- Rejected: 8
- Contextual recovered: 3
- Persistencia durante quality-review: 0
- Errores: 0

### Persistencia controlada

Comando:

```powershell
python pipelines/run_agentic_labor_intelligence.py --persist-approved-gold-from-results
```

Resultado:

- Bronze persistido: 1
- Silver persistido: 1
- Gold persistido: 1

Solo se persistio la vacante aprobada por Gold B. No se persistieron paginas con ruido, listados ni rechazados.

## Comparacion Antes / Despues

| Metrica | Corrida anterior | Nueva corrida curricular |
|---|---:|---:|
| Bronze | 11 | 9 |
| Silver | 11 | 9 |
| Gold A | 0 | 0 |
| Gold B | 1 | 1 |
| Rejected | 10 | 8 |
| Contextual recovered | 5 | 3 |

La nueva formula no aumento Gold neto en esta muestra, pero si explico mejor por que algunas paginas no deben promocionarse aunque tengan fuerte overlap curricular.

## Vacante Promovida

### Desarrollador Backend .NET Senior (hibrido)

- Curriculum alignment: 0.6851
- Gold score: 0.7182
- Curriculum tier: Gold B
- Hybrid semantic tier: Gold B
- Aprobada Gold: true
- Familia: backend_data_platform
- Motivo: accepted_for_gold

Skills cubiertas:

- AI
- BI
- KPIs
- Python
- dashboarding
- data governance
- machine learning

Skills parcialmente cubiertas / extensiones:

- business intelligence
- dashboards
- gobierno de datos
- modelos predictivos
- data governance
- KPIs

Explicacion curricular:

La vacante se alinea porque comparte competencias presentes en los microcurriculos reales y extiende el ecosistema hacia arquitectura backend/plataforma de datos con evidencia BI, dashboards, KPIs, governance y machine learning.

## Vacantes No Promovidas y Motivo

### Skills

- Curriculum alignment: 0.8182
- Gold score: 0.7623
- Curriculum tier: Gold B
- Aprobada Gold: false
- Motivo: rejected_negative_support_or_infrastructure_signal
- Interpretacion: alta similitud curricular, pero la pagina incluye senales negativas de soporte/listado. No se promueve para proteger Gold.

### Lugar de trabajo

- Curriculum alignment: 0.8475
- Gold score: 0.8087
- Curriculum tier: Gold A
- Aprobada Gold: false
- Motivo: rejected_negative_support_or_infrastructure_signal
- Interpretacion: fuerte overlap curricular, pero el contenido corresponde a bloque de pagina/listado con ruido operativo. Correctamente bloqueada.

### Administrador de Aplicaciones Oracle / WebLogic / Middleware

- Curriculum alignment: 0.5238
- Gold score: 0.5341
- Curriculum tier: Silver
- Aprobada Gold: false
- Motivo: accepted_contextual_curriculum_signal
- Interpretacion: relacion parcial con SQL, dashboarding y pipelines, pero no suficiente para Gold.

### Administrador base datos en Bogota alrededores

- Curriculum alignment: 0.6067
- Gold score: 0.6245
- Curriculum tier: Silver
- Aprobada Gold: false
- Motivo: rejected_negative_support_or_infrastructure_signal
- Interpretacion: comparte BI, KPIs, Power BI, SQL y estadistica, pero la pagina presenta senales negativas/ruido de portal. Requiere detail page mas limpio.

## Skills Cubiertas

- Python
- SQL
- KPIs
- BI
- AI
- machine learning
- Power BI
- ETL
- Hadoop
- Spark
- Tableau
- dashboarding
- data governance
- estadistica

## Skills Parcialmente Cubiertas

- pipelines
- reporting
- business intelligence
- data warehouse
- cloud analytics
- modelos predictivos
- gobierno de datos
- analitica empresarial

## Gaps Detectados

En esta muestra viva limitada no emergieron gaps nuevos robustos en las vacantes aprobadas. En pruebas unitarias y escenarios controlados el engine detecta:

- Azure Synapse
- Microsoft Fabric
- DataOps
- Databricks
- GenAI analytics

Para que esos gaps entren al reporte productivo se requiere capturar detail pages laborales con esas senales en contexto real, no solo listados.

## Roles Hibridos Aceptados

- backend_data_platform: 1 Gold B persistido.
- analytics_bi_visualization: recuperado como Silver/Gold curricular en paginas con ruido, no persistido.
- generic_technology: rechazado.

## Recomendaciones Para Microcurriculo

- Mantener y profundizar BI, SQL, dashboards, KPIs, visualizacion y machine learning como nucleo curricular.
- Incorporar evidencia evaluable de data governance aplicada, porque aparece como senal laboral alineada.
- Fortalecer arquitectura de plataformas de datos y backend data solo cuando se conecte a dashboards, pipelines, APIs de datos o BI.
- Preparar unidades optativas o casos practicos sobre Microsoft Fabric, Azure Synapse, Databricks y DataOps, pero validarlas con mas evidencia Gold antes de tratarlas como brecha critica.
- Mejorar captura de detail pages para separar vacantes reales de bloques de pagina como "Skills" o "Lugar de trabajo".

## Conclusion

El sistema ya no evalua solamente si una vacante es analytics pura. Ahora calcula si pertenece al ecosistema profesional derivado de los microcurriculos reales. La gobernanza se mantiene: paginas ruidosas con alta similitud curricular no entran a Gold si tienen senales negativas o parsing incompleto.

## Correccion De Evidencia Laboral

Se agrego una barrera explicita entre skills de taxonomia del portal y skills de vacantes reales.

- `portal_taxonomy`: puede guardarse en Bronze como evidencia cruda, pero no alimenta Silver valido, Gold, gaps ni recomendaciones.
- `search_listing`: puede guardarse en Bronze, pero no entra a Gold.
- `filter_page`: queda bloqueada para Gold aunque contenga Power BI, SQL, Tableau u otras tecnologias.
- `job_posting`: unica fuente habilitada para `job_evidence_skills`, matching curricular y Gold.

Campos nuevos usados por el agente:

- `document_type`
- `is_real_job_posting`
- `evidence_source_type`
- `invalid_job_reason`
- `job_evidence_skills`
- `portal_taxonomy_skills`

Regla operativa:

Una pagina titulada `Skills`, con `source_url=javascript:;`, empresa vacia o catalogo de filtros puede conservarse como Bronze, pero sus skills se reportan como `portal_taxonomy_skills` y no se consideran evidencia laboral.
