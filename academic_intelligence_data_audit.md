# Academic Intelligence Data Audit

Scope: production Railway PostgreSQL audit for executive observatory readiness.

## Executive summary

- The production warehouse is populated and structurally sound for the executive layers.
- `program_intelligence` is now canonical and deduplicated: 26 records, 0 duplicate groups.
- Risk segmentation is present in the data layer: aligned=4, observation=12, critical=10.
- The two remaining empty executive surfaces are not caused by missing program records:
  - Forecast is narrow because all 45 rows are skill forecasts; there are no production rows for technology/company horizons.
  - Simulation is empty because `recommendation_observatory` does not persist `estimated_alignment_increase`, so the frontend cannot build a scenario payload.

## program_intelligence

- Total records: 26
- Duplicate groups: 0
- Duplicate rate: 0.0%
- Null percentages:
  - program_id: 0 (0.0%)
  - canonical_program_key: 0 (0.0%)
  - program_name: 0 (0.0%)
  - program_role: 0 (0.0%)
  - alignment_score: 0 (0.0%)
  - risk_score: 0 (0.0%)
  - risk_level: 0 (0.0%)
  - gap_count: 0 (0.0%)
  - confidence: 0 (0.0%)
  - generated_at: 0 (0.0%)
- Primary key / canonical mapping: `specializaciones.id -> program_intelligence.program_id`
- Risk distribution: aligned=4, observation=12, critical=10, zero_risk=0
- Alignment range: min=0.00, max=100.00, avg=51.30
- Risk range: min=18.74, max=63.74, avg=41.06

## curriculum_gap_observatory

- Total records: 23
- Duplicate groups: not computed for this table
- Duplicate rate: n/a
- Null percentages:
  - specialization: 0 (0.0%)
  - missing_skill: 0 (0.0%)
  - market_demand_score: 0 (0.0%)
  - curriculum_coverage_score: 0 (0.0%)
  - urgency_score: 0 (0.0%)
  - emergence_score: 0 (0.0%)
  - recommendation: 0 (0.0%)
  - generated_at: 0 (0.0%)
- Primary key / canonical mapping: `specializaciones.nombre/rol -> curriculum_gap_observatory.specialization`
- Missing skill mapping coverage: 3 mapped / 23 total, 20 gaps are still not mapped to the canonical `skills` table

## recommendation_observatory

- Total records: 13
- Duplicate groups: not computed for this table
- Duplicate rate: n/a
- Null percentages:
  - recommendation_type: 0 (0.0%)
  - target_role: 0 (0.0%)
  - target_company: 0 (0.0%)
  - recommendation_confidence: 0 (0.0%)
  - metric_period: 0 (0.0%)
  - generated_at: 0 (0.0%)
- Primary key / canonical mapping: `specializations.role / company demand -> recommendation_observatory.target_role/target_company`
- Scenario payload coverage: 13/13 rows do not expose `estimated_alignment_increase`, so the frontend simulation block cannot calculate impact from this table alone

## market_forecasts

- Total records: 45
- Duplicate groups: 0
- Duplicate rate: 0.0%
- Null percentages:
  - entity_type: 0 (0.0%)
  - entity_name: 0 (0.0%)
  - horizon_months: 0 (0.0%)
  - growth_velocity: 0 (0.0%)
  - forecast_confidence: 0 (0.0%)
  - market_phase: 0 (0.0%)
  - first_seen_at: 45 (100.0%)
  - last_seen_at: 45 (100.0%)
- Primary key / canonical mapping: `skills/technologies/companies/roles -> market_forecasts.entity_name`
- Forecast coverage by entity type: skill=45, technology=0, company=0, role=0
- This is why the technology/company forecast panes are empty in the executive UI.

## semantic_role_graph

- Total records: 2221
- Duplicate groups: 0
- Duplicate rate: 0.0%
- Null percentages:
  - source_role: 0 (0.0%)
  - target_role: 0 (0.0%)
  - similarity_score: 0 (0.0%)
  - transition_probability: 0 (0.0%)
  - cluster_affinity: 0 (0.0%)
  - centrality_score: 0 (0.0%)
- Primary key / canonical mapping: role families from jobs and transitions

## company_observatory

- Total records: 11
- Duplicate groups: not computed for this table
- Duplicate rate: n/a
- Null percentages:
  - company: 0 (0.0%)
  - dominant_stack: 0 (0.0%)
  - dominant_cluster: 0 (0.0%)
  - hiring_velocity: 0 (0.0%)
  - ai_adoption_score: 0 (0.0%)
  - cloud_maturity_score: 0 (0.0%)
  - bi_maturity_score: 0 (0.0%)
- Primary key / canonical mapping: `jobs.company -> company_observatory.company`

## Orphan and mapping checks

- program_intelligence missing program mapping: 0
- curriculum_gap_observatory missing specialization mapping: 0
- recommendation_observatory missing role/company mapping: 0
- market_forecasts missing entity mapping: 0
- semantic_role_graph missing endpoints: 0
- company_observatory missing company mapping: 0

## Why the key symptoms happen

- `risk_score` is **not** zero in the current production snapshot. If the UI displayed zeros earlier, that came from the stale materialized view that existed before the canonical `program_intelligence` table migration.
- No programs appear in observation/critical only in stale or filtered views. The current production snapshot contains observation=12 and critical=10, so the data layer supports those bands.
- The forecast section looks empty because production has only skill forecasts; there are no rows for `technology` or `company`, which are the categories the UI renders in separate columns.
- The simulation section is empty because `recommendation_observatory` does not persist `estimated_alignment_increase`, so the scenario builder returns `null` even though recommendations exist.

## Summary metrics

- `program_intelligence`: 26
- `curriculum_gap_observatory`: 23
- `recommendation_observatory`: 13
- `market_forecasts`: 45
- `semantic_role_graph`: 2221
- `company_observatory`: 11

