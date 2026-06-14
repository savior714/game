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

---

## 2. Execution Gates (pointer)

**메타 금지 11** normative SSOT: [error_patterns.md#메타-금지-11](.agents/core/error_patterns.md#메타-금지-11) (`always_apply`).

### 2.1 Editing / Routing

**규범 SSOT**: [routing.md](.agents/core/routing.md) §1 · §2. **WRONG/CORRECT 예시**: [error_patterns §1](.agents/core/error_patterns.md#1-파일-편집-실수) lazy-load.

**부분 수정 호출 전 (always-on, tri-runtime)**: 호스트 **읽기 도구**로 디스크 최신본 확보 → 대상 문자열이 파일에 **정확히 1번**인지 확인 → **old ≠ new** (같으면 호출 금지). `"No changes to apply"` 수신 시 동일 쌍 재호출 금지 → 재읽기 → 목표 내용 있으면 완료, 없으면 old/범위/new 변경 후 1회만 재시도. **도구 이름·키**: [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md) (Cursor `StrReplace`/`old_string` · OpenCode `edit`/`oldString` · Antigravity `replace_file_content`/`TargetContent`). Terminal Response: [routing.md](.agents/core/routing.md) (Cursor) · [opencode_tools.md §edit](.agents/core/opencode_tools.md) (OpenCode).

### 2.2 Plan / Blueprint

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
