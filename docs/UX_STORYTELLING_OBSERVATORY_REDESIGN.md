# UX Storytelling Observatory Redesign

## Nueva narrativa del producto

La experiencia del piloto cambia de un panel técnico de microcurrículos a un observatorio ejecutivo de inteligencia curricular. La lectura ahora avanza en seis pasos:

1. ¿Qué programa estamos analizando?
2. ¿Qué tan pertinente es hoy?
3. ¿Qué evidencia curricular existe?
4. ¿Qué demanda el mercado laboral?
5. ¿Cómo se compara frente a programas similares?
6. ¿Qué microcurrículo actualizado propone la IA?

El componente `AnalysisStoryline` organiza esta lectura y permite navegar por la historia estratégica sin mostrar todos los datos al mismo tiempo.

## Cambios visuales

- Recuperación del layout institucional con sidebar izquierdo fijo, header superior UNIR y navegación enterprise.
- Hero institucional con selector de especialización, estado del análisis, microcurrículos procesados y acciones principales.
- Navegación principal por Observatorio, Oferta académica, Mercado laboral, Benchmarking SNIES, Reescritura IA, Comité académico y Configuración.
- Reducción de tarjetas repetitivas y eliminación de chips como visualización principal.
- Uso de una paleta sobria basada en azul institucional, blanco, gris claro y negro moderado.
- Secciones amplias, jerarquía de lectura clara y componentes más cercanos a observatorios ejecutivos tipo QS, Power BI Executive y Gartner Insights.

## KPIs definitivos

El KPI principal aparece una sola vez:

- Índice de pertinencia curricular.

Los cinco KPIs accionables son:

- Cobertura curricular.
- Brechas críticas.
- Demanda laboral.
- Competitividad SNIES.
- Prioridad de actualización.

Cada KPI abre evidencia relacionada con barras de severidad, detalle curricular y lectura ejecutiva. Si un KPI no tiene dato consolidado, se mantiene como evidencia preliminar controlada.

## Visualizaciones implementadas

- Gauge premium del índice de pertinencia curricular.
- Radar de capacidades curriculares con Recharts: Visual Analytics, Big Data, IA aplicada, Gobierno del dato, Cloud Analytics y Storytelling.
- Barras comparativas: currículo actual vs demanda laboral.
- Tendencia laboral con línea de demanda vs cobertura curricular.
- Bubble chart de demanda, cobertura y volumen relativo de capacidades.
- Flujo skill-mercado para conectar capacidades, roles y outcomes.
- Heatmap de profundidad curricular: tecnologías, metodologías y competencias frente a mención, práctica, evaluación y proyecto aplicado.
- Ranking de benchmarking SNIES con posición competitiva, score comparativo, ciudad, modalidad y gráfico horizontal premium.
- Vista de reescritura tipo documento académico: microcurrículo original, microcurrículo propuesto y justificación institucional.
- Trazabilidad de transformación curricular con timeline ejecutivo, sección modificada, cambio aplicado, razón académica, evidencia laboral e impacto esperado.

## Tratamiento de datos laborales

Cuando el backend no entrega una capa Gold consolidada, la interfaz no muestra errores ni mensajes de ausencia. Usa el estado:

`Señal laboral exploratoria`

La explicación visible es:

`Esta lectura se basa en capacidades ocupacionales y señales preliminares. La consolidación Gold se encuentra en fase de integración.`

Los roles y capacidades de fallback están acotados al piloto de Visual Analytics y Big Data: Data Analyst, BI Analyst, Data Visualization Specialist, Data Engineer, Analytics Consultant, Business Intelligence Specialist, Power BI, SQL, Python, ETL, Data Governance, Tableau, Cloud Analytics y Storytelling with Data.

## Tratamiento SNIES

La sección de benchmarking usa programas relacionados cuando el backend los entrega. Si no hay datos suficientes, utiliza una referencia comparativa inicial para no romper la experiencia visual ni presentar bloques vacíos.

La interfaz evita mensajes como `pendiente`, `sin evidencia`, `undefined`, `null` o `0 datos`. En su lugar usa etiquetas ejecutivas como `Referencia comparativa inicial`, `Fuente en validación` o `Evidencia preliminar`.

## Flujo de reescritura curricular

La función principal es `Microcurrículo actualizado propuesto`. El flujo muestra:

- Microcurrículo original.
- Microcurrículo propuesto.
- Cambios clave.
- Justificación institucional.
- Evidencia laboral.
- Descarga con botón `Descargar`.
- Exportación secundaria de trazabilidad.

La propuesta se presenta como documento académico revisable por comité, no como recomendación genérica.

## Pendientes reales para producción

- Integrar señal laboral Gold definitiva cuando el pipeline de vacantes esté consolidado.
- Reemplazar la referencia SNIES inicial por una fuente oficial normalizada y versionada.
- Añadir pruebas visuales automatizadas para los estados de análisis, propuesta generada y fallback.
- Definir permisos por rol para comité académico, administrador institucional y analista curricular.
- Conectar la descarga de informe ejecutivo a un generador formal PDF/DOCX institucional si se requiere evidencia firmable.
