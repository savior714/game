# AGENTS.md — AidenGame 실행 규약

이 문서는 저장소 작업의 최소 실행 계약이다. Plan·Blueprint·라우팅 매니페스트·장문 보고는 일반 작업의 선행 조건이 아니다.

## 1. 우선순위

1. 사용자의 현재 요청
2. 이 문서
3. `PROJECT_RULES.md`
4. 대상 코드와 테스트
5. 기타 문서와 과거 계획

## 2. Git과 work package

- canonical branch는 `origin/main`이며 기본 방식은 `main` 직접 수정과 fast-forward push다.
- PR과 feature branch는 사용자가 요청한 경우에만 사용한다.
- 병렬 mutation은 isolated worktree 또는 동등한 격리 공간을 사용한다.
- 기본값은 reservation 없는 낙관적 병렬 실행이다.
- 하나의 package는 coherent objective와 rollback 경계를 가진다.
- 강하게 결합된 source, caller, type, test, asset, config는 함께 변경할 수 있다.
- unrelated change와 rollback 경계가 다른 문제만 분리한다.
- force push와 `--no-verify`는 금지한다.
- unrelated dirty state를 보존한다.

## 3. Exclusive reservation

`agents/workflows/work-package-claim.md`는 일반 작업 claim이 아니라 희소 자원의 reservation이다.

다음에만 Issue #1을 사용한다.

- 같은 semantic hotspot/shared contract
- 같은 generated bundle·atlas·registry 또는 publication destination
- 같은 canonical browser/runtime identity, fixed port, profile, output directory
- 같은 migration/schema 자원(해당되는 경우)

서로 다른 기능 디렉터리, test, UI flow, 독립 bug fix는 reservation 없이 병렬 실행한다.
같은 파일이라는 이유만으로 자동 예약하지 않는다.
reservation에는 `WORK / OWNER / EXPIRES / SCOPE`만 사용한다.

## 4. 작업과 게시

1. 최신 `origin/main`에서 현재 상태를 확인한다.
2. isolated worktree에서 최소 완결 변경을 적용한다.
3. focused verification을 실행한다.
4. 게시 직전 `git fetch origin`을 다시 실행한다.
5. 관련 없는 main 변경은 최신 main 위에 재적용하고 focused verification을 다시 실행한다.
6. 관련 경로·contract가 바뀌었으면 최신 상태에 맞게 변경을 조정한다.
7. fast-forward push를 시도한다. 다른 세션이 먼저 게시하면 최신 main 기준으로 반복한다.

push를 별도 lock으로 직렬화하지 않는다. Git의 non-fast-forward 거부를 사용한다.

## 5. 검증

대표 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

모든 명령을 일괄 실행하지 않는다. 현재 package 위험과 contract에 필요한 focused bundle을 사용한다.
workaround, fail-open fallback, baseline·snapshot 갱신, unrelated cleanup으로 실패를 숨기지 않는다.

## 6. 프로젝트 경계

- 사용자 런타임은 정적 HTML/CSS/JavaScript다.
- 메인 허브는 `index.html`이다.
- 과목별 기능은 `domains/`, 공용 로직은 `shared/`에 둔다.
- 실험은 `experiments/`, 보호자·관리는 `guardian/`, `admin/`에 둔다.
- Next.js, Tauri, 별도 백엔드 API는 현재 범위 밖이다.
- Ocean Rescue 세부 계약은 가장 가까운 technical spec을 따른다.

## 7. 로컬 에이전트 위임

- 웹 세션에서 가능한 작업을 먼저 완료한다.
- 프롬프트는 최대 700줄이며 현재 package에 필요한 delta만 전달한다.
- objective, current state, included/excluded scope, Do / Do not, acceptance, verification, stop conditions를 포함한다.
- 일반 병렬 prompt는 reservation 없이 발급한다.
- exclusive 자원이 있을 때만 `RESERVATION_COMMENT / WORK / OWNER / EXPIRES / SCOPE`를 추가한다.
- 첫 mutation과 게시 직전에 최신 `origin/main`을 확인한다.
- task/parent key, custom claim ID, activation SHA, start window, dependency graph를 만들지 않는다.

## 8. 거버넌스 동결

실제 충돌이 반복 재현되고 worktree·고유 runtime identity·게시 전 overlap 확인으로 막을 수 없을 때만
새 coordination 규칙을 추가한다. validator·상태 머신·완료 보고 필드는 기본적으로 추가하지 않는다.

## 9. 완료 보고

```text
RESULT: PASS | BLOCKED
CHANGE: <one line>
VERIFY: <one line>
```

게시 시에만 `COMMIT`, 중단 시에만 `BLOCKER`와 `NEXT`를 추가한다.
