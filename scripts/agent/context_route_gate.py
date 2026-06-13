#!/usr/bin/env python3
"""Context Route Gate — 파일 수정 전 must_read 강제 로드.

routing.md §2 Context Route Gate 절차를 자동화합니다.
에이전트 워크플로우에서 파일 수정 전 이 스크립트를 호출하면:
  1. must_read 목록을 JSON으로 출력
  2. 각 항목의 installed 상태를 포함

Usage:
    uv run python scripts/agent/context_route_gate.py --files a.py b.tsx --json
    uv run python scripts/agent/context_route_gate.py --files a.py b.tsx

Output format (JSON):
    {
      "must_read": [
        {"path": ".agents/core/execution.md", "kind": "rule", "installed": true},
        ...
      ],
      "gate_command": "just route -- <paths> --json",
      "before_edit": "Read every path in must_read where installed=true before patching."
    }

Verify:  uv run python scripts/agent/context_route_gate.py --files test.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

# Import from route_context to reuse its engine
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.agent.route_context import (  # noqa: E402
    get_route_bundle,
)


def context_route_gate(
    file_paths: Sequence[str],
    *,
    repo_root: Path | None = None,
    tight: bool = False,
) -> dict:
    """Run Context Route Gate and return must_read bundle."""
    bundle = get_route_bundle(
        file_paths,
        repo_root=repo_root,
        apply_cap=not tight,
        cap=2 if tight else 5,
        tight=tight,
    )
    return {
        "must_read": bundle["must_read"],
        "must_read_paths": bundle["must_read_paths"],
        "missing_paths": bundle.get("missing_paths", []),
        "gate_command": bundle["gate"]["command"],
        "before_edit": bundle["gate"]["before_edit"],
        "tight": tight,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Context Route Gate — enforce must_read before file edits."
    )
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="Repo-relative file paths to check (e.g., src/foo.py docs/bar.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format (for machine consumption).",
    )
    parser.add_argument(
        "--tight",
        action="store_true",
        help="Ultra-light mode: cap skills at 2, skip Always Load rules.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    gate_result = context_route_gate(args.files, tight=args.tight)

    if args.json:
        print(json.dumps(gate_result, ensure_ascii=False, indent=2))
    else:
        must_read = gate_result["must_read"]
        installed = [e for e in must_read if e.get("installed")]
        missing = [e for e in must_read if not e.get("installed")]

        print(f"🔒 Context Route Gate — {len(args.files)} file(s)")
        print()
        if installed:
            print(f"  MUST READ ({len(installed)} installed):")
            for e in installed:
                lazy = " [lazy]" if e.get("lazy_load") else ""
                print(f"    [{e.get('kind', '?'):14}{lazy}] {e['path']}")
        else:
            print("  MUST READ: (none)")

        if missing:
            print(f"  Missing ({len(missing)}):")
            for e in missing:
                print(f"    [{e.get('kind', '?'):14}] {e['path']}")

        print()
        print(f"  Gate: {gate_result['before_edit']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
