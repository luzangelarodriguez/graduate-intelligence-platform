# Microcurriculum Context Engine Phase 1

Fecha: 2026-05-25

## Objetivo

Hacer que el análisis de cada programa use microcurrículos reales y no métricas globales, mocks o textos genéricos.

Programa piloto:

```text
Especialización en Visual Analytics y Big Data
```

Fuente oficial:

```text
storage/test_microcurriculos/especialización en visual analytics y big data
```

## Documentos procesados

Se indexaron 10 documentos DOCX reales:

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

## Implementación

Archivos creados:

- `microcurriculum_context_engine.py`
- `database/migrations/009_microcurriculum_program_context.sql`
- `backend/repositories/microcurriculum_context_repository.py`

Archivos actualizados:

- `graduate_intelligence_platform/backend/app/api.py`

## Tablas

La migración `009` agrega:

- `microcurriculo_keywords`
- `microcurriculum_program_contexts`
- `microcurriculos.specialization_id`
- `microcurriculos.specialization_name`

Además reutiliza:

- `microcurriculos`
- `microcurriculo_asignaturas`
- `microcurriculo_skills`
- `microcurriculo_competencias`
- `microcurriculo_herramientas`
- `microcurriculo_plataformas`
- `microcurriculo_market_gaps`

## Resultado persistido en Railway

Contexto consolidado:

- specialization_id resuelto: `13`
- endpoint/backend canónico resuelto: `94`
- documentos procesados: `10`
- dominio detectado: `analitica`
- subdominio: `visual_analytics_big_data`
- tecnologías consolidadas: `37`
- brechas reales: `7`
- microcurrículos persistidos: `10`
- skills por microcurrículo persistidas: `61`

El repositorio backend resuelve contexto por:

1. `specialization_id`
2. nombre normalizado con `unaccent`

Esto evita perder contexto cuando existen duplicados/canónicos de una misma especialización.

## Narrativa generada

```text
El programa fue analizado a partir de 10 microcurrículos reales. Presenta una orientación fuerte hacia visualización de datos y tableros ejecutivos, tratamiento, integración y análisis de datos, analítica avanzada e inteligencia artificial aplicada.
```

## Roles laborales contextuales

- Data Analyst
- BI Specialist
- Analytics Engineer
- Data Visualization Consultant
- Business Intelligence Architect

## Brechas reales detectadas

- Databricks
- DataOps
- IA generativa
- MLOps
- Power Platform
- Snowflake
- Storytelling with Data

La regla aplicada fue: si una entidad se detecta en el microcurrículo, no se reporta como brecha real; se clasifica como área a fortalecer.

## Backend

`GET /api/programas/{id}` ahora devuelve, cuando existe:

- `microcurriculum_context`
- `skills_reales_microcurriculo`
- `competencias_reales_microcurriculo`
- `herramientas_reales_microcurriculo`
- `brechas_reales_microcurriculo`
- `areas_a_fortalecer`
- `roles_laborales_contextuales`
- `benchmarking_contextual`
- `narrativa_ia`

`GET /api/dashboard/programa/{id}` usa el mismo contexto para:

- KPIs
- brechas
- roles
- insight narrativo
- fuente contextual del programa

## Validación

Comandos ejecutados:

```powershell
python microcurriculum_context_engine.py --no-persist
python microcurriculum_context_engine.py
python -m pytest tests
```

Resultado:

```text
34 passed, 4 skipped
```

## Riesgos pendientes

- El benchmarking externo Coursera/edX/QS está representado como referencias curatoriales internas, no como extracción automática.
- Falta extender este indexado a las demás especializaciones.
- Algunos documentos incluyen términos técnicos transversales como `api`, `javascript`, `php` o `devops`; se mantienen porque aparecen en documentos reales del programa, pero no se promueven como brechas prioritarias.
- Se recomienda resolver encoding/mojibake en nombres históricos para evitar duplicados visuales.

## Próximo paso

Ejecutar el mismo pipeline por carpeta/programa y activar una vista de dashboard donde el selector siempre consulte primero `microcurriculum_program_contexts`.

