#!/usr/bin/env python3
"""Verify that agent-secret required phrases are present in security.md / AGENTS.md.

Exit 0 when all required phrases are found in at least one of the target files.
Exit 1 and report missing phrases otherwise.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Required substrings — the minimum set that must remain in agent-secret docs.
# These are the Zero-Leak guard-rails; add/remove with test updates.
REQUIRED_PHRASES = [
    "비밀 문자열을 읽어 채팅",
    "grep",
    "just",
    "원천 금지",
    "즉시 폐기",
]

TARGET_FILES = [
    ROOT / ".agents" / "core" / "security.md",
    ROOT / "AGENTS.md",
]


def main() -> int:
    errors: list[str] = []

    for phrase in REQUIRED_PHRASES:
        found_in: list[str] = []
        for fpath in TARGET_FILES:
            if not fpath.exists():
                continue
            content = fpath.read_text(encoding="utf-8")
            if phrase in content:
                found_in.append(fpath.name)
        if not found_in:
            errors.append(f"MISSING phrase: {phrase!r} (checked: {[f.name for f in TARGET_FILES if f.exists()]})")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("OK: All required agent-secret phrases found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
