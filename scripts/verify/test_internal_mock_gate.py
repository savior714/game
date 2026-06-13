#!/usr/bin/env python3
"""FE test internal mock gate — vi.mock/jest.mock on SUT internals (baseline incremental).

T-2: Mock은 HTTP·DB·clock·외부 SDK 등 **경계**에서만. features/components/hooks 등
내부 모듈 mock은 baseline burndown 대상이며 **신규** 항목만 FAIL.

Usage:
  python3 scripts/verify/test_internal_mock_gate.py
  python3 scripts/verify/test_internal_mock_gate.py --check
  python3 scripts/verify/test_internal_mock_gate.py --update-baseline
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_VERIFY = Path(__file__).resolve().parent
if str(_SCRIPTS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_VERIFY))

from baseline_gate import filter_new_entries, load_baseline, write_baseline

DEFAULT_TARGET = ROOT / "apps" / "renderer"
BASELINE_PATH = ROOT / "scripts" / "verify" / "test_internal_mock_baseline.txt"

_MOCK_CALL = re.compile(r"""(?:vi|jest)\.mock\s*\(\s*['"]([^'"]+)['"]""")
_TEST_MARKERS = (".test.", ".spec.", "/__tests__/", "/tests/")

# 외부 경계 — T-2 허용 (API gateway, framework, npm package)
_ALLOW_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^next/"),
    re.compile(r"^@/?(?:src/)?lib/"),
    re.compile(r"^[^@./]"),  # bare package name (react, vitest, …)
)

# SUT 내부 레이어 — mock 금지 (신규만 gate)
_INTERNAL_LAYERS = r"(?:features|components|hooks|contexts|stores|app|views)"
_INTERNAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    # @/ · @/src/ alias
    re.compile(rf"^@/?(?:src/)?{_INTERNAL_LAYERS}/"),
    # relative: ../../../src/contexts, ../../stores, ../hooks
    re.compile(rf"(?:\.\./)+(?:src/)?{_INTERNAL_LAYERS}/"),
    # bare src/ (vitest resolve, no @ alias)
    re.compile(rf"^src/{_INTERNAL_LAYERS}/"),
)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _is_test_file(path: Path) -> bool:
    rel = path.as_posix()
    return any(marker in rel for marker in _TEST_MARKERS)


def _is_allowed_mock_target(target: str) -> bool:
    return any(pattern.match(target) for pattern in _ALLOW_PATTERNS)


def _is_internal_mock_target(target: str) -> bool:
    if _is_allowed_mock_target(target):
        return False
    return any(pattern.search(target) for pattern in _INTERNAL_PATTERNS)


def collect_internal_mocks(target: Path) -> set[str]:
    entries: set[str] = set()
    if not target.exists():
        return entries

    for path in sorted(target.rglob("*")):
        if path.suffix not in (".ts", ".tsx") or not path.is_file():
            continue
        if not _is_test_file(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        rel = _rel(path)
        for line_no, line in enumerate(lines, start=1):
            match = _MOCK_CALL.search(line)
            if not match:
                continue
            mock_target = match.group(1)
            if _is_internal_mock_target(mock_target):
                entries.add(f"{rel}:{line_no}:{mock_target}")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Frontend internal mock baseline gate")
    parser.add_argument("--check", action="store_true", help="Fail on new internal mocks")
    parser.add_argument("--update-baseline", action="store_true", help="Rewrite baseline file")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    current = collect_internal_mocks(args.target)
    loaded = load_baseline(BASELINE_PATH)

    if args.update_baseline:
        write_baseline(BASELINE_PATH, current)
        print(f"[test-mock] Baseline updated: {len(current)} entries → {BASELINE_PATH}")
        return 0

    new_entries = filter_new_entries(current, loaded)
    print(
        f"[test-mock] Internal mocks: current={len(current)}, "
        f"baseline={len(loaded)}, new={len(new_entries)}"
    )

    if args.check and new_entries:
        print("[test-mock] FAIL — new internal module mocks (T-2):")
        for entry in new_entries[:20]:
            print(f"  - {entry}")
        if len(new_entries) > 20:
            print(f"  ... and {len(new_entries) - 20} more")
        return 1

    if args.check:
        print("[test-mock] PASS — no new internal module mocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
