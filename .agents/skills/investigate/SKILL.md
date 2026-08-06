---
name: investigate
description: AidenGame의 버그·문서·구조 문제를 수정 전에 증거 중심으로 조사하는 read-first skill
metadata:
  version: "2.0.0"
---
<!-- Language: ko -->

# Investigate skill

이 skill은 원인과 영향 범위를 먼저 이해해야 하는 작업에 사용한다.
workflow 진입점은 [`investigate.md`](../../workflows/investigate.md)다.

## 1. 조사 질문 고정

조사 시작 시 다음을 한 문장으로 정리한다.

- 무엇이 잘못됐다고 의심되는가
- 어느 사용자 흐름 또는 저장소 계약에 영향을 주는가
- 이번 조사에서 무엇을 확인하면 종료되는가

“전체적으로 이상한 점을 찾아라”처럼 넓은 요청이면 authority, runtime, test, workflow 순으로 감사 축을 나누되 한 반복에는 하나의 모순 유형만 다룬다.

## 2. 증거 수집

우선순위:

1. 최신 `origin/main`의 대상 파일
2. 직접 관련 caller와 test
3. 가장 가까운 product/technical spec
4. 실제 browser, build, artifact 또는 connector 결과
5. 과거 commit은 변화 원인을 이해할 때만 참고

문서의 수정일이나 status 문자열을 현재 동작 증거로 사용하지 않는다.

## 3. 실행 경로 추적

필요한 범주만 확인한다.

- DOM event → handler → state transition → render
- answer selection → feedback → next question → reset
- pointer/timer/listener → cancel/shutdown cleanup
- source → build config → generated artifact → deployment entry
- authority document → routing/workflow → local prompt
- test fixture → actual boundary → assertion

전체 저장소를 무차별 검색하지 않고 현재 질문을 구분하는 경계를 따라간다.

## 4. 사실과 가설

### 사실

직접 읽거나 실행해 확인한 내용:

- 파일·symbol 존재
- 특정 state transition
- test assertion 범위
- 실제 command 존재
- browser error 또는 request failure
- commit diff

### 가설

사실만으로 아직 확정되지 않은 설명이다.
가설에는 검증 방법과 반증 조건을 함께 둔다.

확정되지 않은 가설을 root cause라고 보고하지 않는다.

## 5. 재현 여부

- 재현 가능하면 trigger, initial state, expected, actual을 기록한다.
- 재현되지 않으면 이미 해결됐는지, 환경 차이인지, test gap인지 구분한다.
- 브라우저 증상은 source inspection만으로 최종 확정하지 않는다.
- 문서·경로·명령 drift는 direct file comparison으로 판정할 수 있다.

## 6. 영향 범위

다음을 구분한다.

- 사용자 진행을 막는 runtime defect
- 상태 또는 데이터 오염
- test coverage gap
- stale documentation
- agent workflow misrouting
- generated artifact drift
- 보안 또는 credential 위험

영향 유형이 다르면 한 수정 작업으로 합치지 않는다.

## 7. 수정 권장 경계

수정이 필요하면 다음만 제시한다.

- 첫 failure domain
- 포함 파일 또는 semantic hotspot
- non-goal
- 재현 조건
- binary criterion
- focused verification

향후 전체 roadmap을 자동으로 만들지 않는다.
저장소 Blueprint는 사용자가 명시적으로 요청한 경우에만 권장할 수 있다.

## 8. 조사 종료

다음 중 하나면 조사를 종료한다.

- 원인과 영향이 충분히 확정됨
- 원인 후보를 구분할 다음 실험이 명확함
- 현재 main에서 결함이 재현되지 않음
- 필요한 환경·입력이 없어 더 이상 증거를 얻을 수 없음

결과는 간결하게 사실, 근거, 영향, 첫 수정 경계 순으로 보고한다.
