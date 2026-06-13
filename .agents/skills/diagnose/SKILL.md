---
name: diagnose
description: >
  Hard-bug discipline — build a fast feedback loop first, then six phases
  (reproduce → hypothesise → instrument → fix + regression test → cleanup).
  Use for /diagnose, debugging, performance regressions, and flaky failures.
license: MIT
metadata:
  version: "1.0.0"
---

<!-- Language: ko -->

# Diagnose

A discipline for hard bugs. Skip phases only when explicitly justified.
When exploring the codebase, use the project's domain glossary to get a clear mental model of the relevant modules, and check ADRs in the area you're touching.

---

# Response Language (MUST)

**이 스킬이 활성화된 세션의 모든 채팅 응답은 한국어로 작성한다.**

- Phase별 진행 보고·가설 목록·계측 결과·수정 요약·사후 분석 등 **진단 보고 전체**를 한국어로 쓴다.
- 코드 식별자·로그·스택 트레이스·CLI·파일 경로·`[DEBUG-...]` 태그는 영문을 유지해도 된다.
- **영문 단락·영문-only 요약·영문-only 결론은 금지**한다. (기술 용어 한 단어는 허용)
- Diagnose Output Format(아래)의 **섹션 제목·본문** 모두 한국어를 따른다.
- 정책 SSOT: [markdown.md](../../domains/documentation/markdown.md) **Korean First Policy**, [reporting.md](../../core/reporting.md) §1.6

---

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause — bisection, hypothesis-testing, and instrumentation all just consume that signal. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — try them in roughly this order

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright / Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace.** Save a real network request / payload / event log to disk; replay it through the code path in isolation.
6. **Throwaway harness.** Spin up a minimal subset of the system (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" so you can `git bisect run` it.
9. **Differential loop.** Run the same input through old-version vs new-version (or two configs) and diff outputs.
10. **HITL bash script.** Last resort. If a human must click, drive _them_ with a structured checklist script so the loop is still structured. Captured output feeds back to you.

Build the right feedback loop, and the bug is 90% fixed.

### Iterate on the loop itself

Treat the loop as a product. Once you have _a_ loop, ask:

- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

A 30-second flaky loop is barely better than no loop. A 2-second deterministic loop is a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; 1% is not — keep raising the rate until it's debuggable.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to whatever environment reproduces it, (b) a captured artifact (HAR file, log dump, core dump, screen recording with timestamps), or (c) permission to add temporary production instrumentation. Do **not** proceed to hypothesise without a loop.

Do not proceed to Phase 2 until you have a loop you believe in.

## Phase 2 — Reproduce

Run the loop. Watch the bug appear.

Confirm:

- [ ] The loop produces the failure mode the **user** described — not a different failure that happens to be nearby. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, reproducible at a high enough rate to debug against).
- [ ] You have captured the exact symptom (error message, wrong output, slow timing) so later phases can verify the fix actually addresses it.

Do not proceed until you reproduce the bug.

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly ("we just deployed a change to #3"), or know hypotheses they've already ruled out. Cheap checkpoint, big time saver. Don't block on it — proceed with your ranking if the user is AFK.

## Phase 4 — Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:

1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch.** For performance regressions, logs are usually wrong. Instead: establish a baseline measurement (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

**AidenGame — hub raw JSONL (LLM/API format mismatch):** Before type casts or defensive `get()` patches, read raw responses:

1. `just api-response-errors` → `var/log/emr/hub/api_response_errors.jsonl`
2. `just raw-logs` → `api_log.jsonl`, `tool_log.jsonl`

SSOT: [diagnose.md](../../workflows/diagnose.md) AidenGame 부록 · [execution.md](../../core/execution.md) §3.5.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (single-caller test when the bug needs multiple callers, unit test that can't replicate the chain that triggered the bug), a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. Flag this for the next phase.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

## Phase 6 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location)
- [ ] The hypothesis that turned out correct is stated in the commit / PR message — so the next debugger learns
- [ ] **Material Impact 디버깅**(아키텍처·환경·추측 패치 회피 궤적)이면 `/ai-log` Golden Log 검토 — `success=false`·`failure_category`·`root_cause` 포함 ([cognitive_logging.md](../../adaptive/cognitive_logging.md))

**Then ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling) hand off to **improve-codebase-architecture** (`.agents/skills/improve-codebase-architecture/SKILL.md`) with the specifics. Make the recommendation **after** the fix is in, not before — you have more information now than you started.

### Agent tool mistake → error_patterns (MUST)

When the **root cause** was an **agent tool or edit-discipline** failure — not application/runtime logic — complete this **before** declaring diagnose done:

- bump 전 [`.agents/core/error_patterns.md`](../../core/error_patterns.md) 상단 «메타 금지 7» 절을 먼저 읽는다.

- [ ] **MUST** register or refresh: `just error-pattern-add "<name>" "<symptom>" "<cause>" "<fix>"`. If the same **name** already exists in [`.agents/core/error_patterns.md`](../../core/error_patterns.md), re-run add with that name to **bump** `occurrence_count` / `last_seen` (do not add a duplicate section).
- [ ] Keep editor-mistake prose in **error_patterns** SSOT; do not copy the same pattern into RES or knowledge-asset.

**Judgment — treat as tool mistake if any one applies:**

1. **Edit-tool chain** — patch uniqueness not checked, patch failed then same old/target retried without re-read, read → full-write overwrite, regex/newline corruption, or JSX patch stack damage (see [runtime_edit_tools.md](../../core/runtime_edit_tools.md), error_patterns §1–§4).
2. **Gate skip** — edit before `just route-gate-check`, implementation before `just plan-lint` PASS, or line-number / `grep -n`-only patch despite AGENTS.md editing rules.
3. **Repeat pattern** — same symptom again in-session, or clear match to a named pattern in error_patterns (bump; do not invent a near-duplicate name).

If **none** apply, use [RES_COMMON_ERROR_RESOLUTIONS.md](../../../docs/knowledge/RES_COMMON_ERROR_RESOLUTIONS.md) for **runtime** symptoms and [knowledge-asset](../knowledge-asset/SKILL.md) for durable **product/code** knowledge — not for editor mistakes.

### Phase 6.5 — Spec sync (post-fix doc drift gate)

If the fix touched **routes**, **`next.config`**, **`proxy.ts`**, **auth/cookie middleware**, or any **Blueprint/Plan Conclusion** that records a technical choice:

- [ ] Run **Unified Sync** (`.agents/skills/sync/SKILL.md`, workflow `.agents/workflows/sync.md`): Claim Inventory → `just sync --check` → Phase 2 본문 갱신 → PASS.
- [ ] When the renderer dev server is up: `just renderer-route-smoke` (catches “build passes, all routes 404” misconfigs such as wrong `pageExtensions`).
- [ ] Supersede or correct stale Plan Conclusions before `knowledge-asset` 자산화 검토.

---

# Diagnose Output Format

> **언어**: 아래 섹션 제목·본문은 **반드시 한국어**로 작성한다. 코드·로그 인용만 영문 허용.

Phase 진행 중·완료 시 채팅 보고는 필요한 섹션만 골라 쓰되, **항상 한국어**로 작성한다.

## 증상 (Symptom)

무엇이 실패하거나 느려졌는가?

## 피드백 루프 (Feedback Loop)

어떤 pass/fail 신호로 재현·검증하는가?

## 가설 (Hypotheses)

Phase 3 — 순위별 가설과 각각의 **반증 가능한 예측** (한국어 서술)

## 근본 원인 (Root Cause)

계측·증거로 확정된 원인

## 수정 (Fix)

적용한 최소 수정 + 회귀 테스트 여부

## 사후 분석 (Post-mortem)

무엇을 정리·제거했는가, 다음에 막을 수 있는 구조적 개선이 있는가

---

# Final Rule

**최종 보고도 한국어로 마무리한다.** (Response Language MUST 준수)
