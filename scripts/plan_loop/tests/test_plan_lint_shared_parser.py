"""Regression tests for plan_lint.shared task block parsers."""

from scripts.plan_loop.plan_lint.shared import (
    _parse_fields,
    _split_task_blocks,
)

PACKED_TASK_BLOCK = """
#### Task 1.1: Extract shared parser [Unit: Atomic]
- Task-ID: [LINT-SHR-005] | Status: todo | Priority: 1 | RetryPolicy: none
- Goal: packed meta parses Status
"""

INDENTED_PREREAD_BLOCK = """
#### Task 1.2: Pre-read multiline [Unit: Atomic]
- Task-ID: [LINT-SHR-005]
- Status: running
- Pre-read:
  1. `[rule]` `.agents/domains/testing/tdd.md`
  2. `[project_skill]` `.agents/skills/frontend/web-design-guidelines/SKILL.md`
- Goal: collect indented pre-read lines
"""

PIPE_INLINE_STATUS_BLOCK = """
#### Task 1.3: Pipe inline fields [Unit: Atomic]
- Task-ID: [LINT-SHR-005]
- **Status**: todo | **RetryPolicy**: none | **Priority**: 2
- Goal: pipe-separated bold keys parse as separate fields
"""


def test_packed_task_meta_parses_status() -> None:
    blocks = _split_task_blocks(PACKED_TASK_BLOCK)
    assert len(blocks) == 1
    fields = _parse_fields(blocks[0])
    assert fields["Task-ID"] == "[LINT-SHR-005]"
    assert fields["Status"] == "todo"
    assert fields["Priority"] == "1"
    assert fields["RetryPolicy"] == "none"


def test_indented_preread_multiline_collected() -> None:
    blocks = _split_task_blocks(INDENTED_PREREAD_BLOCK)
    assert len(blocks) == 1
    fields = _parse_fields(blocks[0])
    assert "tdd.md" in fields["Pre-read"]
    assert "web-design-guidelines" in fields["Pre-read"]
    assert fields["Status"] == "running"


def test_pipe_inline_bold_fields_extracted() -> None:
    blocks = _split_task_blocks(PIPE_INLINE_STATUS_BLOCK)
    assert len(blocks) == 1
    fields = _parse_fields(blocks[0])
    assert fields["Status"] == "todo"
    assert fields["RetryPolicy"] == "none"
    assert fields["Priority"] == "2"


def test_split_task_blocks_finds_numbered_headings() -> None:
    text = PACKED_TASK_BLOCK + INDENTED_PREREAD_BLOCK
    blocks = _split_task_blocks(text)
    assert len(blocks) == 2
    assert blocks[0].startswith("#### Task 1.1:")
    assert blocks[1].startswith("#### Task 1.2:")
