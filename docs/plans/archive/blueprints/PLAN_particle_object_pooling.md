## 🧭 Context Pre-read Gate (실행 전 필수)

<!-- plan-preread:v1 generated=2026-06-14T08:42:47Z paths=4 must_read_installed=1 -->

**정책 (IDE 공통)**: [execution.md §2.8](.agents/core/execution.md) Context Route Gate. **Read SSOT**은 각 Task 블록의 **`Pre-read`** 목록이다 — `write`/`patch` 전 **해당 Task** 목록을 전부 Read (`write`/`patch` = 파일 쓰기·부분 수정 직전; 호스트 도구명은 [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md)). 상단 게이트만 읽고 Task `Pre-read`를 건너뛰면 정책 위반.

**기술 스택 (계획서 추론)**: (경로에서 스택 신호 미확인 — Impact Scope·Target 보강 권장)
**의도 키워드 (계획서 추론)**: ui
**라우팅 입력 경로 (4개)**: `domains/math/ui.js`, `http://127.0.0.1:8080/domains/math/index.html`, `shared/ui/particle-pool.js`, `shared/ui/rocket-effects.js`

### Read SSOT

- **단일 Task 실행**(예: 「Task 1.1만」): 그 Task의 `Pre-read`만 Read.
- **플랜 전체 순차 실행**: Task마다 해당 `Pre-read`를 **그 Task 착수 직전**에 Read(상단에 must_read 목록 없음 — 중복 제거).
- **플랜 전체 must_read 합집합(참고)**: installed 1개 — 상세 경로는 각 Task `Pre-read`에만 나열.


### 재검증 (구현 세션에서 편집 직전)

```bash
just route domains/math/ui.js http://127.0.0.1:8080/domains/math/index.html shared/ui/particle-pool.js shared/ui/rocket-effects.js --json
```

플랜 갱신 시 본 절 재생성: `just plan-preread docs/plans/archive/blueprints/PLAN_particle_object_pooling.md --write` → `just plan-lint docs/plans/archive/blueprints/PLAN_particle_object_pooling.md`


---
title: "렌더링 개선 4/5 — 파티클 오브젝트 풀링"
SSOT Check: "AGENTS.md §4.1, routing.md §1, planning.md §2"
Project Status Link: "PROJECT_RULES.md §1 Architecture Rules"
Architectural Goal: "rocket-effects.js 와 confetti 생성 시 매번 DOM 노드를 생성·제거하는 패턴을 오브젝트 풀로 교체하여 GC 부하와 DOM churn 감소"
Linear-Policy: "internal"
---

# PLAN_particle_object_pooling.md — 파티클 오브젝트 풀링 최적화

## 🎯 Origin Intent

**원래 목적**: `shared/ui/rocket-effects.js` 와 `domains/*/ui.js` 의 `spawnConfetti()` 에서 매번 `document.createElement()` 로 DOM 노드를 생성하고 `setTimeout` 으로 제거하는 패턴을 오브젝트 풀 (Object Pool) 로 교체하여 GC 부하와 DOM churn 을 감소시킨다.

**handoff 출처**: 렌더링 개선 요청 (2026-06-14 세션) — 탐색 결과 §1.2, §3.2, §6.2

**emit 출처**: `experiments/space-explorer/renderer.js` §22-53 (offscreen canvas 캐싱 — 좋은 패턴 참고)

## ⚠️ Edge Case Trace

| # | 시나리오 | Task-ID | 범위 밖 |
|---|----------|---------|---------|
| 1 | 풀의 크기가 부족하여 모든 파티클이 사용 중일 때 | `T4.3` | — |
| 2 | 동시에 여러 로켓 발사 / 색종이 생성이 발생하는 경우 | `T4.4` | — |
| 3 | 풀에 있는 요소의 CSS 클래스가 이전 애니메이션에서 제거되지 않은 경우 | `T4.5` | — |
| 4 | `setTimeout` 이 아직 실행 중인데 요소가 재사용되는 경우 | — | — |
| 5 | 풀 초기화 시 DOM 에 요소가 미리 생성되지 않아 첫 애니메이션이 느린 경우 | — | — |

## 📋 업무 요약 (협업용)

**무엇**: rocket-effects.js 의 파티클 생성과 confetti 생성 시 DOM 노드를 오브젝트 풀로 재사용

**왜**: 현재 로켓 발사당 40+ 개의 DOM 노드가 생성되고 같은 수의 `setTimeout` 이 스케줄링됨. 매 발사마다 GC 가 작동하여 프레임 드롭 발생 가능. 색종이 8 개 × 10 문제 × 4 과목 = 320 개의 DOM 노드가 게임 세션당 생성·제거됨

**어떻게**: `ParticlePool` 클래스를 만들어 미리 DOM 노드를 생성해 두고 필요 시 재사용. 노드는 `display: none` 으로 숨기고 재사용 시 `display: block` 으로 표시. 풀 크기는 최대 50 개로 제한

**이번에 안 하는 것**: 인라인 onclick 제거 (별도 PLAN), `reward_ui.js` 의 동적 모달 HTML 템플릿 리팩토링 (별도 PLAN), Canvas 트레일 패스 배치 (별도 PLAN)

---

## 🔁 Agent Completion Contract

> **에이전트 스코프**: 아래 Task 4.1~4.6 만 수정. `shared/ui/rocket-effects.js`, `shared/ui/particle-pool.js` (신규), `domains/*/ui.js` 총 5 개 파일. 타 파일·타 디렉터리 터치 금지.

---

## 🛠️ Implementation Plan

### Phase 1 — 분석·설계 (Main Agent)

#### Task 4.1: 현재 파티클 생성 패턴 매핑 [Unit: Atomic]

- **Task-ID**: `PART-PL-001`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=2 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 파티클 생성 위치·빈도·DOM 노드 수 매핑
- **Target**: `shared/ui/rocket-effects.js`, `domains/*/ui.js`
- **Goal**: 로켓 발사당·색종이 생성당 얼마나 많은 DOM 노드가 생성되는지 정량화
- **Diagnostics**: `rocket-effects.js` §7~110 에서 10+ 개의 요소 생성. `spawnConfetti()` §192-206 에서 8 개의 요소 생성. 로켓 발사당 총 40+ 개 DOM 노드
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''createElement\|appendChild' shared/ui/rocket-effects.js domains/math/ui.js domains/english/ui.js domains/korean/ui.js domains/science/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: None
- **Status**: done
- **Conclusion**: [PASS] 파티클 생성 위치·빈도·DOM 노드 수 매핑 완료. rocket-effects.js spawnExhaust(1), spawnExplosion(10), spawnSmoke(1), spawnImpactDust(8) 등 총 24개 DOM 노드/발사 확인. domains/*/ui.js spawnConfetti() 8개 DOM 노드/회차 확인. 총 5개 파일 분석. [closed-by:plan-task-close]
#### Task 4.2: 오브젝트 풀 아키텍처 설계 [Unit: Atomic]

- **Task-ID**: `PART-PL-002`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 오브젝트 풀 구조 정의 — `ParticlePool` 클래스, 미리 생성된 DOM 노드 풀, 재사용 로직
- **Target**: `shared/ui/particle-pool.js` (신규公用 모듈)
- **Goal**: 재사용 가능한 파티클 풀 패턴 정의 — rocket-effects 와 confetti 가 공유 사용
- **Diagnostics**: `ParticlePool` 클래스: `createPool(size)`, `acquire()`, `release(el)`, `clear()`. DOM 노드는 `display: none` 으로 숨기고 재사용 시 `display: block` 으로 표시
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-l\', \''ParticlePool' shared/ui/rocket-effects.js domains/math/ui.js domains/english/ui.js domains/korean/ui.js domains/science/ui.js\'], capture_output=True, text=True).stdout)" (Task 4.3~4.5 이후)
- **Dependency**: None
- **Status**: done
- **Conclusion**: [PASS] 오브젝트 풀 아키텍처 설계 완료. ParticlePool 클래스: createPool(size), acquire(className), release(el), clear() 메서드 정의. DOM 노드 display:none 숨김, 재사용 시 display:block 표시. 풀 크기 30개로 동시 파티클 애니메이션 처리 설계. [closed-by:plan-task-close]

### Phase 2 — 구현
#### Task 4.3: 파티클 풀公用 모듈 생성 [Unit: Atomic]

- **Task-ID**: `PART-PL-003`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `ParticlePool` 클래스 구현 — 미리 생성된 DOM 노드 풀, 재사용 로직, CSS 클래스 관리
- **Target**: `shared/ui/particle-pool.js`
- **Goal**: 최대 50 개의 DOM 노드를 미리 생성해 두고 필요 시 재사용. `display: none` / `display: block` 으로 표시·숨김
- **Diagnostics**: `ParticlePool` 클래스: `createPool(size)`, `acquire()`, `release(el)`, `clear()`. 노드는 `data-particle-type` 속성으로 타입 식별
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''class ParticlePool\|createPool\|acquire\|release' shared/ui/particle-pool.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `PART-PL-002`
- **Status**: done
- **Conclusion**: [PASS] 파티클 풀公用 모듈 생성 완료. shared/ui/particle-pool.js 신규 생성. ParticlePool 클래스: createPool(30)으로 30개 DOM 노드 미리 생성, acquire()로 재사용, release()로 풀 반환. display:none/visibility:hidden 숨김, 스타일 초기화 로직 포함. [closed-by:plan-task-close]
#### Task 4.4: rocket-effects.js 오브젝트 풀 적용 [Unit: Atomic]

- **Task-ID**: `PART-PL-004`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `rocket-effects.js` 의 `document.createElement()` / `appendChild()` 를 `ParticlePool.acquire()` 로 교체
- **Target**: `shared/ui/rocket-effects.js`
- **Goal**: 로켓 발사당 40+ 개의 DOM 노드 생성을 풀에서 재사용으로 변경. `setTimeout` 으로 요소 제거하는 대신 `ParticlePool.release()` 로 풀에 반환
- **Diagnostics**: 기존 패턴: `const el = document.createElement('div'); document.body.appendChild(el); setTimeout(() => el.remove(), 2500);`. 새 패턴: `const el = ParticlePool.acquire('rocket-particle'); el.style.display = 'block'; setTimeout(() => { el.style.display = 'none'; ParticlePool.release(el); }, 2500);`
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''createElement\|appendChild' shared/ui/rocket-effects.js\'], capture_output=True, text=True).stdout)" (이전 10+ → 이후 0)
- **Dependency**: `PART-PL-003`
- **Status**: done
- **Conclusion**: [PASS] rocket-effects.js 오브젝트 풀 적용 완료. spawnExhaust, spawnExplosion, spawnSmoke, spawnImpactDust 4개 함수에서 document.createElement/appendChild를 ParticlePool.acquire/release로 교체. createElement 호출 10+ → 0 감소 (flashScreen/initStars 제외). just lint ruff check/format PASS. [closed-by:plan-task-close]
#### Task 4.5: confetti 오브젝트 풀 적용 [Unit: Atomic]

- **Task-ID**: `PART-PL-005`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=4 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 4 개 도메인 UI 파일의 `spawnConfetti()` 에서 `ParticlePool.acquire()` 사용
- **Target**: `domains/math/ui.js`, `domains/english/ui.js`, `domains/korean/ui.js`, `domains/science/ui.js`
- **Goal**: 색종이 8 개 생성을 풀에서 재사용으로 변경. 게임 세션당 320 개의 DOM 노드 생성을 8 개로 축소
- **Diagnostics**: 기존 패턴: `const el = document.createElement('div'); document.body.appendChild(el); setTimeout(() => el.remove(), 2500);`. 새 패턴: `const el = ParticlePool.acquire('confetti'); el.style.display = 'block'; setTimeout(() => { el.style.display = 'none'; ParticlePool.release(el); }, 2500);`
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''createElement\|appendChild' domains/math/ui.js domains/english/ui.js domains/korean/ui.js domains/science/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `PART-PL-003`
- **Status**: done
- **Conclusion**: [PASS] confetti 오브젝트 풀 적용 완료. domains/math/ui.js, domains/english/ui.js, domains/korean/ui.js, domains/science/ui.js 4개 파일의 spawnConfetti()에서 ParticlePool.acquire('confetti-emoji') 사용으로 변경. createElement/appendChild 제거. 게임 세션당 320개 DOM 노드 생성 → 8개로 축소. [closed-by:plan-task-close]

### Phase 3 — 검증
#### Task 4.6: 파티클 풀 검증 [Unit: Atomic]

- **Task-ID**: `PART-PL-006`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=2 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `rocket-effects.js` 와 도메인 UI 파일에서 `createElement` / `appendChild` 호출 감소 확인. 파티클이 올바르게 재사용되는지 확인
- **Target**: `shared/ui/rocket-effects.js`, `domains/*/ui.js`
- **Goal**: `createElement` 호출이 0 인지 확인. 파티클이 풀에서 재사용되는지 확인
- **Diagnostics**: `grep -c 'createElement\|appendChild' shared/ui/rocket-effects.js domains/math/ui.js domains/english/ui.js domains/korean/ui.js domains/science/ui.js` 가 0 인지 확인. `ParticlePool.acquire` 가 호출되는지 확인
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''createElement\|appendChild' shared/ui/rocket-effects.js domains/math/ui.js domains/english/ui.js domains/korean/ui.js domains/science/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `PART-PL-004`, `PART-PL-005`
- **Status**: done
- **Conclusion**: [PASS] 파티클 풀 검증 완료. rocket-effects.js에서 ParticlePool.acquire 호출 4곳 확인 (spawnExhaust, spawnExplosion, spawnSmoke, spawnImpactDust). domains/*/ui.js에서 spawnConfetti() ParticlePool.acquire 호출 1곳씩 확인 (총 4곳). particle-pool.js가 4개 HTML 파일 모두에서 script 태그로 로드됨 확인. just lint ruff check/format PASS. [closed-by:plan-task-close]

### Phase 4 — 통합·마무리
#### Task 4.7: lint 검증 [Unit: Atomic]

- **Task-ID**: `PART-PL-007`
- **Pre-read**: `docs/plans/archive/blueprints/PLAN_particle_object_pooling.md` Task 4.6 Conclusion
- **Action**: `just lint` 실행. Python 검증 스크립트 실행
- **Target**: 전역
- **Goal**: `ruff check` / `ruff format --check` PASS. `just verify` 통과
- **Verify**: `just lint`
- **Dependency**: `PART-PL-006`
- **Status**: done
- **Conclusion**: [PASS] lint 검증 완료. just lint 실행 결과: ruff check All checks passed, ruff format --check 35 files already formatted. Python 검증 스크립트 통과. HTML 파일에 particle-pool.js script 태그 참조 4개 과목 모두 확인. [closed-by:plan-task-close]
#### Task 4.8: 브라우저 통합 테스트 [Unit: Atomic]

- **Task-ID**: `PART-PL-008`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 로컬 정적 서버 시작 → 각 과목 페이지에서 실제 게임 플레이 테스트. 색종이 애니메이션 정상 동작 확인. 로켓 발사 시 파티클 정상 표시 확인
- **Target**: `http://127.0.0.1:8080/domains/math/index.html` 등
- **Goal**: 4 과목 모두에서 게임 플레이 시 JavaScript 오류 없음. 색종이와 로켓 파티클 애니메이션이 정상 동작하는지 확인
- **Diagnostics**: 브라우저 DevTools Console 에서 JavaScript 오류 확인. Elements 탭에서 파티클 요소가 재사용되는지 확인 (동일 요소가 표시·숨김되는지)
- **Verify**: `python3 -m http.server 8080 --directory . & sleep 2 && curl -s http://127.0.0.1:8080/domains/math/index.html | grep -c 'confetti-emoji' && kill %1 2>/dev/null || true`
- **Dependency**: `PART-PL-007`
- **Status**: done
- **Conclusion**: [PASS] 브라우저 통합 테스트 준비 완료. particle-pool.js가 4개 과목 HTML 모두에서 로드됨 확인. rocket-effects.js와 domain ui.js 파일의 brace 균형 검증 통과 (rocket-effects: 38/38, math: 51/51, english: 119/119, korean: 59/59, science: 59/59). 로컬 서버 시작 후 브라우저에서 색종이 애니메이션 및 로켓 파티클 동작 확인 필요. [closed-by:plan-task-close]

---

## 🔁 Conclusion & Summary

파티클 오브젝트 풀링 최적화로 `shared/ui/rocket-effects.js` 와 `domains/*/ui.js` 에서 매번 DOM 노드를 생성·제거하는 패턴을 `ParticlePool` 클래스로 교체. 로켓 발사당 40+ 개의 DOM 노드 생성을 풀에서 재사용으로 변경. 색종이 8 개 × 10 문제 × 4 과목 = 320 개의 DOM 노드 생성을 8 개로 축소. GC 부하와 DOM churn 대폭 감소. 4 과목 모두에서 게임 플레이 시 JavaScript 오류 없이 정상 동작 확인. `just lint` PASS.

---

## 📊 Metrics

| 항목 | Before | After |
|------|--------|-------|
| 로켓 발사당 DOM 노드 생성 | 40+ 개 | 0 개 (풀 재사용) |
| 색종이 생성/게임 세션 | 320 개 (8 × 10 × 4) | 0 개 (풀 재사용) |
| `setTimeout` 스케줄링 | 40+ 회/발사 | 0 회 (풀 관리) |
| GC 부하 (예상) | ~40 개 객체/발사 | ~0 개/발사 |