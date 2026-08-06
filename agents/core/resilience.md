---
scope:
- '*'
always_apply: false
priority: 1
domain: core
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_auxiliary_core_contract_consistency.py
---
<!-- Language: ko -->

# 재시도와 복구

이 문서는 tool, network, context, edit 실패를 같은 방식으로 반복하지 않도록 복구 전략을 정의한다.

## 1. 실패 분류

재시도 전에 실패를 다음 중 하나로 분류한다.

### 일시적 실패

- timeout
- connection reset
- rate limit
- 일시적인 service unavailable
- eventual consistency 가능성이 있는 read-only lookup

동일 작업을 무한 반복하지 않고 제한된 횟수와 backoff로 재시도한다.

### 구조적 실패

- tool schema validation
- tool not found
- required field 누락
- 존재하지 않는 경로·명령
- 동일 인자에서 반복되는 deterministic 오류
- non-fast-forward 또는 실제 content conflict

즉시 같은 입력 재시도를 중단하고 schema, current state, 전략을 다시 확인한다.

### 보안 실패

- credential 또는 민감값 노출 가능성
- 의도하지 않은 외부 전송
- 권한 경계 불명확

재시도보다 노출 중단과 안전한 credential 회전·주입 안내가 우선이다.
민감값을 다시 출력하지 않는다.

## 2. 읽기·검색 복구

- 응답이 잘리면 필요한 구간이나 symbol로 범위를 줄인다.
- 검색 색인이 최신 commit을 반영하지 않을 수 있으면 direct file read로 확인한다.
- 검색 0건만으로 부재를 단정하지 않는다.
- 연결된 저장소 URL을 일반 web search로 대체하지 않는다.

## 3. 편집 복구

- 부분 수정 실패 후 파일을 다시 읽는다.
- 같은 target과 replacement를 반복 호출하지 않는다.
- 매칭 범위를 무작정 넓히지 않는다.
- 대형 파일 전체 교체는 원본 blob과 후보 diff를 확인한다.
- 여러 비연속 수정은 가능한 경우 하나의 원자적 patch로 만든다.
- edit 성공 후 실제 파일 또는 commit diff를 재확인한다.

## 4. 원격 이동

작업 중 main이 이동하면 다음을 수행한다.

1. 최신 ref와 새 commit의 changed files를 확인한다.
2. 현재 변경과 겹치는지 판단한다.
3. 충돌이 없으면 최신 tree 위에 재적용한다.
4. 직접 영향 검증을 반복한다.
5. fast-forward로만 게시한다.

원격 이동 자체만으로 BLOCKED 처리하지 않는다.
실제 semantic conflict가 있고 안전하게 병합할 수 없을 때만 중단한다.

## 5. context 부족

- 완료된 이력과 중복 정책을 제거한다.
- 현재 objective, baseline, 단일 gap, 검증 기준만 유지한다.
- 전체 roadmap을 local prompt에 넣지 않는다.
- 다음 작업은 결과를 받은 뒤 최신 main에서 새로 결정한다.

context 제한을 함수·타입·도메인 계약 삭제로 해결하지 않는다.

## 6. 장기 작업 진행 보고

복수 tool call이 필요한 작업은 다음을 짧게 공유한다.

- 현재 감사 또는 수정 범위
- 이미 확인된 핵심 결함
- 다음 판정 경계

낮은 수준의 모든 명령을 나열하지 않는다.
사용자가 중간에 방향을 바꾸면 새 지시를 반영해 현재 작업을 조정한다.

## 7. 중단 기준

다음 경우에만 BLOCKED로 종료한다.

- 필수 입력이 없고 저장소 증거로 해소할 수 없음
- 안전 정책 또는 권한상 수행 불가
- 필수 검증 환경을 사용할 수 없고 대체 증거도 없음
- 최신 main과 실제 semantic conflict
- 필수 criterion을 안전하게 만족할 수 없음

가능한 부분 완료와 확인된 증거를 함께 보고한다.
