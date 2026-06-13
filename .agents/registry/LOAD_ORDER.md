---
scope: registry
domain: core
---
<!-- Language: ko -->

# 📋 Load Order & Precedence

세션 **시작·로딩·종료** 절차와 규칙 Phase 순서의 **단일 SSOT**. 실행 게이트·검증·우선순위는 `AGENTS.md` · `.agents/core/*.md`.

---

## Phase 로딩 순서

| Phase | 시점 | 내용 |
| :--- | :--- | :--- |
| **1** | 세션 시작 | `PROJECT_RULES.md`, `AGENTS.md` (플랫폼 T0와 중복 pointer). OpenCode: `opencode.json` → 추가로 `opencode_tools.md` |
| **2** | **lazy** — 편집·`just route` / `route-smart` 직전 | 본 문서, [CONTEXT_ROUTING.md](CONTEXT_ROUTING.md) |
| **3** | 세션 시작 | `docs/agent-context/memory/MEMORY.md` 인덱스(≤200줄). **`ROADMAP.md` lazy** — plan·roadmap·discuss·`just plan-preread` |
| **4** | `--full` / 편집 직전 | CONTEXT_ROUTING 「Always Load T2」`core/*.md` · 필요 시 `adaptive/*.md`. **tight**는 `must_read`만 |
| **5** | 편집 대상 확정 | `just route <paths> --json` → domain · skills ([CONTEXT_ROUTING](CONTEXT_ROUTING.md)) |
| **6** | 슬래시·워크플로 | `.agents/workflows/<name>.md` |
| **7** | 종료·명시 트리거 | `adaptive/self_evolution.md` 등 |

**Cursor T0** (플랫폼 주입): `principles.md` + `error_patterns.md` 헤더 `always_apply: true` — tight 번들과 **별개**.

**세션 시작 SSOT**: `PROJECT_RULES.md` + `MEMORY.md` 인덱스 (`AGENTS.md`는 T0). Phase 2·`ROADMAP.md`는 lazy.

**첫 응답**: 위 세션 시작 SSOT. 코드·문서 편집 착수 전 Phase 2 Read. 선읽기(권장): `just route-smart '<요약>' <paths> --json --full --write-manifest --phase turn1`. 슬래시·키워드·AskQuestion(`question` 병용): [principles.md](../core/principles.md) §1.1 · [CONTEXT_ROUTING.md](CONTEXT_ROUTING.md) (Phase 2 lazy).

**멀티 에이전트**: `ROUTE_MANIFEST_PATH` · `ROUTE_SESSION_KEY`. **필수 파일 부재**: 사용자 보고 — 거버넌스 placeholder 생성 금지.

### 편집 직전 (Phase 5 실무)

**`just route <paths> --json --write-manifest` → `must_read` 전량 Read → `just route-read` → `just route-gate-check`** — [execution.md](../core/execution.md) §2.8 · [CONTEXT_ROUTING.md](CONTEXT_ROUTING.md) 「Route 매니페스트」. `just route` 직후 `--` 금지.

**편집 실패 시**: 같은 old/target 재시도·도구 자동 전환 금지 — [runtime_edit_tools.md](../core/runtime_edit_tools.md) · [routing.md](../core/routing.md) §1 · [error_patterns.md](../core/error_patterns.md).

### 종료 (저장소 수정 후)

[reporting.md](../core/reporting.md) §1.0: `just lint-turn-end` → [memory_hygiene.md](../core/memory_hygiene.md). 매니페스트 없으면 route gate skip. `ROUTE_GATE_SKIP=1` 가능.

### 규칙 정합성

레지스트리 상충·깨진 참조 → `docs/agent-context/memory/changelog/` 또는 Blueprint. `MEMORY.md` Consistency Issues는 제품·환경 이슈 전용.

**충돌 해결**: [AGENTS.md §0](../../AGENTS.md). Phase는 로딩 순서이며 우선순위를 재정의하지 않음. Domain 간 충돌: 더 specific한 Glob 우선.
