# AGENTS.md — Execution Protocol (Adaptive)

## 0. Purpose
이 문서는 에이전트의 실행 방식(How)을 정의한다.
이 프로젝트는 **TDD(Test-Driven Development)**를 최우선 원칙으로 하며, 시스템적으로 이를 강제한다.

---

## 1. Core Execution Flow (Always-On)

모든 작업은 아래 순서를 따른다:

1. **Context Sync**: `PROJECT_RULES.md` 및 기존 설계 문서를 확인한다.
2. **TDD 확인**: `tests/` 선검토 및 관련 테스트 존재 여부를 확인한다.
3. **정정 우선**: 코드 수정 전 문서(docs/)나 테스트(tests/) SSOT를 먼저 수정한다.
4. **Red Step (Fail First)**: 실패하는 테스트를 먼저 작성한다. (Assertion 필수)
5. **Green Step (Implement)**: 테스트를 통과할 만큼의 코드만 작성한다.
6. **Verification**: `verify.sh`를 실행하여 전체 시스템 무결성을 검증한다.

---

## 2. Recommended Tools (Allowlist)

이 프로젝트는 효율적인 개발을 위해 다음 도구들의 사용을 권장하며 우선적으로 활용한다:

- **uv**: Python 패키지 매니저 및 환경 관리
- **ty / pyx**: 타입 체크 및 pytest 실행 최적화 도구
- **ruff**: 초고속 Python Linter & Formatter
- **nu**: Nushell 기반의 현대적 스크립팅
- **just**: 명령 실행기 (Justfile)
- **nix**: 선언적 개발 환경 구성 (flake.nix)

---

## 3. SSOT Principles

역할 기반 단일 출처:
- 정책/스택: `PROJECT_RULES.md`
- 설계 결정: `docs/specs/`
- 요구사항 계약: `tests/`
- 세션 맥락: `docs/memory/`

---

## 4. Verification (Tiered)

- **L1 (Local)**: `pytest`, `lint` (ruff/biome)
- **L2 (Integration)**: `verify.sh`
- **L3 (CI)**: GitHub Actions / CI Pipeline

---

## 5. TDD Gate (Fatal Constraint)

코드 생성 전 반드시 아래 조건을 만족해야 한다:

1. 관련 `tests/` 파일 존재
2. 최소 1개의 실패 테스트 존재 (red-first)
3. 테스트는 명확한 assertion 포함

위 조건 미충족 시 **코드 작성이 금지**되며, `verify.sh` 및 `pytest` 플러그인에 의해 차단된다.

---

## 6. Execution Rules

- TDD 우선 (`tests/` 먼저 확인)
- Dirty-Write 금지 (수정 후 즉시 lint)
- 파일 500라인 초과 금지
- 경로 추측 금지 (실제 확인)
- SSOT 문서 먼저 수정 후 코드 반영

---

## 7. Stop Condition

- 요구사항 명확
- 리스크 식별 완료
- `verify.sh` 통과
- 실행 가능한 해답 확보
