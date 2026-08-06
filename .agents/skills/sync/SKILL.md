---
name: sync
description: AidenGame의 code·test·config와 stable product/technical 문서 사이 drift를 증거로 분류하고 최소 정합화하는 skill
metadata:
  version: "2.0.0"
---
<!-- Language: ko -->

# Sync skill

workflow 진입점은 [`sync.md`](../../workflows/sync.md)다.

## 1. claim 단위 비교

문서 전체가 오래됐다는 인상보다 구체적인 claim 하나를 비교한다.

예:

- 실제 production entry 경로
- next button이 한 문제만 전진한다는 계약
- 특정 controller가 pointer cleanup을 소유함
- generated artifact가 build pipeline 소유임
- Ocean Rescue가 현재 development freeze 상태임
- MEMORY의 다음 실행이 공통 과목 진단임

각 claim에 근거 파일과 검증 방법을 붙인다.

## 2. 분류

### MATCH

문서, 구현, test가 같은 계약을 가리킨다. 변경하지 않는다.

### DOC_STALE

현재 product decision 또는 검증된 runtime은 올바르지만 문서가 이전 경로·명령·상태를 가리킨다.
해당 문서만 수정한다.

### IMPLEMENTATION_VIOLATION

stable product/technical contract가 유효한데 구현이 이를 위반한다.
문서를 구현에 맞춰 낮추지 않고 별도 runtime failure domain으로 처리한다.

### UNVERIFIED

source만으로 실제 동작을 확정할 수 없거나 필요한 browser/build 환경이 없다.
추정으로 양쪽을 수정하지 않는다.

## 3. authority 판단

충돌 시 다음을 확인한다.

1. 사용자의 현재 결정
2. `AGENTS.md`
3. `PROJECT_RULES.md`와 가장 가까운 product/technical spec
4. 최신 code/test/config

문서 종류가 다르면 역할에 맞게 비교한다.
README 설명이 product spec을 재정의할 수 없고, 과거 plan이 현재 execution priority를 정할 수 없다.

## 4. 실제 저장소 확인

- 링크 대상은 path resolution로 확인한다.
- 명령은 `Justfile`, `verify.sh`, package script, 실제 Python script에서 확인한다.
- entry와 routing은 HTML·`vercel.json`·build config에서 확인한다.
- generated artifact는 source와 build metadata를 구분한다.
- test 이름이나 과거 PASS 보고만으로 runtime claim을 확정하지 않는다.

현재 `just sync`는 `uv sync` recipe이므로 spec sync 옵션을 붙이지 않는다.

## 5. 문서 수정

- stable contract가 실제로 바뀐 경우만 authority 문서를 수정한다.
- 진행 상태와 commit history를 authority 문서에 누적하지 않는다.
- 같은 claim을 여러 문서가 사용자 진입을 위해 요약한다면 링크와 핵심 범위만 일치시킨다.
- 문서 전체 재작성 전 기존 안정적인 기술 계약이 유실되지 않는지 확인한다.
- inactive feature plan은 `PAUSED_REFERENCE_ONLY` 역할을 유지한다.

## 6. guard test

문서 drift가 반복될 가능성이 있으면 test를 추가할 수 있다.
좋은 guard는 다음을 검증한다.

- 링크가 실제로 존재함
- 실제 command가 존재함
- authority 우선순위가 일치함
- active/frozen 범위가 일치함
- stale foreign repository path가 없음
- 제품 test에 일정 상태가 결합되지 않음

수동 진행률, 날짜 하나, 다음 작업 문자열만 고정하는 test는 만들지 않는다.

## 7. 완료

- 선택한 claim이 `MATCH`가 됨
- 수정한 문서의 링크와 command가 유효함
- 다른 authority와 충돌하지 않음
- runtime 위반을 문서 수정으로 숨기지 않음
- 실행하지 못한 동작 검증은 `UNVERIFIED`로 남김

모든 문서를 동시에 최신화하려 하지 않고, 재검색에서 새 material drift가 발견될 때 다음 반복으로 이동한다.
