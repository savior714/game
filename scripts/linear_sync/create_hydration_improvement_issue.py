#!/usr/bin/env python3
"""Create a Linear issue for the server layout hydration improvement plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.lib.issue_factory import create_linear_issue  # noqa: E402
from scripts.linear_sync.sync_engine import load_env  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()

    description = """## Context
- Goal: Remove hydration guards and improve SSR performance using RSC and cookies.
- Plan: `docs/plans/PLAN_server_layout_hydration_improvement_blueprint.md`

## Key Improvements
- Migrate settings/sidebar state to cookies for server-side awareness.
- Convert DashboardLayout to Server Component.
- Optimize RootLayout and remove intrusive hydration guards.
- Implement loading.tsx and error.tsx for streaming.
"""

    try:
        issue = create_linear_issue(
            title="FE: Server Layout Hydration Improvement (Next.js 15 RSC + Cookies)",
            description=description,
            priority=2,
            labels=["Frontend", "Improvement", "UI/UX"],
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.dry_run or issue is None:
        return 0

    print(f"created_issue_identifier={issue.get('identifier') or ''}")
    print(f"created_issue_url={issue.get('url') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
