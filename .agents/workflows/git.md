---
situation: 커밋
# trigger: /git  ← catalog metadata only; Read this file before executing (error_patterns §16.1)
level: Mandatory
description: Git Commit & Push - WIP 슬라이스 커밋·1회 push
version: 1.4.0
last_updated: 2026-06-08
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Git Commit & Push (`/git`)

세션 WIP를 SSOT에 반영한 뒤 **슬라이스별 커밋** → **push 1회**로 마무리. **트리거 시 본 문서 1회 Read.**

**검증 레이어 SSOT**: [verification.md](../core/verification.md) — Scope L1/L2/L3.

---

## 금지

| 규칙 | 이유 |
| :--- | :--- |
| `git add .` (일괄 스테이징) | 도메인 혼합·비밀 파일 유입 |
| `git push --force` / `--force-with-lease` | 원격 히스토리 파괴 |
| 기본 `--no-verify` | hard 게이트(dotenv·비밀) 우회 — PR·`just lint`에서 재차단 |
| 슬라이스 미완료 상태에서 push | unstaged WIP 잔존 시 §5.1 재실행 |
| NEVER_STAGE 경로 커밋 | 로컬·비밀·아티팩트 — §5.0 표 |

---

## CLI (권장 순서)

| 단계 | 명령 |
| :--- | :--- |
| hard 선제 검증 | `just commit-gate-hard` (빠름, 보안 관련) |
| soft 선제 검증 | `just commit-gate-soft` (느림, lint/ty 포함) |
| WIP 보존 | `just wip "pre-commit-$(date +%Y%m%d_%H%M)"` |
| 슬라이스 커밋 | `git add <paths>` → `git commit -m "type(scope): 요약"` (§5.1 루프) |
| push 전 동기화 | `git pull --rebase origin $(git branch --show-current)` |
| push | `git push origin $(git branch --show-current)` |

**commit-gate 층**: hard(`env-lint`, `staged_secret_gate`) — `--no-verify` **금지** · soft(`lint-fix`, archive) — 예외 가능하나 후속 통과 필요.

### 게이트 실패 시 원인 분류

`just commit-gate` 실패 시 다음 순서로 원인 분류:

```bash
just commit-gate-hard   # 1. hard 게이트 (보안) — 먼저 확인
just commit-gate-soft   # 2. soft 게이트 (lint/ty) — hard 통과 시 확인
```

**hard 게이트 실패** → 변경사항 수정 후 재시도 (우회 금지)
**soft 게이트 실패** → §6.1 ty 에러 pre-existing 확인 → §6.2 `--no-verify` 우회 (필요 시)

### §6.1 ty 에러 pre-existing 확인

```bash
# 내 변경 파일에서만 ty 에러가 발생하는지 확인
just ty 2>&1 | grep "error\[" | while read -r line; do
  file=$(echo "$line" | grep -oP '--> \K[^:]+')
  git diff --name-only | grep -q "$file" && echo "MY CHANGE: $file" || echo "PRE-EXISTING: $file"
done
```

pre-existing 에러인 경우 `--no-verify`로 우회 가능 (hard 게이트는 통과했으므로).

### §6.2 `--no-verify` 사용 시 commit 메시지에 명시

pre-existing 에러로 `--no-verify` 사용할 때 **반드시** commit 메시지에 원인 명시:

```bash
git commit -m "type(scope): 요약

Note: ty errors are pre-existing (file1.py, file2.py)
" --no-verify
```

**금지**: 이유 없이 `--no-verify` 사용 → 추후 리뷰 시 원인 추적 불가

### §6.3 ARG001 미사용 인자 처리

```bash
# 미사용 인자 발견 시:
# 1. 정말 미사용이면 함수 시그니처에서 제거
# 2. API 계약상 필요하면 _prefix 패턴 사용 (의도적 미사용 명시)
# 3. 아니면 # noqa: ARG001 주석 추가
```

**규칙**: `_prefix`, `_env_name` 등 underscore prefix는 "의도적 미사용"을 명시하는 좋은 관행

### §6.4 unstaged 변경사항 정리

push 전 rebase 실패 방지:

```bash
# unstaged 변경사항 확인 (tracked 파일만)
git status --short | grep -v "^??"

# unstaged가 많으면 stash 후 push
git stash push -m "pre-push-wip"
git push origin $(git branch --show-current)
git stash pop
```

**stash pathspec 구문**: `git stash push -m "message" -- path/to/file` 형태로 `--` 뒤에 경로를 명시해야 함. `git stash push -m "message" path/to/file` (dash 없이)는 구문 오류.

### §6.5 stash rebase 패턴

rebase 전 unstaged 변경사항 처리:

```bash
# rebase 전 stash
git stash push -m "pre-rebase-wip"

# rebase 실행
git pull --rebase origin $(git branch --show-current)

# stash 복원
git stash pop
```

**주의**: `git stash`만 실행하면 전체 unstaged가 stash됨. 특정 파일만 stash하려면 `git stash push -m "message" -- path/to/file` 사용.

---

## 게이트 — §5.0~§5.2 슬라이스 루프

**완료 조건**: `git status --short`에 커밋 대상 없음 (NEVER_STAGE·제외 untracked만 잔존 가능).

### §5.0 NEVER_STAGE (스테이징 금지)

| 패턴 | 사유 |
|------|------|
| `.agents/route/session-manifest.json`, `.agent/route/**` | 세션 route 매니페스트 |
| `.kilo/**`, `.cursor/**` | IDE·러너 로컬 |
| `test-results/**`, `playwright-report/**` | E2E 아티팩트 |
| `.env`, `.env.*`, `*.pem`, `*.key`, `*.db` | 비밀·로컬 DB |

### §5.1 슬라이스 루프 (Mandatory)

```text
WHILE 커밋 대상(M/N/??) 존재:
  1. §5.0.1 휴리스틱으로 다음 슬라이스 S 선택
  2. git add <path1> <path2> ...  (S만)
  3. Scope 검증 (해당 paths 기준 최소 1회)
  4. git commit -m "type(scope): [ID] 요약" (+ 본문 Verify 1줄)
  5. commit-gate 실패 → 해당 슬라이스만 수정 → 3부터 (최대 3회)
END WHILE
```

- **혼합 금지**: 서로 다른 scope를 한 커밋에 넣지 않는다.
- **push 거부** → rebase 후 재시도 (`force push` 금지).

**§5.0.1 슬라이스 휴리스틱** (동일 prefix·Blueprint·`git diff` 주제 → 한 슬라이스):

| 경로 prefix | type(scope) 예 |
|-------------|----------------|
| `.agents/**`, `AGENTS.md`, `scripts/agent/**` | `docs(agent)` |
| `docs/plans/**`, `docs/discussions/**` | `docs(plans)` / `docs(...)` |
| `apps/renderer/**` | `feat(renderer)` / `fix(renderer)` |
| `src/**`, `tests/**` | `fix(backend)` / `test(...)` |
| `Justfile`, `scripts/verify/**` | `chore(tools)` |

### §5.2 Push

모든 슬라이스 커밋 **후** 1회. rebase 전 unstaged가 NEVER_STAGE 외에 있으면 §5.1 미완료.

**unstaged rebase 패턴**: push 전 unstaged 변경사항이 있으면 stash → rebase → pop:

```bash
# push 전 unstaged 확인
git status --short | grep -v "^??"

# unstaged 있으면 stash
git stash push -m "pre-push-wip"

# rebase + push
git pull --rebase origin $(git branch --show-current)
git push origin $(git branch --show-current)

# stash 복원
git stash pop
```

**에이전트 종료점**: push 성공까지. PR 생성·병합·GitHub MCP 원격 작업은 **기본 수행하지 않음**.

---

## lazy (필요 시 Read)

| 주제 | SSOT |
| :--- | :--- |
| 슬라이스 경계 모호 | `git diff` 의미·Blueprint 참조 — **더 좁은 scope**로 분리 |
| 불확실 상황 대응 | [verification.md](../core/verification.md) · [memory_hygiene.md](../core/memory_hygiene.md) |
| SSOT 문서 갱신 (0~1단계) | `PROJECT_RULES.md` §6 · `docs/agent-context/memory/MEMORY.md` (링크만) |
| Scope L1/L2/L3 | [verification.md](../core/verification.md) |
| 커밋 메시지 형식 | `PROJECT_RULES.md` §5 |
| Feature-split commits | AGENTS.md §5 pointer → **본 문서 §5.1** |
| Verify Report | `PROJECT_RULES.md` §4.4 |
