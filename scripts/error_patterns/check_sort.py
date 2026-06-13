#!/usr/bin/env python3
"""patterns.yaml 패턴 ID 순서 검증.

새 패턴이 추가될 때마다 append-only 로 쌓여 ID 순서가 무너지는 것을 방지.
CLI: just error-patterns-sort-check
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.error_patterns.patterns_store import load_patterns, save_patterns  # noqa: E402


def load_ids() -> list[str]:
    """patterns.yaml 에서 패턴 ID 목록 추출."""
    patterns = load_patterns()
    if not patterns:
        print("ERROR: patterns.yaml에 패턴 없음", file=sys.stderr)
        sys.exit(1)
    return [str(p["id"]) for p in patterns if isinstance(p, dict) and "id" in p]


def check_sorted(ids: list[str]) -> list[tuple[int, str, str]]:
    """ID 가 숫자 순서대로 정렬되었는지 확인. 어긋난 위치 반환."""
    sorted_ids = sorted(ids, key=lambda x: tuple(map(int, x.split("."))))
    return [(i, ids[i], sorted_ids[i]) for i in range(len(ids)) if ids[i] != sorted_ids[i]]


def main() -> int:
    ids = load_ids()
    violations = check_sorted(ids)

    if not violations:
        print(f"PASS — patterns ID {len(ids)}개 모두 정렬 완료")
        return 0

    print(f"FAIL — patterns ID 순서 어김 {len(violations)}개", file=sys.stderr)
    for pos, actual, expected in violations:
        print(f"  position {pos}: '{actual}' → '{expected}' 필요", file=sys.stderr)

    print(
        "\n수정: patterns.yaml patterns 배열을 ID 숫자 순으로 정렬 후 save_patterns()",
        file=sys.stderr,
    )
    print(
        "  uv run python -c \"from scripts.error_patterns.patterns_store import load_patterns, save_patterns; "
        "p=load_patterns(); p.sort(key=lambda x: tuple(map(int, x['id'].split('.')))); save_patterns(p)\"",
        file=sys.stderr,
    )

    return 1


if __name__ == "__main__":
    sys.exit(main())
