-- Row Level Security (RLS) policies for user_data table
-- Server-authoritative keys ('aiden_canonical_weekly_vocabulary_v1', 'englishWeeklyWords')
-- are blocked from ordinary direct table upsert. They MUST go through designated SECURITY DEFINER RPCs.

-- Enable RLS on user_data table
ALTER TABLE public.user_data ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotent migration)
DROP POLICY IF EXISTS "Users can only view their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can only insert their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can only update their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can only delete their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can insert via upsert" ON public.user_data;
DROP POLICY IF EXISTS "Authenticated users can upsert own data" ON public.user_data;
DROP POLICY IF EXISTS "Authenticated users can insert non-server-authoritative data" ON public.user_data;
DROP POLICY IF EXISTS "Authenticated users can update non-server-authoritative data" ON public.user_data;

-- Policy 1: Users can SELECT only their own data
CREATE POLICY "Users can only view their own data"
    ON public.user_data
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy 2: Users can INSERT only their own data, FORBIDDING server-authoritative weekly keys
CREATE POLICY "Authenticated users can insert non-server-authoritative data"
    ON public.user_data
    FOR INSERT
    WITH CHECK (
        auth.uid() = user_id
        AND data_key NOT IN ('aiden_canonical_weekly_vocabulary_v1', 'englishWeeklyWords')
    );

-- Policy 3: Users can UPDATE only their own data, FORBIDDING server-authoritative weekly keys
CREATE POLICY "Authenticated users can update non-server-authoritative data"
    ON public.user_data
    FOR UPDATE
    USING (
        auth.uid() = user_id
        AND data_key NOT IN ('aiden_canonical_weekly_vocabulary_v1', 'englishWeeklyWords')
    )
    WITH CHECK (
        auth.uid() = user_id
        AND data_key NOT IN ('aiden_canonical_weekly_vocabulary_v1', 'englishWeeklyWords')
    );

-- Revoke all public access
REVOKE ALL ON public.user_data FROM public;
REVOKE ALL ON public.user_data FROM anon;

-- Grant necessary permissions to authenticated role
GRANT SELECT, INSERT, UPDATE ON public.user_data TO authenticated;

-- Comment on RLS policies
COMMENT ON TABLE public.user_data IS 'RLS enabled: All access restricted to owner (auth.uid() = user_id). Server-authoritative weekly keys blocked from direct upsert.';
