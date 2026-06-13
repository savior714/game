#!/usr/bin/env python3
"""Cancel fixed internal TEM issues on Linear (DISCUSS SSOT list).

Usage:
    python3 scripts/linear_sync/cancel_internal_tem_batch.py --dry-run
    python3 scripts/linear_sync/cancel_internal_tem_batch.py --apply

No extra issue IDs via CLI — only the hard-coded DISCUSS list.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.env import load_env, validate_api_key  # noqa: E402
from scripts.linear_sync.linear_client import LinearClient  # noqa: E402

# DISCUSS §3 확정 목록 (PLAN_linear_internal_tem_cancel.md SSOT)
INTERNAL_TEM_TO_CANCEL: tuple[str, ...] = (
    "TEM-251",
    "TEM-256",
    "TEM-279",
    "TEM-280",
    "TEM-281",
    "TEM-282",
    "TEM-283",
    "TEM-284",
)

TARGET_STATE_NAME = "Canceled"
CANCELED_STATE_TYPES = frozenset({"canceled"})


@dataclass
class IssueRow:
    identifier: str
    uuid: str
    title: str
    state_name: str
    state_type: str


def find_canceled_state_id(client: LinearClient, issue_identifier: str) -> Optional[str]:
    """Resolve team workflow state id for Canceled (name or type)."""
    states = client.get_team_states(issue_identifier)
    for st in states:
        if str(st.get("name")) == TARGET_STATE_NAME and st.get("type") in CANCELED_STATE_TYPES:
            return str(st.get("id"))
    for st in states:
        if st.get("type") in CANCELED_STATE_TYPES:
            return str(st.get("id"))
    return None


def _issue_row(client: LinearClient, identifier: str) -> Optional[IssueRow]:
    issue = client.get_issue_by_identifier(identifier)
    if not issue:
        return None
    state = issue.get("state") or {}
    return IssueRow(
        identifier=str(issue.get("identifier") or identifier),
        uuid=str(issue["id"]),
        title=str(issue.get("title") or ""),
        state_name=str(state.get("name") or "Unknown"),
        state_type=str(state.get("type") or ""),
    )


def _is_already_canceled(row: IssueRow) -> bool:
    if row.state_name == TARGET_STATE_NAME:
        return True
    return row.state_type.lower() in CANCELED_STATE_TYPES


def run_batch(client: LinearClient, *, apply: bool) -> int:
    mode = "apply" if apply else "dry-run"
    print(f"Linear internal TEM cancel batch ({mode})")
    print(f"Targets ({len(INTERNAL_TEM_TO_CANCEL)}): {', '.join(INTERNAL_TEM_TO_CANCEL)}")
    print()

    canceled_state_id: Optional[str] = None
    updated = 0
    skipped = 0
    missing = 0
    failed = 0

    for identifier in INTERNAL_TEM_TO_CANCEL:
        row = _issue_row(client, identifier)
        if not row:
            print(f"  {identifier}: NOT FOUND")
            missing += 1
            continue

        if _is_already_canceled(row):
            print(f"  {identifier}: skip (already {row.state_name}) — {row.title[:60]}")
            skipped += 1
            continue

        if not apply:
            print(
                f"  {identifier}: plan → {TARGET_STATE_NAME} "
                f"(from {row.state_name}) — {row.title[:60]}"
            )
            continue

        if canceled_state_id is None:
            canceled_state_id = find_canceled_state_id(client, identifier)
            if not canceled_state_id:
                print(f"  {identifier}: ERROR — no '{TARGET_STATE_NAME}' state on team workflow")
                failed += len(INTERNAL_TEM_TO_CANCEL)
                return 1

        ok = client.update_issue_state(row.uuid, canceled_state_id)
        if ok:
            print(f"  {identifier}: OK → {TARGET_STATE_NAME} — {row.title[:60]}")
            updated += 1
        else:
            print(f"  {identifier}: FAILED update — {row.title[:60]}")
            failed += 1

    print()
    print(
        f"Summary: updated={updated} skipped={skipped} missing={missing} failed={failed} "
        f"(expected {len(INTERNAL_TEM_TO_CANCEL)} identifiers)"
    )

    if missing > 0 or failed > 0:
        return 1
    if not apply:
        planned = len(INTERNAL_TEM_TO_CANCEL) - skipped - missing
        if planned < 0:
            planned = 0
        print(f"Dry-run: {planned} issue(s) would move to {TARGET_STATE_NAME}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cancel DISCUSS-fixed internal TEM issues on Linear."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print current state and plan only")
    mode.add_argument("--apply", action="store_true", help="Set issues to Canceled via API")
    args = parser.parse_args()

    load_env()
    api_key = __import__("os").environ.get("LINEAR_API_KEY", "")
    client = validate_api_key(api_key)
    return run_batch(client, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
