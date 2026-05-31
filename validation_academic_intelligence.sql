-- Academic Intelligence Production Validation
-- Run against Railway PostgreSQL

-- 1) Core row counts
SELECT 'program_intelligence' AS table_name, COUNT(*) AS total_records FROM program_intelligence;
SELECT 'curriculum_gap_observatory' AS table_name, COUNT(*) AS total_records FROM curriculum_gap_observatory;
SELECT 'recommendation_observatory' AS table_name, COUNT(*) AS total_records FROM recommendation_observatory;
SELECT 'market_forecasts' AS table_name, COUNT(*) AS total_records FROM market_forecasts;
SELECT 'semantic_role_graph' AS table_name, COUNT(*) AS total_records FROM semantic_role_graph;
SELECT 'company_observatory' AS table_name, COUNT(*) AS total_records FROM company_observatory;

-- 2) program_intelligence distribution
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE COALESCE(risk_score, 0) = 0) AS zero_risk,
    COUNT(*) FILTER (WHERE COALESCE(alignment_score, 0) >= 70) AS aligned,
    COUNT(*) FILTER (WHERE COALESCE(alignment_score, 0) >= 50 AND COALESCE(alignment_score, 0) < 70) AS observation,
    COUNT(*) FILTER (WHERE COALESCE(alignment_score, 0) < 50) AS critical,
    MIN(risk_score) AS min_risk,
    MAX(risk_score) AS max_risk,
    AVG(risk_score) AS avg_risk,
    AVG(alignment_score) AS avg_alignment
FROM program_intelligence;

-- 3) Duplicate checks
SELECT canonical_program_key, COUNT(*) AS duplicate_count
FROM program_intelligence
GROUP BY canonical_program_key
HAVING COUNT(*) > 1;

SELECT entity_type, entity_name, COALESCE(horizon_months, 12) AS horizon_months, COUNT(*) AS duplicate_count
FROM market_forecasts
GROUP BY entity_type, entity_name, COALESCE(horizon_months, 12)
HAVING COUNT(*) > 1;

SELECT source_role, target_role, COUNT(*) AS duplicate_count
FROM semantic_role_graph
GROUP BY source_role, target_role
HAVING COUNT(*) > 1;

-- 4) Null percentage checks
SELECT 'program_intelligence' AS table_name, 'program_name' AS column_name, ROUND(100.0 * COUNT(*) FILTER (WHERE program_name IS NULL) / NULLIF(COUNT(*), 0), 2) AS null_pct FROM program_intelligence
UNION ALL
SELECT 'program_intelligence', 'risk_score', ROUND(100.0 * COUNT(*) FILTER (WHERE risk_score IS NULL) / NULLIF(COUNT(*), 0), 2) FROM program_intelligence
UNION ALL
SELECT 'curriculum_gap_observatory', 'missing_skill', ROUND(100.0 * COUNT(*) FILTER (WHERE missing_skill IS NULL) / NULLIF(COUNT(*), 0), 2) FROM curriculum_gap_observatory
UNION ALL
SELECT 'recommendation_observatory', 'recommendation_confidence', ROUND(100.0 * COUNT(*) FILTER (WHERE recommendation_confidence IS NULL) / NULLIF(COUNT(*), 0), 2) FROM recommendation_observatory
UNION ALL
SELECT 'market_forecasts', 'first_seen_at', ROUND(100.0 * COUNT(*) FILTER (WHERE first_seen_at IS NULL) / NULLIF(COUNT(*), 0), 2) FROM market_forecasts
UNION ALL
SELECT 'market_forecasts', 'last_seen_at', ROUND(100.0 * COUNT(*) FILTER (WHERE last_seen_at IS NULL) / NULLIF(COUNT(*), 0), 2) FROM market_forecasts;

-- 5) Orphan / mapping validation
SELECT COUNT(*) AS orphan_programs
FROM program_intelligence p
LEFT JOIN especializaciones e ON e.id = p.program_id
WHERE e.id IS NULL;

SELECT COUNT(*) AS orphan_gaps
FROM curriculum_gap_observatory c
LEFT JOIN especializaciones e
  ON lower(unaccent(coalesce(e.nombre, ''))) = lower(unaccent(coalesce(c.specialization, '')))
WHERE e.id IS NULL;

SELECT COUNT(*) AS missing_skill_mappings
FROM curriculum_gap_observatory c
WHERE NOT EXISTS (
    SELECT 1
    FROM skills s
    WHERE lower(unaccent(coalesce(s.nombre, ''))) = lower(unaccent(coalesce(c.missing_skill, '')))
);

SELECT COUNT(*) AS unmapped_skill_forecasts
FROM market_forecasts m
WHERE m.entity_type = 'skill'
  AND NOT EXISTS (
      SELECT 1
      FROM skills s
      WHERE lower(unaccent(coalesce(s.nombre, ''))) = lower(unaccent(coalesce(m.entity_name, '')))
  );

-- 6) Forecast coverage by entity type
SELECT entity_type, COUNT(*) AS total
FROM market_forecasts
GROUP BY entity_type
ORDER BY total DESC, entity_type ASC;

-- 7) Scenario readiness
SELECT
    COUNT(*) AS total_recommendations,
    COUNT(*) FILTER (WHERE recommendation_payload ? 'estimated_alignment_increase') AS with_alignment_increase,
    COUNT(*) FILTER (WHERE recommendation_payload ? 'recommended_skills') AS with_skills_payload
FROM recommendation_observatory;

-- 8) Recommendation coverage by type
SELECT recommendation_type, COUNT(*) AS total
FROM recommendation_observatory
GROUP BY recommendation_type
ORDER BY total DESC, recommendation_type ASC;

