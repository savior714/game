---
status: LEGACY_REFERENCE_ONLY
last_verified: 2026-08-06
implementation: scripts/agent/orchestration/
current_execution_authority: AGENTS.md
---

# Optional Legacy Orchestration Library

`scripts/agent/orchestration/`에는 과거에 만든 typed multi-phase orchestration helper가 남아 있다.
이 package는 현재 AidenGame 작업의 필수 실행 파이프라인이나 자동 dispatch authority가 아니다.
현재 작업 선택, 분해, 검증, 게시 규칙은 `AGENTS.md`, `PROJECT_RULES.md`, 가장 가까운 product/technical spec을 따른다.

## 1. 현재 역할

이 package는 다음 경우에만 선택적으로 사용할 수 있다.

- 사용자가 orchestration library 자체의 유지보수·검증을 요청함
- typed data contract를 재사용하는 명시적 script 작업이 있음
- 기존 orchestration tests의 failure를 독립 failure domain으로 수정함

범위가 없는 “다음 작업”, 일반 구현, local LLM 위임에서 자동 실행하지 않는다.
파일 그룹마다 subagent를 만들거나 5단계 pipeline을 거쳐야 한다는 저장소 전역 규칙은 없다.

## 2. 실제 package 구조

| 파일 | 역할 |
|---|---|
| `scripts/agent/orchestration/spec.py` | WorkSpec, TaskSpec, DiffResult, AuditReport 등 typed data contract |
| `scripts/agent/orchestration/analyzer.py` | WorkSpec을 task 후보로 변환 |
| `scripts/agent/orchestration/dispatcher.py` | dispatch instruction과 result parsing helper |
| `scripts/agent/orchestration/auditor.py` | DiffResult audit helper |
| `scripts/agent/orchestration/fixer.py` | audit finding 기반 fix request helper |
| `scripts/agent/orchestration/final_auditor.py` | 최종 orchestration result 조합 |
| `scripts/agent/orchestration/__init__.py` | PipelineOrchestrator entry |

실제 signature와 enum은 현재 source와 tests가 authority다. 이 문서의 오래된 예시를 보고 API를 추측하지 않는다.

## 3. 현재 실행 계약과의 관계

현재 AidenGame 기본 작업은 다음을 따른다.

```text
한 작업
= 한 failure domain
= 한 검증 가능한 가설
= 한 binary criterion
= 한 독립 검증
```

- 강하게 결합된 source, caller, test, config는 한 작업으로 다룰 수 있다.
- 파일 그룹 수를 기준으로 task를 자동 분해하지 않는다.
- 일반 작업은 reservation 없이 isolated worktree에서 실행한다.
- local LLM에는 현재 실행할 한 단계만 전달한다.
- 사용자 결정이 필요한 material context gap이 있을 때만 질문 하나를 한다.
- 저장소 Blueprint는 사용자가 명시적으로 요청한 경우에만 만든다.

orchestration helper를 사용하더라도 위 계약을 바꾸지 않는다.

## 4. Legacy assumptions

기존 package와 tests에는 과거 도구·audit category가 남아 있을 수 있다.
예를 들어 route gate, partial-edit category 또는 generic task dispatch model은 현재 repository-wide policy가 아니다.

- legacy enum과 helper 존재를 현재 작업 의무로 확대 해석하지 않는다.
- 제거 또는 변경은 package 자체가 명시적 작업 범위일 때만 수행한다.
- package를 사용하지 않는 일반 작업을 이 library에 맞추기 위해 production workflow를 변경하지 않는다.
- code와 test가 실제로 사용하는 contract를 확인한 뒤 별도 migration을 계획한다.

## 5. 테스트

현재 package의 직접 test가 존재한다.

- `tests/test_orchestration_spec.py`
- `tests/test_orchestration_analyzer.py`
- `tests/test_orchestration_auditor.py`
- `tests/test_orchestration_pipeline.py`

package를 수정할 때는 변경한 component의 focused test부터 실행한다.
전체 AidenGame product 검증을 orchestration package test로 대체하지 않는다.

## 6. 사용 전 확인

1. 최신 `origin/main`에서 package와 tests가 존재하는지 확인한다.
2. 현재 request가 package 사용을 실제로 요구하는지 확인한다.
3. dispatch runtime 또는 callback을 누가 제공하는지 확인한다.
4. legacy category가 현재 정책과 충돌하지 않는지 확인한다.
5. package를 사용하지 않는 더 단순한 직접 실행이 있는지 확인한다.
6. 사용한다면 한 failure domain과 독립 verification을 유지한다.

## 7. 금지

- `AGENTS.md`에 없는 section을 이 문서가 있다고 가정
- 존재하지 않는 `just route` 또는 route manifest를 필수 gate로 요구
- 모든 작업을 analyzer → dispatcher → auditor → fixer → final auditor로 강제
- task tool이나 특정 subagent runtime이 항상 존재한다고 가정
- orchestration result status를 product completion 근거로 사용
- package 사용을 위해 일반 과목 안정화 범위를 확장

## 8. 향후 처리

이 library는 현재 삭제 대상도 기본 실행 경로도 아니다.
다음 중 하나가 있을 때만 별도 결정을 한다.

- 실제 workflow에서 재사용할 명확한 use case
- 유지 비용이 반복적으로 발생함
- tests 또는 dependency가 필수 gate를 깨뜨림
- 사용자가 제거·현대화·재사용을 명시적으로 요청함

그전까지 `LEGACY_REFERENCE_ONLY`로 유지한다.
