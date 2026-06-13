#!/usr/bin/env python3
"""Update Linear TEM-50 description from Blueprint SSOT; optionally mark Done + comment."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.create_observability_hub_issue import (  # noqa: E402
    BLUEPRINT,
    build_description,
)
from scripts.linear_sync.sync_engine import LinearClient, load_env  # noqa: E402

API_URL = "https://api.linear.app/graphql"
ISSUE_ID = "TEM-50"
COMPLETION_MARKER = "TEM-50 Complete"


def _graphql(api_key: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("errors"):
        msg = payload["errors"][0].get("message", str(payload["errors"]))
        raise RuntimeError(msg)
    return payload.get("data") or {}


def fetch_issue(api_key: str, identifier: str = ISSUE_ID) -> dict | None:
    data = _graphql(
        api_key,
        """
        query GetIssue($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
            state { id name type }
          }
        }
        """,
        {"id": identifier},
    )
    return data.get("issue")


def update_issue_content(api_key: str, issue_uuid: str, *, dry_run: bool) -> bool:
    title = "Project Blueprint: 전 구간 통합 에러 관측 허브 (Unified Error Observability Hub)"
    description = build_description()
    if dry_run:
        print(f"[dry-run] Would update {ISSUE_ID} description")
        print(description[:400])
        return True

    data = _graphql(
        api_key,
        """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) { success }
        }
        """,
        {
            "id": issue_uuid,
            "input": {"title": title, "description": description, "priority": 2},
        },
    )
    return bool((data.get("issueUpdate") or {}).get("success"))


def find_completed_state_id(client: LinearClient, issue_uuid: str) -> str | None:
    states = client.get_team_states(issue_uuid)
    for state in states:
        if str(state.get("type") or "").lower() == "completed":
            return state["id"]
        if str(state.get("name") or "").lower() in ("done", "completed"):
            return state["id"]
    return None


def build_completion_comment() -> str:
    return f"""### {COMPLETION_MARKER} (2026-05-16)

**Conclusion**: Phase 0~7 완료. 전 구간 emit → `var/log/emr/hub/events.jsonl` → `just error-logs` / Admin `/dashboard/admin/errors` → prompt API.

**Verify**: `PYTHONPATH=src uv run pytest tests/observability/ -q` (46 passed) · `plan_close_gate` PASS

**Blueprint SSOT**: `{BLUEPRINT}`
"""


def has_completion_comment(client: LinearClient, issue_uuid: str) -> bool:
    comments = client.get_issue_comments(issue_uuid)
    return any(COMPLETION_MARKER in (c.get("body") or "") for c in comments)


def mark_issue_done(client: LinearClient, issue_uuid: str, *, dry_run: bool) -> tuple[bool, str]:
    issue = fetch_issue(client.api_key, ISSUE_ID)
    if not issue:
        return False, "issue_not_found"

    state = issue.get("state") or {}
    state_type = str(state.get("type") or "").lower()
    state_name = str(state.get("name") or "")

    if state_type == "completed" or state_name.lower() in ("done", "completed"):
        print(f"{ISSUE_ID} already in completed state: {state_name}")
        return True, "already_done"

    done_id = find_completed_state_id(client, issue_uuid)
    if not done_id:
        return False, "no_completed_state"

    comment = build_completion_comment()
    if dry_run:
        print(f"[dry-run] Would add completion comment and set stateId={done_id[:8]}...")
        print(comment[:300])
        return True, "dry_run"

    if not has_completion_comment(client, issue_uuid):
        if not client.add_comment(issue_uuid, comment):
            print(f"warning: commentCreate failed for {ISSUE_ID}", file=sys.stderr)
    else:
        print(f"{ISSUE_ID} completion comment already present — skip comment")

    if client.update_issue_state(issue_uuid, done_id):
        print(f"{ISSUE_ID} state set to Done/completed")
        return True, "state_updated"

    return False, "state_update_failed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync TEM-50 Linear issue to Blueprint SSOT.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without API writes")
    parser.add_argument(
        "--mark-done",
        action="store_true",
        help="After description sync, add completion comment and set issue state to Done",
    )
    parser.add_argument(
        "--mark-done-only",
        action="store_true",
        help="Only mark Done + comment (skip description update)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()

    if args.dry_run:
        if not args.mark_done_only:
            update_issue_content(api_key or "dry", ISSUE_ID, dry_run=True)
        if args.mark_done or args.mark_done_only:
            client = LinearClient(api_key or "dry")
            mark_issue_done(client, ISSUE_ID, dry_run=True)
        return 0

    if not api_key:
        print("LINEAR_API_KEY not available.", file=sys.stderr)
        return 1

    issue = fetch_issue(api_key)
    if not issue:
        print(f"Issue {ISSUE_ID} not found — run create_observability_hub_issue.py first.", file=sys.stderr)
        return 1

    issue_uuid = issue["id"]
    client = LinearClient(api_key)

    if not args.mark_done_only:
        if update_issue_content(api_key, issue_uuid, dry_run=False):
            print(f"{ISSUE_ID} description updated successfully.")
        else:
            print(f"Failed to update {ISSUE_ID} description.", file=sys.stderr)
            return 1

    if args.mark_done or args.mark_done_only:
        ok, reason = mark_issue_done(client, issue_uuid, dry_run=False)
        if not ok:
            print(f"Failed to mark {ISSUE_ID} Done: {reason}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
