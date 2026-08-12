---
situation: 구현·문서·설정 사이의 drift 확인과 정합화
level: Recommended
description: 실제 code/test/config를 기준으로 stable contract 문서의 drift를 최소 수정하는 sync workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Sync workflow

상세 절차는 [`sync/SKILL.md`](../skills/sync/SKILL.md)를 따른다.

## 1. 역할

sync는 다음 두 경우를 구분한다.

- **implementation drift:** 코드·설정이 stable product/technical contract와 어긋남
- **documentation drift:** 실제 구현은 올바르지만 authority 문서가 오래됨

코드가 언제나 문서보다 옳다고 가정하지 않는다.
사용자 결정과 product contract가 구현을 제한할 수 있으므로 어느 쪽이 drift인지 먼저 판정한다.

## 2. 명령 주의

현재 `Justfile`의 `sync` recipe는 dependency/environment 동기화용 `uv sync`다.
spec alignment CLI가 아니다.

- spec alignment CLI(--check), code lock, 자동 명세 생성 기능이 존재한다고 가정하지 않는다.
- 문서에 적힌 명령은 최신 `Justfile`, `verify.sh`, `scripts/`에서 실제 존재 여부를 확인한다.
- sync 완료를 위해 특정 자동화 manifest나 외부 service를 요구하지 않는다.

## 3. 정합화 순서

1. 사용자가 지정한 기능·문서·변경 diff를 확인한다.
2. authority 문서와 직접 관련 code/test/config를 읽는다.
3. 각 claim을 `MATCH`, `DOC_STALE`, `IMPLEMENTATION_VIOLATION`, `UNVERIFIED`로 분류한다.
4. 첫 drift 원인 하나를 선택한다.
5. 문서 drift면 해당 stable contract만 최소 수정한다.
6. 구현 위반이면 자동 수정하지 않고 failure domain과 criterion을 먼저 고정한다.
7. 링크·경로·실제 명령·동결 범위를 검증한다.
8. 수정 후 같은 claim을 다시 비교한다.

## 4. 문서별 역할

- `AGENTS.md`: 실행·Git·검증·보고 계약
- `PROJECT_RULES.md`: 제품·아키텍처·품질 경계
- product spec: 사용자 동작과 수용 기준
- technical spec: runtime boundary와 trade-off
- `MEMORY.md`: 현재 방향과 다음 실행 경계
- README: 저장소 진입 정보
- plan/evidence: 현재 authority가 아니라 명시적 계획 또는 과거 증거

진행률만 바뀌었다면 stable authority 문서를 수정하지 않는다.

## 5. 현재 동결 정책

일반 과목 안정화 중:

- Ocean Rescue와 `experiments/` 기술 문서는 reference-only 상태를 유지한다.
- 과거 plan의 next WP를 현재 작업으로 복원하지 않는다.
- 문서 drift를 이유로 동결된 runtime migration을 자동 재개하지 않는다.

## 6. 검증

문서 정합화에서는 다음을 확인한다.

- 모든 local Markdown link가 존재함
- 경로와 command가 실제 저장소에 존재함
- authority 우선순위가 `AGENTS.md`와 일치함
- product test가 일정 상태를 검증하지 않음
- MEMORY가 현재 방향과 다음 단일 실행 경계를 반영함
- README가 현재 active/frozen 구분을 명확히 함

관련 focused test 중 실제 변경에 필요한 항목만 실행한다.

## 7. 결과

```text
RESULT: PASS | BLOCKED
CHANGE: <정합화한 stable contract 한 문장>
VERIFY: <비교한 claim과 focused 검증 결과>
```

모든 문서를 일괄 갱신하지 않는다.
직접 drift가 확인된 문서만 수정한다.
