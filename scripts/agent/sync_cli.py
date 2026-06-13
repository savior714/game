#!/usr/bin/env python3
"""CLI argument parsing and main entry point for the Unified Sync Engine.

Extracted from ``scripts/agent/sync.py`` as part of IMP-014 module split.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.agent.code_sync import apply_lock, update_lock  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified Sync Engine: Code Lock & Spec Drift Gate"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check", action="store_true", help="Run full project integrity checks"
    )
    group.add_argument(
        "--lock",
        type=str,
        metavar="LOCK_ID",
        help="Apply a new code lock hash to LOCK_ID",
    )
    group.add_argument(
        "--update",
        type=str,
        metavar="LOCK_ID",
        help="Force update code lock hash for LOCK_ID",
    )

    parser.add_argument(
        "--file", type=str, help="Target file for locking (required with --lock)"
    )
    parser.add_argument(
        "--spec", type=str, help="Spec document path to reference under --lock"
    )
    parser.add_argument(
        "--lines",
        type=str,
        metavar="START-END",
        help="Line range for auto-insert (e.g. '10-30'). Required when no function boundary can be auto-detected.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 when Spec Sync level is required (CI gate only)",
    )
    parser.add_argument(
        "--ack-spec",
        action="store_true",
        help="Declare manual spec reverse-verification complete (required when code-only diff)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix suggested drift by updating metadata (Last Verified, Claim) in candidate specs",
    )
    parser.add_argument(
        "--skip-spec-check",
        action="store_true",
        help="Bypass spec alignment verification (for incremental Phase 1 development)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.check:
        from scripts.agent.sync_checker import run_check  # noqa: PLC0415

        return run_check(
            strict=args.strict,
            ack_spec=args.ack_spec,
            fix=args.fix,
            skip_spec_check=args.skip_spec_check,
        )

    if args.lock:
        if not args.file:
            print("❌ --file is required when generating a new --lock.")
            return 1
        lines_range: tuple[int, int] | None = None
        if args.lines:
            try:
                parts = args.lines.split("-", 1)
                lines_range = (int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                print(f"❌ Invalid --lines format: '{args.lines}'. Use START-END (e.g. '10-30').")
                return 1
        return apply_lock(args.lock, args.file, args.spec, lines_range)

    if args.update:
        return update_lock(args.update)

    return 0


if __name__ == "__main__":
    sys.exit(main())
