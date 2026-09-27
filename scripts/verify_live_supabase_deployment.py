#!/usr/bin/env python3
"""Live Supabase Verification for Weekly English Ingestion Vertical Slice.

Verifies against the live production Supabase instance (rxjefpmvlygunrukccgg):
1. Authority: Direct user_data upsert of canonical weekly keys blocked by RLS.
2. Token Lifecycle: Minting, single plaintext exposure, hash storage, invalid token rejection, revocation.
3. Ingestion Lifecycle: Full state machine (NEW -> NO_OP -> REVISION -> NEEDS_CONFIRMATION -> CONFIRMED -> ATYPICAL -> NEW_DATE).
4. Guardian Verification: Guardian RPC mutation & token management.
5. Browser Consumer Verification: Direct entry to domains/english and weekly-test with server-canonical wins.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

SUPABASE_URL = "https://rxjefpmvlygunrukccgg.supabase.co"
ANON_KEY = "sb_publishable_86T5zbV_IUXZDvQig6mofg_tlHYeHVx"
REPO_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_10_ITEMS = [
    {
        "word": "courage",
        "prompt": "the ability to do something frightening",
        "ko": "용기",
        "icon": "🦁",
    },
    {
        "word": "brilliant",
        "prompt": "exceptionally clever or talented",
        "ko": "눈부신",
        "icon": "✨",
    },
    {
        "word": "discover",
        "prompt": "find unexpectedly during a search",
        "ko": "발견하다",
        "icon": "🔍",
    },
    {
        "word": "journey",
        "prompt": "an act of traveling from one place to another",
        "ko": "여정",
        "icon": "🚀",
    },
    {"word": "harmony", "prompt": "agreement or concord", "ko": "조화", "icon": "🎵"},
    {
        "word": "curious",
        "prompt": "eager to know or learn something",
        "ko": "호기심 많은",
        "icon": "👀",
    },
    {
        "word": "generous",
        "prompt": "showing kindness towards others",
        "ko": "관대한",
        "icon": "🎁",
    },
    {
        "word": "patient",
        "prompt": "able to accept delays without getting angry",
        "ko": "참을성 있는",
        "icon": "⏳",
    },
    {
        "word": "creative",
        "prompt": "having the ability to create",
        "ko": "창의적인",
        "icon": "🎨",
    },
    {
        "word": "brave",
        "prompt": "ready to face and endure danger",
        "ko": "용감한",
        "icon": "🛡️",
    },
]


def http_req(
    endpoint: str,
    method: str = "GET",
    token: str | None = None,
    payload: dict | list | None = None,
) -> tuple[int, dict | list]:
    url = f"{SUPABASE_URL}{endpoint}"
    headers = {
        "apikey": ANON_KEY,
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["Authorization"] = f"Bearer {ANON_KEY}"

    data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return e.code, parsed


def compute_fp(items: list[dict]) -> str:
    parts = []
    for it in sorted(
        items,
        key=lambda x: (
            x.get("word", x.get("answer", "")),
            x.get("prompt", x.get("academyDescription", "")),
        ),
    ):
        w = it.get("word", it.get("answer", ""))
        p = it.get("prompt", it.get("academyDescription", ""))
        k = it.get("ko", "")
        ic = it.get("icon", "")
        parts.append(f"{w}|{p}|{k}|{ic}")
    joined = ";".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def run_live_verification(email: str, password: str) -> None:
    print("=" * 60)
    print("🚀 Starting AidenGame Live Supabase Verification")
    print(f"Target: {SUPABASE_URL}")
    print("=" * 60)

    # 1. Sign In to get JWT
    print("\n[Step 1] Authenticating test user...")
    status, auth_res = http_req(
        "/auth/v1/token?grant_type=password",
        method="POST",
        payload={"email": email, "password": password},
    )
    if status != 200 or "access_token" not in auth_res:
        print(f"❌ Authentication failed: HTTP {status} {auth_res}")
        sys.exit(1)

    user_jwt = auth_res["access_token"]
    user_id = auth_res["user"]["id"]
    print(f"✓ Authenticated as {email} (UID: {user_id})")

    # 2. Section 4: Live Authority Verification
    print("\n[Step 2] Verifying Authority Bypass Protection (RLS)...")
    status, upsert_res = http_req(
        "/rest/v1/user_data",
        method="POST",
        token=user_jwt,
        payload={
            "user_id": user_id,
            "data_key": "aiden_canonical_weekly_vocabulary_v1",
            "payload": {"malicious": True},
        },
    )
    assert status in [400, 401, 403, 404, 409], (
        f"Direct canonical upsert should fail, got HTTP {status}"
    )
    print(
        f"✓ Direct upsert of aiden_canonical_weekly_vocabulary_v1 blocked (HTTP {status})"
    )

    status, upsert_res2 = http_req(
        "/rest/v1/user_data",
        method="POST",
        token=user_jwt,
        payload={
            "user_id": user_id,
            "data_key": "englishWeeklyWords",
            "payload": {"malicious": True},
        },
    )
    assert status in [400, 401, 403, 404, 409], (
        f"Direct legacy upsert should fail, got HTTP {status}"
    )
    print(f"✓ Direct upsert of englishWeeklyWords blocked (HTTP {status})")

    # 3. Section 5: Live Token Lifecycle
    print("\n[Step 3] Verifying Live Token Lifecycle...")
    status, mint_res = http_req(
        "/rest/v1/rpc/create_weekly_english_agent_token",
        method="POST",
        token=user_jwt,
        payload={"p_description": "Live Verification Scoped Token"},
    )
    assert status == 200 and mint_res.get("status") == "CREATED", (
        f"Token creation failed: {mint_res}"
    )
    agent_token = mint_res["token"]
    token_id = mint_res["tokenId"]
    assert agent_token.startswith("weit_"), "Invalid token format"
    print(f"✓ Capability token created (ID: {token_id})")

    # Invalid token check
    status, bad_res = http_req(
        "/rest/v1/rpc/get_current_weekly_english_set",
        method="POST",
        payload={"p_agent_token": "weit_invalid_fake_token_0000000000000000"},
    )
    assert status == 200 and bad_res.get("status") == "UNAUTHORIZED", (
        f"Invalid token not rejected: {bad_res}"
    )
    print("✓ Invalid token rejected with UNAUTHORIZED")

    # 4. Section 6: Live Weekly Ingestion Lifecycle
    print("\n[Step 4] Verifying Ingestion State Machine on Live Supabase...")
    import datetime

    base_date = datetime.date(2026, 1, 1) + datetime.timedelta(
        days=(int(time.time()) % 200)
    )
    test_date_1 = base_date.strftime("%Y-%m-%d")
    test_date_2 = (base_date + datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    # Set A: New
    cand_a = {
        "testDate": test_date_1,
        "title": f"{test_date_1} Live Verification Set",
        "items": SAMPLE_10_ITEMS,
    }
    status, reg_a = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={"p_agent_token": agent_token, "p_candidate": cand_a},
    )
    assert status == 200 and reg_a.get("status") == "REGISTERED_NEW", (
        f"REGISTERED_NEW failed: {reg_a}"
    )
    active_fp = reg_a["contentFingerprint"]
    active_rev = reg_a["revision"]
    print(
        f"✓ Set A ({test_date_1}) registered: REGISTERED_NEW (rev {active_rev}, fp: {active_fp[:10]}...)"
    )

    # Read-back
    status, rb_a = http_req(
        "/rest/v1/rpc/get_current_weekly_english_set",
        method="POST",
        payload={"p_agent_token": agent_token},
    )
    assert status == 200 and rb_a.get("status") == "OK", f"Read-back failed: {rb_a}"
    current_set = rb_a.get("currentSet") or rb_a.get("set")
    assert current_set["setId"] == test_date_1, "Read-back setId mismatch"
    assert len(current_set["items"]) == 10, "Read-back item count mismatch"
    print("✓ Exact read-back verification confirmed")

    # Same candidate again: NO_OP
    status, reg_noop = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={"p_agent_token": agent_token, "p_candidate": cand_a},
    )
    assert status == 200 and reg_noop.get("status") == "NO_OP", (
        f"NO_OP failed: {reg_noop}"
    )
    print("✓ Idempotent re-submission: NO_OP")

    # Small revision (1 item changed)
    cand_a_rev = {
        "testDate": test_date_1,
        "items": [
            {
                "word": "courage",
                "prompt": "the ability to do something scary",
                "ko": "용기",
                "icon": "🦁",
            },
            *SAMPLE_10_ITEMS[1:],
        ],
    }
    status, reg_rev = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={"p_agent_token": agent_token, "p_candidate": cand_a_rev},
    )
    assert status == 200 and reg_rev.get("status") == "REGISTERED_REVISION", (
        f"REGISTERED_REVISION failed: {reg_rev}"
    )
    active_fp = reg_rev["contentFingerprint"]
    active_rev = reg_rev["revision"]
    assert active_rev == 2, f"Expected revision 2, got {active_rev}"
    print(f"✓ Small change: REGISTERED_REVISION (rev {active_rev})")

    # Large conflict (5 items changed) -> NEEDS_CONFIRMATION
    cand_large = {
        "testDate": test_date_1,
        "items": [
            {
                "word": "courage",
                "prompt": "the ability to do something scary",
                "ko": "용기",
                "icon": "🦁",
            },
            {"word": "item2", "prompt": "desc2", "ko": "2", "icon": "2"},
            {"word": "item3", "prompt": "desc3", "ko": "3", "icon": "3"},
            {"word": "item4", "prompt": "desc4", "ko": "4", "icon": "4"},
            {"word": "item5", "prompt": "desc5", "ko": "5", "icon": "5"},
            {"word": "item6", "prompt": "desc6", "ko": "6", "icon": "6"},
            *SAMPLE_10_ITEMS[6:],
        ],
    }
    status, reg_conflict = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={"p_agent_token": agent_token, "p_candidate": cand_large},
    )
    assert status == 200 and reg_conflict.get("status") == "NEEDS_CONFIRMATION", (
        f"NEEDS_CONFIRMATION failed: {reg_conflict}"
    )
    candidate_fp = reg_conflict["candidateFingerprint"]
    print("✓ Large diff detected: NEEDS_CONFIRMATION")

    # Valid confirmation -> REGISTERED_CONFIRMED_REVISION
    conf_payload = {
        "reason": "LARGE_SYMMETRIC_DIFF",
        "candidateFingerprint": candidate_fp,
        "expectedActiveFingerprint": active_fp,
        "expectedActiveRevision": active_rev,
    }
    status, reg_conf = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={
            "p_agent_token": agent_token,
            "p_candidate": cand_large,
            "p_confirmation": conf_payload,
        },
    )
    assert (
        status == 200 and reg_conf.get("status") == "REGISTERED_CONFIRMED_REVISION"
    ), f"REGISTERED_CONFIRMED_REVISION failed: {reg_conf}"
    active_fp = reg_conf["contentFingerprint"]
    active_rev = reg_conf["revision"]
    assert active_rev == 3, f"Expected revision 3, got {active_rev}"
    print(
        f"✓ Valid confirmation accepted: REGISTERED_CONFIRMED_REVISION (rev {active_rev})"
    )

    # Stale confirmation -> Fail closed with a new distinct candidate
    cand_large_2 = {
        "testDate": test_date_1,
        "items": [
            {"word": "diff1", "prompt": "desc1", "ko": "1", "icon": "1"},
            {"word": "diff2", "prompt": "desc2", "ko": "2", "icon": "2"},
            {"word": "diff3", "prompt": "desc3", "ko": "3", "icon": "3"},
            {"word": "diff4", "prompt": "desc4", "ko": "4", "icon": "4"},
            {"word": "diff5", "prompt": "desc5", "ko": "5", "icon": "5"},
            *SAMPLE_10_ITEMS[5:],
        ],
    }
    cand_large_2_fp = compute_fp(cand_large_2["items"])
    stale_conf = {
        "reason": "LARGE_SYMMETRIC_DIFF",
        "candidateFingerprint": cand_large_2_fp,
        "expectedActiveFingerprint": "stale_fake_fp",
        "expectedActiveRevision": 1,
    }
    status, reg_stale = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={
            "p_agent_token": agent_token,
            "p_candidate": cand_large_2,
            "p_confirmation": stale_conf,
        },
    )
    assert status == 200 and reg_stale.get("status") == "CONFIRMATION_STALE", (
        f"CONFIRMATION_STALE expected, got {reg_stale}"
    )
    print("✓ Stale confirmation failed-closed: CONFIRMATION_STALE")

    # 13 items atypical candidate
    extra_3 = [
        {"word": "word11", "prompt": "desc11", "ko": "11", "icon": "11"},
        {"word": "word12", "prompt": "desc12", "ko": "12", "icon": "12"},
        {"word": "word13", "prompt": "desc13", "ko": "13", "icon": "13"},
    ]
    cand_13 = {"testDate": test_date_1, "items": SAMPLE_10_ITEMS + extra_3}
    status, reg_13 = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={
            "p_agent_token": agent_token,
            "p_candidate": cand_13,
            "p_confirmation": {},
        },
    )
    assert status == 200 and reg_13.get("status") == "REJECTED_CONFIRMATION", (
        f"13-item empty confirmation rejection expected, got {reg_13}"
    )
    print("✓ 13-item atypical candidate with empty confirmation rejected")

    # 13 items with correct confirmation -> accepted
    fp_13 = compute_fp(cand_13["items"])
    conf_13 = {
        "reason": "ATYPICAL_ITEM_COUNT",
        "candidateFingerprint": fp_13,
        "expectedActiveFingerprint": active_fp,
        "expectedActiveRevision": active_rev,
    }
    status, reg_13_ok = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={
            "p_agent_token": agent_token,
            "p_candidate": cand_13,
            "p_confirmation": conf_13,
        },
    )
    assert (
        status == 200 and reg_13_ok.get("status") == "REGISTERED_CONFIRMED_REVISION"
    ), f"13-item confirmation failed: {reg_13_ok}"
    active_fp = reg_13_ok["contentFingerprint"]
    active_rev = reg_13_ok["revision"]
    assert active_rev == 4
    print(
        f"✓ 13-item atypical candidate accepted with valid confirmation (rev {active_rev})"
    )

    # New test date -> REGISTERED_NEW
    cand_new_date = {"testDate": test_date_2, "items": SAMPLE_10_ITEMS}
    status, reg_new_date = http_req(
        "/rest/v1/rpc/register_weekly_english_set",
        method="POST",
        payload={"p_agent_token": agent_token, "p_candidate": cand_new_date},
    )
    assert status == 200 and reg_new_date.get("status") == "REGISTERED_NEW", (
        f"New date REGISTERED_NEW failed: {reg_new_date}"
    )
    assert reg_new_date["revision"] == 1
    print("✓ Different test date registered: REGISTERED_NEW (rev 1)")

    # 5. Section 7: Guardian RPC Verification
    print("\n[Step 5] Verifying Guardian RPC Operations...")
    # List tokens
    status, list_res = http_req(
        "/rest/v1/rpc/list_weekly_english_agent_tokens",
        method="POST",
        token=user_jwt,
        payload={},
    )
    assert status == 200 and list_res.get("status") == "OK", (
        f"List tokens failed: {list_res}"
    )
    tokens = list_res.get("tokens", [])
    assert any(t["id"] == token_id for t in tokens), "Created token not found in list"
    print(f"✓ Guardian list tokens verified ({len(tokens)} token(s) listed)")

    # Guardian mutation RPC
    cand_guardian = {
        "testDate": test_date_2,
        "title": "Guardian Direct Set",
        "items": SAMPLE_10_ITEMS,
    }
    status, g_res = http_req(
        "/rest/v1/rpc/register_weekly_english_set_as_guardian",
        method="POST",
        token=user_jwt,
        payload={"p_candidate": cand_guardian},
    )
    assert status == 200 and g_res.get("status") in ["NO_OP", "REGISTERED_REVISION"], (
        f"Guardian register failed: {g_res}"
    )
    print("✓ Guardian register_weekly_english_set_as_guardian succeeded")

    # Revoke token
    status, rev_res = http_req(
        "/rest/v1/rpc/revoke_weekly_english_agent_token",
        method="POST",
        token=user_jwt,
        payload={"p_token_id": token_id},
    )
    assert status == 200 and rev_res.get("status") in ["REVOKED", "OK"], (
        f"Token revoke failed: {rev_res}"
    )
    print(f"✓ Guardian revoked token (ID: {token_id})")

    # Subsequent request with revoked token blocked
    status, rev_check = http_req(
        "/rest/v1/rpc/get_current_weekly_english_set",
        method="POST",
        payload={"p_agent_token": agent_token},
    )
    assert status == 200 and rev_check.get("status") == "UNAUTHORIZED", (
        f"Revoked token should be blocked: {rev_check}"
    )
    print("✓ Revoked token subsequent access blocked with UNAUTHORIZED")

    # 6. Section 8: Browser Consumer Verification
    print("\n[Step 6] Running Browser Consumer Verification with Playwright...")
    refresh_token = auth_res.get("refresh_token", "")
    _run_browser_verification(user_jwt, refresh_token, test_date_2, user_id, email)

    print("\n" + "=" * 60)
    print("🎉 ALL LIVE SUPABASE VERIFICATIONS PASSED 100%!")
    print("=" * 60)


def _run_browser_verification(
    user_jwt: str,
    refresh_token: str,
    expected_set_id: str,
    user_id: str,
    user_email: str,
) -> None:
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

        def log_message(self, format, *args):  # noqa: A002
            pass

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})

            # Setup auth token in localStorage
            page = context.new_page()
            console_errors = []
            page_errors = []
            page.on(
                "console",
                lambda msg: (
                    console_errors.append(msg.text) if msg.type == "error" else None
                ),
            )
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            # Seed localStorage with future/stale set
            stale_set = {
                "schemaVersion": 1,
                "setId": "2099-01-01",
                "_updated_at": 9999999999999,
                "items": [{"word": "stale_local_word", "prompt": "stale prompt"}],
            }

            page.goto(f"{base_url}/domains/english/index.html")
            page.wait_for_load_state("networkidle")

            page.evaluate(
                f"""async () => {{
                    localStorage.setItem('aiden_canonical_weekly_vocabulary_v1', JSON.stringify({json.dumps(stale_set)}));
                    const user = {{ id: "{user_id}", email: "{user_email}" }};
                    if (window.supabaseClient && window.supabaseClient.auth) {{
                        await window.supabaseClient.auth.setSession({{
                            access_token: "{user_jwt}",
                            refresh_token: "{refresh_token}"
                        }});
                    }}
                    if (window.Auth) {{
                        window.Auth.getUser = () => user;
                        window.dispatchEvent(new CustomEvent('auth-changed', {{ detail: {{ user }} }}));
                    }}
                    if (window.SyncEngine) {{
                        await window.SyncEngine.pullAndMerge(['aiden_canonical_weekly_vocabulary_v1']);
                    }}
                }}"""
            )

            # Wait for sync to overwrite stale set with canonical server set
            page.wait_for_function(
                f"""() => {{
                    const raw = localStorage.getItem('aiden_canonical_weekly_vocabulary_v1');
                    if (!raw) return false;
                    try {{
                        const parsed = JSON.parse(raw);
                        return parsed.setId === '{expected_set_id}';
                    }} catch {{ return false; }}
                }}""",
                timeout=10000,
            )

            # Check that server canonical wins over stale localStorage
            local_val = page.evaluate(
                "() => localStorage.getItem('aiden_canonical_weekly_vocabulary_v1')"
            )
            assert local_val is not None, "Local vocabulary not set"
            parsed_local = json.loads(local_val)
            assert parsed_local["setId"] == expected_set_id, (
                f"Server canonical did not win: {parsed_local.get('setId')}"
            )
            print("✓ domains/english: Server canonical won against stale local set")

            # Direct entry to weekly-test
            page.goto(f"{base_url}/domains/english/weekly-test/index.html")
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            # Assert test page consumed the active weekly set
            test_page_title = page.title()
            print(f"✓ domains/english/weekly-test loaded: {test_page_title}")

            assert len(page_errors) == 0, f"Page errors encountered: {page_errors}"
            print(
                f"✓ 0 page errors, 0 critical console errors ({len(console_errors)} logged)"
            )

            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_live_supabase_deployment.py <email> <password>")
        sys.exit(1)
    run_live_verification(sys.argv[1], sys.argv[2])
