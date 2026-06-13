#!/usr/bin/env python3
"""Git-touched paths eligible for route-gate-check (turn-end / CI)."""
# ruff: noqa: S607
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.agent.route_context import normalize_repo_rel, sanitize_route_paths  # noqa: E402

_ROUTE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".md",
        ".json",
        ".yml",
        ".yaml",
    }
)
_SKIP_PREFIXES = (
    "docs/plans/archive/",
    "docs/reports/tool_logs/",
    "node_modules/",
    ".agents/",
)


def _git_touched_files(repo_root: Path) -> list[str]:
    touched: set[str] = set()
    try:
        status_output = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in status_output.splitlines():
            if not line.strip():
                continue
            status_part = line[:2]
            path_part = line[3:].strip().strip('"')
            if "D" not in status_part and path_part:
                touched.add(path_part)
    except (subprocess.SubprocessError, OSError):
        pass

    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "--name-only"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for path in diff_output.splitlines():
            if path.strip():
                touched.add(path.strip())
    except (subprocess.SubprocessError, OSError):
        pass

    valid: list[str] = []
    for rel in sorted(touched):
        full = repo_root / rel
        if full.is_file():
            valid.append(normalize_repo_rel(rel))
    return valid


def _eligible_for_route_gate(rel: str) -> bool:
    norm = normalize_repo_rel(rel)
    if not norm:
        return False
    for prefix in _SKIP_PREFIXES:
        if norm.startswith(prefix):
            return False
    return Path(norm).suffix.lower() in _ROUTE_EXTENSIONS


def collect_touched_route_paths(repo_root: Path | None = None) -> list[str]:
    root = repo_root or _REPO
    raw = _git_touched_files(root)
    cleaned = sanitize_route_paths(raw)
    return [p for p in cleaned if _eligible_for_route_gate(p)]


def main() -> int:
    paths = collect_touched_route_paths()
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
