#!/usr/bin/env python3
"""FE import graph gate — dependency_boundary_scan + baseline (신규 위반만 FAIL).

Usage:
  python3 scripts/verify/frontend_boundary_gate.py
  python3 scripts/verify/frontend_boundary_gate.py --check
  python3 scripts/verify/frontend_boundary_gate.py --update-baseline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_VERIFY = Path(__file__).resolve().parent
if str(_SCRIPTS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_VERIFY))

from baseline_gate import filter_new_entries, load_baseline, write_baseline  # noqa: E402
from dependency_boundary_scan import ScanResult, scan_directory, Violation  # noqa: E402

DEFAULT_TARGET = ROOT / "apps" / "renderer" / "src"
BASELINE_PATH = ROOT / "scripts" / "verify" / "frontend_boundary_baseline.txt"


def violation_fingerprint(v: Violation) -> str:
    return f"{v.file}:{v.line}:{v.type}:{v.target}"


def collect_violations(target: Path) -> set[str]:
    result = ScanResult()
    scan_directory(target, result)
    return {violation_fingerprint(v) for v in result.violations}


def main() -> int:
    parser = argparse.ArgumentParser(description="Frontend import boundary gate")
    parser.add_argument("--check", action="store_true", help="Fail on new boundary violations")
    parser.add_argument("--update-baseline", action="store_true", help="Rewrite baseline")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    if not args.target.exists():
        print(f"[fe-boundary] SKIP — target missing: {args.target}")
        return 0

    current = collect_violations(args.target)
    loaded = load_baseline(BASELINE_PATH)

    if args.update_baseline:
        write_baseline(BASELINE_PATH, current)
        print(f"[fe-boundary] Baseline updated: {len(current)} entries → {BASELINE_PATH}")
        return 0

    new_entries = filter_new_entries(current, loaded)
    print(
        f"[fe-boundary] Violations: current={len(current)}, "
        f"baseline={len(loaded)}, new={len(new_entries)}"
    )

    if args.check and new_entries:
        print("[fe-boundary] FAIL — new import boundary violations:")
        for entry in new_entries[:25]:
            print(f"  - {entry}")
        if len(new_entries) > 25:
            print(f"  ... and {len(new_entries) - 25} more")
        return 1

    if args.check:
        print("[fe-boundary] PASS — no new import boundary violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
