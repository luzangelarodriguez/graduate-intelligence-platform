# Executive Observatory Refactor

## Objetivo

Convertir la pantalla de analisis de microcurriculos en un observatorio institucional de inteligencia curricular y pertinencia laboral, evitando que la experiencia parezca un extractor NLP, un listado tecnico de tags o un dashboard de depuracion.

El piloto principal sigue siendo:

**Especializacion en Visual Analytics y Big Data**

## Problemas corregidos

### Redundancia de porcentajes

Antes aparecian dos lecturas porcentuales equivalentes:

- Alineacion actual 67%
- Indice de pertinencia curricular 67%

Ahora:

- La franja horizontal muestra **Alineacion actual** como estado ejecutivo: Baja, Media o Alta.
- El bloque principal mantiene el porcentaje unico del **Indice de pertinencia curricular**.

### KPIs estaticos

Las cinco cards KPI fueron convertidas en botones/filtros ejecutivos:

- Skills criticas faltantes
- Roles laborales con alta demanda
- Tendencia de empleabilidad
- Cobertura de habilidades digitales
- Senal de actualizacion curricular

Al seleccionar un KPI se abre un panel contextual con evidencia, prioridad y lectura ejecutiva.

### Ausencia de inteligencia laboral

Se agrego la seccion **Inteligencia laboral**, marcada como **Datos laborales exploratorios** hasta que la evidencia Gold laboral quede conectada al indicador productivo.

La seccion muestra:

- cargos asociados
- skills mas solicitadas
- frecuencia o fuerza relativa de senales laborales

Roles incluidos para el piloto:

- Data Analyst
- BI Analyst
- Analytics Consultant
- Data Engineer
- Visualization Specialist

Skills laborales incluidas:

- Power BI
- SQL
- Python
- ETL
- Tableau
- Data Governance
- Cloud Analytics

### Resumen ejecutivo reemplazado

Se elimino el bloque principal de **Resumen ejecutivo** como protagonista de la pantalla.

Fue reemplazado por:

**Benchmarking curricular SNIES**

Este modulo muestra:

- universidades o programas similares cuando el endpoint SNIES devuelve datos
- modalidad y ciudad
- score comparativo
- posicion competitiva
- promedio competidores
- diferencia competitiva

### Eliminacion de tag clouds

Se dejaron de usar chips y listas de palabras como visual principal.

Fueron reemplazados por:

- heatmap curricular
- radar de pertinencia
- barras comparativas curriculo vs mercado
- gauge del indice de pertinencia
- timeline de actualizacion curricular
- barras ejecutivas de evidencia tecnologica

## Nueva narrativa ejecutiva

La pantalla ahora sigue esta historia:

1. Que tan pertinente es el programa.
2. Que demanda el mercado laboral.
3. Que capacidades curriculares ya existen.
4. Que brechas estrategicas requieren atencion.
5. Como se compara el programa frente a oferta academica SNIES.
6. Que transformacion curricular se propone.

## Visualizaciones implementadas

### Gauge

Muestra el **Indice de pertinencia curricular** como lectura ejecutiva de alto nivel.

### Radar de pertinencia

Dimensiones:

- IA
- Visual analytics
- Cloud
- Gobierno del dato
- Storytelling
- Ingenieria de datos

### Heatmap curricular

Reemplaza el listado de tags por un **Mapa de capacidades curriculares** con profundidad estimada.

### Barras comparativas

Muestran brechas estrategicas como comparacion entre:

- curriculo actual
- demanda de mercado

### Timeline curricular

Ordena las senales de actualizacion en una secuencia para comite academico:

- Cobertura base
- Profundizacion
- Evidencia laboral Gold
- Comite academico

## Benchmark SNIES

El frontend intenta cargar programas relacionados mediante:

`GET /api/programs/related-universities/{program_id}`

Si el endpoint devuelve resultados, se muestran como ranking ejecutivo. Si no hay evidencia suficiente, el modulo muestra un estado vacio institucional sin inventar competidores.

## Inteligencia laboral

La evidencia laboral se muestra como exploratoria porque aun no debe alimentar el KPI institucional productivo sin pasar por:

bronze -> silver -> gold -> relevance_score -> release_gate

Esto mantiene coherencia con la gobernanza de datos definida para la plataforma.

## Trazabilidad curricular

La matriz tecnica sigue disponible como export secundario, pero ahora la pantalla principal muestra:

- Antes
- Despues
- Motivo e impacto

Los botones fueron renombrados:

- "Descargar DOCX actualizado" -> "Descargar"
- "Descargar matriz de trazabilidad" -> "Exportar trazabilidad"

## Archivos modificados

- `graduate_intelligence_platform/frontend/src/pages/MicrocurriculumDemoPage.tsx`
- `graduate_intelligence_platform/frontend/src/styles/index.css`

## Validacion ejecutada

Comandos:

- `npm run build`
- `python -m pytest tests`

Resultado:

- Build frontend exitoso.
- Suite de pruebas exitosa: 34 passed, 4 skipped.

## Riesgos pendientes

- La inteligencia laboral mostrada en esta vista es exploratoria hasta conectar vacantes Gold reales.
- El benchmark SNIES depende de la disponibilidad de resultados para el `specialization_id` seleccionado.
- La calidad del indicador de tendencia de empleabilidad mejorara cuando `alineacion_laboral` tenga soporte laboral Gold longitudinal.

## Criterio de aceptacion visual

La pantalla debe percibirse como:

- observatorio institucional
- producto de decision academica
- inteligencia curricular para comite
- narrativa ejecutiva de pertinencia laboral

No debe percibirse como:

- extractor NLP
- listado de keywords
- depurador de embeddings
- pantalla tecnica de backend
