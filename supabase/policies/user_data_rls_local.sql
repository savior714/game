-- Simplified RLS policies for local PostgreSQL testing
-- This is a simplified version without Supabase-specific features
-- For production Supabase, use supabase/policies/user_data_rls.sql

-- Enable RLS on user_data table
ALTER TABLE public.user_data ENABLE ROW LEVEL SECURITY;

-- Create a test user role for testing
DROP ROLE IF EXISTS test_user;
CREATE ROLE test_user LOGIN PASSWORD 'test_password';

-- Grant basic access to test_user
GRANT SELECT, INSERT, UPDATE ON public.user_data TO test_user;

-- For local testing, we skip complex RLS policies
-- In production Supabase, use auth.uid() based policies

-- Insert test data for lost update reproduction
INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'mathGameStats',
    '{
        "math": {
            "levels": {
                "0": {"attempts": 0, "correct": 0, "totalTime": 0},
                "1": {"attempts": 0, "correct": 0, "totalTime": 0},
                "2": {"attempts": 0, "correct": 0, "totalTime": 0},
                "3": {"attempts": 0, "correct": 0, "totalTime": 0},
                "4": {"attempts": 0, "correct": 0, "totalTime": 0},
                "5": {"attempts": 0, "correct": 0, "totalTime": 0},
                "6": {"attempts": 0, "correct": 0, "totalTime": 0}
            },
            "weaknesses": {
                "overall": {"attempts": 0, "correct": 0}
            }
        },
        "_updated_at": 1700000000000
    }'::jsonb,
    '2024-01-01 00:00:00+00'
)
ON CONFLICT (user_id, data_key) DO UPDATE
SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at;

-- Verify insertion
SELECT
    user_id,
    data_key,
    payload->'math'->'levels'->'0' as level_0_stats,
    updated_at
FROM public.user_data
WHERE user_id = '00000000-0000-0000-0000-000000000001';
