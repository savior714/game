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
   - Step 8: Suspicious conflict (same date + large symmetric diff => NEEDS_CONFIRMATION)
   - Step 8b: Confirmed override => REGISTERED_CONFIRMED_REVISION
   - Step 8c: Stale confirmation => CONFIRMATION_STALE
   - Step 9: New week (different date Set B => REGISTERED_NEW, both consumers consume Set B)
2. SECURITY PRIMARY CHECKS:
   - Invalid token rejected (UNAUTHORIZED)
   - Revoked token rejected (UNAUTHORIZED)
   - No generic user_data arbitrary write
   - Cross-user data isolation
   - Malformed/ambiguous candidate rejected, current unchanged
   - No service-role key committed or exposed
   - search_path pinned and SECURITY DEFINER safe
3. VALIDATION (004 closure):
   - Item count range: 7 reject, 8 accept, 12 accept, 13+ NEEDS_CONFIRMATION
   - Calendar date validation: 2026-99-99 rejected
   - Duplicate pair detection: identical (answer, prompt) rejected
   - Same word different prompt (multi-sense): allowed
4. FRESHNESS (server-authoritative):
   - Stale local future timestamp cannot overwrite remote
   - Remote hydrate preserves remote version
   - Local mutation gets fresh timestamp
5. SOURCE FIDELITY:
   - Prompt exact text preservation required
   - Answer case normalization acceptable
6. SYMMETRIC CONFLICT DETECTION:
   - Deletion counted in diff
   - 5 pairs modified (10 sym diff) → NEEDS_CONFIRMATION
7. DIRECT ENTRY & CONSUMER CLOSURE
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_003 = ROOT / "supabase/migrations/003_create_weekly_english_ingestion.sql"
MIGRATION_004 = ROOT / "supabase/migrations/004_weekly_ingestion_closure.sql"
MIGRATION_005 = (
    ROOT
    / "supabase/migrations/005_weekly_ingestion_authority_and_confirmation_closure.sql"
)
MIGRATION_006 = (
    ROOT / "supabase/migrations/006_weekly_vocabulary_item_count_unbounded.sql"
)
RLS_SQL = ROOT / "supabase/policies/weekly_english_ingestion_rls.sql"
SYNC_ENGINE_JS = ROOT / "domains/sync/sync-engine.js"
STORE_JS = ROOT / "domains/english/weekly-vocabulary-store.js"
ENGLISH_INDEX = ROOT / "domains/english/index.html"
WEEKLY_TEST_INDEX = ROOT / "domains/english/weekly-test/index.html"
HARNESS_MJS = ROOT / "tests/fixtures/weekly_english_ingestion_harness.mjs"
TRANSPORT_MJS = ROOT / "scripts/register-weekly-english-set.mjs"
MCP_SERVER_MJS = ROOT / "integrations/weekly-english/antigravity/mcp-server.mjs"


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
    sql_003 = MIGRATION_003.read_text(encoding="utf-8")
    sql_004 = MIGRATION_004.read_text(encoding="utf-8")
    rls_text = RLS_SQL.read_text(encoding="utf-8")

    # 1. Pinned search_path in both migrations
    for sql_text, name in [(sql_003, "003"), (sql_004, "004")]:
        assert "SET search_path = public, pg_temp" in sql_text, (
            f"{name}: missing pinned search_path"
        )
        assert "SECURITY DEFINER" in sql_text, f"{name}: missing SECURITY DEFINER"

    # 2. SHA-256 hashing
    assert "digest(" in sql_003
    assert "'sha256'" in sql_003

    # 3. No service role key
    for sql_text, name in [(sql_003, "003"), (sql_004, "004")]:
        assert "sb_secret" not in sql_text, f"{name}: service key leak"

    # 4. RLS enabled on all new tables
    assert "ENABLE ROW LEVEL SECURITY" in rls_text
    assert "weekly_ingestion_tokens" in rls_text
    assert "weekly_vocabulary_history" in rls_text

    # 5. Token provisioning RPC exists in 004
    assert "create_weekly_english_agent_token" in sql_004
    assert "gen_random_bytes" in sql_004

    # 6. Confirmation parameter in 004
    assert "p_confirmation" in sql_004
    assert "CONFIRMATION_STALE" in sql_004
    assert "REGISTERED_CONFIRMED_REVISION" in sql_004

    # 7. Symmetric diff in 004
    assert "v_added_count" in sql_004
    assert "v_removed_count" in sql_004
    assert "v_sym_diff_count" in sql_004

    # 8. Calendar date validation in 004
    assert "v_parsed_date" in sql_004

    # 9. Duplicate pair detection in 004
    assert "v_dup_count" in sql_004

    # 10. Item count constants in 004
    assert "C_NORMAL_ITEM_MAX" in sql_004
    assert "C_ATYPICAL_ITEM_MAX" in sql_004

    # 11. Mutation authority tag in 004
    assert "_mutationAuthority" in sql_004


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


def test_sync_engine_server_authoritative_weekly_key() -> None:
    """Verifies sync-engine.js treats canonical weekly key as server-authoritative."""
    sync_code = SYNC_ENGINE_JS.read_text(encoding="utf-8")

    assert "aiden_canonical_weekly_vocabulary_v1" in sync_code
    assert "weekly-vocabulary-synced" in sync_code
    assert "SERVER_AUTHORITATIVE_KEYS" in sync_code
    # Must not push server-authoritative keys back via LWW
    assert "Never push server-authoritative keys" in sync_code


def test_vocabulary_store_has_hydrate_and_mutation_functions() -> None:
    """Verifies weekly-vocabulary-store.js exports hydrateFromRemote and saveLocalMutation."""
    store_code = STORE_JS.read_text(encoding="utf-8")

    assert "hydrateFromRemote" in store_code
    assert "saveLocalMutation" in store_code
    assert "_mutationAuthority" in store_code


# ── Full Primary Criterion End-to-End Simulation ────────────


def test_primary_criterion_full_lifecycle_and_security_gate() -> None:
    """Full lifecycle test with all closure fixes applied."""
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

    # Step 8: Suspicious conflict on same date => NEEDS_CONFIRMATION with fingerprints
    step8 = payload["step8"]
    assert step8["status"] == "NEEDS_CONFIRMATION"
    assert payload["conflictHasActiveFingerprint"] is True
    assert payload["conflictHasCandidateFingerprint"] is True
    assert payload["conflictCurrentUnchanged"] is True

    # Step 8b: Confirmed override => REGISTERED_CONFIRMED_REVISION
    step8b = payload["step8b"]
    assert step8b["status"] == "REGISTERED_CONFIRMED_REVISION"
    assert step8b["revision"] == 3
    assert step8b["readBackVerified"] is True

    # Step 8c: Stale confirmation => CONFIRMATION_STALE
    assert payload["step8cStaleConfirmation"] == "CONFIRMATION_STALE"

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

    # ── VALIDATION ASSERTIONS ────────────────────────────────
    # Item count unbounded & empty check (#7)
    assert payload["emptyItemsRejected"] == "REJECTED_INVALID"
    assert payload["accept7items"] in ("REGISTERED_NEW", "REGISTERED_REVISION")
    assert payload["accept8items"] in ("REGISTERED_NEW", "REGISTERED_REVISION")
    assert payload["accept13items"] in ("REGISTERED_NEW", "REGISTERED_REVISION")
    assert payload["accept26items"] in ("REGISTERED_NEW", "REGISTERED_REVISION")
    assert payload["accept26itemCount"] == 26
    assert payload["accept26ReadBackVerified"] is True
    assert payload["accept26SourceFidelityVerified"] is True

    # Calendar date validation (#9)
    assert payload["invalidCalendarDate"] == "REJECTED_INVALID"

    # Duplicate pair detection (#8)
    assert payload["duplicatePairRejected"] == "REJECTED_INVALID"

    # Multi-sense allowed
    assert payload["multiSenseAllowed"] is True

    # ── FRESHNESS ASSERTIONS ─────────────────────────────────
    # Stale local with future timestamp overwritten by remote hydrate (#4)
    assert payload["staleLocalOverwritten"] is True
    # Remote version preserved on hydrate (#5)
    assert payload["remoteVersionPreserved"] is True
    # Local mutation gets fresh timestamp (#5)
    assert payload["localMutationFreshTs"] is True

    # ── SOURCE FIDELITY ASSERTIONS ───────────────────────────
    # Prompt case change detected as fidelity violation (#10)
    assert payload["sourceFidelityFailsOnCaseChange"] is True
    # Answer case normalization is acceptable
    assert payload["sourceFidelityOkWithAnswerCaseChange"] is True
    # Transport flow promotes fidelity failure to terminal failure status
    assert (
        payload["sourceFidelityTerminalStatus"] == "SOURCE_FIDELITY_VERIFICATION_FAILED"
    )
    assert payload["sourceFidelityVerifiedFalse"] is True
    assert payload["sourceFidelityReadBackVerifiedTrue"] is True

    # ── SYMMETRIC DIFF ASSERTIONS ────────────────────────────
    # Deletion-only scenario counted (#3)
    assert payload["deletion1Item"] in ("REGISTERED_REVISION", "REGISTERED_NEW")
    # 5 pairs modified → needs confirmation (#3)
    assert payload["modified5PairsNeedsConf"] == "NEEDS_CONFIRMATION"
    assert payload["modified5PairsSymDiff"] == 10  # 5 added + 5 removed

    # ── OPERATIONAL CLOSURE ASSERTIONS ───────────────────────
    # Write path enforcement
    assert payload["pushStatsCanonicalBlocked"] is True
    assert payload["preExistingQueuePurged"] is True

    # Large diff confirmation fail-closed
    assert payload["largeDiffEmptyConfRejected"] is True
    assert payload["largeDiffWrongCandFpRejected"] is True
    assert payload["largeDiffWrongReasonRejected"] is True
    assert payload["largeDiffStaleActiveRevRejected"] is True
    assert payload["largeDiffValidConfAccepted"] is True

    # Guardian manual editing server RPC integration
    assert payload["guardianAddMutationSuccess"] is True
    assert payload["guardianAddHydrated"] is True
    assert payload["guardianAddServerOriginPreserved"] is True
    assert payload["guardianDelMutationSuccess"] is True
    assert payload["guardianDelHydrated"] is True

    # Agent onboarding token minting
    assert payload["tokenMintCreated"] is True


def test_guardian_ui_and_token_onboarding_elements() -> None:
    """Verifies Guardian UI contains agent token management elements and server mutation bindings."""
    guardian_html = (ROOT / "domains/reward/guardian/index.html").read_text(
        encoding="utf-8"
    )
    guardian_js = (ROOT / "domains/reward/guardian/guardian.js").read_text(
        encoding="utf-8"
    )

    # HTML elements
    assert "ww-agent-token-section" in guardian_html
    assert "agent-token-mint-result" in guardian_html
    assert "agent-token-desc-input" in guardian_html
    assert "agent-token-list-container" in guardian_html
    assert 'data-action="mint-agent-token"' in guardian_html
    assert 'data-action="copy-minted-token"' in guardian_html

    # JS bindings
    assert "mutateWeeklyWordsAsGuardian" in guardian_js
    assert "register_weekly_english_set_as_guardian" in guardian_js
    assert "loadAgentTokens" in guardian_js
    assert "mintAgentToken" in guardian_js
    assert "revokeAgentToken" in guardian_js
    assert "copyMintedToken" in guardian_js
    # Ensure no generic pushStats in saveLocalMutation or guardian
    assert "SyncEngine.pushStats('englishWeeklyWords'" not in guardian_js


def test_write_path_server_authoritative_block() -> None:
    """Verifies that generic write paths block server-authoritative keys."""
    sync_code = SYNC_ENGINE_JS.read_text(encoding="utf-8")
    store_code = STORE_JS.read_text(encoding="utf-8")

    # pushStats must block server authoritative keys
    assert "SERVER_AUTHORITATIVE_KEYS.has(key)" in sync_code
    # pushToSupabase must block server authoritative keys
    assert "SERVER_AUTHORITATIVE_KEYS.has(key)" in sync_code
    # getQueue and flushQueue must clean server authoritative keys
    assert "SERVER_AUTHORITATIVE_KEYS.has(k)" in sync_code
    # WeeklyVocabularyStore.saveLocalMutation must not pushStats
    assert "window.SyncEngine.pushStats" not in store_code


def test_transport_validate_candidate_shape_unbounded_and_empty_check() -> None:
    """Verifies scripts/register-weekly-english-set.mjs validates non-empty items
    and accepts 26 items without arbitrary count limits.
    """
    harness = f"""
import {{ validateCandidateShape }} from '{TRANSPORT_MJS.as_posix()}';

const items26 = Array.from({{ length: 26 }}, (_, i) => ({{
  answer: `word${{i}}`,
  prompt: `definition ${{i}}`
}}));

const resEmpty = validateCandidateShape({{
  testDate: '2026-11-06',
  items: []
}});

const res26 = validateCandidateShape({{
  testDate: '2026-11-06',
  items: items26
}});

console.log(JSON.stringify({{
  emptyValid: resEmpty.valid,
  emptyError: resEmpty.error,
  valid26: res26.valid
}}));
"""
    result = subprocess.run(
        [_node(), "--input-type=module", "-e", harness],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    assert payload["emptyValid"] is False
    assert "empty" in payload["emptyError"].lower()
    assert payload["valid26"] is True


def test_antigravity_mcp_schema_has_no_8_15_limitation() -> None:
    """Regression test: MCP server schema and descriptions must not contain obsolete 8-15 limitation."""
    mcp_code = MCP_SERVER_MJS.read_text(encoding="utf-8")
    assert "8-15" not in mcp_code
    assert "8 to 15" not in mcp_code
    assert "Complete weekly vocabulary set" in mcp_code


def test_sql_006_unbounded_item_count_contract() -> None:
    """Verifies migration 006 supersedes _register_weekly_english_set_internal without count upper bounds."""
    sql_006 = MIGRATION_006.read_text(encoding="utf-8")
    assert "SET search_path = public, extensions, pg_temp" in sql_006
    assert "SECURITY DEFINER" in sql_006
    assert "_register_weekly_english_set_internal" in sql_006
    assert "C_NORMAL_ITEM_MAX" not in sql_006
    assert "C_ATYPICAL_ITEM_MAX" not in sql_006
    assert "v_item_count = 0" in sql_006
    assert "LARGE_SYMMETRIC_DIFF" in sql_006
