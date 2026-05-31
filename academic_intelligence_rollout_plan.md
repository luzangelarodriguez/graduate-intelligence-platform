# Academic Intelligence Remediation Rollout Plan

## Phase 1: Schema readiness
- Apply `024_academic_intelligence_remediation.sql` to Railway PostgreSQL.
- Verify that the new tables exist:
  - `skill_normalization_mappings`
  - `program_skill_gap`
  - `program_market_pressure`
  - `program_employability_index`
  - `program_risk_index`
  - `skill_trend_forecast`
  - `technology_forecasts`
  - `company_forecasts`
  - `role_forecasts`
  - `curriculum_simulations`

## Phase 2: Data normalization
- Run the intelligence pipeline with persistence enabled.
- Canonicalize skills from:
  - `curriculum_gap_observatory`
  - `recommendation_observatory`
  - market forecasts
  - program-level signals
- Persist mappings into `skill_normalization_mappings` and `skill_aliases`.

## Phase 3: Simulation materialization
- Recompute curriculum impact simulations for all analyzed programs.
- Persist:
  - `program_risk_index`
  - `program_employability_index`
  - `program_market_pressure`
  - `curriculum_simulations`

## Phase 4: Forecast expansion
- Expand the forecast layer to:
  - skills
  - technologies
  - companies
  - roles
- Persist into:
  - `market_forecasts`
  - `skill_trend_forecast`
  - `technology_forecasts`
  - `company_forecasts`
  - `role_forecasts`

## Phase 5: API exposure
- Expose the new endpoints in FastAPI:
  - `GET /critical-programs`
  - `GET /curriculum-simulator`
  - `GET /forecast-summary`
- Keep all existing routes unchanged.

## Phase 6: Validation
- Execute `validation_academic_intelligence_v2.sql`.
- Verify:
  - skill mappings are populated
  - simulation rows exist for every program
  - forecast coverage includes skill, technology, company, and role
  - recommendations expose alignment/employability/risk impact fields

## Rollback
- Revert migration `024` only if the schema change must be removed.
- Otherwise, disable the new pipeline steps and keep the new tables in place.
- Existing dashboards and API routes remain backward compatible throughout the rollout.
