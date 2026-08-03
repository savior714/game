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
- PR, feature branch, worktree, Linear 연동은 사용자가 요청한 경우에만 사용한다.
- force push와 `--no-verify`는 금지한다.
- 작업 전 `origin/main`과 현재 HEAD를 확인한다.
- unrelated dirty state가 있으면 보존하고 대상 경로와 섞지 않는다.
- 원격이 작업 중 선행되면 재확인하고, 안전한 fast-forward가 불가능하면 publish를 중단한다.

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

강하게 결합된 requirements, callers, types, tests, configuration은 함께 변경할 수 있다.
변경의 완결성과 개발 속도를 고려하여 그룹핑한다.
여러 오류를 함께 처리할 수 있으나 관계가 명확해야 한다.

### 3.1 수정 전

1. 현재 실패 또는 마찰을 재현한다.
2. work package의 coherent development objective를 정의한다.
3. 허용 변경 범위를 명시한다.
4. 검증 묶음을 정의한다.
5. 중단 조건과 rollback 경계를 정한다.

재현되지 않거나 근거가 사라진 가설은 `REJECTED`로 닫고 코드를 수정하지 않는다.

### 3.2 수정

- 명시된 검증 묶지를 검증하는 최소 변경만 한다.
- unrelated refactor, 대규모 정리, 새 프레임워크 도입을 묶지 않는다.
- 여러 문제가 보여도 현재 work package 범위 밖의 문제는 기록만 하고 수정하지 않는다.
- workaround, fail-open fallback, 검증 우회로 문제를 숨기지 않는다.
- 삭제·데이터 변경·배포 등 비가역성이 큰 작업은 현재 요청 범위를 벗어나면 중단한다.
- 범위가 너무 크거나 rollback 경계가 다르면 별도 work package로 분할한다.

### 3.3 수정 후

1. 명시된 검증 묶지만 targeted verification으로 독립 검증한다.
2. acceptance checklist를 충족하면 해당 작업을 닫는다.
3. 다른 실패가 남으면 별도 failure domain으로 분리한다.
4. full-suite는 변경 위험이나 저장소 계약상 필요할 때만 추가한다.

한 번에 여러 원인을 수정한 뒤 full-suite 결과 하나로 모두를 판정하지 않는다.

---

## 4. 계획 문서 정책

### 4.1 기본값

일반 작업은 별도 Plan 또는 Blueprint 없이 바로 atomic 계약으로 시작한다.

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

다음 조건 중 하나에 해당할 때만 짧은 SSOT 문서를 추가한다.

- 여러 세션에 걸친 장기 작업
- 독립적인 atomic task가 3개 이상이며 순서 의존성이 있음
- 제품·데이터·배포 계약을 장기간 추적해야 함

계획 문서를 만들더라도 각 실행 항목은 여전히 하나의 failure domain으로 분리한다. 계획 문서 자체의 완성도가 제품 변경보다 우선하지 않는다.

---

## 5. 검증 원칙

검증은 실제 위험, 변경 범위, 회귀 가능성, 계약 경계에 비례해야 한다.

- 기존 테스트·정적 분석·런타임 계약으로 충분하면 새 게이트를 추가하지 않는다.
- 새 검증은 잡아낼 구체적 failure mode와 단일 판정 기준이 있을 때만 추가한다.
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

모든 작업에 모든 명령을 실행하는 것이 아니라, 현재 failure domain에 필요한 최소 명령을 선택한다.

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

로컬 LLM에 위임할 때는 하나의 프롬프트에 하나의 atomic task만 담는다.

- 단일 프롬프트는 최대 700줄로 제한한다.
- 입력에는 failure domain, hypothesis, verdict criterion, allowed paths, targeted verification을 명시한다.
- 과거 계획 전체를 반복 삽입하지 않고 현재 작업에 필요한 delta만 전달한다.
- 독립 작업은 순차 실행하며 이전 결과를 확인한 뒤 다음 failure domain을 선택한다.

---

## 9. 완료 보고 계약

완료 보고에는 최소한 다음을 포함한다.

```text
TASK_ID
RESULT
VERDICT
CONFIDENCE
BLOCKER
FAILURE_DOMAIN
HYPOTHESIS
HYPOTHESIS_VERDICT
VERIFICATION
CHANGED_PATHS
GIT / PUBLICATION STATUS
REMAINING_SEPARATE_FAILURES
```

보고는 실제 실행 근거만 포함한다. 과거 Blueprint의 Status/Conclusion 필드를 갱신하는 것은 일반 완료 조건이 아니다.

---

## 10. SSOT 인덱스

| 목적 | SSOT |
|---|---|
| 프로젝트 개요 | `README.md` |
| 실행 규약 | `AGENTS.md` |
| 아키텍처·스택·품질 정책 | `PROJECT_RULES.md` |
| 실행 가능한 요구사항 | `tests/` |
| 통합 검증 | `verify.sh`, `Justfile` |
| Ocean Rescue 개발 아키텍처 | `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md` |
| Ocean Rescue Vite/ESM/TS 마이그레이션 | `docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md` |
| 기능별 설계 | 대상 기능과 가장 가까운 `docs/` 문서 |

과거 Plan/Blueprint 자료는 역사적 참고 자료이며 현재 실행 규약의 상위 SSOT가 아니다.
