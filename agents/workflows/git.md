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
- 둘 이상의 mutation 세션 또는 shared resource가 있을 때만 Issue #1 최소 lock을 확인한다.

## 수정·검증

- 한 failure domain과 allowed paths 안에서 수정한다.
- formatter·generator가 범위 밖 파일을 바꾸면 중단한다.
- focused verification을 먼저 실행한다.
- 독립 failure는 별도 작업으로 남긴다.

## Commit

```bash
git add -- <exact-paths>
git diff --cached --name-only
git diff --cached
git commit -m "<message>"
```

## Remote advance

push 직전에 `origin/main`을 갱신한다.

- 현재 변경 경로와 겹치지 않으면 최신 main 위에 재적용하고 focused verification을 다시 실행한다.
- 겹치면 중단한다.
- SHA가 달라졌다는 이유만으로 자동 중단하지 않는다.
- force push나 merge commit으로 경쟁 변경을 덮지 않는다.

## 완료

```bash
git push origin main
git fetch origin
git status --short
```

published commit이 `origin/main`에 존재하고 대상 dirty가 없어야 한다. 잠금을 사용했다면 최소 `RELEASE`를 게시한다.
