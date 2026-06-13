"""Map edit paths to error_patterns detail/*.md for route must_read."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from scripts.agent.route_parsing import normalize_repo_rel

DETAIL_PREFIX = ".agents/core/error_patterns/detail"

# Category → detail file (for add.py body append)
CATEGORY_DETAIL_FILE: dict[str, str] = {
    "파일 편집 실수": "editing.md",
    "테스트 실수": "testing.md",
    "React 실수": "editing.md",
    "도구 사용 실수": "tools.md",
    "계획서 (Blueprint) 실수": "blueprint.md",
    "기타 실수": "workflow.md",
    "프롬프트 라우팅 실패": "workflow.md",
    "Python 의존성 실수": "editing.md",
    "스크립트 경로 오류": "editing.md",
    "계획서 파싱 오류": "blueprint.md",
    "스크립트 사용 오류": "blueprint.md",
    "YAML 파싱 오류": "workflow.md",
    "검증 오인": "workflow.md",
    "환경/도구 오인": "tools.md",
    "메모리 도구 오인": "workflow.md",
}


def detail_file_for_category(category: str) -> str:
    return CATEGORY_DETAIL_FILE.get(category, "workflow.md")


def detail_paths_for_edit_files(
    file_paths: Sequence[str],
    repo_root: Path,
) -> list[str]:
    """Return ordered repo-relative detail paths required before editing file_paths."""
    if not file_paths:
        return []

    ordered: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        rel = f"{DETAIL_PREFIX}/{name}"
        if rel not in seen and (repo_root / rel).is_file():
            seen.add(rel)
            ordered.append(rel)

    add("editing.md")

    for raw in file_paths:
        rel = normalize_repo_rel(str(raw)).lower()
        if not rel:
            continue
        if (
            "tests/" in rel
            or "/test_" in rel
            or rel.startswith("test_")
            or ".test." in rel
            or rel.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
        ):
            add("testing.md")
        if rel.endswith((".tsx", ".jsx")):
            add("editing.md")
        if rel.startswith("docs/plans/") or "/docs/plans/" in rel:
            add("blueprint.md")
        if rel.startswith("docs/discussions/") or "/docs/discussions/" in rel:
            add("workflow.md")
        if rel.startswith(".agents/workflows/"):
            add("workflow.md")
        if rel.startswith(".agents/"):
            add("tools.md")

    return ordered
