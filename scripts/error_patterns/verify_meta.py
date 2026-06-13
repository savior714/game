#!/usr/bin/env python3
"""error_patterns.md 메타 금지 블록 정적 검사.

DISCUSS_error_pattern_meta_hook.md §3 합의 (2026-06 갱신):
- 메타 금지 8 normative SSOT는 error_patterns.md (AGENTS.md §2는 pointer만)
- 키워드만 검사, 문장 품질은 v1 범위 밖
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]

REQUIRED: list[tuple[Path, str]] = [
    (
        REPO_ROOT / ".agents" / "core" / "error_patterns.md",
        "메타 금지 11",
    ),
    (
        REPO_ROOT / ".agents" / "core" / "error_patterns.md",
        "디스크 SSOT",
    ),
    (
        REPO_ROOT / "AGENTS.md",
        "error_patterns.md#메타-금지-11",
    ),
]


def check() -> list[str]:
    """필수 키워드 존재 여부를 검사하고, 누락 목록을 반환한다."""
    missing: list[str] = []

    for file_path, keyword in REQUIRED:
        if not file_path.exists():
            missing.append(f"{file_path} — 파일 없음")
            continue

        content = file_path.read_text(encoding="utf-8")
        if keyword not in content:
            missing.append(f"{file_path} — '{keyword}' 누락")

    return missing


def main() -> int:
    """진입점. 누락 있으면 exit 1, 아니면 exit 0."""
    missing = check()

    if missing:
        print("FAIL — 메타 금지 검사 실패:", file=sys.stderr)
        for item in missing:
            print(f"  ✗ {item}", file=sys.stderr)
        return 1

    print("PASS — error_patterns.md 메타 금지 11 · AGENTS pointer 존재")
    return 0


if __name__ == "__main__":
    sys.exit(main())
