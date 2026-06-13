#!/usr/bin/env python3
"""Git-touched active plan blueprints for turn-end plan-lint gate."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.agent.route_gate_touched import _git_touched_files  # noqa: E402
from scripts.plan_loop.plan_lint.linter import lint_plan_file  # noqa: E402

_SKIP_PREFIXES = ("docs/plans/archive/",)


def _eligible_active_plan(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    if not norm.startswith("docs/plans/"):
        return False
    for prefix in _SKIP_PREFIXES:
        if norm.startswith(prefix):
            return False
    name = Path(norm).name
    return name.startswith("PLAN_") and name.endswith(".md")


def collect_touched_active_plans(repo_root: Path | None = None) -> list[str]:
    root = repo_root or _REPO
    valid: list[str] = []
    for rel in _git_touched_files(root):
        if not _eligible_active_plan(rel):
            continue
        full = root / rel
        if full.is_file():
            valid.append(rel.replace("\\", "/"))
    return sorted(valid)


def run_plan_lint_on_touched(
    repo_root: Path | None = None,
    paths: list[str] | None = None,
) -> int:
    root = repo_root or _REPO
    targets = paths if paths is not None else collect_touched_active_plans(root)
    if not targets:
        return 0

    failed: list[str] = []
    for rel in targets:
        plan_path = root / rel
        if not plan_path.is_file():
            continue
        issues, _warnings = lint_plan_file(plan_path, is_archive_ready=False)
        if not issues:
            continue
        failed.append(rel)
        for issue in issues:
            print(f"[FAIL] {rel}: {issue}", file=sys.stderr)

    if failed:
        print(
            "plan-lint-touched: "
            f"{len(failed)} touched plan(s) failed — {', '.join(failed)}",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    paths = collect_touched_active_plans()
    if not paths:
        return 0
    for rel in paths:
        print(rel)
    return run_plan_lint_on_touched(paths=paths)


if __name__ == "__main__":
    raise SystemExit(main())
