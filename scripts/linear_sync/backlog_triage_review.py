#!/usr/bin/env python3
"""Interactive review for Linear backlog triage queue."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.lib.backlog_triage_queue import (  # noqa: E402
    DEFAULT_QUEUE_PATH,
    BacklogTriageQueue,
    ReviewChoice,
)
from scripts.linear_sync.linear_client import LinearClient  # noqa: E402
from scripts.linear_sync.sync_engine import load_env  # noqa: E402

_CHOICE_ALIASES = {
    "p": ReviewChoice.PROCESS,
    "process": ReviewChoice.PROCESS,
    "y": ReviewChoice.PROCESS,
    "yes": ReviewChoice.PROCESS,
    "d": ReviewChoice.DELETE,
    "delete": ReviewChoice.DELETE,
    "df": ReviewChoice.DEFER_7D,
    "defer_7d": ReviewChoice.DEFER_7D,
    "s": ReviewChoice.SKIP,
    "skip": ReviewChoice.SKIP,
}


def format_review_prompt(candidate: dict) -> str:
    lines = [
        "=== Linear Backlog Triage Review ===",
        f"Issue: {candidate.get('issue_id')} — {candidate.get('title')}",
        f"Created: {candidate.get('created_at')}",
    ]
    description = candidate.get("description") or ""
    if description:
        preview = description[:500].replace("\n", " ").strip()
        if len(description) > 500:
            preview += "..."
        lines.append(f"Description: {preview}")
    else:
        lines.append("Description: (none)")
    lines.extend([
        "",
        "Choices:",
        "  process(p)   - 아카이브 (250개 한도 즉시 감소)",
        "  delete(d)    - 아카이브 (250개 한도 즉시 감소)",
        "  defer_7d(df) - Defer for 7 days",
        "  skip(s)      - Skip, move to next pending candidate",
    ])
    return "\n".join(lines)


def format_queue_summary_row(candidate: dict) -> str:
    return (f"  - {candidate.get('issue_id')}: {candidate.get('title')} "
            f"(created: {candidate.get('created_at')}, pattern: {candidate.get('pattern')}, "
            f"recommended: {candidate.get('recommended_action')})")


def _parse_choice(raw: str) -> ReviewChoice | None:
    return _CHOICE_ALIASES.get(raw.strip().lower())


def _apply_delete_action(client: LinearClient, candidate: dict) -> str:
    issue_uuid = str(candidate.get("issue_uuid") or "")
    issue_id = str(candidate.get("issue_id") or "")
    ok = client.archive_issue(issue_uuid, trash=False)
    if not ok:
        msg = f"Failed to archive {issue_id}"
        raise RuntimeError(msg)
    return "archived"


def _apply_process_action(client: LinearClient, candidate: dict) -> str:
    issue_uuid = str(candidate.get("issue_uuid") or "")
    issue_id = str(candidate.get("issue_id") or "")
    ok = client.archive_issue(issue_uuid, trash=False)
    if not ok:
        msg = f"Failed to archive {issue_id}"
        raise RuntimeError(msg)
    return "archived"


def run_review(
    *,
    client: LinearClient,
    queue_path: Path,
    choice: str | None = None,
    input_fn: Callable[[str], str] | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> int:
    queue = BacklogTriageQueue(queue_path, now_fn=now_fn)
    candidate = queue.next_pending()
    if candidate is None:
        print("No pending triage candidates.")
        return 0

    print(format_review_prompt(candidate))
    raw = choice
    if raw is None:
        raw = (input_fn or input)("> ")
    parsed = _parse_choice(raw or "")
    if parsed is None:
        print(f"Unknown choice: {raw!r}")
        return 1

    action_taken: str | None = None
    if parsed == ReviewChoice.PROCESS:
        action_taken = _apply_process_action(client, candidate)
    elif parsed == ReviewChoice.DELETE:
        action_taken = _apply_delete_action(client, candidate)

    queue.apply_review(parsed, action_taken=action_taken)
    print(f"Recorded review choice: {parsed.value}")
    return 0


def print_queue_summary(queue_path: Path) -> int:
    queue = BacklogTriageQueue(queue_path)
    summary = queue.list_summary()
    print("=== Pending ===")
    for row in summary["pending"]:
        print(format_queue_summary_row(row))
    if not summary["pending"]:
        print("  (none)")
    print("=== Deferred ===")
    for row in summary["deferred"]:
        print(
            f"  - {row.get('issue_id')}: until {row.get('defer_until')} "
            f"({row.get('pattern')})"
        )
    if not summary["deferred"]:
        print("  (none)")
    print("=== Recent history ===")
    for row in summary["history"][-10:]:
        print(
            f"  - {row.get('issue_id')}: {row.get('review_choice')} "
            f"→ {row.get('action_taken')} @ {row.get('at')}"
        )
    if not summary["history"]:
        print("  (none)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review backlog triage queue.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--list", action="store_true", help="List queue summary only.")
    parser.add_argument("--choice", default=None, help="Non-interactive choice (yes/no/defer_7d/skip).")
    args = parser.parse_args(argv)

    if args.list:
        return print_queue_summary(args.queue)

    load_env()
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY 가 없습니다. 루트 `.env` 파일에 설정하세요.", file=sys.stderr)
        raise SystemExit(2)
    client = LinearClient(api_key)
    return run_review(client=client, queue_path=args.queue, choice=args.choice)


if __name__ == "__main__":
    raise SystemExit(main())
