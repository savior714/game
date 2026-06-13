#!/usr/bin/env python3
"""Estimate Cursor T0 always-applied context size (token budget)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.agent.route_budget import estimate_tokens  # noqa: E402

T0_FILES = (
    "AGENTS.md",
    ".agents/core/principles.md",
    ".agents/core/error_patterns.md",
)

DEFAULT_TARGET_TOKENS = 8000


def estimate_t0(repo_root: Path, *, target_tokens: int = DEFAULT_TARGET_TOKENS) -> dict:
    """Return per-file and total token estimates for Cursor T0 injection."""
    files: list[dict] = []
    total = 0
    for rel in T0_FILES:
        full = repo_root / rel
        tokens = estimate_tokens(full)
        files.append({"path": rel, "tokens": tokens, "bytes": full.stat().st_size if full.is_file() else 0})
        total += tokens
    return {
        "files": files,
        "total_tokens": total,
        "target_tokens": target_tokens,
        "within_target": total <= target_tokens,
        "status": "PASS" if total <= target_tokens else "WARN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate Cursor T0 context token budget")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET_TOKENS, help="Target token budget")
    args = parser.parse_args()

    report = estimate_t0(REPO, target_tokens=args.target)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"T0 estimate: {report['total_tokens']} tok (target {report['target_tokens']}) — {report['status']}")
        for entry in report["files"]:
            print(f"  {entry['path']}: {entry['tokens']} tok ({entry['bytes']} bytes)")
    return 0 if report["within_target"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
