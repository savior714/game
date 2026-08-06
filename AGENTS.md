# AGENTS.md — AidenGame 저장소 계약

이 문서는 AidenGame 저장소에만 해당하는 계약만 담는다. 일반적인 에이전트 행동은 시스템 프롬프트를 따른다.

## 1. 적용 순서

1. 사용자의 현재 요청
2. 이 문서
3. `PROJECT_RULES.md`와 대상 기능의 가장 가까운 product/technical spec
4. 최신 `origin/main`의 코드·테스트·설정

과거 계획과 완료 보고를 현재 상태의 근거로 사용하지 않는다.

## 2. WP 계획과 상태

- `WP-33E` 같은 이름은 대화와 실행 보고에서 사용하는 작업 라벨이다.
- 사용자가 저장소 문서화를 명시적으로 요청하지 않는 한 WP 계획·다음 WP·진행 상태·완료 상태는 대화에서만 관리한다.
- 일반 WP 작업을 위해 `docs/plans/PLAN_ocean_rescue_wp*.md` 또는 상태 전용 `docs/evidence/` 문서를 생성·수정하지 않는다.
- 테스트는 제품 동작·타입·빌드·배포 계약을 검증하며 `다음 WP`, `현재 WP`, `WP COMPLETE` 같은 일정 상태를 검증하지 않는다.
- 기존 migration plan과 과거 WP 문서는 참고 자료일 뿐 현재 일정의 권위가 아니다.
- Blueprint 절차는 사용자가 저장소 Blueprint를 명시적으로 요청한 경우에만 적용한다.

## 3. 현재 제품 방향

현재 기본 작업 선택은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`를 따른다.

- 우선 대상은 `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/`의 일반 문제풀이 신뢰성이다.
- 범위가 지정되지 않은 “다음 작업”, “이어서 진행”, 로컬 프롬프트 요청은 네 과목 공통 진단 또는 아직 닫히지 않은 일반 문제풀이 failure domain으로 해석한다.
- 최근 커밋이나 과거 대화가 Ocean Rescue였다는 이유만으로 Ocean Rescue 작업을 재개하지 않는다.
- 일반 과목 안정화 종료 전에는 Ocean Rescue와 `experiments/`의 신규 기능·구조 이전을 시작하거나 이를 위한 로컬 프롬프트를 발행하지 않는다.
- 예외는 사용자가 현재 요청에서 개발 방향을 명시적으로 변경했거나, 현재 배포를 막는 치명적 회귀·데이터 손상·보안 문제를 독립 failure domain으로 해결하는 경우다.
- 기존 테스트 파일이나 과거 PASS 보고만으로 과목 완료를 선언하지 않는다. 최신 main의 상태 계약과 실제 브라우저 증거를 함께 확인한다.
- 과목별 진행률·다음 과목·완료 체크는 저장소 문서에 누적하지 않는다. 현재 완료 근거는 코드, 테스트, 브라우저 증거, 게시 커밋이다.

## 4. Git과 workspace

- 통합·게시 기준은 `origin/main`이며 기본 게시 방식은 `main` fast-forward push다. PR·feature branch는 사용자가 요청한 경우에만 사용한다.
- mutation은 최신 `origin/main`에서 만든 isolated worktree 또는 동등한 격리 공간에서 수행한다.
- 기본 worktree 경로는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`다. 저장소 위치가 다르면 같은 개발 루트의 안정적인 `.worktrees/game/<task-slug>` sibling 경로를 사용한다.
- source worktree를 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 아래에 만들지 않는다.
- IDE, LSP, uv, pnpm, Docker, 브라우저 E2E, generated artifact 검증은 모두 실제 작업 worktree 하나를 동일한 workspace root와 CWD로 사용한다.
- unrelated dirty state를 보존한다. force push, history rewrite, `--no-verify`, 필수 검증 우회는 금지한다.
- 게시 전 최신 `origin/main`을 다시 확인한다. non-fast-forward가 발생하면 최신 main에 재적용하고 직접 영향 검증을 다시 실행한다.
- 비중첩 remote advance와 다른 세션의 선행 게시는 blocker가 아니다. 최신 main 재적용, V1·필수 V2 재실행, 게시 재시도를 반복한다.

## 5. 병렬 실행과 reservation

일반 작업은 reservation 없이 격리된 worktree에서 병렬 실행한다. 다음 자원이 실제로 겹칠 때만 `agents/workflows/work-package-claim.md`와 Issue #1을 사용한다.

- 같은 semantic hotspot 또는 shared contract
- 같은 generated bundle·atlas·registry·publication destination
- 같은 browser/runtime identity, fixed port, profile, output directory
- 같은 migration·schema 자원

같은 파일이라는 이유만으로 reservation하지 않는다. reservation에는 `WORK / OWNER / EXPIRES / SCOPE`만 사용한다.

## 6. 프로젝트 경계

- 사용자 런타임은 정적 HTML/CSS/JavaScript다.
- 메인 허브는 `index.html`이다.
- 과목별 기능은 `domains/`, 공용 로직은 `shared/`에 둔다.
- 실험은 `experiments/`, 보호자·관리 기능은 `guardian/`, `admin/`에 둔다.
- Next.js, Tauri, 별도 backend API는 현재 범위 밖이다.
- Ocean Rescue 세부 계약은 사용자가 해당 범위를 명시적으로 재개한 경우 대상 코드에서 가장 가까운 technical spec을 따른다.

## 7. 검증과 작업 판정

현재 방향 문서 정합성:

```bash
uv run pytest -q tests/test_core_quiz_reliability_policy.py
```

대표 저장소 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

### 위험 기반 개발·테스트 선택

정통 TDD를 모든 변경에 일률적으로 강제하지 않는다. TDD를 생략하는 것은 무검증 개발을 허용한다는 뜻이 아니다.

- 화면 구성, 스타일, 애니메이션, 조작감, 게임 감각, 콘텐츠 표현, 탐색적 신규 기능과 단순 dependency/toolchain 승격은 먼저 구현하고 실제 브라우저·입력·렌더링으로 직접 확인한 뒤 안정된 계약만 회귀 테스트로 고정할 수 있다.
- 입력 한 번에 효과 한 번, 이벤트 중복 연결, 점수·진행·저장 데이터, 복잡한 상태 전이, 재시작·복구, 공유 controller, 사용자 데이터 손상 가능성과 이미 발생한 회귀 버그는 테스트 우선 또는 구현과 동시에 테스트한다.
- 시각적 품질과 재미를 단위 테스트로 대신하지 않는다. 반대로 자동 검증 가능한 핵심 계약을 수동 확인만으로 남기지 않는다.
- 테스트는 구현 구조를 복제하지 않고 사용자에게 중요한 동작과 재발 방지에 집중한다.
- 모든 변경은 수정 전 재현 조건 또는 기대 동작과 단일 판정 기준을 정하고, 수정 후 해당 failure domain을 가장 짧은 독립 검증으로 판정한다.
- 형식적인 RED 증명, 고정 횟수 반복, 전 과목·전체 suite 실행을 모든 작업의 기본 절차로 삼지 않는다. 현재 위험이나 실제 불안정성이 요구할 때만 넓힌다.

현재 작업 결과는 다음 두 항목으로만 판정한다.

- `PRIMARY_CRITERION`: 현재 단일 가설을 직접 판정하는 기준
- `DIRECT_IMPACT_CLOSURE`: 수정 파일과 직접 영향 범위의 lint·type·focused regression

검증 계층:

- V0 `BASELINE`: 수정 전 결함 재현
- V1 `PRIMARY`: 단일 가설 판정
- V2 `DIRECT`: 수정 파일과 직접 영향 closure
- V3 `SYSTEM_SMOKE`: 독립 결함 탐색; 현재 작업 PASS를 취소하지 않음
- V4 `RELEASE`: 명시적인 release candidate에서만 수행

현재 변경이 정상이어도 실패할 수 있는 broad smoke, full suite 또는 다른 과목·실험 영역의 실패는 primary criterion이 될 수 없다. V3에서 발견된 독립 실패는 현재 작업의 PASS를 취소하지 않고 `DISCOVERED_FAILURE`로 분리한다.

변경 위험에 직접 대응하는 가장 작은 검증부터 시작하며 모든 명령을 일괄 실행하지 않는다.

수정 파일과 직접 영향 모듈의 LSP·typecheck·lint 오류는 0이어야 한다. 환경·workspace·SDK·cache·generated/vendor 오분석을 production code 변경으로 우회하지 않는다.

workaround, fail-open fallback, broad ignore, 검사 대상 축소, baseline·snapshot 갱신, unrelated cleanup으로 실패를 숨기지 않는다. 실행하지 못한 V1·필수 V2 criterion은 PASS로 보고하지 않는다.

`BLOCKED`는 `DECISION_REQUIRED`, `PRIMARY_UNEVALUABLE`, `SEMANTIC_OVERLAP`, `SAFETY_BOUNDARY`, 또는 V1·필수 V2 실패를 현재 failure domain 안에서 안전하게 닫을 수 없는 경우에만 사용한다.

remote advance, non-fast-forward, unrelated dirty, V3 실패, 새 독립 결함, 다른 세션의 선행 게시는 blocker가 아니다.

## 8. 로컬 에이전트 위임

로컬 LLM용 프롬프트는 바로 발행하지 않는다. 매 프롬프트마다 먼저 사용자의 요청을 구체적으로 재해석하여 다음을 제시한다.

- 목표와 대상 failure domain 또는 검증 가설
- 대상 저장소·기능과 변경 허용 범위
- 포함·제외 범위와 변경 금지 계약
- primary criterion과 직접 영향 검증
- 게시 여부와 예상 최종 상태

그 다음 사용자에게 “제가 이렇게 해석했습니다. 이대로 진행해도 되는 게 맞습니까?”라는 취지로 명시적 승인을 요청한다. 승인 전에는 프롬프트 본문, 코드 블록, 부분 초안 또는 실행 가능한 지시를 제공하지 않는다.

이 절차는 요청이 명확해 보이거나 이전 작업을 단순히 이어가는 경우에도 생략하지 않는다. 사용자가 범위를 수정하면 변경된 해석을 다시 제시하고 재승인받는다. 이미 제시된 해석에 대한 사용자의 명시적 승인은 해당 프롬프트 발행을 위한 승인으로 간주한다.

이 의도 재확인은 대화상 책임 경계다. 전용 스크립트·정기 검사·CI gate·강제 checklist로 자동화하거나 로컬 작업자에게 대신 판단시키지 않는다.

- 프롬프트 발행 전 현재 objective가 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`의 포함 범위인지 확인한다.
- 포함 범위가 아니고 사용자가 현재 요청에서 방향 변경이나 허용 예외를 명시하지 않았다면 구현 프롬프트를 발행하지 않는다.
- 프롬프트에는 현재 objective, workspace, included/excluded scope, Do / Do not, primary acceptance, direct verification, optional system smoke, stop condition만 전달한다.
- 현재 package에 필요한 delta만 포함하고 최대 700줄을 넘기지 않는다.
- source workspace는 안정적인 `.worktrees/game/<task-slug>` 하나로 고정한다.
- 일반 병렬 prompt에는 reservation metadata를 넣지 않는다.
- WP 작업 프롬프트에는 계획 파일·WP 상태·상태 전용 evidence 생성을 포함하지 않는다.

## 9. 거버넌스

새 coordination 규칙·validator·상태 머신·완료 보고 필드는 실제 충돌이 반복 재현되고 worktree·고유 runtime identity·게시 전 overlap 확인으로 해결되지 않을 때만 추가한다.

## 10. 완료 보고

```text
RESULT: PASS | BLOCKED
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED
DISCOVERED_FAILURE: <독립 failure domain 또는 NONE>
```

실제 게시 시에만 `COMMIT`, 허용된 blocker로 중단할 때만 `BLOCKER`와 `NEXT`를 추가한다.
