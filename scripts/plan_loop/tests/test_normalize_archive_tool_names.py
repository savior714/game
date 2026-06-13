"""Tests for archive plan legacy tool name normalization."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO / "scripts" / "plan_loop") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts" / "plan_loop"))

from normalize_archive_tool_names import normalize_text, repo_relative  # noqa: E402


def test_token_replacements() -> None:
    raw = "Use read_file then apply_diff and list_files with grep_search."
    out, n = normalize_text(raw)
    assert n >= 4
    assert "Read" in out
    assert "StrReplace" in out
    assert "Glob" in out
    assert "Grep" in out
    assert "read_file" not in out


def test_repo_relative_uses_cwd_prefix() -> None:
    rel = repo_relative(Path("docs/ops/rules/DOC_troubleshooting.md"))
    assert rel == "docs/ops/rules/DOC_troubleshooting.md"


def test_literal_and_particle_fixes() -> None:
    raw = (
        "- **Action**: `[Edit File]` (apply_diff)\n"
        "- Verify: view_file로 self.session.flush() 확인\n"
        "- Pre-read: `Write`/`StrReplace` 전 Read\n"
    )
    out, n = normalize_text(raw)
    assert n >= 3
    assert "[Edit File]" not in out
    assert "Read로" in out
    assert "`write`/`patch`" in out
    assert "`Write`/`StrReplace`" not in out
