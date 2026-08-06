---
scope:
- '*'
always_apply: true
priority: 1
domain: core
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_auxiliary_core_contract_consistency.py
---
<!-- Language: ko -->

# 반복 오류 패턴

이 문서는 AidenGame 작업에서 반복적으로 발생한 실행 오류를 현재 규칙으로 압축한다.
세부 도구 이름보다 실패 원인과 복구 순서를 우선한다.

## 1. 읽지 않고 수정

**증상:** 존재하지 않는 경로·오래된 본문·잘못된 symbol을 대상으로 패치함.

**방지:**

- 최신 main과 대상 파일을 먼저 읽는다.
- 검색 결과와 과거 보고를 현재 파일 내용으로 착각하지 않는다.
- 대형 파일은 관련 symbol과 직접 test로 범위를 좁힌다.

## 2. 부분 수정 대상 불일치

**증상:** 같은 문자열이 여러 곳에 있거나 formatter 이후 본문이 달라 edit가 실패함.

**복구:**

1. 같은 입력으로 반복 호출하지 않는다.
2. 파일을 다시 읽는다.
3. 더 정확한 block 또는 symbol 경계를 선택한다.
4. 전체 교체가 필요하면 원본과 후보 diff를 확인한다.

대상과 결과가 같으면 편집 호출을 생략한다.

## 3. 다른 런타임 tool schema 혼용

**증상:** tool not found, schema validation, key casing 오류, pseudo tool payload 노출.

**방지:**

- 현재 세션의 tool descriptor만 따른다.
- 다른 IDE나 에이전트의 JSON 예시를 재사용하지 않는다.
- local LLM이 다중 호출에 취약하면 한 turn에 도구 하나만 호출한다.
- structural 오류는 retry하지 않고 schema와 인자를 재검토한다.

## 4. 계획 문서 자동 생성

**증상:** “계획”, “다음 작업”, “이어서 진행”을 저장소 Blueprint 생성 요청으로 오인함.

**방지:**

- 일반 계획은 채팅에서 관리한다.
- 사용자가 저장소 Blueprint를 명시적으로 요청한 경우만 plan 파일을 만든다.
- 일반 WP 일정과 다음 WP를 tests 또는 evidence에 결합하지 않는다.

## 5. 최근 커밋 관성

**증상:** 최근 작업이 Ocean Rescue라는 이유로 동결된 migration을 계속 진행함.

**방지:**

- `AGENTS.md`, `PROJECT_RULES.md`, 현재 product spec을 먼저 확인한다.
- 범위가 없는 작업은 네 과목 공통 진단 또는 아직 닫히지 않은 일반 문제풀이 failure domain으로 해석한다.
- 사용자의 명시적 방향 변경이나 허용 예외가 없으면 Ocean Rescue·실험 구조 이전을 재개하지 않는다.

## 6. 해결된 결함 재작업

**증상:** 과거 보고에 나온 오류를 최신 main 재현 없이 다시 수정함.

**방지:**

- 동일 재현 조건으로 baseline을 확인한다.
- 이미 PASS면 개발 목표로 선택하지 않는다.
- 기존 테스트의 공백과 실제 runtime failure를 구분한다.

## 7. 검증 범위 왜곡

**증상:** 조사용 grep을 PASS/FAIL gate로 만들거나, 실행하지 않은 테스트를 통과했다고 보고함.

**방지:**

- 한 binary criterion을 먼저 고정한다.
- focused test부터 필요한 regression으로 확장한다.
- source inspection, connector 대조, 실제 test 실행을 보고에서 구분한다.
- full suite를 관성적으로 실행하지 않는다.

## 8. 일정 상태와 제품 테스트 결합

**증상:** `다음 WP`, `현재 WP`, COMPLETE 문자열, plan header를 제품 test가 검증함.

**방지:**

- test는 사용자 동작, 상태, 타입, build, artifact, rollback을 검증한다.
- 문서 guard는 authority, 링크, 실제 명령, 동결 정책을 검증한다.
- 진행 상태는 대화에서 관리한다.

## 9. 대형 파일 전체 교체 유실

**증상:** 마지막 함수 하나를 제거하려다 기존 동작 테스트나 문서 계약을 함께 잃음.

**방지:**

- 원본 blob 전체를 확보한다.
- 후보 commit을 만들어 exact diff를 확인한다.
- 의도한 추가·삭제만 있는 경우에만 branch ref를 갱신한다.

## 10. 원격 이동 처리 실패

**증상:** 감사 또는 구현 중 main이 이동해 stale parent에 게시하거나 불필요하게 BLOCKED 처리함.

**복구:**

1. 최신 remote ref를 다시 읽는다.
2. 새 커밋의 변경 파일과 겹치는지 확인한다.
3. 충돌이 없으면 최신 tree 위에 재적용한다.
4. 직접 영향 검증을 반복한다.
5. fast-forward로만 게시한다.

## 11. 정적 오류 면책

**증상:** 수정 파일·직접 영향 모듈의 오류를 pre-existing 또는 out of scope로 남기고 PASS함.

**방지:**

- 현재 원인의 정적 오류를 0으로 만든다.
- 다른 원인이면 별도 failure domain으로 분리한다.
- 필수 criterion이 남으면 BLOCKED로 보고한다.
- broad ignore와 검사 축소로 녹색을 만들지 않는다.

## 12. 비밀값 노출

**증상:** 환경 파일, 실패 로그, remote URL에서 token·password가 출력됨.

**방지:**

- 비밀 파일의 내용을 출력하지 않는다.
- 존재 여부와 key 이름만 안전하게 확인한다.
- 노출 가능성이 있으면 값을 재인용하지 않고 회전 필요성을 알린다.

## 13. 변경 후 확인 누락

편집 도구 성공은 완료가 아니다.

- 파일 또는 commit diff 재확인
- focused criterion 확인
- 최신 remote ref 확인
- 게시 후 commit과 changed files 확인

위 네 단계 중 현재 작업에 필요한 항목을 마치기 전 PASS로 보고하지 않는다.
