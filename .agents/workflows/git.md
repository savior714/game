---
situation: 변경 검증 후 commit과 main fast-forward 게시
level: Recommended
description: 격리된 작업 경계에서 의도한 파일만 commit하고 origin/main에 안전하게 게시하는 Git workflow
version: 2.0.0
last_updated: 2026-08-06
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

## 2. commit 전

1. 현재 branch, HEAD, remote main을 확인한다.
2. changed files와 diff를 확인한다.
3. 현재 failure domain 밖의 변경이 없는지 확인한다.
4. 필요한 focused test와 정적 진단을 실행한다.
5. secret·dotenv hard gate를 실행한다.
6. 생성 artifact가 포함되면 source/build 계약과 drift를 확인한다.

현재 저장소의 gate:

```bash
just commit-gate-hard
just commit-gate-soft
```

soft gate가 다른 원인의 오류를 드러내더라도 `--no-verify`로 우회하지 않는다.
현재 PASS 조건에 필요한 오류가 남으면 별도 failure domain으로 해결하거나 BLOCKED로 보고한다.

## 3. staging

- `git add .` 대신 정확한 파일 경로를 지정한다.
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

## 4. commit

commit message는 실제 변경을 설명한다.

```text
type(scope): imperative summary
```

예:

- `fix(quiz): reset feedback before next question`
- `test(quiz): prove restart clears transient state`
- `docs(agent): align browser workflow contract`

실행하지 않은 검증이나 완료되지 않은 장기 계획을 message에 쓰지 않는다.

## 5. 원격 이동

게시 직전 `origin/main`을 다시 확인한다.

- remote가 그대로면 push한다.
- remote가 이동했고 현재 변경과 겹치지 않으면 최신 main에 재적용한다.
- 재적용 후 직접 영향 검증을 반복한다.
- 실제 semantic conflict가 있으면 무리하게 자동 병합하지 않는다.
- non-fast-forward를 force로 해결하지 않는다.

원격 이동 자체만으로 BLOCKED 처리하지 않는다.

## 6. connector 기반 게시

repository connector로 직접 commit하는 경우:

1. 최신 main ref와 commit tree를 읽는다.
2. 수정 파일 blob을 만든다.
3. 최신 tree를 base로 candidate tree와 commit을 만든다.
4. candidate diff가 의도한 파일에만 한정되는지 확인한다.
5. main ref를 다시 읽는다.
6. parent가 여전히 최신이면 `force=false`로 ref를 이동한다.
7. 게시 후 remote ref와 changed files를 재확인한다.

대형 파일 전체 교체는 candidate commit diff가 정확한지 확인한 뒤 게시한다.

## 7. 완료

- intended files only
- focused verification PASS
- 필수 정적 진단 closure
- hard security gate PASS
- remote main fast-forward 확인
- working tree 또는 connector candidate에 unrelated mutation 없음

보고:

```text
RESULT: PASS
CHANGE: <한 문장>
VERIFY: <한 문장>
COMMIT: <게시 SHA>
```

게시하지 않은 작업에는 `COMMIT`을 적지 않는다.
