-- Migration 027: add body section columns to empleos and jobs
ALTER TABLE public.empleos
    ADD COLUMN IF NOT EXISTS responsabilidades TEXT,
    ADD COLUMN IF NOT EXISTS requisitos        TEXT;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS responsibilities TEXT,
    ADD COLUMN IF NOT EXISTS requirements     TEXT;
