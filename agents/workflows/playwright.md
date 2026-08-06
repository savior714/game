---
situation: 실제 브라우저에서 AidenGame 사용자 흐름 검증
level: Recommended
description: 운영 entry와 browser-generated input으로 상태·오류·요청 실패를 검증하는 Playwright workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Playwright workflow

브라우저 테스트 규칙은 [`testing/playwright.md`](../domains/testing/playwright.md)를 함께 따른다.

## 1. 사용 조건

- 사용자 흐름이 실제 DOM·focus·pointer·network timing에 의존함
- source test만으로 문제 identity나 state reset을 증명할 수 없음
- page error, request failure, redirect, static asset loading을 확인해야 함
- touch·keyboard·modal·overlay 동작을 검증해야 함
- 반복 실행으로 flake 여부를 판정해야 함

단순 pure function 또는 문서 drift를 브라우저로 검증하지 않는다.

## 2. scope 선택

사용자가 지정한 entry와 flow를 우선한다.
현재 일반 과목의 운영 entry는 다음과 같다.

- `domains/math/index.html`
- `domains/english/index.html`
- `domains/korean/index.html`
- `domains/science/index.html`

범위가 없으면 네 과목 공통 진단 또는 현재 failure domain의 가장 작은 흐름을 선택한다.
login, dashboard, backend API가 존재한다고 가정하지 않는다.

## 3. server와 browser

- repository root를 local HTTP server로 제공한다.
- fixed port보다 OS가 할당한 ephemeral port를 우선한다.
- server, thread, browser, context, page를 test 종료 시 정리한다.
- locale, timezone, viewport는 재현 조건에 필요한 경우 명시한다.
- 각 test가 storage isolation을 요구하면 새 context를 사용한다.
- 외부 network를 요구하지 않는 standalone flow에서 unexpected external request는 실패로 처리한다.

특정 browser automation CLI를 강제하지 않는다.
현재 세션과 저장소에서 지원되는 Playwright API 또는 browser tool을 사용한다.

## 4. 사용자 입력

- 실제 role, accessible name, stable ID, 현재 DOM contract에 맞는 locator를 사용한다.
- browser-generated mouse, keyboard, pointer input을 우선한다.
- production handler를 직접 호출해 핵심 입력 boundary를 건너뛰지 않는다.
- 내부 API 호출은 해당 API 자체가 검증 대상이거나 환경 설정에 필요한 경우에만 사용한다.
- selector는 실제 사용자 의미와 stability를 기준으로 선택하며 `data-testid`를 무조건 추가하지 않는다.

## 5. 오류 수집

필요한 test에서 다음을 수집한다.

- `pageerror`
- console error
- `requestfailed`
- 예상하지 않은 외부 request
- timeout 또는 무한 대기

허용 목록이 필요한 경우 구체적인 원인과 URL·message pattern을 계약으로 설명한다.
오류를 단순히 수집만 하고 assertion하지 않는 test를 만들지 않는다.

## 6. 일반 과목 공통 흐름

과목 completion 진단은 다음을 포함한다.

1. entry와 첫 문제 표시
2. 초기 answer/submit/next 상태
3. 정답 경로와 feedback
4. next 후 실제 question identity 변화
5. selection·style·feedback·disabled·focus reset
6. 오답 경로와 진행 가능성
7. 중복 click·key repeat 방지
8. 마지막 문제와 result
9. restart 후 fresh transient state
10. page error와 request failure 0건

반복 기준은 현재 product spec의 subject completion contract를 따른다.

## 7. 결과와 수정

- browser discovery만 요청받았다면 finding과 재현 경로를 보고하고 코드를 수정하지 않는다.
- 수정까지 요청받았다면 첫 failure domain 하나만 닫는다.
- 발견된 문제를 자동으로 Blueprint 파일로 만들지 않는다.
- screenshot이나 trace는 실제 시각·timing 증거가 필요할 때만 생성하며 repository source와 분리한다.

## 8. 완료

- 동일 flow가 반복 가능함
- assertion이 사용자 가시 상태 또는 실제 lifecycle을 검증함
- browser resource가 정리됨
- flake를 고정 sleep으로 숨기지 않음
- page error와 request failure 결과가 보고됨
- 실행하지 않은 browser flow를 PASS로 확대 해석하지 않음
