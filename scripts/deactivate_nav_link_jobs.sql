-- Deactivate jobs scraped from Magneto navigation/listing pages instead of
-- actual job detail pages. These have title='Ver todos' (pagination link text)
-- and source_job_id=NULL (listing URL has no slug to extract an ID from).
--
-- Run this directly against the Railway DB:
--   psql $RAILWAY_DATABASE_URL -f scripts/deactivate_nav_link_jobs.sql
--
-- Preview first (no changes):
SELECT id, title, source, source_job_id, created_at
FROM jobs
WHERE LOWER(TRIM(title)) = 'ver todos'
ORDER BY id;

-- Apply:
UPDATE jobs
SET activo = FALSE
WHERE LOWER(TRIM(title)) = 'ver todos';
-- Expected: 44 rows (all from source='magneto', created 2026-09-14 16:04-16:05 UTC)
