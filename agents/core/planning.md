---
scope:
- '*'
always_apply: false
priority: 1
domain: core
last_verified: 2026-08-08
verify_with:
- uv run pytest -q tests/test_planning_workflow_consistency.py
---
<!-- Language: ko -->

# AidenGame 계획 규칙

이 문서는 채팅 계획, 실행 프롬프트, 명시적으로 요청된 저장소 Blueprint의 경계를 정의한다.
현재 실행 우선순위는 [`AGENTS.md`](../../AGENTS.md)를 따르며, 제품 범위는 [`PROJECT_RULES.md`](../../PROJECT_RULES.md)와 가장 가까운 product spec이 결정한다.

## 1. 기본 계획 방식

일반적인 계획 요청은 채팅에서 처리한다.

- 다음 작업 정리
- 구현 순서 제안
- 로컬 모델용 실행 프롬프트
- 현재 failure domain 분해
- 결과 보고 후 후속 단계 선택

위 요청만으로 `docs/plans/` 파일을 만들지 않는다.
프론티어 모델이 전체 순서를 관리하고 로컬 실행에는 현재 단일 작업만 전달한다.

저장소 Blueprint는 사용자가 파일 생성 또는 기존 Blueprint 사용을 명시적으로 요청한 경우에만 작성·수정한다.
상세 workflow는 [`plan.md`](../workflows/plan.md)를 따른다.

## 2. 계획 단위

계획의 기본 실행 단위는 다음과 같다.

```text
한 작업
= 한 failure domain
= 한 검증 가능한 가설
= 한 binary criterion
= 한 독립 검증
```

같은 원인을 닫는 source, caller, test, asset, config는 함께 변경할 수 있다.
파일 수나 줄 수만으로 작업을 인위적으로 나누지 않는다.

다음 경계는 서로 독립적으로 검증 가능하면 별도 작업으로 나눈다.

- 상태 또는 ownership 이전
- 이벤트 처리와 cleanup
- timer lifecycle
- browser evidence
- generated artifact 게시
- rollback
- unrelated 정적 진단
- 계획·문서 drift

## 3. 현재 제품 방향 적용

범위가 없는 계획과 다음 작업 요청은
[`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)를 따른다.

- Math, English, Korean, Science 일반 문제풀이를 우선한다.
- 첫 실행은 네 과목 공통 진단 또는 아직 닫히지 않은 첫 failure domain이다.
- Ocean Rescue와 `experiments/` 신규 기능·구조 이전은 동결한다.
- 최근 커밋이나 과거 계획이 Ocean Rescue라는 이유로 자동 재개하지 않는다.
- 이미 해결된 결함은 최신 main에서 재현되지 않으면 다시 목표로 선택하지 않는다.

사용자가 현재 요청에서 방향을 명시적으로 변경하면 그 요청이 우선한다.

## 4. 컨텍스트 갭

누락 정보에 따라 사용자 가시 동작, 도메인 계약, 수정 범위, 합격 기준이 실질적으로 달라지는 경우만 context gap으로 본다.

- 저장소 증거로 해소할 수 있으면 먼저 조사한다.
- 사용자 결정이 반드시 필요하면 질문 하나만 한다.
- 질문은 하나의 결정축과 상호 배타적 선택지를 가져야 한다.
- 권장 기본값은 정확히 하나이며 표시와 결론이 일치해야 한다.
- 경미한 세부사항은 합리적 가정이나 명시적 placeholder로 처리한다.

구현 가능한 작업을 장기간 멈추기 위한 질문은 하지 않는다.

## 5. 로컬 실행 프롬프트

로컬 프롬프트는 최신 저장소 상태와 아직 남은 단일 gap을 기준으로 매번 새로 작성한다.
이전 프롬프트에 과거 이력과 정책을 계속 덧붙이지 않는다.

포함 항목:

- 현재 objective
- 검증된 baseline
- included / excluded scope
- Do / Do not
- 수정 허용 범위
- 검증 명령
- 단일 PASS/FAIL 기준
- stop condition
- 결과 형식

제외 항목:

- 완료된 WP 이력
- 향후 모든 하위 단계
- 현재 실행에서 소비되지 않는 메타데이터
- 저장소에 이미 있는 공통 정책의 장문 복사
- 계획 상태 문서 생성 지시

허용 파일은 쓰기 범위이며 조사·검색·테스트 읽기 범위와 동일하지 않다.

## 6. 명시적 Blueprint

사용자가 저장소 Blueprint를 명시적으로 요청하면 다음을 포함한다.

- 목적과 사용자 결과
- 현재 baseline
- scope와 non-goal
- dependency와 실행 순서
- 재현 조건 또는 입력 계약
- 실제 존재하는 검증 명령
- 작업별 판정 기준
- rollback 또는 중단 경계
- 전체 완료 조건

Blueprint는 단일 실행 경로를 제공해야 한다.
서로 다른 가설이 남아 있다면 먼저 조사하거나 별도 독립 작업으로 분리한다.
실행 중 계획 상태를 제품 테스트에 결합하지 않는다.

## 7. 계획과 현재 상태의 관계

계획 문서는 현재 코드보다 높은 권위가 아니다.
실행 전 최신 `origin/main`에서 다음을 다시 확인한다.

- 대상 경로와 symbol이 존재하는가
- 직접 관련 테스트가 존재하는가
- fallback·compatibility path가 무엇인가
- ownership 계약이 이미 이전됐는가
- 제거 대상의 실행 참조가 남아 있는가
- 검증 명령이 현재 환경에서 유효한가

계획과 저장소가 충돌하면 구현을 억지로 맞추지 않고 계획 drift를 먼저 해소한다.

## 8. 상태와 완료

일반 WP 일정, 다음 작업, 과목별 진행 상태는 대화에서 관리한다.
상태 전용 plan/evidence를 만들지 않는다.

제품 테스트는 다음을 검증한다.

- 사용자 동작
- 상태 전이와 불변조건
- 타입과 API 경계
- browser flow
- build·artifact·rollback

제품 테스트는 다음을 검증하지 않는다.

- 다음 WP
- 현재 WP
- 문서의 COMPLETE 문자열
- 일정 header
- 수동 체크박스 진행률

완료 근거는 최신 main의 구현과 실행 증거다.

## 9. 검증과 보고

계획·workflow 문서를 변경하면 링크, 실제 명령, 현재 제품 방향, 동결 범위, 상태 결합 여부를 검증한다.

```bash
uv run pytest -q tests/test_planning_workflow_consistency.py
uv run pytest -q tests/test_agent_registry_consistency.py
```

최종 보고는 `AGENTS.md` 형식을 따른다.
실제 게시 시에만 커밋 SHA를 기록한다.

## 10. Review backlog에서 실행 후보 공급

계획·runbook·다음 실행 task를 만들 때 repository 전체 broad scan부터 시작하지 않는다.

1. latest `origin/main`을 확인한다.
2. [`../reviews/review-backlog.md`](../reviews/review-backlog.md)를 먼저 읽는다.
3. backlog candidate를 production owner, sibling invariant, relevant diff/history, focused test/runtime evidence에 대조해 독립 재검증한다.
4. 여전히 실제 gap인 LIVE finding만 task 후보로 유지하고 SATISFIED / OBSOLETE / INVALID finding은 backlog에서 제거한다.
5. LIVE 후보 중 가치가 높은 finding을 실행 task로 승격한다.
6. hypothesis, primary criterion, authorized scope와 RDV strategy는 승격 시점의 최신 evidence에서 정한다.
7. 후보가 부족하면 targeted review를 먼저 수행하고, 그래도 부족할 때만 broad review로 확장한다.
8. 새 evidence-grounded unresolved finding은 backlog에 기록한다.
9. publication 뒤 latest main에서 primary criterion 만족을 다시 확인한 후에만 backlog에서 제거한다.

Discovery 순서는 `review backlog → targeted review → broad review`다.
Review backlog는 truth cache, product roadmap, 완료 이력 또는 실행 queue가 아니다. Runbook 승격만으로 finding을 제거하지 않는다.

각 finding은 failure domain, current evidence, likely owner, primary risk/invariant와 semantic revalidation anchors만 유지한다. 구현 recipe, 상세 patch plan, authorized scope, lifecycle status, RED/GREEN history, stale SHA 중심 evidence와 filler는 기록하지 않는다.

승격 task는 기본적으로 `한 작업 = 한 failure domain = 한 hypothesis = 한 primary criterion`을 유지한다.