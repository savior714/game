---
scope:
- '*'
always_apply: false
priority: 1
domain: core
verify_with:
- just prevent-tech-debt
---
<!-- Language: ko -->
# Core Execution & Operating Principles
본 문서는 에이전트의 핵심 사고 방식(Why/What)과 실행 방식(How)을 규정하는 핵심 실행 규칙입니다.
---
## 1. Core Operating Principles
상세: [principles.md](principles.md)
---
## 2. Non-Negotiable Execution Rules
### MUST
#### 2.1 Disk State First
- 수정 전 반드시 호스트 **읽기 도구**로 exact snippet을 확보한다 (Cursor `Read` · OpenCode `read` · Antigravity `view_file` — [runtime_edit_tools.md §1](./runtime_edit_tools.md)).
- truth는 디스크 상태뿐이다.
- grep 결과나 기억만으로 부분 수정 금지.
- 파일 I/O 실수 예시: [error_patterns.md §1](error_patterns.md#1-파일-편집-실수).
- 편집 도구 실패·재시도·도구 선택: [runtime_edit_tools.md](./runtime_edit_tools.md) · Cursor 상세 [routing.md](./routing.md) §1.
#### 2.2 Verification First
- lint/type/test 실패 상태에서 완료 선언 금지.
- severity 하향(`error → warn`) 또는 gate 우회 금지.
#### 2.3 Plan First (강제 트리거)
**트리거 키워드 감지**: "계획", "plan", "blueprint", "roadmap",
"설계", "로드맵", "실행 계획", "구현 계획" 중 하나라도 발견 시:
1. **반드시** [.agents/workflows/plan.md](../workflows/plan.md)를 **Read** (워크플로 SSOT — 별도 라우팅 API 없음)
2. 해당 템플릿을 **전부 따라야 함**
3. `docs/plans/PLAN_*.md`에 Blueprint 생성 (`.hermes/plans/ 아님`)
4. `just plan-lint <path>`로 검증 후 저장
5. 채팅으로 끝내지 말고 파일로 산출
**검증**: 작성 직후 `python3 scripts/plan_loop/plan_lint.py <path>` 실행 —
실패 시 수정 없이 제출 금지.
자유형 계획 텍스트만 던지는 것으로 대체하지 않는다.
#### 2.4 TDD Red-First
- 구현 전 실패 테스트를 작성하고 실행 로그를 확인한다.
- `Red → Green → Refactor`를 강제한다.
- 구현 후 테스트를 덧붙이는 방식 금지.
- assertion 없는 테스트, Red 로그 없는 “TDD 완료” 선언 금지.
- **예외 (UI/Styling)**: 비즈니스 로직이 없는 순수 View 렌더링, CSS 및 레이아웃 수정 등 디자인 변경 작업은 TDD Red-First 요건(실패 테스트 선 작성)에서 면제된다. (오버엔지니어링 방지 및 실용성 확보)
#### 2.5 Roadmap Integrity
- 미래 태스크(`todo`, `pending`)는 명시적 폐기 없이 삭제하지 않는다.
#### 2.6 Section Numbering Integrity
- 규칙 섹션 번호는 연속성을 유지한다(예: 2.5 다음은 2.6).
- 번호 공백이 생기면 자동/수동 참조 불일치가 발생할 수 있으므로 즉시 정리한다.
#### 2.7 README MSOT Integrity
- 루트 `README.md`의 진척도나 아키텍처 명세를 업데이트하기 전, 반드시 `find`나 `ls`를 통해 해당 파일/디렉토리가 현재 코드베이스에 존재하는지 실측한다. (과거 아카이브된 파일에 대한 허위 참조 방지)
- 라이선스 리스크(SSPL, BSL 등)가 있는 기술 도입은 원칙적으로 금지한다.
- 불가피한 경우 `docs/knowledge/research/`에 분석 문서를 선행 작성하고 사용자의 최종 승인을 득한 후 진행한다.
#### 2.8 Context Route Gate (편집 전 강제, IDE 공통)
저장소 파일을 **생성·수정·삭제**하기 전, 아래 순서를 반드시 지킨다.
1. `just route <paths> --json --write-manifest`
2. `must_read` 전량 Read
3. `just route-read <paths...>`
4. `just route-gate-check <paths>`
절차·lazy Read 상세: [routing.md](./routing.md) §2
#### 2.9 Secrets & Credentials (ZERO-LEAK, 재발 금지)
상세: [PROJECT_RULES.md §4.1](../../PROJECT_RULES.md) · [emr_security.md](../domains/medical/emr_security.md)
#### 2.10 Information Integrity & Honesty (Agentic Honesty)

**MUST**
- 디스크·도구·테스트로 확인하기 전 **원인·동작·존재 여부를 단정하지 않는다.**
- 불확실하면 "모름"을 명시하고, 확인 경로(Read·grep·테스트·사용자 질문)를 제시한다.
- 그럴듯한 추측으로 패치·설계·스펙 서술을 채우지 않는다.
- Blueprint 경로·README·스펙과 코드가 상충하면 **실측(rg/Glob/Read) 우선** — 문서만으로 경로·동작을 단정하지 않는다.

**MUST NOT**
- "아마 ~일 것", "보통 ~한다"만으로 Verify PASS·완료 선언.
- Read/grep 없이 파일·API·설정 존재를 단정.

**Cross-ref**: [diagnose.md](../workflows/diagnose.md) Anti-pattern · [routing.md](./routing.md) §1 터미널 실측 · [principles.md](principles.md) §1.1 Think Before Coding.

#### 2.11 Root Directory & Temporary Files (No Root Clutter)
- **MUST NOT**: 디버깅, 텍스트 치환, 테스트 목적의 일회성/임시 스크립트(`.py`, `.ts`, `.js`, `.sh` 등)를 프로젝트 루트 디렉토리(`CWD: .`)에 임의로 생성하거나 방치하지 않는다.
- **MUST**: 모든 임시/스크래치 파일은 반드시 `scratch/` 또는 `scripts/agent/` 디렉토리 내부에 생성해야 하며, 사용이 끝난 후에는 가급적 삭제한다.
- **DDD Adherence**: 정식 프로덕션 및 비즈니스 로직 코드는 프로젝트 계층 구조(`apps/`, `packages/`, `services/` 등)를 위반하여 루트에 생성해서는 안 되며, 반드시 도메인 및 아키텍처 규칙(`PROJECT_RULES.md`)에 맞는 적절한 경로에 생성해야 한다.
### SHOULD
- 작은 semantic patch 단위로 작업한다.
- formatter 후 재읽기한다.
- AST/codemod를 우선 고려한다.
- JSX/Tailwind 수정은 regex보다 AST 기반을 선호한다.
---
## 3. Execution Flow
### 3.1 Context Sync
작업 시작 시 다음을 순서대로 확인한다.
1. `PROJECT_RULES.md`
2. 관련 specs
3. `docs/agent-context/memory/MEMORY.md`
4. `tests/`
5. **Plan Blueprint 가 있으면** `scripts/agent/auto_load_preread.py docs/plans/<plan>.md` 실행 → Task Pre-read 목록 전량 Read
6. **편집 대상이 정해지면 즉시** [routing.md](./routing.md) §2 Context Route Gate
 (`just route <paths> --json --write-manifest` → `must_read` 전량 Read → `just route-read <paths...>` → `just route-gate-check <paths>`)
연관 가이드라인을 추출하고, 계획에 반영한다.
### 3.2 Read Before Edit
- 파일 읽기 → exact snippet 확보 → **부분 수정** 또는 **전체/신규 쓰기** (런타임별 도구명: [runtime_edit_tools.md §1](./runtime_edit_tools.md))
- 수정 전에는 반드시 현재 디스크 상태를 다시 확인한다.
- formatter가 multiline wrapping / prop ordering / import sorting / indentation을 바꿀 수 있으므로 이전 old/target context를 신뢰하지 않는다.
### 3.3 SSOT / TDD
우선순위는 다음과 같다.
1. tests
2. specs
3. implementation
반드시 `Red → Green → Refactor` 순서를 따른다.
### 3.4 Implementation
- minimal patch
- bounded scope
- dirty-write 금지
- 추상화 남발 금지
- 구현 시점 품질(에러 경계·중첩 평탄화·helper 중복 금지): [code_quality_lifecycle.md](code_quality_lifecycle.md) §2
### 3.5 Verification
- 작업 범위에 맞는 검증을 통과한 후 완료 선언한다.
- 변경 시 formatter / lint / typecheck / test를 다시 실행하고, 필요하면 재읽기한다.
- **LLM/API 연동 디버깅**: 파싱 실패·opaque 응답 시 hub raw JSONL을 계측 SSOT로 우선 조회한다 — `just raw-logs`, `just api-response-errors` ([diagnose.md](../workflows/diagnose.md) AidenGame 부록).
- 저장소 수정 후 완료 응답 직전: [verification.md](verification.md) §2.5 (`just lint` + renderer `pnpm run typecheck`)로 전체 오류를 확인하고, 내가 변경한 파일의 오류를 우선 0으로 맞춘 뒤 타 파일 기존 오류는 [reporting.md](reporting.md) §1.5에 블로커/경고로 보고한다.
---
## 4. File Access Priority
상세: [routing.md](./routing.md) §3
