"""error_patterns detail 파일 렌더링 — LLM 선제 지침 형식 (B: 원칙 + 참고 1개)."""

from __future__ import annotations

DETAIL_INTRO_EDITING = """\
> **역할**: WRONG/CORRECT 예시 전용. 규범(도구 분기·Editing Rules·패치 전제조건)은 [runtime_edit_tools.md](../../runtime_edit_tools.md) · Cursor 상세 [routing.md](../../routing.md) §1 — 본문에 재서술하지 않는다.
> **도구**: 세션에 노출된 호스트 읽기·부분 수정·쓰기 도구 ([runtime_edit_tools.md §1](../../runtime_edit_tools.md)). 예시 블록의 `StrReplace`/`old_string`은 Cursor 표기일 수 있음.
"""

DETAIL_INTRO_TOOLS = """\
> **역할**: LLM이 읽고 재발을 막을 **선제 지침**. 규범 SSOT는 [routing.md](../../routing.md) §1 · MCP 도구명은 세션 `mcps/` 디스크립터.
"""

DETAIL_INTRO_DEFAULT = """\
> **역할**: LLM이 읽고 재발을 막을 **선제 지침**. 규범·워크플로 SSOT는 각 SKILL·[error_patterns.md](../../error_patterns.md) 메타 금지 8.
"""

FRONTMATTER = """\
---
scope: detail
domain: core
parent: .agents/core/error_patterns.md
lazy_load: true
---
<!-- Language: ko -->

"""


def render_pattern(
    pattern_id: str,
    title: str,
    situation: str,
    avoid: str,
    instead: str,
    mnemonic: str,
    reference: str | None = None,
) -> str:
    """한 패턴 섹션을 선제 지침 형식으로 렌더."""
    ref_block = ""
    if reference and reference.strip():
        ref_block = (
            f"\n<details>\n<summary>참고 (예시 1개)</summary>\n\n"
            f"{reference.strip()}\n\n</details>\n"
        )
    return (
        f"### {pattern_id} {title}\n\n"
        f"**상황**: {situation}\n\n"
        f"**하지 말 것**: {avoid}\n\n"
        f"**대신 할 것**: {instead}\n\n"
        f"**기억할 한 줄**: {mnemonic}\n"
        f"{ref_block}"
    )


def render_detail_file(
    intro: str,
    sections: list[tuple[str, list[tuple]]],
) -> str:
    """detail md 전체 본문."""
    parts = [FRONTMATTER, intro, ""]
    for heading, patterns in sections:
        parts.append(f"## {heading}\n")
        for p in patterns:
            parts.append(render_pattern(*p))
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"
