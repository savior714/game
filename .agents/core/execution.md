---
scope:
- '*'
always_apply: false
priority: 1
domain: core
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_core_agent_contract_consistency.py
---
<!-- Language: ko -->

# AidenGame 실행 규칙

이 문서는 작업 시작부터 게시까지의 실행 순서를 정의한다.
도구 선택 세부는 [`routing.md`](routing.md), 검증은 [`verification.md`](verification.md), 보고는 [`reporting.md`](reporting.md)를 따른다.

## 1. 작업 시작

1. 사용자의 현재 요청을 확인한다.
2. 최신 `origin/main`과 대상 파일·직접 관련 테스트를 읽는다.
3. `AGENTS.md`, `PROJECT_RULES.md`, 가장 가까운 product/technical spec을 확인한다.
4. 현재 failure domain, 재현 조건, binary criterion을 한 문장으로 고정한다.
5. 동결 범위나 forbidden action과 충돌하지 않는지 확인한다.

범위가 지정되지 않았다면 일반 과목 안정화 계약을 따른다.
계획 관련 단어가 있다는 이유만으로 plan 파일을 만들지 않는다.

## 2. workspace와 Git

- mutation은 최신 `origin/main`에서 만든 isolated worktree 또는 동등한 격리 공간에서 수행한다.
- 기본 로컬 경로는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`다.
- source worktree를 OS 임시 디렉터리에 만들지 않는다.
- IDE, LSP, package manager, 브라우저, generator는 같은 source root와 CWD를 사용한다.
- unrelated dirty state를 보존한다.
- force push, history rewrite, 필수 검증 우회는 금지한다.
- 게시 직전 원격 이동 여부를 다시 확인한다.

connector 기반 작업에서는 최신 branch ref와 대상 blob을 직접 읽고, 후보 commit을 만든 뒤 fast-forward 조건을 다시 확인한다.

## 3. 조사와 진단

- 파일 존재, import graph, caller, fallback, generated artifact 경계를 실측한다.
- 검색 결과는 조사 자료이며 존재 자체를 결함으로 취급하지 않는다.
- 실패를 재현할 수 있는 가장 작은 경로를 찾는다.
- 여러 원인이 나오면 현재 binary criterion과 직접 연결된 하나만 선택한다.
- baseline이 이미 PASS면 과거 보고만으로 결함을 재작업하지 않는다.

환경·workspace·SDK·dependency·cache·generated/vendor 오분석 가능성을 production code 변경보다 먼저 확인한다.

## 4. 수정

- 대상 파일의 최신 내용을 다시 읽는다.
- 부분 수정은 정확히 식별되는 최소 블록을 사용한다.
- 대형 파일 전체 교체는 원본과 후보 diff를 확인한 후에만 수행한다.
- 같은 failure domain의 source, caller, test, config는 함께 변경할 수 있다.
- unrelated refactor, formatting, dependency upgrade, 문서 상태 갱신을 섞지 않는다.
- generated artifact를 수동 편집하지 않는다.

편집 실패 시 더 넓은 치환으로 즉시 재시도하지 않고 파일을 다시 읽어 원인을 확인한다.

## 5. 테스트와 TDD

재현 가능한 결함은 가능하면 수정 전에 failing contract를 확인한다.
다만 현재 저장소에서 이미 실패가 명확히 재현되고 있거나 문서·설정 drift를 직접 비교할 수 있는 경우, 동일 실패를 중복 생성하기 위해 인위적인 테스트를 먼저 만들지 않는다.

새 테스트는 잡아낼 구체적 failure mode가 있을 때만 추가한다.
assertion 없는 테스트나 일정 상태 문자열만 검증하는 테스트를 만들지 않는다.

## 6. 검증

다음 순서로 확장한다.

1. 현재 binary criterion의 focused check
2. 수정 파일과 직접 영향 모듈의 lint/typecheck
3. 필요한 browser, build, artifact, rollback 검증
4. 공유 경계 변경 시 영향받는 regression
5. repository-wide gate는 실제 위험이나 정책이 요구할 때

필수 criterion을 실행하지 못했으면 이유를 기록하고 PASS로 표시하지 않는다.
검증 실패를 broad ignore나 범위 축소로 숨기지 않는다.

## 7. 게시

1. 변경 파일과 diff scope를 확인한다.
2. 최신 `origin/main`을 다시 읽는다.
3. 원격이 이동했으면 최신 main에 재적용한다.
4. 직접 영향 검증을 반복한다.
5. fast-forward로만 게시한다.
6. 게시 후 remote ref와 commit diff를 재확인한다.

SHA 불일치나 원격 이동만으로 작업을 포기하지 않는다. 실제 충돌이 없으면 최신 main에 안전하게 재적용한다.

## 8. 로컬 에이전트 위임

로컬 프롬프트에는 현재 실행할 한 단계만 전달한다.

- objective
- verified baseline
- included / excluded scope
- Do / Do not
- 쓰기 허용 범위
- verification
- binary criterion
- stop condition
- 결과 형식

전체 roadmap, 완료 이력, 이후 모든 단계, 반복 정책 전문을 넣지 않는다.
결과를 받은 뒤 최신 main과 실제 diff를 다시 확인하고 다음 프롬프트를 새로 작성한다.

## 9. 완료

완료는 코드·테스트·브라우저·build·artifact 중 현재 criterion에 필요한 증거가 모두 있을 때만 선언한다.
보고 형식은 `RESULT / CHANGE / VERIFY`를 기본으로 한다.
실제 게시 시에만 `COMMIT`, 중단 시에만 `BLOCKER / NEXT`를 추가한다.
