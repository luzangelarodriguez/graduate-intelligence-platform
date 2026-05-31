-- Executive AI validation for Railway PostgreSQL
-- Validate horizon-specific outputs, microcurriculum traceability and explanation coverage.

SELECT
  program_id,
  horizon_months,
  current_alignment_score,
  projected_alignment_score,
  projected_risk_score,
  projected_employability_gain,
  projected_gap_reduction,
  confidence_score
FROM curriculum_simulations
WHERE horizon_months IN (6, 12, 24)
ORDER BY program_id, horizon_months;

SELECT
  program_id,
  program_name,
  jsonb_typeof(microcurriculum_context) AS microcurriculum_context_type
FROM specializaciones
WHERE microcurriculum_context IS NOT NULL
LIMIT 50;

SELECT
  recommendation_id,
  recommendation_title,
  explanation,
  why_this_recommendation,
  confidence,
  model
FROM recommendation_observatory
WHERE estimated_alignment_increase IS NOT NULL
ORDER BY generated_at DESC NULLS LAST
LIMIT 50;

SELECT
  program_id,
  program_name,
  summary,
  why_at_risk,
  confidence,
  model
FROM program_intelligence
ORDER BY generated_at DESC NULLS LAST
LIMIT 50;
