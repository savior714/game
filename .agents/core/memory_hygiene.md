---
scope:
- docs/agent-context/memory/MEMORY.md
always_apply: false
priority: 1
domain: core
verify_with:
- uv run pytest -q tests/test_core_quiz_reliability_policy.py::test_memory_handoff_tracks_current_product_direction
---
<!-- Language: ko -->

# Memory Hygiene Check

본 문서는 프로젝트 세션 메모리(`MEMORY.md`)의 위생 상태를 유지하고 관리하기 위한 규칙을 정의합니다.

## 1. Memory Hygiene Standards

세션 종료 전 `docs/agent-context/memory/MEMORY.md`의 상태를 점검한다.

### 1.1 필수 점검 항목

- 파일 전체를 200줄 이하로 유지한다.
- 동일한 결정과 리소스 링크를 중복 기록하지 않는다.
- 현재 `PROJECT_RULES.md`와 product spec이 가리키는 개발 방향을 반영한다.
- 과목별 진행률이나 다음 작업 이력을 누적하지 않고 현재 실행에 필요한 계약만 유지한다.
- 아래 focused 검증을 실행한다.

```bash
uv run pytest -q tests/test_core_quiz_reliability_policy.py::test_memory_handoff_tracks_current_product_direction
```

### 1.2 위생 불량 시 대응

- 200줄을 초과하거나 구조가 복잡해지면 오래된 로그를 `docs/agent-context/memory/changelog/` 하위로 이관한다.
- 제품 방향이 바뀌면 최신 product spec 링크, 현재 범위, 다음 실행 경계만 교체한다.
- 위생 검증이 실패하면 세션 handoff를 완료 처리하지 않는다.
