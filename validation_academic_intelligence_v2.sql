-- Academic Intelligence remediation validation
-- Run against Railway PostgreSQL after migration 024 and pipeline execution.

SELECT 'skill_normalization_mappings' AS table_name, COUNT(*) AS total_records FROM public.skill_normalization_mappings
UNION ALL
SELECT 'program_skill_gap', COUNT(*) FROM public.program_skill_gap
UNION ALL
SELECT 'program_market_pressure', COUNT(*) FROM public.program_market_pressure
UNION ALL
SELECT 'program_employability_index', COUNT(*) FROM public.program_employability_index
UNION ALL
SELECT 'program_risk_index', COUNT(*) FROM public.program_risk_index
UNION ALL
SELECT 'curriculum_simulations', COUNT(*) FROM public.curriculum_simulations
UNION ALL
SELECT 'skill_trend_forecast', COUNT(*) FROM public.skill_trend_forecast
UNION ALL
SELECT 'technology_forecasts', COUNT(*) FROM public.technology_forecasts
UNION ALL
SELECT 'company_forecasts', COUNT(*) FROM public.company_forecasts
UNION ALL
SELECT 'role_forecasts', COUNT(*) FROM public.role_forecasts
ORDER BY table_name;

SELECT
    COUNT(*) AS recommendation_rows,
    COUNT(*) FILTER (WHERE COALESCE(estimated_alignment_increase, 0) > 0) AS rows_with_alignment_increase,
    COUNT(*) FILTER (WHERE COALESCE(estimated_employability_gain, 0) > 0) AS rows_with_employability_gain,
    COUNT(*) FILTER (WHERE COALESCE(estimated_risk_reduction, 0) > 0) AS rows_with_risk_reduction
FROM public.recommendation_observatory;

SELECT
    COUNT(*) AS total_programs,
    COUNT(*) FILTER (WHERE risk_score >= 75) AS critical_programs,
    COUNT(*) FILTER (WHERE risk_score >= 50 AND risk_score < 75) AS observation_programs,
    COUNT(*) FILTER (WHERE risk_score < 50) AS aligned_programs
FROM public.program_intelligence;

SELECT
    entity_type,
    COUNT(*) AS total_records,
    COUNT(DISTINCT entity_name) AS distinct_entities
FROM public.market_forecasts
GROUP BY entity_type
ORDER BY entity_type;

SELECT
    COUNT(*) AS unmapped_gaps
FROM public.program_skill_gap
WHERE canonical_skill_id IS NULL OR COALESCE(TRIM(missing_skill), '') = '';

SELECT
    COUNT(*) AS duplicate_skill_normalizations
FROM (
    SELECT raw_skill_normalized, COUNT(*) AS total
    FROM public.skill_normalization_mappings
    GROUP BY raw_skill_normalized
    HAVING COUNT(*) > 1
) dup;
