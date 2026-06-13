#!/usr/bin/env python3
"""Scan oldest Linear backlog issue and enqueue triage candidates."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.archive_done_issues import (  # noqa: E402
    _resolve_team_id,
    build_issue_filter,
    collect_blueprint_references,
)
from scripts.linear_sync.lib.backlog_triage_patterns import (  # noqa: E402
    detect_pattern,
    recommend_action,
    resolve_linked_plan,
)
from scripts.linear_sync.lib.backlog_triage_queue import (  # noqa: E402
    DEFAULT_QUEUE_PATH,
    BacklogTriageQueue,
)
from scripts.linear_sync.lib.state_mapping import _LINEAR_TO_BLUEPRINT  # noqa: E402
from scripts.linear_sync.linear_client import LinearClient  # noqa: E402
from scripts.linear_sync.sync_engine import load_env  # noqa: E402

_BACKLOG_STATE_TYPES = sorted(
    {t for types, _ in _LINEAR_TO_BLUEPRINT for t in types if t in {"backlog", "unstarted", "todo"}}
)


@dataclass
class ScanResult:
    enqueued: bool = False
    would_enqueue: bool = False
    skipped_reason: str | None = None
    candidate: dict | None = None


def collect_oldest_backlog_issue(client: LinearClient, team_id: str | None, queue: BacklogTriageQueue | None = None) -> dict | None:
    issue_filter = build_issue_filter(
        team_id=team_id,
        state_types=_BACKLOG_STATE_TYPES,
        older_than_days=None,
    )
    oldest: dict | None = None
    for node in client.iter_issues(
        issue_filter=issue_filter,
        first=50,
        order_by="createdAt",
    ):
        if node.get("archivedAt"):
            continue
        ident = str(node.get("identifier") or "")
        if queue and (queue.has_pending_issue(ident) or queue.is_deferred_active(ident) or queue.has_skipped_issue(ident)):
            continue
        created = str(node.get("createdAt") or "")
        if oldest is None:
            oldest = node
            continue
        if created and created < str(oldest.get("createdAt") or "z"):
            oldest = node
    return oldest


def _build_candidate(issue: dict, *, repo_root: Path) -> tuple[dict | None, str | None]:
    linked = resolve_linked_plan(issue, repo_root=repo_root)
    pattern = detect_pattern(linked)
    if pattern is None:
        return None, "no_matching_pattern"
    action = recommend_action(pattern)
    plan_path = None
    plan_status = None
    if linked is not None:
        try:
            plan_path = linked.path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            plan_path = str(linked.path)
        plan_status = linked.lifecycle.value
    return (
        {
            "issue_id": str(issue.get("identifier") or ""),
            "issue_uuid": str(issue.get("id") or ""),
            "title": str(issue.get("title") or ""),
            "created_at": str(issue.get("createdAt") or ""),
            "description": str(issue.get("description") or ""),
            "pattern": pattern.value,
            "recommended_action": action.verb,
            "plan_path": plan_path,
            "plan_status": plan_status,
            "status": "pending",
            "defer_until": None,
            "scanned_at": None,
            "reviewed_at": None,
            "review_choice": None,
        },
        None,
    )


def run_scan(
    *,
    client: LinearClient,
    team_id: str | None,
    repo_root: Path,
    queue_path: Path,
    execute: bool,
    plans_dir: Path,
) -> ScanResult:
    blueprint_refs = collect_blueprint_references(plans_dir)
    queue = BacklogTriageQueue(queue_path)

    issue = collect_oldest_backlog_issue(client, team_id, queue)
    if issue is None:
        return ScanResult(skipped_reason="no_backlog_issue")

    ident = str(issue.get("identifier") or "")
    if ident in blueprint_refs:
        return ScanResult(skipped_reason="active_blueprint_reference")

    candidate, skip = _build_candidate(issue, repo_root=repo_root)
    if candidate is None:
        return ScanResult(skipped_reason=skip)

    candidate["scanned_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    if not execute:
        return ScanResult(would_enqueue=True, candidate=candidate)

    queue.enqueue(candidate)
    return ScanResult(enqueued=True, candidate=candidate)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan oldest Linear backlog for triage.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview without writing queue (default).")
    mode.add_argument("--execute", action="store_true", help="Enqueue candidate to queue.json.")
    args = parser.parse_args(argv)
    execute = bool(args.execute)

    load_env()
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY 가 없습니다. 루트 `.env` 파일에 설정하세요.", file=sys.stderr)
        raise SystemExit(2)
    client = LinearClient(api_key)
    team_id = _resolve_team_id(client, None)
    plans_dir = _REPO_ROOT / "docs" / "plans"
    result = run_scan(
        client=client,
        team_id=team_id,
        repo_root=_REPO_ROOT,
        queue_path=DEFAULT_QUEUE_PATH,
        execute=execute,
        plans_dir=plans_dir,
    )

    if result.enqueued:
        ident = result.candidate.get("issue_id") if result.candidate else "?"
        print(f"Enqueued triage candidate {ident}.")
        return 0
    if result.would_enqueue:
        ident = result.candidate.get("issue_id") if result.candidate else "?"
        print(f"Dry-run: would enqueue {ident} ({result.candidate.get('pattern')}).")
        return 0
    print(f"No enqueue: {result.skipped_reason or 'unknown'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
