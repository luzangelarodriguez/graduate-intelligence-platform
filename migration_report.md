# Migration Report - Production Endpoint Compatibility

## Executive Summary

The production FastAPI layer is currently driven by:

- curricular core tables
- program-to-market match bridge tables and views
- observatory tables
- microcurriculum program context

The Railway backend already exposes the production API contract, but the observatory layer is missing or incomplete in the target database. That is why the dashboard can still show empty observability values even when the core program endpoints work.

This migration plan intentionally excludes:

- crawler tables
- audit logs
- manifests
- staging / temp tables
- experimental / backup tables

## Discovery Outcome

### Direct endpoint dependencies

- `/api/programas`
- `/api/programas/{id}`
- `/api/dashboard/programa/{id}`
- `/metrics`
- `/curriculum-gaps`
- `/recommendations`
- `/emerging-skills`
- `/semantic-roles`
- `/company-intelligence`
- `/career-paths`
- `/market-forecast`

### Production tables required by code

Most critical:

- `especializaciones`
- `skills`
- `competencias`
- `herramientas`
- `habilidades_blandas`
- `especializacion_skills`
- `especializacion_herramientas`
- `especializacion_competencias`
- `especializacion_habilidades_blandas`
- `empleos`
- `empleo_skills`
- `labor_program_skill_matches`
- `microcurriculum_program_contexts`
- `observatory_metrics`
- `curriculum_gap_observatory`
- `recommendation_observatory`
- `semantic_role_graph`
- `company_observatory`
- `emerging_technology_observatory`
- `career_transitions`
- `market_forecasts`

Supporting relations:

- `vw_programa_skills`
- `vw_dashboard_especializacion`
- `mv_dashboard_especializacion`
- `vw_labor_program_job_matches`
- `vw_latest_ml_program_job_matches`

## Inventory Classification

### A. Required for Production

The migration inventory in `migration_inventory.md` marks the following as category A:

- core curricular tables
- job / match bridge tables
- program context table
- observatory tables
- career / forecast tables
- supporting dashboard views

### B. Optional

Useful for ML / future observability, but not required by the listed production endpoints.

### C. Unused / Deprecated

Crawler, audit, manifest, backup, experimental, and staging tables are excluded from migration scope.

## Schema Compatibility

### What is known

- The production API schemas are aligned with the source DDL for the required tables.
- The observatory tables are defined in the migration set but were not present in the current Railway observability state.
- The match bridge (`labor_program_skill_matches` and `vw_labor_program_job_matches`) is the critical dependency for meaningful dashboard program matches.

### What is not live-validated here

I did **not** run a live cross-database schema diff in this environment, so I cannot claim a byte-for-byte source vs target schema match.

The generated `schema_comparison.md` therefore marks target presence/absence from code and observed production state, not from a live introspection dump.

## Migration Strategy

The generated `migration.sql` follows these rules:

- idempotent `CREATE TABLE IF NOT EXISTS` for observatory / missing support tables
- `CREATE OR REPLACE VIEW` for compatibility views
- `INSERT ... SELECT ... ON CONFLICT DO UPDATE` for data movement
- no `DELETE`
- no destructive drops

## Validation Strategy

The generated `validation.sql` covers:

- row counts
- distinct / PK validation
- orphan detection
- duplicate detection
- executive rollup counts

## Expected Production Outcome

After loading the approved category A objects, Railway production should stop returning empty observability payloads for:

- skills
- companies
- semantic roles
- recommendations
- curriculum gaps
- forecast signals

and the dashboard should be able to render real production data instead of zero-state placeholders.

## Notes for Execution

Recommended order:

1. validate live target schema
2. apply `migration.sql`
3. run `validation.sql`
4. compare source vs target counts
5. refresh materialized dashboard view

No migration was executed automatically by this task.
