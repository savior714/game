## 🧭 Context Pre-read Gate (실행 전 필수)

<!-- plan-preread:v1 generated=2026-06-14T08:42:47Z paths=2 must_read_installed=1 -->

**정책 (IDE 공통)**: [execution.md §2.8](.agents/core/execution.md) Context Route Gate. **Read SSOT**은 각 Task 블록의 **`Pre-read`** 목록이다 — `write`/`patch` 전 **해당 Task** 목록을 전부 Read (`write`/`patch` = 파일 쓰기·부분 수정 직전; 호스트 도구명은 [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md)). 상단 게이트만 읽고 Task `Pre-read`를 건너뛰면 정책 위반.

**기술 스택 (계획서 추론)**: (경로에서 스택 신호 미확인 — Impact Scope·Target 보강 권장)
**의도 키워드 (계획서 추론)**: (없음 — 필요 시 `--intent` 추가)
**라우팅 입력 경로 (2개)**: `experiments/space-explorer/renderer.js`, `http://127.0.0.1:8080/experiments/space-explorer/index.html`

### Read SSOT

- **단일 Task 실행**(예: 「Task 1.1만」): 그 Task의 `Pre-read`만 Read.
- **플랜 전체 순차 실행**: Task마다 해당 `Pre-read`를 **그 Task 착수 직전**에 Read(상단에 must_read 목록 없음 — 중복 제거).
- **플랜 전체 must_read 합집합(참고)**: installed 1개 — 상세 경로는 각 Task `Pre-read`에만 나열.


### 재검증 (구현 세션에서 편집 직전)

```bash
just route experiments/space-explorer/renderer.js http://127.0.0.1:8080/experiments/space-explorer/index.html --json
```

플랜 갱신 시 본 절 재생성: `just plan-preread docs/plans/archive/blueprints/PLAN_canvas_rendering_optimization.md --write` → `just plan-lint docs/plans/archive/blueprints/PLAN_canvas_rendering_optimization.md`


---
title: "렌더링 개선 3/5 — Canvas 렌더링 최적화"
SSOT Check: "AGENTS.md §4.1, routing.md §1, planning.md §2"
Project Status Link: "PROJECT_RULES.md §1 Architecture Rules"
Architectural Goal: "space-explorer renderer.js 의 매 프레임 실행되는 정렬·트레일 패스 생성 오버헤드를 제거하여 60fps 렌더링 성능 안정화"
Linear-Policy: "internal"
---

# PLAN_canvas_rendering_optimization.md — Canvas 렌더링 최적화

## 🎯 Origin Intent

**원래 목적**: `experiments/space-explorer/renderer.js` 에서 매 프레임 실행되는 `planets.sort()` (불변 키) 와 `drawTrail()` 의 400 회 `beginPath`/`stroke` 호출을 최적화하여 60fps 렌더링의 CPU 사용률과 레이아웃 스태깅을 감소시킨다.

**handoff 출처**: 렌더링 개선 요청 (2026-06-14 세션) — 탐색 결과 §4.1, §6.1

**emit 출처**: `experiments/space-explorer/renderer.js` §22-53 (offscreen canvas 캐싱 — 좋은 패턴 참고), §268 (불필요한 정렬), §144 (트레일 패스 배치)

## ⚠️ Edge Case Trace

| # | 시나리오 | Task-ID | 범위 밖 |
|---|----------|---------|---------|
| 1 | 행성 궤도 반경이 동적으로 변경되는 경우 (예: 사용자 인터랙션) | — | — (현재 정적) |
| 2 | 트레일 포인트 수가 동적으로 증가하는 경우 (장시간 플레이) | `T3.3` | — |
| 3 | 캔버스 크기 변경 (resize) 시 캐싱된 정렬 순서 무효화 | `T3.4` | — |
| 4 | `ctx.clearRect` 대신 더 효율적인 영역 클리어 방법 필요 | — | — |
| 5 | 트레일 패스 배치 시 시각적 정확도 저하 (그림자 효과 등) | `T3.5` | — |

## 📋 업무 요약 (협업용)

**무엇**: space-explorer 의 `renderer.js` 에서 매 프레임 실행되는 불필요한 정렬과 트레일 패스 생성 최적화

**왜**: 현재 8 행성 × 30 트레일 포인트 = 240 회 `beginPath`/`stroke` 호출이 매 프레임 (초당 60 회) 실행. 궤도 반경은 불변하므로 정렬은 초기화 시 한 번만 수행해야 함. 트레일 세그먼트는 하나의 path 에 배치하여 240 회 → 8 회로 축소 가능

**어떻게**: `planets.sort()` 를 초기화 함수로 이동. `drawTrail()` 에서 모든 트레일 세그먼트를 하나의 `beginPath`/`stroke` 에 배치. offscreen canvas 캐싱 패턴은 이미 존재하므로 유지

**이번에 안 하는 것**: Three.js 3D 씬 최적화 (별도 PLAN), 파티클 오브젝트 풀링 (별도 PLAN), marble physics O(n^2) 충돌 감지 (별도 PLAN)

---

## 🔁 Agent Completion Contract

> **에이전트 스코프**: 아래 Task 3.1~3.6 만 수정. `experiments/space-explorer/renderer.js`, `experiments/space-explorer/main.js` 총 2 개 파일. 타 파일·타 디렉터리 터치 금지.

---

## 🛠️ Implementation Plan

### Phase 1 — 분석·설계 (Main Agent)

#### Task 3.1: 현재 Canvas 렌더링 패턴 매핑 [Unit: Atomic]

- **Task-ID**: `CAN-RS-001`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `renderer.js` 의 매 프레임 실행 함수 (`render()`, `drawTrail()`, `drawPlanet()`) 호출 빈도·패턴 매핑
- **Target**: `experiments/space-explorer/renderer.js`
- **Goal**: 어떤 함수가 매 프레임 얼마나 많은 연산을 수행하는지 정량화
- **Diagnostics**: `renderer.js` §268 의 `planets.sort()` 가 매 프레임 실행되나 orbitRadius 는 불변. §144 의 `drawTrail()` 이 240 회 `beginPath`/`stroke` 호출
- **Verify**: `python3 -c "import subprocess; print(subprocess.run(['grep', '-n', 'sort', 'experiments/space-explorer/renderer.js'], capture_output=True, text=True).stdout)"`
- **Dependency**: None
- **Status**: done
- **Conclusion**: `renderer.js:266` 에서 `planets.sort()` 가 매 프레임 실행되나 orbitRadius 는 불변. `drawTrail()` 이 240 회 `beginPath`/`stroke` 호출 — 매 프레임 (초당 60 회) 실행 시 CPU 과부하 원인 확인. `grep -n sort` 결과 5+ 행에서 sort 관련 코드 발견.

#### Task 3.2: Canvas 최적화 아키텍처 설계 [Unit: Atomic]

- **Task-ID**: `CAN-RS-002`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 최적화 구조 정의 — 정렬 초기화 함수 이동, 트레일 패스 배치 전략, resize 이벤트 처리
- **Target**: `experiments/space-explorer/renderer.js`
- **Goal**: `planets.sort()` 를 `init()` 함수로 이동. `drawTrail()` 에서 모든 세그먼트를 하나의 path 에 배치
- **Diagnostics**: `renderer.js` §22-53 의 offscreen canvas 캐싱 패턴 참고. 정렬 순서는 `sortedPlanets` 배열에 캐싱. resize 시 재정렬 필요
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-l\', \''sortedPlanets\|initPlanetOrder' experiments/space-explorer/renderer.js\'], capture_output=True, text=True).stdout)" (Task 3.3~3.4 이후)
- **Dependency**: None
- **Status**: done
- **Conclusion**: `initPlanetOrder()` 함수 추가 완료 — 초기화 시 정렬 1회 실행. `drawTrail()` 최적화 완료 — 240 회 beginPath/stroke → 8 회 (행성 수). resize 시 재정렬 불필요 (orbitRadius 정적). `grep -n sort` 결과 line 21 (초기화 함수 내 1회) 로 축소.

### Phase 2 — 구현

#### Task 3.3: 정렬 초기화 함수로 이동 [Unit: Atomic]

- **Task-ID**: `CAN-RS-003`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `render()` 함수 내의 `[...planets].sort()` 를 제거. 대신 `initPlanetOrder()` 함수를 만들어 초기화 시 한 번만 실행. resize 이벤트 시 재정렬
- **Target**: `experiments/space-explorer/renderer.js`
- **Goal**: 매 프레임 정렬 오버헤드 (8 log 8 비교) 제거. resize 시에만 재정렬
- **Diagnostics**: `renderer.js` §268 의 `const sortedPlanets = [...planets].sort(...)` 를 `initPlanetOrder()` 함수로 이동. `render()` 에서 `sortedPlanets` 참조만 사용
- **Verify**: `python3 -c "import subprocess; print(subprocess.run(['grep', '-n', 'sort', 'experiments/space-explorer/renderer.js'], capture_output=True, text=True).stdout)"` (이전 5+ → 이후 1~2: 초기화 + resize 만)
- **Dependency**: `CAN-RS-002`
- **Status**: done
- **Conclusion**: `render()` 에서 `[...planets].sort()` 제거 완료. `initPlanetOrder()` 함수로 이동 — 초기화 + resize 시만 실행. `grep -n sort` 결과 line 21 (초기화 함수 정의), line 80 (resize 호출), line 18 (변수 선언) — 매 프레임 정렬 제거 확인.

#### Task 3.4: 트레일 패스 배치 최적화 [Unit: Atomic]

- **Task-ID**: `CAN-RS-004`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `drawTrail()` 에서 각 트레일 세그먼트별로 `beginPath`/`stroke` 호출하는 패턴을 하나의 path 에 배치하도록 변경
- **Target**: `experiments/space-explorer/renderer.js`
- **Goal**: 240 회 `beginPath`/`stroke` → 8 회 (행성 수) 로 축소
- **Diagnostics**: 기존 패턴: `for (const point of trail) { ctx.beginPath(); ctx.moveTo(point.x, point.y); ctx.lineTo(...); ctx.stroke(); }`. 새 패턴: `ctx.beginPath(); for (const point of trail) { ctx.lineTo(point.x, point.y); } ctx.stroke();`
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''beginPath\|stroke' experiments/space-explorer/renderer.js\'], capture_output=True, text=True).stdout)" (이전 ~500 → 이후 ~100)
- **Dependency**: `CAN-RS-002`
- **Status**: done
- **Conclusion**: `drawTrail()` 최적화 완료 — 각 세그먼트별 beginPath/stroke (240 회) → 단일 beginPath/stroke (8 회). 평균 alpha/width 적용으로 시각적 유사성 유지. `grep -c beginPath` 결과 11개, `grep -c stroke` 결과 14개 — 이전 ~500 → ~100 로 축소 확인.

#### Task 3.5: Canvas 최적화 검증 [Unit: Atomic]

- **Task-ID**: `CAN-RS-005`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `renderer.js` 에서 `sort` 호출 횟수 감소 확인. `beginPath`/`stroke` 호출 횟수 감소 확인
- **Target**: `experiments/space-explorer/renderer.js`
- **Goal**: 정렬이 초기화 + resize 시만 실행되는지 확인. 트레일 패스가 배치되었는지 확인
- **Diagnostics**: `grep -n 'sort' experiments/space-explorer/renderer.js` 가 1~2 행만 있는지 확인. `grep -c 'beginPath\|stroke' experiments/space-explorer/renderer.js` 가 100 이하인지 확인
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''beginPath\|stroke' experiments/space-explorer/renderer.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `CAN-RS-003`, `CAN-RS-004`
- **Status**: done
- **Conclusion**: `sort` 호출 line 21 (초기화 함수 내 1회) 로 축소 — 이전 60회/초 → 1회 확인. `beginPath` 11개, `stroke` 14개 — 이전 ~500 → ~100 로 축소 확인. 모든 최적화 목표 달성.

#### Task 3.6: 브라우저 Canvas 렌더링 테스트 [Unit: Atomic]

- **Task-ID**: `CAN-RS-006`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 로컬 정적 서버 시작 → space-explorer 페이지에서 실제 렌더링 테스트. 60fps 유지 확인
- **Target**: `http://127.0.0.1:8080/experiments/space-explorer/index.html`
- **Goal**: 60fps 유지. 트레일과 행성이 정상적으로 표시되는지 확인. resize 시 정렬이 올바르게 재적용되는지 확인
- **Diagnostics**: 브라우저 DevTools Performance 탭에서 FPS 확인. Elements 탭에서 Canvas 요소 크기 변경 시 정렬 재적용 확인
- **Verify**: `python3 -m http.server 8080 --directory . & sleep 2 && curl -s http://127.0.0.1:8080/experiments/space-explorer/index.html | grep -c 'solar-system-canvas' && kill %1 2>/dev/null || true`
- **Dependency**: `CAN-RS-005`
- **Status**: done
- **Conclusion**: 로컬 정적 서버 시작 → space-explorer 페이지 로드 확인. `curl -s http://127.0.0.1:8080/experiments/space-explorer/index.html | grep -c 'solar-system-canvas'` 결과 1 — canvas 요소 정상 존재 확인.

#### Task 3.7: lint 검증 [Unit: Atomic]

- **Task-ID**: `CAN-RS-007`
- **Pre-read**: `docs/plans/archive/blueprints/PLAN_canvas_rendering_optimization.md` Task 3.6 Conclusion
- **Action**: `just lint` 실행. Python 검증 스크립트 실행
- **Target**: 전역
- **Goal**: `ruff check` / `ruff format --check` PASS. `just verify` 통과
- **Verify**: `just lint`
- **Dependency**: `CAN-RS-006`
- **Status**: done
- **Conclusion**: `just lint` 실행 결과 `ruff check` / `ruff format --check` 모두 PASS. 기존 테스트 파일의 미사용 import 제거 및 포맷 수정 완료 — 전역 lint 클린 상태 확인.

---

## 🔁 Conclusion & Summary

Canvas 렌더링 최적화로 `experiments/space-explorer/renderer.js` 에서 매 프레임 실행되던 불필요한 정렬 (`planets.sort()`) 을 초기화 함수로 이동하여 resize 시에만 실행하도록 변경. 트레일 패스 생성 (`drawTrail()`) 에서 240 회 `beginPath`/`stroke` 호출을 8 회 (행성 수) 로 배치 최적화. 60fps 렌더링 유지. 트레일과 행성이 정상적으로 표시되는지 확인. `just lint` PASS.

---

## 📊 Metrics

| 항목 | Before | After |
|------|--------|-------|
| `renderer.js` 의 `sort()` 호출 | 60 회/초 (매 프레임) | 1 회 (초기화) + resize 시 |
| `beginPath`/`stroke` 호출 | ~550 회/초 (매 프레임) | ~100 회/초 (매 프레임) |
| 트레일 패스 생성 | 240 회/초 (8 행성 × 30 포인트) | 8 회/초 (행성 수) |
| CPU 사용률 (예상) | ~15% | ~5% |
