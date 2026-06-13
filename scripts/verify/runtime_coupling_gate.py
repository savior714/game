#!/usr/bin/env python3
"""Runtime coupling gate — illegal layer-pair R1 signals only (baseline incremental).

Usage:
  python3 scripts/verify/runtime_coupling_gate.py --check
  python3 scripts/verify/runtime_coupling_gate.py --update-baseline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_VERIFY = Path(__file__).resolve().parent
if str(_SCRIPTS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_VERIFY))

from baseline_gate import filter_new_entries, load_baseline, write_baseline
from runtime_coupling_scan import ScanResult, scan_directory, CouplingSignal

DEFAULT_TARGET = ROOT / "src"
BASELINE_PATH = ROOT / "scripts" / "verify" / "runtime_coupling_baseline.txt"

# Allowed: main→application/infrastructure, application→domain, infrastructure→domain
_ILLEGAL_LAYER_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("domain", "application"),
        ("domain", "infrastructure"),
        ("domain", "main"),
        ("application", "infrastructure"),
        ("application", "main"),
        ("infrastructure", "application"),
        ("infrastructure", "main"),
    }
)


def signal_fingerprint(signal: CouplingSignal) -> str:
    return (
        f"{signal.file}:{signal.line}:{signal.type}:"
        f"{signal.source_layer}->{signal.target_layer}:"
        f"{signal.source_func}->{signal.target_func}"
    )


def collect_gate_signals(target: Path) -> set[str]:
    result = ScanResult()
    scan_directory(target, result)
    return {
        signal_fingerprint(s)
        for s in result.signals
        if s.type == "R1-boundary-cross"
        and (s.source_layer, s.target_layer) in _ILLEGAL_LAYER_PAIRS
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime illegal coupling gate")
    parser.add_argument("--check", action="store_true", help="Fail on new illegal R1 signals")
    parser.add_argument("--update-baseline", action="store_true", help="Rewrite baseline")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    if not args.target.exists():
        print(f"[runtime-coupling] SKIP — target missing: {args.target}")
        return 0

    current = collect_gate_signals(args.target)
    loaded = load_baseline(BASELINE_PATH)

    if args.update_baseline:
        write_baseline(BASELINE_PATH, current)
        print(f"[runtime-coupling] Baseline updated: {len(current)} entries → {BASELINE_PATH}")
        return 0

    new_entries = filter_new_entries(current, loaded)
    print(
        f"[runtime-coupling] Illegal R1: current={len(current)}, "
        f"baseline={len(loaded)}, new={len(new_entries)}"
    )

    if args.check and new_entries:
        print("[runtime-coupling] FAIL — new illegal runtime coupling signals:")
        for entry in new_entries[:25]:
            print(f"  - {entry}")
        if len(new_entries) > 25:
            print(f"  ... and {len(new_entries) - 25} more")
        return 1

    if args.check:
        print("[runtime-coupling] PASS — no new illegal runtime coupling signals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
