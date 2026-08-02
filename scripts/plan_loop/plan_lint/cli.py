from __future__ import annotations

import argparse
from pathlib import Path

from scripts.plan_loop.plan_lint.fixer import apply_fix_to_file
from scripts.plan_loop.plan_lint.linter import lint_plan_file
from scripts.plan_loop.plan_lint.shared import ATOMIC_UNIT_TAG, DEPRECATED_LEVEL_LOW_TAG

COLOR_RED = "\033[91m"

COLOR_GREEN = "\033[92m"

COLOR_YELLOW = "\033[93m"

COLOR_BLUE = "\033[94m"

COLOR_RESET = "\033[0m"


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint plan markdown task contracts.")
    parser.add_argument("plan_files", type=Path, nargs="+", help="Path to plan markdown file(s)")

    parser.add_argument(
        "--archive-ready",
        action="store_true",
        help="Enforce strict checks for archiving (all tasks done, spec links present)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply mechanical auto-fixes before linting and write changes in-place",
    )
    args = parser.parse_args()

    overall_fail = False
    linted_count = 0
    template_link = "file:///.agents/workflows/plan.md"

    for plan_file in args.plan_files:
        if not plan_file.exists():
            print(f"{COLOR_RED}[ERROR] File not found: {plan_file}{COLOR_RESET}")
            overall_fail = True
            continue

        if plan_file.is_dir() or plan_file.suffix != ".md":
            print(f"{COLOR_YELLOW}[SKIP] {plan_file} (not a .md file or is a directory){COLOR_RESET}")
            continue

        linted_count += 1

        # Apply mechanical fixes before linting (opt-in via --fix)
        if args.fix:
            _fixed, fixes = apply_fix_to_file(plan_file)
            if fixes:
                print(f"{COLOR_BLUE}[fix] {plan_file}:")
                for fix in fixes:
                    print(f"  {COLOR_BLUE}- {fix}{COLOR_RESET}")

        issues, warnings = lint_plan_file(plan_file, is_archive_ready=args.archive_ready)

        for warning in warnings:
            print(f"{COLOR_YELLOW}[WARN] {plan_file}: {warning}{COLOR_RESET}")

        if not issues and not warnings:
            print(f"{COLOR_GREEN}[PASS] {plan_file} contract lint passed{COLOR_RESET}")
        elif not issues and warnings:
            print(f"{COLOR_YELLOW}[WARN] {plan_file} contract lint passed with warnings — fix required before implementation{COLOR_RESET}")
            overall_fail = True
        else:
            print(f"{COLOR_RED}[FAIL] {plan_file} contract lint failed{COLOR_RESET}")
            print(f"{COLOR_YELLOW}Guideline: Follow the structural sequence in {template_link}{COLOR_RESET}")
            for issue in issues:
                print(f" {COLOR_RED}- {issue}{COLOR_RESET}")
            print(
                f"\n{COLOR_BLUE}Tip: Every blueprint task needs '{ATOMIC_UNIT_TAG}' "
                f"(or deprecated '{DEPRECATED_LEVEL_LOW_TAG}') and no placeholders.{COLOR_RESET}\n"
            )
            overall_fail = True

    if linted_count == 0:
        print(f"{COLOR_RED}[ERROR] No .md plan files were linted{COLOR_RESET}")
        return 1

    return 1 if overall_fail else 0
