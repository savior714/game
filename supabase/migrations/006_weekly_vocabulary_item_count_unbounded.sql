-- 006_weekly_vocabulary_item_count_unbounded.sql
-- Removes brittle 8-15 item-count product assumptions from weekly vocabulary ingestion.
--   1. Replaces _register_weekly_english_set_internal to allow arbitrary item count (> 0).
--   2. Preserves:
--      - empty items array rejection (items must be non-empty)
--      - calendar date validation
--      - unresolved ambiguity rejection
--      - duplicate (answer, prompt) pair rejection
--      - multi-sense support & itemId generation
--      - LARGE_SYMMETRIC_DIFF confirmation on same date (threshold > 3)
--      - token-based / guardian-based scoped security & history preservation
--      - canonical & legacy projection atomic sync

CREATE OR REPLACE FUNCTION public._register_weekly_english_set_internal(
    p_user_id UUID,
    p_candidate JSONB,
    p_confirmation JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions, pg_temp
AS $$
DECLARE
    C_CHANGE_THRESHOLD CONSTANT INT := 3;

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

    -- Item count non-empty check
    IF v_item_count = 0 THEN
        RETURN jsonb_build_object(
            'status', 'REJECTED_INVALID',
            'message', 'Candidate items array must not be empty'
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

        v_p_hash := substr(encode(sha256(v_prompt::bytea), 'hex'), 1, 8);
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

            -- Large Symmetric Diff Check (> C_CHANGE_THRESHOLD)
            IF v_sym_diff_count > C_CHANGE_THRESHOLD THEN
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
                v_status := 'REGISTERED_REVISION';
                v_new_rev := v_existing_rev + 1;
            END IF;

        ELSE
            -- ── Different Date: clean new week activation ────
            v_status := 'REGISTERED_NEW';
            v_new_rev := 1;
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
        v_status := 'REGISTERED_NEW';
        v_new_rev := 1;
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
