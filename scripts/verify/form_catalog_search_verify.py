#!/usr/bin/env python3
"""Verify form-catalog search (TestClient; optional live curl when server is up).

Run from repo root: uv run python scripts/verify/form_catalog_search_verify.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402


def verify_in_process() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/form-catalog/search", params={"q": "진단"})
    response.raise_for_status()
    data = response.json()
    if data["total_count"] <= 0:
        msg = "expected at least one form for q=진단"
        raise AssertionError(msg)
    print(f"OK (TestClient): {data['total_count']} items")


def verify_live_curl() -> None:
    result = subprocess.run(
        ["/usr/bin/curl", "-sf", "http://localhost:8000/api/v1/form-catalog/search?q=진단"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("SKIP live curl: server not reachable on :8000", file=sys.stderr)
        return
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("SKIP live curl: non-JSON response (stale server?)", file=sys.stderr)
        return
    if data.get("total_count", 0) <= 0:
        print("SKIP live curl: empty catalog (restart BE to pick up changes)", file=sys.stderr)
        return
    print(f"OK (curl): {data['total_count']} items")


if __name__ == "__main__":
    verify_in_process()
    verify_live_curl()
