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
2. 에러 1건 선택
3. 파일 read
4. exact snippet 확보
5. minimal **부분 수정** 또는 **전체/신규 쓰기** (런타임별: [runtime_edit_tools.md §1](runtime_edit_tools.md))
6. formatter / lint 재실행
7. 변경이 있으면 재read

**편집 도구 실패 시**: [runtime_edit_tools.md §2](runtime_edit_tools.md) · Cursor [routing.md](routing.md) §1.4 · §1.2.

### 2.2 Additional Rules
- regex보다 AST 기반 수정을 우선한다.
- formatter에 의해 context가 쉽게 바뀔 수 있으므로 patch 이후 재확인한다.
- **구현 중**에는 요청 범위 밖 **기능·리팩터**를 넣지 않는다. (드라이브바이 리팩터 금지)
- **세션 종료 게이트**에서는 §2.5를 따른다 — “태스크와 무관”한 lint/type 오류도 **최소 패치로 0**이 되게 하거나, 미해결 사유를 보고한다.

### 2.3 Turn-End Lint / Type Clean

저장소 파일을 **생성·수정·삭제**한 뒤 **완료·마무리** 응답 직전(`just sync --check` / Phase 2 **이전**)에 실행:

```bash
just lint-turn-end
```

| 항목 | 규칙 |
|------|------|
| 범위 | 명령 출력의 **전체** 실패를 확인한다. 이번 세션에서 건드리지 않은 파일·BE/FE 교차 오류도 포함해 가시화한다. |
| 수정 | §2.1 Safe Edit Loop — **내가 변경한 파일의 오류만** 오류당 최소 패치로 해결한다. **이번 세션에서 건드리지 않은 파일의 기존 무관 오류는 'Surgical Changes(최소 변경)' 원칙에 따라 수정하지 않는다.** 드라이브바이 기능·리팩터 금지. |
| 완료 선언 | 본인이 변경한 파일의 오류는 0이어야 "완료". 내 작업과 무관하게 실패한 타 파일의 오류는 `파일:줄 — 요약` 형태로 블로커/경고 항목으로 보고서에 명시하고 패스한다. |
| 예외 | 사용자가 lint/type 제외를 **명시**한 경우. `just ci`/전체 테스트는 L2/L3·별도 요청 시에만. |

**진행 중 자가진단**: `lint-fe`(FE만) / `lint-be`(BE만) — 구현 중 "내 레이어는 깨끗한가?" 확인용. **완료 선언 대체 불가.**

**구현 중 vs 종료 직전:** §2.2는 구현 중 범위를 좁힌다. §2.5는 종료 게이트로 본인 작업 범위의 lint/type을 0에 맞추되, 타 파일의 기존 오류는 보고를 통해 책임을 인계한다. 둘은 'Surgical Changes' 원칙 아래 완벽히 조화된다.

보고 절차: [reporting.md](reporting.md) §1.5

### 2.4 Advanced Testing & Performance Patterns
- **Async DB Testing**: `async_session_factory()`와 같은 비동기 세션 생성기를 모킹할 때는 `MockAsyncSessionFactory` (클래스 기반 `__call__` + `__aenter__/__aexit__`) 패턴을 사용하여 실제 DB 컨텍스트와 유사한 통합 테스트 환경을 구축한다.
- **Index Scan Integrity**: PostgreSQL 등에서 `ILIKE '%keyword%'` 패턴은 B-tree 인덱스 스캔을 타지 않을 수 있음을 명시한다. 대량 데이터 조회 시 `code=`(Index Scan)와 부분 문자열 검색(Seq Scan/Bitmap Scan)을 명확히 분리하여 설계한다.

### 2.5 Ephemeral File Management
- **Cleanup**: `verify-*-summary.json`과 같은 게이트 실행 결과 파일은 매번 덮어씌워지는 일시적인 파일이므로, 레포지토리에 커밋하지 않거나 작업 종료 후 명시적으로 삭제한다. (Grep 노이즈 제거)

### 2.6 Zero-Leak / Security Verification
- **시크릿 누출 검사**: 작업 완료 및 완료 선언 전, 응답 메시지나 도구 출력(터미널 캡처, 에러 로그 등)에 API 키, 토큰, `.env` 원문 등 비밀값이 한 글자라도 노출되지 않았는지 반드시 자체 점검한다.
