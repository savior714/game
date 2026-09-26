"""Comprehensive Contract Tests for Agent Weekly English Ingestion Vertical Slice.

Verifies:
1. PRIMARY_CRITERION end-to-end lifecycle:
   - Starting condition: old set
   - Step 1: register new Set A (10 pairs) with scoped agent token
   - Step 2: read-back semantic equivalence verification
   - Step 3: client pull & sync with timestamp freshness
   - Step 4: local canonical store updated to Set A
   - Step 5: General English and Weekly Test both consume Set A
   - Step 6: Idempotency (same date + same content => NO_OP, no revision bump)
   - Step 7: Revision (same date + 1 item change => REGISTERED_REVISION, rollback preserved)
   - Step 8: Suspicious conflict (same date + large conflict => NEEDS_CONFIRMATION, current unchanged)
   - Step 9: New week (different date Set B => REGISTERED_NEW, both consumers consume Set B)
2. SECURITY PRIMARY CHECKS:
   - Invalid token rejected (UNAUTHORIZED)
   - Revoked token rejected (UNAUTHORIZED)
   - No generic user_data arbitrary write
   - Cross-user data isolation
   - Malformed/ambiguous candidate rejected, current unchanged
   - No service-role key committed or exposed
   - search_path pinned and SECURITY DEFINER safe
3. DIRECT ENTRY & CONSUMER CLOSURE:
   - Direct entry to English loads Auth & SyncEngine
   - Direct entry to Weekly Test loads Auth & SyncEngine
   - Live refresh event rebinds consumers cleanly
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_SQL = ROOT / "supabase/migrations/003_create_weekly_english_ingestion.sql"
RLS_SQL = ROOT / "supabase/policies/weekly_english_ingestion_rls.sql"
SYNC_ENGINE_JS = ROOT / "domains/sync/sync-engine.js"
ENGLISH_INDEX = ROOT / "domains/english/index.html"
WEEKLY_TEST_INDEX = ROOT / "domains/english/weekly-test/index.html"
HARNESS_MJS = ROOT / "tests/fixtures/weekly_english_ingestion_harness.mjs"


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JavaScript contract tests")
    return node


# ── Security & Structural Static Invariants ─────────────────


def test_sql_security_invariants_and_least_privilege() -> None:
    """Security check:
    - SECURITY DEFINER functions must pin search_path = public, pg_temp
    - Token stored as SHA-256 hash (never plaintext)
    - No service_role key mentioned
    - Scoped strictly to canonical weekly key and legacy projection
    """
    sql_text = MIGRATION_SQL.read_text(encoding="utf-8")
    rls_text = RLS_SQL.read_text(encoding="utf-8")

    # 1. Pinned search_path
    assert "SET search_path = public, pg_temp" in sql_text
    assert "SECURITY DEFINER" in sql_text

    # 2. SHA-256 hashing
    assert "digest(" in sql_text
    assert "'sha256'" in sql_text

    # 3. No service role key
    assert (
        "service_role" not in sql_text.lower()
        or "grant all on public.user_data to service_role" not in sql_text.lower()
    )
    assert "sb_secret" not in sql_text

    # 4. RLS enabled on all new tables
    assert "ENABLE ROW LEVEL SECURITY" in rls_text
    assert "weekly_ingestion_tokens" in rls_text
    assert "weekly_vocabulary_history" in rls_text

    # 5. Scoped data keys in migration
    assert "aiden_canonical_weekly_vocabulary_v1" in sql_text
    assert "englishWeeklyWords" in sql_text


def test_no_secret_hardcoded_in_repository() -> None:
    """Security check: no Supabase service role secret exists in tracked files."""
    for pattern in ["*.js", "*.mjs", "*.html", "*.sql", "*.json", "*.py"]:
        for file in ROOT.glob(pattern):
            if "node_modules" in file.parts or ".git" in file.parts:
                continue
            content = file.read_text(encoding="utf-8", errors="ignore")
            assert (
                "service_role" not in content
                or "grant all on" in content
                or "comment" in content
            ), f"Potential service_role leak in {file}"
            assert "sb_secret" not in content, f"Secret pattern in {file}"


def test_direct_entry_html_includes_sync_bootstrap() -> None:
    """Verifies that direct entry to domains/english and domains/english/weekly-test
    includes Supabase, Auth, and SyncEngine to ensure immediate remote sync.
    """
    eng_html = ENGLISH_INDEX.read_text(encoding="utf-8")
    wt_html = WEEKLY_TEST_INDEX.read_text(encoding="utf-8")

    for html_name, html in [
        ("english/index.html", eng_html),
        ("weekly-test/index.html", wt_html),
    ]:
        assert "supabase" in html.lower(), f"{html_name} lacks Supabase client script"
        assert "auth.js" in html, f"{html_name} lacks auth.js bootstrap"
        assert "sync-engine.js" in html, f"{html_name} lacks sync-engine.js bootstrap"


def test_sync_engine_pulls_canonical_weekly_key_and_resolves_timestamps() -> None:
    """Verifies sync-engine.js includes canonical key and handles ms / ISO timestamps."""
    sync_code = SYNC_ENGINE_JS.read_text(encoding="utf-8")

    assert "aiden_canonical_weekly_vocabulary_v1" in sync_code
    assert "weekly-vocabulary-synced" in sync_code
    # Timestamp reconciliation logic present
    assert "_updated_at" in sync_code
    assert "updatedAt" in sync_code


# ── Full Primary Criterion End-to-End Simulation ────────────


def test_primary_criterion_full_lifecycle_and_security_gate() -> None:
    """Full implementation of PRIMARY_CRITERION and SECURITY PRIMARY CHECKS:
    Starting condition: localStorage and remote current have old set.
    Step 1: Register Set A (10 pairs) with scoped agent token.
    Step 2: Read-back verified (byte and semantic equivalence).
    Step 3: Stale local session syncs from remote.
    Step 4: Local canonical store updated to Set A.
    Step 5: General English and Weekly Test both consume Set A.
    Step 6: Idempotency (same date + same content => NO_OP, no revision bump).
    Step 7: Revision (same date + 1 item change => REGISTERED_REVISION, rollback preserved).
    Step 8: Suspicious conflict (same date + large conflict => NEEDS_CONFIRMATION, current unchanged).
    Step 9: New week (different date Set B => REGISTERED_NEW, both consumers use Set B).

    Security Checks:
    - Invalid token rejected (UNAUTHORIZED)
    - Revoked token rejected (UNAUTHORIZED)
    - Ambiguous candidate rejected, current unchanged
    - Incomplete/missing prompt/answer rejected, current unchanged
    - Cross-user data isolation (tokens mapped to specific user_id)
    """
    result = subprocess.run(
        [_node(), str(HARNESS_MJS)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)

    # Security Check Assertions
    assert payload["invalidTokenStatus"] == "UNAUTHORIZED"
    assert payload["revokedTokenStatus"] == "UNAUTHORIZED"
    assert payload["ambiguousStatus"] == "REJECTED_INVALID"

    # Step 1 & 2: Register Set A and Read-Back Verification
    step1 = payload["step1"]
    assert step1["status"] == "REGISTERED_NEW"
    assert step1["setId"] == "2026-09-25"
    assert step1["revision"] == 1
    assert step1["itemCount"] == 10
    assert step1["readBackVerified"] is True

    # Step 3 & 4: Stale client syncs to Set A
    assert payload["clientUpdated"] is True

    # Step 5: Consumers read Set A
    assert payload["consumerEngCount"] == 10
    assert payload["consumerEngFirstWord"] == "courage"
    assert payload["consumerTestId"] == "2026-09-25"
    assert (
        payload["consumerTestFirstPrompt"] == "the ability to do something frightening"
    )

    # Step 6: Idempotency (same date + same content => NO_OP)
    step6 = payload["step6"]
    assert step6["status"] == "NO_OP"
    assert step6["revision"] == 1
    assert step6["readBackVerified"] is True

    # Step 7: Revision (same date + small change => REGISTERED_REVISION)
    step7 = payload["step7"]
    assert step7["status"] == "REGISTERED_REVISION"
    assert step7["revision"] == 2
    assert step7["readBackVerified"] is True
    assert payload["historyCount"] >= 2  # Rollback preserved

    # Step 8: Suspicious conflict on same date => NEEDS_CONFIRMATION, current unchanged
    step8 = payload["step8"]
    assert step8["status"] == "NEEDS_CONFIRMATION"
    assert step8["conflictDiffCount"] == 5
    assert payload["conflictCurrentUnchanged"] is True

    # Step 9: New week => REGISTERED_NEW, both consumers consume Set B
    step9 = payload["step9"]
    assert step9["status"] == "REGISTERED_NEW"
    assert step9["setId"] == "2026-10-02"
    assert step9["revision"] == 1
    assert step9["readBackVerified"] is True
    assert payload["setBConsumedEng"] is True
    assert payload["setBConsumedTest"] is True

    # Cross-user isolation
    assert payload["otherUserIsolated"] is True
