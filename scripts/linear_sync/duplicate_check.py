#!/usr/bin/env python3
"""Scan Blueprint ↔ Linear mappings for duplicate issues and optionally mark orphans."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.lib.duplicate_guard import (  # noqa: E402
    DuplicateGroup,
    blueprint_rel_path,
    build_duplicate_group,
    format_duplicate_report,
    mark_issue_duplicate,
    search_issues_for_plan,
)
from scripts.linear_sync.lib.plan_metadata import parse_doc_meta  # noqa: E402
from scripts.linear_sync.sync_engine import LinearClient, load_env  # noqa: E402


def _active_plans() -> list[Path]:
    plans_dir = _REPO_ROOT / "docs" / "plans"
    return sorted(p for p in plans_dir.glob("PLAN_*.md") if p.is_file())


def _archived_plans() -> list[Path]:
    plans_dir = _REPO_ROOT / "docs" / "plans" / "archive"
    return sorted(p for p in plans_dir.rglob("PLAN_*.md") if p.is_file())


def check_plan(
    client: LinearClient,
    plan_path: Path,
    *,
    apply: bool,
    dry_run: bool,
) -> DuplicateGroup | None:
    content = plan_path.read_text(encoding="utf-8")
    meta = parse_doc_meta(content, plan_path)
    title = meta.title or plan_path.stem
    issues = search_issues_for_plan(client, plan_path, title)
    prefer = meta.linear_issue if meta.linear_issue else None
    group = build_duplicate_group(plan_path, issues, prefer=prefer)
    if not group:
        return None

    print(format_duplicate_report(group))
    if apply:
        for dup in group.duplicates:
            if mark_issue_duplicate(client, dup, canonical=group.canonical, dry_run=dry_run):
                action = "Would mark" if dry_run else "Marked"
                print(f"  ✅ {action} {dup.identifier} → Duplicate")
    return group


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect duplicate Linear issues for the same Blueprint scope."
    )
    parser.add_argument("--plan", type=Path, help="Single blueprint path (repo-relative or absolute)")
    parser.add_argument(
        "--active",
        action="store_true",
        help="Scan all docs/plans/PLAN_*.md (default when --plan and --archive omitted)",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Scan all archived plans in docs/plans/archive/**/*.md",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Mark non-canonical open issues as Duplicate on Linear",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only; simulate --apply")
    parser.add_argument("--json", action="store_true", help="Machine-readable summary on stdout")
    args = parser.parse_args()

    load_env()
    import os  # noqa: PLC0415

    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()
    if not api_key:
        print("LINEAR_API_KEY absent — cannot run duplicate check.", file=sys.stderr)
        return 1

    client = LinearClient(api_key)
    if args.plan:
        plans = [args.plan.resolve() if args.plan.is_absolute() else (_REPO_ROOT / args.plan)]
    elif args.archive:
        plans = _archived_plans()
        if args.active:
            plans.extend(_active_plans())
    else:
        plans = _active_plans()

    groups: list[DuplicateGroup] = []
    is_first_plan = True
    import time  # noqa: PLC0415
    for plan in plans:
        if not is_first_plan:
            time.sleep(2.1)  # 30 searches/min (1분 버스트 제한) 원천 회피
        is_first_plan = False

        if not plan.exists():
            print(f"⚠️  Skip missing plan: {plan}", file=sys.stderr)
            continue
        if not plan.name.startswith("PLAN_"):
            continue
        print(f"\n📂 {blueprint_rel_path(plan)}")
        group = check_plan(client, plan, apply=args.apply, dry_run=args.dry_run)
        if group:
            groups.append(group)
        else:
            print("  ✔️ No duplicate cluster (0–1 Linear match for this blueprint).")  # noqa: RUF001

    if args.json:
        payload = [
            {
                "plan": g.plan_rel,
                "canonical": g.canonical,
                "duplicates": [d.identifier for d in g.duplicates],
            }
            for g in groups
        ]
        print(json.dumps({"groups": payload, "count": len(groups)}, ensure_ascii=False, indent=2))

    if groups:
        print(f"\n⚠️  Found {len(groups)} blueprint(s) with duplicate Linear issues.")
        if not args.apply:
            print("   Re-run with `--apply` to mark non-canonical issues Duplicate.")
        return 0 if args.dry_run or args.apply else 2

    print("\n✅ No duplicate Blueprint↔Linear clusters detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
