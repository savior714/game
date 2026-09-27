-- weekly_english_ingestion_rls.sql
-- Row Level Security (RLS) policies and Grants for weekly English ingestion

-- ── 1. Enable RLS on new tables ─────────────────────────────
ALTER TABLE public.weekly_ingestion_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_vocabulary_history ENABLE ROW LEVEL SECURITY;

-- ── 2. Policies for weekly_ingestion_tokens ─────────────────
DROP POLICY IF EXISTS "Users can view their own tokens" ON public.weekly_ingestion_tokens;
DROP POLICY IF EXISTS "Users can insert their own tokens" ON public.weekly_ingestion_tokens;
DROP POLICY IF EXISTS "Users can update their own tokens" ON public.weekly_ingestion_tokens;
DROP POLICY IF EXISTS "Users can delete their own tokens" ON public.weekly_ingestion_tokens;

CREATE POLICY "Users can view their own tokens"
    ON public.weekly_ingestion_tokens
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own tokens"
    ON public.weekly_ingestion_tokens
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own tokens"
    ON public.weekly_ingestion_tokens
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own tokens"
    ON public.weekly_ingestion_tokens
    FOR DELETE
    USING (auth.uid() = user_id);

-- Deny anon access to raw token table
REVOKE ALL ON public.weekly_ingestion_tokens FROM public;
REVOKE ALL ON public.weekly_ingestion_tokens FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.weekly_ingestion_tokens TO authenticated;

-- ── 3. Policies for weekly_vocabulary_history ───────────────
DROP POLICY IF EXISTS "Users can view their own vocabulary history" ON public.weekly_vocabulary_history;
DROP POLICY IF EXISTS "Users can insert their own vocabulary history" ON public.weekly_vocabulary_history;

CREATE POLICY "Users can view their own vocabulary history"
    ON public.weekly_vocabulary_history
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own vocabulary history"
    ON public.weekly_vocabulary_history
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

REVOKE ALL ON public.weekly_vocabulary_history FROM public;
REVOKE ALL ON public.weekly_vocabulary_history FROM anon;
GRANT SELECT, INSERT ON public.weekly_vocabulary_history TO authenticated;

-- ── 4. Grants on SECURITY DEFINER RPC Functions ─────────────
-- External agents connect via Supabase HTTPS RPC using anon publishable key
-- and provide their scoped capability token as an argument.
GRANT EXECUTE ON FUNCTION public.register_weekly_english_set(TEXT, JSONB, JSONB) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_current_weekly_english_set(TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.revoke_weekly_ingestion_token(TEXT) TO anon, authenticated;
-- Token provisioning requires authenticated guardian
GRANT EXECUTE ON FUNCTION public.create_weekly_english_agent_token(TEXT) TO authenticated;
-- Guardian mutation wrapper & token management
GRANT EXECUTE ON FUNCTION public.register_weekly_english_set_as_guardian(JSONB, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION public.list_weekly_english_agent_tokens() TO authenticated;
GRANT EXECUTE ON FUNCTION public.revoke_weekly_english_agent_token(UUID) TO authenticated;

