---
scope: workflow
status: active
---

<!-- Language: ko -->

# Work-Package Claim and Prompt Delegation

## 목적

여러 웹 GPT·로컬 에이전트 세션이 동일하거나 충돌하는 실행 단위를 중복 수행하는 것은 막고,
같은 제품 축 안의 독립 work package는 병렬로 수행할 수 있게 한다.

```text
PARENT_KEY
= 상위 제품 축 또는 closure group
= 병렬 작업 grouping
= 잠금이 아님

TASK_KEY
= 독립적으로 검증 가능한 bounded work package
= 이 단위마다 owner 한 세션
```

동적 owner 상태는 저장소 파일이 아니라 GitHub Issue #1
`[Coordination] Active Work-Package Claims`의 comments가 소유한다.

## 적용 대상

다음 중 하나에 해당하면 mutation 또는 장시간 실행 전에 claim이 필수다.

- 제품·test·runner·migration·shared contract·상태 문서 mutation
- commit 또는 push
- canonical browser/release/evidence runner의 장시간 실행
- 여러 파일이나 generated artifact를 함께 수정·재생성하는 작업
- 다른 세션과 같은 work package 또는 겹치는 write/resource scope를 사용할 가능성이 있는 작업

다음은 claim 없이 가능하다.

- read-only 방향 분석
- 현재 코드·gate·test 경로 확인
- work-package 분해와 병렬 가능성 판정
- active claim 확인
- active owner scope와 겹치지 않는 독립 read-only 검증

분석에서 mutation·publish·장시간 실행으로 전환하는 시점에 bounded package를 정하고 claim한다.
경계가 불명확하면 상위 제품축 전체를 broad `TASK_KEY`로 잠그지 말고 read-only로 먼저 분해한다.

## Claim board

- Repository: `savior714/game`
- Issue: `#1`
- Title: `[Coordination] Active Work-Package Claims`

board 또는 전체 comments에 접근할 수 없으면 claim-required 실행과 실행 프롬프트 발급은
`BLOCKED_COORDINATION_UNAVAILABLE`이다. main 파일, 대화 기억, branch, worktree 또는 로컬 lockfile로
대체하지 않는다.

## 병렬 허용 조건

같은 `PARENT_KEY` 아래 여러 active claim과 여러 owner가 동시에 존재할 수 있다.
다음 조건을 모두 만족해야 한다.

1. `TASK_KEY`가 다르다.
2. root cause와 `EXPECTED_TRANSITION`이 독립적이다.
3. `WRITE_SCOPE`가 경로상·의미상 겹치지 않는다.
4. `EXCLUSIVE_RESOURCES`가 겹치지 않는다.
5. `DEPENDS_ON`의 선행 task가 모두 `DONE` release 상태다.
6. 한쪽이 다른 쪽의 output을 동시에 재생성·소비·publish하지 않는다.

별도 key여도 다음이면 충돌한다.

- 같은 source, test, runner, config, contract 또는 generated artifact 변경
- 같은 fixed port, browser profile, output directory, preview server, artifact path 사용
- 같은 root cause나 outcome을 다른 이름으로 중복 수정
- 한 task가 다른 task 완료를 선행조건으로 가짐

## Claim 후보 정의

```text
PARENT_KEY:
TASK_KEY:
EXPECTED_TRANSITION:
WRITE_SCOPE:
- <path 또는 logical boundary>
EXCLUSIVE_RESOURCES:
- <resource 또는 NONE>
DEPENDS_ON:
- <task key 또는 NONE>
```

`TASK_KEY`는 lowercase kebab 형식으로 독립 outcome을 나타낸다. 파일명이나 세션명만 사용하지 않는다.
`PARENT_KEY` 자체를 broad `TASK_KEY`로 사용하지 않는다. final integration처럼 실제로 넓은 배타 범위가
필요한 경우에만 별도 integration task key와 정확한 scope/resource를 명시한다.

## Conflict 판정

Issue #1의 전체 comments에서 만료되지 않고 대응 `RELEASE`가 없는 claim을 active로 본다.

### Duplicate

- 같은 `TASK_KEY`
- 같은 root cause와 outcome을 다른 key로 표현

결과: `BLOCKED_DUPLICATE_ACTIVE_CLAIM`

### Overlap

- `WRITE_SCOPE` 경로 또는 semantic boundary 교집합
- `EXCLUSIVE_RESOURCES` 교집합
- 같은 artifact·runner·runtime identity를 동시에 재생성·소비·publish

결과: `BLOCKED_OVERLAPPING_ACTIVE_CLAIM`

### Dependency

- `DEPENDS_ON` task가 아직 `DONE` release되지 않음

결과: `BLOCKED_UNMET_CLAIM_DEPENDENCY`

위 충돌이 없으면 같은 `PARENT_KEY` 아래 다른 owner가 있어도 새 claim을 게시할 수 있다.

## Claim 절차

### 1. 기존 comments를 읽는다

모든 active claim의 `TASK_KEY`, root cause, outcome, scope, resource, dependency, expiry와 release를 확인한다.

### 2. 충돌이 없을 때만 게시한다

```text
CLAIM
PARENT_KEY: <parent axis>
TASK_KEY: <bounded work-package key>
CLAIM_ID: <task-key>-<UTC timestamp>-<short nonce>
PROGRAM: <current program>
TRACK: CRITICAL_PATH | GUARDRAIL_BLOCKER | PARALLEL_PRODUCT | SCOPED_MAINTENANCE
BASE_SHA: <40-char origin/main SHA>
OWNER_LABEL: <user-visible session label>
CLAIMED_AT_UTC: <ISO-8601 UTC>
EXPIRES_AT_UTC: <ISO-8601 UTC, normally +4h>
WRITE_SCOPE:
- <paths or logical boundary>
EXCLUSIVE_RESOURCES:
- <resource or NONE>
DEPENDS_ON:
- <task key or NONE>
EXPECTED_TRANSITION: <independently verifiable transition>
```

### 3. 게시 직후 arbitration한다

comment를 게시한 즉시 전체 comments를 다시 읽고 자신과 충돌하는 active claim 집합을 계산한다.
그 집합에서 GitHub comment ID가 가장 작은 claim만 owner다. 충돌하지 않는 다른 task claim은 경쟁
대상이 아니다.

winner가 아니면 mutation 없이 종료한다.

```text
RESULT: BLOCKED_DUPLICATE_ACTIVE_CLAIM | BLOCKED_OVERLAPPING_ACTIVE_CLAIM
PARENT_KEY: <parent key>
TASK_KEY: <task key>
CLAIM_ID: <own claim>
WINNING_CLAIM_ID: <conflicting owner claim>
MUTATION_PERFORMED: NO
```

## Owner 실행 규칙

owner만 declared `TASK_KEY`, `WRITE_SCOPE`, `EXCLUSIVE_RESOURCES` 범위에서 mutation, commit·push와
장시간 실행을 수행한다.

다음 시점에 Issue #1 comments를 다시 확인한다.

1. 첫 mutation 직전
2. 장시간 canonical 실행 직전
3. 원격 publish 직전

새 overlap이나 unmet dependency가 확인되면 중단한다. claim은 Git overlap 검사와 runtime resource
격리를 대체하지 않는다. scope 확대가 필요하면 release 후 새 claim으로 다시 arbitration한다.

## 웹 GPT의 실행 프롬프트 발급 자격

claim-required work package의 로컬 실행 프롬프트는 **웹 GPT 세션이 해당 package claim owner가 된
뒤에만** 발급한다.

owner 웹 세션은 claim을 로컬 에이전트 한 세션에 delegated executor로 위임할 수 있다.

프롬프트에는 다음을 반드시 포함한다.

```text
PARENT_KEY
TASK_KEY
CLAIM_ID
OWNER_LABEL
BASE_SHA
EXPIRES_AT_UTC
WRITE_SCOPE
EXCLUSIVE_RESOURCES
DEPENDS_ON
EXPECTED_TRANSITION
CLAIM_DELEGATION: WEB_OWNER_TO_SINGLE_LOCAL_EXECUTOR
```

규칙:

- 같은 `CLAIM_ID`를 여러 로컬 executor에 동시에 전달하지 않는다.
- 위임받은 로컬 executor는 별도 `CLAIM`을 중복 게시하지 않는다.
- 로컬 executor가 Issue #1에 접근할 수 있으면 mutation·long run·publish 직전에 active 상태를 재확인한다.
- 접근할 수 없으면 coordinating 웹 세션이 재확인과 `RELEASE` 게시를 책임진다.
- claim이 만료·release·loss 상태가 되면 로컬 executor는 즉시 mutation과 publish를 중단한다.
- owner가 아니거나 board에 접근할 수 없는 웹 세션은 실행 프롬프트 대신 read-only coordination 보고만 제공한다.
- read-only 분석 프롬프트는 claim 없이 만들 수 있지만 mutation·commit·push 권한을 포함하면 안 된다.

## Lease와 release

- 기본 lease: 4시간
- 만료된 claim: inactive
- background heartbeat는 요구하지 않는다.
- 더 오래 필요하면 만료 전에 `RELEASE` 후 새 `CLAIM`을 얻는다.
- owner 생존 여부를 대화 기억으로 추측하지 않는다.

완료, blocker 확인 또는 포기 시 반드시 게시한다.

```text
RELEASE
PARENT_KEY: <same parent key>
TASK_KEY: <same task key>
CLAIM_ID: <same claim id>
RESULT: DONE | BLOCKED | ABANDONED
FINAL_SHA: <40-char SHA or NONE>
RELEASED_AT_UTC: <ISO-8601 UTC>
HANDOFF: <one-line current state or resume condition>
```

`BLOCKED`도 claim을 계속 보유하는 상태가 아니다. 후속 세션은 release 이후 다시 claim한다.

## 금지사항

- 상위 `PARENT_KEY` 전체를 broad task로 claim해 독립 병렬 작업까지 잠금
- 같은 task를 다른 key 이름으로 중복 claim
- scope·resource overlap 또는 dependency를 무시한 병렬 실행
- owner가 아닌 세션의 mutation·commit·push·long run
- claim 없는 실행 프롬프트 발급
- 같은 claim을 여러 executor에 동시 위임
- delegated executor의 중복 claim 게시
- dynamic owner를 main 문서·lockfile에 기록
- board unavailable 상태에서 임의 대체물 사용
- `RELEASE` 없이 세션 종료

## 완료 보고

claim-required 작업 보고에는 다음을 포함한다.

```text
PARENT_KEY
TASK_KEY
CLAIM_ID
CLAIM_STATUS: OWNER | LOST_DUPLICATE | LOST_OVERLAP | BLOCKED_DEPENDENCY | BLOCKED_COORDINATION_UNAVAILABLE
OWNER_LABEL
WRITE_SCOPE
EXCLUSIVE_RESOURCES
MUTATION_PERFORMED
RELEASE_POSTED
```
