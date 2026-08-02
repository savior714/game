# Main-Only Git Workflow

Canonical branch: `main`

## 1. 시작 상태

```bash
git fetch origin
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

현재 branch가 canonical branch가 아니면 write를 시작하지 않는다.

## 2. Dirty ownership

각 dirty path를 분류한다.

- `OWNED_BY_THIS_TASK`
- `OWNED_BY_OTHER_SESSION`
- `PRE_EXISTING_UNKNOWN`
- `RUNTIME_ARTIFACT`

작업 write set과 겹치지 않는 dirty는 보존한다.
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

## 3. 수정과 검증

- 한 시점에 write 세션 하나
- 명시한 write set 밖을 수정하지 않음
- formatter·generator가 범위 밖 파일을 바꾸면 중단
- 현재 가설에 직접 대응하는 targeted validation을 먼저 실행
- 실패하면 다른 failure를 같이 수정하지 않음

## 4. Stage와 commit

```bash
git add -- <exact-paths>
git diff --cached --check
git diff --cached --name-only
git diff --cached
```

staged set이 write set과 정확히 일치할 때만 원자적 commit 하나를 만든다.

## 5. Remote advance

push 직전에 `origin/main`을 갱신한다.

- 원격 변경이 write set과 직접 closure에 겹치지 않으면 fast-forward 후 재검증
- overlap이면 `BLOCKED_REMOTE_OVERLAP`
- local commit 뒤 원격이 전진하면 rebase·merge commit으로 해결하지 않고
  `BLOCKED_REMOTE_ADVANCE_AFTER_COMMIT`
- SHA가 달라졌다는 이유만으로 자동 중단하지 않음

## 6. Closure

```bash
git push origin main
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

완료 조건:

- targeted validation PASS
- push 성공
- `HEAD == origin/main`
- 작업 대상 dirty 없음
- unrelated dirty 보존
- blocker 없음
