# Program selector microcurriculum filter audit
## Summary
- Raw programs in `especializaciones`: **53**
- Programs visible after the filter: **27** canonical programs
- Raw rows removed from dashboard: **26** duplicate/variant rows
- Programs with official evidence sources: `vw_programa_skills` and `microcurriculum_program_contexts`
- No canonical program with processed microcurriculum evidence was removed; the excluded rows are duplicate or variant records from the raw catalog.

## Source of the listing
The program selector is fed by `dashboard_service.list_programs_base()`, which now delegates to `backend/repositories/programas_repository.py::fetch_program_rows_with_metrics()` and the Flask path in `app.py::get_programas()` now reuses the same shared source.

## Official source coverage
- vw_programa_skills: **27** distinct program ids
- microcurriculum_program_contexts: **3** distinct program ids

## Programs visible after the filter
- `108` Especializaci?n en Criminolog?a
- `107` Especialización en Administración y Gerencia de la Salud
- `82` Especialización en Alta Gerencia
- `97` Especialización en Derecho de la Empresa
- `100` Especialización en Derecho Digital
- `99` Especialización en Derechos Humanos
- `88` Especialización en Dirección Comercial y Ventas
- `90` Especialización en Dirección y Gestión de Proyectos
- `96` Especialización en Dirección y Gestión de Tecnologías de la Información
- `105` Especialización en Educación Inclusiva
- `102` Especialización en Educación y Orientación Familiar
- `104` Especialización en Gerencia Educativa
- `84` Especialización en Gerencia Financiera
- `95` Especialización en Gestión Ambiental y Energética
- `83` Especialización en Gestión de la Seguridad y Salud en el Trabajo
- `86` Especialización en Gestión Humana
- `98` Especialización en Gestión Pública
- `91` Especialización en Ingeniería de Software
- `92` Especialización en Inteligencia Artificial
- `85` Especialización en Inteligencia de Negocio
- `87` Especialización en Marketing Digital
- `101` Especialización en Neuropsicología y Educación
- `106` Especialización en Pedagogía y Docencia
- `89` Especialización en Revisoría Fiscal y Auditoría de Cuentas
- `93` Especialización en Seguridad Informática
- `103` Especialización en TIC para la Enseñanza
- `94` Especialización en Visual Analytics y Big Data

## Programs removed from the dashboard
- `26` especialización en administración y gerencia de la salud
- `1` especialización en alta gerencia
- `16` especialización en derecho de la empresa
- `19` especialización en derecho digital
- `18` especialización en derechos humanos
- `7` especialización en dirección comercial y ventas
- `9` especialización en dirección y gestión de proyectos
- `15` especialización en dirección y gestión de tecnologías de la información
- `24` especialización en educación inclusiva
- `21` especialización en educación y orientación familiar
- `23` especialización en gerencia educativa
- `3` especialización en gerencia financiera
- `14` especialización en gestión ambiental y energética
- `2` especialización en gestión de la seguridad y salud en el trabajo
- `5` especialización en gestión humana
- `17` especialización en gestión pública
- `10` especialización en ingeniería de software
- `11` especialización en inteligencia artificial
- `4` especialización en inteligencia de negocio
- `6` especialización en marketing digital
- `20` especialización en neuropsicología y educación
- `25` especialización en pedagogía y docencia
- `8` especialización en revisoría fiscal y auditoría de cuentas
- `12` especialización en seguridad informática
- `22` especialización en tic para la enseñanza
- `13` especialización en visual analytics y big data

## Affected endpoints
| Endpoint | Purpose | Source |
|---|---|---|
| `GET /api/programas` | FastAPI selector | graduate_intelligence_platform/backend/app/api.py::programs() -> dashboard_service.list_programs_base() |
| `GET /api/programas` | Flask selector | backend/routes/programas.py -> dashboard_service.list_programs_base() |
| `GET /api/bootstrap` | Executive summary bootstrap | graduate_intelligence_platform/backend/app/api.py -> programs() |
| `GET /api/dashboard/kpis` | Executive summary KPIs | graduate_intelligence_platform/backend/app/api.py -> programs() |
| `GET /api/dashboard/programa/{program_id}` | Program detail dashboard | graduate_intelligence_platform/backend/app/api.py -> program_by_id() -> programs() |
| `GET /api/programas/{program_id}/market-alignment` | Market alignment | graduate_intelligence_platform/backend/app/api.py -> build_program_market_alignment_report() |
| `GET /api/programas/{program_id}/skill-gaps` | Skill gaps | graduate_intelligence_platform/backend/app/api.py -> build_program_market_alignment_report() |
| `GET /api/programas/{program_id}/recommended-jobs` | Recommendations | graduate_intelligence_platform/backend/app/api.py -> build_program_market_alignment_report() |
| `GET /api/specializations` | Program selector / microcurriculum demo | graduate_intelligence_platform/backend/app/api.py -> _list_specializations() -> programs() |

## Corrected query
```sql
WITH allowed_programs AS (
    SELECT DISTINCT especializacion_id AS program_id
    FROM vw_programa_skills
    UNION
    SELECT DISTINCT specialization_id AS program_id
    FROM public.microcurriculum_program_contexts
), visible_programs AS (
    SELECT DISTINCT ON (lower(s.nombre))
        s.id AS especializacion_id,
        s.nombre AS nombre_especializacion,
        COALESCE(s.rol, '') AS rol
    FROM especializaciones s
    INNER JOIN allowed_programs ap ON ap.program_id = s.id
    ORDER BY lower(s.nombre),
        CASE WHEN COALESCE(s.source_url, '') <> '' OR COALESCE(s.plan_estudios, '') <> '' THEN 0 ELSE 1 END,
        CASE WHEN COALESCE(s.rol, '') <> '' THEN 0 ELSE 1 END,
        CASE WHEN s.nombre ~ '^[A-Z]' THEN 0 ELSE 1 END,
        s.id DESC
)
SELECT *
FROM visible_programs
ORDER BY nombre_especializacion;
```

## Validation
- `dashboard_service.list_programs_base()` returned **27** programs after the patch.
- The selector now excludes raw catalog variants that do not survive the canonical ranking or the official evidence filter.
