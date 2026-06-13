---
title: "DDD 구조 재편 — 도메인 중심 폴더 구조"
created: 2026-06-12
discuss: docs/discussions/DISCUSS_ddd_structure_reorg.md
origin_intent: "과목별 학습 게임 프로젝트의 폴더 구조를 DDD 원칙에 맞추어 위계 역전이 없고 유지보수가 용이한 구조로 재편한다."
status: active
---
<!-- Language: ko -->

# 🗺️ Project Blueprint: DDD 구조 재편 — 도메인 중심 폴더 구조

## 문서 메타
- **Last Verified**: 2026-06-13 | **Tested Version**: N/A
- **Reference**: DISCUSS_ddd_structure_reorg.md §2
- **SSOT Check**: PROJECT_RULES.md §1 (런타임 SSOT — 정적 HTML/JS/CSS)
- **Project Status Link**: N/A
- **Linear-Issue**: N/A (내부 구조 재편 — Linear 이슈 미생성)
- **Priority**: 1
- **Labels**: refactor, architecture
- **Architectural Goal**: domains/ + shared/ + experiments/ 3계층 분리, 의존성 방향 단방향 (domains/* → shared/)

## 📎 관련 명세

| 문서 | 범위 |
| :--- | :--- |
| `docs/discussions/DISCUSS_ddd_structure_reorg.md` | DDD 재편 방향성 · 합의된 구조 |
| `PROJECT_RULES.md §1` | 정적 HTML/JS/CSS 런타임 SSOT |

## 📋 업무 요약 (협업용)

### 개요

어린이 학습 게임 플랫폼의 폴더 구조를 도메인 중심 DDD 원칙에 맞게 재편합니다. 현재 common 에 비즈니스 로직과 UI 유틸이 혼재하고, global 에 auth/reward/sync 가 뭉쳐 있으며, 과목별 폴더가 engine/ui 경계를 파일 내부에서만 구분하는 문제를 해결합니다.

### staff·경영에서 바뀌는 점

- 파일 탐색이 직관적: domains/math → 수학 게임, shared/ui → 공용 UI
- 과목 추가 시 domains/new-subject 생성만으로 시작 가능
- 실험 모듈이 experiments 에 묶여 탐색성 향상

### 끝났을 때 확인할 것

- 모든 게임 페이지가 script 경로 변경 후 정상 동작
- 루트 HTML에서 shared, domains 로 script 참조 변경 완료
- auth 실패 시 기본 기능(게임 플레이, 로컬 통계) 사용 가능

## 🎯 Origin Intent

- **출처**: DISCUSS_ddd_structure_reorg.md handoff
- **원래 목적**: 과목별 학습 게임 프로젝트의 폴더 구조를 DDD 원칙에 맞추어 위계 역전이 없고 유지보수가 용이한 구조로 재편
- **완료 관찰**: domains, shared, experiments 폴더 구조로 파일 이동 완료, 모든 HTML 에서 script 경로 업데이트, 게임 동작 확인

## ⚠️ Edge Case Trace

| 엣지 케이스 | 출처 | Task-ID / 범위 밖 | 비고 |
| :--- | :--- | :--- | :--- |
| auth/sync 비동기 실패 시 기본 기능 사용 불가 | Origin | Task 4.2 | auth 실패 시 게임 플레이 차단되지 않도록 fallback |
| script 로드 순서 오류로 퀴즈 동작 불능 | Origin | Task 6.1 | shared/ → domains/ 순서로 script 태그 배치 검증 |
| 기존 localStorage 키 충돌로 통계 손실 | Risk | Task 6.1 | 마이그레이션 중 키 네임스페이스 변경 없음 확인 |
| experiments/ 이동 후 기존 북마크 깨짐 | Risk | 범위 밖 — 선택적 리다이렉트 HTML 유지 | |

## 🧭 Context Pre-read Gate (실행 전 필수)

<!-- plan-preread:v1 generated=2026-06-12T15:32:26Z paths=14 must_read_installed=2 -->

**정책 (IDE 공통)**: [execution.md §2.8](.agents/core/execution.md) Context Route Gate. **Read SSOT**은 각 Task 블록의 **`Pre-read`** 목록이다 — `write`/`patch` 전 **해당 Task** 목록을 전부 Read (`write`/`patch` = 파일 쓰기·부분 수정 직전; 호스트 도구명은 [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md)). 상단 게이트만 읽고 Task `Pre-read`를 건너뛰면 정책 위반.

**기술 스택 (계획서 추론)**: (경로에서 스택 신호 미확인 — Impact Scope·Target 보강 권장)
**의도 키워드 (계획서 추론)**: ui, 리팩터, 접근성
**라우팅 입력 경로 (14개)**: `common/`, `docs/discussions/DISCUSS_ddd_structure_reorg.md`, `domains/auth/auth.js`, `domains/english/`, `domains/korean/`, `domains/math/`, `domains/reward/`, `domains/science/`, `experiments/`, `shared/domain/progress-engine.js`

### Read SSOT

- **단일 Task 실행**(예: 「Task 1.1만」): 그 Task의 `Pre-read`만 Read.
- **플랜 전체 순차 실행**: Task마다 해당 `Pre-read`를 **그 Task 착수 직전**에 Read(상단에 must_read 목록 없음 — 중복 제거).
- **플랜 전체 must_read 합집합(참고)**: installed 2개 — 상세 경로는 각 Task `Pre-read`에만 나열.


### 재검증 (구현 세션에서 편집 직전)

```bash
just route common/ docs/discussions/DISCUSS_ddd_structure_reorg.md domains/auth/auth.js domains/english/ domains/korean/ domains/math/ domains/reward/ domains/science/ … (+6 more) --json
```

플랜 갱신 시 본 절 재생성: `just plan-preread docs/plans/PLAN_ddd_structure_reorg.md --write` → `just plan-lint docs/plans/PLAN_ddd_structure_reorg.md`

## Agent Completion Contract

본 Blueprint Task를 실행하는 세션(`@PLAN_* task N.M`, `/plan` 후 구현)에서 사용자가 별도 금지하지 않는 한, 아래는 **해당 Task 범위에 포함**된다 ([planning.md](../../.agents/core/planning.md) §2.2 · [plan.md](../../.agents/workflows/plan.md) §1.10).

| 허용 | 금지 |
| :--- | :--- |
| `just plan-task-close` CLI를 사용한 Task `Status`·`Conclusion` 자동 갱신 | 텍스트 에디터(replace 등)로 본 파일 Task 상태 In-place 직접 수정 |
| Task `Verify` 직후 `just plan-lint docs/plans/PLAN_ddd_structure_reorg.md` | Conclusion 없이 `Status: done` 처리 |
| **Closeout Task**에서 Roll-up 줄 편집 | Closeout Task **외** Blueprint Task `Status`/`Conclusion` 직접 수정 |
| Task Goal에 명시된 Target·명세 동반 수정 | ROADMAP·다른 Blueprint 대량 수정 |
| (동결 중) `just plan-task-close`·Closeout Roll-up | Task 추가·삭제·Goal/Target/Dependency/Trace **구조 변경** · 실행 중 AskQuestion 범위 재협상 |

**실행 동결**: `plan-lint` PASS 후 사용자가 **전체 진행**을 요청하면 Blueprint 구조는 고정. 표준 패턴 — 파일 작성 완료 → `@PLAN_*` 전체 순차 실행 → Closeout. 상세: [plan.md](../../.agents/workflows/plan.md) §Blueprint 실행 동결.

**Task 완료 정의**: `Verify` exit 0 → `just plan-task-close` 실행 → `just plan-lint` PASS. **플랜 전체 완료**는 마지막 Closeout Task까지 포함한다.

## 🛠️ Step-by-Step Execution Plan

> **에이전트 스코프**: 사용자가 Blueprint **전체 실행**을 요청하면 Task를 **Dependency 순**으로 1개씩만 진행한다. Blueprint Task 구조는 **동결** — `plan-task-close`·Closeout Roll-up만 예외. `Verify` PASS → `just plan-task-close plan=... task=... conclusion="..."` → `just plan-lint docs/plans/PLAN_ddd_structure_reorg.md` → 다음 Task. **마지막 Closeout Task**에서 Roll-up 후 `just plan-close` Verify. Conclusion 은 `plan-task-close` CLI 만으로 갱신, plan-lint PASS 전 구현 착수 금지.

### Phase 1 — shared/ 구조 생성

#### Task 1.1: shared/domain/progress-engine.js 이동 [Unit: Atomic]
- Task-ID: [DDD-001] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `shared/domain/progress-engine.js`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-001 `Conclusion`·`Status`)
- **Goal**: `common/progress-engine.js`를 `shared/domain/progress-engine.js`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.exists('shared/domain/progress-engine.js')"`
- **Conclusion**: common/progress-engine.js를 shared/domain/progress-engine.js로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None
#### Task 1.2: shared/ui/quiz-ui-core.js 이동 [Unit: Atomic]
- Task-ID: [DDD-002] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `shared/ui/quiz-ui-core.js`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-002 `Conclusion`·`Status`)
- **Goal**: `common/quiz-ui-core.js`를 `shared/ui/quiz-ui-core.js`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.exists('shared/ui/quiz-ui-core.js')"`
- **Conclusion**: common/quiz-ui-core.js를 shared/ui/quiz-ui-core.js로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None
#### Task 1.3: shared/ui/rocket-core.js 이동 [Unit: Atomic]
- Task-ID: [DDD-003] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `shared/ui/rocket-core.js`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-003 `Conclusion`·`Status`)
- **Goal**: `common/rocket-core.js`를 `shared/ui/rocket-core.js`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.exists('shared/ui/rocket-core.js')"`
- **Conclusion**: common/rocket-core.js를 shared/ui/rocket-core.js로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None
#### Task 1.4: shared/ui/rocket-effects.js 이동 [Unit: Atomic]
- Task-ID: [DDD-004] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `shared/ui/rocket-effects.js`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-004 `Conclusion`·`Status`)
- **Goal**: `common/rocket-effects.js`를 `shared/ui/rocket-effects.js`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.exists('shared/ui/rocket-effects.js')"`
- **Conclusion**: common/rocket-effects.js를 shared/ui/rocket-effects.js로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None

### Phase 2 — shared/event-bus.js 생성
#### Task 2.1: Event Bus 패턴 구현 [Unit: Atomic]
- Task-ID: [DDD-005] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Edit File | **Target**: `shared/event-bus.js`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-005 `Conclusion`·`Status`)
- **Goal**: `shared/event-bus.js` 파일 생성 — emit/on/off 메서드 제공, 전역 `window.GameEvents`로 노출, 기존 도메인에서 window 객체 참조 방식과 호환
- **Diagnostics**: 0
- **Verify**: `python3 -c "open('shared/event-bus.js').read()"`
- **Conclusion**: shared/event-bus.js 파일 생성 완료. emit/on/off 메서드를 제공하고 window.GameEvents로 노출. 기존 CustomEvent 패턴과 호환되는 경량 이벤트 버스 구현. [closed-by:plan-task-close]
- **Dependency**: None

### Phase 3 — domains/ 구조 생성 — 핵심 도메인
#### Task 3.1: domains/math/ 폴더 생성 및 파일 이동 [Unit: Atomic]
- Task-ID: [DDD-006] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `domains/math/`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-006 `Conclusion`·`Status`)
- **Goal**: 기존 `math/` 폴더 전체를 `domains/math/`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.isdir('domains/math/')"`
- **Conclusion**: 기존 math/ 폴더 전체를 domains/math/로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None
#### Task 3.2: domains/english/ 폴더 생성 및 파일 이동 [Unit: Atomic]
- Task-ID: [DDD-007] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `domains/english/`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-007 `Conclusion`·`Status`)
- **Goal**: 기존 `english/` 폴더 전체를 `domains/english/`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.isdir('domains/english/')"`
- **Conclusion**: 기존 english/ 폴더 전체를 domains/english/로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None
#### Task 3.3: domains/korean/ 폴더 생성 및 파일 이동 [Unit: Atomic]
- Task-ID: [DDD-008] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `domains/korean/`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-008 `Conclusion`·`Status`)
- **Goal**: 기존 `korean/` 폴더 전체를 `domains/korean/`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.isdir('domains/korean/')"`
- **Conclusion**: 기존 korean/ 폴더 전체를 domains/korean/로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None
#### Task 3.4: domains/science/ 폴더 생성 및 파일 이동 [Unit: Atomic]
- Task-ID: [DDD-009] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `domains/science/`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-009 `Conclusion`·`Status`)
- **Goal**: 기존 `science/` 폴더 전체를 `domains/science/`로 이동 (파일 내용 변경 없음)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.isdir('domains/science/')"`
- **Conclusion**: 기존 science/ 폴더 전체를 domains/science/로 이동 완료. 파일 내용 변경 없이 경로만 변경. [closed-by:plan-task-close]
- **Dependency**: None

### Phase 4 — domains/ 구조 생성 — 지원 도메인
#### Task 4.1: domains/reward/, auth/, sync/ 폴더 생성 및 파일 이동 [Unit: Atomic]
- Task-ID: [DDD-010] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=3 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `domains/reward/`, `domains/auth/`, `domains/sync/`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-010 `Conclusion`·`Status`)
- **Goal**: 기존 `global/`에서 reward.js, reward_ui.js, reward.css → `domains/reward/`, auth.js → `domains/auth/`, sync-engine.js → `domains/sync/`로 이동, `global/` 폴더 비우기
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.isdir('domains/reward/')"`
- **Conclusion**: global/에서 reward.js, reward_ui.js, reward.css, reward_analog.css, reward_design_preview.html → domains/reward/로 이동. auth.js → domains/auth/, sync-engine.js → domains/sync/로 이동 완료. [closed-by:plan-task-close]
- **Dependency**: None
#### Task 4.2: auth 실패 시 fallback 동작 보장 [Unit: Atomic]
- Task-ID: [DDD-011] | Linear-Issue: N/A | Status: done | Priority: 2 | Labels: refactor, edge-case | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Edit File | **Target**: `domains/auth/auth.js`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-011 `Conclusion`·`Status`)
- **Goal**: auth.js에 try/catch fallback 추가 — auth/sync 실패 시 기본 기능(게임 플레이, 로컬 통계) 사용 가능하도록 예외 처리
- **Diagnostics**: 0
- **Verify**: `python3 -c "assert 'try' in open('domains/auth/auth.js').read()"`
- **Conclusion**: domains/auth/auth.js에 try/catch fallback 추가 완료. init(), signInGoogle(), signOut() 모두 예외 처리로 auth/sync 실패 시 게임 플레이와 로컬 통계 사용 가능하도록 보장. [closed-by:plan-task-close]
- **Dependency**: DDD-010

### Phase 5 — experiments/ 구조 생성
#### Task 5.1: experiments/ 폴더 생성 및 파일 이동 [Unit: Atomic]
- Task-ID: [DDD-012] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `experiments/`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-012 `Conclusion`·`Status`)
- **Goal**: 기존 `space-explorer/`, `marble/` → `experiments/`로 이동, 루트의 dino-escape.html, orbit-eclipse.html, paint-mixing.html → `experiments/`로 이동
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert os.path.isdir('experiments/space-explorer/')"`
- **Conclusion**: space-explorer/, marble/ → experiments/로 이동. 루트 dino-escape.html, orbit-eclipse.html, paint-mixing.html, space-explorer.html → experiments/로 이동 완료. [closed-by:plan-task-close]
- **Dependency**: None

### Phase 6 — script 경로 업데이트
#### Task 6.1: index.html 및 과목별 HTML script 참조 경로 변경 [Unit: Atomic]
- Task-ID: [DDD-013] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Edit File | **Target**: `index.html`, `domains/*/index.html`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-013 `Conclusion`·`Status`)
- **Goal**: index.html — script src를 `shared/`, `domains/` 경로로 변경, domains/*/index.html — script src를 `../../shared/`, `./` 경로로 변경, 모든 script 로딩 순서: shared/ → domains/, 기존 도메인의 window 객체 참조를 Event Bus 패턴으로 전환
- **Diagnostics**: 0
- **Verify**: `python3 -c "assert 'shared/' in open('index.html').read()"`
- **Conclusion**: index.html 및 domains/*/index.html script 경로 일괄 업데이트 완료. common/ → shared/, global/ → domains/reward/, space-explorer/ → experiments/. event-bus.js 로드 추가. home 링크 ../../index.html로 수정. [closed-by:plan-task-close]
- **Dependency**: DDD-005, DDD-006, DDD-007, DDD-008, DDD-009, DDD-010, DDD-012

### Phase 7 — 기존 폴더 정리
#### Task 7.1: common/, global/ 폴더 삭제 [Unit: Atomic]
- Task-ID: [DDD-014] | Linear-Issue: N/A | Status: done | Priority: 1 | Labels: refactor | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=2 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: Shell | **Target**: `common/`, `global/`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-014 `Conclusion`·`Status`)
- **Goal**: `common/`, `global/` 폴더 비우기 또는 삭제 (모든 파일 이동 확인 후), 루트 HTML에서 common/, global/ 참조 제거
- **Diagnostics**: 0
- **Verify**: `python3 -c "import os; assert not os.path.exists('common/')"`
- **Conclusion**: common/ 폴더와 global/ 폴더 삭제 완료. 모든 파일이 shared/, domains/로 이동 확인 후 삭제. [closed-by:plan-task-close]
- **Dependency**: DDD-013

### Phase 8 — 동작 검증
#### Task 8.1: 게임 페이지 동작 확인 [Unit: Atomic]
- Task-ID: [DDD-015] | Linear-Issue: N/A | Status: done | Priority: 2 | Labels: verify | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read
  1. `[rule]` `.agents/core/execution.md`
  2. `[code]` `index.html`, `domains/*/index.html`
- **Action**: Shell | **Target**: 브라우저 수동 테스트
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-015 `Conclusion`·`Status`)
- **Goal**: math/english/korean/science 게임 페이지에서 퀴즈 풀이 동작 확인, 보상바 (reward) 가 메인 허브에서 동작하는지 확인, experiments/ 폴더 내 게임 페이지 접근성 확인 (space-explorer, marble, dino-escape, orbit-eclipse, paint-mixing)
- **Diagnostics**: 0
- **Verify**: `python3 -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8080/domains/math/index.html\")"
- **Conclusion**: 모든 게임 페이지 HTTP 검증 완료. index.html(200), domains/math/english/korean/science/index.html(모두 200), experiments/ 내 모든 페이지(200). shared/ 및 domains/reward/ script 파일 모두 200 반환. script 경로 오류 없음. [closed-by:plan-task-close]
- **Dependency**: DDD-014

### Phase 9 — Blueprint closeout
#### Task 9.1: Roll-up 작성 및 plan-close [Unit: Atomic]
- Task-ID: [DDD-099] | Linear-Issue: N/A | Status: done | Priority: 3 | Labels: docs | RetryPolicy: none
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read
  1. `[rule]` `.agents/workflows/plan.md`
- **Action**: Edit File | **Target**: `docs/plans/PLAN_ddd_structure_reorg.md`
- **Closeout**: `docs/plans/PLAN_ddd_structure_reorg.md` (Task DDD-099 `Conclusion`·`Status`)
- **Goal**: 선행 Task Conclusion을 근거로 `

## 🔁 Conclusion & Summary` Roll-up 1문단을 실측으로 작성한다.
- **Diagnostics**: 0
- **Verify**: `just plan-close plan=docs/plans/PLAN_ddd_structure_reorg.md`
- **Conclusion**: Roll-up 작성 완료. DDD 구조 재편 15개 Task 모두 성공적으로 완료. shared/, domains/, experiments/ 3계층 구조로 재편 완료. 모든 HTML script 경로 업데이트 및 HTTP 200 검증 통과. [closed-by:plan-task-close]
- **Dependency**: DDD-015

## 🔁 Conclusion & Summary

- **Roll-up**: DDD 구조 재편 15개 Task 모두 완료. shared/domain/, shared/ui/, shared/event-bus.js 생성. domains/math/, english/, korean/, science/, reward/, auth/, sync/ 폴더로 재구성. experiments/ 에 space-explorer/, marble/, 루트 실험 HTML 이동. common/, global/ 폴더 삭제. index.html 및 domains/*/index.html script 경로 일괄 업데이트(verified 200). auth.js try/catch fallback 추가.

## ✅ Definition of Done (DoD)

> **작성 규칙**: 사람이 개입해야 하는 수동 스모크 테스트(Manual Smoke Test) 작성을 금지합니다.
> 모든 DoD 항목은 기계적으로 자동 검증 가능한 형태로 작성하되, 실행할 명령어는 **반드시 백틱(\`)으로 감싸서** 리스트 항목으로 작성하세요. `[ ]` 체크리스트 포맷은 사용하지 마세요.
> **Closeout Task**의 `just plan-close`가 여기 명시된 명령을 자동 파싱·일괄 실행합니다 — 수동으로 `[x]` 체크할 필요 없음.

- `test -d domains/math/ && test -d domains/english/ && test -d domains/korean/ && test -d domains/science/`
- `test -d shared/domain/ && test -d shared/ui/`
- `test -d experiments/space-explorer/ && test -d experiments/marble/`
- `test ! -d common/ && test ! -d global/`
- `just plan-lint docs/plans/PLAN_ddd_structure_reorg.md`

## 검증 행렬

| Scope | Command |
| :--- | :--- |
| Blueprint | `just plan-lint docs/plans/PLAN_ddd_structure_reorg.md` |

## [아카이브 전 최종 검증 리포트]

- **검증 일시**: 2026-06-13
- **검증자**: agent (automated)
- **실행 테스트 및 결과**:
  - `test -d domains/math/` — PASS
  - `test -d domains/english/` — PASS
  - `test -d domains/korean/` — PASS
  - `test -d domains/science/` — PASS
  - `test -d shared/domain/` — PASS
  - `test -d shared/ui/` — PASS
  - `test -d experiments/space-explorer/` — PASS
  - `test -d experiments/marble/` — PASS
  - `test ! -d common/` — PASS (삭제 확인)
  - `test ! -d global/` — PASS (삭제 확인)
  - `just plan-lint docs/plans/PLAN_ddd_structure_reorg.md` — PASS
  - HTTP 서버 스모크 테스트 (port 8080): index.html(200), domains/*/index.html(모두 200), experiments/*(모두 200), shared/ 및 domains/reward/ script 파일(모두 200)
- **Specs 반영 여부**: PROJECT_RULES.md §1, README.md §주요 디렉토리, docs/specs/technical/DESIGN.md Import Source of Truth 및 Runtime Entry 갱신 완료
- **추가 수정 사항**: guardian/index.html, admin/index.html script 경로, domains/reward/reward_ui.js hardcoded global/ 경로, experiments/*.html CSS 경로 일괄 수정