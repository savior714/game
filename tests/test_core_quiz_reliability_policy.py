from __future__ import annotations

import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = "docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md"
MEMORY_VERIFY = (
    "uv run pytest -q tests/test_core_quiz_reliability_policy.py::"
    "test_memory_handoff_tracks_current_product_direction"
)
SUBJECT_PATHS = (
    "domains/math/",
    "domains/english/",
    "domains/korean/",
    "domains/science/",
)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_current_direction_is_reachable_from_all_authority_layers() -> None:
    agents = read("AGENTS.md")
    project_rules = read("PROJECT_RULES.md")
    readme = read("README.md")
    memory = read("docs/agent-context/memory/MEMORY.md")

    for document in (agents, project_rules, readme, memory):
        assert SPEC_PATH in document

    for subject_path in SUBJECT_PATHS:
        assert subject_path in project_rules

    assert "Ocean Rescue" in agents
    assert "experiments/" in agents
    assert "신규 기능·구조 이전" in agents
    assert "명시적으로 변경" in agents
    assert "최근 커밋" in agents


def test_memory_handoff_tracks_current_product_direction() -> None:
    memory_path = ROOT / "docs/agent-context/memory/MEMORY.md"
    memory = memory_path.read_text(encoding="utf-8")
    hygiene = read(".agents/core/memory_hygiene.md")

    assert len(memory.splitlines()) <= 200
    assert SPEC_PATH in memory
    assert "공통 브라우저 진단" in memory
    assert "한 failure domain" in memory
    assert MEMORY_VERIFY in memory
    assert MEMORY_VERIFY in hygiene
    assert "just memory-verify" not in memory
    assert "just memory-verify" not in hygiene

    match = re.search(r"^last_verified:\s*(\d{4}-\d{2}-\d{2})$", memory, re.MULTILINE)
    assert match is not None
    assert date.fromisoformat(match.group(1)) >= date(2026, 8, 6)


def test_policy_guard_does_not_assert_schedule_status() -> None:
    source = Path(__file__).read_text(encoding="utf-8")

    forbidden_schedule_assertions = (
        "WP COMPLETE",
        "현재 WP",
        "다음 WP",
        "Status:** ACTIVE",
    )
    for phrase in forbidden_schedule_assertions:
        assert phrase not in source
