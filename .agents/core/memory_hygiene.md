---
scope:
- docs/agent-context/memory/MEMORY.md
always_apply: false
priority: 1
domain: core
verify_with:
- just memory-verify
---
<!-- Language: ko -->

# Memory Hygiene Check

본 문서는 프로젝트 세션 메모리(`MEMORY.md`)의 위생 상태를 유지하고 관리하기 위한 규칙을 정의합니다.

---

## 1. Memory Hygiene Standards

세션 종료 전 반드시 `docs/agent-context/memory/MEMORY.md`의 상태를 점검해야 합니다.

### 1.1 필수 점검 항목
- **라인 수 제한**: 파일 전체 라인 수를 **200줄 이하**로 유지합니다.
- **중복 링크 확인**: 동일한 리소스나 결정에 대한 중복 링크가 없는지 확인합니다.
- **검증 스크립트**: `just memory-verify`를 실행하여 정합성을 확인합니다.

### 1.2 위생 불량 시 대응
- 파일이 200줄을 초과하거나 구조가 복잡해진 경우, 오래된 로그나 결정 사항을 `docs/agent-context/memory/changelog/` 하위로 이관합니다.
- 위생 상태가 불량한 경우 세션을 종료하지 않고 먼저 정리 작업을 수행합니다.
