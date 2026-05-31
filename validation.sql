-- Validation SQL for source vs target comparison.
-- Run the source section against `cliente_a_db`
-- and the target section against Railway production PostgreSQL.
-- For cross-db comparison, export results to CSV and compare externally,
-- or stage source tables into a `source_snapshot` schema in the target DB.

-- ============================================================
-- 1) Source counts
-- ============================================================

-- Specialization core
SELECT 'especializaciones' AS table_name, COUNT(*) AS source_count FROM public.especializaciones;
SELECT 'skills' AS table_name, COUNT(*) AS source_count FROM public.skills;
SELECT 'competencias' AS table_name, COUNT(*) AS source_count FROM public.competencias;
SELECT 'herramientas' AS table_name, COUNT(*) AS source_count FROM public.herramientas;
SELECT 'habilidades_blandas' AS table_name, COUNT(*) AS source_count FROM public.habilidades_blandas;
SELECT 'especializacion_skills' AS table_name, COUNT(*) AS source_count FROM public.especializacion_skills;
SELECT 'especializacion_herramientas' AS table_name, COUNT(*) AS source_count FROM public.especializacion_herramientas;
SELECT 'especializacion_competencias' AS table_name, COUNT(*) AS source_count FROM public.especializacion_competencias;
SELECT 'especializacion_habilidades_blandas' AS table_name, COUNT(*) AS source_count FROM public.especializacion_habilidades_blandas;
SELECT 'microcurriculum_program_contexts' AS table_name, COUNT(*) AS source_count FROM public.microcurriculum_program_contexts;
SELECT 'empleos' AS table_name, COUNT(*) AS source_count FROM public.empleos;
SELECT 'empleo_skills' AS table_name, COUNT(*) AS source_count FROM public.empleo_skills;
SELECT 'canonical_jobs' AS table_name, COUNT(*) AS source_count FROM public.canonical_jobs;
SELECT 'silver_normalized_jobs' AS table_name, COUNT(*) AS source_count FROM public.silver_normalized_jobs;
SELECT 'gold_validated_jobs' AS table_name, COUNT(*) AS source_count FROM public.gold_validated_jobs;
SELECT 'labor_program_skill_matches' AS table_name, COUNT(*) AS source_count FROM public.labor_program_skill_matches;
SELECT 'observatory_metrics' AS table_name, COUNT(*) AS source_count FROM public.observatory_metrics;
SELECT 'curriculum_gap_observatory' AS table_name, COUNT(*) AS source_count FROM public.curriculum_gap_observatory;
SELECT 'recommendation_observatory' AS table_name, COUNT(*) AS source_count FROM public.recommendation_observatory;
SELECT 'semantic_role_graph' AS table_name, COUNT(*) AS source_count FROM public.semantic_role_graph;
SELECT 'company_observatory' AS table_name, COUNT(*) AS source_count FROM public.company_observatory;
SELECT 'emerging_technology_observatory' AS table_name, COUNT(*) AS source_count FROM public.emerging_technology_observatory;
SELECT 'career_transitions' AS table_name, COUNT(*) AS source_count FROM public.career_transitions;
SELECT 'market_forecasts' AS table_name, COUNT(*) AS source_count FROM public.market_forecasts;

-- ============================================================
-- 2) Target counts
-- ============================================================

SELECT 'especializaciones' AS table_name, COUNT(*) AS target_count FROM public.especializaciones;
SELECT 'skills' AS table_name, COUNT(*) AS target_count FROM public.skills;
SELECT 'competencias' AS table_name, COUNT(*) AS target_count FROM public.competencias;
SELECT 'herramientas' AS table_name, COUNT(*) AS target_count FROM public.herramientas;
SELECT 'habilidades_blandas' AS table_name, COUNT(*) AS target_count FROM public.habilidades_blandas;
SELECT 'especializacion_skills' AS table_name, COUNT(*) AS target_count FROM public.especializacion_skills;
SELECT 'especializacion_herramientas' AS table_name, COUNT(*) AS target_count FROM public.especializacion_herramientas;
SELECT 'especializacion_competencias' AS table_name, COUNT(*) AS target_count FROM public.especializacion_competencias;
SELECT 'especializacion_habilidades_blandas' AS table_name, COUNT(*) AS target_count FROM public.especializacion_habilidades_blandas;
SELECT 'microcurriculum_program_contexts' AS table_name, COUNT(*) AS target_count FROM public.microcurriculum_program_contexts;
SELECT 'empleos' AS table_name, COUNT(*) AS target_count FROM public.empleos;
SELECT 'empleo_skills' AS table_name, COUNT(*) AS target_count FROM public.empleo_skills;
SELECT 'canonical_jobs' AS table_name, COUNT(*) AS target_count FROM public.canonical_jobs;
SELECT 'silver_normalized_jobs' AS table_name, COUNT(*) AS target_count FROM public.silver_normalized_jobs;
SELECT 'gold_validated_jobs' AS table_name, COUNT(*) AS target_count FROM public.gold_validated_jobs;
SELECT 'labor_program_skill_matches' AS table_name, COUNT(*) AS target_count FROM public.labor_program_skill_matches;
SELECT 'observatory_metrics' AS table_name, COUNT(*) AS target_count FROM public.observatory_metrics;
SELECT 'curriculum_gap_observatory' AS table_name, COUNT(*) AS target_count FROM public.curriculum_gap_observatory;
SELECT 'recommendation_observatory' AS table_name, COUNT(*) AS target_count FROM public.recommendation_observatory;
SELECT 'semantic_role_graph' AS table_name, COUNT(*) AS target_count FROM public.semantic_role_graph;
SELECT 'company_observatory' AS table_name, COUNT(*) AS target_count FROM public.company_observatory;
SELECT 'emerging_technology_observatory' AS table_name, COUNT(*) AS target_count FROM public.emerging_technology_observatory;
SELECT 'career_transitions' AS table_name, COUNT(*) AS target_count FROM public.career_transitions;
SELECT 'market_forecasts' AS table_name, COUNT(*) AS target_count FROM public.market_forecasts;

-- ============================================================
-- 3) Distinct / PK validation
-- ============================================================

SELECT 'especializaciones' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT id) AS distinct_pk, COUNT(DISTINCT nombre) AS distinct_nombre FROM public.especializaciones;
SELECT 'skills' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT id) AS distinct_pk, COUNT(DISTINCT nombre) AS distinct_nombre FROM public.skills;
SELECT 'competencias' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT id) AS distinct_pk, COUNT(DISTINCT nombre) AS distinct_nombre FROM public.competencias;
SELECT 'empleos' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT id) AS distinct_pk FROM public.empleos;
SELECT 'empleo_skills' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT id) AS distinct_pk, COUNT(DISTINCT (empleo_id, skill_id, skill_normalized)) AS distinct_bridge_keys FROM public.empleo_skills;
SELECT 'labor_program_skill_matches' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT id) AS distinct_pk, COUNT(DISTINCT (especializacion_id, job_id, skill_id, source)) AS distinct_bridge_keys FROM public.labor_program_skill_matches;
SELECT 'observatory_metrics' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (metric_name, metric_period)) AS distinct_business_key FROM public.observatory_metrics;
SELECT 'curriculum_gap_observatory' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (specialization, missing_skill)) AS distinct_business_key FROM public.curriculum_gap_observatory;
SELECT 'recommendation_observatory' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (recommendation_type, target_role, target_company, metric_period)) AS distinct_business_key FROM public.recommendation_observatory;
SELECT 'semantic_role_graph' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (source_role, target_role, metric_period)) AS distinct_business_key FROM public.semantic_role_graph;
SELECT 'company_observatory' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (company, metric_period)) AS distinct_business_key FROM public.company_observatory;
SELECT 'emerging_technology_observatory' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (technology, metric_period)) AS distinct_business_key FROM public.emerging_technology_observatory;
SELECT 'career_transitions' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (source_role, target_role)) AS distinct_business_key FROM public.career_transitions;
SELECT 'market_forecasts' AS table_name, COUNT(*) AS rows_total, COUNT(DISTINCT (entity_type, entity_name)) AS distinct_business_key FROM public.market_forecasts;

-- ============================================================
-- 4) Referential integrity / orphan detection
-- ============================================================

-- Curricular bridges
SELECT COUNT(*) AS orphan_especializacion_skills
FROM public.especializacion_skills es
LEFT JOIN public.especializaciones e ON e.id = es.especializacion_id
LEFT JOIN public.skills s ON s.id = es.skill_id
WHERE e.id IS NULL OR s.id IS NULL;

SELECT COUNT(*) AS orphan_especializacion_herramientas
FROM public.especializacion_herramientas eh
LEFT JOIN public.especializaciones e ON e.id = eh.especializacion_id
LEFT JOIN public.herramientas h ON h.id = eh.herramienta_id
WHERE e.id IS NULL OR h.id IS NULL;

SELECT COUNT(*) AS orphan_especializacion_competencias
FROM public.especializacion_competencias ec
LEFT JOIN public.especializaciones e ON e.id = ec.especializacion_id
LEFT JOIN public.competencias c ON c.id = ec.competencia_id
WHERE e.id IS NULL OR c.id IS NULL;

SELECT COUNT(*) AS orphan_especializacion_habilidades_blandas
FROM public.especializacion_habilidades_blandas eb
LEFT JOIN public.especializaciones e ON e.id = eb.especializacion_id
LEFT JOIN public.habilidades_blandas hb ON hb.id = eb.habilidad_id
WHERE e.id IS NULL OR hb.id IS NULL;

SELECT COUNT(*) AS orphan_microcurriculum_contexts
FROM public.microcurriculum_program_contexts m
LEFT JOIN public.especializaciones e ON e.id = m.specialization_id
WHERE e.id IS NULL;

-- Job / match bridge
SELECT COUNT(*) AS orphan_empleo_skills_empleo
FROM public.empleo_skills es
LEFT JOIN public.empleos e ON e.id::text = es.empleo_id::text
WHERE e.id IS NULL;

SELECT COUNT(*) AS orphan_empleo_skills_skill
FROM public.empleo_skills es
LEFT JOIN public.skills s ON s.id = es.skill_id
WHERE es.skill_id IS NOT NULL AND s.id IS NULL;

SELECT COUNT(*) AS orphan_labor_program_skill_matches_program
FROM public.labor_program_skill_matches m
LEFT JOIN public.especializaciones e ON e.id = m.especializacion_id
WHERE e.id IS NULL;

SELECT COUNT(*) AS orphan_labor_program_skill_matches_skill
FROM public.labor_program_skill_matches m
LEFT JOIN public.skills s ON s.id = m.skill_id
WHERE m.skill_id IS NOT NULL AND s.id IS NULL;

SELECT COUNT(*) AS orphan_labor_program_skill_matches_job
FROM public.labor_program_skill_matches m
LEFT JOIN public.empleos e ON e.id::text = m.job_id
WHERE e.id IS NULL;

-- Observatory tables have no FK chains by design, but we still validate duplicates.
SELECT COUNT(*) AS duplicate_observatory_metrics
FROM (
    SELECT metric_name, metric_period, COUNT(*)
    FROM public.observatory_metrics
    GROUP BY metric_name, metric_period
    HAVING COUNT(*) > 1
) dup;

SELECT COUNT(*) AS duplicate_recommendations
FROM (
    SELECT recommendation_type, target_role, target_company, metric_period, COUNT(*)
    FROM public.recommendation_observatory
    GROUP BY recommendation_type, target_role, target_company, metric_period
    HAVING COUNT(*) > 1
) dup;

-- ============================================================
-- 5) Executive validation rollup
-- ============================================================

SELECT 'especializaciones' AS entity, COUNT(*) AS total FROM public.especializaciones
UNION ALL SELECT 'skills', COUNT(*) FROM public.skills
UNION ALL SELECT 'company_observatory', COUNT(*) FROM public.company_observatory
UNION ALL SELECT 'semantic_role_graph', COUNT(*) FROM public.semantic_role_graph
UNION ALL SELECT 'recommendation_observatory', COUNT(*) FROM public.recommendation_observatory
UNION ALL SELECT 'curriculum_gap_observatory', COUNT(*) FROM public.curriculum_gap_observatory;
