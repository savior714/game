"""Load/save error pattern metadata from patterns.yaml (machine SSOT)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PATTERNS_FILE = REPO_ROOT / ".agents" / "core" / "error_patterns" / "patterns.yaml"


def load_patterns() -> list[dict]:
    """Return pattern metadata list from patterns.yaml."""
    if not PATTERNS_FILE.is_file():
        return []
    data = yaml.safe_load(PATTERNS_FILE.read_text(encoding="utf-8")) or {}
    patterns = data.get("patterns", [])
    if not isinstance(patterns, list):
        return []
    return patterns


def save_patterns(patterns: list[dict]) -> None:
    """Persist pattern metadata list to patterns.yaml."""
    PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.dump(
        {"patterns": patterns},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    )
    PATTERNS_FILE.write_text(text, encoding="utf-8")
