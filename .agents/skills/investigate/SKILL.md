---
name: investigate
description: "Investigate bugs and failures systematically"
---

<!-- Language: ko -->

# Investigate Skill

## Purpose

Investigate bugs and failures systematically.

Goal:

* identify root cause
* avoid speculative fixes
* isolate failure conditions
* produce reproducible understanding

---

# Response Language (MUST)

**이 스킬이 활성화된 세션의 모든 채팅 응답은 한국어로 작성한다.**

- 증상·재현·근본 원인·수정 전략·회귀 위험 등 **진단 보고 전체**를 한국어로 쓴다.
- 코드 식별자·로그·스택 트레이스·CLI·파일 경로는 영문을 유지해도 된다.
- **영문 단락·영문-only 요약·영문-only 결론은 금지**한다. (기술 용어 한 단어는 허용)
- Investigation Output Format(아래)의 **섹션 제목·본문** 모두 한국어를 따른다.
- 정책 SSOT: [markdown.md](../../domains/documentation/markdown.md) **Korean First Policy**, [reporting.md](../../core/reporting.md) §1.6

---

# Iron Law

NEVER implement fixes before identifying root cause.

Do not patch symptoms blindly.

---

# Investigation Workflow

## Step 1 — Reproduce
First reproduce the issue consistently.

Identify:

* exact trigger
* environment
* sequence of actions
* frequency

If issue cannot be reproduced:
* gather more signals
* add logging
* isolate variables

Do not guess.

---
## Step 2 — Isolate

Reduce problem scope.

Determine:
* where failure begins
* what changed recently
* whether issue is deterministic
* whether issue is state-dependent

Use:
* logs
* stack traces
* diffs
* binary search
* instrumentation

---
## Step 3 — Trace

Trace:

* data flow
* state transitions
* async behavior
* network interactions
* rendering lifecycle
* persistence boundaries

Verify assumptions directly in code.

---


Create hypothesis only AFTER evidence collection.

For each hypothesis:

1. supporting evidence
2. contradictory evidence
3. validation method

Reject weak hypotheses quickly.

---
## Step 5 — Verify Root Cause

Before fixing, confirm:

* root cause fully explains symptom
* reproduction matches explanation
* proposed fix addresses actual cause

---


If 3 fix attempts fail:

* stop patching
* reassess architecture/design assumptions
* investigate systemic issues

Do not continue random edits.

---
# Debugging Principles

## Prefer observation over guessing

Bad:

* "maybe this fixes it"

Good:

* "state becomes null here because X"

---
## Prefer minimal experiments

Make small controlled changes.

Avoid:

* broad rewrites
* shotgun debugging
* multiple simultaneous fixes

---
## Preserve Signal

Do not:

* remove logs too early
* suppress exceptions
* hide symptoms

Preserve evidence.

---

# Domain-Specific Diagnostic Signals

## Next.js Fast Refresh Full Reload as Diagnostic Signal

`⚠ Fast Refresh had to perform a full reload` is **not just a warning** — it's a diagnostic signal about component architecture:

- **Triggers when**: Fast Refresh cannot hot-reload a module because of structural changes in the component tree, state loss during HMR, or client components inside layouts with side-effect hooks
- **What it tells you**: Look at the component that changed — is it a layout? Does it contain client components with `useEffect` redirect guards, event listeners, or ResizeObservers?
- **Common root cause**: Auth state transition during hydration (isLoading→isAuthenticated) in a client component nested inside layout
- **Investigation path**: Check `layout.tsx` → client component imports → useEffect redirect guards → auth context initialization timing

See also: [Next.js Fast Refresh](https://nextjs.org/docs/architecture/fast-refresh)

## React Render Cascade Freezing

환자 전환, 데이터 변경 후 UI가 멈추는 현상은 **렌더링 캐스케이드**가 원인일 수 있습니다.

- **Triggers when**: `useMemo` 컨텍스트 객체의 의존성 배열이 과도하게 넓음 (20개 초과), `useDeferredValue`가 부분만 적용됨
- **What it tells you**: `widgetBinderContext`, `examination` 훅, `contentProps` 등 큰 `useMemo` 객체의 의존성 배열 길이를 확인
- **Common root causes**:
  - A1. 거대 컨텍스트 객체 (~60개 의존성) → 모든 하위 컴포넌트가 리렌더됨
  - A2. `useDeferredValue` 부분 적용 (patientId만 defer, selectedPatient은 즉시 렌더)
  - A3. Hook 참조 불안정 (`useMemo` spread 하위 훅 → 하나 변경 시 전체 recompute)
  - A4. 동기 Effect 블록 (`useLayoutEffect` 내 JSON.stringify 등 메인 스레드 차단)
- **Investigation path**: `investigate` → [vercel-react-best-practices](../frontend/vercel-react-best-practices/SKILL.md) §5 Re-render Optimization 참고 → Step 2~6 진행

---
# Investigation Output Format

> **언어**: 아래 섹션 제목·본문은 **반드시 한국어**로 작성한다. 코드·로그 인용만 영문 허용.

## 증상 (Symptom)

무엇이 실패하는가?

## 재현 (Reproduction)

어떻게 재현하는가?

## 근본 원인 (Root Cause)

왜 발생하는가?

로그 / 트레이스 / 코드 경로

## 수정 전략 (Fix Strategy)

최소한의 수정 방향

## 회귀 위험 (Regression Risk)

무엇이 추가로 깨질 수 있는가?

---

# Final Rule

A clean diagnosis is more valuable than a fast blind fix.

Use logging and instrumentation before broad code modification.

**최종 보고도 한국어로 마무리한다.** (Response Language MUST 준수)