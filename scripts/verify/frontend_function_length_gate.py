#!/usr/bin/env python3
"""FE 함수 라인 수 게이트 — max-lines-per-function (baseline + incremental).

Usage:
  python3 scripts/verify/frontend_function_length_gate.py
  python3 scripts/verify/frontend_function_length_gate.py --check
  python3 scripts/verify/frontend_function_length_gate.py --update-baseline
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_VERIFY = Path(__file__).resolve().parent
if str(_SCRIPTS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_VERIFY))

from baseline_gate import filter_new_entries, load_baseline, write_baseline

DEFAULT_TARGET = ROOT / "apps" / "renderer" / "src"
BASELINE_PATH = ROOT / "scripts" / "verify" / "frontend_function_length_baseline.txt"
MAX_FUNCTION_LINES = 100

SKIP_MARKERS = (".test.", ".spec.", "/__tests__/", "/mocks/")

_FUNC_START = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)"
)
_ARROW_START = re.compile(
    r"^\s*(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?"
    r"(?:\([^)]*\)|[\w<>,\s\[\]?&|]+)\s*=>"
)


@dataclass(frozen=True)
class FunctionSpan:
    file: str
    name: str
    start_line: int
    end_line: int

    @property
    def length(self) -> int:
        return self.end_line - self.start_line + 1

    @property
    def fingerprint(self) -> str:
        return f"{self.file}:{self.start_line}:{self.name}:{self.length}"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _should_skip(path: Path) -> bool:
    rel = path.as_posix()
    return any(marker in rel for marker in SKIP_MARKERS)


def extract_functions(file_path: Path) -> list[FunctionSpan]:
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    rel = _rel(file_path)
    spans: list[FunctionSpan] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = _FUNC_START.match(line) or _ARROW_START.match(line)
        if not match:
            i += 1
            continue

        name = match.group(1)
        start = i
        brace = 0
        started = False
        j = i
        while j < len(lines):
            for ch in lines[j]:
                if ch == "{":
                    brace += 1
                    started = True
                elif ch == "}":
                    brace -= 1
            if started and brace <= 0:
                spans.append(FunctionSpan(rel, name, start + 1, j + 1))
                i = j + 1
                break
            j += 1
        else:
            i += 1
    return spans


def collect_oversized(target: Path, max_lines: int) -> set[str]:
    entries: set[str] = set()
    if not target.exists():
        return entries
    for path in sorted(target.rglob("*")):
        if path.suffix not in (".ts", ".tsx") or not path.is_file():
            continue
        if _should_skip(path):
            continue
        for span in extract_functions(path):
            if span.length > max_lines:
                entries.add(span.fingerprint)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Frontend max-lines-per-function gate")
    parser.add_argument("--check", action="store_true", help="Fail on new oversized functions")
    parser.add_argument("--update-baseline", action="store_true", help="Rewrite baseline file")
    parser.add_argument("--max-lines", type=int, default=MAX_FUNCTION_LINES)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    current = collect_oversized(args.target, args.max_lines)
    loaded = load_baseline(BASELINE_PATH)

    if args.update_baseline:
        write_baseline(BASELINE_PATH, current)
        print(f"[func-len] Baseline updated: {len(current)} entries → {BASELINE_PATH}")
        return 0

    new_entries = filter_new_entries(current, loaded)
    print(
        f"[func-len] Oversized (>{args.max_lines} lines): "
        f"current={len(current)}, baseline={len(loaded)}, new={len(new_entries)}"
    )

    if args.check and new_entries:
        print("[func-len] FAIL — new oversized functions:")
        for entry in new_entries[:20]:
            print(f"  - {entry}")
        if len(new_entries) > 20:
            print(f"  ... and {len(new_entries) - 20} more")
        return 1

    if args.check:
        print("[func-len] PASS — no new oversized functions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
