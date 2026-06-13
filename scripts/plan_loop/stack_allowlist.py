"""Stack allowlist loader (STK-002) — SSOT from guide_SPEC_TECH_stack_upgrade_enforcement.md.

Loads the allowed technology tokens defined in the Stack Enforcement spec so that
plan-lint can verify declared tech in Blueprint files against this single source.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SPEC_PATH = _REPO_ROOT / "docs" / "specs" / "technical" / "guide_SPEC_TECH_stack_upgrade_enforcement.md"


def _parse_allowlist_from_spec(spec_path: Path) -> set[str]:
    """Parse allowed technology tokens from the Stack Enforcement spec markdown.

    Reads sections 2.1 (Backend/Python), 2.2 (Frontend), and 2.3 (DevOps/Ops)
    from guide_SPEC_TECH_stack_upgrade_enforcement.md and extracts all bolded
    technology names as a flat token set.

    Also extracts non-bolded tokens from the same sections (e.g. `uv`, `ty`,
    `ruff`, `asyncpg`, `SQLModel`, `FastAPI`, `Nushell`, `Lazydocker`,
    `PostgreSQL`, `Docker`, `just`).
    """
    if not spec_path.exists():
        return set()

    text = spec_path.read_text(encoding="utf-8")

    # Find sections 2.1, 2.2, 2.3 — from "## 2) 허용 스택 (Allowlist)" to next "## 3)"
    sections_match = re.search(
        r"## 2\) 허용 스택 \(Allowlist\).*?(?=## 3\))",
        text,
        re.DOTALL,
    )
    if not sections_match:
        return set()

    section_text = sections_match.group(0)

    tokens: set[str] = set()

    # Extract bolded names: **name** or **bold text with spaces**
    for match in re.finditer(r"\*\*([^*]+)\*\*", section_text):
        name = match.group(1).strip()
        if name:
            tokens.add(name)

    # Extract inline code names: `name`
    for match in re.finditer(r"`([^`]+)`", section_text):
        name = match.group(1).strip()
        if name:
            tokens.add(name)

    # Extract standalone Python tool names from section 2.1 bullets
    # e.g. "- 패키지/가상환경: `uv`"
    # Already handled by inline code above

    return tokens


def load_allowlist_tokens(spec_path: Path | None = None) -> frozenset[str]:
    """Load the allowlist token set from the Stack Enforcement spec.

    Returns a frozenset of allowed technology names (case-sensitive).
    This is the single source of truth for plan-lint stack validation.
    """
    path = spec_path or _SPEC_PATH
    return frozenset(_parse_allowlist_from_spec(path))


def check_stack_in_allowlist(declared: str, spec_path: Path | None = None) -> bool:
    """Check if a declared technology name is in the allowlist.

    Args:
        declared: A technology name extracted from a Blueprint's "기술 스택" line.
        spec_path: Optional override for the spec file path.

    Returns:
        True if the declared name matches at least one allowlist token.
    """
    tokens = load_allowlist_tokens(spec_path)

    # Direct match
    if declared in tokens:
        return True

    # Partial match: check if declared is a substring of any token or vice versa
    declared_lower = declared.lower()
    for token in tokens:
        if declared_lower in token.lower() or token.lower() in declared_lower:
            return True

    return False


def get_denylist() -> dict[str, str]:
    """Return the denylist mapping from the spec: {forbidden_tech: recommended_alternative}.

    Returns an empty dict if the spec cannot be parsed.
    """
    if not _SPEC_PATH.exists():
        return {}

    text = _SPEC_PATH.read_text(encoding="utf-8")

    # Find section 3) 비허용 스택 (Denylist)
    denylist_match = re.search(
        r"## 3\) 비허용 스택 \(Denylist\).*?(?=---)",
        text,
        re.DOTALL,
    )
    if not denylist_match:
        return {}

    section_text = denylist_match.group(0)

    # Parse "forbidden -> alternative" lines
    denylist: dict[str, str] = {}
    for match in re.finditer(r"`([^`]+)`\s*->\s*\*\*([^*]+)\*\*", section_text):
        forbidden, alternative = match.group(1).strip(), match.group(2).strip()
        denylist[forbidden] = alternative

    # Also parse lines without markdown formatting: "name -> alternative"
    for match in re.finditer(r"^[-•]\s+`([^`]+)`\s*->\s*([^*\n]+)", section_text, re.MULTILINE):
        forbidden, alternative = match.group(1).strip(), match.group(2).strip().strip("*")
        if forbidden not in denylist:
            denylist[forbidden] = alternative

    # Clean up leftover backticks from inline code in alternative names
    cleaned: dict[str, str] = {}
    for k, v in denylist.items():
        cleaned[k] = v.replace("`", "").replace("*", "").strip()
    return cleaned
