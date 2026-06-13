#!/usr/bin/env python3
"""Archive completed (Done) Linear issues to free non-archived quota on free plans.

Linear counts only non-archived issues toward the 250 limit. Done issues stay in the
quota until archived — this script bulk-archives them via the GraphQL API.

Usage (repo root):
  just linear-archive-done
    → Done 이슈 중 updatedAt이 2일보다 오래된 것을 archive (기본 동작)

  just linear-archive-done -- --dry-run
  just linear-archive-done -- --days 30
  just linear-archive-done -- --days 0 --dry-run
  just linear-archive-done -- --team TEM --include-canceled --max 100
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.linear_client import LinearClient  # noqa: E402
from scripts.linear_sync.sync_engine import _validate_api_key, load_env  # noqa: E402


def _resolve_team_id(client: LinearClient, team_key: str | None) -> str | None:
    key = (team_key or os.environ.get("LINEAR_TEAM_KEY") or "").strip()
    teams = client.list_teams()
    if not key:
        if len(teams) == 1:
            return str(teams[0]["id"])
        print(
            "ℹ️  Multiple teams — pass --team KEY or set LINEAR_TEAM_KEY in .env",
            file=sys.stderr,
        )
        return None
    lowered = key.lower()
    for team in teams:
        if str(team.get("key", "")).lower() == lowered:
            return str(team["id"])
    keys = ", ".join(sorted(str(t.get("key", "")) for t in teams if t.get("key")))
    raise SystemExit(f"Unknown team key {key!r}. Available: {keys or '(none)'}")


def build_issue_filter(
    *,
    team_id: str | None,
    state_types: list[str],
    older_than_days: int | None,
) -> dict:
    filt: dict = {"state": {"type": {"in": state_types}}}
    if team_id:
        filt["team"] = {"id": {"eq": team_id}}
    if older_than_days is not None and older_than_days > 0:
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        filt["updatedAt"] = {"lt": cutoff.isoformat().replace("+00:00", "Z")}
    return filt


def collect_blueprint_references(plans_dir: Path) -> set[str]:
    """Scan all Blueprint files for Linear-Issue: TEM-XXX references."""
    references = set()
    linear_issue_pattern = re.compile(r"Linear-Issue:\s*(TEM-\d+)")
    
    for plan_file in plans_dir.rglob("*.md"):
        try:
            content = plan_file.read_text(encoding="utf-8")
            matches = linear_issue_pattern.findall(content)
            references.update(matches)
        except (OSError, UnicodeDecodeError):
            continue
    
    return references


def collect_candidates(
    client: LinearClient,
    *,
    team_id: str | None,
    state_types: list[str],
    older_than_days: int | None,
    max_issues: int | None,
) -> list[dict]:
    issue_filter = build_issue_filter(
        team_id=team_id,
        state_types=state_types,
        older_than_days=older_than_days,
    )
    out: list[dict] = []
    for node in client.iter_issues(issue_filter=issue_filter, first=50):
        if node.get("archivedAt"):
            continue
        out.append(node)
        if max_issues is not None and len(out) >= max_issues:
            break
    return out


def archive_candidates(
    client: LinearClient,
    issues: list[dict],
    *,
    execute: bool,
    trash: bool,
    blueprint_references: set[str] | None = None,
) -> tuple[int, int]:
    if not issues:
        return 0, 0

    # Filter out issues that are still referenced by Blueprints
    if blueprint_references:
        filtered_issues = []
        for row in issues:
            ident = row.get("identifier", "")
            if ident in blueprint_references:
                print(f"  ⚠️ Skipping {ident} — still referenced in Blueprint files", file=sys.stderr)
            else:
                filtered_issues.append(row)
        
        if len(filtered_issues) < len(issues):
            print(f"  ℹ️  Filtered {len(issues) - len(filtered_issues)} issue(s) still in Blueprints")
        issues = filtered_issues
    
    if not issues:
        print(f"\n📝 All candidate issues are still referenced in Blueprints. Nothing to archive.")
        return 0, 0

    if not execute:
        print(f"\n🔍 Dry-run: would archive {len(issues)} issue(s). Re-run without --dry-run.")
        for row in issues[:20]:
            state = (row.get("state") or {}).get("name") or "?"
            team = (row.get("team") or {}).get("key") or "?"
            print(
                f"  - {row.get('identifier')} [{team}] ({state}) "
                f"updated={row.get('updatedAt', '')[:10]} {row.get('title', '')[:60]}"
            )
        if len(issues) > 20:
            print(f"  … and {len(issues) - 20} more")
        return 0, len(issues)

    ok = 0
    failed = 0
    for row in issues:
        issue_id = str(row["id"])
        ident = row.get("identifier") or issue_id
        try:
            if client.archive_issue(issue_id, trash=trash):
                ok += 1
                print(f"  ✅ archived {ident}")
            else:
                failed += 1
                print(f"  ❌ archive failed {ident}", file=sys.stderr)
        except Exception as exc:
            failed += 1
            print(f"  ❌ {ident}: {exc}", file=sys.stderr)
    return ok, failed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive Done/completed Linear issues (frees non-archived quota)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matches only; do not call issueArchive.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=2,
        metavar="N",
        help="Only issues with updatedAt older than N days (default: 2). Use 0 for no age filter.",
    )
    parser.add_argument(
        "--team",
        metavar="KEY",
        help="Team key filter (e.g. TEM). Defaults to LINEAR_TEAM_KEY from .env.",
    )
    parser.add_argument(
        "--include-canceled",
        action="store_true",
        help="Also archive canceled issues (default: completed/Done only).",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        metavar="N",
        help="Cap how many issues to process in one run.",
    )
    parser.add_argument(
        "--trash",
        action="store_true",
        help="Move to trash while archiving (irreversible purge path in Linear UI).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_env()
    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()
    client = _validate_api_key(api_key)

    state_types = ["completed"]
    if args.include_canceled:
        state_types.append("canceled")

    team_id = _resolve_team_id(client, args.team)
    older_than = args.days if args.days > 0 else None
    execute = not args.dry_run

    # Scan Blueprint files for Linear-Issue references (active + archive)
    active_refs = collect_blueprint_references(_REPO_ROOT / "docs" / "plans")
    archive_refs = collect_blueprint_references(_REPO_ROOT / "docs" / "plans" / "archive")
    blueprint_references = active_refs | archive_refs
    print(f"📄 Found {len(blueprint_references)} Linear-Issue references in Blueprint files.")

    print(
        f"📋 Scanning: state types={state_types}"
        + (f", team_id={team_id}" if team_id else ", all teams")
        + (f", updated > {args.days}d ago" if older_than else ", no age filter")
        + (" [dry-run]" if not execute else "")
    )

    issues = collect_candidates(
        client,
        team_id=team_id,
        state_types=state_types,
        older_than_days=older_than,
        max_issues=args.max,
    )
    print(f"Found {len(issues)} non-archived issue(s) matching filters.")

    ok, rest = archive_candidates(
        client,
        issues,
        execute=execute,
        trash=args.trash,
        blueprint_references=blueprint_references,
    )

    if execute:
        print(f"\nDone: archived={ok}, failed={rest}")
        return 1 if rest else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
