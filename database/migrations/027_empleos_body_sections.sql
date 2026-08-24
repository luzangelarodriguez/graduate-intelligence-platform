-- Migration 027: add named body-section columns to empleos and jobs tables
-- These are populated by the extended scraper (responsabilidades / requisitos)
-- and used by load_jobs() in academic_relevance_engine.py for richer skill extraction.

ALTER TABLE public.empleos
    ADD COLUMN IF NOT EXISTS responsabilidades TEXT,
    ADD COLUMN IF NOT EXISTS requisitos        TEXT;

-- jobs table already has responsibilities / requirements from migration 015,
-- but add IF NOT EXISTS guards for safety.
ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS responsibilities TEXT,
    ADD COLUMN IF NOT EXISTS requirements     TEXT;
