# AGENTS.md — AidenGame 실행 규약

이 문서는 저장소 작업의 최소 실행 계약이다. Plan·Blueprint·라우팅 매니페스트·장문 보고는 일반 작업의 선행 조건이 아니다.

## 1. 우선순위

1. 사용자의 현재 요청
2. 이 문서
3. `PROJECT_RULES.md`
4. 대상 코드와 테스트
5. 기타 문서와 과거 계획

## 2. Git과 work package

- 통합·게시 기준 브랜치는 `origin/main`이며 기본 방식은 `main` fast-forward push다.
- PR과 feature branch는 사용자가 요청한 경우에만 사용한다.
- 병렬 mutation은 isolated worktree 또는 동등한 격리 공간을 사용한다.
- source worktree는 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 하위에 만들지 않는다.
- 기본 worktree root는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`이며, 실제 저장소가 다른 개발 루트에 있으면 같은 상위 디렉터리의 안정적인 `.worktrees/game/<task-slug>` sibling 경로를 사용한다.
- VS Code·OpenCode·LSP·uv·pnpm·Docker·브라우저 E2E·generated artifact 검증은 모두 실제 작업 worktree 하나를 동일한 workspace root와 CWD로 사용한다. main checkout, worktree, symlink alias, `/tmp`와 `/private/tmp` 경로를 혼합하지 않는다.
- OS temp는 prompt transport, patch/diff, 다운로드·압축 해제, 테스트 fixture와 폐기 가능한 비소스 산출물에만 사용한다. 임시 source tree를 프로젝트 workspace로 열지 않는다.
- 기본값은 reservation 없는 낙관적 병렬 실행이다.
- 하나의 package는 coherent objective와 rollback 경계를 가진다.
- 강하게 결합된 source, caller, type, test, asset, config는 함께 변경할 수 있다.
- unrelated product change와 rollback 경계가 다른 문제만 분리한다.
- 서로 다른 LSP·typecheck·lint failure domain은 한 패치에 섞지 않고 하나씩 수정·독립 검증한다.
- force push와 `--no-verify`는 금지한다.
- unrelated dirty state를 보존한다.

## 3. Exclusive reservation

`agents/workflows/work-package-claim.md`는 일반 작업 claim이 아니라 희소 자원의 reservation이다.

다음에만 Issue #1을 사용한다.

- 같은 semantic hotspot/shared contract
- 같은 generated bundle·atlas·registry 또는 publication destination
- 같은 browser/runtime identity, fixed port, profile, output directory
- 같은 migration/schema 자원(해당되는 경우)

서로 다른 기능 디렉터리, test, UI flow, 독립 bug fix는 reservation 없이 병렬 실행한다.
같은 파일이라는 이유만으로 자동 예약하지 않는다.
reservation에는 `WORK / OWNER / EXPIRES / SCOPE`만 사용한다.

## 4. 작업과 게시

1. 최신 `origin/main`에서 현재 상태를 확인한다.
2. 안정적인 프로젝트 전용 경로의 isolated worktree를 만들고 그 worktree 자체를 IDE·LSP·실행 workspace root로 연다.
3. 최소 완결 변경을 적용한다.
4. focused verification과 정적 진단 closure를 실행한다.
5. 게시 직전 `git fetch origin`을 다시 실행한다.
6. 관련 없는 main 변경은 최신 main 위에 재적용하고 focused verification과 정적 진단 closure를 다시 실행한다.
7. 관련 경로·contract가 바뀌었으면 최신 상태에 맞게 변경을 조정한다.
8. fast-forward push를 시도한다. 다른 세션이 먼저 게시하면 최신 main 기준으로 반복한다.

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

### 정적 진단 closure

- 작업 시작 시 안정적인 worktree root에서 관련 LSP·typecheck·lint baseline을 확인한다.
- 현재 변경으로 새로 생긴 오류와 수정 파일·직접 영향 모듈의 오류는 현재 package에서 반드시 수정한다.
- 잘못된 workspace root, SDK/interpreter, 누락된 의존성, stale cache/index, generated/vendor 오분석이 원인이면 production code를 억지로 바꾸지 말고 환경·설정을 바로잡아 같은 진단을 재실행한다.
- broad ignore, `type: ignore`, `noqa`, ESLint disable, 검사 대상 축소로 오류를 덮지 않는다.
- 저장소 전체 정적 게이트가 다른 기존 오류를 드러내면 현재 원인과 섞어 대규모 수정하지 않는다. 현재 failure domain을 독립 검증한 뒤 다음 정적 failure domain 하나를 선택해 계속 해결한다.
- 최종 PASS는 현재 변경과 직접 영향 범위의 정적 오류가 0이고 이번 작업에 요구되는 저장소 정적 게이트가 통과했을 때만 허용한다. 안전하게 해결할 수 없는 정적 오류가 남으면 정확한 재현 명령과 원인을 포함해 `BLOCKED`로 보고한다.

workaround, fail-open fallback, baseline·snapshot 갱신, unrelated cleanup으로 실패를 숨기지 않는다.
LSP·typecheck·lint 오류를 “pre-existing” 또는 “out of scope”라는 이유만으로 보고하고 PASS하지 않는다.

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
- objective, current state, workspace, included/excluded scope, Do / Do not, acceptance, verification, stop conditions를 포함한다.
- source worktree는 안정적인 `.worktrees/game/<task-slug>` 경로를 사용하고 IDE·LSP·명령의 workspace root를 그 경로 하나로 고정하도록 명시한다.
- 현재 변경이 만든 정적 오류와 수정 파일·직접 영향 모듈의 오류를 0으로 만들고, 별도 정적 오류는 다음 failure domain으로 순차 해결하도록 명시한다.
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