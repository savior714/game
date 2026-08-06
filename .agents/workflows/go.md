---
situation: 세션 이관
level: Recommended
description: 현재 제품 방향과 검증된 다음 실행 경계를 새 세션에 전달
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# 세션 이관 워크플로우

이 워크플로우는 새 세션이 과거 대화나 최근 커밋을 추측하지 않고 **현재 제품 방향, 검증된 baseline, 다음 단일 실행 경계**를 복원하도록 한다.

## 1. 이관 전 확인

1. 최신 `origin/main`을 확인한다.
2. 이번 세션에서 실제로 게시된 커밋과 변경 파일을 확인한다.
3. 실행한 검증과 실행하지 못한 검증을 구분한다.
4. `AGENTS.md`, `PROJECT_RULES.md`, 현재 product spec과 충돌이 없는지 확인한다.
5. 다음 작업이 하나의 failure domain으로 좁혀졌는지 확인한다.

검증 결과 파일이나 특정 artifact가 존재한다고 가정하지 않는다.
현재 저장소에서 실제 명령과 파일을 확인한 뒤 필요한 항목만 읽는다.

## 2. MEMORY 갱신 조건

[`MEMORY.md`](../../docs/agent-context/memory/MEMORY.md)는 다음 중 하나가 바뀐 경우에만 갱신한다.

- 최우선 제품 방향
- 포함·동결 범위
- 다음 실행의 종류
- 반복 세션에서 반드시 보존해야 할 안정적인 baseline

다음 내용은 MEMORY에 누적하지 않는다.

- 과목별 진행률
- 모든 커밋 목록
- 완료된 작업의 상세 diff
- 다음 WP 또는 장기 일정
- 이미 authority 문서에 있는 규칙의 복사본

MEMORY는 200줄 이하로 유지하고 현재 product spec 링크와 다음 단일 실행 경계를 담는다.

## 3. 현재 AidenGame 기본 handoff

범위가 별도로 지정되지 않았다면 다음을 전달한다.

- 현재 우선순위: Math, English, Korean, Science 일반 문제풀이 신뢰성
- 동결 범위: Ocean Rescue와 `experiments/` 신규 기능·구조 이전
- 다음 실행: 최신 main에서 네 과목 공통 브라우저 진단 또는 아직 닫히지 않은 첫 failure domain
- 완료 근거: 코드, focused test, 실제 브라우저 증거, 게시 커밋

최근 커밋이 Ocean Rescue라는 이유로 다음 세션에 해당 작업을 지시하지 않는다.

## 4. 이관 출력

이관 내용은 다음 구조로 충분하다.

```text
CURRENT DIRECTION:
- <현재 최우선 제품 방향>

VERIFIED BASELINE:
- <이미 main에서 검증된 사실 1~5개>

OPEN FAILURE DOMAIN:
- <아직 닫히지 않은 원인 하나 또는 진단 작업>

NEXT ACTION:
- <새 세션의 첫 물리 작업 하나>

VERIFY:
- <재현 또는 focused 검증 명령>

REFERENCE:
- <가장 가까운 authority 문서 1~3개>
```

긴 과거 이력이나 전체 roadmap을 복사하지 않는다.
다음 세션이 현재 main을 읽어야만 알 수 있는 세부 구현은 handoff에 장문으로 넣지 않는다.

## 5. 검증

문서 또는 MEMORY를 갱신했다면 직접 관련 focused test를 실행한다.
현재 방향 handoff 검증은 다음이다.

```bash
uv run pytest -q tests/test_core_quiz_reliability_policy.py::test_memory_handoff_tracks_current_product_direction
```

저장소 코드를 수정했다면 해당 failure domain의 검증을 별도로 실행한다.
검증하지 못한 항목을 PASS로 기록하지 않는다.

## 6. 보고

세션 이관은 push를 강제하지 않는다.
이미 게시된 변경과 미게시 변경을 구분하고, 실제 게시 시에만 커밋 SHA를 기록한다.

금지:

- 존재하지 않는 renderer·backend 명령 사용
- 자동 생성된 roadmap을 다음 작업의 권위로 사용
- 새 session handoff를 위해 상태 전용 문서 생성
- 사용자가 요청하지 않은 에이전트별 장문 프롬프트 여러 개 생성
- 검증 실패 상태를 성공 이관으로 보고
