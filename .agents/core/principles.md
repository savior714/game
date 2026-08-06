---
scope:
- '*'
always_apply: true
priority: 1
domain: core
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_core_agent_contract_consistency.py
---
<!-- Language: ko -->

# AidenGame 핵심 원칙

이 문서는 에이전트의 판단 원칙을 정의한다.
실행 우선순위는 [`AGENTS.md`](../../AGENTS.md), 제품 경계는 [`PROJECT_RULES.md`](../../PROJECT_RULES.md)가 결정한다.

## 1. 증거 우선

- 파일·경로·symbol·명령·오류 원인을 확인하기 전에 단정하지 않는다.
- 현재 `origin/main`의 코드·테스트·설정을 과거 계획과 완료 보고보다 우선한다.
- 직접 확인한 사실과 아직 검증되지 않은 가설을 구분한다.
- 실행하지 않은 검증을 PASS로 보고하지 않는다.
- 도구 제한이나 접근 불가가 있으면 우회 사실과 검증 한계를 명시한다.

## 2. 현재 목표 우선

범위가 없는 다음 작업은 현재 product spec을 따른다.
현재 기본 방향은 Math, English, Korean, Science 일반 문제풀이 신뢰성 안정화다.

- Ocean Rescue와 `experiments/` 신규 기능·구조 이전은 동결한다.
- 최근 커밋이나 과거 계획이 특정 기능이라는 이유로 자동 재개하지 않는다.
- 사용자가 현재 요청에서 방향을 명시적으로 변경하면 그 요청이 우선한다.
- 치명적 운영 회귀, 데이터 손상, 보안 문제는 독립 failure domain으로 예외 처리할 수 있다.

## 3. 한 번에 하나의 원인

```text
한 작업
= 한 failure domain
= 한 검증 가능한 가설
= 한 binary criterion
= 한 독립 검증
```

- 같은 원인을 닫는 source, caller, test, asset, config는 함께 변경할 수 있다.
- 파일 수나 줄 수만으로 인위적으로 분할하지 않는다.
- 서로 다른 ownership, event cleanup, timer, browser proof, artifact, rollback, 문서 drift는 독립 검증 가능하면 분리한다.
- unrelated cleanup과 미래 구조 개선을 현재 패치에 섞지 않는다.

## 4. 단순성과 최소 변경

- 현재 문제를 해결하는 최소 의미 변경을 선택한다.
- 검증되지 않은 추상화와 configurability를 추가하지 않는다.
- 기존 스타일과 public contract를 보존한다.
- 현재 변경으로 생긴 unused code만 정리한다.
- 대형 파일을 전체 교체해야 하면 원본과 후보 diff를 먼저 확인한다.
- generated artifact는 source와 build pipeline으로만 갱신한다.

## 5. 질문과 context gap

불확실성이 있다는 이유만으로 항상 질문하지 않는다.

1. 저장소와 연결된 데이터로 해소 가능한지 먼저 조사한다.
2. 답에 따라 사용자 가시 동작, 도메인 계약, 수정 범위, 합격 기준이 실질적으로 달라지는지 판단한다.
3. 사용자 결정이 반드시 필요할 때만 질문 하나를 한다.
4. 질문은 하나의 결정축과 상호 배타적인 선택지를 갖는다.
5. 권장 기본값은 정확히 하나이며 표시와 결론이 일치해야 한다.

경미한 세부사항은 합리적 가정이나 명시적 placeholder로 처리한다.
이미 답을 얻은 질문을 반복하지 않는다.

## 6. 계획과 문서

- 일반 계획과 다음 작업은 채팅에서 관리한다.
- 사용자가 저장소 Blueprint를 명시적으로 요청한 경우에만 plan 파일을 만든다.
- 일반 WP 일정, 다음 WP, 진행 상태를 product test에 결합하지 않는다.
- 문서는 안정적인 제품·기술 계약을 설명할 때만 추가한다.
- 진행률과 완료 보고만 저장하기 위한 plan/evidence 문서를 만들지 않는다.

상세 규칙은 [`planning.md`](planning.md)를 따른다.

## 7. 검증 가능한 완료

- 버그 수정은 재현 조건이 사라졌는지 같은 기준으로 확인한다.
- 상태·ownership 변경은 source와 caller, cleanup, 직접 회귀를 함께 검증한다.
- UI 흐름은 필요한 경우 실제 브라우저 입력으로 확인한다.
- build·artifact 변경은 결정성, drift, rollback 중 실제 위험에 대응하는 항목을 확인한다.
- 수정 파일과 직접 영향 모듈의 필수 정적 진단은 0이어야 한다.

전체 검증을 관성적으로 실행하지 않고 위험에 직접 대응하는 가장 작은 검증부터 확장한다.

## 8. 우회와 실패의 정직한 처리

- broad ignore, 검사 범위 축소, snapshot 갱신, fail-open fallback으로 만든 녹색 결과를 정상 해결로 보고하지 않는다.
- 환경 문제를 production code 변경으로 덮지 않는다.
- 안전하게 해결하지 못한 필수 criterion이 남으면 `BLOCKED`로 보고한다.
- 임시 우회를 사용했다면 무엇을 우회했는지와 남은 근본 원인을 설명한다.
- 완료 후 불필요한 선택 질문이나 장기 backlog를 자동으로 붙이지 않는다.

## 9. 보안과 개인정보

- API key, token, cookie, password, `.env` 원문을 출력하거나 문서화하지 않는다.
- 민감값이 노출됐을 가능성이 있으면 값을 재인용하지 않는다.
- 외부 입력과 권한 경계는 fail-closed를 기본으로 한다.
