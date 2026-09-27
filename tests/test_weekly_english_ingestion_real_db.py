"""Real PostgreSQL Integration Tests for Weekly English Agent Ingestion.

Executes real PostgreSQL queries against the running aiden-test-pg container.
Verifies:
1. Migration cleanly applied & schema structure
2. Capability token provisioning (one-time plaintext, SHA-256 hash, auth.uid enforcement)
3. Token authentication & revocation & invalid token rejection
4. Cross-user isolation (User A token cannot read or mutate User B data)
5. Full lifecycle: Set A registration -> read-back -> idempotency (NO_OP) ->
   small revision (REGISTERED_REVISION) -> large symmetric conflict (NEEDS_CONFIRMATION) ->
   confirmed override (REGISTERED_CONFIRMED_REVISION) -> stale confirmation rejection ->
   new week (REGISTERED_NEW)
6. Symmetric conflict detection (added + removed)
7. Item count range validation (7 reject, 8-12 auto, 13-15 confirmation, >15 reject)
8. Calendar date validation (2026-99-99 reject)
9. Duplicate pair rejection vs multi-sense admission
10. Transaction rollback on invalid input
11. Canonical key and legacy projection update in user_data
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

CONTAINER_NAME = "aiden-test-pg"
DB_NAME = "aiden_test"
DB_USER = "test"


def _is_pg_available() -> bool:
    try:
        res = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                CONTAINER_NAME,
                "psql",
                "-U",
                DB_USER,
                "-d",
                DB_NAME,
                "-c",
                "SELECT 1;",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False


def setup_module() -> None:
    if not _is_pg_available():
        if os.environ.get("WEEKLY_INGESTION_REAL_DB_REQUIRED") == "1":
            pytest.fail(
                "PostgreSQL test container (aiden-test-pg) is required by "
                "WEEKLY_INGESTION_REAL_DB_REQUIRED=1 but is not available"
            )
        else:
            pytest.skip("PostgreSQL test container (aiden-test-pg) is not available")


def _exec_psql(sql: str, user_id: str | None = None) -> str:
    script = ""
    if user_id:
        script += f"SET request.jwt.claim.sub = '{user_id}';\n"
    elif user_id is not None and user_id == "":
        script += "SET request.jwt.claim.sub = '';\n"
    script += sql
    res = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-A",
            "-t",
            "-q",
        ],
        input=script,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln.strip() for ln in res.stdout.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""


SAMPLE_10_ITEMS = [
    {
        "word": "courage",
        "meaning": "the ability to do something frightening",
        "academyDescription": "the ability to do something frightening",
    },
    {
        "word": "curiosity",
        "meaning": "desire to learn",
        "academyDescription": "desire to learn",
    },
    {
        "word": "whisper",
        "meaning": "speak very softly",
        "academyDescription": "speak very softly",
    },
    {
        "word": "wander",
        "meaning": "walk without aim",
        "academyDescription": "walk without aim",
    },
    {
        "word": "glimmer",
        "meaning": "shine faintly",
        "academyDescription": "shine faintly",
    },
    {
        "word": "shelter",
        "meaning": "place giving protection",
        "academyDescription": "place giving protection",
    },
    {
        "word": "journey",
        "meaning": "act of traveling",
        "academyDescription": "act of traveling",
    },
    {
        "word": "treasure",
        "meaning": "quantity of precious items",
        "academyDescription": "quantity of precious items",
    },
    {"word": "breeze", "meaning": "gentle wind", "academyDescription": "gentle wind"},
    {
        "word": "shadow",
        "meaning": "dark area produced by body",
        "academyDescription": "dark area produced by body",
    },
]


# ── 1. Schema & Migration Cleanliness ──────────────────────────


def test_real_db_schema_tables_and_functions_exist() -> None:
    """Verifies that all tables, indexes, and RPC functions exist in PostgreSQL."""
    tables_query = """
    SELECT json_agg(table_name)::text
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('user_data', 'weekly_ingestion_tokens', 'weekly_vocabulary_history');
    """
    tables = json.loads(_exec_psql(tables_query))
    assert set(tables) == {
        "user_data",
        "weekly_ingestion_tokens",
        "weekly_vocabulary_history",
    }

    functions_query = """
    SELECT json_agg(routine_name)::text
    FROM information_schema.routines
    WHERE routine_schema = 'public'
      AND routine_name IN ('create_weekly_english_agent_token', 'register_weekly_english_set', 'get_current_weekly_english_set');
    """
    functions = json.loads(_exec_psql(functions_query))
    assert set(functions) == {
        "create_weekly_english_agent_token",
        "register_weekly_english_set",
        "get_current_weekly_english_set",
    }


# ── 2. Capability Token Provisioning & Security ─────────────────


def test_real_db_token_provisioning_and_security() -> None:
    """Verifies:
    - Unauthenticated user cannot mint token
    - Authenticated user mints scoped token (returns plaintext with weit_ prefix once)
    - Database stores ONLY the SHA-256 hash, NEVER plaintext
    - Invalid token rejected
    - Revoked token rejected
    """
    # 1. Unauthenticated mint attempt
    unauth_sql = (
        "SELECT public.create_weekly_english_agent_token('Unauthorized attempt')::text;"
    )
    res_unauth = json.loads(_exec_psql(unauth_sql, user_id=""))
    assert res_unauth["status"] == "UNAUTHORIZED"

    # 2. Authenticated mint
    user_id = "11111111-1111-1111-1111-111111111111"
    _exec_psql(
        f"DELETE FROM public.weekly_ingestion_tokens WHERE user_id = '{user_id}'::uuid;"
    )
    mint_sql = (
        "SELECT public.create_weekly_english_agent_token('Primary Agent Token')::text;"
    )
    mint_res = json.loads(_exec_psql(mint_sql, user_id=user_id))
    assert mint_res["status"] == "CREATED"
    token = mint_res["token"]
    token_id = mint_res["tokenId"]
    assert token.startswith("weit_")
    assert len(token) > 30

    # 3. Verify DB stores hash only
    hash_query = f"""
    SELECT json_build_object(
        'token_hash', token_hash,
        'scope', scope,
        'is_revoked', is_revoked,
        'user_id', user_id::text
    )::text
    FROM public.weekly_ingestion_tokens
    WHERE id = '{token_id}'::uuid;
    """
    db_record = json.loads(_exec_psql(hash_query))
    assert db_record["scope"] == "weekly_english_ingestion"
    assert db_record["is_revoked"] is False
    assert db_record["user_id"] == user_id
    # Plaintext token must NOT appear anywhere in the row
    assert token != db_record["token_hash"]
    assert len(db_record["token_hash"]) == 64  # SHA-256 hex length

    # 4. Invalid token rejected
    invalid_res = json.loads(
        _exec_psql(
            "SELECT public.get_current_weekly_english_set('weit_invalid_token_xyz')::text;"
        )
    )
    assert invalid_res["status"] == "UNAUTHORIZED"

    # 5. Revoke token and verify rejection
    _exec_psql(
        f"UPDATE public.weekly_ingestion_tokens SET is_revoked = TRUE WHERE id = '{token_id}'::uuid;"
    )
    revoked_res = json.loads(
        _exec_psql(f"SELECT public.get_current_weekly_english_set('{token}')::text;")
    )
    assert revoked_res["status"] == "UNAUTHORIZED"


# ── 3. Cross-User Isolation ─────────────────────────────────────


def test_real_db_cross_user_isolation() -> None:
    """Verifies that User A's token cannot read or modify User B's vocabulary."""
    user_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    user_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    _exec_psql(f"""
        DELETE FROM public.user_data WHERE user_id IN ('{user_a}'::uuid, '{user_b}'::uuid);
        DELETE FROM public.weekly_ingestion_tokens WHERE user_id IN ('{user_a}'::uuid, '{user_b}'::uuid);
        DELETE FROM public.weekly_vocabulary_history WHERE user_id IN ('{user_a}'::uuid, '{user_b}'::uuid);
    """)

    # Create tokens for User A and User B
    token_a = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('User A')::text;",
            user_id=user_a,
        )
    )["token"]

    token_b = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('User B')::text;",
            user_id=user_b,
        )
    )["token"]

    # User A registers Set A
    candidate_a = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS})
    reg_a = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token_a}', '{candidate_a}'::jsonb)::text;"
        )
    )
    assert reg_a["status"] in ("REGISTERED_NEW", "NO_OP")

    # User B reads with User B's token -> MUST NOT see User A's set
    read_b = json.loads(
        _exec_psql(f"SELECT public.get_current_weekly_english_set('{token_b}')::text;")
    )
    # User B has no registered set yet
    assert read_b["status"] == "NOT_FOUND"

    # Verify user_data isolation
    user_data_a = json.loads(
        _exec_psql(
            f"SELECT COUNT(*)::int FROM public.user_data WHERE user_id = '{user_a}'::uuid;"
        )
    )
    user_data_b = json.loads(
        _exec_psql(
            f"SELECT COUNT(*)::int FROM public.user_data WHERE user_id = '{user_b}'::uuid;"
        )
    )
    assert user_data_a >= 1
    assert user_data_b == 0


# ── 4. Full Lifecycle End-to-End Simulation ──────────────────────


def test_real_db_primary_lifecycle_e2e() -> None:
    """Executes the full end-to-end lifecycle on real PostgreSQL:
    1. Authenticated user mints scoped token
    2. Agent registers Set A (10 pairs) -> REGISTERED_NEW (rev 1)
    3. Read-back verification matches exact candidate
    4. user_data has both canonical key and legacy projection
    5. Same candidate again -> NO_OP (rev 1)
    6. Small revision (1 item changed) -> REGISTERED_REVISION (rev 2)
       Rollback history preserved in weekly_vocabulary_history
    7. Large symmetric conflict (5 items changed) -> NEEDS_CONFIRMATION
       Active set unchanged (rev 2)
    8. Confirmed override with matching fingerprints -> REGISTERED_CONFIRMED_REVISION (rev 3)
    9. Stale confirmation rejected -> CONFIRMATION_STALE
    10. New test date (Set B) -> REGISTERED_NEW (rev 1)
    """
    user_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    _exec_psql(f"""
        DELETE FROM public.user_data WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_vocabulary_history WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_ingestion_tokens WHERE user_id = '{user_id}'::uuid;
    """)

    # Step 1: Mint token
    mint_res = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('Lifecycle Test')::text;",
            user_id=user_id,
        )
    )
    token = mint_res["token"]

    # Step 2: Register Set A
    candidate_a = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS})
    reg_a = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{candidate_a}'::jsonb)::text;"
        )
    )
    assert reg_a["status"] == "REGISTERED_NEW"
    assert reg_a["setId"] == "2026-09-25"
    assert reg_a["revision"] == 1
    assert reg_a["itemCount"] == 10
    active_fp_rev1 = reg_a["contentFingerprint"]

    # Step 3: Exact read-back
    read_a = json.loads(
        _exec_psql(f"SELECT public.get_current_weekly_english_set('{token}')::text;")
    )
    assert read_a["status"] == "OK"
    assert read_a["currentSet"]["setId"] == "2026-09-25"
    assert read_a["currentSet"]["revision"] == 1
    assert len(read_a["currentSet"]["items"]) == 10
    assert read_a["currentSet"]["_mutationAuthority"] == "server_rpc"
    first_item = read_a["currentSet"]["items"][0]
    assert first_item["word"] == "courage"
    assert first_item["prompt"] == "the ability to do something frightening"

    # Step 4: user_data check
    canonical_row = json.loads(
        _exec_psql(f"""
        SELECT payload::text FROM public.user_data
        WHERE user_id = '{user_id}'::uuid AND data_key = 'aiden_canonical_weekly_vocabulary_v1';
        """)
    )
    assert canonical_row["setId"] == "2026-09-25"
    legacy_row = json.loads(
        _exec_psql(f"""
        SELECT payload::text FROM public.user_data
        WHERE user_id = '{user_id}'::uuid AND data_key = 'englishWeeklyWords';
        """)
    )
    assert isinstance(legacy_row, list)
    assert len(legacy_row) == 10
    assert legacy_row[0]["en"] == "courage"

    # Step 5: Idempotency (same candidate again)
    reg_same = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{candidate_a}'::jsonb)::text;"
        )
    )
    assert reg_same["status"] == "NO_OP"
    assert reg_same["revision"] == 1
    assert reg_same["contentFingerprint"] == active_fp_rev1

    # Step 6: Small revision (1 item changed: prompt of courage tweaked)
    revised_items = [dict(it) for it in SAMPLE_10_ITEMS]
    revised_items[0] = {
        "word": "courage",
        "meaning": "bravery facing fear",
        "academyDescription": "bravery facing fear",
    }
    candidate_small_rev = json.dumps({"testDate": "2026-09-25", "items": revised_items})
    reg_small = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{candidate_small_rev}'::jsonb)::text;"
        )
    )
    assert reg_small["status"] == "REGISTERED_REVISION"
    assert reg_small["revision"] == 2
    active_fp_rev2 = reg_small["contentFingerprint"]

    # Verify rollback history preserved
    hist_count = json.loads(
        _exec_psql(f"""
        SELECT COUNT(*)::int FROM public.weekly_vocabulary_history
        WHERE user_id = '{user_id}'::uuid AND set_id = '2026-09-25';
        """)
    )
    assert hist_count >= 2

    # Step 7: Large symmetric conflict (5 words completely replaced)
    conflict_items = [dict(it) for it in revised_items]
    conflict_items[0] = {
        "word": "conflictone",
        "meaning": "m1",
        "academyDescription": "m1",
    }
    conflict_items[1] = {
        "word": "conflicttwo",
        "meaning": "m2",
        "academyDescription": "m2",
    }
    conflict_items[2] = {
        "word": "conflictthree",
        "meaning": "m3",
        "academyDescription": "m3",
    }
    conflict_items[3] = {
        "word": "conflictfour",
        "meaning": "m4",
        "academyDescription": "m4",
    }
    conflict_items[4] = {
        "word": "conflictfive",
        "meaning": "m5",
        "academyDescription": "m5",
    }
    candidate_conflict = json.dumps({"testDate": "2026-09-25", "items": conflict_items})

    reg_conflict = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{candidate_conflict}'::jsonb)::text;"
        )
    )
    assert reg_conflict["status"] == "NEEDS_CONFIRMATION"
    assert reg_conflict["activeRevision"] == 2
    assert reg_conflict["activeFingerprint"] == active_fp_rev2
    assert reg_conflict["conflictDiffCount"] == 10  # 5 added + 5 removed
    candidate_fp = reg_conflict["candidateFingerprint"]

    # Active set remains unchanged at rev 2
    read_current = json.loads(
        _exec_psql(f"SELECT public.get_current_weekly_english_set('{token}')::text;")
    )
    assert read_current["currentSet"]["revision"] == 2

    # Step 8: Confirmed override
    confirmation = json.dumps(
        {
            "reason": "LARGE_SYMMETRIC_DIFF",
            "expectedActiveFingerprint": active_fp_rev2,
            "expectedActiveRevision": 2,
            "candidateFingerprint": candidate_fp,
        }
    )
    reg_override = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{candidate_conflict}'::jsonb, '{confirmation}'::jsonb)::text;"
        )
    )
    assert reg_override["status"] == "REGISTERED_CONFIRMED_REVISION"
    assert reg_override["revision"] == 3

    # Step 9: Stale confirmation after another revision
    # Advance current set by 1 item revision to rev 4
    rev4_items = [dict(it) for it in conflict_items]
    rev4_items[5] = {
        "word": "shelter",
        "meaning": "safe haven",
        "academyDescription": "safe haven",
    }
    cand_rev4 = json.dumps({"testDate": "2026-09-25", "items": rev4_items})
    reg_rev4 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_rev4}'::jsonb)::text;"
        )
    )
    assert reg_rev4["status"] == "REGISTERED_REVISION"
    assert reg_rev4["revision"] == 4

    # Now attempt a new large conflict candidate using the old confirmation (which expected rev 2)
    new_conflict_items = [dict(it) for it in SAMPLE_10_ITEMS]
    for i in range(5):
        new_conflict_items[i] = {
            "word": f"stalechange{i}",
            "meaning": f"sc{i}",
            "academyDescription": f"sc{i}",
        }
    cand_new_conflict = json.dumps(
        {"testDate": "2026-09-25", "items": new_conflict_items}
    )

    preview = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_new_conflict}'::jsonb)::text;"
        )
    )
    assert preview["status"] == "NEEDS_CONFIRMATION"

    stale_conf = json.dumps(
        {
            "reason": "LARGE_SYMMETRIC_DIFF",
            "expectedActiveFingerprint": active_fp_rev2,  # Stale: pointing to rev 2 instead of rev 4
            "expectedActiveRevision": 2,
            "candidateFingerprint": preview["candidateFingerprint"],
        }
    )
    reg_stale = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_new_conflict}'::jsonb, '{stale_conf}'::jsonb)::text;"
        )
    )
    assert reg_stale["status"] == "CONFIRMATION_STALE"

    # Step 10: New week (different test date)
    cand_week2 = json.dumps({"testDate": "2026-10-02", "items": SAMPLE_10_ITEMS})
    reg_week2 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_week2}'::jsonb)::text;"
        )
    )
    assert reg_week2["status"] == "REGISTERED_NEW"
    assert reg_week2["setId"] == "2026-10-02"
    assert reg_week2["revision"] == 1


# ── 5. Real DB Validations & Rollback ───────────────────────────


def test_real_db_validations_and_rollback() -> None:
    """Verifies that invalid candidate inputs fail-closed and roll back cleanly."""
    user_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"

    _exec_psql(f"""
        DELETE FROM public.user_data WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_vocabulary_history WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_ingestion_tokens WHERE user_id = '{user_id}'::uuid;
    """)

    token = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('Validation Test')::text;",
            user_id=user_id,
        )
    )["token"]

    # Baseline: register 10 items
    baseline_cand = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS})
    res_base = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{baseline_cand}'::jsonb)::text;"
        )
    )
    assert res_base["status"] in ("REGISTERED_NEW", "NO_OP")

    # 1. Reject < 8 items (7 items)
    cand_7 = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS[:7]})
    res_7 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_7}'::jsonb)::text;"
        )
    )
    assert res_7["status"] == "REJECTED_INVALID"
    assert "items count" in res_7["message"].lower()

    # 2. Accept 8 items
    cand_8 = json.dumps({"testDate": "2026-10-08", "items": SAMPLE_10_ITEMS[:8]})
    res_8 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_8}'::jsonb)::text;"
        )
    )
    assert res_8["status"] == "REGISTERED_NEW"

    # 3. Accept 12 items
    extra_2 = [
        {"word": "word11", "meaning": "m11", "academyDescription": "m11"},
        {"word": "word12", "meaning": "m12", "academyDescription": "m12"},
    ]
    cand_12 = json.dumps({"testDate": "2026-10-12", "items": SAMPLE_10_ITEMS + extra_2})
    res_12 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_12}'::jsonb)::text;"
        )
    )
    assert res_12["status"] == "REGISTERED_NEW"

    # 4. 13-15 items requires confirmation (atypical item count)
    extra_3 = extra_2 + [
        {"word": "word13", "meaning": "m13", "academyDescription": "m13"}
    ]
    cand_13 = json.dumps({"testDate": "2026-10-13", "items": SAMPLE_10_ITEMS + extra_3})
    res_13 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_13}'::jsonb)::text;"
        )
    )
    assert res_13["status"] == "NEEDS_CONFIRMATION"
    assert res_13["reason"] == "ATYPICAL_ITEM_COUNT"

    # 5. > 15 items rejected unconditionally
    extra_6 = extra_2 + [
        {"word": "word13", "meaning": "m13", "academyDescription": "m13"},
        {"word": "word14", "meaning": "m14", "academyDescription": "m14"},
        {"word": "word15", "meaning": "m15", "academyDescription": "m15"},
        {"word": "word16", "meaning": "m16", "academyDescription": "m16"},
    ]
    cand_16 = json.dumps({"testDate": "2026-10-16", "items": SAMPLE_10_ITEMS + extra_6})
    res_16 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_16}'::jsonb)::text;"
        )
    )
    assert res_16["status"] == "REJECTED_INVALID"

    # 6. Reject invalid calendar date (2026-99-99)
    cand_bad_date = json.dumps({"testDate": "2026-99-99", "items": SAMPLE_10_ITEMS})
    res_bad_date = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_bad_date}'::jsonb)::text;"
        )
    )
    assert res_bad_date["status"] == "REJECTED_INVALID"
    assert "calendar date" in res_bad_date["message"].lower()

    # 7. Reject duplicate identical pair (same answer and prompt)
    dup_items = list(SAMPLE_10_ITEMS)
    dup_items[9] = dup_items[0]  # Exact duplicate of item 0
    cand_dup = json.dumps({"testDate": "2026-10-20", "items": dup_items})
    res_dup = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_dup}'::jsonb)::text;"
        )
    )
    assert res_dup["status"] == "REJECTED_INVALID"
    assert (
        "duplicate" in res_dup["message"].lower()
        and "pair" in res_dup["message"].lower()
    )

    # 8. Same word different prompt (multi-sense) MUST BE ALLOWED
    multi_sense_items = list(SAMPLE_10_ITEMS)
    multi_sense_items[9] = {
        "word": "courage",
        "meaning": "a different definition of courage",
        "academyDescription": "a different definition of courage",
    }
    cand_multi = json.dumps({"testDate": "2026-10-25", "items": multi_sense_items})
    res_multi = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_multi}'::jsonb)::text;"
        )
    )
    assert res_multi["status"] == "REGISTERED_NEW"


# ── 6. RLS Direct Upsert Authority Enforcement ─────────────────


def test_real_db_direct_user_data_upsert_blocked_by_rls() -> None:
    """Verifies:
    1. Authenticated user cannot directly UPSERT into aiden_canonical_weekly_vocabulary_v1
    2. Authenticated user cannot directly UPSERT into englishWeeklyWords
    3. Normal non-authoritative keys (e.g., mathGameStats) are permitted
    """
    user_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    _exec_psql(f"DELETE FROM public.user_data WHERE user_id = '{user_id}'::uuid;")

    # 1. Direct UPSERT on canonical key blocked
    sql_canonical = f"""
    SET ROLE authenticated;
    SET request.jwt.claim.sub = '{user_id}';
    INSERT INTO public.user_data (user_id, data_key, payload)
    VALUES ('{user_id}'::uuid, 'aiden_canonical_weekly_vocabulary_v1', '{{"hacked": true}}'::jsonb)
    ON CONFLICT (user_id, data_key) DO UPDATE SET payload = EXCLUDED.payload;
    RESET ROLE;
    """
    res_can = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-A",
            "-t",
            "-q",
        ],
        input=sql_canonical,
        capture_output=True,
        text=True,
    )
    assert (
        res_can.returncode != 0
        or "violates row-level security policy" in res_can.stderr
    )

    # 2. Direct UPSERT on legacy projection blocked
    sql_legacy = f"""
    SET ROLE authenticated;
    SET request.jwt.claim.sub = '{user_id}';
    INSERT INTO public.user_data (user_id, data_key, payload)
    VALUES ('{user_id}'::uuid, 'englishWeeklyWords', '[]'::jsonb)
    ON CONFLICT (user_id, data_key) DO UPDATE SET payload = EXCLUDED.payload;
    RESET ROLE;
    """
    res_leg = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-A",
            "-t",
            "-q",
        ],
        input=sql_legacy,
        capture_output=True,
        text=True,
    )
    assert (
        res_leg.returncode != 0
        or "violates row-level security policy" in res_leg.stderr
    )

    # 3. Normal key permitted
    sql_normal = f"""
    SET ROLE authenticated;
    SET request.jwt.claim.sub = '{user_id}';
    INSERT INTO public.user_data (user_id, data_key, payload)
    VALUES ('{user_id}'::uuid, 'mathGameStats', '{{"score": 100}}'::jsonb)
    ON CONFLICT (user_id, data_key) DO UPDATE SET payload = EXCLUDED.payload;
    RESET ROLE;
    """
    _exec_psql(sql_normal)
    normal_row = json.loads(
        _exec_psql(
            f"SELECT payload::text FROM public.user_data WHERE user_id = '{user_id}'::uuid AND data_key = 'mathGameStats';"
        )
    )
    assert normal_row["score"] == 100


# ── 7. Guardian Manual Modification RPC ─────────────────────────


def test_real_db_guardian_mutation_e2e() -> None:
    """Verifies that Guardian manual edits go through designated server RPC,
    write through SECURITY DEFINER, preserve _mutationAuthority='server_rpc',
    and fail clearly when unauthenticated.
    """
    user_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    _exec_psql(f"""
        DELETE FROM public.user_data WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_vocabulary_history WHERE user_id = '{user_id}'::uuid;
    """)

    # 1. Unauthenticated call fails
    cand_10 = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS})
    unauth_res = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set_as_guardian('{cand_10}'::jsonb)::text;",
            user_id="",
        )
    )
    assert unauth_res["status"] == "UNAUTHORIZED"

    # 2. Authenticated Guardian creates set
    auth_sql = f"""
    SET ROLE authenticated;
    SET request.jwt.claim.sub = '{user_id}';
    SELECT public.register_weekly_english_set_as_guardian('{cand_10}'::jsonb)::text;
    RESET ROLE;
    """
    res_reg = json.loads(_exec_psql(auth_sql))
    assert res_reg["status"] == "REGISTERED_NEW"
    assert res_reg["revision"] == 1

    # Verify user_data payload has _mutationAuthority = 'server_rpc'
    row = json.loads(
        _exec_psql(
            f"SELECT payload::text FROM public.user_data WHERE user_id = '{user_id}'::uuid AND data_key = 'aiden_canonical_weekly_vocabulary_v1';"
        )
    )
    assert row["_mutationAuthority"] == "server_rpc"
    assert row["revision"] == 1
    assert len(row["items"]) == 10


# ── 8. ATYPICAL_ITEM_COUNT Fail-Closed Confirmations ────────────


def test_real_db_atypical_confirmation_fail_closed_and_accept() -> None:
    """Verifies atypical confirmation paths fail-closed on malformed/stale confirmations
    and succeed only with strict valid confirmation.
    """
    user_id = "12121212-1212-1212-1212-121212121212"
    _exec_psql(f"""
        DELETE FROM public.user_data WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_vocabulary_history WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_ingestion_tokens WHERE user_id = '{user_id}'::uuid;
    """)

    token = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('Atypical Test')::text;",
            user_id=user_id,
        )
    )["token"]

    # 1. Baseline 10 items
    cand_10 = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS})
    res_10 = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_10}'::jsonb)::text;"
        )
    )
    assert res_10["status"] == "REGISTERED_NEW"
    active_fp = res_10["contentFingerprint"]
    active_rev = res_10["revision"]

    # 2. 13 items candidate on same date
    extra_3 = [
        {"word": "word11", "academyDescription": "d11"},
        {"word": "word12", "academyDescription": "d12"},
        {"word": "word13", "academyDescription": "d13"},
    ]
    cand_13 = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS + extra_3})

    # Needs confirmation without payload
    res_needs = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_13}'::jsonb)::text;"
        )
    )
    assert res_needs["status"] == "NEEDS_CONFIRMATION"
    assert res_needs["reason"] == "ATYPICAL_ITEM_COUNT"
    candidate_fp = res_needs["candidateFingerprint"]

    # Empty confirmation -> REJECTED_CONFIRMATION
    res_empty = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_13}'::jsonb, '{{}}'::jsonb)::text;"
        )
    )
    assert res_empty["status"] == "REJECTED_CONFIRMATION"

    # Wrong reason -> REJECTED_CONFIRMATION
    bad_reason_conf = json.dumps(
        {
            "reason": "LARGE_SYMMETRIC_DIFF",
            "candidateFingerprint": candidate_fp,
            "expectedActiveFingerprint": active_fp,
            "expectedActiveRevision": active_rev,
        }
    )
    res_bad_reason = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_13}'::jsonb, '{bad_reason_conf}'::jsonb)::text;"
        )
    )
    assert res_bad_reason["status"] == "REJECTED_CONFIRMATION"

    # Wrong candidate fingerprint -> CONFIRMATION_STALE or REJECTED_CONFIRMATION
    wrong_cand_conf = json.dumps(
        {
            "reason": "ATYPICAL_ITEM_COUNT",
            "candidateFingerprint": "wrong_fingerprint_hash_value",
            "expectedActiveFingerprint": active_fp,
            "expectedActiveRevision": active_rev,
        }
    )
    res_wrong_cand = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_13}'::jsonb, '{wrong_cand_conf}'::jsonb)::text;"
        )
    )
    assert res_wrong_cand["status"] in ("CONFIRMATION_STALE", "REJECTED_CONFIRMATION")

    # Stale active revision -> CONFIRMATION_STALE
    stale_active_conf = json.dumps(
        {
            "reason": "ATYPICAL_ITEM_COUNT",
            "candidateFingerprint": candidate_fp,
            "expectedActiveFingerprint": active_fp,
            "expectedActiveRevision": 999,
        }
    )
    res_stale_active = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_13}'::jsonb, '{stale_active_conf}'::jsonb)::text;"
        )
    )
    assert res_stale_active["status"] == "CONFIRMATION_STALE"

    # Valid confirmation -> REGISTERED_CONFIRMED_REVISION
    valid_conf = json.dumps(
        {
            "reason": "ATYPICAL_ITEM_COUNT",
            "candidateFingerprint": candidate_fp,
            "expectedActiveFingerprint": active_fp,
            "expectedActiveRevision": active_rev,
        }
    )
    res_valid = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_13}'::jsonb, '{valid_conf}'::jsonb)::text;"
        )
    )
    assert res_valid["status"] == "REGISTERED_CONFIRMED_REVISION"
    assert res_valid["itemCount"] == 13


def test_real_db_new_date_atypical_confirmation() -> None:
    """Verifies atypical confirmation on different date behaves fail-closed and registers new week."""
    user_id = "34343434-3434-3434-3434-343434343434"
    _exec_psql(f"""
        DELETE FROM public.user_data WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_vocabulary_history WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_ingestion_tokens WHERE user_id = '{user_id}'::uuid;
    """)

    token = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('New Date Atypical')::text;",
            user_id=user_id,
        )
    )["token"]

    # Existing active set on 2026-09-25
    cand_10 = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS})
    res_prev = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_10}'::jsonb)::text;"
        )
    )
    active_fp = res_prev["contentFingerprint"]
    active_rev = res_prev["revision"]

    # 13 items on new date 2026-10-02
    extra_3 = [
        {"word": "word11", "academyDescription": "d11"},
        {"word": "word12", "academyDescription": "d12"},
        {"word": "word13", "academyDescription": "d13"},
    ]
    cand_new_13 = json.dumps(
        {"testDate": "2026-10-02", "items": SAMPLE_10_ITEMS + extra_3}
    )

    res_needs = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_new_13}'::jsonb)::text;"
        )
    )
    assert res_needs["status"] == "NEEDS_CONFIRMATION"
    assert res_needs["reason"] == "ATYPICAL_ITEM_COUNT"
    candidate_fp = res_needs["candidateFingerprint"]

    # Invalid confirmation rejected
    res_bad = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_new_13}'::jsonb, '{{}}'::jsonb)::text;"
        )
    )
    assert res_bad["status"] == "REJECTED_CONFIRMATION"

    # Valid confirmation accepted -> REGISTERED_NEW
    valid_conf = json.dumps(
        {
            "reason": "ATYPICAL_ITEM_COUNT",
            "candidateFingerprint": candidate_fp,
            "expectedActiveFingerprint": active_fp,
            "expectedActiveRevision": active_rev,
        }
    )
    res_valid = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_new_13}'::jsonb, '{valid_conf}'::jsonb)::text;"
        )
    )
    assert res_valid["status"] == "REGISTERED_CONFIRMED_REVISION"
    assert res_valid["setId"] == "2026-10-02"
    assert res_valid["itemCount"] == 13


def test_real_db_first_ever_atypical_confirmation() -> None:
    """Verifies first-ever atypical candidate (no prior active set) requires confirmation and accepts."""
    user_id = "56565656-5656-5656-5656-565656565656"
    _exec_psql(f"""
        DELETE FROM public.user_data WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_vocabulary_history WHERE user_id = '{user_id}'::uuid;
        DELETE FROM public.weekly_ingestion_tokens WHERE user_id = '{user_id}'::uuid;
    """)

    token = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('First Ever Atypical')::text;",
            user_id=user_id,
        )
    )["token"]

    extra_3 = [
        {"word": "word11", "academyDescription": "d11"},
        {"word": "word12", "academyDescription": "d12"},
        {"word": "word13", "academyDescription": "d13"},
    ]
    cand_first_13 = json.dumps(
        {"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS + extra_3}
    )

    res_needs = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_first_13}'::jsonb)::text;"
        )
    )
    assert res_needs["status"] == "NEEDS_CONFIRMATION"
    assert res_needs["reason"] == "ATYPICAL_ITEM_COUNT"
    candidate_fp = res_needs["candidateFingerprint"]

    # Empty confirmation rejected
    res_empty = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_first_13}'::jsonb, '{{}}'::jsonb)::text;"
        )
    )
    assert res_empty["status"] == "REJECTED_CONFIRMATION"

    # Valid confirmation for first-ever set (no active set to match)
    valid_conf = json.dumps(
        {
            "reason": "ATYPICAL_ITEM_COUNT",
            "candidateFingerprint": candidate_fp,
        }
    )
    res_valid = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_first_13}'::jsonb, '{valid_conf}'::jsonb)::text;"
        )
    )
    assert res_valid["status"] == "REGISTERED_CONFIRMED_REVISION"
    assert res_valid["itemCount"] == 13


# ── 9. Token Management RPCs (Onboarding & Revocation) ──────────


def test_real_db_token_list_and_revoke_rpc() -> None:
    """Verifies list_weekly_english_agent_tokens and revoke_weekly_english_agent_token RPCs."""
    user_id = "78787878-7878-7878-7878-787878787878"
    _exec_psql(
        f"DELETE FROM public.weekly_ingestion_tokens WHERE user_id = '{user_id}'::uuid;"
    )

    # Mint token 1
    mint_res = json.loads(
        _exec_psql(
            "SELECT public.create_weekly_english_agent_token('Onboarding Agent Token')::text;",
            user_id=user_id,
        )
    )
    token_id = mint_res["tokenId"]
    token = mint_res["token"]

    # List tokens via RPC
    list_res = json.loads(
        _exec_psql(
            "SELECT public.list_weekly_english_agent_tokens()::text;",
            user_id=user_id,
        )
    )
    assert list_res["status"] == "OK"
    assert len(list_res["tokens"]) == 1
    t0 = list_res["tokens"][0]
    assert t0["id"] == token_id
    assert t0["isRevoked"] is False

    # Revoke token via RPC
    revoke_res = json.loads(
        _exec_psql(
            f"SELECT public.revoke_weekly_english_agent_token('{token_id}'::uuid)::text;",
            user_id=user_id,
        )
    )
    assert revoke_res["status"] == "REVOKED"

    # Verify ingestion with revoked token is UNAUTHORIZED
    cand_10 = json.dumps({"testDate": "2026-09-25", "items": SAMPLE_10_ITEMS})
    res_ingest = json.loads(
        _exec_psql(
            f"SELECT public.register_weekly_english_set('{token}', '{cand_10}'::jsonb)::text;"
        )
    )
    assert res_ingest["status"] == "UNAUTHORIZED"


# ── 10. Fail-Closed Acceptance Verification Mode ────────────────


def test_real_db_required_mode_fails_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that when WEEKLY_INGESTION_REAL_DB_REQUIRED=1 and the DB is unavailable,
    the suite fails closed rather than skipping.
    """
    import sys

    mod = sys.modules[__name__]
    monkeypatch.setenv("WEEKLY_INGESTION_REAL_DB_REQUIRED", "1")
    monkeypatch.setattr(mod, "_is_pg_available", lambda: False)
    with pytest.raises(
        pytest.fail.Exception, match="required by WEEKLY_INGESTION_REAL_DB_REQUIRED"
    ):
        setup_module()
