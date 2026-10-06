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

# AidenGame 보고 규칙

이 문서는 진행·완료·중단 보고의 최소 계약을 정의하며 보고 형식의 유일한 owner다.
실행 규칙은 [`AGENTS.md`](../../AGENTS.md), 검증 판정은 [`verification.md`](verification.md)를 따른다.

## 1. 기본 형식

```text
RESULT: PASS | BLOCKED
CHANGE: <무엇을 바꿨는지 한 문장>
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED
DISCOVERED_FAILURE: <독립 failure domain 또는 NONE>
```

- `PRIMARY_VERIFY`와 `DIRECT_VERIFY`는 `verification.md`의 `PRIMARY_CRITERION`과
  `DIRECT_IMPACT_CLOSURE`에 대응한다. 실행하지 않은 criterion은 `NOT_RUN`으로 적는다.
- 실제 게시 시에만 `COMMIT`을 추가한다.
- 중단 시에만 `BLOCKER`와 `NEXT`를 추가한다.
- 변경하지 않았다면 `CHANGE: 변경 없음`으로 명확히 적는다.
- claim, lease, task key, activation SHA 같은 내부 조정 메타데이터를 반복하지 않는다.
- `DISCOVERED_FAILURE`는 현재 작업의 PASS를 취소하지 않고 독립 failure domain으로 분리한 발견이다.

## 2. PASS 조건

다음을 모두 만족할 때만 PASS로 보고한다.

- 현재 binary criterion이 충족됨
- 실행하기로 한 필수 검증이 성공함
- 수정 파일과 직접 영향 범위의 필수 정적 오류가 0임
- broad ignore, 검사 축소, snapshot 갱신만으로 녹색을 만들지 않음
- 게시가 요구된 작업이면 remote fast-forward가 확인됨

문서 작업은 제품 기능이 완료됐다는 뜻이 아니다.
예를 들어 안정화 계약 문서 PASS와 네 과목 런타임 안정화 PASS를 구분한다.

## 3. BLOCKED 조건

필수 criterion을 안전하게 충족하지 못하면 BLOCKED로 보고한다.

```text
RESULT: BLOCKED
CHANGE: <안전하게 완료한 범위 또는 변경 없음>
PRIMARY_VERIFY: <NOT_RUN 또는 FAIL과 이유>
DIRECT_VERIFY: <NOT_RUN 또는 FAIL과 이유>
PUBLISH: NOT_APPLICABLE | BLOCKED
DISCOVERED_FAILURE: <독립 failure domain 또는 NONE>
BLOCKER: <재현 가능한 차단 사유 코드와 원인>
NEXT: <재개에 필요한 단일 조건>
```

다음은 면책 사유가 아니다.

- pre-existing
- unrelated
- out of scope
- 로컬에서는 아마 통과할 것임
- 과거 테스트가 PASS했음

또한 remote advance, non-fast-forward, unrelated dirty state, V3 시스템 smoke 실패, 새 독립 결함, 다른
세션의 선행 게시는 `verification.md` §10에서 정의한 대로 blocker가 아니다.

다른 원인의 오류라면 현재 failure domain의 판정과 분리해 정확히 보고하고, PASS 조건과 충돌하면 BLOCKED로 종료한다.

## 4. 상세 근거

다음 경우에만 필요한 세부사항을 추가한다.

- 사용자가 상세 보고를 요청함
- 검증 실패 또는 flake
- 원격 이동·충돌·재적용
- build·artifact·rollback identity
- 보안 또는 데이터 손상 위험
- 실행 환경 제약으로 일부 검증 불가

같은 내용을 여러 필드와 목록에서 반복하지 않는다.
전체 터미널 로그를 붙이지 않고 판정에 필요한 부분만 요약한다.

## 5. 검증 표현

`PRIMARY_VERIFY`와 `DIRECT_VERIFY`에는 실제로 실행하거나 직접 대조한 방법을 구분해서 적는다.

예:

- `focused pytest 6/6 PASS`
- `browser initial + 3 repeats, 4/4 PASS; pageerror=0; requestfailed=0`
- `candidate diff: 2 files only; remote main fast-forward confirmed`
- `repository connector로 게시 문서의 링크·문구·blob SHA를 독립 대조`

테스트를 실행하지 않고 source contract만 확인했다면 “pytest PASS”라고 쓰지 않는다.
실행 환경의 외부 네트워크나 브라우저 제약도 숨기지 않는다.

## 6. 우회와 한계

우회책을 사용했다면 다음을 설명한다.

- 원래 시도와 실패 원인
- 사용한 대체 경로
- 대체 경로로 검증된 범위
- 여전히 검증되지 않은 항목

우회가 목표와 모든 criterion을 충족했다면 PASS가 가능하지만, 근본 criterion이 남아 있으면 BLOCKED다.

## 7. 사용자 응답

- 사용자가 개발 용어를 사용하면 정확한 기술 용어로 답한다.
- 핵심 결과, 변경, 검증을 먼저 제시한다.
- 완료 후 불필요한 선택지나 장기 backlog를 자동으로 나열하지 않는다.
- 다음 작업이 현재 요청에 포함되지 않았다면 한 줄 이상의 영업성 follow-up을 붙이지 않는다.
- 사용자 결정이 반드시 필요한 경우에만 질문 하나를 한다.

## 8. 보안

보고·로그·도구 출력에서 API key, token, cookie, password, `.env` 원문을 재인용하지 않는다.
민감 정보가 노출됐을 가능성이 있으면 값을 반복하지 않고 차단 사실과 회전 필요성만 알린다.
