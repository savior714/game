---
scope:
- tests/e2e/**/*
- '**/*.spec.ts'
- .playwright-mcp/**/*
always_apply: false
priority: normal
description: "Playwright E2E \uD14C\uC2A4\uD2B8 \uBC0F \uC790\uB3D9 \uBB38\uC81C \uBC1C\
  \uACAC \uADDC\uCE59"
domain: playwright
verify_with:
- just test-frontend
---
<!-- Language: ko -->

# Playwright & Browser Testing Rules

## MUST
- **UI Discovery**: UI 변경이나 버그 발견 시 브라우저 자동화 도구를 활용하여 실제 페이지 상태를 스캔하고 문제점을 기록한다.
- **Blueprint Integration**: `/playwright` 워크플로우를 통해 발견된 이슈는 반드시 `docs/plans/`의 Blueprint로 전환하여 관리한다.
- **Stable Selectors**: 테스트 작성 시 텍스트나 깨지기 쉬운 CSS selector 대신 `data-testid` 또는 역할(Role) 기반 locator를 우선 사용한다.

## MUST NOT
- **Manual Repetition**: 수동으로 브라우저를 반복 조작하여 확인하는 것을 지양하고, 가능한 한 자동화된 스크립트로 재현 경로를 확보한다.
- **Flaky Asserts**: 네트워크 지연이나 애니메이션을 고려하지 않은 즉각적인 Assertion 사용을 금지한다 (`waitFor` 활용).
