-- 005_weekly_ingestion_authority_and_confirmation_closure.sql
-- Closes final operational holes in the weekly English agent ingestion pipeline:
--   1. Confirmation validation helper (_validate_weekly_confirmation) for all atypical & conflict branches
--   2. Strict fail-closed verification for:
--      - same-date atypical (reason = ATYPICAL_ITEM_COUNT, candidateFp, expectedActiveFp, expectedActiveRev)
--      - different-date atypical (reason = ATYPICAL_ITEM_COUNT, candidateFp, expectedActiveFp, expectedActiveRev)
--      - no-current-set atypical (reason = ATYPICAL_ITEM_COUNT, candidateFp)
--      - large symmetric diff (reason = LARGE_SYMMETRIC_DIFF, candidateFp, expectedActiveFp, expectedActiveRev)
--   3. Authenticated guardian mutation wrapper (register_weekly_english_set_as_guardian)
--   4. Token management RPCs (list_weekly_english_agent_tokens, revoke_weekly_english_agent_token)
--   5. Restrict user_data RLS to forbid ordinary direct upserts of server-authoritative weekly keys

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ══════════════════════════════════════════════════════════════
-- 1. Shared Confirmation Validator Helper
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public._validate_weekly_confirmation(
    p_confirmation JSONB,
    p_expected_reason TEXT,
    p_candidate_fp TEXT,
    p_active_fp TEXT DEFAULT NULL,
    p_active_rev INT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_reason TEXT;
    v_confirm_candidate_fp TEXT;
    v_confirm_expected_fp TEXT;
    v_confirm_expected_rev INT;
BEGIN
    IF p_confirmation IS NULL OR jsonb_typeof(p_confirmation) <> 'object' OR p_confirmation = '{}'::JSONB THEN
        RETURN jsonb_build_object(
            'valid', false,
            'status', 'REJECTED_CONFIRMATION',
            'message', 'Confirmation payload is required and cannot be empty'
        );
    END IF;

    -- 1. Validate confirmation reason
    v_reason := trim(COALESCE(p_confirmation->>'reason', ''));
    IF v_reason = '' OR v_reason <> p_expected_reason THEN
        RETURN jsonb_build_object(
            'valid', false,
            'status', 'REJECTED_CONFIRMATION',
            'message', format('Invalid confirmation reason: expected %s, got %s', p_expected_reason, COALESCE(v_reason, 'none'))
        );
    END IF;

    -- 2. Validate candidate fingerprint match
    v_confirm_candidate_fp := trim(COALESCE(p_confirmation->>'candidateFingerprint', ''));
    IF v_confirm_candidate_fp = '' OR v_confirm_candidate_fp <> p_candidate_fp THEN
        RETURN jsonb_build_object(
            'valid', false,
            'status', 'CONFIRMATION_STALE',
            'message', 'Confirmation candidateFingerprint does not match actual candidate content',
            'expectedCandidateFp', v_confirm_candidate_fp,
            'actualCandidateFp', p_candidate_fp
        );
    END IF;

    -- 3. Validate existing active set context if active set exists
    IF p_active_fp IS NOT NULL AND p_active_fp <> '' THEN
        v_confirm_expected_fp := trim(COALESCE(p_confirmation->>'expectedActiveFingerprint', ''));
        v_confirm_expected_rev := COALESCE((p_confirmation->>'expectedActiveRevision')::INT, -1);

        IF v_confirm_expected_fp = '' OR v_confirm_expected_rev < 0 THEN
            RETURN jsonb_build_object(
                'valid', false,
                'status', 'REJECTED_CONFIRMATION',
                'message', 'Active set confirmation requires expectedActiveFingerprint and expectedActiveRevision'
            );
        END IF;

        IF v_confirm_expected_fp <> p_active_fp OR v_confirm_expected_rev <> p_active_rev THEN
            RETURN jsonb_build_object(
                'valid', false,
                'status', 'CONFIRMATION_STALE',
                'message', 'Active set has changed since confirmation was issued',
                'expectedActiveFingerprint', v_confirm_expected_fp,
                'expectedActiveRevision', v_confirm_expected_rev,
                'actualActiveFingerprint', p_active_fp,
                'actualActiveRevision', p_active_rev
            );
        END IF;
    END IF;

    RETURN jsonb_build_object('valid', true);
END;
$$;


-- ══════════════════════════════════════════════════════════════
-- 2. Internal Core Set Registration Logic
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public._register_weekly_english_set_internal(
    p_user_id UUID,
    p_candidate JSONB,
    p_confirmation JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    C_CHANGE_THRESHOLD CONSTANT INT := 3;
    C_NORMAL_ITEM_MIN  CONSTANT INT := 8;
    C_NORMAL_ITEM_MAX  CONSTANT INT := 12;
    C_ATYPICAL_ITEM_MAX CONSTANT INT := 15;

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
    v_added_count INT := 0;
    v_removed_count INT := 0;
    v_sym_diff_count INT := 0;
    v_new_rev INT := 1;
    v_status TEXT;
    v_now_iso TEXT;
    v_now_ms BIGINT;
    v_canonical_items JSONB := '[]'::JSONB;
    v_legacy_items JSONB := '[]'::JSONB;
    v_new_payload JSONB;
    v_item_id TEXT;
    v_p_hash TEXT;

    v_dup_count INT;
    v_parsed_date DATE;
    v_conf_val JSONB;
BEGIN
    -- ── 1. Validate Candidate ─────────────────────────────────
    IF p_candidate IS NULL OR jsonb_typeof(p_candidate) <> 'object' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate must be a JSON object'
        );
    END IF;

    v_test_date := trim(COALESCE(p_candidate->>'testDate', ''));

    -- Format check
    IF v_test_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate testDate must match YYYY-MM-DD format'
        );
    END IF;

    -- Calendar date validation
    BEGIN
        v_parsed_date := v_test_date::DATE;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', format('Candidate testDate %s is not a valid calendar date', v_test_date)
        );
    END;

    -- Ambiguity check
    v_ambiguities := p_candidate->'ambiguities';
    IF v_ambiguities IS NOT NULL AND jsonb_typeof(v_ambiguities) = 'array' AND jsonb_array_length(v_ambiguities) > 0 THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate contains unresolved ambiguities; automatic activation forbidden'
        );
    END IF;

    -- Item array check
    v_items := p_candidate->'items';
    IF v_items IS NULL OR jsonb_typeof(v_items) <> 'array' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate items must be a non-empty array'
        );
    END IF;

    v_item_count := jsonb_array_length(v_items);

    -- Item count range check
    IF v_item_count < C_NORMAL_ITEM_MIN OR v_item_count > C_ATYPICAL_ITEM_MAX THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', format('Candidate items count (%s) outside allowed bounds (%s-%s)',
                             v_item_count, C_NORMAL_ITEM_MIN, C_ATYPICAL_ITEM_MAX)
        );
    END IF;

    -- ── 2. Validate items & build canonical array ─────────────
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

    -- Duplicate detection
    SELECT (jsonb_array_length(v_canonical_items) - COUNT(DISTINCT (
        lower(trim(COALESCE(e->>'answer', e->>'word', ''))) || '::' ||
        lower(trim(COALESCE(e->>'prompt', e->>'academyDescription', '')))
    )))::INT
    INTO v_dup_count
    FROM jsonb_array_elements(v_canonical_items) AS e;

    IF v_dup_count > 0 THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', format('Candidate contains %s duplicate (answer, prompt) pair(s)', v_dup_count)
        );
    END IF;

    -- ── 3. Calculate new fingerprint ──────────────────────────
    v_new_fp := public._compute_weekly_content_fingerprint(v_canonical_items);

    -- ── 4. Inspect current active set ─────────────────────────
    SELECT * INTO v_current_row
    FROM public.user_data
    WHERE user_id = p_user_id
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

            -- Symmetric difference calculation
            SELECT COUNT(*) INTO v_added_count
            FROM (
                SELECT lower(trim(COALESCE(e->>'answer', e->>'word', ''))) AS w,
                       lower(trim(COALESCE(e->>'prompt', e->>'academyDescription', ''))) AS p
                FROM jsonb_array_elements(v_canonical_items) AS e
                EXCEPT
                SELECT lower(trim(COALESCE(o->>'answer', o->>'word', ''))) AS w,
                       lower(trim(COALESCE(o->>'prompt', o->>'academyDescription', ''))) AS p
                FROM jsonb_array_elements(COALESCE(v_existing_items, '[]'::JSONB)) AS o
            ) added_set;

            SELECT COUNT(*) INTO v_removed_count
            FROM (
                SELECT lower(trim(COALESCE(o->>'answer', o->>'word', ''))) AS w,
                       lower(trim(COALESCE(o->>'prompt', o->>'academyDescription', ''))) AS p
                FROM jsonb_array_elements(COALESCE(v_existing_items, '[]'::JSONB)) AS o
                EXCEPT
                SELECT lower(trim(COALESCE(e->>'answer', e->>'word', ''))) AS w,
                       lower(trim(COALESCE(e->>'prompt', e->>'academyDescription', ''))) AS p
                FROM jsonb_array_elements(v_canonical_items) AS e
            ) removed_set;

            v_sym_diff_count := v_added_count + v_removed_count;

            -- ── Branch A: Atypical Item Count (13-15 items) ───
            IF v_item_count > C_NORMAL_ITEM_MAX THEN
                IF p_confirmation IS NULL THEN
                    RETURN jsonb_build_object(
                        'status', 'NEEDS_CONFIRMATION',
                        'message', format('Atypical item count (%s) exceeds normal range (%s-%s); confirmation required',
                                         v_item_count, C_NORMAL_ITEM_MIN, C_NORMAL_ITEM_MAX),
                        'reason', 'ATYPICAL_ITEM_COUNT',
                        'activeSetId', v_existing_date,
                        'activeRevision', v_existing_rev,
                        'activeFingerprint', v_existing_fp,
                        'activeItemCount', jsonb_array_length(COALESCE(v_existing_items, '[]'::JSONB)),
                        'candidateFingerprint', v_new_fp,
                        'candidateItemCount', v_item_count,
                        'conflictDiffCount', v_sym_diff_count
                    );
                END IF;

                -- Validate atypical confirmation
                v_conf_val := public._validate_weekly_confirmation(
                    p_confirmation, 'ATYPICAL_ITEM_COUNT', v_new_fp, v_existing_fp, v_existing_rev
                );
                IF NOT (v_conf_val->>'valid')::BOOLEAN THEN
                    RETURN v_conf_val;
                END IF;

                v_status := 'REGISTERED_CONFIRMED_REVISION';
                v_new_rev := v_existing_rev + 1;

            -- ── Branch B: Normal Count with Large Symmetric Diff ─
            ELSIF v_sym_diff_count > C_CHANGE_THRESHOLD THEN
                IF p_confirmation IS NULL THEN
                    RETURN jsonb_build_object(
                        'status', 'NEEDS_CONFIRMATION',
                        'message', format('Large content change on same date %s (%s items in symmetric diff > threshold %s)',
                                         v_test_date, v_sym_diff_count, C_CHANGE_THRESHOLD),
                        'reason', 'LARGE_SYMMETRIC_DIFF',
                        'activeSetId', v_existing_date,
                        'activeRevision', v_existing_rev,
                        'activeFingerprint', v_existing_fp,
                        'activeItemCount', jsonb_array_length(COALESCE(v_existing_items, '[]'::JSONB)),
                        'candidateFingerprint', v_new_fp,
                        'candidateItemCount', v_item_count,
                        'conflictDiffCount', v_sym_diff_count,
                        'addedCount', v_added_count,
                        'removedCount', v_removed_count
                    );
                END IF;

                -- Validate large diff confirmation
                v_conf_val := public._validate_weekly_confirmation(
                    p_confirmation, 'LARGE_SYMMETRIC_DIFF', v_new_fp, v_existing_fp, v_existing_rev
                );
                IF NOT (v_conf_val->>'valid')::BOOLEAN THEN
                    RETURN v_conf_val;
                END IF;

                v_status := 'REGISTERED_CONFIRMED_REVISION';
                v_new_rev := v_existing_rev + 1;

            ELSE
                -- Branch C: Normal Count with Small Diff
                v_status := 'REGISTERED_REVISION';
                v_new_rev := v_existing_rev + 1;
            END IF;

        ELSE
            -- ── Different Date ────────────────────────────────
            IF v_item_count > C_NORMAL_ITEM_MAX THEN
                IF p_confirmation IS NULL THEN
                    RETURN jsonb_build_object(
                        'status', 'NEEDS_CONFIRMATION',
                        'message', format('Atypical item count (%s) exceeds normal range (%s-%s); confirmation required',
                                         v_item_count, C_NORMAL_ITEM_MIN, C_NORMAL_ITEM_MAX),
                        'reason', 'ATYPICAL_ITEM_COUNT',
                        'activeSetId', v_existing_date,
                        'activeRevision', v_existing_rev,
                        'activeFingerprint', v_existing_fp,
                        'activeItemCount', jsonb_array_length(COALESCE(v_existing_items, '[]'::JSONB)),
                        'candidateFingerprint', v_new_fp,
                        'candidateItemCount', v_item_count,
                        'conflictDiffCount', 0
                    );
                END IF;

                v_conf_val := public._validate_weekly_confirmation(
                    p_confirmation, 'ATYPICAL_ITEM_COUNT', v_new_fp, v_existing_fp, v_existing_rev
                );
                IF NOT (v_conf_val->>'valid')::BOOLEAN THEN
                    RETURN v_conf_val;
                END IF;

                v_status := 'REGISTERED_CONFIRMED_REVISION';
                v_new_rev := 1;
            ELSE
                v_status := 'REGISTERED_NEW';
                v_new_rev := 1;
            END IF;
        END IF;

        -- Preserve existing current set into history
        UPDATE public.weekly_vocabulary_history
        SET is_current = FALSE
        WHERE user_id = p_user_id AND is_current = TRUE;

        INSERT INTO public.weekly_vocabulary_history (
            user_id, set_id, revision, payload, registered_at, is_current
        ) VALUES (
            p_user_id,
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
        -- ── First-Ever Set (No current row exists) ────────────
        IF v_item_count > C_NORMAL_ITEM_MAX THEN
            IF p_confirmation IS NULL THEN
                RETURN jsonb_build_object(
                    'status', 'NEEDS_CONFIRMATION',
                    'message', format('Atypical item count (%s) exceeds normal range (%s-%s); confirmation required',
                                     v_item_count, C_NORMAL_ITEM_MIN, C_NORMAL_ITEM_MAX),
                    'reason', 'ATYPICAL_ITEM_COUNT',
                    'candidateFingerprint', v_new_fp,
                    'candidateItemCount', v_item_count,
                    'conflictDiffCount', 0
                );
            END IF;

            -- First ever: no active set fp or rev to check
            v_conf_val := public._validate_weekly_confirmation(
                p_confirmation, 'ATYPICAL_ITEM_COUNT', v_new_fp, NULL, NULL
            );
            IF NOT (v_conf_val->>'valid')::BOOLEAN THEN
                RETURN v_conf_val;
            END IF;

            v_status := 'REGISTERED_CONFIRMED_REVISION';
            v_new_rev := 1;
        ELSE
            v_status := 'REGISTERED_NEW';
            v_new_rev := 1;
        END IF;
    END IF;

    -- ── 5. Prepare New Current Payload ────────────────────────
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
        'registeredAt', v_now_iso,
        '_mutationAuthority', 'server_rpc'
    );

    -- ── 6. Atomic Write to user_data (SECURITY DEFINER bypasses RLS) ─
    INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
    VALUES (p_user_id, 'aiden_canonical_weekly_vocabulary_v1', v_new_payload, NOW())
    ON CONFLICT (user_id, data_key) DO UPDATE
    SET payload = v_new_payload,
        updated_at = NOW();

    INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
    VALUES (p_user_id, 'englishWeeklyWords', v_legacy_items, NOW())
    ON CONFLICT (user_id, data_key) DO UPDATE
    SET payload = v_legacy_items,
        updated_at = NOW();

    -- Record in history
    UPDATE public.weekly_vocabulary_history
    SET is_current = FALSE
    WHERE user_id = p_user_id AND is_current = TRUE;

    INSERT INTO public.weekly_vocabulary_history (
        user_id, set_id, revision, payload, registered_at, is_current
    ) VALUES (
        p_user_id,
        v_test_date,
        v_new_rev,
        v_new_payload,
        NOW(),
        TRUE
    )
    ON CONFLICT (user_id, set_id, revision) DO UPDATE
    SET payload = v_new_payload,
        is_current = TRUE;

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


-- ══════════════════════════════════════════════════════════════
-- 3. Scoped Agent Token Entrypoint
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.register_weekly_english_set(
    p_agent_token TEXT,
    p_candidate JSONB,
    p_confirmation JSONB DEFAULT NULL
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

    RETURN public._register_weekly_english_set_internal(v_user_id, p_candidate, p_confirmation);
END;
$$;

GRANT EXECUTE ON FUNCTION public.register_weekly_english_set(TEXT, JSONB, JSONB) TO anon, authenticated;


-- ══════════════════════════════════════════════════════════════
-- 4. Authenticated Guardian Entrypoint
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.register_weekly_english_set_as_guardian(
    p_candidate JSONB,
    p_confirmation JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object(
            'status', 'UNAUTHORIZED',
            'message', 'Authentication required for guardian modification'
        );
    END IF;

    RETURN public._register_weekly_english_set_internal(v_user_id, p_candidate, p_confirmation);
END;
$$;

GRANT EXECUTE ON FUNCTION public.register_weekly_english_set_as_guardian(JSONB, JSONB) TO authenticated;


-- ══════════════════════════════════════════════════════════════
-- 5. Token Management RPCs (List & Revoke by ID)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.list_weekly_english_agent_tokens()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_user_id UUID;
    v_tokens JSONB;
BEGIN
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object('status', 'UNAUTHORIZED', 'tokens', '[]'::JSONB);
    END IF;

    SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'id', id,
        'description', description,
        'isRevoked', is_revoked,
        'createdAt', created_at,
        'expiresAt', expires_at
    ) ORDER BY created_at DESC), '[]'::JSONB)
    INTO v_tokens
    FROM public.weekly_ingestion_tokens
    WHERE user_id = v_user_id;

    RETURN jsonb_build_object('status', 'OK', 'tokens', v_tokens);
END;
$$;

GRANT EXECUTE ON FUNCTION public.list_weekly_english_agent_tokens() TO authenticated;


CREATE OR REPLACE FUNCTION public.revoke_weekly_english_agent_token(
    p_token_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_user_id UUID;
    v_updated_id UUID;
BEGIN
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object('status', 'UNAUTHORIZED', 'message', 'Authentication required');
    END IF;

    UPDATE public.weekly_ingestion_tokens
    SET is_revoked = TRUE
    WHERE id = p_token_id AND user_id = v_user_id
    RETURNING id INTO v_updated_id;

    IF v_updated_id IS NULL THEN
        RETURN jsonb_build_object('status', 'NOT_FOUND', 'message', 'Token not found or unauthorized');
    END IF;

    RETURN jsonb_build_object('status', 'REVOKED', 'tokenId', v_updated_id);
END;
$$;

GRANT EXECUTE ON FUNCTION public.revoke_weekly_english_agent_token(UUID) TO authenticated;


-- ══════════════════════════════════════════════════════════════
-- 6. Tighten user_data RLS to block ordinary direct upserts of weekly keys
-- ══════════════════════════════════════════════════════════════
-- Drop loose policies
DROP POLICY IF EXISTS "Users can only insert their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can only update their own data" ON public.user_data;
DROP POLICY IF EXISTS "Users can insert via upsert" ON public.user_data;
DROP POLICY IF EXISTS "Authenticated users can upsert own data" ON public.user_data;

-- Recreate SELECT policy (users can still read their own data)
DROP POLICY IF EXISTS "Users can only view their own data" ON public.user_data;
CREATE POLICY "Users can only view their own data"
    ON public.user_data
    FOR SELECT
    USING (auth.uid() = user_id);

-- Restrict INSERT/UPDATE to non-server-authoritative keys only.
-- Server-authoritative keys MUST go through designated SECURITY DEFINER RPCs.
CREATE POLICY "Authenticated users can insert non-server-authoritative data"
    ON public.user_data
    FOR INSERT
    WITH CHECK (
        auth.uid() = user_id
        AND data_key NOT IN ('aiden_canonical_weekly_vocabulary_v1', 'englishWeeklyWords')
    );

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
