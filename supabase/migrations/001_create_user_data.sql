-- Supabase user_data table schema
-- Based on analysis of:
--   - domains/sync/sync-engine.js:97-104 (upsert pattern)
--   - domains/sync/sync-engine.js:138-142 (select pattern)
--   - shared/domain/progress-engine.js:32-41 (stats payload shape)

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create user_data table
CREATE TABLE IF NOT EXISTS public.user_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    data_key TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraint: Each user can have only one row per data_key
    CONSTRAINT unique_user_data_key UNIQUE (user_id, data_key)
);

-- Index for faster lookups by user_id
CREATE INDEX IF NOT EXISTS idx_user_data_user_id ON public.user_data(user_id);

-- Index for faster lookups by data_key (useful for admin queries)
CREATE INDEX IF NOT EXISTS idx_user_data_data_key ON public.user_data(data_key);

-- Index for updated_at ordering
CREATE INDEX IF NOT EXISTS idx_user_data_updated_at ON public.user_data(updated_at DESC);

-- Comment on table
COMMENT ON TABLE public.user_data IS 'Stores user-specific game stats, study rewards, and other persistent data';

-- Comment on columns
COMMENT ON COLUMN public.user_data.user_id IS 'Auth user ID (from Supabase Auth)';
COMMENT ON COLUMN public.user_data.data_key IS 'Logical data identifier (e.g., study_rewards, mathGameStats)';
COMMENT ON COLUMN public.user_data.payload IS 'JSON payload containing game stats or reward data';
COMMENT ON COLUMN public.user_data.updated_at IS 'Last update timestamp (copied from payload._updated_at or current time)';
