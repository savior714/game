#!/usr/bin/env python3
"""Agent governance path gates: meta prohibitions + patterns ID sort.

Runs before route gate returns ok for paths under .agents, scripts, or docs/plans.
FAIL → stderr one-line tag ([META] / [SORT]) and exit code 1 via caller.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.agent.route_context import normalize_repo_rel

_AGENT_PREFIXES = (
    ".agents/",
    "scripts/",
    "docs/plans/",
)


def needs_agent_pattern_gates(paths: Sequence[str]) -> bool:
    """True when any edit path is agent governance scope."""
    for raw in paths:
        rel = normalize_repo_rel(raw)
        if not rel:
            continue
        if rel.startswith(_AGENT_PREFIXES):
            return True
    return False


def _run_just(recipe: str, repo_root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        ["just", recipe],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    err = (proc.stderr or proc.stdout or "").strip()
    return proc.returncode, err


def run_agent_pattern_gates(repo_root: Path) -> tuple[bool, str]:
    """
    Run meta then sort checks. Returns (ok, message).
    On failure message is a single stderr line with [META] or [SORT] prefix.
    """
    code, detail = _run_just("agent-meta-prohibitions-check", repo_root)
    if code != 0:
        line = detail.splitlines()[-1] if detail else "메타 금지 검사 실패"
        return False, f"[META] {line}"

    code, detail = _run_just("error-patterns-sort-check", repo_root)
    if code != 0:
        line = detail.splitlines()[-1] if detail else "patterns ID 순서 검사 실패"
        return False, f"[SORT] {line}"

    return True, ""


def main(argv: Sequence[str] | None = None) -> int:
    from scripts.agent.route_context import find_repo_root  # noqa: PLC0415

    root = find_repo_root()
    ok, msg = run_agent_pattern_gates(root)
    if not ok:
        print(msg, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
