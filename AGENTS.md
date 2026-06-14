# AGENTS.md — Unified Execution Constitution

에이전트 **헌법 요약**입니다. 우선순위·게이트·레지스트리 진입점만 둡니다. 표·긴 스킬 목록은 레지스트리 파일로 위임합니다.

---

## 0. Priority / Rule Precedence

우선순위는 아래와 같습니다.

1. `PROJECT_RULES.md`
2. 본 문서 (`AGENTS.md`)
3. `.agents/core/*.md`
4. `.agents/domains/**/*.md`
5. 기타 명세 및 가이드라인

충돌 시 위 순서를 따르며, 불명확하면 질문합니다.

---

## 1. Core Operating Principles

normative SSOT: [.agents/core/principles.md](.agents/core/principles.md)

- **Policy**: [PROJECT_RULES.md §3](PROJECT_RULES.md)
- **Think Before Coding · Quick Pick**: [principles.md §1.1](.agents/core/principles.md#11-think-before-coding)
- **Simplicity · Surgical · Goal-Driven**: [principles.md §1.2–§1.4](.agents/core/principles.md#12-simplicity-first)
- **Bug Fixes**: [/diagnose](.agents/workflows/diagnose.md) · [/investigate](.agents/workflows/investigate.md)
- **Merge & Review**: [/review](.agents/skills/review/SKILL.md)
- **Execution Rules**: [execution.md §2](.agents/core/execution.md)
- **Commit Gate Failure**: [error_patterns.md §10](.agents/core/error_patterns.md#10-커밋-게이트-실패시--no-verify-금지) — `--no-verify` 우회 절대 금지, 반드시 오류 수정 후 재시도
- **Edit Tool Schema**: [routing.md §1.1](.agents/core/routing.md#11-file-edit-tool-schema-편집-도구-ssot) (Cursor) · Tri-Runtime: [runtime_edit_tools.md](.agents/core/runtime_edit_tools.md) (Cursor · OpenCode · Antigravity)
- **Workaround Accountability**: [principles.md §1.6](.agents/core/principles.md#16-workaround-accountability--close-turn-reflection)
- **Code Quality Lifecycle** (설계→구현→리뷰→테스트): [code_quality_lifecycle.md](.agents/core/code_quality_lifecycle.md)
- **Self-Evolution**: 세션 중 반복된 실패·도구 호출 오류·비효율적인 패턴을 감지하면 사용자에게 개선 사항을 제안. 제안은 MEMORY.md 또는 별도 논의 노트에 기록하고, 승인 시 AGENTS.md·프로젝트 규칙에 반영

---

## 2. Execution Gates (pointer)

**메타 금지 11** normative SSOT: [error_patterns.md#메타-금지-11](.agents/core/error_patterns.md#메타-금지-11) (`always_apply`).

### 2.1 Editing / Routing

**규범 SSOT**: [routing.md](.agents/core/routing.md) §1 · §2. **WRONG/CORRECT 예시**: [error_patterns §1](.agents/core/error_patterns.md#1-파일-편집-실수) lazy-load.

**부분 수정 호출 전 (always-on, tri-runtime)**: 호스트 **읽기 도구**로 디스크 최신본 확보 → 대상 문자열이 파일에 **정확히 1번**인지 확인 → **old ≠ new** (같으면 호출 금지). `"No changes to apply"` 수신 시 동일 쌍 재호출 금지 → 재읽기 → 목표 내용 있으면 완료, 없으면 old/범위/new 변경 후 1회만 재시도. **도구 이름·키**: [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md) (Cursor `StrReplace`/`old_string` · OpenCode `edit`/`oldString` · Antigravity `replace_file_content`/`TargetContent`). Terminal Response: [routing.md](.agents/core/routing.md) (Cursor) · [opencode_tools.md §edit](.agents/core/opencode_tools.md) (OpenCode).

### 2.2 Multi-Agent Orchestration (병렬 구현·검증 패턴)

복수 파일 수정이 필요한 복합 작업은 단일 에이전트가 순차적으로 처리하지 말고, 아래 5단계 페이즈로 분할 실행한다.

**핵심 원칙**: 각 페이즈는 **상태가 독립적인 fresh subagent**를 사용한다. 이전 페이즈의 컨텍스트·결과를 `task` prompt에 명시적으로 전달하되, subagent 간 내부 상태는 공유되지 않는다.

```
Phase 1: 분석·계획 (Main Agent)
  ↓
Phase 2: 구현 (N개 Subagent 병렬, fresh)
  ↓
Phase 3: 검증 (N개 Subagent 병렬, fresh — 구현 페이즈와 별도 인스턴스)
  ↓
Phase 4: 수정 (M개 Subagent 병렬, M≤N, fresh)
  ↓
Phase 5: 최종 감사 (Main Agent)
```

#### Phase 1 — 분석·계획 (Main Agent 전담)

- 작업 범위 분석 → 수정 대상 파일·영역 식별
- N(구현 에이전트 수) 결정: 서로 독립적인 파일 그룹마다 1개
- 각 태스크의 **범위·목표·성공 기준**을 명확히 정의
- 의존 관계가 없는 태스크는 병렬 실행 가능하도록 분리

#### Phase 2 — 구현 (N개 Subagent 병렬 실행)

- 각 subagent에 **독립적인 파일 범위** 할당 (중복 금지)
- `task` 도구로 동시 호출 (동일 메시지 내 복수 호출)
- subagent별 지시사항:
  - `subagent_type`: `general` (구현용)
  - 명시된 파일 범위만 수정, 타 영역 터치 금지
  - 수정 후 `git diff` 결과 요약 포함

**prompt 템플릿**:
```
작업: [파일 경로/범위] 수정
목표: [구체적 목표]
성공 기준: [검증 가능한 기준]
제약: [파일 범위 외 터치 금지, AGENTS.md §4.1–§4.2 준수 등]
출력: 수정 후 `git diff --stat` + 주요 변경 3줄 요약
```

#### Phase 3 — 검증 (N개 Subagent 병렬 실행)

- **구현 subagent와 동일한 수**의 audit subagent 배치 (별도 fresh 인스턴스)
- 각 audit subagent는 **자신의 구현 결과를 전담 검증** (다른 페이즈의 컨텍스트 공유 금지)
- subagent별 지시사항:
  - `subagent_type`: `general` (검증용)
  - 구현 subagent의 `git diff`만 검토 (전체 코드베이스 아님)
  - 집중 체크리스트:
    - **한글/인코딩**: `edit` 도구 실패 패턴 재발 여부 ([AGENTS.md §4.1](#41-partial-edit-tool--한글-콘텐츠-limitation-tri-runtime))
    - **중복 메시지**: 정적 HTML/JS의 `querySelector` 고유성 ([AGENTS.md §4.2](#42-test--메시지-전역-고유성))
    - **Context Route Gate**: `just route` 절차 준수 여부 ([routing.md §2](.agents/core/routing.md#2-context-route-gate-편집-전-강제ide-공통))
    - **Partial Edit 규칙**: `oldString ≠ newString`, 단일 매칭 ([routing.md §1.2](.agents/core/routing.md#12-patch-preconditions-메타-금지12))
  -发现问题 → `git diff` 기반 구체 근거 + 라인 번호 제시

**prompt 템플릿**:
```
검증 대상: [파일 경로/범위] — [구현 subagent의 git diff 결과]
체크리스트:
  1. 한글/인코딩: edit 도구 실패 없음, UTF-8 정상
  2. 메시지 고유성: querySelector 중복 텍스트 없음
  3. Route Gate: just route 절차 준수
  4. Partial Edit: oldString ≠ newString, 단일 매칭
결과: issue 있으면 파일:라인 + 근거 제시. clean이면 "PASS"만 출력
```

#### Phase 4 — 수정 (M개 Subagent 병렬, M≤N)

- Phase 3에서 발견된 issue만 수정
- 같은 파일에 issue가 여러 개면 **1개 subagent가 전담**
- 수정 후 `git diff` 결과 포함

**prompt 템플릿**:
```
수정 대상: [파일 경로] — Phase 3 issue: [issue 목록]
지시: 아래 issue만 수정. unrelated 변경 금지.
  - [issue 1: 파일:라인 + 설명]
  - [issue 2: 파일:라인 + 설명]
출력: 수정 후 `git diff` + 변경 요약
```

#### Phase 5 — 최종 감사 (Main Agent 전담)

- 전체 `git diff` 검토
- lint/test/verify 실행 (`just lint`, `pytest` 등)
- 모든 subagent 결과 요약 → 완료 선언

#### 실행 규칙

- **동시 호출**: Phase 2/3의 subagent는 **동일 메시지 내 복수 `task` 호출**로 병렬 실행
- **결과 대기**: 모든 subagent 완료 전 다음 Phase 시작 금지
- **고립 범위**: 구현 subagent 간 파일 중복 금지 (충돌 방지)
- **실패 시**: 해당 subagent 태스크 `Status: failed` + 원인 기록 → Phase 4에서 재시도 1회만
- **스케일링**: 파일 수 ≤ 5면 N=2~3, 파일 수 > 5면 N=4~5로 분할 (과도한 병렬화 금지)
- **fresh 인스턴스 강제**: Phase 3 audit subagent는 Phase 2 구현 subagent와 **다른 세션 컨텍스트**. 동일한 task_id 재사용 금지

#### 언제 사용할지

| 작업 규모 | 패턴 적용 |
|---|---|
| 단일 파일 수정 | Phase 1 → Main Agent 구현 (단일 실행) |
| 2~3개 파일, 독립적 | Phase 1 → Phase 2(N=2~3) → Phase 5 |
| 4개+ 파일 또는 복잡도 높음 | 전체 5단계 페이즈 적용 |
| 버그 수정 | [/diagnose](.agents/workflows/diagnose.md) 우선 → 필요시 이 패턴 |

#### 예시: 3개 과목 UI 동시 리팩토링

```
Main Agent → Phase 1: domains/math/, domains/english/, domains/korean/ 식별

task(description="Refactor math UI", subagent_type="general",
  prompt="작업: domains/math/ 내 HTML/JS/CSS 리팩토링\n목표: UI 일관성 개선, 접근성 준수\n성공 기준: lint PASS, querySelector 중복 없음\n출력: git diff --stat + 주요 변경 3줄")

task(description="Refactor english UI", subagent_type="general",
  prompt="작업: domains/english/ 내 HTML/JS/CSS 리팩토링\n목표: UI 일관성 개선, 접근성 준수\n성공 기준: lint PASS, querySelector 중복 없음\n출력: git diff --stat + 주요 변경 3줄")

task(description="Refactor korean UI", subagent_type="general",
  prompt="작업: domains/korean/ 내 HTML/JS/CSS 리팩토링\n목표: UI 일관성 개선, 접근성 준수\n성공 기준: lint PASS, querySelector 중복 없음\n출력: git diff --stat + 주요 변경 3줄")

→ (3개 subagent 병렬 완료 대기)

task(description="Audit math UI", subagent_type="general",
  prompt="검증 대상: domains/math/ — [math subagent의 git diff]\n체크리스트: 1. 한글 인코딩 2. querySelector 고유성 3. Route Gate 4. Partial Edit 규칙\n결과: issue 있으면 파일:라인 + 근거. clean이면 PASS")

task(description="Audit english UI", subagent_type="general",
  prompt="검증 대상: domains/english/ — [english subagent의 git diff]\n체크리스트:同上\n결과: issue 있으면 파일:라인 + 근거. clean이면 PASS")

task(description="Audit korean UI", subagent_type="general",
  prompt="검증 대상: domains/korean/ — [korean subagent의 git diff]\n체크리스트:同上\n결과: issue 있으면 파일:라인 + 근거. clean이면 PASS")

→ (3개 audit subagent 병렬 완료 대기)

Main Agent → Phase 5: 전체 diff 검토 + lint/test
```

---

### 2.3 Plan / Blueprint

- **Plan First**: 복합 작업은 `just plan-lint` PASS 전 구현 착수 금지 — [PROJECT_RULES.md §3](PROJECT_RULES.md) · [planning.md](.agents/core/planning.md).
- **Task closeout**: Blueprint Task `Status`/`Conclusion`은 **`just plan-task-close` CLI만** — 에디터 직접 수정 **절대 금지** — [plan.md §1.10](.agents/workflows/plan.md) · [error_patterns/detail/blueprint.md §5.6](.agents/core/error_patterns/detail/blueprint.md#56-task-statusconclusion-%EC%97%90%EB%94%94%ED%84%B0-%EC%A7%81%EC%A0%9D-%EC%88%98%EC%A0%95).
- **DoD 재귀 금지**: DoD 섹션에 `just plan-close`를 verify 명령어로 포함하지 않음 — `plan_close_gate.py`가 이를 추출해 자기 자신을 호출하는 재귀 타임아웃을 유발함 — [error_patterns/detail/blueprint.md §5.7](.agents/core/error_patterns/detail/blueprint.md#57-dod%EC%97%90-just-plan-close-%ED%8F%B0%EB%A6%AC%EB%A7%8C-%ED%8F%B0%EB%A6%AC%EB%A7%88%EC%9D%B4%EC%8A%A4%ED%86%B5).
- **Archive**: `docs/plans/` 파일 이동 시 **반드시** [`.agents/workflows/archive.md`](.agents/workflows/archive.md) 먼저 Read → `scripts/archive_plans.py` 실행 — 수동 복사/삭제 **절대 금지** — [archive.md §실행 절차](.agents/workflows/archive.md#%EC%8B%A4%ED%96%89-%EC%A0%80%EC%B2%9C).
- 상세: [planning.md](.agents/core/planning.md) · [workflows/plan.md](.agents/workflows/plan.md) · [archive.md](.agents/workflows/archive.md).

---

## 3. Dynamic Rules & Loading

**세션 시작**: `PROJECT_RULES.md` + [MEMORY.md](docs/agent-context/memory/MEMORY.md) 인덱스. **lazy** (편집·route 직전): [LOAD_ORDER.md](.agents/registry/LOAD_ORDER.md) Phase 2 · [CONTEXT_ROUTING.md](.agents/registry/CONTEXT_ROUTING.md) · `ROADMAP.md` (plan·roadmap·discuss).

편집 직전: `just route <paths> --json --write-manifest` → `must_read` Read → `just route-read` → `just route-gate-check`.

---

## 4. Verification

검증 수준·게이트: [verification.md](.agents/core/verification.md) — 세션 종료 `just lint-turn-end`. 시점별 품질 체크: [code_quality_lifecycle.md](.agents/core/code_quality_lifecycle.md).

### 4.1 Partial Edit Tool — 한글 콘텐츠 제한 (tri-runtime)

호스트 **부분 수정 도구**(Cursor `StrReplace`, OpenCode `edit`, Antigravity `replace_file_content` 등 — [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md))는 ASCII-only JSON 파싱에 최적화됨. 한글/특수문자 본문을 그대로 넣으면 **실패**할 수 있음 (`JSON parsing failed: Property name must be a string literal`).

**규칙**:
- 영문/코드 변경 → 세션에 노출된 **부분 수정 도구** 사용 (런타임별 이름·키는 [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md))
- 한글/특수문자 대량 → [runtime_edit_tools.md §4](.agents/core/runtime_edit_tools.md) 터미널 우회
- 한글 포함 대량 콘텐츠 → `bash`/`Shell` + `cat > file << 'EOF'` (또는 OpenCode `bash`, Antigravity `run_command`)
- `sed -i ''` (macOS)는 한글과 함께 사용하면 이스케이프 오류 발생 → `python3 -c` 또는 `cat << 'EOF'`로 대체
- MCP `repo_patch` 노출 시: [SPEC_TECH_repo_mcp_tools.md](docs/specs/technical/SPEC_TECH_repo_mcp_tools.md) (`old_text`/`new_text` snake_case) — 선택, tri-runtime 네이티브와 병행

### 4.2 Test — 메시지 전역 고유성

정적 HTML/JS 페이지에서 `document.querySelector()` / `getByText()`는 **단일 요소만** 찾음. 중복 텍스트가 있으면 오류.

**규칙**:
- 테스트 message는 고유 식별자 포함 (`"적정"` X → `"수학 3학년 1단원 정답"` O)
- 중복 텍스트가 있으면 `querySelectorAll()` + 인덱스 또는 `data-testid` 사용 고려

### 4.3 Plan — closeout 실행 순서

`just plan-close`는 다음 순서를 **반드시** 따름.

```bash
just verify               # 1. 검증 스크립트 실행
just plan-close           # 2. plan close gate (실제 justfile 레시피만 사용)
```

**규칙**:
- DoD에 명시된 `just <recipe>`는 실제 justfile에 존재하는지 사전 확인 (`just --list`로 검증)
- 존재하지 않으면 stub 또는 실제 검증 스크립트로 교체

### 4.4 Plan — Conclusion 플레이스홀더 금지

`just plan-lint`는 각 Task의 `Conclusion` 필드를 검증.

**규칙**:
- Conclusion은 최소 **25자 이상**
- 실제 검증 결과 포함 (파일명, 테스트 수, 명령어 결과)
- 플레이스홀더 문자열 절대 남기지 않음:
  - `[판정 — 비개발자용 요약. 검증 결과]` X
  - `[완료 시 기입]` X
  - `Task 9.9에서 선행 Task 결과를 근거로 작성한다.` X
- 예시: `SPEC_ui_billing.md에 청구 준비 점검 패널 요구사항 추가 완료. just docs-ssot-headers PASS.`

### 4.5 Justfile — DoD 레시피 실존 검증

PLAN 파일의 DoD에 명시된 `just <recipe>`는 실제 justfile에 존재해야 함.

**규칙**:
- PLAN 작성 시 `just --list`로 레시피 실존 확인
- 검증 스크립트가 `--check` 플래그를 지원하지 않으면 stub 또는 별도 검증 로직 사용

---

## 5. Reference Index

| Purpose | SSOT |
|---|---|
| Project overview | `README.md` |
| Execution protocol | `AGENTS.md` |
| Project policy | `PROJECT_RULES.md` |
| Requirements contract | `tests/` |
| Session memory | `docs/agent-context/memory/MEMORY.md` |
| Rule registry | `.agents/registry/RULE_INDEX.md` |
| Space Explorer spec | `docs/SPACE_EXPLORER_PLAN.md` |

에이전트 규칙 SSOT는 `PROJECT_RULES.md`, `.agents/core/` 및 `AGENTS.md`입니다.

중복 방지: `.cursor/rules/` 미사용. **`.cursor/commands/*.md`는 workflow pointer만** (본문 SSOT: `.agents/workflows/`). 슬래시·키워드 카탈로그: [WORKFLOW_AND_SKILL_INDEX.md](.agents/registry/WORKFLOW_AND_SKILL_INDEX.md).
