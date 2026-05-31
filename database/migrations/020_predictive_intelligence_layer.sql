-- Graduate Intelligence Platform
-- Migration 020: predictive intelligence layer.
-- Non destructive. Extends market forecasts to support multiple horizons.

ALTER TABLE public.market_forecasts
    ADD COLUMN IF NOT EXISTS horizon_months INTEGER NOT NULL DEFAULT 12;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'market_forecasts_entity_type_entity_name_key'
          AND conrelid = 'public.market_forecasts'::regclass
    ) THEN
        ALTER TABLE public.market_forecasts
            DROP CONSTRAINT market_forecasts_entity_type_entity_name_key;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ux_market_forecasts_entity_horizon
    ON public.market_forecasts(entity_type, entity_name, horizon_months);

CREATE INDEX IF NOT EXISTS idx_market_forecasts_entity_horizon
    ON public.market_forecasts(entity_type, horizon_months, growth_velocity DESC);

