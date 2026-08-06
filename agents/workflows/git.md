# Git Workflow

Integration and publication branch: `main`

## 시작

```bash
git fetch origin
git rev-parse origin/main
git status --short

TASK_SLUG=${TASK_SLUG:?set a short task slug}
WORKTREE_ROOT=${WORKTREE_ROOT:-/Users/seungjulee/Desktop/Dev/.worktrees/game}
WORKTREE_DIR="$WORKTREE_ROOT/$TASK_SLUG"
mkdir -p "$WORKTREE_ROOT"
test ! -e "$WORKTREE_DIR"
git worktree add --detach "$WORKTREE_DIR" origin/main
cd "$WORKTREE_DIR"
```

- unrelated dirty state를 보존한다.
- mutation은 안정적인 프로젝트 전용 isolated worktree에서 수행한다.
- source checkout/worktree는 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 하위에 만들지 않는다.
- 실제 저장소가 다른 개발 루트에 있으면 같은 상위 디렉터리의 `.worktrees/game/<task-slug>` 같은 안정적인 sibling root를 사용한다.
- VS Code·OpenCode·LSP·`uv`·`pnpm`·Docker·브라우저·generator는 모두 `$WORKTREE_DIR` 자체를 workspace root와 CWD로 사용한다.
- main checkout, worktree, symlink alias, `/tmp`와 `/private/tmp` 경로를 혼합하지 않는다.
- OS temp는 prompt transport, patch/diff, 다운로드·압축 해제, 테스트 fixture와 폐기 가능한 비소스 산출물에만 사용한다.
- 일반 작업은 reservation 없이 시작한다.
- hotspot·runtime identity·generated artifact처럼 exclusive 자원이 있을 때만 Issue #1을 확인한다.

## 수정·검증

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

## Commit

```bash
git add -- <exact-paths>
git diff --cached --check
git diff --cached --name-only
git diff --cached
git commit -m "<message>"
```

## Optimistic publish

push 직전에 `git fetch origin`을 다시 실행한다.

- base 이후 변경이 현재 경로·contract와 무관하면 최신 main에서 만든 다른 안정적인 worktree에 안전하게 재적용한다.
- 재적용 후 focused verification과 정적 진단 closure를 다시 실행한다.
- 관련 경로·contract가 바뀌었으면 최신 상태를 읽고 현재 변경을 조정한 뒤 재검증한다.
- fast-forward push를 시도한다.
- 다른 세션이 먼저 push해 non-fast-forward로 거부되면 최신 main 기준으로 반복한다.
- force push나 merge commit으로 경쟁 변경을 덮지 않는다.
- SHA가 이동했다는 이유만으로 자동 중단하지 않는다.

## 완료

```bash
git push origin HEAD:main
git fetch origin
git status --short
```

완료 조건:

- focused verification PASS
- 현재 변경·수정 파일·직접 영향 범위의 LSP/typecheck/lint 오류 0
- 요구된 저장소 정적 게이트 PASS
- published commit이 `origin/main`에 존재함
- 대상 dirty가 없음

reservation을 사용했다면 `DONE`을 게시한다.

## cleanup

게시 또는 중단 후 자신이 만든 worktree만 제거한다.

```bash
git -C <main-checkout> worktree remove "$WORKTREE_DIR"
git -C <main-checkout> worktree prune
```

다른 세션의 worktree·branch·dirty state를 정리하지 않는다.