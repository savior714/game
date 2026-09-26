-- 003_create_weekly_english_ingestion.sql
-- Agent Weekly English Ingestion Vertical Slice
--
-- Provides:
-- 1. weekly_ingestion_tokens: scoped credential token hashes bound to user_id.
-- 2. weekly_vocabulary_history: rollback preservation history for weekly sets.
-- 3. register_weekly_english_set: atomic RPC for candidate registration, validation,
--    idempotency (NO_OP), small change (REVISION), large conflict (NEEDS_CONFIRMATION),
--    and new week (NEW_SET).
-- 4. get_current_weekly_english_set: read-back RPC.
-- 5. revoke_weekly_ingestion_token: token revocation RPC.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── 1. Scoped Capability Tokens Table ───────────────────────
CREATE TABLE IF NOT EXISTS public.weekly_ingestion_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL DEFAULT 'weekly_english_ingestion',
    description TEXT,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_weekly_ingestion_tokens_hash
    ON public.weekly_ingestion_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_weekly_ingestion_tokens_user
    ON public.weekly_ingestion_tokens(user_id);

COMMENT ON TABLE public.weekly_ingestion_tokens IS
    'Scoped capability tokens for external agent weekly English ingestion. Tokens are stored only as SHA-256 hashes.';

-- ── 2. Rollback Preservation History Table ──────────────────
CREATE TABLE IF NOT EXISTS public.weekly_vocabulary_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    set_id TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    payload JSONB NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT unique_user_set_revision UNIQUE (user_id, set_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_weekly_vocabulary_history_user_set
    ON public.weekly_vocabulary_history(user_id, set_id, revision DESC);

COMMENT ON TABLE public.weekly_vocabulary_history IS
    'Rollback preservation history for weekly vocabulary sets per user.';

-- ── 3. Helper: Deterministic Content Fingerprint ────────────
CREATE OR REPLACE FUNCTION public._compute_weekly_content_fingerprint(p_items JSONB)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_item JSONB;
    v_lines TEXT[] := ARRAY[]::TEXT[];
    v_joined TEXT;
BEGIN
    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' THEN
        RETURN '';
    END IF;

    FOR v_item IN SELECT value FROM jsonb_array_elements(p_items) LOOP
        v_lines := array_append(
            v_lines,
            lower(trim(COALESCE(v_item->>'answer', v_item->>'word', ''))) || '::' ||
            lower(trim(COALESCE(v_item->>'prompt', v_item->>'academyDescription', '')))
        );
    END LOOP;

    -- Sort lines for order invariance
    SELECT string_agg(elem, E'\n' ORDER BY elem) INTO v_joined
    FROM unnest(v_lines) AS elem;

    RETURN encode(digest(COALESCE(v_joined, ''), 'sha256'), 'hex');
END;
$$;

-- ── 4. Canonical RPC: register_weekly_english_set ───────────
CREATE OR REPLACE FUNCTION public.register_weekly_english_set(
    p_agent_token TEXT,
    p_candidate JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_token_hash TEXT;
    v_user_id UUID;
    v_test_date TEXT;
    v_items JSONB;
    v_item_count INT;
    v_ambiguities JSONB;
    v_idx INT;
    v_elem JSONB;
    v_ans TEXT;
    v_prompt TEXT;
    v_new_fp TEXT;
    v_current_row RECORD;
    v_current_payload JSONB;
    v_existing_date TEXT;
    v_existing_fp TEXT;
    v_existing_rev INT;
    v_existing_items JSONB;
    v_diff_count INT := 0;
    v_new_rev INT := 1;
    v_status TEXT;
    v_now_iso TEXT;
    v_now_ms BIGINT;
    v_canonical_items JSONB := '[]'::JSONB;
    v_legacy_items JSONB := '[]'::JSONB;
    v_new_payload JSONB;
    v_item_id TEXT;
    v_p_hash TEXT;
BEGIN
    -- 1. Authenticate scoped token via SHA-256 hash
    IF p_agent_token IS NULL OR trim(p_agent_token) = '' THEN
        RETURN jsonb_build_object(
            'status', 'UNAUTHORIZED',
            'message', 'Agent token is required'
        );
    END IF;

    v_token_hash := encode(digest(trim(p_agent_token), 'sha256'), 'hex');

    SELECT user_id INTO v_user_id
    FROM public.weekly_ingestion_tokens
    WHERE token_hash = v_token_hash
      AND is_revoked = FALSE
      AND (expires_at IS NULL OR expires_at > NOW())
      AND scope = 'weekly_english_ingestion';

    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object(
            'status', 'UNAUTHORIZED',
            'message', 'Invalid, expired, or revoked token'
        );
    END IF;

    -- 2. Validate Candidate
    IF p_candidate IS NULL OR jsonb_typeof(p_candidate) <> 'object' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate must be a JSON object'
        );
    END IF;

    v_test_date := trim(COALESCE(p_candidate->>'testDate', ''));
    IF v_test_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate testDate must match YYYY-MM-DD format'
        );
    END IF;

    v_ambiguities := p_candidate->'ambiguities';
    IF v_ambiguities IS NOT NULL AND jsonb_typeof(v_ambiguities) = 'array' AND jsonb_array_length(v_ambiguities) > 0 THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate contains unresolved ambiguities; automatic activation forbidden'
        );
    END IF;

    v_items := p_candidate->'items';
    IF v_items IS NULL OR jsonb_typeof(v_items) <> 'array' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate items must be a non-empty array'
        );
    END IF;

    v_item_count := jsonb_array_length(v_items);
    IF v_item_count < 8 OR v_item_count > 15 THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', format('Candidate items count (%s) out of standard weekly bounds (8-15)', v_item_count)
        );
    END IF;

    -- Validate each item & build canonical item array
    FOR v_idx IN 0 .. v_item_count - 1 LOOP
        v_elem := v_items->v_idx;
        IF v_elem IS NULL OR jsonb_typeof(v_elem) <> 'object' THEN
            RETURN jsonb_build_object(
                'status', 'REJECTED_INVALID',
                'message', format('Item at index %s is not an object', v_idx)
            );
        END IF;

        v_ans := trim(COALESCE(v_elem->>'answer', v_elem->>'word', ''));
        v_prompt := trim(COALESCE(v_elem->>'prompt', v_elem->>'academyDescription', ''));

        IF v_ans = '' OR v_prompt = '' THEN
            RETURN jsonb_build_object(
                'status', 'REJECTED_INVALID',
                'message', format('Item at index %s has missing answer or prompt', v_idx)
            );
        END IF;

        v_p_hash := substr(encode(digest(v_prompt, 'sha256'), 'hex'), 1, 8);
        v_item_id := lower(v_test_date || '-' || v_ans || '-' || v_p_hash);

        v_canonical_items := v_canonical_items || jsonb_build_object(
            'itemId', v_item_id,
            'id', v_item_id,
            'word', v_ans,
            'answer', v_ans,
            'academyDescription', v_prompt,
            'prompt', v_prompt,
            'ko', COALESCE(v_elem->>'ko', ''),
            'icon', COALESCE(v_elem->>'icon', ''),
            'acceptedAnswers', COALESCE(v_elem->'acceptedAnswers', '[]'::JSONB)
        );

        v_legacy_items := v_legacy_items || jsonb_build_object(
            'en', v_ans,
            'ko', COALESCE(v_elem->>'ko', ''),
            'icon', COALESCE(v_elem->>'icon', '')
        );
    END LOOP;

    -- 3. Calculate new fingerprint
    v_new_fp := public._compute_weekly_content_fingerprint(v_canonical_items);

    -- 4. Inspect current active set
    SELECT * INTO v_current_row
    FROM public.user_data
    WHERE user_id = v_user_id
      AND data_key = 'aiden_canonical_weekly_vocabulary_v1';

    IF v_current_row.id IS NOT NULL THEN
        v_current_payload := v_current_row.payload;
        v_existing_date := COALESCE(v_current_payload->>'testDate', v_current_payload->>'setId', '');
        v_existing_fp := COALESCE(v_current_payload->>'contentFingerprint', '');
        v_existing_rev := COALESCE((v_current_payload->>'revision')::INT, 1);
        v_existing_items := v_current_payload->'items';

        IF v_existing_date = v_test_date THEN
            -- Same date: check fingerprint
            IF v_existing_fp = v_new_fp THEN
                -- Case 1: Same date + same content => NO_OP
                RETURN jsonb_build_object(
                    'status', 'NO_OP',
                    'setId', v_test_date,
                    'testDate', v_test_date,
                    'revision', v_existing_rev,
                    'itemCount', v_item_count,
                    'contentFingerprint', v_new_fp,
                    'updatedAt', v_current_payload->>'updatedAt'
                );
            END IF;

            -- Different content on same date: compute item differences
            SELECT COUNT(*) INTO v_diff_count
            FROM (
                SELECT lower(trim(COALESCE(e->>'answer', e->>'word', ''))) AS w,
                       lower(trim(COALESCE(e->>'prompt', e->>'academyDescription', ''))) AS p
                FROM jsonb_array_elements(v_canonical_items) AS e
                EXCEPT
                SELECT lower(trim(COALESCE(o->>'answer', o->>'word', ''))) AS w,
                       lower(trim(COALESCE(o->>'prompt', o->>'academyDescription', ''))) AS p
                FROM jsonb_array_elements(COALESCE(v_existing_items, '[]'::JSONB)) AS o
            ) diff_set;

            IF v_diff_count > 3 THEN
                -- Case 3: Same date + large change (>3 items changed) => NEEDS_CONFIRMATION
                RETURN jsonb_build_object(
                    'status', 'NEEDS_CONFIRMATION',
                    'message', format('Large content change detected on same date %s (%s items changed > threshold 3); automatic overwrite withheld', v_test_date, v_diff_count),
                    'activeSetId', v_existing_date,
                    'activeRevision', v_existing_rev,
                    'activeItemCount', jsonb_array_length(COALESCE(v_existing_items, '[]'::JSONB)),
                    'conflictDiffCount', v_diff_count
                );
            END IF;

            -- Case 2: Same date + small change (1-3 items) => REGISTERED_REVISION
            v_status := 'REGISTERED_REVISION';
            v_new_rev := v_existing_rev + 1;
        ELSE
            -- Case 4: Different test date => REGISTERED_NEW
            v_status := 'REGISTERED_NEW';
            v_new_rev := 1;
        END IF;

        -- Preserve existing current set to rollback history before overwriting
        UPDATE public.weekly_vocabulary_history
        SET is_current = FALSE
        WHERE user_id = v_user_id AND is_current = TRUE;

        INSERT INTO public.weekly_vocabulary_history (
            user_id, set_id, revision, payload, registered_at, is_current
        ) VALUES (
            v_user_id,
            v_existing_date,
            v_existing_rev,
            v_current_payload,
            NOW(),
            FALSE
        )
        ON CONFLICT (user_id, set_id, revision) DO UPDATE
        SET payload = EXCLUDED.payload,
            is_current = FALSE;
    ELSE
        -- No current row exists: First time registration
        v_status := 'REGISTERED_NEW';
        v_new_rev := 1;
    END IF;

    -- 5. Prepare New Current Payload
    v_now_iso := to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
    v_now_ms := (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT;

    v_new_payload := jsonb_build_object(
        'schemaVersion', 1,
        'setId', v_test_date,
        'testDate', v_test_date,
        'title', v_test_date || ' 주간 영단어',
        'revision', v_new_rev,
        'contentFingerprint', v_new_fp,
        'items', v_canonical_items,
        '_updated_at', v_now_ms,
        'updatedAt', v_now_iso,
        'registeredAt', v_now_iso
    );

    -- 6. Atomic Activation into user_data
    INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
    VALUES (v_user_id, 'aiden_canonical_weekly_vocabulary_v1', v_new_payload, NOW())
    ON CONFLICT (user_id, data_key) DO UPDATE
    SET payload = v_new_payload,
        updated_at = NOW();

    -- Also update legacy projection key 'englishWeeklyWords' for compatibility
    INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
    VALUES (v_user_id, 'englishWeeklyWords', v_legacy_items, NOW())
    ON CONFLICT (user_id, data_key) DO UPDATE
    SET payload = v_legacy_items,
        updated_at = NOW();

    -- Record new revision in weekly_vocabulary_history
    UPDATE public.weekly_vocabulary_history
    SET is_current = FALSE
    WHERE user_id = v_user_id AND is_current = TRUE;

    INSERT INTO public.weekly_vocabulary_history (
        user_id, set_id, revision, payload, registered_at, is_current
    ) VALUES (
        v_user_id,
        v_test_date,
        v_new_rev,
        v_new_payload,
        NOW(),
        TRUE
    )
    ON CONFLICT (user_id, set_id, revision) DO UPDATE
    SET payload = v_new_payload,
        is_current = TRUE;

    -- 7. Return machine-readable result
    RETURN jsonb_build_object(
        'status', v_status,
        'setId', v_test_date,
        'testDate', v_test_date,
        'revision', v_new_rev,
        'itemCount', v_item_count,
        'contentFingerprint', v_new_fp,
        'updatedAt', v_now_iso
    );
END;
$$;

-- ── 5. Read-Back RPC: get_current_weekly_english_set ────────
CREATE OR REPLACE FUNCTION public.get_current_weekly_english_set(
    p_agent_token TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_token_hash TEXT;
    v_user_id UUID;
    v_current_payload JSONB;
BEGIN
    IF p_agent_token IS NULL OR trim(p_agent_token) = '' THEN
        RETURN jsonb_build_object(
            'status', 'UNAUTHORIZED',
            'message', 'Agent token is required'
        );
    END IF;

    v_token_hash := encode(digest(trim(p_agent_token), 'sha256'), 'hex');

    SELECT user_id INTO v_user_id
    FROM public.weekly_ingestion_tokens
    WHERE token_hash = v_token_hash
      AND is_revoked = FALSE
      AND (expires_at IS NULL OR expires_at > NOW())
      AND scope = 'weekly_english_ingestion';

    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object(
            'status', 'UNAUTHORIZED',
            'message', 'Invalid, expired, or revoked token'
        );
    END IF;

    SELECT payload INTO v_current_payload
    FROM public.user_data
    WHERE user_id = v_user_id
      AND data_key = 'aiden_canonical_weekly_vocabulary_v1';

    IF v_current_payload IS NULL THEN
        RETURN jsonb_build_object(
            'status', 'NOT_FOUND',
            'message', 'No canonical weekly vocabulary set registered for this user'
        );
    END IF;

    RETURN jsonb_build_object(
        'status', 'OK',
        'currentSet', v_current_payload
    );
END;
$$;

-- ── 6. Revocation RPC: revoke_weekly_ingestion_token ────────
CREATE OR REPLACE FUNCTION public.revoke_weekly_ingestion_token(
    p_agent_token TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_token_hash TEXT;
    v_user_id UUID;
BEGIN
    IF p_agent_token IS NULL OR trim(p_agent_token) = '' THEN
        RETURN jsonb_build_object('status', 'UNAUTHORIZED', 'revoked', false);
    END IF;

    v_token_hash := encode(digest(trim(p_agent_token), 'sha256'), 'hex');

    UPDATE public.weekly_ingestion_tokens
    SET is_revoked = TRUE
    WHERE token_hash = v_token_hash
    RETURNING user_id INTO v_user_id;

    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object('status', 'NOT_FOUND', 'revoked', false);
    END IF;

    RETURN jsonb_build_object('status', 'REVOKED', 'revoked', true);
END;
$$;
