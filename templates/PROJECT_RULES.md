# PROJECT_RULES.md

## 1. Core Principles

### 1.1 TDD First & Coverage Gate
- 모든 기능 구현 및 버그 수정은 테스트 코드 작성이 선행되어야 한다.
- `verify.sh`는 코드 변경 시 테스트 변경 여부를 강제로 체크한다.
- **Coverage Gate**: 테스트 커버리지는 항상 80% 이상을 유지해야 하며, 미달 시 빌드가 실패한다.

### 1.2 SSOT & Hermeticity
- 모든 설계와 정책은 `docs/` 디렉토리 아래의 문서들을 유일한 진실의 원천으로 삼는다.
- **Environment Hermeticity**: 개발 환경은 `flake.nix`를 통해 완전히 고정되어야 한다.
- **Dependency Lock**: `uv.lock`은 반드시 버전 관리 시스템에 포함되어야 하며, `uv sync`를 통해 환경을 동기화한다.

---

## 2. Technical Stack (Allowlist)
- **Language**: [LANGUAGE_PLACEHOLDER]
- **Framework**: [FRAMEWORK_PLACEHOLDER]
- **Package Manager**: `uv`, `nix`
- **Scripting/Task**: `nu`, `just`
- **Lint/Format**: `ruff`, [LINT_TOOL_PLACEHOLDER]
- **Type/Test**: `ty`, `pyx` (pytest wrapper)

---

## 3. Directory Structure
- `docs/`: 명세 및 문서
- `src/` or `app/`: 소스 코드
- `tests/`: 테스트 코드
- `tools/`: 개발 도구 및 플러그인
- `.agents/`: 에이전트 전용 워크플로우

---

## 4. Enforcement
- **TDD Gate**: `verify.sh` 및 `pytest` 플러그인을 통한 코드 변경 차단.
- **Pre-commit**: 커밋 전 정적 분석 및 검증 강제.
- **CI**: 모든 PR에 대해 `verify.sh` 실행 필수.

---

## 5. Workflow Triggers
| 상황 | 호출 | 수준 |
|------|------|------|
| 신규 기능 | `/plan` | Mandatory |
| 에러 해결 | `/error` | Mandatory |
| 문서 작업 | `/index_knowledge` | Mandatory |
| 커밋 | `/git` | Mandatory |
| 시스템 동기화 | `/bootstrap` | Recommended |
