# Main-Only Git Workflow

Canonical branch: `main`

이 workflow는 `agents/workflows/work-package-claim.md`와 함께 사용한다.
claim은 작업 소유권을 정하고, 이 문서는 작업공간·remote advance·publish 안전성을 정한다.

## 1. 시작 상태

```bash
git fetch origin
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

- canonical checkout에서 직접 작업하면 branch가 `main`인지 확인한다.
- 병렬 mutation은 서로 다른 isolated worktree 또는 동등한 격리 작업공간에서 수행한다.
- detached isolated worktree는 `TASK_BASE_SHA`가 최신 `origin/main`의 commit인지 기록하고, publish 전 fast-forward 가능성을 다시 확인한다.
- claim-required 작업은 첫 mutation 전에 Issue #1의 owner 상태를 재확인한다.

## 2. Dirty ownership

각 dirty path를 분류한다.

- `OWNED_BY_THIS_TASK`
- `OWNED_BY_OTHER_SESSION`
- `PRE_EXISTING_UNKNOWN`
- `RUNTIME_ARTIFACT`

작업 write scope와 겹치지 않는 dirty는 보존한다.
겹치는 타 세션 또는 unknown dirty가 있으면 수정 전에 중단한다.

금지:

```bash
git reset --hard
git stash
git clean
git add .
git add -A
git commit -a
```

unowned path를 restore하거나 삭제하지 않는다.

## 3. Claim과 병렬 수정

- 전역적으로 write 세션 하나만 허용하는 정책은 사용하지 않는다.
- 동일·중복·overlap work package에는 owner 한 세션만 허용한다.
- 서로 다른 `TASK_KEY`이고 `WRITE_SCOPE`, `EXCLUSIVE_RESOURCES`, `DEPENDS_ON`이 충돌하지 않으면 여러 세션이 병렬 수정할 수 있다.
- 각 owner는 자신의 declared write/resource scope 밖을 수정하지 않는다.
- formatter·generator가 범위 밖 파일을 바꾸면 중단한다.
- 독립적인 새 outcome이나 추가 path가 필요하면 기존 claim을 release하고 새 경계로 다시 claim한다.
- local executor는 위임받은 `CLAIM_ID`를 다른 executor와 공유하지 않는다.

## 4. 수정과 검증

- 현재 work package의 objective와 acceptance checklist에 직접 대응하는 focused validation을 먼저 실행한다.
- 강하게 결합된 source, caller, type, test, configuration은 같은 verification bundle로 검증할 수 있다.
- 독립 failure는 현재 변경에 섞지 않고 remaining work로 분리한다.
- 장시간 browser/release/evidence 실행 직전에 Issue #1 comments와 exclusive resource overlap을 다시 확인한다.

## 5. Stage와 commit

```bash
git add -- <exact-paths>
git diff --cached --check
git diff --cached --name-only
git diff --cached
```

staged set이 claim의 `WRITE_SCOPE`와 현재 work package의 실제 changed paths에 정확히 포함될 때만 commit을 만든다.

## 6. Remote advance

push 직전에 다음을 수행한다.

1. Issue #1 comments에서 active overlap claim을 재확인한다.
2. `origin/main`을 갱신한다.
3. `BASE_SHA` 이후 변경과 현재 changed paths의 경로·semantic overlap을 판정한다.

- 원격 변경이 write scope와 직접 closure에 겹치지 않으면 최신 `origin/main` 위에 안전하게 재적용하고 focused validation을 다시 실행한다.
- overlap이면 `BLOCKED_REMOTE_OVERLAP`으로 중단한다.
- SHA가 달라졌다는 이유만으로 자동 중단하지 않는다.
- rebase·merge·cherry-pick 여부보다 최종 publish가 fast-forward이고 unrelated 변경을 보존하는지가 기준이다.
- force push와 merge commit으로 경쟁 변경을 덮지 않는다.

## 7. Closure

```bash
git push origin main
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

완료 조건:

- focused validation PASS
- push 성공
- 최종 published commit이 `origin/main`에 존재
- 작업 대상 dirty 없음
- unrelated dirty 보존
- blocker 없음
- Issue #1에 `RELEASE` 게시

`BLOCKED` 또는 `ABANDONED`도 claim을 계속 보유하는 상태가 아니다. 현재 상태와 resume condition을 handoff에 남기고 release한다.
