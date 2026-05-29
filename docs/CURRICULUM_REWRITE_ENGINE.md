# Curriculum Rewrite Engine

## Objetivo

El motor de reescritura curricular transforma el analisis de microcurriculos en un producto institucional: un nuevo microcurriculo propuesto, en DOCX, que conserva la estructura original y actualiza las secciones pedagogicas segun evidencia de pertinencia laboral.

## Flujo Funcional

1. Localiza microcurriculos por especializacion.
2. Extrae texto desde PDF, DOCX o TXT.
3. Mapea secciones institucionales.
4. Clasifica secciones como conservar, actualizar o profundizar.
5. Reescribe solo secciones permitidas.
6. Exporta un DOCX actualizado por asignatura.
7. Genera matriz de trazabilidad en `outputs/curriculum_change_traceability.csv`.

## Secciones Conservadas

No se modifican automaticamente:

- PROGRAMA ACADEMICO
- DENOMINACION DE LA ASIGNATURA
- SEMESTRE
- CREDITOS/HORAS
- TIPO DE ASIGNATURA
- EVALUACION Y CALIFICACION

## Secciones Reescritas O Profundizadas

- DESCRIPCION DE LA ASIGNATURA
- RESULTADOS DE APRENDIZAJE
- CONTENIDO TEMATICO
- ACTIVIDADES FORMATIVAS
- MEDIOS EDUCATIVOS
- PERFIL DEL DOCENTE DE LA ASIGNATURA

## Reglas De Conservacion

- Si el contenido sigue siendo pertinente, se conserva.
- Si el contenido es pertinente pero debil, se profundiza.
- Si falta una competencia critica de mercado, se incorpora como actualizacion curricular.
- Si una tecnologia puede estar desactualizada, se marca como reemplazo sugerido en trazabilidad.
- No se eliminan contenidos sin dejar trazabilidad.

## Piloto Visual Analytics Y Big Data

Ruta conectada:

`storage/test_microcurriculos/especialización en visual analytics y big data/`

Documentos procesados en validacion local: `10`.

Salidas generadas:

- `outputs/rewritten_microcurricula/Microcurriculo_Actualizado_*.docx`
- `outputs/rewritten_microcurricula/Resumen_Cambios_Visual_Analytics_Big_Data.md`
- `outputs/curriculum_change_traceability.csv`

## Ejemplos Antes/Despues

### Visualizacion Interactiva

Antes: contenidos generales de visualizacion y herramientas.

Despues: se profundiza en storytelling with data, dashboards ejecutivos, criterios UX, Power BI/Tableau y comunicacion de hallazgos.

### Tecnicas De Inteligencia Artificial

Antes: fundamentos y tecnicas de IA.

Despues: se refuerza machine learning aplicado, validacion de modelos, interpretabilidad, etica y notebooks reproducibles.

### Gobierno Del Dato

Antes: enfoque general en gestion de datos.

Despues: se incorpora calidad, linaje, seguridad, data stewardship y gobierno del dato.

### Procesado Masivo De Datos

Antes: fundamentos de procesamiento y big data.

Despues: se profundiza en Spark, cloud analytics, lakehouse, Databricks y procesamiento distribuido.

## Endpoints

- `POST /api/microcurriculum/rewrite`
- `POST /api/microcurriculum/specialization/{specialization_id}/rewrite`
- `GET /api/microcurriculum/rewrite/{rewrite_id}/download`

## Riesgos

- El mapeo de secciones depende de la calidad del formato DOCX original.
- La reescritura actual es deterministica y conservadora; no reemplaza revision de comite academico.
- No se deben modificar creditos, horas, semestre ni porcentajes salvo sugerencia explicita validada por humanos.

## Uso Recomendado

1. Analizar la especializacion.
2. Generar microcurriculos actualizados.
3. Revisar la matriz de trazabilidad.
4. Descargar DOCX por asignatura.
5. Presentar versiones propuestas a comite academico.

