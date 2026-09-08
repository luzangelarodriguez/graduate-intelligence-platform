-- Migration 029: add updated_at to ml_program_job_matches
-- Tracks when each match row was last recalculated so the frontend can show
-- an accurate "Corte" date instead of the run's original created_at.

ALTER TABLE ml_program_job_matches
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Back-fill existing rows so updated_at == created_at for historical data.
UPDATE ml_program_job_matches SET updated_at = created_at WHERE updated_at = now() AND created_at < now();

CREATE INDEX IF NOT EXISTS ix_ml_program_job_matches_updated_at
    ON ml_program_job_matches (run_id, updated_at DESC);
