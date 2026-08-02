-- Row Level Security (RLS) policies for user_data table
-- Based on analysis of domains/sync/sync-engine.js push/pull patterns

-- Enable RLS on user_data table
ALTER TABLE public.user_data ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotent migration)
DROP POLICY IF EXISTS "Users can only view their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can only insert their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can only update their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can only delete their own data" ON public.user_data;

-- Policy 1: Users can SELECT only their own data
-- This is used by pullAndMerge (sync-engine.js:138-142)
CREATE POLICY "Users can only view their own data"
    ON public.user_data
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy 2: Users can INSERT only their own data
-- Note: Current code passes user_id from client (security risk)
-- This policy enforces that auth.uid() must match user_id
CREATE POLICY "Users can only insert their own data"
    ON public.user_data
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy 3: Users can UPDATE only their own data
-- This is used by pushToSupabase upsert (sync-engine.js:97-104)
-- RLS applies to the target row, not the incoming user_id
CREATE POLICY "Users can only update their own data"
    ON public.user_data
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy 4: Users can INSERT via upsert (INSERT part of ON CONFLICT)
-- Supabase upsert with onConflict performs INSERT when no conflict
CREATE POLICY "Users can insert via upsert"
    ON public.user_data
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy 5: Allow authenticated users to upsert their own data
-- This covers the upsert pattern in sync-engine.js:97-104
-- The ON CONFLICT clause will UPDATE if row exists, INSERT if not
-- RLS is applied to both branches
CREATE POLICY "Authenticated users can upsert own data"
    ON public.user_data
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Revoke all public access
REVOKE ALL ON public.user_data FROM public;
REVOKE ALL ON public.user_data FROM anon;

-- Grant necessary permissions to authenticated role
GRANT SELECT, INSERT, UPDATE ON public.user_data TO authenticated;

-- Optional: Grant table access to service_role (for admin functions)
-- This is automatically handled by Supabase, but documented for clarity
-- GRANT ALL ON public.user_data TO service_role;

-- Comment on RLS policies
COMMENT ON TABLE public.user_data IS 'RLS enabled: All access restricted to owner (auth.uid() = user_id)';
