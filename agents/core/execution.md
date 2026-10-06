---
scope:
- '*'
always_apply: false
priority: 1
domain: core
last_verified: 2026-10-06
verify_with:
- uv run pytest -q tests/test_core_agent_contract_consistency.py
---
<!-- Language: ko -->

# AidenGame 실행 규칙

이 문서는 작업 시작부터 게시까지의 실행 순서와 workspace·commit·게시 lifecycle을 정의한다.
도구 선택은 [`routing.md`](routing.md), 파괴적 Git 안전 판정은
[`../workflows/git.md`](../workflows/git.md), 검증은 [`verification.md`](verification.md), 보고는
[`reporting.md`](reporting.md)를 따른다.

## 1. 작업 시작

1. 사용자의 현재 요청을 확인한다.
2. 최신 `origin/main`과 대상 파일·직접 관련 테스트를 읽는다.
3. `AGENTS.md`의 권위 라우팅으로 해당 failure domain의 owner를 정해 읽는다.
4. 현재 failure domain, 재현 조건, binary criterion을 한 문장으로 고정한다.
5. 동결 범위나 forbidden action과 충돌하지 않는지 확인한다.

범위가 지정되지 않았다면 현재 제품 SSOT인 `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`의 current
development priority에서 시작한다.
계획 관련 단어가 있다는 이유만으로 plan 파일을 만들지 않는다.

## 2. 조사와 진단

- 파일 존재, import graph, caller, fallback, generated artifact 경계를 실측한다.
- 검색 결과는 조사 자료이며 존재 자체를 결함으로 취급하지 않는다.
- 실패를 재현할 수 있는 가장 작은 경로를 찾는다.
- 여러 원인이 나오면 현재 binary criterion과 직접 연결된 하나만 선택한다.
- baseline이 이미 PASS면 과거 보고만으로 결함을 재작업하지 않는다.

환경·workspace·SDK·dependency·cache·generated/vendor 오분석 가능성을 production code 변경보다 먼저 확인한다.

## 3. 수정

- 대상 파일의 최신 내용을 다시 읽는다.
- 부분 수정은 정확히 식별되는 최소 블록을 사용한다.
- 대형 파일 전체 교체는 원본과 후보 diff를 확인한 후에만 수행한다.
- 같은 failure domain의 source, caller, test, config는 함께 변경할 수 있다.
- unrelated refactor, formatting, dependency upgrade, 문서 상태 갱신을 섞지 않는다.
- generated artifact를 수동 편집하지 않는다.

편집 실패 시 더 넓은 치환으로 즉시 재시도하지 않고 파일을 다시 읽어 원인을 확인한다.

## 4. 테스트와 TDD

재현 가능한 결함은 가능하면 수정 전에 failing contract를 확인한다.
다만 현재 저장소에서 이미 실패가 명확히 재현되고 있거나 문서·설정 drift를 직접 비교할 수 있는 경우, 동일 실패를 중복 생성하기 위해 인위적인 테스트를 먼저 만들지 않는다.

새 테스트는 잡아낼 구체적 failure mode가 있을 때만 추가한다.
assertion 없는 테스트나 일정 상태 문자열만 검증하는 테스트를 만들지 않는다.

## 5. 검증

다음 순서로 확장한다.

1. 현재 binary criterion의 focused check
2. 수정 파일과 직접 영향 모듈의 lint/typecheck
3. 필요한 browser, build, artifact, rollback 검증
4. 공유 경계 변경 시 영향받는 regression
5. repository-wide gate는 실제 위험이나 정책이 요구할 때

필수 criterion을 실행하지 못했으면 이유를 기록하고 PASS로 표시하지 않는다.
검증 실패를 broad ignore나 범위 축소로 숨기지 않는다.

## 6. workspace와 Git lifecycle

`MODE: BUILD` mutation은 tracking `main`이 아니라 최신 `origin/main`에서 만든 격리 worktree에서
수행한다. 실제 명령과 lock·정리 절차는 이 문서가 소유하고, 그 상태 전이가 안전한지는
[`../workflows/git.md`](../workflows/git.md)가 판정한다.

### 6.1 worktree 생성·lock

- 기본 worktree root는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`다. 저장소가 다른
  개발 루트에 있으면 같은 상위 디렉터리의 `.worktrees/game/<task-slug>` sibling root를 사용한다.
- 새 primary/reapply worktree는 생성 시점부터 lock해 현재 활성 workspace임을 Git metadata에 남긴다.
- lock reason에는 owner/tool, task 식별자, 생성 시각, phase처럼 짧은 운영 식별자만 기록하고 PII,
  secret, prompt 원문을 넣지 않는다.
- source worktree를 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 하위에 만들지 않는다.
- IDE, LSP, `uv`, `pnpm`, Docker, 브라우저 E2E, generated artifact 검증은 모두 작업 worktree 하나를
  동일한 workspace root와 CWD로 사용한다. main checkout, worktree, symlink alias, OS 임시 경로를
  혼합하지 않는다.
- OS temp는 prompt transport, patch/diff, 다운로드·압축 해제, 테스트 fixture와 폐기 가능한 비소스
  산출물에만 사용한다.

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

### 6.2 정적 진단과 commit gate

- coherent objective와 선언된 scope 안에서 최소 완결 변경을 한다.
- 강하게 결합된 source, caller, test, asset, config는 함께 수정할 수 있다.
- formatter·generator가 unrelated path를 바꾸면 분리하거나 중단한다.
- focused verification을 먼저 실행한다.
- LSP·typecheck·lint closure와 `BLOCKED` 판정 기준은
  [`verification.md`](verification.md)를 따른다.

현재 저장소의 gate:

```bash
just commit-gate-hard
just commit-gate-soft
```

soft gate가 다른 원인의 오류를 드러내더라도 `--no-verify`로 우회하지 않는다.
현재 PASS 조건에 필요한 오류가 남으면 별도 failure domain으로 해결하거나 `BLOCKED`로 보고한다.

### 6.3 staging과 commit

- 통합·게시 기준은 `origin/main`이며 기본 게시 방식은 main fast-forward push다.
  PR·feature branch는 사용자가 명시적으로 요청한 경우에만 사용한다.
- 전체 선택 스테이징 대신 정확한 파일 경로를 지정한다.
- secret, local database, IDE state, browser report, temporary artifact를 stage하지 않는다.
- 하나의 commit에는 한 coherent failure domain만 포함한다.
- 같은 원인을 닫는 source, caller, test, config는 함께 stage할 수 있다.
- 문서 진행 상태나 unrelated cleanup을 기능 commit에 섞지 않는다.
- unrelated dirty state를 보존하고 전역 stash나 reset으로 숨기지 않는다.
- force push, history rewrite, `--no-verify`는 금지한다.

stage 후 반드시 확인한다.

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached
```

commit message는 실제 변경을 설명한다.

```text
type(scope): imperative summary
```

예:

- `fix(quiz): reset feedback before next question`
- `test(quiz): prove restart clears transient state`
- `docs(agent): route git safety to a single owner`

실행하지 않은 검증이나 완료되지 않은 장기 계획을 message에 쓰지 않는다.

### 6.4 connector 기반 게시

repository connector로 직접 commit하는 경우:

1. 최신 main ref와 commit tree를 읽는다.
2. 수정 파일 blob을 만든다.
3. 최신 tree를 base로 candidate tree와 commit을 만든다.
4. candidate diff가 의도한 파일에만 한정되는지 확인한다.
5. main ref를 다시 읽는다.
6. parent가 여전히 최신이면 `force=false`로 ref를 이동한다.
7. 게시 후 remote ref와 changed files를 재확인한다.

대형 파일 전체 교체는 candidate commit diff가 정확한지 확인한 뒤 게시한다.

## 7. 게시

1. 변경 파일과 diff scope를 확인한다.
2. `git fetch origin`으로 최신 `origin/main`을 다시 읽는다.
3. 원격이 이동했으면 최신 main에 재적용한다.
4. 직접 영향 검증을 반복한다.
5. fast-forward로만 게시를 시도한다.
6. 게시 후 remote ref와 commit diff를 재확인한다.

재적용:

- base 이후 변경이 현재 경로·contract와 무관하면 최신 main에서 만든 다른 안정적인 worktree에 안전하게
  재적용한다.
- 재적용용 worktree도 별도 활성 workspace이므로 §6.1과 동일한 lock lifecycle을 사용한다.
- 재적용 후 focused verification과 정적 진단 closure를 다시 실행한다.
- 관련 경로·contract가 바뀌었으면 최신 상태를 읽고 현재 변경을 조정한 뒤 재검증한다.

```bash
REAPPLY_DIR="$WORKTREE_ROOT/${TASK_SLUG}-reapply"
REAPPLY_CREATED_AT=$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$REAPPLY_DIR"
git worktree add \
  --lock \
  --reason "owner=game-agent task=$TASK_SLUG created=$REAPPLY_CREATED_AT phase=reapply" \
  --detach "$REAPPLY_DIR" origin/main
```

- 다른 세션이 먼저 push해 non-fast-forward로 거부되면 최신 main 기준으로 반복한다.
- force push나 merge commit으로 경쟁 변경을 덮지 않는다.
- SHA가 이동했다는 이유나 원격 이동 자체만으로 자동 중단하거나 BLOCKED 처리하지 않는다.

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
게시하지 않은 작업에는 `COMMIT`을 적지 않는다.

### 7.1 cleanup

게시에 성공하고 worktree가 clean이며 HEAD가 최신 `origin/main`에 포함되고 자신이 만든 worktree임을 확인한 뒤에만 unlock 후 plain `git worktree remove`로 회수한다. 중단된 작업, dirty worktree 또는 아직 `origin/main`에 포함되지 않은 HEAD는 unlock하거나 제거하지 않고 경로를 보존한다.

```bash
git -C <main-checkout> fetch origin --prune
test -z "$(git -C "$WORKTREE_DIR" status --porcelain)"
WORKTREE_HEAD=$(git -C "$WORKTREE_DIR" rev-parse HEAD)
git -C <main-checkout> merge-base --is-ancestor "$WORKTREE_HEAD" origin/main
git -C <main-checkout> worktree unlock "$WORKTREE_DIR"
git -C <main-checkout> worktree remove "$WORKTREE_DIR"
git -C <main-checkout> worktree prune --dry-run --verbose
```

- unlock은 삭제 직전의 마지막 단계다. clean, published, self-owned 조건을 모두 확인하기 전에는
  unlock하지 않는다.
- plain `git worktree remove`가 실패하면 `--force`로 우회하지 않고 worktree를 보존한다.
- `git worktree prune`은 정상 worktree 제거 수단이 아니다. `--dry-run`에서 이미 경로가 사라진 stale
  metadata가 확인된 경우에만 별도로 실행한다.
- 다른 세션의 worktree·branch·dirty state를 정리하지 않는다.

## 8. 로컬 에이전트 위임

로컬 실행 프롬프트의 구성과 발행 기준은
[`LOCAL_LLM_DELEGATION.md`](../project/LOCAL_LLM_DELEGATION.md)와
[`planning.md`](planning.md)가 소유한다. 이 문서는 두 owner를 다시 정의하지 않는다.

## 9. 완료

완료는 코드·테스트·브라우저·build·artifact 중 현재 criterion에 필요한 증거가 모두 있을 때만 선언한다.
형식과 PASS/BLOCKED 근거는 [`reporting.md`](reporting.md)가 소유한다.