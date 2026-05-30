# Schema Comparison Matrix

This comparison is code-based and migration-based.  
I did **not** run a live cross-database schema diff in this environment, so the matrix below reflects:

- source DDL in `database/migrations/*.sql` and `database/enterprise_labor_intelligence_schema.sql`
- production FastAPI usage in `api/services.py` and repository layers
- target state implied by current Railway health checks and existing deployed tables

## Compatibility Summary

Legend:
- **Compatible** = source DDL and target expectations align from code analysis
- **Missing in target** = required by production code but currently not present in Railway observatory state
- **Present in target** = already observed in Railway health / production table set
- **View/materialized view** = supporting relation, not a table

| object | source schema / keys | target expectation | status | notes |
|---|---|---|---|---|
| `especializaciones` | `id SERIAL PK`, `nombre UNIQUE`, `descripcion`, `rol`, `facultad`, `nivel`, `estado`, `modalidad`, `campo_laboral`, `plan_estudios`, `general_text`, `source_url`, timestamps | Used by `/api/programas`, `/api/programas/{id}`, `/api/dashboard/programa/{id}` | Present in target | Core program table |
| `skills` | `id SERIAL PK`, `nombre UNIQUE`, `categoria`, `dominio`, `tipo`, `descripcion`, timestamps | Used by program and match bridges | Present in target | Core skill dictionary |
| `competencias` | `id SERIAL PK`, `nombre UNIQUE`, `categoria`, `dominio`, `descripcion`, timestamps | Used by `/api/programas/{id}` and dashboard context | Likely compatible | Direct curricular core |
| `herramientas` | `id SERIAL PK`, `nombre UNIQUE`, `categoria`, `dominio`, `descripcion`, timestamps | Used by program detail normalization | Likely compatible | Core curricular support table |
| `habilidades_blandas` | `id SERIAL PK`, `nombre UNIQUE`, `categoria`, `dominio`, `descripcion`, timestamps | Used by program detail normalization | Likely compatible | Core curricular support table |
| `especializacion_skills` | composite PK `(especializacion_id, skill_id)`, FK to `especializaciones` and `skills`, `confidence_score`, `source_document`, timestamp | Used by `/api/programas`, `/api/programas/{id}`, match bridge | Present / compatible | Critical bridge table |
| `especializacion_herramientas` | composite PK `(especializacion_id, herramienta_id)` | Used by `/api/programas/{id}` | Likely compatible | Bridge table |
| `especializacion_competencias` | composite PK `(especializacion_id, competencia_id)` | Used by `/api/programas/{id}` | Likely compatible | Bridge table |
| `especializacion_habilidades_blandas` | composite PK `(especializacion_id, habilidad_id)` | Used by `/api/programas/{id}` | Likely compatible | Bridge table |
| `empleos` | legacy/core job table with `id`, `portal`, `titulo`, `titulo_normalizado`, `empresa`, `ciudad`, `modalidad`, `salario`, `descripcion`, `seniority`, `sector`, `dominio`, `fecha_publicacion`, `url`, `hash_contenido`, `embedding`, `confidence_score`, `confidence_factors`, timestamps | Used by `vw_labor_program_job_matches` and fallback evidence engine | Present in target | Existing production table |
| `empleo_skills` | `id BIGSERIAL PK`, `empleo_id FK`, `skill_original`, `skill_normalized`, `skill_domain`, `tipo_skill`, `confianza_extraccion`, timestamp, `skill_id` FK added later | Used by match bridge and market evidence engine | Present / compatible | Critical match evidence table |
| `canonical_jobs` | canonicalized job warehouse table | Used by `vw_labor_program_job_matches` and search | Present in target | Existing production table |
| `silver_normalized_jobs` | normalized job warehouse table | Used by `vw_labor_program_job_matches` and evidence engine | Present in target | Existing production table |
| `gold_validated_jobs` | validated job warehouse table | Used by market evidence engine | Present in target | Existing production table |
| `labor_program_skill_matches` | `id BIGSERIAL PK`, `especializacion_id FK`, `job_id`, `skill_id FK`, `match_score`, `source`, `confidence`, timestamps, unique `(especializacion_id, job_id, skill_id, source)` | Used by `/api/dashboard/programa/{id}` match view and dashboard metrics | Present / compatible | Required for meaningful dashboard matches |
| `microcurriculum_program_contexts` | PK `specialization_id`, many JSONB context columns, `specialization_name`, `source_directory`, `documents_processed`, `confidence`, `real_market_gaps`, `strengthening_areas`, `labor_roles`, `benchmarking`, `scores`, `executive_narrative`, `raw_context`, timestamps | Used by `/api/programas/{id}` and `/api/dashboard/programa/{id}` | Missing in target | Must be materialized |
| `mv_dashboard_especializacion` | materialized view on `vw_dashboard_especializacion` | Used by `dashboard_service.list_programs_base` if present | Missing / stale | Recreate if absent |
| `vw_dashboard_especializacion` | view combining curricular counts + ML match metrics | Used by `dashboard_service.list_programs_base` fallback relation | Missing / stale | Recreate if absent |
| `vw_programa_skills` | view of `especializaciones` to `skills` | Used by `fetch_program_skill_rows` when present | Missing / optional | Compatibility helper |
| `vw_labor_program_job_matches` | job-program match bridge view | Used by `matches_repository.match_relation_name` preference chain | Missing / optional but recommended | Improves dashboard match quality |
| `vw_latest_ml_program_job_matches` | legacy ML match view | Used as fallback relation | Likely present | Legacy compatibility path |
| `observatory_metrics` | `id BIGSERIAL PK`, `metric_name`, `metric_category`, `metric_value`, `metric_period`, `confidence_score`, `source_payload`, `generated_at`, `updated_at`, unique `(metric_name, metric_period)` | Used by `/metrics` | Missing in target | Required observatory table |
| `curriculum_gap_observatory` | `specialization`, `missing_skill`, `market_demand_score`, `curriculum_coverage_score`, `urgency_score`, `emergence_score`, `recommendation`, `evidence`, timestamps, unique `(specialization, missing_skill)` | Used by `/curriculum-gaps` | Missing in target | Required observatory table |
| `recommendation_observatory` | `recommendation_type`, `target_role`, `target_company`, `recommendation_payload`, `recommendation_reasoning`, `recommendation_confidence`, `recommendation_evidence`, `metric_period`, timestamps, unique `(recommendation_type, target_role, target_company, metric_period)` | Used by `/recommendations` | Missing in target | Required observatory table |
| `semantic_role_graph` | `source_role`, `target_role`, `similarity_score`, `transition_probability`, `shared_skills`, `cluster_affinity`, `centrality_score`, `evidence`, unique `(source_role, target_role, metric_period)` | Used by `/semantic-roles` | Missing in target | Required observatory table |
| `company_observatory` | `company`, `dominant_stack`, `dominant_cluster`, `hiring_velocity`, `ai_adoption_score`, `cloud_maturity_score`, `bi_maturity_score`, `technology_maturity`, `top_skills`, `top_clusters`, `evidence`, unique `(company, metric_period)` | Used by `/company-intelligence` | Missing in target | Required observatory table |
| `emerging_technology_observatory` | `technology`, `emergence_score`, `growth_velocity`, `adoption_trend`, `forecast_confidence`, `source_payload`, unique `(technology, metric_period)` | Used by observatory layer | Missing in target | Required observatory table |
| `career_transitions` | `source_role`, `target_role`, `role_progression_probability`, `transition_skill_gaps`, `recommended_next_skills`, unique `(source_role, target_role)` | Used by `/career-paths` | Missing in target | Required observatory table |
| `market_forecasts` | `entity_type`, `entity_name`, `first_seen_at`, `last_seen_at`, `growth_velocity`, `forecast_confidence`, `market_phase`, `evidence`, unique `(entity_type, entity_name)` | Used by `/market-forecast` | Missing in target | Required observatory table |

## Tables that are good candidates for migration but not direct endpoint dependencies

These are useful for analytics / ML / future observability, but are not queried directly by the listed production endpoints:

- `microcurriculos`
- `microcurriculo_market_gaps`
- `labor_market_skill_universe`
- `occupational_skill_clusters`
- `specialization_curriculum_graph`
- `specialization_skill_affinity`
- `curriculum_market_gaps`
- `curriculum_recommendation_candidates`
- `company_profiles`
- `company_skill_affinity`
- `company_cluster_affinity`
- `company_trend_metrics`
- `semantic_role_clusters`
- `occupational_graph_edges`
- `emerging_skill_candidates`
- `job_embeddings`
- `skill_embeddings`
- `company_embeddings`
- `human_validation_feedback`
- `ml_prediction_explanations`

## Schema Risk Assessment

- Core curricular tables are aligned with the production API contract.
- Observatory tables are the primary missing layer in Railway.
- The dashboard match bridge is sensitive to `labor_program_skill_matches`, `empleo_skills`, and the dashboard/match views.
- No destructive schema change is recommended without a live schema diff against Railway.
