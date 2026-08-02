-- Test fixtures for user_data table
-- Used for local testing and lost update reproduction

-- Clear existing test data (safe for disposable environments)
DELETE FROM public.user_data WHERE user_id = 'test-user-uuid';

-- Insert initial test row with mathGameStats
INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
VALUES (
    'test-user-uuid',
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

-- Insert test row for study_rewards
INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
VALUES (
    'test-user-uuid',
    'study_rewards',
    '{
        "gems": 0,
        "youtube_minutes": 0,
        "snacks": 0,
        "marble_plays": 0,
        "custom_inventory": {},
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
WHERE user_id = 'test-user-uuid';
