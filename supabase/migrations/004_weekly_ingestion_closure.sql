-- 004_weekly_ingestion_closure.sql
-- Closes all remaining defects in the weekly English agent ingestion pipeline:
--   1. Token provisioning RPC (create_weekly_english_agent_token)
--   2. Confirmed override contract (p_confirmation parameter)
--   3. Symmetric conflict detection (added + removed)
--   4. testDate actual calendar validation
--   5. Duplicate pair detection (identical answer+prompt)
--   6. Item count range adjustment (8-12 auto, 13-15 atypical/confirmation)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ══════════════════════════════════════════════════════════════
-- 1. Token Provisioning RPC
-- ══════════════════════════════════════════════════════════════
-- Authenticated guardian creates a scoped agent token.
-- Returns plaintext token ONCE. DB stores only SHA-256 hash.
-- Requires the caller to be authenticated (auth.uid() IS NOT NULL).

CREATE OR REPLACE FUNCTION public.create_weekly_english_agent_token(
    p_description TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_user_id UUID;
    v_plaintext TEXT;
    v_token_hash TEXT;
    v_token_id UUID;
BEGIN
    -- Must be authenticated
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object(
            'status', 'UNAUTHORIZED',
            'message', 'Authentication required to create agent tokens'
        );
    END IF;

    -- Generate cryptographically strong random token (32 bytes = 64 hex chars)
    v_plaintext := 'weit_' || encode(gen_random_bytes(32), 'hex');
    v_token_hash := encode(digest(v_plaintext, 'sha256'), 'hex');

    INSERT INTO public.weekly_ingestion_tokens (
        user_id, token_hash, scope, description, is_revoked
    ) VALUES (
        v_user_id, v_token_hash, 'weekly_english_ingestion', p_description, FALSE
    )
    RETURNING id INTO v_token_id;

    -- Return plaintext only this once; it cannot be recovered
    RETURN jsonb_build_object(
        'status', 'CREATED',
        'tokenId', v_token_id,
        'token', v_plaintext,
        'scope', 'weekly_english_ingestion',
        'message', 'Save this token now. It cannot be retrieved again.'
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.create_weekly_english_agent_token(TEXT) TO authenticated;

COMMENT ON FUNCTION public.create_weekly_english_agent_token(TEXT) IS
    'Creates a scoped capability token for weekly English agent ingestion. '
    'Returns the plaintext token exactly once. DB stores only the SHA-256 hash. '
    'Scope is strictly weekly_english_ingestion (register + read-back).';


-- ══════════════════════════════════════════════════════════════
-- 2-6. Replace register_weekly_english_set with closure-complete version
-- ══════════════════════════════════════════════════════════════

-- Conflict detection constants
-- CHANGE_THRESHOLD: max symmetric-diff items for auto-revision
-- NORMAL_ITEM_MIN/MAX: auto-activation item count range
-- ATYPICAL_ITEM_MAX: hard upper bound

DROP FUNCTION IF EXISTS public.register_weekly_english_set(TEXT, JSONB);

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
    -- Config constants
    C_CHANGE_THRESHOLD CONSTANT INT := 3;
    C_NORMAL_ITEM_MIN  CONSTANT INT := 8;
    C_NORMAL_ITEM_MAX  CONSTANT INT := 12;
    C_ATYPICAL_ITEM_MAX CONSTANT INT := 15;

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

    -- Duplicate detection
    v_dup_count INT;

    -- Calendar validation
    v_parsed_date DATE;

    -- Confirmation handling
    v_confirm_expected_fp TEXT;
    v_confirm_expected_rev INT;
    v_confirm_candidate_fp TEXT;
BEGIN
    -- ── 1. Authenticate scoped token via SHA-256 hash ──────────
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

    -- ── 2. Validate Candidate ─────────────────────────────────
    IF p_candidate IS NULL OR jsonb_typeof(p_candidate) <> 'object' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate must be a JSON object'
        );
    END IF;

    v_test_date := trim(COALESCE(p_candidate->>'testDate', ''));

    -- 2a. Format check
    IF v_test_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate testDate must match YYYY-MM-DD format'
        );
    END IF;

    -- 2b. Actual calendar date validation (#9)
    BEGIN
        v_parsed_date := v_test_date::DATE;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', format('Candidate testDate %s is not a valid calendar date', v_test_date)
        );
    END;

    -- 2c. Ambiguity check
    v_ambiguities := p_candidate->'ambiguities';
    IF v_ambiguities IS NOT NULL AND jsonb_typeof(v_ambiguities) = 'array' AND jsonb_array_length(v_ambiguities) > 0 THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate contains unresolved ambiguities; automatic activation forbidden'
        );
    END IF;

    -- 2d. Item array check
    v_items := p_candidate->'items';
    IF v_items IS NULL OR jsonb_typeof(v_items) <> 'array' THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate items must be a non-empty array'
        );
    END IF;

    v_item_count := jsonb_array_length(v_items);

    -- 2e. Item count range check (#7)
    IF v_item_count < C_NORMAL_ITEM_MIN OR v_item_count > C_ATYPICAL_ITEM_MAX THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', format('Candidate items count (%s) outside allowed bounds (%s-%s)',
                             v_item_count, C_NORMAL_ITEM_MIN, C_ATYPICAL_ITEM_MAX)
        );
    END IF;

    -- ── 3. Validate each item & build canonical item array ────
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

    -- ── 3b. Duplicate pair detection (#8) ─────────────────────
    -- Detect structurally identical (answer, prompt) pairs
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

    -- ── 4. Calculate new fingerprint ──────────────────────────
    v_new_fp := public._compute_weekly_content_fingerprint(v_canonical_items);

    -- ── 5. Inspect current active set ─────────────────────────
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

            -- ── 5a. Symmetric difference calculation (#3) ─────
            -- Count items added (in new but not in old)
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

            -- Count items removed (in old but not in new)
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

            -- ── 5b. Atypical item count check (#7) ───────────
            -- 13-15 items require confirmation even if diff is small
            IF v_item_count > C_NORMAL_ITEM_MAX AND p_confirmation IS NULL THEN
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

            IF v_sym_diff_count > C_CHANGE_THRESHOLD THEN
                -- ── NEEDS_CONFIRMATION or CONFIRMED_OVERRIDE ──
                IF p_confirmation IS NULL THEN
                    -- Case 3: Same date + large change => NEEDS_CONFIRMATION
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

                -- ── Confirmation supplied — validate it (#2) ──
                v_confirm_expected_fp := trim(COALESCE(p_confirmation->>'expectedActiveFingerprint', ''));
                v_confirm_expected_rev := COALESCE((p_confirmation->>'expectedActiveRevision')::INT, -1);
                v_confirm_candidate_fp := trim(COALESCE(p_confirmation->>'candidateFingerprint', ''));

                -- Guard: candidate fingerprint must match what we computed
                IF v_confirm_candidate_fp <> v_new_fp THEN
                    RETURN jsonb_build_object(
                        'status', 'CONFIRMATION_STALE',
                        'message', 'Confirmation candidateFingerprint does not match actual candidate content',
                        'expectedCandidateFp', v_confirm_candidate_fp,
                        'actualCandidateFp', v_new_fp
                    );
                END IF;

                -- Guard: expected active state must match current DB state
                IF v_confirm_expected_fp <> v_existing_fp OR v_confirm_expected_rev <> v_existing_rev THEN
                    RETURN jsonb_build_object(
                        'status', 'CONFIRMATION_STALE',
                        'message', 'Active set has changed since confirmation was issued; re-submit without confirmation to get fresh conflict info',
                        'expectedActiveFingerprint', v_confirm_expected_fp,
                        'expectedActiveRevision', v_confirm_expected_rev,
                        'actualActiveFingerprint', v_existing_fp,
                        'actualActiveRevision', v_existing_rev
                    );
                END IF;

                -- Confirmation is valid — proceed with override
                v_status := 'REGISTERED_CONFIRMED_REVISION';
                v_new_rev := v_existing_rev + 1;

            ELSE
                -- Case 2: Same date + small change (1-C_CHANGE_THRESHOLD items) => REGISTERED_REVISION
                v_status := 'REGISTERED_REVISION';
                v_new_rev := v_existing_rev + 1;
            END IF;
        ELSE
            -- ── 5c. Atypical item count on new date (#7) ──────
            IF v_item_count > C_NORMAL_ITEM_MAX AND p_confirmation IS NULL THEN
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
        -- ── Atypical item count with no existing set (#7) ─────
        IF v_item_count > C_NORMAL_ITEM_MAX AND p_confirmation IS NULL THEN
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

        -- No current row exists: First time registration
        v_status := 'REGISTERED_NEW';
        v_new_rev := 1;
    END IF;

    -- ── 6. Prepare New Current Payload ────────────────────────
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

    -- ── 7. Atomic Activation into user_data ───────────────────
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

    -- ── 8. Return machine-readable result ─────────────────────
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

-- Grant on updated function signature (3 params)
GRANT EXECUTE ON FUNCTION public.register_weekly_english_set(TEXT, JSONB, JSONB) TO anon, authenticated;

COMMENT ON FUNCTION public.register_weekly_english_set(TEXT, JSONB, JSONB) IS
    'Atomic RPC for weekly English vocabulary registration with: '
    'symmetric conflict detection, confirmed override, '
    'calendar date validation, duplicate pair rejection, '
    'and atypical item count gating (8-12 auto, 13-15 confirmation).';
