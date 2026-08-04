# Git Workflow

Canonical branch: `main`

## 시작

```bash
git fetch origin
git rev-parse origin/main
git status --short
```

- unrelated dirty state를 보존한다.
- 병렬 mutation은 isolated worktree 또는 동등한 격리 공간을 사용한다.
- 일반 작업은 reservation 없이 시작한다.
- hotspot·canonical runtime·generated artifact처럼 exclusive 자원이 있을 때만 Issue #1을 확인한다.

## 수정·검증

- coherent objective와 declared scope 안에서 최소 완결 변경을 한다.
- 강하게 결합된 source, caller, test, asset, config는 함께 수정할 수 있다.
- formatter·generator가 unrelated path를 바꾸면 분리하거나 중단한다.
- focused verification을 먼저 실행한다.

## Commit

```bash
git add -- <exact-paths>
git diff --cached --name-only
git diff --cached
git commit -m "<message>"
```

## Optimistic publish

push 직전에 `git fetch origin`을 다시 실행한다.

- base 이후 변경이 현재 경로·contract와 무관하면 최신 main 위에 rebase 또는 안전하게 재적용한다.
- 재적용 후 focused verification을 다시 실행한다.
- 관련 경로·contract가 바뀌었으면 최신 상태를 읽고 현재 변경을 조정한 뒤 재검증한다.
- fast-forward push를 시도한다.
- 다른 세션이 먼저 push해 non-fast-forward로 거부되면 최신 main 기준으로 반복한다.
- force push나 merge commit으로 경쟁 변경을 덮지 않는다.
- SHA가 이동했다는 이유만으로 자동 중단하지 않는다.

## 완료

```bash
git push origin main
git fetch origin
git status --short
```

published commit이 `origin/main`에 존재하고 대상 dirty가 없어야 한다.
reservation을 사용했다면 `DONE`을 게시한다.
