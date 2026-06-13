#!/usr/bin/env python3
"""Quick smoke test for maybe_repair_stale_linear_title."""
from pathlib import Path
from unittest.mock import MagicMock

import sys
# scripts/ 디렉토리에서 실행 시 repo 루트(/scripts/의 부모)를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.linear_sync.lib.issue_factory import (
    STALE_LINEAR_TITLE_RE,
    maybe_repair_stale_linear_title,
)

def test_repairs_global_preread():
    client = MagicMock()
    client.update_issue.return_value = True
    issue = {"id": "i1", "identifier": "TEM-207", "title": "세션 시작 시 한 번 로드 — Global Pre-read"}
    meta = MagicMock()
    meta.title = "Linear 이슈 제목 복구 및 재발 방지"
    plan_path = Path("/fake/plan.md")
    result = maybe_repair_stale_linear_title(client, issue, meta, plan_path)
    assert result is True, f"Expected True, got {result}"
    client.update_issue.assert_called_once()
    new_title = client.update_issue.call_args[1]["title"]
    assert "Linear 이슈 제목 복구" in new_title, f"Unexpected title: {new_title}"
    print("PASS test_repairs_global_preread")

def test_skips_non_stale():
    client = MagicMock()
    issue = {"id": "i2", "identifier": "TEM-207", "title": "Linear 이슈 제목 복구 및 재발 방지"}
    meta = MagicMock()
    meta.title = "Linear 이슈 제목 복구 및 재발 방지"
    plan_path = Path("/fake/plan.md")
    result = maybe_repair_stale_linear_title(client, issue, meta, plan_path)
    assert result is False, f"Expected False, got {result}"
    client.update_issue.assert_not_called()
    print("PASS test_skips_non_stale")

def test_regex_matches():
    assert STALE_LINEAR_TITLE_RE.search("Global Pre-read")
    assert STALE_LINEAR_TITLE_RE.search("세션 시작 시 한 번 로드")
    assert STALE_LINEAR_TITLE_RE.search("GLOBAL PRE-READ")
    print("PASS test_regex_matches")

def test_returns_false_on_update_failure():
    client = MagicMock()
    client.update_issue.return_value = False
    issue = {"id": "i3", "identifier": "TEM-207", "title": "Global Pre-read"}
    meta = MagicMock()
    meta.title = "Linear 이슈 제목 복구 및 재발 방지"
    plan_path = Path("/fake/plan.md")
    result = maybe_repair_stale_linear_title(client, issue, meta, plan_path)
    assert result is False
    print("PASS test_returns_false_on_update_failure")

def test_skips_when_new_title_same_as_current():
    client = MagicMock()
    issue = {"id": "i4", "identifier": "TEM-207", "title": "세션 시작 시 한 번 로드 — Global Pre-read"}
    meta = MagicMock()
    meta.title = "세션 시작 시 한 번 로드 — Global Pre-read"
    plan_path = Path("/fake/plan.md")
    result = maybe_repair_stale_linear_title(client, issue, meta, plan_path)
    assert result is False, f"Expected False (same title), got {result}"
    print("PASS test_skips_when_new_title_same_as_current")

if __name__ == "__main__":
    test_repairs_global_preread()
    test_skips_non_stale()
    test_regex_matches()
    test_returns_false_on_update_failure()
    test_skips_when_new_title_same_as_current()
    print("\nAll 5 tests passed!")
