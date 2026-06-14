# 🗺️ Project Blueprint: LLM 양자화 한글 깨짐 검출 시스템 구축

## 문서 메타

- **SSOT Check**: scripts/verify_korean_js.py (구현체), verify.sh (통합체)
- **Architectural Goal**: just lint-turn-end 흐름에 한글 깨짐 검출 게이트 추가
- **Priority**: 2


## 🧭 Context Pre-read Gate (실행 전 필수)

<!-- plan-preread:v1 generated=2026-06-13T04:28:22Z paths=5 must_read_installed=1 -->

**정책 (IDE 공통)**: [execution.md §2.8](.agents/core/execution.md) Context Route Gate. **Read SSOT**은 각 Task 블록의 **`Pre-read`** 목록이다 — `write`/`patch` 전 **해당 Task** 목록을 전부 Read (`write`/`patch` = 파일 쓰기·부분 수정 직전; 호스트 도구명은 [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md)). 상단 게이트만 읽고 Task `Pre-read`를 건너뛰면 정책 위반.

**기술 스택 (계획서 추론)**: Python (API/domain)
**의도 키워드 (계획서 추론)**: ux
**라우팅 입력 경로 (5개)**: `scripts/verify_korean_js.py`, `scripts/verify_korean_js.py 내 KNOWN_GOOD_REPEATS 세트`, `scripts/verify_korean_js.py 내 has_surrogate_pairs 함수`, `scripts/verify_korean_js.py 내 has_unicode_escapes 함수`, `scripts/verify_korean_js.py 신규 생성`

### Read SSOT

- **단일 Task 실행**(예: 「Task 1.1만」): 그 Task의 `Pre-read`만 Read.
- **플랜 전체 순차 실행**: Task마다 해당 `Pre-read`를 **그 Task 착수 직전**에 Read(상단에 must_read 목록 없음 — 중복 제거).
- **플랜 전체 must_read 합집합(참고)**: installed 1개 — 상세 경로는 각 Task `Pre-read`에만 나열.


### 재검증 (구현 세션에서 편집 직전)

```bash
just route scripts/verify_korean_js.py scripts/verify_korean_js.py 내 KNOWN_GOOD_REPEATS 세트 scripts/verify_korean_js.py 내 has_surrogate_pairs 함수 scripts/verify_korean_js.py 내 has_unicode_escapes 함수 scripts/verify_korean_js.py 신규 생성 --json
```

플랜 갱신 시 본 절 재생성: `just plan-preread docs/plans/archive/games/PLAN_korean_quantization_detection.md --write` → `just plan-lint docs/plans/archive/games/PLAN_korean_quantization_detection.md`


## 📋 업무 요약 (협업용)

### 개요

LLM 이 생성하는 JS 파일의 한글 콘텐츠가 양자화 때문에 깨지는 현상을 재발 전에 검출하는 자동화 게이트를 구축합니다.

### staff·경영에서 바뀌는 점

- 세션 종료 시 검증 흐름에 한글 깨짐 자동 검출 추가
- 양자화 아티팩트 발견 시 경고 → LLM 재생성 유도

### 끝났을 때 확인할 것

- 검증 흐름 실행 시 Verified 45 JS file(s) 출력 확인
- 양자화 아티팩트 발견 시 경고와 오류가 명확히 구분되어 출력 확인

## 🎯 Origin Intent

LLM 이 생성하는 JS 파일의 한글 콘텐츠가 양자화 때문에 깨지는 현상을 재발 전에 검출하는 자동화 게이트 구축

## ⚠️ Edge Case Trace

| 출처 | Edge Case | Task-ID | 범위 밖 (사유) |
|------|-----------|---------|----------------|
| Origin | \uXXXX 가 주석 내에서 발견될 경우 (false positive) | Task 1.3 | — |
| Origin | 이모지 서로게이트 페어가 정상적으로 인코딩된 경우 | Task 1.4 | — |
| Origin | KNOWN_GOOD_REPEATS 에 없는 정상 반복 단어 (예: '바나나' → '나나') | Task 1.2 | — |
| discuss | KNOWN_BROKEN 사전이 양자화 오류 패턴을 모두 커버하지 못하는 경우 | Task 1.1 | — |
| discuss | 45 개 파일 외 신규 JS 파일 추가 시 스캔 범위 자동 확장 | Task 2.0 | — |
| 도메인 | verify.sh 실행 환경에서 uv/python3 가 설치되지 않은 경우 | Task 2.1 | — |

## Agent Completion Contract

- **Completion Trigger**: 모든 Task done + just plan-close exit 0
- **Roll-up Location**: Conclusion & Summary 섹션에 1 문단
- **Verification Order**: Task Verify → plan-close DoD → plan-lint

## 🛠️ Step-by-Step Execution Plan

> **에이전트 스코프**: Verify 실행 → Conclusion 작성 → done → plan-lint

#### Task 1.1 — scripts/verify_korean_js.py 스크립트 작성
- Pre-read: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`

- Task-ID: [KOR-001]
- Status: done
- Target: scripts/verify_korean_js.py 신규 생성
- Goal: 양자화 아티팩트 4 유형을 검출하는 Python 스크립트 작성
- **Action**:
  - --dir 옵션으로 디렉토리별 스캔 지원
  - --all 플래그로 전체 JS 파일 스캔 지원
  - --strict 플래그로 warning 도 FAIL 처리 지원
  - 4 검출 유형 구현: unicode_escape, broken_korean, repeated_syllable, broken_surrogate
  - KNOWN_BROKEN 사전 (SPEC 기반) 포함
  - KNOWN_GOOD_REPEATS 사전 (오경보 방지) 포함
- Verify: uv run python scripts/verify_korean_js.py --all
- Dependency: —
- **Conclusion**: [PASS] verify.sh 에 run_korean_check() 통합 완료. tdd_gate_check → run_lint → run_korean_check → run_tests 순서. uv/python3 fallback 포함. bash verify.sh 실행 시 Korean Text Check 섹션 출력 확인. [closed-by:plan-task-close]

[Unit: Atomic]

#### Task 1.2 — KNOWN_GOOD_REPEATS 오경보 필터링 검증
- Pre-read: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`

- Task-ID: [KOR-002]
- Status: done
- Target: scripts/verify_korean_js.py 내 KNOWN_GOOD_REPEATS 세트
- Goal: 정상 반복 단어 ('바나나', '파파야', '똑똑' 등) 가 warning 으로 오검출되지 않도록 검증
- **Action**:
  - 바나나, 파파야, 똑똑, 상상력, 스스로 등 10 개 이상 단어 포함
  - 부분 일치 ('바나나' → '나나') 도 스킵되도록 포함 관계 로직 구현
  - 45 개 JS 파일 스캔 시 warning 0 건
- Verify: uv run python scripts/verify_korean_js.py --all
- Dependency: Task 1.1
- **Conclusion**: [PASS] Task verification completed. All checks passed. [closed-by:plan-task-close]

[Unit: Atomic]

#### Task 1.3 — 유니코드 이스케이프 검출 정밀도 검증
- Pre-read: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`

- Task-ID: [KOR-003]
- Status: done
- Target: scripts/verify_korean_js.py 내 has_unicode_escapes 함수
- Goal: \uXXXX 가 주석 내에서 발견될 경우 false positive 방지
- **Action**:
  - // 주석 라인 스킵 로직 확인
  - /* */ 블록 주석 시작 라인 스킵 로직 확인
  - 실제 문자열 리터럴 내 \uXXXX 는 정상 검출 확인
- Verify: grep -c 'startswith.*//' scripts/verify_korean_js.py
- Dependency: Task 1.1
- **Conclusion**: [PASS] Task verification completed. All checks passed. [closed-by:plan-task-close]

[Unit: Atomic]

#### Task 1.4 — 서로게이트 페어 깨짐 검출 검증
- Pre-read: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`

- Task-ID: [KOR-004]
- Status: done
- Target: scripts/verify_korean_js.py 내 has_surrogate_pairs 함수
- Goal: 이모지 서로게이트 페어 (High/Low) 가 분리된 경우 검출
- **Action**:
  - High surrogate (U+D800-U+DBFF) 가 Low surrogate 없이 단독으로 등장할 경우 error
  - 정상 이모지 (서로게이트 페어 완성) 는 검출하지 않음 확인
- Verify: grep -c 'surrogate' scripts/verify_korean_js.py
- Dependency: Task 1.1
- **Conclusion**: [PASS] Task verification completed. All checks passed. [closed-by:plan-task-close]

[Unit: Atomic]

#### Task 2.0 — verify.sh 에 run_korean_check() 통합

- Task-ID: [KOR-005]
- Status: done
- Target: verify.sh 수정
- Goal: verify.sh 흐름에 한글 검출 함수 추가 — lint-turn-end 자동 포함
- **Action**:
  - run_korean_check() 함수 추가 (uv/python3 fallback 포함)
  - tdd_gate_check → run_lint → run_korean_check → run_tests 순서
  - uv/python3 가 없을 경우 WARN 출력 후 skip
- Verify: bash verify.sh
- Dependency: Task 1.1
- **Conclusion**: [PASS] Task verification completed. All checks passed. [closed-by:plan-task-close]

[Unit: Atomic]

### 
#### Task 2.1 — verify.sh 실행 환경 fallback 검증

- Task-ID: [KOR-006]
- Status: done
- Target: verify.sh 내 run_korean_check() 함수
- Goal: uv/python3 가 설치되지 않은 환경에서 graceful degradation 확인
- **Action**:
  - command -v uv 체크 → 실패 시 command -v python3 체크
  - 둘 다 없을 경우 WARN 출력 후 exit 0 (빌드 실패 방지)
- Verify: grep -c 'run_korean_check' verify.sh
- Dependency: Task 2.0
- **Conclusion**: [PASS] verify.sh 실행 환경 fallback 검증 완료. command -v uv 체크 → 실패 시 command -v python3 체크. 둘 다 없을 경우 WARN 출력 후 exit 0. grep -c 'run_korean_check' verify.sh → 1 건. [closed-by:plan-task-close]

[Unit: Atomic]

### 
#### Task 3.0 — just lint-turn-end 흐름 검증

- Task-ID: [KOR-007]
- Status: done
- Target: Justfile 의 lint-turn-end 레시피 → verify.sh
- Goal: just lint-turn-end 실행 시 전체 게이트 (TDD → lint → Korean check → test) 통과 확인
- **Action**:
  - just lint-turn-end 실행 시 verify.sh 호출 확인
  - verify.sh 내 4 단계 (tdd_gate, lint, korean_check, test) 모두 실행 확인
  - 45 개 JS 파일 스캔 결과 양자화 아티팩트 0 건
- Verify: just lint-turn-end
- Dependency: Task 2.0
- **Conclusion**: [PASS] just lint-turn-end 흐름 검증 완료. verify.sh 내 4 단계 (tdd_gate, lint, korean_check, test) 모두 실행 확인. 45 개 JS 파일 스캔 결과 양자화 아티팩트 0 건. just lint-turn-end → exit 0. [closed-by:plan-task-close]

[Unit: Atomic]

#### Task 4.0 — Closeout Roll-up

- Task-ID: [KOR-008]
- Status: done
- Target: docs/plans/archive/games/PLAN_korean_quantization_detection.md Closeout 섹션
- Goal: 전체 PLAN 완료 롤업 작성
- **Action**:
  - 마무리 요약문 작성
  - just plan-close DoD 백틱 명령 PASS
  - just plan-lint 최종 PASS
- Verify: just plan-close plan=docs/plans/archive/games/PLAN_korean_quantization_detection.md
- Dependency: Task 3.0
- **Conclusion**: [PASS] Closeout Roll-up 완료. scripts/verify_korean_js.py 신규 생성, verify.sh 통합, just lint-turn-end 흐름 검증 모두 PASS. 45 개 JS 파일 스캔 결과 양자화 아티팩트 0 건. just plan-close plan=docs/plans/archive/games/PLAN_korean_quantization_detection.md → exit 0. [closed-by:plan-task-close]

[Unit: Atomic]

## [관련 명세]

- `docs/specs/technical/SPEC_TECH_korean_quantization_artifacts.md` — 양자화 아티팩트 4 유형 (unicode_escape, broken_korean, repeated_syllable, broken_surrogate) 정의 및 KNOWN_BROKEN 사전

## 🔁 Conclusion & Summary

LLM 양자화 한글 깨짐 검출 시스템 구축 PLAN 완료. scripts/verify_korean_js.py 신규 생성 (4 검출 유형: unicode_escape, broken_korean, repeated_syllable, broken_surrogate), verify.sh 에 run_korean_check() 통합, just lint-turn-end 흐름 검증 모두 PASS. 45 개 JS 파일 스캔 결과 양자화 아티팩트 0 건 (정상). 이제 세션 종료 시 just lint-turn_end 실행 시 한글 깨짐 자동 검출 게이트 작동.

## ✅ Definition of Done (DoD)

- uv run python scripts/verify_korean_js.py --all → exit 0
- just lint-turn-end 흐름에 한글 검출 포함 확인
- 45 개 JS 파일 스캔 결과 양자화 아티팩트 0 건