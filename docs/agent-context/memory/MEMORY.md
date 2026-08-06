---
id: MEMORY
type: MEM
status: active
last_verified: 2026-08-06
---

# Memory

**SSOT**: `docs/agent-context/memory/MEMORY.md` · 규정: [memory_hygiene.md](../../../.agents/core/memory_hygiene.md) (≤200줄)

## Current direction

- 현재 최우선 목표는 신규 기능·콘텐츠·게임성보다 일반 과목 문제풀이의 신뢰성 안정화다.
- 대상은 Math, English, Korean, Science의 운영 문제풀이 흐름이다.
- 상세 계약은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`를 따른다.
- 네 과목 모두 완료되기 전에는 Ocean Rescue와 `experiments/`의 신규 기능·구조 이전을 재개하지 않는다.
- 사용자가 현재 요청에서 방향을 명시적으로 변경하거나 치명적 회귀·데이터 손상·보안 문제를 별도 failure domain으로 지정한 경우만 예외다.

## Execution contract

- 다음 작업은 최신 `origin/main`에서 네 과목에 동일한 공통 브라우저 진단을 실행하는 것이다.
- 첫 `FAIL` 과목을 선택하고, 모두 통과하면 가장 큰 `PASS_WITH_GAP` 과목을 선택한다.
- 한 실행은 한 failure domain, 한 재현 조건, 한 binary criterion으로 제한한다.
- 첫 과목은 기존 구조 안에서 안정화하고, 두 번째 과목에서 동일 책임의 중복이 확인된 뒤에만 `shared/` 추출을 검토한다.
- 과목 하나가 완료될 때마다 직접 영향 회귀를 확인하고 `origin/main`에 게시한다.

## Verified baseline

- 비수학 과목의 다음 문제 전환 복구와 네 과목 48px 터치 타깃 보장은 이미 main에 반영됐다.
- 동일 증상이 최신 main에서 재현되지 않으면 다시 개발 목표로 선택하지 않는다.
- `tests/test_math_next_question_progression.py`, `tests/test_nonmath_next_question_progression.py`, `tests/test_nonmath_browser_acceptance.py`는 출발점이지만 과목 완료 증명 전체를 대체하지 않는다.

## Next

- 소스 수정 전에 Math, English, Korean, Science 공통 브라우저 진단을 실행한다.
- 결과에서 첫 failure domain 하나만 선택한다.

## Verify

```bash
uv run pytest -q tests/test_core_quiz_reliability_policy.py::test_memory_handoff_tracks_current_product_direction
```
