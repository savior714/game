---
name: plan
description: 전략적 설계 및 문서화 - 요구사항을 물리적 실행 가능 단위로 분해하고 설계 문서(Blueprint) 작성
---

# 🏗️ 전략적 설계 및 문서화 워크플로우 (/plan)

이 워크플로우는 요구사항을 **물리적으로 실행 가능한 독립적 기능 단위**로 분해하고, 이를 **설계 문서(Blueprints)**로 박제하여 후속 세션의 가이드라인으로 활용하기 위한 지침입니다.

> **환경 호환성**: 이 워크플로우는 **Claude Code(VS Code)** 및 **Google Antigravity** 양쪽 환경에서 동일하게 동작합니다.
> 각 Task의 `Action` 타입은 환경별 도구 매핑표를 참조하십시오.

## 환경별 도구 매핑

| Action 타입 | Claude Code |  Google Antigravity  |
| :---------: | :---------: | :------------------: |
|  파일 읽기  |   `Read`    |     `view_file`      |
|  파일 수정  |   `Edit`    | `replace_file_content` |
|  파일 생성  |   `Write`   |    `write_to_file`   |
| 터미널 실행 |   `Bash`    |    `run_command`     |

---

## 📋 핵심 실행 로직

### 0. 🛡️ 가이드라인 준수 (Compliance)

- **1 Task = 1 Action**: 하나의 태스크는 반드시 단일 도구 호출로 제한한다.
- **Step-Lock**: 각 태스크 실행 후 반드시 사용자의 승인을 대기한다.

### 1. Stale Context 방지 — 설계 전 현재 상태 확인

> 오래된 컨텍스트를 기반으로 설계하면 실제 코드와 어긋난 Blueprint가 만들어진다.

- 수정 대상 파일을 **설계 시작 전 반드시 읽어** 현재 상태를 확인한다.
- 파일의 실제 라인 수, 구조, 최근 변경 흔적을 파악한 뒤 설계를 시작한다.
- 컨텍스트가 불일치할 경우 설계를 즉시 중단하고 사용자에게 보고한다.

### 2. 영향 범위 분석 (Impact Scope Analysis)

> 공통 모듈이나 타입 파일 수정 시 사이드이펙트를 설계 단계에서 미리 식별한다.

- 수정 대상 파일을 **다른 파일이 import/참조하는지** 확인한다.
- 영향받는 파일 목록을 Blueprint의 `Impact Scope` 섹션에 명시한다.
- 영향 범위가 3개 파일 이상이면 Task 순서에 **의존성 방향**을 명시한다.

### 3. 원자적 분해 및 모듈화 검토 (Atomic Decomposition)

- 사용자의 목표를 분석하여 즉시 실행 가능한 마이크로 단위 태스크(Task)로 분해한다.
- 수정 대상 파일이 **500라인 이상**이거나 책임이 과중할 경우, 기능 수정 전 **Refactoring Task**를 우선 배치한다.
- **물리적 산출물**: 분석된 내용을 `./docs/plans/[goal_name].md` 파일로 생성한다. (UTF-8 no BOM 준수)

### 4. 설계 무결성 및 SSOT 정렬 (Integrity & SSOT Alignment)

- 모든 설계는 `docs/CRITICAL_LOGIC.md`의 비즈니스 로직과 충돌하지 않는지 우선 검토한다.
- 각 태스크는 **독립적으로 구현 및 검증이 가능**해야 하며, 상호 의존성을 명확히 표기한다.
- 구현 전 필요한 **의사코드(Pseudocode)**와 기술적 제약 조건을 포함한다.

---

## 🏗️ BLUEPRINT DOCUMENT TEMPLATE (Saved to ./docs/plans/)

```markdown
# 🗺️ Project Blueprint: [목표 동작 이름]

## 문서 메타 (Version SSOT)
- **Last Verified**: [YYYY-MM-DD]
- **Tested Version**: [스택/버전]
- **Min Supported**: [환경]
- **Reference**: [관련 SSOT/외부 근거]

## 문서 경계(SSOT)
- **규칙/운영**: `PROJECT_RULES.md`
- **결정/핵심 불변(대안/채택 이유/증적 경로)**: `docs/CRITICAL_LOGIC.md`
- **요구사항/계약(specs)**: `docs/specs/`
- **세션 지식(memory/plans)**: `docs/memory/`

---

## 🎯 Architectural Goal

- [설계가 해결하려는 핵심 비즈니스 로직 및 목적 요약]
- **SSOT 정렬**: `docs/CRITICAL_LOGIC.md`와의 충돌 여부 확인 완료

## 🔍 Impact Scope (영향 범위)

| 수정 대상 파일 | 현재 라인 수 | 참조하는 파일         | 비고                                      |
| -------------- | :----------: | --------------------- | ----------------------------------------- |
| `[파일 경로]`  |    [N]줄     | `[import하는 파일들]` | [300라인 초과 시 "Refactoring 선행" 표기] |

## 🛠️ Step-by-Step Execution Plan

> 아래 목록은 **독립적인 기능 단위**로 설계되었습니다. 우선순위에 따라 원하는 항목을 선택하여 진행을 요청하세요.

### 📦 Task List

> ⚠️ **각 Task는 단 하나의 Action으로 완료되어야 한다.**
> 파일이 500라인 이상일 경우 기능 수정 전 Refactoring Task를 반드시 선행할 것.

- [ ] **Task 1: [파일명] 읽기 — 현재 상태 파악**
  - **Action**: 파일 읽기
  - **Target**: `[파일 전체 경로]`
  - **Goal**: [무엇을 확인하기 위해 읽는지]
  - **Verify**: 파일 실제 라인 수 및 구조가 설계 전제와 일치함을 확인한다.
  - **Dependency**: None

- [ ] **Task 2: [파일명]에 [구체적 대상] 추가/수정/삭제**
  - **Action**: 파일 수정
  - **Target**: `[파일 전체 경로]`
  - **Goal**: [이 단일 변경이 달성하려는 목표]
  - **Pseudocode**: [변경될 코드 초안, 5줄 이내]
  - **Verify**: [수정 후 확인할 수 있는 물리적 증거 — 예: "해당 함수가 새 파라미터를 받음"]
  - **Dependency**: Task 1
```

## ⚠️ 기술적 제약 및 규칙

- **Encoding**: UTF-8 no BOM 고정.
- **Refactoring**: 기능 구현에 필수적이지 않은 리팩토링 금지 (단, 500라인 초과 시 분리 선행).

## ✅ Definition of Done

1. [ ] Impact Scope에 명시된 모든 영향 파일에서 사이드이펙트가 없음을 확인함.
2. [ ] 선택된 모든 Task의 `Verify` 조건이 충족됨.
3. [ ] **통합 검증(`verify.ps1`)**을 실행하여 `exitCode: 0`을 달성함.
4. [ ] 타입 체크 및 린트 오류 Zero 달성.
5. [ ] `docs/memory/MEMORY.md`(인덱스·Anti-Drift) 및 관련 SSOT·`project_changelog_*.md` 등에 변경 사항 반영 완료.
6. [ ] 파일 500라인 가드레일 준수 여부 최종 확인.
