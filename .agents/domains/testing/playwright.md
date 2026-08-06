---
scope:
- tests/**/*browser*.py
- tests/**/test_*browser*.py
- '**/*.spec.ts'
always_apply: false
priority: normal
description: AidenGame 실제 브라우저 흐름과 오류 수집 규칙
domain: playwright
last_verified: 2026-08-06
verify_with:
- uv run pytest -q <focused-browser-test>
---
<!-- Language: ko -->

# Playwright와 브라우저 테스트 규칙

상위 workflow는 [`playwright.md`](../../workflows/playwright.md)다.

## MUST

- 실제 운영 entry를 local HTTP server로 연다.
- 핵심 흐름은 browser-generated mouse, keyboard 또는 pointer input으로 실행한다.
- 사용자 가시 상태와 실제 state transition을 함께 확인한다.
- 필요한 흐름에서 `pageerror`와 `requestfailed`를 수집하고 assertion한다.
- fixed sleep보다 locator expectation, state predicate, event를 사용한다.
- server, thread, browser, context, page를 종료한다.
- storage isolation이 필요한 test는 독립 context를 사용한다.
- flake 판정이 계약이면 동일 flow를 명시된 횟수만큼 반복한다.

## SHOULD

- role과 accessible name이 안정적이면 우선 사용한다.
- 현재 DOM contract에 안정적인 ID가 있으면 사용할 수 있다.
- question progression은 counter만이 아니라 question identity 또는 의미 있는 content 변화로 확인한다.
- next 진입 후 answer selection, feedback, style, disabled, focus 상태가 초기화되는지 확인한다.
- standalone flow에서는 unexpected external request를 수집한다.
- viewport·locale·timezone이 재현에 영향을 주면 fixture에 고정한다.

## MUST NOT

- 발견된 모든 문제를 자동으로 `docs/plans/` Blueprint로 만들지 않는다.
- login, dashboard, backend API 같은 존재하지 않는 route를 기본 scope로 가정하지 않는다.
- production handler를 직접 호출해 검증할 사용자 입력 boundary를 우회하지 않는다.
- 고정 sleep을 늘려 race나 lifecycle bug를 숨기지 않는다.
- console·network 오류를 수집만 하고 assertion 없이 버리지 않는다.
- 깨지기 쉬운 nth-child selector를 사용자 의미가 있는 locator 대신 선택하지 않는다.
- 실제 browser flow 한 번의 PASS를 과목 전체 완료로 확대 해석하지 않는다.

## 일반 과목 최소 관찰값

- first question visible and nonblank
- correct and incorrect path
- next control state
- actual question change
- per-question transient state reset
- final result
- restart freshness
- page error count
- request failure count

현재 과목별 완료 기준은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`를 따른다.
