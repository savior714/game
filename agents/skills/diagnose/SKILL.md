---
name: diagnose
description: 재현 가능한 실패에 대해 빠른 판정 루프를 만들고 증거로 원인 하나를 닫는 AidenGame 진단 skill
metadata:
  version: "2.0.0"
---
<!-- Language: ko -->

# Diagnose skill

이 skill은 hard bug, 성능 회귀, flake처럼 원인이 즉시 드러나지 않는 실패를 다룬다.
workflow 진입점은 [`diagnose.md`](../../workflows/diagnose.md)다.

## 1. 핵심 계약

진단의 첫 산출물은 설명이 아니라 **빠르고 반복 가능한 PASS/FAIL 신호**다.

좋은 판정 루프는 다음을 만족한다.

- 사용자가 설명한 동일 증상을 잡음
- 환경과 입력이 명확함
- 실행 시간이 충분히 짧음
- 실패 조건이 구체적임
- 수정 전후 같은 방식으로 실행 가능함
- 관련 없는 초기화와 전체 suite를 피함

루프를 만들 수 없으면 필요한 환경·로그·화면 기록·실기기 접근 중 무엇이 부족한지 정확히 보고한다. 증거 없이 원인을 확정하지 않는다.

## 2. 재현 최소화

1. 최신 main에서 증상을 재현한다.
2. 입력, 순서, 저장 상태, viewport, 브라우저, timing 중 필요한 변수를 기록한다.
3. 관련 없는 단계와 데이터를 제거한다.
4. 재현률을 측정한다.
5. 간헐 실패면 반복 횟수를 늘려 신호를 강화한다.

일반 과목에서는 직접 entry, 첫 문제, answer path, next transition, final/restart 경계를 분리해 어느 전이에서 처음 계약이 깨지는지 찾는다.

## 3. 증거와 가설

source와 runtime 증거만으로 원인이 구분되지 않을 때 가설을 만든다.
각 가설은 다음을 가져야 한다.

- 이를 지지하는 관찰
- 반대되는 관찰
- 틀렸음을 보여줄 수 있는 예측
- 가장 작은 검증 방법

가설 개수를 3개나 5개로 형식적으로 맞추지 않는다.
첫 번째 그럴듯한 설명에 고정되지 않되, 이미 증거로 원인이 하나로 좁혀졌다면 가짜 대안을 만들지 않는다.

## 4. 계측

계측은 가설을 구분하는 경계에만 추가한다.

- 상태 전이 직전·직후
- event listener 또는 pointer lifecycle
- timer schedule·cancel·rearm
- persistence read/write
- browser page error와 request failure
- build input, output, metadata identity

모든 것을 로그로 남긴 뒤 검색하는 방식은 피한다.
임시 계측은 고유 marker를 사용하고 완료 전에 제거한다.
성능 문제는 로그보다 반복 가능한 timing 또는 profiler 기준을 먼저 만든다.

## 5. 수정과 회귀

원인이 확인되면:

1. 올바른 seam에서 회귀 계약을 만든다.
2. 수정 전 실패 또는 현재 위반 상태를 확인한다.
3. 최소 수정한다.
4. focused 계약을 통과시킨다.
5. 원래 사용자 흐름을 다시 실행한다.
6. 직접 영향 회귀와 정적 진단으로 확장한다.

올바른 test seam이 없다면 얕은 mock test로 거짓 안전성을 만들지 않는다. 대신 실제 browser harness, static contract 또는 구조상 test gap을 명확히 기록한다.

## 6. AidenGame 과목 진단

현재 기본 대상은 Math, English, Korean, Science다.

확인 항목:

- question content 또는 안정적 identity 변화
- 정답·오답 경로 모두 진행 가능
- answer selection과 feedback 초기화
- next button의 visible/disabled 상태
- 중복 입력으로 index가 두 번 증가하지 않음
- final result와 restart
- 새 세션에 이전 transient state가 남지 않음
- 실제 browser error와 request failure 0건

기존 progression test 한 번의 PASS를 과목 완료 전체로 확대 해석하지 않는다.

## 7. 실패한 수정 시도

수정 시도가 실패하면 무작정 두 번째·세 번째 patch를 쌓지 않는다.

- 같은 재현 신호가 유지되는지 확인
- 가설이 틀렸는지, 수정 seam이 잘못됐는지 구분
- 변경을 되돌리거나 분리
- 새 증거로 원인 모델을 갱신

연속된 실패 횟수보다 **같은 원인 모델로 더 진행할 근거가 있는지**가 중단 기준이다.

## 8. cleanup과 완료

완료 전 확인:

- 원래 repro PASS
- 회귀 계약 PASS
- 임시 log와 fixture 제거
- listener, timer, pointer, server, browser resource cleanup
- unrelated 변경 없음
- 필수 static diagnostic 0
- diff scope와 remote publish 상태 확인

## 9. 출력

필요한 섹션만 사용한다.

- 증상
- 판정 루프
- 확인된 증거
- 근본 원인
- 수정
- 검증
- 남은 blocker

진행 가능한 저장소 작업에서 사용자 체크포인트를 형식적으로 요구하지 않는다. 사용자 결정에 따라 동작·계약·범위·합격 기준이 달라질 때만 질문 하나를 한다.
