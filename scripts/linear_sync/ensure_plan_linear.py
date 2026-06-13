#!/usr/bin/env python3
"""Ensure a Blueprint has a real Linear issue (create + patch + sync).

Usage:
  python3 scripts/linear_sync/ensure_plan_linear.py tests/fixtures/plans/PLAN_example.md
  python3 scripts/linear_sync/ensure_plan_linear.py tests/fixtures/plans/PLAN_example.md --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.lib.issue_factory import ensure_plan_linear_issue  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/patch Linear issue for a Blueprint.")
    parser.add_argument("plan", type=Path, help="Path to blueprint markdown")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-sync", action="store_true", help="Skip just linear-sync after create")
    args = parser.parse_args()

    result = ensure_plan_linear_issue(
        args.plan,
        dry_run=args.dry_run,
        sync=not args.no_sync,
    )
    if result.identifier:
        print(f"linear_issue={result.identifier}")
    if result.url:
        print(f"linear_url={result.url}")
    print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
