---
scope:
- '*'
always_apply: true
priority: 1
domain: core
verify_with:
- agent-meta-prohibitions-check
- error-patterns-sort-check
patterns_file: .agents/core/error_patterns/patterns.yaml
---

<!-- Language: ko -->

# Error Patterns — 에이전트가 자주 하는 실수

에이전트가 작업을 진행할 때 반복적으로 저지르는 실수들을 기록합니다.
**헤더(본 문서)** = 라우팅·**TOP 4**·**메타 금지 11** normative SSOT (always-on). TOP 5–9·WRONG/CORRECT = `error_patterns/detail/` **lazy-load**. **규범 SSOT**: 편집 도구 → [runtime_edit_tools.md](runtime_edit_tools.md) (tri-runtime) · Cursor 상세 → [routing.md](routing.md) §1 · AGENTS → [AGENTS.md §2](../../AGENTS.md).

---

## 📋 AGENTS.md 헌법 적용 요약

| 원칙 | 이 문서에서의 구현 |
|------|-------------------|
| **1. 규칙 위계** | always_apply: true — 에러 패턴은 최우선 참조, 충돌 시 AGENTS.md §1 우선순위 적용 |
| **2. 사고→단순→표적** | 메타 금지 3~4 — 실패 후 동일 입력 재시도 금지, 2회 실패 시 전략 전환 (단순화) |
| **3. 편집 게이트 4단계** | TOP 1~4 + 메타 금지 1~3, 9 — 읽기→단일매칭→old≠new→재시도1회 전량 포함 |
| **4. 다중 에이전트** | 이 문서의 대상 — Phase 3 검증에서 TOP 1~9 체크리스트 전담 |
| **5. Plan CLI 전용** | 메타 금지 6 — discuss/plan 종료는 사용자 선택(AskQuestion) 없이 마무리 금지 |
| **6. 검증·한글·고유성** | Zero-Leak 보안 금지 패턴, 메타 금지 11 — edit 후 검증 누락 방지 |

### 언제 어떤 문서를 볼지

| 상황 | 먼저 볼 문서 |
| :--- | :--- |
| pytest·빌드·런타임 코드 오류 | [RES_COMMON_ERROR_RESOLUTIONS.md](../../docs/knowledge/RES_COMMON_ERROR_RESOLUTIONS.md) |
| 부분 수정·파일 I/O 실수 (tri-runtime) | [runtime_edit_tools.md](runtime_edit_tools.md), [error_patterns/detail/editing.md](error_patterns/detail/editing.md), [error_patterns/detail/tools.md](error_patterns/detail/tools.md) |
| Blueprint·plan-lint·Task closeout | [workflows/plan.md](../workflows/plan.md), [error_patterns/detail/blueprint.md](error_patterns/detail/blueprint.md) |
| discuss 세션·AskQuestion/`question`(병용)·close 규칙 | [discuss/SKILL.md](../skills/discuss/SKILL.md), [error_patterns/detail/workflow.md](error_patterns/detail/workflow.md) |
| 희귀 1회 사고 (§8~15) | [error_patterns_archive/incidents.md](error_patterns_archive/incidents.md) |

## Quick Reference — TOP 4 (always-on)

1. **읽기 → 전체 쓰기 직행** — 라인 번호가 파일에 기록됨 (메타 금지 1) → [editing §1.1](error_patterns/detail/editing.md)
2. **부분 수정 시 대상 문자열 유일성 미확인** — "Found N matches" 반복 (메타 금지 2) → [editing §1.2](error_patterns/detail/editing.md)
3. **부분 수정 실패 후 같은 old/target 재시도** — 외부 수정을 무시 (메타 금지 3) → [editing §1.3](error_patterns/detail/editing.md)
4. **부분 수정 후 검증 누락** — 성공 응답 후 실제 변경 미검증 (메타 금지 11) → [editing §1.3](error_patterns/detail/editing.md) · [error_patterns.md §11](#11-edit-후-검증-누락)

## TOP 5–9 (lazy — 편집·`just route` 직전)

`just route`가 경로별 `error_patterns/detail/*.md`를 `must_read`에 추가한다. 편집·슬래시·plan 직전 Read.

5. **JSX 부분 수정 누적 실패** — 2회 연속 실패 시 전략 전환 (메타 금지 4) → [editing §1.4](error_patterns/detail/editing.md)
6. **게이트 PASS 전 다음 단계** — plan-lint·route-gate (메타 금지 5) → [blueprint §5.1](error_patterns/detail/blueprint.md)
7. **텍스트 툴 마커 오용** — `[TOOL_REQUEST]`·`<tool_call>` 등 → [workflow §16.2](error_patterns/detail/workflow.md)
8. **워크플로 Read 누락** — [workflow §16.1](error_patterns/detail/workflow.md)
9. **edit 후 검증 누락** — "Edit applied successfully" 반환 후 실제 변경 미검증 (메타 금지 11) → [error_patterns.md §11](#11-edit-후-검증-누락)

## 🚫 메타 금지 11

작업 전·실패 후 선제 지침. **normative SSOT (본 절)** · 편집 도구·old/target 문자열 규칙 → [runtime_edit_tools.md](runtime_edit_tools.md) · Cursor 상세 → [routing.md §1](routing.md). WRONG/CORRECT 예시는 [error_patterns/detail/](error_patterns/detail/) lazy-load.

1. **디스크 SSOT** — 수정·판단 전 디스크 최신본을 읽는다. 읽기 도구 출력(줄 번호 등)을 파일 본문으로 쓰지 않는다.
2. **단일 매칭** — 부분 수정 전 대상 문자열이 파일에 **정확히 1번**인지 확인한다. 여러 번이면 범위를 좁히거나 전략을 바꾼다.
3. **실패 후 동일 입력 금지** — 부분 수정 도구 실패 후 같은 old/target 문자열·같은 전략으로 재시도하지 않는다. 반드시 재읽기 후 진행한다.
4. **2회 실패 → 전략 전환** — 같은 파일·같은 작업에서 편집이 2회 연속 실패하면 부분 수정을 멈추고(예: 구조 파일은 전체 재작성, 범위 축소) 상위 전략으로 바꾼다.
5. **게이트 PASS 전 다음 단계 금지** — plan-lint·route-gate·해당 Verify PASS 전에 구현·Task 완료 처리·다음 워크플로 단계로 넘어가지 않는다.
6. **종료는 선택 필수** — discuss/plan 등 종료·핸드오프는 사용자 선택(AskQuestion/`question` 병용) 없이 마무리하지 않는다.
7. **격리·완전성** — 테스트·mock·공유 저장소는 사용처가 기대하는 export·초기값·cleanup을 맞춘다. «아마 비어 있겠지»로 두지 않는다.
8. **patterns ID 정렬** — `patterns.yaml` SSOT는 ID 숫자 순 유지. `just error-patterns-sort-check`로 검증.
9. **동일 입력 무한 재시도 금지** — **호출 전**: old와 new(또는 Target/Replacement)가 같으면 부분 수정 도구를 호출하지 않는다. **수신 후**: `"No changes to apply"` 류 응답이면 **같은 쌍으로 재호출하지 않는다** → 호스트 읽기 도구로 재확인 → (a) 목표 내용이 이미 있으면 완료·다음 단계, (b) 없으면 old/target·범위·new 중 하나 이상을 바꿔 1회만 재시도. 상세: [runtime_edit_tools.md §2](runtime_edit_tools.md) · [routing.md §1.4·Terminal Response Rule](routing.md) · [editing §1.7](error_patterns/detail/editing.md).
10. **커밋 게이트 실패 시 `--no-verify` 금지** — `commit-gate`(Husky pre-commit 훅)가 실패하면 **반드시 린트/타입 오류를 수정**하고 재시도한다. `git commit --no-verify`로 우회하는 것은 **절대 금지**된다. 예외: 아카이브 워크플로우에서 `scripts/` 이동만 수행한 경우 (이 경우에도 린트 오류 파일은 별도 커밋으로 수정).
11. **부분 수정 후 검증 누락** — 부분 수정 도구가 성공 응답을 반환해도, **반드시 grep/read(또는 런타임 동등 도구)로 실제 변경을 검증**한다. 스테이트 불일치로 미적용된 경우가 있으며, Blueprint의 `or → and` 같은 요구가 코드에 없으면 검증 의미가 사라진다. Verify 명령어(`just discover-dead-verify`, `just plan-lint` 등)를 실행하고, 실패 시 재읽기 후 재시도한다.

---

## 🚫 Zero-Leak (보안 금지 패턴)

- **증상**: 에이전트 응답이나 도구 출력(터미널 캡처 등)에 API 키, 토큰, 비밀번호, `.env` 원문 등이 그대로 노출됨.
- **원인**: `cat`, `grep`, `Read`·`Grep`·`Shell` 등으로 시크릿이 포함된 파일을 읽고 필터링 없이 출력하거나, 명령어 실패 후 에러 로그를 그대로 인용함.
- **WRONG**: 환경변수 설정 파일 내용을 그대로 텍스트로 출력하거나, `echo $API_KEY` 등 비밀값을 터미널에 표시.
- **CORRECT**: 비밀값이 필요하면 사용자에게 안전한 입력 경로(예: 로컬 환경 변수 수동 설정 유도)를 묻고, 쉘 스크립트 등에서 사용할 때는 표준 출력(echo, print)이나 로그에 남기지 않음.

---

## Detail 인덱스 (lazy-load)

`just route <paths>` 시 대상 경로에 맞는 detail이 `must_read`에 자동 추가된다. 편집 직전 Read 필수.

> **`error_patterns/detail/*.md` 주의**: `.cursorignore` 대상이라 호스트 읽기/쓰기 도구가 Permission denied일 수 있다. 이 경우 **shell(`cat`/`rg`)로 본문 확인** 후 편집한다. "확인 불가"로 건너뛰지 않는다.

| Detail | § | 트리거 (경로 패턴) |
| :--- | :--- | :--- |
| [editing.md](error_patterns/detail/editing.md) | §1, §3, §7 | **모든** 편집 경로 · `*.tsx`/`*.jsx` (React §3 포함) |
| [testing.md](error_patterns/detail/testing.md) | §2 | `tests/**`, `*.test.*`, `test_*` |
| [tools.md](error_patterns/detail/tools.md) | §3 | `.agents/**` |
| [blueprint.md](error_patterns/detail/blueprint.md) | §4 | `docs/plans/**` |
| [workflow.md](error_patterns/detail/workflow.md) | §5, §16 | `docs/discussions/**`, `.agents/workflows/**` |

## 부록: 희귀 패턴 (archive)

`occurrence_count` 1회·도메인 특화 사고. frontmatter id는 유지, 상세 본문은 아카이브.

| id | 이름 | 아카이브 |
| :--- | :--- | :--- |
| 8.1 | dependency-injector mixin 상속 실패 | [incidents.md §8](error_patterns_archive/incidents.md) |
| 9.1 | Path.parents[N] repo root 오계산 | [incidents.md §9](error_patterns_archive/incidents.md) |
| 10.1 | plan-lint Status 파싱 충돌 | [incidents.md §10](error_patterns_archive/incidents.md) |
| 11.1 | plan-task-close shell 해석 | [incidents.md §11](error_patterns_archive/incidents.md) |
| 12.1 | DISCUSS dual `---` YAML 파싱 | [incidents.md §12](error_patterns_archive/incidents.md) |
| 13.1 | docs-discuss-lifecycle 오인 | [incidents.md §13](error_patterns_archive/incidents.md) |
| 14.1 | macOS 시스템 Python PATH | [incidents.md §14](error_patterns_archive/incidents.md) |
| 15.1 | MEMORY.md ↔ memory tool 충돌 | [incidents.md §15](error_patterns_archive/incidents.md) |

---
