# AGENTS.md — AidenGame 실행 규약

이 문서는 저장소에서 작업하는 사람과 에이전트가 따라야 할 **최소 실행 규약**이다.
복잡한 Blueprint, Plan CLI, 라우팅 매니페스트, Linear 동기화는 일반 작업의 선행 조건이 아니다.

---

## 1. 규칙 우선순위

충돌 시 다음 순서를 따른다.

1. 사용자의 현재 요청과 명시적 제약
2. `PROJECT_RULES.md`
3. 본 문서 (`AGENTS.md`)
4. 대상 코드와 테스트가 표현하는 현재 계약
5. 기타 문서와 과거 계획 자료

`.agents/`, `docs/plans/`, `ROADMAP.md` 아래 문서는 참고 자료다. 사용자가 명시적으로 해당 워크플로우를 요청하지 않는 한 실행 게이트가 아니다.

---

## 2. 기본 개발 모델

- canonical branch는 `origin/main`이다.
- 1인 개발 기본값은 `main` 직접 수정과 fast-forward push다.
- PR과 feature branch는 사용자가 요청한 경우에만 사용한다.
- 병렬 세션은 서로 다른 isolated worktree 또는 동등한 격리 작업공간을 사용한다.
- force push와 `--no-verify`는 금지한다.
- 작업 전 `origin/main`과 현재 HEAD를 확인한다.
- unrelated dirty state가 있으면 보존하고 대상 경로와 섞지 않는다.
- 원격이 작업 중 선행되면 재확인하고, 안전한 fast-forward가 불가능하면 publish를 중단한다.

### 2.1 병렬 세션과 work-package claim

AidenGame은 프로젝트 전체를 한 세션만 수정하는 전역 single-writer 모델을 사용하지 않는다.
대신 **동일하거나 충돌하는 work package마다 owner 한 세션**을 둔다.

```text
PARENT_KEY
= 상위 제품 축 또는 closure group
= 병렬 작업을 묶는 식별자
= 잠금이 아님

TASK_KEY
= 독립적으로 검증 가능한 bounded work package
= 이 단위마다 owner 한 세션
```

- 같은 `PARENT_KEY` 아래에서도 `TASK_KEY`, `WRITE_SCOPE`, `EXCLUSIVE_RESOURCES`, `DEPENDS_ON`이 충돌하지 않으면 여러 owner가 병렬 실행할 수 있다.
- mutation, commit·push, 공통 runner·contract 변경 또는 장시간 canonical browser/release/evidence 실행 전에는 `agents/workflows/work-package-claim.md`를 따른다.
- 동적 owner 상태는 GitHub Issue #1 `[Coordination] Active Work-Package Claims`의 comments가 소유한다.
- read-only 분석, 코드 경로 확인, work-package 분해와 병렬 가능성 판정에는 claim이 필요하지 않다.
- 작업 지명이나 다음 작업 추천은 실행 권한이 아니다. claim-required 작업은 claim owner가 된 뒤에만 실행하거나 로컬 실행 프롬프트로 위임한다.
- claim은 isolated worktree, 최신 `origin/main` overlap 검사, focused verification, exact artifact identity 확인과 fast-forward publish 안전성을 대체하지 않는다.

---

## 3. 작업 계약

모든 개발·디버깅 작업은 다음 경계를 기본으로 한다.

```text
ONE WORK PACKAGE
= ONE COHERENT DEVELOPMENT OBJECTIVE
= EXPLICIT CHANGE SCOPE
= EXPLICIT VERIFICATION BUNDLE
= EXPLICIT STOP AND ROLLBACK CONDITIONS
```

강하게 결합된 requirements, callers, types, tests, configuration은 하나의 work package로 함께 변경할 수 있다.
변경의 완결성과 개발 속도를 고려하여 그룹핑한다.
여러 오류를 함께 처리할 수 있으나, 같은 목적과 rollback 경계를 공유하는 관계가 명확해야 한다.

### 3.1 수정 전

1. 현재 실패, 마찰 또는 변경 필요성을 재현하거나 관찰 가능한 근거로 확인한다.
2. work package의 coherent development objective를 정의한다.
3. 허용 변경 범위와 명시적 제외 범위를 정한다.
4. 검증 묶음과 acceptance checklist를 정의한다.
5. 중단 조건과 rollback 경계를 정한다.
6. claim-required 작업이면 `PARENT_KEY`, `TASK_KEY`, `WRITE_SCOPE`, `EXCLUSIVE_RESOURCES`, `DEPENDS_ON`을 정의하고 owner를 확정한다.

재현되지 않거나 근거가 사라진 후보는 수정하지 않고 `REJECTED`, `OBSOLETE` 또는 별도 조사 필요 상태로 기록한다.

### 3.2 수정

- 명시된 objective와 acceptance checklist를 충족하는 데 필요한 최소 완결 변경을 한다.
- 강하게 결합된 source, caller, type, test, configuration은 함께 수정할 수 있다.
- unrelated refactor, 대규모 정리, 현재 목적과 무관한 프레임워크 도입을 끼워 넣지 않는다.
- 작업 중 새 문제가 발견되면 현재 목적과의 결합도와 rollback 경계를 판정한다.
- 강하게 결합된 문제를 포함할 때는 허용 범위와 검증 묶음을 명시적으로 갱신한다.
- 독립적인 문제는 remaining work 또는 별도 work package로 남긴다.
- claim의 declared write/resource scope를 임의로 확대하지 않는다. 확대가 필요하면 기존 claim을 release하고 새 경계로 다시 arbitration한다.
- workaround, fail-open fallback, 검증 우회로 문제를 숨기지 않는다.
- 삭제·데이터 변경·배포 등 비가역성이 큰 작업은 현재 요청 범위를 벗어나면 중단한다.
- 범위가 로컬 모델의 안정적인 컨텍스트를 넘거나 rollback 경계가 다르면 child work package로 분할한다.

### 3.3 수정 후

1. 정의한 verification bundle을 실행한다.
2. acceptance checklist의 각 항목을 실제 근거로 판정한다.
3. 검증 실패는 다른 성공 결과로 덮지 않는다.
4. full-suite는 변경 위험, 저장소 계약 또는 cutover 성격상 필요할 때만 추가한다.
5. 여러 변경을 수행했더라도 full-suite 결과 하나만으로 모든 계약을 뭉뚱그려 판정하지 않는다.
6. 남은 독립 문제와 후속 작업을 분리해 기록한다.
7. claim-required 작업은 완료·차단·포기 여부와 관계없이 Issue #1에 `RELEASE`를 게시한다.

---

## 4. 계획 문서 정책

### 4.1 기본값

일반 작업은 별도 Plan 또는 Blueprint 없이 bounded work package로 바로 시작한다.

다음 항목은 **필수 선행 게이트가 아니다**.

- `just plan-lint`
- `just plan-preread`
- `just plan-task-close`
- `just plan-close`
- `just route`, `just route-read`, `just route-gate-check`
- Linear issue 생성 또는 동기화
- 다중 subagent 5단계 실행

기존 Plan 관련 스크립트와 문서는 과거 작업 재현 또는 명시적 요청을 위해 남겨둘 수 있으나, 새 작업을 차단하지 않는다.

### 4.2 계획 문서가 필요한 경우

다음 조건 중 하나에 해당할 때만 짧은 SSOT 또는 migration plan을 추가한다.

- 여러 세션에 걸친 장기 작업
- 순서 의존적인 bounded work package가 3개 이상인 작업
- 제품·데이터·배포 계약을 장기간 추적해야 하는 작업
- 여러 cutover와 rollback 경계를 단계적으로 관리해야 하는 작업

계획 문서는 장기 기술 결정과 실행 상태를 구분한다.
각 실행 항목은 목적, 범위, 검증, 중단 조건, rollback 경계를 가져야 한다.
계획 문서 자체의 완성도가 제품 변경보다 우선하지 않는다.

---

## 5. 검증 원칙

검증은 실제 위험, 변경 범위, 회귀 가능성, 계약 경계에 비례해야 한다.

- 기존 테스트·정적 분석·런타임 계약으로 충분하면 새 게이트를 추가하지 않는다.
- 새 검증은 잡아낼 구체적인 실패 모드와 판정 방법이 있을 때만 추가한다.
- acceptance checklist 또는 verification matrix를 사용할 수 있다.
- 동일 사실을 반복 확인하는 스크립트, 체크리스트, 중복 게이트를 늘리지 않는다.
- 필수 검증 도구가 없으면 성공으로 처리하지 말고 fail-closed한다.
- 문서 전용 변경은 문서 계약만 검증한다.
- 제품 코드 변경은 관련 테스트를 우선하고 필요할 때만 범위를 확장한다.

저장소의 대표 명령은 다음과 같다.

```bash
just verify
just lint
just typecheck
just test
just ci
```

모든 작업에 모든 명령을 실행하는 것이 아니라, 현재 work package의 위험과 계약에 필요한 최소 검증 묶음을 선택한다.

---

## 6. 프로젝트 경계

- 사용자 런타임은 정적 HTML/CSS/JavaScript다.
- 메인 허브는 `index.html`이다.
- 과목별 기능은 `domains/` 아래에 둔다.
- 공용 로직은 `shared/` 아래에 둔다.
- 실험 기능은 `experiments/` 아래에 둔다.
- 보호자·관리 기능은 `guardian/`, `admin/` 아래에 둔다.
- Next.js, Tauri, 별도 백엔드 API는 현재 범위 밖이다.

상세 아키텍처와 스택 계약은 `PROJECT_RULES.md`를 따른다.

---

## 7. 보안과 정직성

- API 키, 토큰, 쿠키, `.env` 원문을 출력하거나 커밋하지 않는다.
- 민감정보 가능성이 있는 파일은 내용을 노출하지 않고 존재와 상태만 보고한다.
- 검증하지 않은 결과를 PASS라고 보고하지 않는다.
- 실행하지 않은 명령, 확인하지 않은 원격 상태, 생성하지 않은 커밋을 수행한 것처럼 표현하지 않는다.
- blocker가 있으면 우회하지 말고 정확한 복구 조건을 보고한다.

---

## 8. 로컬 에이전트 위임

로컬 LLM에 위임할 때는 하나의 프롬프트에 하나의 bounded work package를 담는다.

- 단일 프롬프트는 최대 700줄로 제한한다.
- 입력에는 objective, included scope, excluded scope, allowed paths, verification bundle, stop conditions, rollback boundary를 명시한다.
- 단일 가설, 단일 failure domain 또는 단일 binary criterion을 형식적으로 만들도록 강제하지 않는다.
- 강하게 결합된 source, caller, type, test, configuration은 같은 프롬프트에 포함할 수 있다.
- 과거 계획 전체를 반복 삽입하지 않고 현재 작업에 필요한 delta만 전달한다.
- 컨텍스트가 커지면 phase 또는 child work package로 나누고 이전 결과를 확인한 뒤 다음 작업을 진행한다.
- claim-required 실행 프롬프트는 웹 GPT 세션이 Issue #1에서 package claim owner가 된 뒤에만 발급한다.
- 웹 세션은 획득한 claim을 로컬 에이전트 **한 세션**에 delegated executor로 위임할 수 있다.
- 프롬프트에는 `PARENT_KEY`, `TASK_KEY`, `CLAIM_ID`, `OWNER_LABEL`, `WRITE_SCOPE`, `EXCLUSIVE_RESOURCES`, `DEPENDS_ON`, lease와 재확인·release 책임을 포함한다.
- 같은 `CLAIM_ID`를 여러 로컬 executor에 동시에 위임하지 않는다.
- 위임받은 로컬 executor는 별도 중복 claim을 게시하지 않는다. Issue 접근이 없으면 coordinating 웹 세션이 claim 재확인과 `RELEASE` 게시를 책임진다.
- owner가 아니거나 coordination board에 접근할 수 없는 웹 세션은 claim-required 실행 프롬프트를 제공하지 않고 read-only coordination 결과만 보고한다.

---

## 9. 완료 보고 계약

완료 보고에는 최소한 다음을 포함한다.

```text
TASK_ID
RESULT
VERDICT
CONFIDENCE
BLOCKER
WORK_PACKAGE_OBJECTIVE
INCLUDED_SCOPE
EXCLUDED_SCOPE
ACCEPTANCE_CHECKLIST
VERIFICATION
CHANGED_PATHS
GIT / PUBLICATION STATUS
REMAINING_WORK
```

claim-required 작업은 다음을 추가한다.

```text
PARENT_KEY
TASK_KEY
CLAIM_ID
CLAIM_STATUS
OWNER_LABEL
WRITE_SCOPE
EXCLUSIVE_RESOURCES
RELEASE_POSTED
```

가설 기반 조사에서는 `HYPOTHESIS`와 `HYPOTHESIS_VERDICT`를 추가할 수 있으나 모든 작업의 필수 필드는 아니다.
보고는 실제 실행 근거만 포함한다.
과거 Blueprint의 Status/Conclusion 필드를 갱신하는 것은 일반 완료 조건이 아니다.

---

## 10. SSOT 인덱스

| 목적 | SSOT |
|---|---|
| 프로젝트 개요 | `README.md` |
| 실행 규약 | `AGENTS.md` |
| 아키텍처·스택·품질 정책 | `PROJECT_RULES.md` |
| 병렬 실행·프롬프트 발급 claim | `agents/workflows/work-package-claim.md` + GitHub Issue #1 comments |
| Git·publish 절차 | `agents/workflows/git.md` |
| 실행 가능한 요구사항 | `tests/` |
| 통합 검증 | `verify.sh`, `Justfile` |
| Ocean Rescue 개발 아키텍처 | `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md` |
| Ocean Rescue Vite/ESM/TS 마이그레이션 | `docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md` |
| 기능별 설계 | 대상 기능과 가장 가까운 `docs/` 문서 |

과거 Plan/Blueprint 자료는 역사적 참고 자료이며 현재 실행 규약의 상위 SSOT가 아니다.
