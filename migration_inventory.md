# Migration Inventory - Production FastAPI / Dashboard

Source DB: `cliente_a_db`  
Target DB: Railway production PostgreSQL  
Scope: only tables and supporting relations actually queried by production FastAPI endpoints and dashboard code.

## Discovery Method

Code paths inspected:
- `api/main.py`
- `api/services.py`
- `backend/services/dashboard_service.py`
- `backend/repositories/programas_repository.py`
- `backend/repositories/matches_repository.py`
- `backend/repositories/skills_repository.py`
- `backend/repositories/microcurriculum_context_repository.py`
- `ml/labor/market_skill_intelligence_engine.py`
- `ml/labor/labor_market_skill_extraction_engine.py`
- `intelligence/observatory_pipeline.py`
- `intelligence/recommendation_api_engine.py`
- `intelligence/semantic_role_graph_engine.py`
- `intelligence/company_observatory_engine.py`
- `intelligence/market_forecasting_engine.py`

## Endpoint Dependency Report

| endpoint | service | repository / engine | table / relation |
|---|---|---|---|
| `GET /api/programas` | `api.services.list_programas_compatibility` | `backend.services.dashboard_service.list_programs_base` -> `backend.repositories.programas_repository.fetch_program_rows_with_metrics` | `mv_dashboard_especializacion` or `vw_dashboard_especializacion`; fallback to `especializaciones`, `especializacion_skills`, `especializacion_herramientas`, `especializacion_competencias`, `especializacion_habilidades_blandas`; ML metric relation may use `vw_labor_program_job_matches` / `vw_latest_ml_program_job_matches` |
| `GET /api/programas/{id}` | `api.services.get_programa_compatibility` | `backend.repositories.programas_repository.resolve_program_id`, `fetch_program_base_row`, `fetch_program_skill_rows`; `backend.repositories.microcurriculum_context_repository.fetch_program_context` | `especializaciones`, `especializacion_skills`, `especializacion_herramientas`, `especializacion_competencias`, `especializacion_habilidades_blandas`, `skills`, `microcurriculum_program_contexts`, optional `vw_programa_skills` |
| `GET /api/dashboard/programa/{id}` | `api.services.get_program_dashboard_compatibility` | `backend.repositories.matches_repository.match_relation_name`, `fetch_match_rows_for_program`; `backend.repositories.skills_repository.fetch_missing_market_skill_rows_for_program`; `backend.services.recommendation_service.recommended_program_cards` | `labor_program_skill_matches`, `empleo_skills`, `empleos`, `canonical_jobs`, `silver_normalized_jobs`, `skills`, `especializaciones`, `especializacion_skills`, `especializacion_herramientas`, `especializacion_competencias`, `especializacion_habilidades_blandas`, `microcurriculum_program_contexts`; relation preference: `vw_labor_program_job_matches` -> `vw_latest_ml_program_job_matches` -> `vw_match_empleo_especializacion_positivo` |
| `GET /metrics` | `api.services.list_observatory_metrics` | direct SQL | `observatory_metrics` |
| `GET /curriculum-gaps` | `api.services.list_curriculum_gaps` | direct SQL; fallback `ml.labor.market_skill_intelligence_engine.build_market_skill_intelligence_map` | `curriculum_gap_observatory`; fallback evidence path uses `bronze_empleos_raw`, `silver_empleos_normalized`, `gold_empleos_analytics`, `empleos`, `empleo_skills`, `skills` |
| `GET /recommendations` | `api.services.list_recommendations` | direct SQL; fallback `ml.labor.market_skill_intelligence_engine.build_market_skill_intelligence_map` | `recommendation_observatory`; fallback evidence path uses `bronze_empleos_raw`, `silver_empleos_normalized`, `gold_empleos_analytics`, `empleos`, `empleo_skills`, `skills` |
| `GET /emerging-skills` | `api.services.list_emerging_skills` | `ml.labor.market_skill_intelligence_engine.build_market_skill_intelligence_map` | fallback evidence path uses `bronze_empleos_raw`, `silver_empleos_normalized`, `gold_empleos_analytics`, `empleos`, `empleo_skills`, `skills` |
| `GET /semantic-roles` | `api.services.list_semantic_roles` | direct SQL | `semantic_role_graph` |
| `GET /company-intelligence` | `api.services.list_company_intelligence` | direct SQL | `company_observatory` |
| `GET /career-paths` | `api.services.list_career_paths` | direct SQL | `career_transitions` |
| `GET /market-forecast` | `api.services.list_market_forecast` | direct SQL | `market_forecasts` |

## Migration Inventory

### A. Required for Production

These relations are directly queried by production endpoints or by the production fallback path used by those endpoints.

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
- `canonical_jobs`
- `silver_normalized_jobs`
- `gold_validated_jobs`
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

Supporting relations that should be recreated in production if absent:

- `vw_programa_skills`
- `vw_dashboard_especializacion`
- `mv_dashboard_especializacion`
- `vw_labor_program_job_matches`
- `vw_latest_ml_program_job_matches`

### B. Optional

Useful for analytics, ML, or future observability, but not strictly required by the production endpoints listed above.

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

### C. Unused / Deprecated for this migration

These are crawler, audit, manifest, staging, or legacy artifacts that should not be migrated into Railway production as part of this scope.

- `labor_market_sources`
- `labor_extraction_runs`
- `labor_extraction_errors`
- `api_sources_registry`
- `api_discovery_runs`
- `api_request_logs`
- `api_response_snapshots`
- `api_extraction_metrics`
- `source_quality_metrics`
- `source_quality_history`
- `source_access_strategy`
- `source_sla_metrics`
- `source_governance`
- `source_lineage`
- `extraction_runs`
- `bronze_job_payloads`
- `skill_drift_events`
- `ml_evaluation_runs`
- `ml_model_registry`
- `microcurriculo_processing_runs`
- `microcurriculo_embeddings`
- `microcurriculo_keywords`
- `microcurriculo_asignaturas`
- `microcurriculo_skills`
- `microcurriculo_competencias`
- `microcurriculo_plataformas`
- `microcurriculo_herramientas`
- `source backup / manifest / temp / experimental tables`

## Executive Note

The production FastAPI contract is primarily driven by:
- curricular core tables,
- labor-program match bridge tables,
- observatory tables,
- microcurriculum program context,
- and the direct fallback evidence tables used by `market_skill_intelligence_engine`.

This migration inventory intentionally excludes scraper/audit/manifest tables even if they exist in the source database.
