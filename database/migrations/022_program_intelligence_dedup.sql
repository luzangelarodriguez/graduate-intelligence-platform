BEGIN;

CREATE EXTENSION IF NOT EXISTS unaccent;

ALTER TABLE program_intelligence
    ADD COLUMN IF NOT EXISTS canonical_program_key TEXT;

CREATE OR REPLACE FUNCTION normalize_program_intelligence_key(value TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT regexp_replace(
        lower(unaccent(coalesce(value, ''))),
        '\s+',
        ' ',
        'g'
    );
$$;

UPDATE program_intelligence
SET canonical_program_key = normalize_program_intelligence_key(program_name)
WHERE canonical_program_key IS NULL OR canonical_program_key = '';

WITH ranked AS (
    SELECT
        program_id,
        canonical_program_key,
        ROW_NUMBER() OVER (
            PARTITION BY canonical_program_key
            ORDER BY
                COALESCE(alignment_score, 0) DESC,
                COALESCE(risk_score, 0) DESC,
                COALESCE(gap_count, 0) ASC,
                COALESCE(generated_at, updated_at) DESC NULLS LAST,
                program_id ASC
        ) AS row_rank
    FROM program_intelligence
    WHERE canonical_program_key IS NOT NULL AND canonical_program_key <> ''
)
DELETE FROM program_intelligence pi
USING ranked r
WHERE pi.program_id = r.program_id
  AND r.row_rank > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_program_intelligence_canonical_program_key
    ON program_intelligence (canonical_program_key);

COMMIT;
