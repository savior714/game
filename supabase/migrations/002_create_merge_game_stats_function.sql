-- Atomic merge function for game stats
-- Prevents lost updates by performing server-side merge instead of client-side upsert

CREATE OR REPLACE FUNCTION merge_game_stats(
    p_user_id UUID,
    p_data_key TEXT,
    p_payload JSONB
)
RETURNS JSONB AS $$
DECLARE
    v_existing JSONB;
    v_merged JSONB;
    v_domain_keys TEXT[];
    v_level_keys TEXT[];
    v_weakness_keys TEXT[];
    v_dk TEXT;
    v_lv TEXT;
    v_wk TEXT;
    v_existing_dom JSONB;
    v_new_dom JSONB;
    v_merged_dom JSONB;
    v_merged_levels JSONB := '{}'::jsonb;
    v_merged_weaknesses JSONB := '{}'::jsonb;
    v_existing_val JSONB;
    v_new_val JSONB;
BEGIN
    -- Get existing payload if it exists
    SELECT payload INTO v_existing
    FROM public.user_data
    WHERE user_id = p_user_id AND data_key = p_data_key;

    -- If no existing data, just use new payload
    IF v_existing IS NULL THEN
        v_merged := p_payload || jsonb_build_object('_updated_at', EXTRACT(EPOCH FROM NOW())::bigint);
    ELSE
        -- Get all domain keys from both payloads
        v_domain_keys := ARRAY(
            SELECT jsonb_object_keys(v_existing)
            UNION
            SELECT jsonb_object_keys(p_payload)
        );

        -- Process each domain
        FOR v_dk IN SELECT unnest(v_domain_keys) LOOP
            v_existing_dom := COALESCE(v_existing->v_dk, '{}'::jsonb);
            v_new_dom := COALESCE(p_payload->v_dk, '{}'::jsonb);

            -- Merge levels: sum numeric values for each level
            v_merged_levels := '{}'::jsonb;
            v_level_keys := ARRAY(
                SELECT jsonb_object_keys(v_existing_dom->'levels')
                UNION
                SELECT jsonb_object_keys(v_new_dom->'levels')
            );

            FOR v_lv IN SELECT unnest(v_level_keys) LOOP
                v_existing_val := v_existing_dom->'levels'->v_lv;
                v_new_val := v_new_dom->'levels'->v_lv;

                v_merged_levels := v_merged_levels || jsonb_build_object(
                    v_lv,
                    jsonb_build_object(
                        'attempts', COALESCE((v_existing_val->>'attempts')::int, 0) + COALESCE((v_new_val->>'attempts')::int, 0),
                        'correct', COALESCE((v_existing_val->>'correct')::int, 0) + COALESCE((v_new_val->>'correct')::int, 0),
                        'totalTime', COALESCE((v_existing_val->>'totalTime')::int, 0) + COALESCE((v_new_val->>'totalTime')::int, 0)
                    )
                );
            END LOOP;

            -- Merge weaknesses: sum numeric values for each weakness
            v_merged_weaknesses := '{}'::jsonb;
            v_weakness_keys := ARRAY(
                SELECT jsonb_object_keys(v_existing_dom->'weaknesses')
                UNION
                SELECT jsonb_object_keys(v_new_dom->'weaknesses')
            );

            FOR v_wk IN SELECT unnest(v_weakness_keys) LOOP
                v_existing_val := v_existing_dom->'weaknesses'->v_wk;
                v_new_val := v_new_dom->'weaknesses'->v_wk;

                v_merged_weaknesses := v_merged_weaknesses || jsonb_build_object(
                    v_wk,
                    jsonb_build_object(
                        'attempts', COALESCE((v_existing_val->>'attempts')::int, 0) + COALESCE((v_new_val->>'attempts')::int, 0),
                        'correct', COALESCE((v_existing_val->>'correct')::int, 0) + COALESCE((v_new_val->>'correct')::int, 0)
                    )
                );
            END LOOP;

            -- Build merged domain object
            v_merged := v_merged || jsonb_build_object(
                v_dk,
                jsonb_build_object('levels', v_merged_levels, 'weaknesses', v_merged_weaknesses)
            );
        END LOOP;

        -- Add _updated_at timestamp
        v_merged := v_merged || jsonb_build_object('_updated_at', EXTRACT(EPOCH FROM NOW())::bigint);
    END IF;

    -- Upsert the merged result
    INSERT INTO public.user_data (user_id, data_key, payload, updated_at)
    VALUES (p_user_id, p_data_key, v_merged, NOW())
    ON CONFLICT (user_id, data_key) DO UPDATE
    SET payload = v_merged,
        updated_at = NOW()
    RETURNING payload INTO v_merged;

    RETURN v_merged;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION merge_game_stats IS 'Atomically merges game stats for a user, preventing lost updates during concurrent pushes';
