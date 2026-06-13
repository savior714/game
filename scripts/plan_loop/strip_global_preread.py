#!/usr/bin/env python3
"""Remove experimental ``### 📌 Global Pre-read`` blocks from Blueprint plans.

Superseded by ``## 🧭 Context Pre-read Gate`` (``plan-preread:v1``). Safe to run
on archive trees; leaves task prose that mentions Global Pre-read unchanged.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

GLOBAL_PREREAD_BLOCK_RE = re.compile(
    r"^### 📌 Global Pre-read \(세션 시작 시 한 번 로드\)\s*\n"
    r"(?:- [^\n]+\n)*"
    r"\n?"
    r"\.agents/[^\n]+\n"
    r"\n*",
    re.MULTILINE,
)
# Leftovers when heading was removed without the path line (earlier buggy pass).
ORPHAN_GLOBAL_PATH_RE = re.compile(
    r"^\.agents/[^\n]*cognitive_logging\.md[^\n]*\n+",
    re.MULTILINE,
)
EXCESS_BLANK_RE = re.compile(r"\n{3,}")


def strip_global_preread(text: str) -> tuple[str, int]:
    new_text, count = GLOBAL_PREREAD_BLOCK_RE.subn("", text)
    new_text, orphan = ORPHAN_GLOBAL_PATH_RE.subn("", new_text)
    new_text = EXCESS_BLANK_RE.sub("\n\n", new_text)
    return new_text.lstrip("\n"), count + orphan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        default=[_REPO / "docs" / "plans"],
        help="Directories to scan (default: docs/plans)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    changed_files = 0
    removed_blocks = 0
    for root_arg in args.roots:
        scan_root = root_arg.resolve()
        if not scan_root.exists():
            print(f"skip missing: {scan_root}")
            continue
        for path in sorted(scan_root.rglob("*.md")):
            if path.name in {"README.md", "ROADMAP.md"}:
                continue
            text = path.read_text(encoding="utf-8")
            if "### 📌 Global Pre-read" not in text and not ORPHAN_GLOBAL_PATH_RE.search(
                text
            ):
                continue
            new_text, count = strip_global_preread(text)
            if new_text == text:
                continue
            rel = path.relative_to(_REPO)
            print(f"  {rel}: removed {count} block(s)")
            removed_blocks += count
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")
                changed_files += 1
            else:
                changed_files += 1

    label = "Would update" if args.dry_run else "Updated"
    print(f"{label} {changed_files} file(s), {removed_blocks} block(s) removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
