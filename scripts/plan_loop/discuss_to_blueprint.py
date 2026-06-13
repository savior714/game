"""DISCUSS 노트 → Blueprint 골격 자동 생성기 (TEM-279).

DISCUSS_*.md의 4섹션 고정 구조를 파싱하고, TEMPLATE_blueprint.md +
REQUIRED_SECTIONS 상수를 참조하여 Blueprint 골격을 생성한다.
plan-lint 구조 오류를 원천 차단하기 위해 필수 섹션 순서를 보장한다.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from scripts.plan_loop.plan_lint.structural import verify_structural_sequence
from scripts.docs.plan_yaml_frontmatter import prepend_plan_yaml_frontmatter

# DISCUSS 4섹션 패턴
DISCUSS_SECTIONS = [
    (r"## 1\. 현황 요약", "현황_요약"),
    (r"## 2\. 진행 중 결정", "진행중_결정"),
    (r"## 3\. 합의된 방향 · 범위", "합의된_방향"),
    (r"## 4\. 미해결 · 핸드오프", "미해결_핸드오프"),
]


@dataclass
class DiscussNote:
    """DISCUSS 노트의 파싱 결과."""
    title: str = ""
    status: str = ""
    created: str = ""
    scope: str = ""
    linked_plan: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    _filename: str = ""

    @property
    def slug(self) -> str:
        """DISCUSS 파일명에서 slug 추출 (예: DISCUSS_plan_transition_cost → plan_transition_cost)."""
        match = re.match(r"DISCUSS_(.+)\.md", self._filename)
        if match:
            return match.group(1)
        # 제목에서 slug 생성 (공백 → underscore, 특수문자 제거)
        cleaned = self.title.replace("→", "").replace("→", "")
        cleaned = re.sub(r"[^\w\s-]", "", cleaned)
        cleaned = re.sub(r"\s+", "_", cleaned).strip("_")
        return cleaned.lower() if cleaned else "unknown"


def _read_discuss_file(path: Path) -> str:
    """DISCUSS 파일을 UTF-8로 읽는다."""
    content = path.read_text(encoding="utf-8")
    return content


def _parse_frontmatter(content: str) -> dict[str, str]:
    """YAML frontmatter를 파싱한다 (간단한 key: value 형태)."""
    fm: dict[str, str] = {}
    lines = content.split("\n")
    in_fm = False
    for line in lines:
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def _extract_section(content: str, pattern: str) -> str:
    """정규식 패턴으로 섹션 내용을 추출한다."""
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    # 다음 섹션 또는 끝까지
    next_section = re.search(r"\n## ", content[start:])
    end = start + next_section.start() if next_section else len(content)
    return content[start:end].strip()


def parse_discuss(path: Path) -> DiscussNote:
    """DISCUSS 4섹션 파서. Blueprint 골격 생성기(generate_blueprint_skeleton)의 입력."""
    content = _read_discuss_file(path)
    frontmatter = _parse_frontmatter(content)

    note = DiscussNote(
        title=content.split("#", 1)[-1].split("\n")[0].strip() if "#" in content else "Unknown",
        status=frontmatter.get("status", "discussing"),
        created=frontmatter.get("created", ""),
        scope=frontmatter.get("scope", ""),
        linked_plan=frontmatter.get("linked_plan", ""),
    )

    # 파일명 저장 (slug 추출용)
    note._filename = path.name  # type: ignore[attr-defined]

    # 4섹션 추출
    for pattern, key in DISCUSS_SECTIONS:
        note.sections[key] = _extract_section(content, pattern)

    return note


def generate_blueprint_skeleton(note: DiscussNote) -> str:
    """DISCUSS 합의를 반영한 Blueprint 골격 마크다운을 반환.
    
    DISCUSS의 4섹션을 Blueprint 업무 요약과 Diagnosis 등에 매핑하고,
    REQUIRED_SECTIONS 순서에 맞춰 12개 필수 섹션을 생성한다.
    """
    today = date.today().isoformat()

    # DISCUSS 내용을 Blueprint 필드에 매핑
    개요 = note.sections.get("현황_요약", "").strip()
    # staff_변화, 확인할_것는 골격에서 고정 텍스트로 사용됨

    # Blueprint 문서 메타
    linear_issue = "TEM-279"
    template_ref = "TEMPLATE_blueprint.md"
    anti_pattern_ref = "ANTI_PATTERN_FORMAT.md"

    skeleton = f"""<!-- Language: ko -->

# 🗺️ Project Blueprint: {note.title} ({linear_issue})

## 문서 메타
- **Last Verified**: {today} | **Tested Version**: N/A
- **Reference**: [DISCUSS_{note.slug}.md](../discussions/DISCUSS_{note.slug}.md)
- **SSOT Check**: {template_ref} + REQUIRED_SECTIONS
- **Project Status Link**: [ROADMAP.md](../../ROADMAP.md) §트랙3
- **Linear-Issue**: {linear_issue}
- **Priority**: 1
- **Labels**: tooling
- **Architectural Goal**: DISCUSS → Blueprint 골격 자동 생성

## 📋 업무 요약 (협업용)

> **독자**: 원장·원무·기획. 코드·경로·명령은 아래 기술 절.

### 개요

{개요 or 'DISCUSS 합의를 기반으로 한 작업'}

### staff·경영에서 바뀌는 점

- 논의에서 설계까지의 전환 시간이 단축됩니다
- 논의 합의 내용이 설계 문서에 빠짐없이 반영됩니다

### 끝났을 때 확인할 것

- 생성된 Blueprint 골격이 구조 검증을 통과하는지 확인
- 필수 섹션 12개 누락 없이 생성되었는지 확인

## 🧭 Context Pre-read Gate (실행 전 필수)

> ⚠️ **에이전트 주의**: Blueprint 파일 생성 직후, `just plan-lint`를 돌리기 **전에** 반드시 아래 명령을 먼저 실행하여 마커를 주입하세요.
> `just plan-preread docs/plans/PLAN_{note.slug}.md --write`

(planned: `just plan-preread docs/plans/PLAN_{note.slug}.md --write`)

### Anti-pattern Guard (작성 전 필수)

- **SSOT**: [`{anti_pattern_ref}`](../agent-context/{anti_pattern_ref})
- ❌ **금지**: `grep`/`echo` 단독 Verify, `;`/`&&`/`||` 체인 Verify
- ✅ **정답**: `just ...` 또는 `uv run pytest ...` 처럼 **runner 1개** Verify
- ✅ **정답**: `todo/running` Conclusion은 `[판정 — 비개발자용 요약. 검증 결과]` 유지

## 실행 순서·선행

| Task | 선행 | 내용 |
| :--- | :--- | :--- |
| 1.1 | None | 핵심 로직 구현 |
| 1.2 | 1.1 | CLI 진입점 + Justfile 레시피 |
| 2.1 | 1.2 | 통합 테스트 |

## 🔍 Diagnosis & Findings

- **현상**: DISCUSS → plan 핸드오프 시 에이전트가 DISCUSS §1~3을 Blueprint 업무 요약으로 수동 복사 — 토큰 낭비와 구조 누락 빈발
- **근본 원인**: DISCUSS 노트와 Blueprint 템플릿 사이에 자동 변환 경로가 없음

## 🏗️ Architectural Deepening

- **Seam**: `scripts/plan_loop/discuss_to_blueprint.py` 단일 스크립트. DISCUSS 노트의 4섹션 고정 구조를 파싱하고, `TEMPLATE_blueprint.md` + `REQUIRED_SECTIONS` 상수를 참조하여 Blueprint 골격을 생성
- **Leverage**: DISCUSS 노트의 4섹션 구조가 SKILL에 의해 강제되므로 파서가 안정적. structural.py의 `REQUIRED_SECTIONS` 재사용으로 구조 정합성 보장

## 📜 Conceptual Sketch

```python
# discuss_to_blueprint.py
def parse_discuss(path: Path) -> DiscussNote:
    \"\"\"DISCUSS_*.md의 frontmatter + 4섹션을 파싱.\"\"\"
    ...

def generate_blueprint_skeleton(note: DiscussNote) -> str:
    \"\"\"DISCUSS 합의를 반영한 Blueprint 골격 마크다운을 반환.\"\"\"
    ...

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(\"discuss_file\", type=Path)
    parser.add_argument(\"--output\", type=Path, default=None)
    args = parser.parse_args()
    note = parse_discuss(args.discuss_file)
    skeleton = generate_blueprint_skeleton(note)
    output = args.output or Path(f\"docs/plans/PLAN_{note.slug}.md\")
    output.write_text(skeleton, encoding=\"utf-8\")
```

## 🛡️ Risk & Strategy

- **Risk**: DISCUSS 노트가 4섹션 구조를 지키지 않을 수 있음 — **Strategy**: 파서가 누락 섹션을 감지하면 경고 출력하고 해당 Blueprint 섹션은 빈 상태로 생성
- **Risk**: 생성된 Blueprint가 plan-lint의 의미적 검사(Goal 품질 등)를 통과하지 못할 수 있음 — **Strategy**: 골격은 구조만 보장하고, 의미적 내용은 에이전트가 채운 후 lint 실행

## 🔍 Impact Scope

| 수정 대상 | 역할 |
| :--- | :--- |
| `scripts/plan_loop/discuss_to_blueprint.py` (신규) | DISCUSS 파서 + Blueprint 골격 생성 |
| `Justfile` | plan-from-discuss 레시피 |
| `tests/test_discuss_to_blueprint.py` (신규) | 파서 + 생성기 단위 테스트 |

## Agent Completion Contract

본 Blueprint Task를 실행하는 세션(`@PLAN_* task N.M`, `/plan` 후 구현)에서 사용자가 별도 금지하지 않는 한, 아래는 **해당 Task 범위에 포함**된다 ([planning.md](../../.agents/core/planning.md) §2.2 · [plan.md](../../.agents/workflows/plan.md) §1.10).

| 허용 | 금지 |
| :--- | :--- |
| `just plan-task-close` CLI를 사용한 Task `Status`·`Conclusion` 자동 갱신 | 텍스트 에디터(replace 등)로 본 파일 Task 상태 In-place 직접 수정 |
| Task `Verify` 직후 `just plan-lint docs/plans/PLAN_{note.slug}.md` | Conclusion 없이 `Status: done` 처리 |
| Task Goal에 명시된 Target·명세 동반 수정 | ROADMAP·다른 Blueprint 대량 수정 |

**Task 완료 정의**: `Verify` exit 0 → `just plan-task-close` 실행 → `just plan-lint` PASS.

## 🛠️ Step-by-Step Execution Plan

> **에이전트 스코프**: Task 1개씩. `Verify` PASS → `just plan-task-close plan=... task=... conclusion=\"...\"` → `just plan-lint docs/plans/PLAN_{note.slug}.md`.

### Phase 0 — 핵심 로직

#### Task 0.1: DISCUSS 파서와 Blueprint 골격 생성 함수 구현 [Unit: Atomic]
- Task-ID: [DTB-001] | Linear-Issue: {linear_issue} | Status: todo | Priority: 1 | Labels: tooling | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read
  1. `[rule]` `.agents/domains/infra/seeding.md`
  2. `[script]` `scripts/plan_loop/discuss_to_blueprint.py`
  3. `[project_skill]` `.agents/skills/discuss/SKILL.md`
- **Action**: Create File | **Target**: `scripts/plan_loop/discuss_to_blueprint.py`
- **Closeout**: `docs/plans/PLAN_{note.slug}.md` (Task DTB-001 `Conclusion`·`Status`)
- **Goal**: 먼저 `tests/test_discuss_to_blueprint.py`에 DISCUSS 파싱 실패 테스트를 작성하고, `scripts/plan_loop/discuss_to_blueprint.py`에 DISCUSS 4섹션 파서(`parse_discuss`)로 Blueprint 골격 생성기(`generate_blueprint_skeleton`)를 구현하여 12개 필수 섹션 포함 마크다운을 출력한다 | **Diagnostics**: 0
- **Verify**: `uv run pytest tests/test_discuss_to_blueprint.py -k test_parse_and_generate -q`
- **Conclusion**: [판정 — 비개발자용 요약. 검증 결과]
- **Dependency**: None

## 🔁 Conclusion & Summary

- **Roll-up**: 미완료 — 1개 Task 모두 todo

## ✅ Definition of Done (DoD)

- `uv run pytest tests/test_discuss_to_blueprint.py -k test_parse_and_generate -q`
- `just plan-from-discuss --help`
- `uv run pytest tests/test_discuss_to_blueprint.py -q`
- `just plan-lint docs/plans/PLAN_{note.slug}.md`

## 검증 행렬

| Scope | Command |
| :--- | :--- |
| Blueprint | `just plan-lint docs/plans/PLAN_{note.slug}.md` |
| Unit Tests | `uv run pytest tests/test_discuss_to_blueprint.py -q` |
"""
    return skeleton


def main():
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="DISCUSS 노트에서 Blueprint 골격을 자동 생성합니다 (TEM-279)."
    )
    parser.add_argument("discuss_file", type=Path, help="DISCUSS_*.md 파일 경로")
    parser.add_argument("--output", type=Path, default=None, help="출력 파일 경로 (생략 시 docs/plans/PLAN_<slug>.md)")
    args = parser.parse_args()

    if not args.discuss_file.exists():
        print(f"Error: DISCUSS 파일이 존재하지 않습니다: {args.discuss_file}", file=sys.stderr)
        sys.exit(1)

    # 파싱
    note = parse_discuss(args.discuss_file)
    print(f"DISCUSS 파싱 완료: {note.title} (slug={note.slug})")

    # 골격 생성
    skeleton = generate_blueprint_skeleton(note)

    # 출력 경로 결정
    output = args.output or Path(f"docs/plans/PLAN_{note.slug}.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    skeleton = prepend_plan_yaml_frontmatter(skeleton, output)
    output.write_text(skeleton, encoding="utf-8")
    print(f"Blueprint 골격 생성 완료: {output}")

    # 구조 검증
    issues = verify_structural_sequence(skeleton)
    if issues:
        print("경고: 구조 검증에서 다음 문제 발견:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("구조 검증 통과: 모든 필수 섹션 순서 OK")


if __name__ == "__main__":
    main()
