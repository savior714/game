#!/usr/bin/env python3
"""FE Biome cognitive complexity gate — warn diagnostics + baseline incremental.

Usage:
  python3 scripts/verify/frontend_complexity_gate.py
  python3 scripts/verify/frontend_complexity_gate.py --check
  python3 scripts/verify/frontend_complexity_gate.py --update-baseline
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_VERIFY = Path(__file__).resolve().parent
if str(_SCRIPTS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_VERIFY))

from baseline_gate import filter_new_entries, load_baseline, write_baseline  # noqa: E402

DEFAULT_FRONTEND = ROOT / "apps" / "renderer"
BASELINE_PATH = ROOT / "scripts" / "verify" / "frontend_complexity_baseline.txt"
COMPLEXITY_CATEGORY = "lint/complexity/noExcessiveCognitiveComplexity"


def _parse_biome_json(raw: str) -> dict:
    for line in raw.splitlines():
        candidate = line.strip()
        if candidate.startswith("{") and '"diagnostics"' in candidate and '"summary"' in candidate:
            return json.loads(candidate)
    return {}


def collect_complexity_violations(frontend_dir: Path) -> set[str]:
    proc = subprocess.run(
        ["pnpm", "run", "lint:ci", "--reporter=json"],
        cwd=str(frontend_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    report = _parse_biome_json(proc.stdout + proc.stderr)
    entries: set[str] = set()
    for item in report.get("diagnostics", []):
        category = item.get("category", "")
        if COMPLEXITY_CATEGORY not in category:
            continue
        location = item.get("location", {})
        path = location.get("path", "<unknown>")
        start = location.get("start", {})
        line = start.get("line", 0)
        message = item.get("message", "").replace("\n", " ").strip()
        entries.add(f"{path}:{line}:{category}:{message}")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Frontend Biome complexity baseline gate")
    parser.add_argument("--check", action="store_true", help="Fail on new complexity violations")
    parser.add_argument("--update-baseline", action="store_true", help="Rewrite baseline file")
    parser.add_argument("--frontend", type=Path, default=DEFAULT_FRONTEND)
    args = parser.parse_args()

    if not args.frontend.exists():
        print(f"[fe-complexity] SKIP — frontend missing: {args.frontend}")
        return 0

    current = collect_complexity_violations(args.frontend)
    loaded = load_baseline(BASELINE_PATH)

    if args.update_baseline:
        write_baseline(BASELINE_PATH, current)
        print(f"[fe-complexity] Baseline updated: {len(current)} entries → {BASELINE_PATH}")
        return 0

    new_entries = filter_new_entries(current, loaded)
    print(
        f"[fe-complexity] Violations: current={len(current)}, "
        f"baseline={len(loaded)}, new={len(new_entries)}"
    )

    if args.check and new_entries:
        print("[fe-complexity] FAIL — new cognitive complexity violations:")
        for entry in new_entries[:20]:
            print(f"  - {entry}")
        if len(new_entries) > 20:
            print(f"  ... and {len(new_entries) - 20} more")
        return 1

    if args.check:
        print("[fe-complexity] PASS — no new cognitive complexity violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
