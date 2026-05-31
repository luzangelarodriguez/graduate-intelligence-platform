# Remediation Plan

1. Backfill and enforce canonical program keys in `program_intelligence` and re-run the intelligence pipeline.
2. Add stronger negative-pressure features into the curriculum-risk model from curriculum gaps, emerging technology pressure, and forecasted company demand.
3. Persist forecast horizon coverage explicitly and ensure the UI requests only horizons that exist in production.
4. Add scenario simulator persistence so the executive view can render actual projected-alignment values instead of empty state; today the recommendation table lacks `estimated_alignment_increase`.
5. Extend mapping tables for recommendations and curriculum gaps so every record points to a valid program or canonical specialization.
6. Add a dedicated validation job that fails the pipeline when duplicate rates or orphan rates exceed thresholds.
7. Refresh the executive observatory after each pipeline run so the UI never renders stale zero states.

## Suggested thresholds
- Duplicate rate: <= 1%
- Null rate on core identity fields: <= 2%
- Orphan rate: 0% for program mappings
- Forecast coverage: at least one active horizon for each major entity type
- Scenario readiness: recommendations should expose `estimated_alignment_increase` or an equivalent projection field
