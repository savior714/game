---
scope:
- '*'
always_apply: false
priority: 1
domain: core
verify_with:
- just prevent-tech-debt
- just ddd-gate
- just fe-boundary-gate
- just fe-function-length-gate
- just fe-complexity-gate
- just test-coupling-gate
- just test-internal-mock-gate
---
<!-- Language: ko -->

# Code Quality Lifecycle — 설계·구현·리뷰·강제·테스트

코드 품질 점검을 **시점별**로 묶은 normative SSOT입니다. 세부 도구·게이트는 각 절의 Cross-ref를 따릅니다.

> **용어 — Mock**: 본 문서 **Mock** = 테스트 더블(stub/spy/fake). **DB 시드·fixture**는 [seeding.md](../domains/infra/seeding.md). **`dependency_overrides`** = FastAPI composition root 교체(T-2 허용) — 내부 함수 patch와 구분.

---

## 0. 적용 순서

| 단계 | 시점 | SSOT |
| :--- | :--- | :--- |
| 1 | **설계** (`/plan`, Blueprint) | §1 |
| 2 | **구현** (코드 편집; Red-first 테스트 **병행**) | §2 · §5 |
| 3 | **CI·lint** (항상·완료 전) | §4 |
| 4 | **리뷰** (`/review`, PR) | §3 |

**실무 한 사이클**: 설계 → 엣지케이스 Red 테스트 → 구현 Green → `just lint-fe` / `just lint-be` → 리뷰.

> §4(강제)는 2·3·4 전 단계에서 **우회 불가**하게 동작한다.

---

## 1. 설계 시점 (Design Gate)

Blueprint·아키텍처 결정 **전** 확인합니다. 상세: [planning.md](planning.md) §0 · [ddd.md](../domains/backend/ddd.md).

### MUST

| ID | 규칙 | 실무 |
| :--- | :--- | :--- |
| **D-1** | **모듈·레이어 경계를 먼저 적는다** | Task `Target`·`Architectural Goal`에 레이어(`domain` / `application` / `features` / `components`)와 허용 의존 방향을 명시. import graph spot-check — [planning.md §0](planning.md) Target Path SSOT Gate |
| **D-2** | **의존성은 lint·스캐너로 기계 검증** | BE: `just be-boundary-gate` · `just ddd-gate` · `runtime_coupling_scan --check`. FE: `just fe-boundary-gate` · `just lint-fe` |
| **D-3** | **공용 유틸·타입·shape SSOT 선지정** | 신규 shape 전 `rg`/Glob으로 기존 타입·매퍼·ViewModel 검색. specs > packages/shared > domain types 우선 — 중복 DTO·parallel type 금지 |
| **D-4** | **디렉터리 위계로 의존 방향을 눈에 보이게** | BE: `main → application → domain ← infrastructure`. FE: `apps/renderer/src/features/<domain>/` · `components/` · `hooks/` — 상위가 하위 UI leaf에 직접 침범하지 않도록 Task 범위를 레이어 단위로 쪼갬 |

### MUST NOT

- 경계·SSOT 없이 "일단 파일 추가" Task 작성
- Blueprint `Target`에 코드베이스 미존재 경로 기재 ([planning.md §0](planning.md) blocked 처리)

---

## 2. 구현 시점 (Implementation Gate)

코드 작성·수정 **중** 확인합니다. 상세: [execution.md](execution.md) §2 · [principles.md](principles.md) §1.2–§1.3.

### MUST

| ID | 규칙 | 실무 |
| :--- | :--- | :--- |
| **I-1** | **에러는 경계·핸들러에서만 처리** | 빈 `catch`/`except: pass` 금지. FE: BP-TS-005* · BE: BP-PY-001/002* — `just lint-fe` / `just lint-be` incremental |
| **I-2** | **중첩 3단계 초과 시 평탄화** | `if`/`for`/`switch` 중첩 3단계 넘으면 early return·guard clause로 재구성. Biome cognitive complexity ≤15 목표 — [biome.json](../../biome.json) |
| **I-3** | **함수·파일 크기 상한 준수** | 파일 **500줄** — `just prevent-tech-debt`. 함수 **100줄** — `just fe-function-length-gate` (baseline incremental) |
| **I-4** | **엣지케이스를 happy path보다 먼저 테스트** | Red-first 시 **빈 입력·null·경계값·동시성·실패 경로** 테스트를 먼저 작성. side-effect(저장·발행·라우팅) assertion 포함 — §5 |
| **I-5** | **신규 function·helper·shape 전 검색** | `rg`/Glob/기존 deep module 우선. pass-through helper·중복 타입 추가 금지 — [improve-codebase-architecture/SKILL.md](../skills/improve-codebase-architecture/SKILL.md) deletion test |

### MUST NOT

- 테스트 통과·lint 회피를 위해 production에 방어 코드 추가 ([tdd.md](../domains/testing/tdd.md) Test Self-Repair)
- I등급(500줄+) 파일 본문 확장 — 분할 Blueprint 선행 ([principles.md §1.3](principles.md))

---

## 3. 리뷰 시점 (Review Gate)

`/review`·PR에서 diff 기준 확인합니다. 상세: [review/SKILL.md](../skills/review/SKILL.md).

### MUST (구조·결합)

| ID | 점검 | 실패 신호 |
| :--- | :--- | :--- |
| **R-1** | **대체 지점에 중복·죽은 코드 없음** | 기존 함수/컴포넌트 옆 parallel 구현, 주석 처리 블록, unused export |
| **R-2** | **조용히 삼킨 에러 없음** | empty catch, `catch { }`, 실패 시 `undefined` 반환만 하고 UI 무반응 |
| **R-3** | **숨은 결합 없음** | 암묵 계약(초기화 순서·전역 mutable·모듈 load side effect), cross-layer import |
| **R-4** | **re-export 정리** | barrel(`index.ts`)이 순환·깊은 re-export chain 유발, public API와 내부 구현 혼재 |
| **R-5** | **fan-in/fan-out 집중 없음** | 단일 파일·함수에 N개 도메인 로직이 몰림 — [improve-codebase-architecture/SKILL.md](../skills/improve-codebase-architecture/SKILL.md) shallow module |

리뷰는 evidence(실행 경로·줄 번호·실패 시나리오) 필수 — 추측 코멘트 금지.

---

## 4. CI·Lint 강제 (Enforcement)

에이전트·CI가 **우회 불가**하게 막는 항목입니다.

| ID | 규칙 | 검증 |
| :--- | :--- | :--- |
| **E-1** | **Strict 타입** | `as any` · `: any` · `catch (e: any)` — BP-TS-001* (**변경 파일 전체** incremental). `as unknown as` — BP-TS-004* (**diff-added-lines**; untracked 신규 파일은 **전체** 검사). 불가피 시 직전 줄 `biome-ignore` + 사유 |
| **E-2** | **순환·경계·결합 CI** | `just verify`(ddd) · CI `runtime_coupling_scan --check` · `just test-coupling-gate` |
| **E-3** | **복잡도·중첩 lint** | Biome complexity ≤15 · `just fe-function-length-gate`(100줄/함수) · Ruff PLR0912/0915 · §2 I-2 guard clause |

### MUST NOT

- `@ts-ignore` · `biome-ignore`로 E-1·E-3 영구 우회 (Tier 4 complexity는 별도 Blueprint + TODO 주석만 허용)
- gate severity 하향(`error → warn`) — [execution.md §2.2](execution.md)

---

## 5. 테스트 시점 (Test Gate)

상세: [tdd.md](../domains/testing/tdd.md).

### MUST

| ID | 규칙 | 실무 |
| :--- | :--- | :--- |
| **T-1** | **문자열이 아니라 행동을 검증** | DOM 텍스트 스냅샷·커버리지 숫자만으로 Green 선언 금지. 상태 변화·콜백·side-effect·API contract assertion |
| **T-2** | **Mock은 외부 경계에서만** | HTTP·DB·clock·파일 I/O·외부 SDK만 stub/spy. **내부 모듈·private helper mocking 금지** — SUT 인터페이스로 검증. FastAPI `dependency_overrides`는 **앱 경계** DI 교체로 허용 |
| **T-3** | **엣지케이스를 테스트로 고정** | 빈 입력·null·경계값·실패·타임아웃 경로를 named test case로 유지 — 회귀 방지 |
| **T-4** | **테스트 맞춤 production 방어 코드 금지** | Green을 위해 SUT에 null guard·silent fallback 추가하지 않음 — 테스트 전제 수정 또는 SUT 버그 수정 |
| **T-5** | **테스트 메시지 전역 고유성 확보** | `@testing-library/react` 등에서 중복 텍스트 매칭 오류(Found multiple elements) 방지를 위해 고유 식별자(예: "적정" X → "상병 S50.000 일치" O)를 포함하거나 `getAllByText` / `data-testid` 등을 명시적으로 사용 — [AGENTS.md §4.2](../../AGENTS.md#42-test--메시지-전역-고유성) |

### Mock vs DB Mock (구분)

| 개념 | 의미 | SSOT |
| :--- | :--- | :--- |
| **테스트 Mock (본 문서)** | 외부 의존을 테스트 더블로 대체 | §5 T-2 |
| **DB Mock / 시드** | 개발·E2E용 fixture·CSV 시드·in-memory DB | [seeding.md](../domains/infra/seeding.md) |
| **dependency_overrides** | FastAPI 앱 **composition root**에서 서비스 교체 | API 테스트 경계 — 내부 함수 patch 아님 |

---

## 6. Cross-ref 요약

| 시점 | SSOT |
| :--- | :--- |
| 설계 | [planning.md](planning.md) · [ddd.md](../domains/backend/ddd.md) |
| 구현 | [execution.md](execution.md) · [principles.md](principles.md) |
| 리뷰 | [review/SKILL.md](../skills/review/SKILL.md) |
| 강제 | [typescript.md](../domains/frontend/typescript.md) · [verification.md](verification.md) |
| 테스트 | [tdd.md](../domains/testing/tdd.md) |

---

## 7. Enforcement Map (기계 검증 SSOT)

| 항목 | 명령 | Baseline | 신규 위반 |
| :--- | :--- | :--- | :--- |
| FE `as unknown as` / 빈 catch | `just lint-fe` (bp_linter BP-TS-004/005) | diff-added-lines | FAIL |
| BE `except: pass` | `just lint-be` (bp_linter BP-PY-001/002) | diff-added-lines | FAIL |
| FE 함수 100줄 초과 | `just fe-function-length-gate` | `frontend_function_length_baseline.txt` | FAIL |
| FE cognitive complexity >15 | `just fe-complexity-gate` | `frontend_complexity_baseline.txt` | FAIL |
| BE import graph (S1–S4) | `just be-boundary-gate` | `backend_boundary_baseline.txt` | FAIL |
| FE import graph (S5–S12) | `just fe-boundary-gate` | `frontend_boundary_baseline.txt` | FAIL |
| BE runtime 역결합 R1 | `just runtime-coupling-gate` | `runtime_coupling_baseline.txt` | FAIL |
| BE 함수 100줄 초과 | `just be-function-length-gate` | `backend_function_length_baseline.txt` | FAIL |
| DDD 통합 게이트 | `just ddd-gate` (= be + fe boundary) | 위 baseline 공유 | FAIL |
| 테스트 결합 Critical/High | `just test-coupling-gate` | `test_coupling_baseline.txt` | FAIL |
| FE 테스트 내부 mock (T-2) | `just test-internal-mock-gate` (CI) | `test_internal_mock_baseline.txt` | FAIL |
| 파일 500줄 | `just prevent-tech-debt` | git diff hard scope | FAIL |
| Biome max-depth | — | 없음 | `fe-complexity-gate` + guard clause(I-2) |

Baseline 갱신(리뷰 후): `--update-baseline` 플래그 — [GUIDE_quality_baseline_gates.md](../../docs/ops/rules/GUIDE_quality_baseline_gates.md) · 각 gate 스크립트 docstring.

**SSOT 정합 (2026-06-10)**: `just fe-quality-gates` / `just be-quality-gates`가 `just lint` · `lint-fe` · `lint-be` · `just ci` · `verify.sh`에서 동일 baseline gate를 공유한다(FE: `fe-boundary-gate` S5–S12, BE: `be-boundary-gate` + `runtime-coupling-gate`). `just ddd-gate` = be + fe boundary 위임. BP-TS/BP-PY incremental bp_linter는 **로컬 dirty tree**용 — CI `verify`에는 baseline gate만 포함(bp_linter full-scan 회피).
