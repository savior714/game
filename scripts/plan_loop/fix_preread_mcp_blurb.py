#!/usr/bin/env python3
"""Strip MCP-related instructions from blueprint markdown (archive cleanup)."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.plan_loop.preread_render import LEGACY_MCP_PREREAD_BLURBS

MCP_SERVERS_SECTION_RE = re.compile(
    r"## 🔌 MCP Servers(?: \(실행 전 준비\))?\n(?:.*?\n)*?(?=## )",
    re.MULTILINE,
)
MCP_FIELD_LINE_RE = re.compile(r"^- (\*\*)?MCP(\*\*)?: .*\n", re.MULTILINE)
MCP_AGENT_NOTICE_RE = re.compile(
    r"> \*\*에이전트 주의\*\*: 본 Blueprint 실행 전[^\n]*MCP[^\n]*\n",
    re.MULTILINE,
)
NATIVE_BYPASS_RE = re.compile(
    r" \(🚫 \*\*Native 우회(?:\s우회)?\s*금지\*\*: Target 코드 분석 시 내장 `view_file` 대신 반드시 Task\s*에\s*명시된 MCP 도구 우선 사용할 것\) "
)
NATIVE_BYPASS_SHORT_RE = re.compile(r" \(🚫 \*\*Native 우회 금지\*\*\) ")
MCP_PREREAD_BLURB_RE = re.compile(
    r"> \*\*💡 MCP 도구 적극 활용\*\*:.*?(?:\n|$)",
    re.MULTILINE,
)
MCP_TOOLS_PREREAD_ITEM_RE = re.compile(
    r"^\s+\d+\. .*mcp_tools\.md.*\n",
    re.MULTILINE,
)


def strip_mcp_instructions(text: str) -> str:
    updated = text
    for legacy in LEGACY_MCP_PREREAD_BLURBS:
        updated = updated.replace(legacy, "")
    updated = MCP_SERVERS_SECTION_RE.sub("", updated)
    updated = MCP_FIELD_LINE_RE.sub("", updated)
    updated = MCP_AGENT_NOTICE_RE.sub("", updated)
    updated = MCP_PREREAD_BLURB_RE.sub("", updated)
    updated = MCP_TOOLS_PREREAD_ITEM_RE.sub("", updated)
    updated = NATIVE_BYPASS_RE.sub(" ", updated)
    updated = NATIVE_BYPASS_SHORT_RE.sub("", updated)
    updated = updated.replace("execution.md §2.10", "execution.md §2.8")
    while "\n\n\n" in updated:
        updated = updated.replace("\n\n\n", "\n\n")
    return updated


def fix_file(path: Path, *, dry_run: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = strip_mcp_instructions(text)
    if updated == text:
        return False
    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Blueprint files or directories")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--glob", default="**/*.md", help="Glob when path is a directory")
    args = parser.parse_args()

    targets: list[Path] = []
    for path in args.paths:
        if path.is_dir():
            targets.extend(sorted(path.glob(args.glob)))
        elif path.is_file():
            targets.append(path)

    changed = 0
    for target in targets:
        if fix_file(target, dry_run=args.dry_run):
            changed += 1
            print(f"fixed: {target}")
    print(f"done: {changed} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
