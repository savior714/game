#!/usr/bin/env python3
"""BE 함수 라인 수 게이트 — max-lines-per-function (baseline + incremental).

Usage:
  python3 scripts/verify/backend_function_length_gate.py
  python3 scripts/verify/backend_function_length_gate.py --check
  python3 scripts/verify/backend_function_length_gate.py --update-baseline
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_VERIFY = Path(__file__).resolve().parent
if str(_SCRIPTS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_VERIFY))

from baseline_gate import filter_new_entries, load_baseline, write_baseline  # noqa: E402

DEFAULT_TARGET = ROOT / "src"
BASELINE_PATH = ROOT / "scripts" / "verify" / "backend_function_length_baseline.txt"
MAX_FUNCTION_LINES = 100

SKIP_DIR_MARKERS = ("/tests/", "/test/", "/__pycache__/")


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
    return any(marker in rel for marker in SKIP_DIR_MARKERS)


def extract_functions(file_path: Path) -> list[FunctionSpan]:
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    rel = _rel(file_path)
    spans: list[FunctionSpan] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = node.end_lineno or node.lineno
        spans.append(FunctionSpan(rel, node.name, node.lineno, end))
    return spans


def collect_oversized(target: Path, max_lines: int) -> set[str]:
    entries: set[str] = set()
    if not target.exists():
        return entries
    for path in sorted(target.rglob("*.py")):
        if not path.is_file() or _should_skip(path):
            continue
        for span in extract_functions(path):
            if span.length > max_lines:
                entries.add(span.fingerprint)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Backend max-lines-per-function gate")
    parser.add_argument("--check", action="store_true", help="Fail on new oversized functions")
    parser.add_argument("--update-baseline", action="store_true", help="Rewrite baseline file")
    parser.add_argument("--max-lines", type=int, default=MAX_FUNCTION_LINES)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    current = collect_oversized(args.target, args.max_lines)
    loaded = load_baseline(BASELINE_PATH)

    if args.update_baseline:
        write_baseline(BASELINE_PATH, current)
        print(f"[be-func-len] Baseline updated: {len(current)} entries → {BASELINE_PATH}")
        return 0

    new_entries = filter_new_entries(current, loaded)
    print(
        f"[be-func-len] Oversized (>{args.max_lines} lines): "
        f"current={len(current)}, baseline={len(loaded)}, new={len(new_entries)}"
    )

    if args.check and new_entries:
        print("[be-func-len] FAIL — new oversized functions:")
        for entry in new_entries[:20]:
            print(f"  - {entry}")
        if len(new_entries) > 20:
            print(f"  ... and {len(new_entries) - 20} more")
        return 1

    if args.check:
        print("[be-func-len] PASS — no new oversized functions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
