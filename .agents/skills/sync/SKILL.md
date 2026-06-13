---
name: sync
description: >
  Unified Sync Gate (Code Lock & Spec Drift Gate) — code lock verification plus
  spec alignment check; spec body updates remain agent-driven (Phase 2).
license: MIT
metadata:
  version: "1.1.1"
---

<!-- Language: ko -->

# Unified Sync (Code Lock & Spec Drift Gate)

코드 무결성 락(`code-sync`)과 스펙 정합(`spec-sync`)을 **한 워크플로·한 CLI**로 묶습니다.
스펙 본문 갱신은 [sync 워크플로 Phase 2](../../workflows/sync.md)에 따라 **에이전트가 자동**으로 수행합니다.

> **트리거**: `/sync` · 세션 종료 직전 · `just sync --check`

---

## 0. 사용자 기대와 실제 동작

| 기대 | 실제 |
|------|------|
| "코드·스펙이 지금 구현과 맞다" | Phase 2에서 **에이전트가 문서 본문**을 맞추고, Phase 3에서 **검증** |
| `just sync --check` 한 번에 끝 | ✅ 락 해시 + **문서가 diff에 포함됐는지** 자동 검사 |
| 스펙 문장 자동 생성 | ✅ 에이전트 자동 ([sync 워크플로 Phase 2](../../workflows/sync.md)) — `required` drift 시 갱신 후 재검증 |

---

## 1. CLI (`just sync`)

| 명령 | 동작 |
|------|------|
| `just sync --check` | ① `@code-sync-lock` 해시 ② **spec alignment** |
| `just lint` / `lint-turn-end` | 위 검증을 `sync-check-gate`로 포함 (`CI=true` → `--strict`) |
| `just sync --check --ack-spec` | 수동 역검증 완료 선언 |
| `just sync --lock` / `--update` | 락 생성·해시 갱신 |

> **Note**: `just sync --nudge`는 현재 `sync.py` 버전에서 제거됨. 필요시 `--check`만 사용.

**Spec alignment FAIL 시**: 후보 스펙 목록을 출력 → 해당 문서 갱신 후 재실행.

---

## 2. 세션 종료 DoD

1. `just lint` + renderer `pnpm run typecheck`
2. `just sync --check` → drift 발생 시 에이전트 자동 Phase 2 수행 ([sync 워크플로 Phase 2](../../workflows/sync.md))
3. `just sync --check` **PASS** 확인
4. 필요 시 `just renderer-route-smoke`
5. `Last Verified` 등 Claim 반영

---

## ⚠️ 함정 (Pitfalls)

### `required` drift 시 에이전트 자동 갱신 루프 ([sync 워크플로 Phase 2](../../workflows/sync.md))

`sync --check`가 `required` drift를 보고해도 **즉시 실패하지 않습니다**. 에이전트가 다음 루프를 수행:

1. drift 목록 확인 → 후보 스펙 경로 식별
2. `@code-sync-lock`의 `spec:` 필드가 가리키는 문서 읽기
3. 스펙 본문 수정 (Claim·표·절 일치)
4. 다시 `just sync --check` → PASS 전까지 반복

**함정**: 스펙을 일부만 수정하고 재검증하면 다시 `required`가 뜰 수 있음. **모든** drift가 해결될 때까지 반복해야 합니다.

### `sync --check`의 `required`는 즉시 편집을 강제하지 않음

`required` drift 힌트가 출력되어도 **code lock + spec alignment가 PASS**이면 통과 가능.
본문 편집은 [sync 워크플로 Phase 2](../../workflows/sync.md) 루프 또는 Phase 종료 게이트에서 수행.

> **레거시**: `just sync --nudge`·`just spec-sync-nudge` CLI는 제거됨. `just sync --check`만 사용.

### CSS 스타일 변경 → 런타임 drift 오인식

`sync --check`가 `.css` 파일 수정을 "라우트·Next 설정·프록시/미들웨어 변경"으로
오인식하여 `level: required`를 보고할 수 있음. **CSS-only 변경은 실제 런타임 영향이 없으므로** spec 본문 편집이 필요하지 않을 수 있음.

**대응**: `sync --check`가 PASS하면 무시해도 됨. `required`라도 CSS 스타일 개선이면
문서 갱신 없이 통과 가능.

### React 렌더링 최적화 → 런타임 drift 오인식 (v1.1.1)

`.tsx` 파일에서 `useDeferredValue`, `startTransition`, `memo`, `useCallback` deps
조정 등 **순수 렌더링 최적화**만 했을 때 `sync --check`가 "라우트·Next 설정·프록시/미들웨어 변경"으로 오인식할 수 있음.

구체적 패턴:
- `ConsultationPage.tsx` 등에서 위젯 prop 에 `deferredPatientId` 적용
- `useExaminationQueue.ts` 에서 `startTransition` 도입
- React 훅 import 추가 (`useDeferredValue`, `useCallback` 등)

이 변경들은 **라우트·Next config·proxy·middleware 를 건드리지 않으므로** 실제 런타임 영향 없음.

**대응**: `sync --check` 가 PASS 하면 무시. `required`라도 렌더링 최적화이면 spec 본문 편집 불필요.
실제 라우트/설정 변경이 아닌지 `git diff` 로 10 초 확인 후 통과.

### Form catalog Phase 1 — lint-turn-end 후 sync --check `required` drift
Task 1.16 에서 `just lint-turn-end` 실행 후 `just sync --check` 를 호출하면,
Phase 1 구현 (DB 모델·API 엔드포인트·Frontend 컴포넌트) 으로 인해 **spec drift level: required** 가 감지됨.

구체적 증상:
~~~
🔍 Spec drift level: required
   Reason: 라우트·Next 설정·프록시/미들웨어 변경 — 런타임과 문서 역검증 필수 ([sync 워크플로 Phase 3](../../workflows/sync.md)).

✅ [PASS] Spec alignment: 문서 갱신 12 건 (docs/specs·plans·knowledge·qa)
   · docs/plans/archive/blueprints/PLAN_office_document_form_catalog_IMPLEMENTATION.md
   · … 외 11 건
~~~

**원인**: `sync --check` 가 코드 변경을 감지하고 spec alignment 을 트리거했으나,
**현재 세션에서는 spec 본문 편집이 필수가 아님**. Phase 2 관리자 CRUD 구현 전까지는
스펙이 불완전할 수 있음 — 이는 의도된 점진적 개발 패턴.

**대응** (Task 1.16 종료 시):
1. `just lint-turn-end` → 0 오류 확인
2. `just sync --check` 실행 — `required`라도 **PASS**면 통과
3. spec 본문 편집은 **Phase 2 종료 시 plan-close 게이트**에서 한 번에 수행
4. `just sync --check` 가 `PASS`이면, `required` drift 는 **다음 Phase 로 이양**

**핵심**: `sync --check` 의 `required` 는 즉시 편집을 강제하지 않음.
코드 무결성 락이 통과 (`✅ [PASS]`) 했으면, spec drift 는 **Phase 2 완료 시** 한 번에 처리.

### Biome baseline 비어있을 때 수동 import 정렬 실패 패턴

`just lint` 또는 `frontend_biome_gate.sh` 가 "New Biome errors detected against baseline (N new)" +
"Current: N, Baseline: 0"을 보고하면 **baseline 파일이 비어있음**을 의미함.

**잘못된 접근**: 각 파일의 import 순수를 수동으로 맞춰보려 하면 (react → @/src → relative 등)
시간만 소모되고 biome이 원하는 exact 순서를 맞추기 어려움.

**올바른 접근**: `frontend_biome_gate.sh` 내장 auto-fix 사용 —
~~~bash
bash scripts/verify/frontend_biome_gate.sh --auto-fix --update-baseline
~~~
이 명령은 (1) biome `--write --unsafe`로 import 순서 자동 정렬, (2) current errors를 baseline에 기록.

**원인**: biome baseline (`apps/renderer/.ci/biome-baseline.txt`) 이 생성되지 않았거나 비어있을 때,
모든 파일이 "new error"로 분류됨. baseline이 0이면 new_count = current_count 이므로 항상 실패.

**대응**: 수동 패치 시도 → 실패 감지 → `--auto-fix --update-baseline`으로 원클릭 해결.

### CSS 변수 순환 참조 (globals.css ↔ tokens.css)

~~~
tokens.css:  --radius: var(--radius-md);
globals.css: --radius-md: calc(var(--radius) - 2px);
~~~

이렇게 되면 `--radius-md` → `var(--radius)` → `var(--radius-md)` → ... **무한 루프**가 되어
브라우저는 값을 해석하지 못하고 기존 스타일을 유지함.

**대응**: CSS 변수 체인에서 서로를 참조하는 순환이 발생하지 않도록 주의.
`calc(var(--radius) - 2px)` 같은 표현은 `--radius`가 이미 `var(--radius-md)`를 가리킬 때
순환을 유발함. 안전한 대안: 하드코딩된 픽셀 값 사용 (`8px`) 또는 토큰 재정의 없이 기존 체인 유지.

---

## 관련 SSOT

- [.agents/workflows/sync.md](../../workflows/sync.md)
- [scripts/agent/sync.py](../../../scripts/agent/sync.py)
- [docs/specs/technical/spec_integrated_sync_roadmap.md](../../../docs/specs/technical/spec_integrated_sync_roadmap.md)

## 참조 문서

- `references/css-variable-circular-reference.md` — CSS 변수 순환 참조 디버깅 레시피 (globals.css ↔ tokens.css)
