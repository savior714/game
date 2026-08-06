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

# AidenGame 코드 품질 생명주기

이 문서는 정적 HTML/CSS/JavaScript 런타임과 Python 기반 검증 도구의 품질 기준을 설계·구현·리뷰·검증 단계로 정리한다.
실제 gate는 최신 `Justfile`, `verify.sh`, package 설정, 테스트 파일을 따른다.

## 1. 설계

- 사용자 가시 결과와 failure domain을 먼저 정의한다.
- 상태 소유권, 이벤트 lifecycle, cleanup, generated artifact 경계를 명확히 한다.
- 공용화는 두 번째 실제 사용처에서 동일 책임이 확인된 뒤에만 검토한다.
- 경로와 symbol은 최신 저장소에서 존재 여부를 확인한다.
- 현재 제품 방향과 동결 범위를 넘는 설계를 시작하지 않는다.

일반 계획은 채팅에서 관리하고, 명시적으로 요청된 Blueprint에만 장기 설계를 기록한다.

## 2. 구현

### 상태와 lifecycle

- 문제별 transient state와 세션 전체 state를 구분한다.
- event listener, pointer capture, timer, animation frame의 소유자와 cleanup 경로를 둔다.
- pause, menu, restart, cancel, page teardown에서 임시 상태를 정리한다.
- 중복 입력이 상태를 두 번 전진시키지 않아야 한다.

### JavaScript

- 암묵적 전역과 load-order side effect를 새로 만들지 않는다.
- 기존 public namespace와 entry contract를 보존한다.
- DOM 조회 실패를 조용히 삼켜 핵심 흐름을 멈추지 않는다.
- 사용자 입력과 상태 변경을 렌더링에서 분리할 수 있는 경계는 명확히 한다.
- 같은 책임의 helper와 state shape를 중복 생성하지 않는다.

### CSS와 UI

- 어린이 사용 환경의 터치 target, disabled state, focus, feedback 가시성을 고려한다.
- 순수 시각 변경과 진행을 막는 usability 결함을 구분한다.
- overlay와 animation이 필수 컨트롤을 가리지 않아야 한다.
- 반응형 변경은 실제 지원 viewport에서 확인한다.

### Python 검증 코드

- Ruff와 type checker가 이해할 수 있는 명시적 타입과 단순한 제어 흐름을 사용한다.
- 테스트 fixture의 server, browser, temp resource를 종료한다.
- 포괄적 예외 무시로 실패를 숨기지 않는다.
- 테스트 helper가 production contract를 우회하지 않아야 한다.

## 3. 테스트

- 문자열 존재보다 사용자 동작과 상태 전이를 우선 검증한다.
- 정답·오답, 다음 문제, 마지막 문제, 재시작 경계를 구분한다.
- 문제 identity와 per-question state reset을 확인한다.
- page error와 request failure를 수집한다.
- browser-generated input을 사용한다.
- flake가 중요하면 계약에 정의된 반복 횟수를 적용한다.
- 내부 구현을 과도하게 mock해 실제 boundary를 건너뛰지 않는다.

문서 test는 stable authority, 링크, 실제 명령, 동결 정책을 검증한다.
일정 상태나 다음 작업 문자열을 제품 test에 결합하지 않는다.

## 4. 리뷰

리뷰에서는 다음을 확인한다.

- 변경이 한 failure domain에 한정되는가
- 다른 과목 또는 fallback 경로에 회귀가 없는가
- 상태·listener·timer cleanup이 완결됐는가
- 중복 구현이나 dead branch가 생기지 않았는가
- broad ignore, fail-open fallback, 검사 범위 축소가 없는가
- generated artifact와 source authority를 혼동하지 않았는가
- 문서가 현재 제품 방향과 실제 명령을 반영하는가

발견 사항은 파일·symbol·실패 시나리오와 함께 제시한다.

## 5. 정적 진단

현재 저장소의 대표 명령:

```bash
just lint
just typecheck
just verify
```

수정 파일과 직접 영향 모듈의 오류는 0이어야 한다.
환경·workspace·dependency 문제를 production code 변경으로 덮지 않는다.

함수·파일 길이는 기계적 숫자만으로 실패시키지 않는다.
긴 코드가 여러 책임, 깊은 중첩, 반복 cleanup을 포함할 때 실제 semantic boundary를 기준으로 분리한다.

## 6. 공용화와 리팩터링

다음 조건이 모두 있을 때만 공용화를 검토한다.

1. 두 개 이상의 실제 사용처에서 같은 책임이 반복됨
2. 입력·출력·상태 전이 계약이 동일함
3. 차이를 data, configuration, callback으로 표현할 수 있음
4. 추출 후 모든 영향 경로를 검증할 수 있음
5. 현재 failure mode 해결 또는 재발 방지에 직접 기여함

코드가 비슷해 보인다는 이유만으로 공용 엔진을 만들지 않는다.

## 7. 완료

- 구현 criterion과 직접 회귀가 통과함
- 필요한 정적 진단이 통과함
- browser/build/artifact 검증이 요구된 경우 실행됨
- diff scope가 의도한 파일과 원인에 한정됨
- remote publish가 요구된 경우 fast-forward가 확인됨

완료 문자열이나 커버리지 숫자만으로 품질 완료를 선언하지 않는다.
