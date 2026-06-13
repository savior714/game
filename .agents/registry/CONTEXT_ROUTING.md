---
scope: registry
domain: core
---
<!-- Language: ko -->

# 🛣️ Context Routing Strategy

작업 파일 경로·키워드에 따라 에이전트 규칙(Instruction)을 로딩하는 **라우팅 테이블 SSOT**.

## 📌 컨텍스트 Tier (Context Budget SSOT)

IDE 플랫폼 선주입(Cursor T0 등)과 `just route` 읽기 용량을 분리한다.

| Tier | 시점 | 내용 | 예상 크기 |
| :--- | :--- | :--- | :--- |
| **T0** | IDE always-applied (Cursor 등) | 루트 `AGENTS.md` + `core/principles.md` + `core/error_patterns.md` 헤더 | ~6.7k tok (`just context-t0-estimate`) |
| **T1** | 세션 시작 (LOAD_ORDER Phase 1·3) | `PROJECT_RULES.md`, `MEMORY.md` 인덱스 | ~8k tok |
| **T1†** | lazy — Phase 2·ROADMAP | `LOAD_ORDER`, 본 문서, `docs/plans/ROADMAP.md` — 편집·`just route` / plan·roadmap·discuss·`just plan-preread` | 가변 |
| **T2** | `just route` / 편집 직전 | Always Load (full) + domain rules + skills | 가변 |
| **T3** | lazy | `SKILL_detail.md`, `error_patterns/detail/*.md`, `patterns.yaml`, `COMPILED.md` | on-demand |

**금지**: 벤더 `AGENTS.md` 파일명 (Cursor 전체 주입). `patterns.yaml` **always_apply 금지**. `vercel-react-best-practices` 풀 컴파일은 `COMPILED.md`.

**예산 CLI**: `just context-t0-estimate` · `just route-budget <paths> --target 8000 --json` · `just context-budget-validate`.

**스킬 카탈로그**: [SKILL_CATALOG.json](SKILL_CATALOG.json) — vendor `skills/vendor/**`는 `open-design-frontend` 경유.

**Cursor 플랫폼 T0 절감** (Reload Window, User Rules, Extension hooks): [DOC_cursor_context_budget.md](../../docs/ops/rules/DOC_cursor_context_budget.md).

---

## 📌 상시 적용 규칙 (Always Load — Tier T2, `just route --full`)

`just route` tight는 always-load 생략. `--full` 또는 편집 게이트 번들:

- `core/execution.md`, `core/verification.md`, `core/planning.md`, `core/reporting.md`
- `core/runtime_edit_tools.md` (tri-runtime 읽기·부분 수정·쓰기 스키마 — Cursor·OpenCode·Antigravity)
- `core/code_quality_lifecycle.md` (코드 편집·plan·review·테스트 — §0·§6 Cross-ref)
- `core/resilience.md`, `core/memory_hygiene.md`
- `core/error_patterns.md` 헤더 (TOP 3·메타 금지 8·detail 인덱스; TOP 4–7·WRONG/CORRECT는 detail lazy)
- `adaptive/*.md` (세션 종료·명시 트리거)

## 🗺️ 경로별 동적 매핑 (Path-based Loading)

| 파일 경로 패턴 (Glob) | 적용 규칙 파일 (Domain) | 용도 |
| :--- | :--- | :--- |
| `docs/**/*`, `.agents/**/*.md`, `README.md` | `documentation/markdown.md` | 한국어 정책, 문서 SSOT |
| `docs/plans/**/*` | `documentation/planning_docs.md` | Blueprint 및 계획 문서 작성 |
| `apps/renderer/**/*.{ts,tsx}` | `frontend/typescript.md`, `frontend/react.md`, `frontend/documentation.md` | renderer TS/React |
| `packages/**/*.{ts,tsx}`, `apps/desktop/**/*.{ts,tsx}`, `apps/server/**/*.ts` | `frontend/typescript.md`, `frontend/documentation.md` | 공유·desktop·server TS |
| `apps/renderer/src/stores/**/*.{ts,tsx}`, `apps/renderer/**/store/**/*.{ts,tsx}`, `apps/renderer/**/stores/**/*.{ts,tsx}`, `apps/renderer/**/store.ts` | `tech-stack/zustand.md` | zustand stores |
| `src/domain/**/*` | `backend/ddd.md` | DDD, Bounded Context, DI |
| `src/api/**/*`, `src/shared/models/**/*` | `backend/api_contracts.md` | API 명세, Pydantic 모델링 |
| `docker-compose.dev.yml`, `scripts/dev/docker_infra.sh`, `run_dev.sh` | `infra/docker.md` | Docker dev infra, Runtime Ports |
| `src/infrastructure/fhir/**/*`, `src/domain/models/fhir/**/*`, `src/shared/krcore/**/*` | `medical/fhir.md` | FHIR R4, KR Core 표준 |
| `src/security/**/*`, `vault/**/*` | `medical/emr_security.md` | Vault, Encryption, Audit |
| `scripts/**/*seed*`, `**/seed*.py`, `src/infrastructure/**/*seed*` | `infra/seeding.md` | CSV 시딩, 인코딩 fallback |
| `tests/**/*`, `**/test_*.py` | `testing/tdd.md` | TDD Red-First, Test Logic |
| `tests/e2e/**/*`, `**/*.spec.ts` | `testing/playwright.md` | Playwright, Browser Testing |

## 프로젝트 스킬 (기계 라우팅)

Glob·의도 매핑 **단일 SSOT**: [PROJECT_SKILL_ROUTING.json](PROJECT_SKILL_ROUTING.json) (open-design-frontend 등 — 위 Path 표 domain 열에 `SKILL.md` 넣지 않음). 편집 전 `just route <paths> --json` **`must_read`** — [execution.md](../core/execution.md) §2.8. Blueprint 선행 Read: `just plan-preread` · OHT: [planning.md](../core/planning.md) §0.

**skill cap (tight 2)**: `packages/ui-*/**/*.{ts,tsx}` → design + a11y 우선 · `typescript-advanced-types`는 **의도적 탈락** (복잡 타입은 `packages/shared`·`apps/server`). cap 상향은 다이어트 역효과 — renderer `page.tsx`와 동일 논쟁 방지.

**error_patterns detail lazy-load**: [error_patterns.md](../core/error_patterns.md) detail 인덱스 — `just route`가 경로별 `detail/*.md`를 `must_read`에 추가.

**2단계 스킬 lazy-load**: `SKILL.md`(헤더) + `SKILL_detail.md`(본문). `route_context.py`가 `lazy_load`/`detail_path` 부여. **금지**: detail만 읽고 헤더 생략. 매핑: [PROJECT_SKILL_ROUTING.json](PROJECT_SKILL_ROUTING.json).

---

## 📒 세션 Route 매니페스트 (멀티 에이전트)

`just route` / `just route-smart` JSON 번들·필독·편집 전 검증 — [routing.md §2](../core/routing.md). 파일: `.agent/route/session-manifest.json` (`ROUTE_MANIFEST_PATH`). 엔진: `scripts/agent/route_gate.py`.

---

## ⚡ 키워드 · 슬래시 (수동 자기 규제)

**카탈로그 SSOT**: [WORKFLOW_AND_SKILL_INDEX.md](WORKFLOW_AND_SKILL_INDEX.md) 「워크플로」「키워드 → Read」「프로세스 · 인지 스킬」. **기계 intent**: [PROJECT_SKILL_ROUTING.json](PROJECT_SKILL_ROUTING.json) `intent_routes` (`just route-smart`).

---

**docs 지형**: [docs/README.md](../../docs/README.md) (6통 SSOT).

**우선순위**: [AGENTS.md §0](../../AGENTS.md) — `PROJECT_RULES` > `AGENTS` > 경로 매핑 > core.

---
**세션 시작 vs lazy**: [LOAD_ORDER.md](LOAD_ORDER.md) Phase 2·ROADMAP lazy — 본 문서 Glob·Tier 표는 **편집·route 직전**에 Read.

**Last Updated**: 2026-06-07
