---
name: discover
description: AidenGame의 현재 제품 범위에서 증거 기반 기술 부채·검증 공백 후보를 찾는 read-first skill
metadata:
  version: "2.0.0"
---
<!-- Language: ko -->

# Discover skill

workflow 진입점은 [`discover.md`](../../workflows/discover.md)다.

## 1. 탐색 범위

범위는 다음 중 하나로 고정한다.

- 사용자가 지정한 과목·기능·경로
- 현재 일반 과목 안정화에서 아직 검증되지 않은 contract
- 반복된 문서·agent workflow drift
- 최근 변경의 직접 영향 영역

“저장소 전체 개선” 요청이면 runtime reliability, test gap, authority drift처럼 감사 축을 나누고 한 반복에는 하나만 다룬다.

## 2. 증거 수집

후보에는 최소 하나의 강한 증거가 필요하다.

- 최신 main에서 재현되는 사용자 failure
- 동일 책임의 두 번째 실제 사용처
- 반복 commit에서 같은 수정이 여러 파일에 복제됨
- listener·timer·pointer cleanup 소유권 불명확
- browser test가 핵심 transition을 전혀 검증하지 않음
- 문서가 존재하지 않는 path·command를 권위로 지시함
- clean build와 tracked artifact가 불일치함

파일 길이, TODO, 주석, 낮은 coverage 숫자만으로 즉시 candidate를 만들지 않는다.

## 3. 후보 정제

각 후보에 대해 확인한다.

1. 현재 제품 방향에 포함되는가
2. 이미 해결됐는가
3. 사용자 또는 개발 속도에 실제 영향이 있는가
4. 한 failure domain으로 좁힐 수 있는가
5. 성공 criterion을 만들 수 있는가
6. 현재 허용 범위 안에서 수정 가능한가

하나라도 불명확하면 조사 후보로 남기고 구현 후보로 승격하지 않는다.

## 4. duplication과 공용화

공용화 후보는 다음을 모두 만족해야 한다.

- 최소 두 과목 또는 두 caller에서 동일 책임이 실제 반복됨
- 입력·출력·상태 전이 계약이 같음
- 차이를 data, configuration, callback으로 표현할 수 있음
- 추출 후 모든 영향 경로를 검증할 수 있음
- 현재 failure 또는 반복 회귀를 줄임

비슷한 코드 두 조각만으로 shared abstraction을 권장하지 않는다.

## 5. 테스트·스크립트 위생

테스트나 script cleanup은 다음 때만 우선한다.

- false positive/negative를 만들고 있음
- 현재 필수 gate를 깨뜨림
- resource leak 또는 fixed-port collision을 반복함
- 존재하지 않는 command·path를 전파함
- 실제 runtime defect를 숨김

단순 분할, 줄 수 감소, unused 후보는 직접 실행·참조를 확인한 뒤 판단한다.

## 6. 우선순위

1. 사용자 흐름 중단·데이터 손상·보안
2. 반복 가능한 state 또는 input defect
3. 완료 판정을 막는 test gap
4. agent misrouting·authority drift
5. 반복 변경 비용이 큰 구조적 중복
6. 순수 코드 hygiene

현재 동결 기능의 장기 개선은 우선순위 목록에 넣지 않는다.

## 7. 결과와 종료

후보마다 근거, 영향, boundary, criterion을 작성한다.
가장 높은 후보 하나가 실행 가능하면 탐색을 종료한다.

자동으로 queue·artifact·Blueprint를 발급하지 않는다.
사용자가 구현을 요청하면 해당 candidate만 실행하고, 완료 후 최신 main에서 다시 탐색한다.
