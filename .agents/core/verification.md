---
scope:
- '*'
always_apply: false
priority: 1
domain: core
verify_with:
- scripts/verify/report.sh
---
<!-- Language: ko -->

# Verification & Patch Integrity Rules

본 문서는 코드 수정 전후의 검증 매트릭스와 패치 무결성을 유지하기 위한 세부 규칙을 정의합니다.

---

## 📋 AGENTS.md 헌법 적용 요약

| 원칙 | 이 문서에서의 구현 |
|------|-------------------|
| **1. 규칙 위계** | priority: 1 — `PROJECT_RULES.md` 다음, 검증 수준·게이트 normative SSOT |
| **2. 사고→단순→표적** | §2.2 구현 중 요청 범위 밖 기능·리팩터 금지 (드라이브바이 리팩터 금지) |
| **3. 편집 게이트 4단계** | §2.1 Safe Edit Loop — lint → 에러 선택 → read → snippet 확보 → minimal edit |
| **4. 다중 에이전트** | 이 문서의 대상 — Phase 3 검증에서 `just lint`/`pytest` 결과 전담 검증 |
| **5. 정적 진단 종료 게이트** | §2.3 Turn-End Lint — `just lint-turn-end` 결과를 failure domain별로 닫음 |
| **6. 검증·한글·고유성** | §1 Verification Matrix — Docs/L1/L2/L3scope별 필수 검증 명령어 정의, §2.6 Zero-Leak |

---

## 1. Verification Matrix

작업 범위에 맞는 검증을 통과한 후 완료를 선언해야 합니다.

| Scope | Required |
|---|---|
| Docs | link/path 정합성 |
| L1 small | `just lint` (= ruff · ty · **be/fe-quality-gates** · biome · sync) |
| L2 feature | L1 + `just tdd-fast` |
| L3 structural | L2 + `just ci` (= verify · coupling · **fe-quality-gates** · coverage) |
| Frontend UI | `pnpm run lint` + `pnpm run typecheck:strict` (`apps/renderer` 기준) |
| Grid/layout | `just grid-verify` |
| Directory | `/directory_verify` |

시점별 품질 체크리스트(설계·구현·리뷰·테스트·강제): [code_quality_lifecycle.md](code_quality_lifecycle.md).

**산출물:**
- `artifacts/verify/verify-last-result.json`
- `docs/reports/REPORT_verify_report.md`

---

## 2. Patch Integrity Rules

### 2.1 Safe Edit Loop
1. lint/type 실행
2. 에러 1건 또는 동일 원인의 최소 묶음 선택
3. 파일 read
4. exact snippet 확보
5. minimal **부분 수정** 또는 **전체/신규 쓰기** (런타임별: [runtime_edit_tools.md §1](runtime_edit_tools.md))
6. 같은 formatter / lint / type 명령 재실행
7. 해당 failure domain 소멸 확인
8. 변경이 있으면 재read
9. 다음 별도 failure domain으로 이동

**편집 도구 실패 시**: [runtime_edit_tools.md §2](runtime_edit_tools.md) · Cursor [routing.md](routing.md) §1.4 · §1.2.

### 2.2 Additional Rules
- regex보다 AST 기반 수정을 우선한다.
- formatter에 의해 context가 쉽게 바뀔 수 있으므로 patch 이후 재확인한다.
- **구현 중**에는 요청 범위 밖 제품 기능·리팩터를 넣지 않는다. 드라이브바이 제품 변경은 금지한다.
- LSP·typecheck·lint 오류는 제품 scope와 별개인 저장소 품질 failure다. 현재 변경과 직접 영향 범위를 먼저 0으로 만든 뒤, 추가 오류를 failure domain별로 순차 해결한다.
- 여러 정적 오류의 원인이 다르면 한 패치에 묶지 않는다. 한 failure domain마다 재현 조건과 판정 명령을 고정하고 독립 검증한다.
- 잘못된 workspace root, SDK/interpreter, 누락된 dependency, stale cache/index, generated/vendor 오분석 가능성을 production code 변경보다 먼저 확인한다.
- broad ignore, `type: ignore`, `noqa`, ESLint disable, 검사 대상 축소, baseline·snapshot 갱신으로 PASS를 만들지 않는다.

### 2.3 Turn-End Lint / Type Clean

저장소 파일을 **생성·수정·삭제**한 뒤 **완료·마무리** 응답 직전에 안정적인 source worktree root에서 실행한다.

```bash
just lint-turn-end
```

| 항목 | 규칙 |
|------|------|
| workspace | `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>` 또는 같은 상위 개발 디렉터리의 안정적인 worktree를 사용한다. `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` source worktree나 main checkout·symlink alias 혼합은 금지한다. |
| baseline | 변경 전에 관련 LSP·typecheck·lint baseline을 기록해 새 오류와 기존 오류를 구분한다. |
| 현재 책임 | 현재 변경으로 새로 생긴 오류와 수정 파일·직접 영향 모듈의 오류를 먼저 최소 패치로 0으로 만든다. |
| 추가 오류 | 이번 세션에서 처음 수정하지 않았던 파일의 기존 오류도 단순 경고로 넘기지 않는다. 현재 failure domain을 같은 명령으로 독립 검증한 뒤 다음 정적 failure domain 하나를 선택해 순차 해결한다. |
| 환경 원인 | workspace root·SDK/interpreter·dependency·stale cache/index·generated/vendor 오분석이면 환경·설정을 수정하고 동일 진단을 재실행한다. |
| 완료 선언 | 명령에 오류가 남은 상태에서 “pre-existing”, “unrelated”, “out of scope”라고 보고하고 PASS하지 않는다. 안전하게 해결할 수 없으면 정확한 진단·재현 명령·차단 원인을 포함해 `BLOCKED`로 종료한다. |
| 예외 | 사용자가 해당 정적 검사를 명시적으로 제외한 경우에만 그 criterion을 실행하지 않을 수 있다. 실행하지 않은 criterion을 PASS로 표시하지 않는다. `just ci`/전체 테스트는 L2/L3 또는 별도 요청 시에만 실행한다. |

**진행 중 자가진단**: `lint-fe`(FE만) / `lint-be`(BE만)는 구현 중 확인용이며 완료 선언을 대체하지 않는다.

**구현 범위와 정적 오류 책임:** 제품 기능·리팩터 scope는 좁게 유지한다. 정적 오류는 서로 다른 원인을 한꺼번에 섞지 않고 하나씩 닫는다. 이는 드라이브바이 제품 변경이 아니라 저장소 정적 품질 회복 절차다.

보고 절차: [reporting.md](reporting.md) §1.5

### 2.4 Advanced Testing & Performance Patterns
- **Async DB Testing**: `async_session_factory()`와 같은 비동기 세션 생성기를 모킹할 때는 `MockAsyncSessionFactory` (클래스 기반 `__call__` + `__aenter__/__aexit__`) 패턴을 사용하여 실제 DB 컨텍스트와 유사한 통합 테스트 환경을 구축한다.
- **Index Scan Integrity**: PostgreSQL 등에서 `ILIKE '%keyword%'` 패턴은 B-tree 인덱스 스캔을 타지 않을 수 있음을 명시한다. 대량 데이터 조회 시 `code=`(Index Scan)와 부분 문자열 검색(Seq Scan/Bitmap Scan)을 명확히 분리하여 설계한다.

### 2.5 Ephemeral File Management
- `verify-*-summary.json`과 같은 게이트 실행 결과 파일은 매번 덮어쓰는 일시 파일이므로 레포지토리에 커밋하지 않거나 작업 종료 후 명시적으로 삭제한다.
- prompt transport, patch/diff, 다운로드·압축 해제, 테스트 fixture와 같은 비소스 artifact는 OS temp를 사용할 수 있다.
- source checkout/worktree와 LSP·프로젝트 실행 root는 OS temp에 두지 않는다.

### 2.6 Zero-Leak / Security Verification
- **시크릿 누출 검사**: 작업 완료 및 완료 선언 전, 응답 메시지나 도구 출력(터미널 캡처, 에러 로그 등)에 API 키, 토큰, `.env` 원문 등 비밀값이 한 글자라도 노출되지 않았는지 반드시 자체 점검한다.
