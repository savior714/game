---
situation: 변경 검증 후 commit과 main fast-forward 게시
level: Recommended
description: 격리된 작업 경계에서 의도한 파일만 commit하고 origin/main에 안전하게 게시하는 Git workflow
version: 3.0.1
last_updated: 2026-08-07
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Git workflow

검증 규칙은 [`verification.md`](../core/verification.md), 보안은 [`security.md`](../core/security.md)를 따른다.

## 1. 기본 정책

- 통합·게시 기준은 `origin/main`이다.
- 기본 게시 방식은 main fast-forward push다.
- PR·feature branch는 사용자가 명시적으로 요청한 경우에만 사용한다.
- mutation은 최신 main에서 만든 isolated worktree 또는 동등한 격리 공간에서 수행한다.
- force push, history rewrite, `--no-verify`는 금지한다.
- unrelated dirty state를 보존하고 전역 stash나 reset으로 숨기지 않는다.
- 일반 작업은 reservation 없이 시작한다.
- hotspot·runtime identity·generated artifact처럼 exclusive 자원이 있을 때만 Issue #1을 확인한다.

## 2. 시작

```bash
git fetch origin
git rev-parse origin/main
git status --short

TASK_SLUG=${TASK_SLUG:?set a short task slug}
WORKTREE_ROOT=${WORKTREE_ROOT:-/Users/seungjulee/Desktop/Dev/.worktrees/game}
WORKTREE_DIR="$WORKTREE_ROOT/$TASK_SLUG"
WORKTREE_CREATED_AT=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$WORKTREE_ROOT"
test ! -e "$WORKTREE_DIR"
git worktree add \
  --lock \
  --reason "owner=game-agent task=$TASK_SLUG created=$WORKTREE_CREATED_AT phase=primary" \
  --detach "$WORKTREE_DIR" origin/main
cd "$WORKTREE_DIR"
```

- 새 task worktree는 생성 시점부터 lock하여 현재 agent가 소유한 활성 workspace임을 Git metadata에 남긴다.
- lock reason에는 owner/tool, task 식별자, 생성 시각과 phase처럼 짧은 운영 식별자만 기록한다. PII, secret 또는 prompt 원문을 넣지 않는다.
- source checkout/worktree는 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 하위에 만들지 않는다.
- 실제 저장소가 다른 개발 루트에 있으면 같은 상위 디렉터리의 `.worktrees/game/<task-slug>` 같은 안정적인 sibling root를 사용한다.
- VS Code·OpenCode·LSP·`uv`·`pnpm`·Docker·브라우저·generator는 모두 `$WORKTREE_DIR` 자체를 workspace root와 CWD로 사용한다.
- main checkout, worktree, symlink alias, `/tmp`와 `/private/tmp` 경로를 혼합하지 않는다.
- OS temp는 prompt transport, patch/diff, 다운로드·압축 해제, 테스트 fixture와 폐기 가능한 비소스 산출물에만 사용한다.

## 3. 수정·검증

- coherent objective와 declared scope 안에서 최소 완결 변경을 한다.
- 강하게 결합된 source, caller, test, asset, config는 함께 수정할 수 있다.
- formatter·generator가 unrelated path를 바꾸면 분리하거나 중단한다.
- focused verification을 먼저 실행한다.

### LSP·typecheck·lint closure

1. 변경 전 `$WORKTREE_DIR`에서 관련 LSP·typecheck·lint baseline을 확인한다.
2. 현재 변경으로 새로 생긴 오류와 수정 파일·직접 영향 모듈의 오류를 하나의 failure domain으로 수정한다.
3. 같은 명령으로 해당 오류가 사라졌는지 독립 검증한다.
4. 저장소 정적 게이트가 다른 기존 오류를 드러내면 현재 원인과 섞어 대규모 수정하지 않는다. 다음 정적 failure domain 하나를 선택해 순차 해결한다.
5. 잘못된 workspace root, SDK/interpreter, 누락된 의존성, stale cache/index, generated/vendor 오분석이 원인이면 production code가 아니라 환경·설정을 수정하고 동일 진단을 재실행한다.
6. broad ignore, `type: ignore`, `noqa`, ESLint disable, 검사 대상 축소, baseline·snapshot 갱신으로 오류를 숨기지 않는다.

현재 변경과 직접 영향 범위의 정적 오류가 0이고 요구된 정적 게이트가 통과하기 전에는 PASS·commit·push하지 않는다.
LSP·typecheck·lint 오류를 “pre-existing” 또는 “out of scope”라는 이유만으로 보고하고 종료하지 않는다.
안전하게 해결할 수 없는 정적 오류가 남으면 정확한 재현 명령과 원인을 포함해 `BLOCKED`로 종료한다.

현재 저장소의 gate:

```bash
just commit-gate-hard
just commit-gate-soft
```

soft gate가 다른 원인의 오류를 드러내더라도 `--no-verify`로 우회하지 않는다.
현재 PASS 조건에 필요한 오류가 남으면 별도 failure domain으로 해결하거나 BLOCKED로 보고한다.

## 4. staging

- 전체 선택 스테이징 대신 정확한 파일 경로를 지정한다.
- secret, local database, IDE state, browser report, temporary artifact를 stage하지 않는다.
- 하나의 commit에는 한 coherent failure domain만 포함한다.
- 같은 원인을 닫는 source, caller, test, config는 함께 stage할 수 있다.
- 문서 진행 상태나 unrelated cleanup을 기능 commit에 섞지 않는다.

stage 후 반드시 확인한다.

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached
```

## 5. commit

commit message는 실제 변경을 설명한다.

```text
type(scope): imperative summary
```

예:

- `fix(quiz): reset feedback before next question`
- `test(quiz): prove restart clears transient state`
- `docs(agent): align browser workflow contract`

실행하지 않은 검증이나 완료되지 않은 장기 계획을 message에 쓰지 않는다.

## 6. Optimistic publish

push 직전에 `git fetch origin`을 다시 실행한다.

- base 이후 변경이 현재 경로·contract와 무관하면 최신 main에서 만든 다른 안정적인 worktree에 안전하게 재적용한다.
- 재적용용 worktree도 별도 활성 workspace이므로 primary worktree와 동일한 lock lifecycle을 사용한다.
- 재적용 후 focused verification과 정적 진단 closure를 다시 실행한다.
- 관련 경로·contract가 바뀌었으면 최신 상태를 읽고 현재 변경을 조정한 뒤 재검증한다.
- fast-forward push를 시도한다.
- 다른 세션이 먼저 push해 non-fast-forward로 거부되면 최신 main 기준으로 반복한다.
- force push나 merge commit으로 경쟁 변경을 덮지 않는다.
- SHA가 이동했다는 이유만으로 자동 중단하지 않는다.
- 원격 이동 자체만으로 BLOCKED 처리하지 않는다.

재적용 worktree를 만들 때도 생성과 동시에 lock한다.

```bash
REAPPLY_DIR="$WORKTREE_ROOT/${TASK_SLUG}-reapply"
REAPPLY_CREATED_AT=$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$REAPPLY_DIR"
git worktree add \
  --lock \
  --reason "owner=game-agent task=$TASK_SLUG created=$REAPPLY_CREATED_AT phase=reapply" \
  --detach "$REAPPLY_DIR" origin/main
```

## 7. connector 기반 게시

repository connector로 직접 commit하는 경우:

1. 최신 main ref와 commit tree를 읽는다.
2. 수정 파일 blob을 만든다.
3. 최신 tree를 base로 candidate tree와 commit을 만든다.
4. candidate diff가 의도한 파일에만 한정되는지 확인한다.
5. main ref를 다시 읽는다.
6. parent가 여전히 최신이면 `force=false`로 ref를 이동한다.
7. 게시 후 remote ref와 changed files를 재확인한다.

대형 파일 전체 교체는 candidate commit diff가 정확한지 확인한 뒤 게시한다.

## 8. 완료

일반 Git CLI 게시:

```bash
git push origin HEAD:main
git fetch origin
git status --short
```

완료 조건:

- intended files only
- focused verification PASS
- 현재 변경·수정 파일·직접 영향 범위의 LSP/typecheck/lint 오류 0
- 요구된 저장소 정적 게이트 PASS
- remote main fast-forward 확인
- published commit이 `origin/main`에 존재함
- 대상 dirty가 없음
- working tree 또는 connector candidate에 unrelated mutation 없음

reservation을 사용했다면 `DONE`을 게시한다.

보고:

```text
RESULT: PASS
CHANGE: <한 문장>
VERIFY: <한 문장>
COMMIT: <게시 SHA>
```

게시하지 않은 작업에는 `COMMIT`을 적지 않는다.

## 9. cleanup

게시에 성공한 뒤 자신이 만든 detached worktree만 회수한다. 중단된 작업, dirty worktree 또는 아직 `origin/main`에 포함되지 않은 HEAD는 unlock하거나 제거하지 않고 경로를 보존한다.

```bash
git -C <main-checkout> fetch origin --prune
test -z "$(git -C "$WORKTREE_DIR" status --porcelain)"
WORKTREE_HEAD=$(git -C "$WORKTREE_DIR" rev-parse HEAD)
git -C <main-checkout> merge-base --is-ancestor "$WORKTREE_HEAD" origin/main
git -C <main-checkout> worktree unlock "$WORKTREE_DIR"
git -C <main-checkout> worktree remove "$WORKTREE_DIR"
git -C <main-checkout> worktree prune --dry-run --verbose
```

- unlock은 삭제 직전의 마지막 단계다. clean, published, self-owned 조건을 모두 확인하기 전에는 unlock하지 않는다.
- plain `git worktree remove`가 실패하면 `--force`로 우회하지 않고 worktree를 보존한다.
- `git worktree prune`은 정상 worktree 제거 수단이 아니다. `--dry-run`에서 이미 경로가 사라진 stale metadata가 확인된 경우에만 별도로 실행한다.
- 다른 세션의 worktree·branch·dirty state를 정리하지 않는다.
