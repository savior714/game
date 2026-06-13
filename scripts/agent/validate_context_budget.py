#!/usr/bin/env python3
"""Validate EMR agent context budget guardrails."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO / ".agents"
SKILLS_DIR = AGENTS_DIR / "skills"
OUTPUT_NAME = "COMPILED.md"
FORBIDDEN_NAME = "AGENTS.md"

T0_ALWAYS_APPLY = {
    REPO / "AGENTS.md",
    AGENTS_DIR / "core" / "principles.md",
    AGENTS_DIR / "core" / "error_patterns.md",
}

T0_BYTE_CAPS: dict[str, int] = {
    ".agents/core/error_patterns.md": 10 * 1024,
    ".agents/core/principles.md": 11 * 1024,
}
T0_TOTAL_BYTE_CAP = 28 * 1024 + 256  # headroom for T0 growth (was 28791 at 2026-06)

CURSORIGNORE_REQUIRED_LINES = (
    ".agents/skills/vendor/",
    ".agents/skills/**/COMPILED.md",
    ".agents/skills/**/AGENTS.md",
    ".agents/route/session-manifest.json",
)

COMPILED_SKILLS = (
    AGENTS_DIR / "skills" / "frontend" / "vercel-react-best-practices",
    AGENTS_DIR / "skills" / "frontend" / "vercel-composition-patterns",
)


def _parse_always_apply(path: Path) -> bool | None:
    if not path.is_file():
        return None
    head = path.read_text(encoding="utf-8")[:600]
    m = re.search(r"^always_apply:\s*(\w+)", head, re.MULTILINE)
    if not m:
        return None
    return m.group(1).lower() == "true"


def check_no_skill_agents_md() -> list[str]:
    """Any AGENTS.md under .agents/skills/ triggers Cursor always-applied injection."""
    issues: list[str] = []
    if not SKILLS_DIR.is_dir():
        return issues
    for path in sorted(SKILLS_DIR.rglob(FORBIDDEN_NAME)):
        issues.append(f"Forbidden {path.relative_to(REPO)} (Cursor always-applied risk)")
    return issues


def check_t0_always_apply() -> list[str]:
    issues: list[str] = []
    scan_dirs = [AGENTS_DIR / "core", AGENTS_DIR / "adaptive"]
    for base in scan_dirs:
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.md")):
            val = _parse_always_apply(path)
            if val is None:
                continue
            rel = path.relative_to(REPO)
            if path.resolve() in {p.resolve() for p in T0_ALWAYS_APPLY}:
                if not val:
                    issues.append(f"T0 file must have always_apply: true — {rel}")
            elif val:
                issues.append(
                    f"always_apply: true only allowed on T0 files — {rel} "
                    "(use just route --full for Tier T2)"
                )
    return issues


def check_cursorignore() -> list[str]:
    issues: list[str] = []
    path = REPO / ".cursorignore"
    if not path.is_file():
        issues.append("Missing .cursorignore for context budget exclusions")
        return issues
    text = path.read_text(encoding="utf-8")
    for needle in CURSORIGNORE_REQUIRED_LINES:
        if needle not in text:
            issues.append(f".cursorignore missing entry: {needle}")
    return issues


def check_compiled_skills() -> list[str]:
    issues: list[str] = []
    for skill_dir in COMPILED_SKILLS:
        if not skill_dir.is_dir():
            continue
        rel = skill_dir.relative_to(REPO)
        compiled = skill_dir / OUTPUT_NAME
        forbidden = skill_dir / FORBIDDEN_NAME
        if forbidden.is_file():
            issues.append(f"{rel}/{FORBIDDEN_NAME} must not exist")
        if not compiled.is_file():
            issues.append(f"{rel}/{OUTPUT_NAME} missing — run just agent-skill-build")
    return issues


def check_t0_byte_caps() -> list[str]:
    """Per-file and combined byte caps for Cursor T0 always-applied files."""
    issues: list[str] = []
    total = 0
    for path in sorted(T0_ALWAYS_APPLY):
        if not path.is_file():
            issues.append(f"T0 file missing: {path.relative_to(REPO)}")
            continue
        size = path.stat().st_size
        total += size
        rel = str(path.relative_to(REPO))
        cap = T0_BYTE_CAPS.get(rel)
        if cap is not None and size > cap:
            issues.append(
                f"T0 byte cap exceeded — {rel}: {size} bytes > {cap} bytes"
            )
    if total > T0_TOTAL_BYTE_CAP:
        issues.append(
            f"T0 total byte cap exceeded: {total} bytes > {T0_TOTAL_BYTE_CAP} bytes"
        )
    return issues


def validate() -> list[str]:
    issues: list[str] = []
    issues.extend(check_no_skill_agents_md())
    issues.extend(check_t0_always_apply())
    issues.extend(check_t0_byte_caps())
    issues.extend(check_cursorignore())
    issues.extend(check_compiled_skills())
    return issues


def main() -> int:
    issues = validate()
    if issues:
        print("❌ Context budget validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("✅ Context budget guardrails OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
