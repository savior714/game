#!/usr/bin/env python3
"""Pull Linear TEM-216 issue description into the repo for offline / air-gapped use."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.sync_engine import load_env  # noqa: E402

API_URL = "https://api.linear.app/graphql"
DEFAULT_OUT = _REPO / "docs/reports/analysis/tem_216_linear_meeting_notes_offline.md"
ISSUE_NUMBER = 216


def _fetch_issue(number: int, api_key: str) -> dict:
    query = """
    query($filter: IssueFilter) {
      issues(filter: $filter, first: 1) {
        nodes { identifier title description updatedAt }
      }
    }
    """
    body = json.dumps(
        {"query": query, "variables": {"filter": {"number": {"eq": number}}}}
    ).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    nodes = payload.get("data", {}).get("issues", {}).get("nodes", [])
    if not nodes:
        raise RuntimeError(f"Linear issue number {number} not found")
    return nodes[0]


def _render_header(node: dict, snapshot_at: str) -> str:
    identifier = node.get("identifier", f"TEM-{ISSUE_NUMBER}")
    title = (node.get("title") or "").replace("\n", " ")
    updated = node.get("updatedAt") or ""
    return f"""---
source: linear
issue: TEM-216
identifier: {identifier}
title: {title}
linear_updated_at: {updated}
snapshot_at: {snapshot_at}
sync_policy: 온라인 시 Linear 본문과 diff 후 갱신. 오프라인·API 불가 시 본 파일을 회의록 SSOT로 사용.
linear_url: https://linear.app/templaremr/issue/TEM-216
---

<!-- Language: ko -->

# TEM-216 Linear 본문 스냅샷 (오프라인 회의록)

> **용도**: 네트워크·Linear API·`gh` 없이 260528 화상회의 **원문**을 읽을 때 사용.
> 로드맵 매핑(L216·T216-R·Epic 44)은 [`ROADMAP.md` § TEM-216](../../plans/ROADMAP.md#tem-216).
>
> **온라인 정본**: [Linear TEM-216](https://linear.app/templaremr/issue/TEM-216) — 불일치 시 Linear 우선 후 `just linear-snapshot-tem-216`으로 갱신.

"""


def snapshot(*, out: Path, number: int, dry_run: bool) -> int:
    load_env()
    import os

    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        print("ERROR: LINEAR_API_KEY not set (see .env)", file=sys.stderr)
        return 1

    node = _fetch_issue(number, api_key)
    description = node.get("description") or ""
    snapshot_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = _render_header(node, snapshot_at) + description.rstrip() + "\n"

    if dry_run:
        print(f"Would write {out} ({len(description)} chars from Linear)")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"OK {out} ({len(description)} chars, linear_updated_at={node.get('updatedAt')})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output markdown path (default: {DEFAULT_OUT.relative_to(_REPO)})",
    )
    parser.add_argument("--number", type=int, default=ISSUE_NUMBER, help="Linear issue number")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        return snapshot(out=args.out.resolve(), number=args.number, dry_run=args.dry_run)
    except urllib.error.URLError as exc:
        print(f"ERROR: Linear API unreachable ({exc})", file=sys.stderr)
        offline = DEFAULT_OUT.resolve()
        if offline.is_file():
            print(f"Hint: use existing offline copy at {offline}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
