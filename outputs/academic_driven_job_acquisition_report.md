# Academic-Driven Job Acquisition Report

## Scope

This report covers the new shared academic-driven labor search layer added in the backend of `graduate_intelligence_platform`.

Implemented surface:

- `backend/app/academic_job_acquisition.py`
- `backend/app/api.py` route: `GET /api/labor/search-intelligence`

The goal is to replace static job keywords with search plans derived from:

- microcurriculum signals
- program and specialization metadata
- curriculum skills and topics
- market skill intelligence
- curriculum gap maps
- occupational cluster signals

## Diagnosis

The repository already had strong academic intelligence sources, but search acquisition was not centralized.

Existing reusable sources in code:

- program base rows from `dashboard_service.list_programs_base`
- program skill rows from `programas_repository.fetch_program_skill_rows`
- program context from `microcurriculum_context_repository.fetch_program_context`
- related virtual programs from `programas_repository.fetch_related_virtual_programs`
- market skill intelligence from `ml.labor.market_skill_intelligence_engine`
- curriculum gap intelligence from `ml.curriculum.curriculum_market_gap_engine`
- occupational clusters from `ml.clustering.labor_cluster_engine`

Before this change, the search layer remained portal-specific and static in spirit. The new backend layer now generates a reusable acquisition plan from academic evidence and market signals.

## Programs Analyzed

Smoke-tested from the local academic blueprint in code:

- Programs analyzed: `36`
- Specializations analyzed: `36`
- Microcurricula analyzed: `0` in the synthetic smoke test

Important note:

- In the live API route, programs are enriched with `microcurriculum_context` when available.
- The smoke test used the local blueprint because it is deterministic and does not require database access.

## Microcurricula and Specializations

The generator consumes:

- program name
- faculty
- curriculum skills
- curriculum topics
- microcurriculum context when present
- market gap terms
- occupational clusters

Specialization coverage is not limited to Data & BI. The role templates include business, technology, law, education, health, and criminology/security signals.

## Skills and Tools Extracted

Extracted from the academic layer and expanded through market signals:

- skills extracted: `123` unique terms in the smoke-tested bundle
- tools extracted: derived from the skill catalog and microcurriculum/tool signals

Representative sources:

- curriculum skills
- curriculum topics
- technical skills from microcurricula
- transversal skills from microcurricula
- market skills
- missing market skills
- strengthening areas
- occupational cluster terms

## Keywords Generated

The shared generator now emits keywords from multiple layers:

1. Curriculum keywords
2. Microcurriculum keywords
3. Market skill intelligence
4. Curriculum gap signals
5. Occupational cluster signals
6. Domain terms derived from the program faculty and domain

Smoke-test result:

- keywords generated: `123`

## Cargos Generados

The generator now expands role discovery beyond static data roles.

Representative role families:

- Data Analyst
- Business Intelligence Analyst
- Power BI Developer
- Analytics Consultant
- Data Scientist
- Machine Learning Engineer
- AI Engineer
- MLOps Engineer
- Software Engineer
- Data Engineer
- BI Developer
- Cloud Engineer
- Compliance Analyst
- Risk Analyst
- Legal Analyst
- Instructional Designer
- Learning Analytics Specialist
- Health Manager
- Patient Safety Specialist
- Criminal Intelligence Analyst
- Investigative Analyst

Smoke-test result:

- roles generated: `43`

## Crawlers Integrated

The repository does not contain the crawler implementations themselves. To avoid violating the scope restriction, the integration was implemented as a shared search plan that external crawlers can consume.

Supported crawler targets in the generated plan:

- LinkedIn
- Elempleo
- Ticjob
- Indeed
- Jooble
- Hireline
- FindJobIT
- Criminology crawlers

Each target receives a normalized source payload with:

- `keywords`
- `roles`
- `families`
- `query`
- `search_terms` where portal-friendly
- `max_jobs`
- `max_pages`
- `mode`

## New Search Modes

Implemented modes:

- `focused`
- `academic_alignment`
- `market_discovery`

Behavior:

- `focused`: manual keywords plus core curriculum terms
- `academic_alignment`: curriculum, microcurriculum, and academic context
- `market_discovery`: adds market signals, cluster expansion, and discovery terms

## Incremento Esperado de Cobertura

The new generator is expected to increase coverage because it:

- expands search beyond static Data & BI keywords
- adds role families for non-data programs
- captures academic terminology that portals use in job ads
- increases recall for adjacent occupations
- enables discovery of emerging skills and new job families

Expected impact:

- higher coverage for technology programs
- better capture of business, finance, HR, legal, education, health, operations, marketing, public sector, security, and criminology roles
- better matching input for `jobs` and `job_skills`

## Risks

### LinkedIn blocking risk

Medium to high. Wider query expansion and multi-page discovery increase the chance of throttling or checkpointing.

Mitigations:

- source-specific payloads
- query capping
- mode-based `max_pages` and `max_jobs`
- reuse of a shared generator instead of ad hoc search explosion

### Duplicate risk

Medium. Broader search plans can overlap across portals and roles.

Mitigations:

- deduplicated keyword and role sets
- mode-aware query shaping
- source-specific normalization

### Curriculum drift risk

Market discovery can drift away from academic relevance if not reviewed against gap maps and microcurriculum context.

Mitigations:

- keep `academic_alignment` as the default
- use `market_discovery` only as an expansion layer
- audit the resulting plan before production crawls

## ML Integration

The generated acquisition plan improves upstream inputs for:

- `jobs`
- `job_skills`
- curriculum matching
- gap analysis
- occupational clustering
- recommendations

The new layer is compatible with existing ML signals because it reuses the same academic and market vocabulary used by the platform.

## SNIES and Microcurricula Integration

The generator uses the same academic primitives already exposed by the platform:

- program base data
- specialization metadata
- microcurriculum context
- curriculum skills
- curriculum topics
- program-related virtual mappings

This makes SNIES and microcurriculum evidence first-class inputs to labor acquisition.

## Code Adjusted

Added:

- `backend/app/academic_job_acquisition.py`

Updated:

- `backend/app/api.py`

New API:

- `GET /api/labor/search-intelligence`

## Validation

Executed successfully:

- `python -m py_compile backend/app/academic_job_acquisition.py backend/app/api.py`
- runtime smoke test of `build_academic_job_acquisition_intelligence(build_programs())`

Smoke-test outputs:

- programs analyzed: `36`
- microcurricula analyzed: `0`
- keywords generated: `123`
- roles generated: `43`

## Recommendation

Use `academic_alignment` as the default mode for all portals.

Use `market_discovery` only when:

- coverage is stagnating
- new occupational families need discovery
- the plan has been reviewed against curricular relevance

