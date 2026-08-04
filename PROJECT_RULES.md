# PROJECT_RULES.md — AidenGame 프로젝트 정책

이 문서는 AidenGame의 아키텍처, 런타임, 품질, 보안 경계를 정의한다.
작업 절차는 `AGENTS.md`를 따른다.

---

## 1. 제품 목적

AidenGame은 어린이를 위한 정적 웹 기반 학습 게임 플랫폼이다.
학습 흐름의 단순성, 즉각적인 피드백, 성취감, 보호자 통제를 우선한다.

---

## 2. 런타임과 아키텍처 SSOT

사용자 화면과 게임 로직은 정적 HTML/CSS/JavaScript로 제공한다.

| 역할 | 경로 |
|---|---|
| 메인 허브 | `index.html` |
| 공용 스타일 | `styles.css` |
| 과목별 게임 | `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/` |
| 지원 도메인 | `domains/reward/`, `domains/auth/`, `domains/sync/` |
| 공용 로직 | `shared/domain/`, `shared/ui/`, `shared/event-bus.js` |
| 실험 기능 | `experiments/` |
| 보호자 기능 | `guardian/` |
| 관리 기능 | `admin/` |
| 테스트 | `tests/` |
| 검증 스크립트 | `verify.sh`, `scripts/`, `tools/` |

### 필수 경계

- 신규 UI와 런타임 로직은 가장 가까운 기능 디렉터리에 둔다.
- 여러 과목이 공유하는 로직만 `shared/`로 올린다.
- 실험 기능은 안정화되기 전까지 `experiments/`에 격리한다.
- 빈 `src/` 디렉터리를 새로운 런타임 SSOT로 사용하지 않는다.
- 현재 범위에 Next.js, Tauri, 별도 백엔드 API를 추가하지 않는다.
- 생성된 배포 산출물과 authoring source를 구분한다.
- Ocean Rescue의 상세 개발 아키텍처는 `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md`를 따른다.

---

## 3. 기술 스택

### 3.1 사용자 런타임

- 브라우저 런타임: HTML, CSS, JavaScript
- 배포: `vercel.json`을 사용하는 정적 호스팅
- 서버 또는 Node 런타임 의존성 없음

### 3.2 공통 검증·도구

- 검증·도구: Python
- 환경·패키지: `uv`
- 명령 진입점: `just`
- 정적 분석: Ruff, `ty` 또는 Pyright
- 테스트: Pytest

### 3.3 Ocean Rescue 개발/build 도구 (PLANNED)

- TypeScript target source
- ESM module system
- Vite development server and application bundling
- pnpm package management
- Node: build-time only
- 기존 Python asset validation, atlas, registry, standalone packaging tooling 유지

이 도구들은 Ocean Rescue 개발 경로에 한정된다.
다른 domain에 Vite, TypeScript 또는 pnpm을 자동으로 강제하지 않는다.

도구의 exact version은 해당 lockfile과 version pin이 authority다.
서로 다른 실행 경로가 다른 판정을 내리면 관련 도구, 설정, 검증을 하나의 coherent reconciliation work package로 다룬다.

---

## 4. 개발 및 배포 정책

- canonical branch는 `origin/main`이다.
- 기본 개발 방식은 `main` 직접 수정과 fast-forward push다.
- PR과 feature branch는 사용자가 요청한 경우에만 사용한다.
- 병렬 세션은 isolated worktree 또는 동등한 격리 작업공간을 사용한다.
- force push는 금지한다.
- 배포 설정 변경은 제품 런타임 경로와 함께 검증한다.
- 원격 상태나 필수 검증이 불명확하면 publish하지 않는다.
- generated artifact는 직접 편집하지 않고 canonical source와 build pipeline을 통해 갱신한다.
- 저장소 전체 전역 single-writer 잠금은 사용하지 않는다. 동일·중복·overlap work package에만 owner 한 세션을 둔다.
- mutation, commit·push, shared runner·contract 변경과 장시간 canonical 실행은 `agents/workflows/work-package-claim.md`에 따라 GitHub Issue #1에서 owner를 확정한 뒤 수행한다.
- `PARENT_KEY`는 상위 제품축 grouping이며 잠금이 아니다. 충돌하지 않는 서로 다른 `TASK_KEY`에는 여러 owner를 허용한다.
- 웹 GPT 세션은 owner claim을 로컬 agent 한 세션에 위임할 수 있으며, claim이 없는 상태에서는 실행 프롬프트를 발급하지 않는다.
- 동적 claim은 저장소 파일에 기록하지 않는다. Issue #1 comments가 owner·lease·release 상태의 SSOT다.

---

## 5. 품질 정책

### 5.1 Coherent work package

모든 변경은 하나의 coherent development objective를 중심으로 구성한다.

- 강하게 결합된 requirements, callers, types, tests, configuration은 함께 변경할 수 있다.
- 허용 범위, 명시적 제외 범위, verification bundle, stop conditions, rollback boundary를 정한다.
- 여러 오류를 함께 수정할 수 있으나 같은 목적과 변경 경계를 공유해야 한다.
- scope가 로컬 모델의 안정적인 컨텍스트를 넘거나 rollback 경계가 다르면 child work package로 분할한다.
- unrelated cleanup은 끼워 넣지 않는다.
- 단일 failure domain, 단일 가설 또는 단일 binary criterion을 모든 작업에 형식적으로 강제하지 않는다.
- 조사형 작업에서 직접 가설이 유용하면 사용할 수 있으나 필수 형식은 아니다.

### 5.2 검증

- 수정 전 현재 동작, 실패 또는 변경 필요성을 재현하거나 관찰 가능한 근거로 확인한다.
- 수정 후 정의된 verification bundle과 acceptance checklist를 실행한다.
- 실제 위험에 비례하지 않는 중복 게이트를 추가하지 않는다.
- 기존 테스트가 충분하면 새 검증 스크립트를 만들지 않는다.
- 필수 도구가 없거나 검증이 실행되지 않았으면 PASS로 처리하지 않는다.
- 여러 변경을 수행했더라도 full-suite 결과 하나만으로 각 계약을 대신 판정하지 않는다.
- full-suite는 변경 범위, cutover 성격 또는 회귀 위험이 요구할 때 실행한다.
- 강하게 결합된 추가 문제를 현재 work package에 포함할 때는 scope와 verification bundle을 함께 갱신한다.
- 독립적인 문제는 remaining work로 분리한다.

대표 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

모든 작업에 모든 명령을 강제하지 않는다.
현재 work package의 위험과 계약에 필요한 최소 검증 묶음을 선택한다.

### 5.3 과거 Plan 도구

`Justfile`, `scripts/plan_loop/`, `docs/plans/`, `.agents/`에 남아 있는 Plan/Blueprint 도구는 역사적 자료 또는 명시적 요청용이다.
다음 항목은 일반 구현의 선행 조건이 아니다.

- Plan 파일 생성
- `just plan-lint` 통과
- Blueprint Task closeout
- route manifest 생성
- Linear 동기화
- Plan archive 갱신

이 도구들의 정리 또는 삭제는 실제 참조, rollback 경계, 회귀 위험을 확인한 별도 cleanup work package에서 수행한다.

---

## 6. 사용자 경험 정책

- 어린이가 이해할 수 있는 짧고 명확한 문구를 사용한다.
- 실패보다 재시도와 성취 피드백을 강조한다.
- 터치 환경과 작은 화면을 기본 사용 환경으로 고려한다.
- 핵심 학습 흐름은 키보드와 보조 기술로도 사용할 수 있어야 한다.
- 시각 효과가 학습 조작이나 텍스트 가독성을 방해하지 않게 한다.
- 보상과 보호자 기능은 학습 결과와 명확히 연결한다.

---

## 7. 보안 정책

- API 키, 토큰, 쿠키, `.env` 원문을 저장소나 에이전트 출력에 노출하지 않는다.
- 인증·동기화·보호자 기능은 권한이 불명확할 때 fail-closed한다.
- 클라이언트 저장소의 값만으로 민감한 권한을 신뢰하지 않는다.
- 외부 입력은 사용 전 검증하고 DOM 삽입 시 안전한 API를 사용한다.

---

## 8. 문서 정책

문서는 현재 코드와 검증 가능한 계약을 설명해야 한다.
과거 계획의 상태 관리 자체를 위해 제품 변경을 지연하지 않는다.

| 목적 | SSOT |
|---|---|
| 프로젝트 개요와 실행 방법 | `README.md` |
| 작업 실행 규약 | `AGENTS.md` |
| 프로젝트 정책 | `PROJECT_RULES.md` |
| 병렬 실행·프롬프트 발급 claim | `agents/workflows/work-package-claim.md` + GitHub Issue #1 comments |
| Git·publish 절차 | `agents/workflows/git.md` |
| 요구사항과 회귀 계약 | `tests/` |
| 배포 경로 | `vercel.json`과 실제 엔트리 파일 |
| Ocean Rescue 개발 아키텍처 | `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md` |
| Ocean Rescue migration 상태 | `docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md` |
| 기능 설계 | 대상 기능에 가장 가까운 `docs/` 문서 |

문서와 실제 런타임이 충돌하면 코드를 무조건 문서에 맞추지 않는다.
현재 의도, 실제 동작, executable contract를 먼저 확인하고 어느 쪽이 canonical인지 근거로 판정한다.
