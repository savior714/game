#!/usr/bin/env python3
"""Live Supabase proof for AidenGame core learning/reward sync.

This verification targets the production Supabase project used by AidenGame and proves:
1. study_rewards + four canonical subject-stat rows are writable for the authenticated owner.
2. Each write can be read back exactly through PostgREST.
3. A fresh browser/localStorage restores those rows through the real auth-changed ->
   SyncEngine.DEFAULT_PULL_KEYS path.
4. Original payloads and updated_at values are restored in a finally block.

Safety:
- Requires an explicit mutation opt-in environment variable.
- Requires all five rows to exist before any mutation; it never creates rows.
- Intended for a dedicated live-test account. It can technically back up/restore an
  existing account, but a dedicated account is strongly preferred.

Required environment variables:
- AIDEN_SUPABASE_TEST_EMAIL
- AIDEN_SUPABASE_TEST_PASSWORD
- AIDEN_SUPABASE_LIVE_SYNC_ALLOW_MUTATION=1
"""

from __future__ import annotations

import datetime as dt
import http.server
import json
import os
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

SUPABASE_URL = "https://rxjefpmvlygunrukccgg.supabase.co"
ANON_KEY = "sb_publishable_86T5zbV_IUXZDvQig6mofg_tlHYeHVx"
REPO_ROOT = Path(__file__).resolve().parent.parent

SYNC_KEYS = (
    "study_rewards",
    "aiden_math_stats",
    "aiden_english_stats",
    "aiden_korean_stats",
    "aiden_science_stats",
)

DEFAULT_SHOP_ITEMS = [
    {
        "id": "youtube",
        "icon": "📺",
        "label": "유튜브 10분",
        "desc": "좋아하는 영상 시청",
        "price": 1,
    },
    {
        "id": "snack",
        "icon": "🍪",
        "label": "간식 1개",
        "desc": "맛있는 간식 시간",
        "price": 1,
    },
    {
        "id": "marble",
        "icon": "🎮",
        "label": "마블 게임",
        "desc": "마블 한 판 더!",
        "price": 1,
    },
    {
        "id": "bubble",
        "icon": "🫧",
        "label": "비눗방울 게임",
        "desc": "버블팡 한 판 더!",
        "price": 1,
    },
]


def _request(
    endpoint: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict | list | None = None,
    prefer: str | None = None,
) -> tuple[int, dict | list]:
    url = f"{SUPABASE_URL}{endpoint}"
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {token or ANON_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer

    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return exc.code, parsed


def _auth(email: str, password: str) -> tuple[str, str, str]:
    status, body = _request(
        "/auth/v1/token?grant_type=password",
        method="POST",
        payload={"email": email, "password": password},
    )
    assert status == 200 and isinstance(body, dict), f"auth failed: HTTP {status} {body}"
    assert "access_token" in body and "user" in body, f"auth response incomplete: {body}"
    return body["access_token"], body.get("refresh_token", ""), body["user"]["id"]


def _row_query(user_id: str, key: str) -> str:
    query = urllib.parse.urlencode(
        {
            "user_id": f"eq.{user_id}",
            "data_key": f"eq.{key}",
            "select": "data_key,payload,updated_at",
        }
    )
    return f"/rest/v1/user_data?{query}"


def _read_row(token: str, user_id: str, key: str) -> dict | None:
    status, body = _request(_row_query(user_id, key), token=token)
    assert status == 200 and isinstance(body, list), (
        f"read failed for {key}: HTTP {status} {body}"
    )
    if not body:
        return None
    assert len(body) == 1, f"expected one row for {key}, got {len(body)}"
    return body[0]


def _patch_row(
    token: str,
    user_id: str,
    key: str,
    *,
    payload: dict,
    updated_at: str,
) -> dict:
    endpoint = _row_query(user_id, key).replace(
        "&select=data_key%2Cpayload%2Cupdated_at", ""
    )
    status, body = _request(
        endpoint,
        method="PATCH",
        token=token,
        payload={"payload": payload, "updated_at": updated_at},
        prefer="return=representation",
    )
    assert status in (200, 204), f"patch failed for {key}: HTTP {status} {body}"
    if status == 204:
        row = _read_row(token, user_id, key)
        assert row is not None
        return row
    assert isinstance(body, list) and len(body) == 1, (
        f"patch response invalid for {key}: {body}"
    )
    return body[0]


def _probe_payloads(probe_ms: int) -> dict[str, dict]:
    rewards = {
        "gems": 17,
        "youtube_minutes": 20,
        "snacks": 2,
        "marble_plays": 1,
        "bubble_plays": 3,
        "shop_items": DEFAULT_SHOP_ITEMS,
        "custom_inventory": {"live_sync_probe": 1},
        "claimed_receipts": {},
        "theme": "modern",
        "last_updated": dt.datetime.fromtimestamp(
            probe_ms / 1000, tz=dt.UTC
        ).isoformat(),
        "_updated_at": probe_ms,
    }

    result: dict[str, dict] = {"study_rewards": rewards}
    for idx, key in enumerate(SYNC_KEYS[1:], start=1):
        result[key] = {
            "live_sync_probe": {
                "levels": {
                    "0": {
                        "attempts": idx,
                        "correct": idx,
                        "totalTime": idx * 100,
                    }
                },
                "weaknesses": {
                    "probe": {"attempts": idx, "correct": idx},
                },
            },
            "_updated_at": probe_ms + idx,
        }
    return result


def _run_browser_restore(
    *,
    access_token: str,
    refresh_token: str,
    user_id: str,
    email: str,
    expected: dict[str, dict],
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
            page = context.new_page()

            page_errors: list[str] = []
            failed_requests: list[str] = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.on(
                "requestfailed",
                lambda req: failed_requests.append(
                    f"{req.method} {req.url}: {req.failure}"
                ),
            )

            page.goto(f"{base_url}/domains/english/index.html")
            page.wait_for_load_state("networkidle")
            page.wait_for_function(
                "() => Boolean(window.supabaseClient && window.Auth && window.SyncEngine)",
                timeout=10000,
            )

            page.evaluate(
                """async ({accessToken, refreshToken, userId, email, keys}) => {
                    for (const key of keys) localStorage.removeItem(key);
                    localStorage.removeItem('sync_queue');

                    await window.supabaseClient.auth.setSession({
                      access_token: accessToken,
                      refresh_token: refreshToken,
                    });

                    const user = { id: userId, email };
                    window.Auth.getUser = () => user;
                    window.dispatchEvent(new CustomEvent('auth-changed', {
                      detail: { user },
                    }));
                }""",
                {
                    "accessToken": access_token,
                    "refreshToken": refresh_token,
                    "userId": user_id,
                    "email": email,
                    "keys": list(SYNC_KEYS),
                },
            )

            page.wait_for_function(
                """({expected}) => Object.entries(expected).every(([key, value]) => {
                    const raw = localStorage.getItem(key);
                    if (!raw) return false;
                    try {
                      return JSON.stringify(JSON.parse(raw)) === JSON.stringify(value);
                    } catch {
                      return false;
                    }
                })""",
                {"expected": expected},
                timeout=15000,
            )

            restored = page.evaluate(
                """(keys) => Object.fromEntries(
                    keys.map((key) => [key, JSON.parse(localStorage.getItem(key))])
                )""",
                list(SYNC_KEYS),
            )
            assert restored == expected, "browser restore payload mismatch"
            assert not page_errors, f"browser page errors: {page_errors}"
            assert not failed_requests, f"browser request failures: {failed_requests}"

            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main() -> None:
    assert os.environ.get("AIDEN_SUPABASE_LIVE_SYNC_ALLOW_MUTATION") == "1", (
        "Refusing live mutation. Set AIDEN_SUPABASE_LIVE_SYNC_ALLOW_MUTATION=1 "
        "only for an intentional live sync verification."
    )
    email = os.environ.get("AIDEN_SUPABASE_TEST_EMAIL", "").strip()
    password = os.environ.get("AIDEN_SUPABASE_TEST_PASSWORD", "")
    assert email and password, (
        "AIDEN_SUPABASE_TEST_EMAIL and AIDEN_SUPABASE_TEST_PASSWORD are required."
    )

    access_token, refresh_token, user_id = _auth(email, password)
    print(f"Authenticated live test user: {email} ({user_id})")

    backups: dict[str, dict] = {}
    for key in SYNC_KEYS:
        row = _read_row(access_token, user_id, key)
        assert row is not None, (
            f"Refusing mutation: required pre-existing row {key!r} is missing. "
            "Use/seed a dedicated test account first; this verifier never creates rows."
        )
        backups[key] = row

    probe_ms = int(time.time() * 1000)
    expected = _probe_payloads(probe_ms)
    probe_updated_at = dt.datetime.fromtimestamp(
        probe_ms / 1000, tz=dt.UTC
    ).isoformat()

    mutated = False
    try:
        for key in SYNC_KEYS:
            _patch_row(
                access_token,
                user_id,
                key,
                payload=expected[key],
                updated_at=probe_updated_at,
            )
        mutated = True

        for key in SYNC_KEYS:
            row = _read_row(access_token, user_id, key)
            assert row is not None
            assert row["payload"] == expected[key], f"exact read-back failed for {key}"
        print("PASS: live PostgREST write + exact read-back for 5 core sync rows")

        _run_browser_restore(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            email=email,
            expected=expected,
        )
        print("PASS: fresh browser restored all 5 rows through auth-changed default sync")
    finally:
        if mutated:
            restore_failures: list[str] = []
            for key, row in backups.items():
                try:
                    _patch_row(
                        access_token,
                        user_id,
                        key,
                        payload=row["payload"],
                        updated_at=row["updated_at"],
                    )
                except Exception as exc:  # pragma: no cover - emergency reporting path
                    restore_failures.append(f"{key}: {exc}")
            assert not restore_failures, (
                "LIVE TEST DATA RESTORE FAILED: " + "; ".join(restore_failures)
            )
            print("PASS: original payloads and updated_at values restored")


if __name__ == "__main__":
    main()
