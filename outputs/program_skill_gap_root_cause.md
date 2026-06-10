# Program skill gap root cause

## Problem statement
`vw_program_skill_gaps` was building academic gaps from `vw_match_empleo_especializacion_positivo` without constraining the market skills to the same disciplinary domain as the program.

That allowed cross-domain positive matches to inject foreign skills into education and health programs.

## Current pre-fix logic
```sql
WITH program_skill_keys AS (
    SELECT DISTINCT
        especializacion_id,
        skill_key
    FROM public.vw_programa_skills
),
market_skill_hits AS (
    SELECT
        m.especializacion_id AS program_id,
        s.nombre AS skill,
        COUNT(DISTINCT m.empleo_id)::int AS gap_frequency
    FROM public.vw_match_empleo_especializacion_positivo m
    INNER JOIN public.empleo_skills es
        ON es.empleo_id = m.empleo_id
    INNER JOIN public.skills s
        ON s.id = es.skill_id
    LEFT JOIN program_skill_keys psk
        ON psk.especializacion_id = m.especializacion_id
       AND psk.skill_key = lower(unaccent(COALESCE(s.nombre, '')))
    WHERE psk.skill_key IS NULL
    GROUP BY m.especializacion_id, s.nombre
)
SELECT
    program_id,
    skill,
    gap_frequency
FROM market_skill_hits;
```

## Join chain producing contamination
1. `vw_match_empleo_especializacion_positivo` contributes positive job-program pairs.
2. `public.empleo_skills` expands each matched job into its skill set.
3. `public.skills` resolves the raw skill names.
4. The only exclusion is whether the skill already exists in `vw_programa_skills`.
5. There is no `program_domain = job_domain` guard, so cross-domain jobs leak their skills into academic gaps.

## Domains contaminating education and health
The contaminated skill inventory for the audited programs was dominated by skills coming from other domains, mainly:
- `artificial_intelligence`
- `data_analytics`
- `software_engineering`
- `cloud_infrastructure`
- `devops_platform`
- `cybersecurity`
- `business_management`

## Evidence from the live warehouse before the fix
Audited programs:
- 102 `Especializacion en Educacion y Orientacion Familiar`
- 103 `Especializacion en TIC para la Ensenanza`
- 104 `Especializacion en Gerencia Educativa`
- 106 `Especializacion en Pedagogia y Docencia`
- 83 `Especializacion en Gestion de la Seguridad y Salud en el Trabajo`
- 107 `Especializacion en Administracion y Gerencia de la Salud`

Before the fix these six programs produced **212** contaminated gap rows.

Examples that should not appear as academic gaps for those programs unless they come from same-domain jobs:
- `AI`
- `APIs`
- `Azure`
- `AWS`
- `ELT`
- `MLflow`
- `pandas`
- `Python`
- `scikit-learn`
- `dashboarding`
- `BI`
- `Power BI`
- `SQL`
- `GCP`
- `data governance`
- `privacy`
- `executive reporting`
- `Oracle`
- `PL/SQL`
- `ITIL`
- `Scrum`
- `Kanban`
- `compliance`

## Root cause
The view was using market skills from all positive matches, not only same-domain positive matches.

## Fix applied
Restrict the source set inside `vw_program_skill_gaps` to rows where:
```sql
m.program_domain = m.job_domain
```

This keeps only same-domain positive matches as the source for academic gaps.

## Dependent view
`vw_program_market_alignment` only consumes `vw_program_skill_gaps` for its `missing_skills` payload, so rebuilding that view is sufficient for the visible dashboard fix.
