"""Advisory checks for unittest.mock.patch targets in tests.

Flags string targets under ``src.`` (application code). Prefer DI container
override via ``tests/helpers/mocking.py`` for router/repo/service seams.

This module is intentionally **non-blocking**: callers emit warnings or
reports; it does not fail plan or CI gates by itself.
"""

from __future__ import annotations

import re
from pathlib import Path

# String literal first argument to patch-like calls, targeting app code.
_PATCH_TARGET_RE = re.compile(
    r"""(?x)
    (?:
        @\s*(?:unittest\.)?mock\.patch
        |
        \b(?:unittest\.)?mock\.patch
        |
        \bmocker\.patch
        |
        (?<![.\w])patch(?=\s*\()
    )
    \s*\(\s*["'](?P<target>src\.[^"']+)["']
    """
)


def collect_internal_patch_warnings(text: str, rel_path: str = "<string>") -> list[str]:
    """Return advisory messages for patch targets pointing at ``src.`` modules.

    Only single-line occurrences are detected (multiline ``patch(`` + string is
    skipped). Lines whose first non-whitespace token is ``#`` are ignored.
    """
    out: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for m in _PATCH_TARGET_RE.finditer(line):
            target = m.group("target")
            out.append(
                f"[advisory] {rel_path}:{lineno}: patch targets internal symbol {target!r} "
                "(prefer app.container provider override / tests.helpers.mocking.override_di_providers)"
            )
    return out


def collect_internal_patch_warnings_for_paths(paths: list[Path], root: Path) -> list[str]:
    """Scan files and return flattened advisory lines (paths relative to *root*)."""
    all_msgs: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        all_msgs.extend(collect_internal_patch_warnings(text, rel_path=rel))
    return all_msgs
