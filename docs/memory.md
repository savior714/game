# memory.md — Bootstrap DevEnv 작업 로그

---

## [누적 요약] 2026-03-10 ~ 2026-03-18 (아카이브)

| 날짜 | 주요 작업 |
| --- | --- |
| 2026-03-10 | PS5 BOM 파싱 오류 해결, 창 종료 원인 README 명시 |
| 2026-03-11 | 그룹 번호 재정렬(1~8), `Add-ToUserPath` 추가, Java/Android PATH 자동 등록 |
| 2026-03-14 | 환경 설정 외부화, `AI_GUIDELINES.md` 마스터 가이드라인 승격 |
| 2026-03-15 | Terminal Protocol 정밀화, Safe Raw IO 수칙 추가 |
| 2026-03-16 | `AI_GUIDELINES.md` 프로토콜 대규모 강화 — Loop Prevention, TPG, Git Guard 신설 |
| 2026-03-17 | TPG Hygiene 고도화, Deep-Dive Version 개정, 문서 위계 확립, `AI_COMMAND_PROTOCOL.md` 신규 생성 |
| 2026-03-17 | Tool-First Policy `[CRITICAL]` 격상, 3-IDE 환경 호환성(Antigravity/Claude Code/Cursor) 확보 |
| 2026-03-18 | TypeScript 타입 검증 전략 + 바이브 코딩 프로토콜 전체 설계 및 3-IDE 반영 (본 세션) |

**안정 상태**: 문서 위계 8단계 확립 / 3-IDE 타입 검증 전략 SSOT 완성 / Vibe Coding Protocol 수립

---

## [2026-03-18] TypeScript 타입 검증 + 바이브 코딩 전략 3-IDE 통합

### 신규 생성 파일

| 파일 | 역할 |
| --- | --- |
| `docs/TS_TYPE_VALIDATION.md` | TypeScript 타입 검증 전략 SSOT (3-IDE 통합, Error-Only Context, Schema-First) |
| `docs/TS_ADVANCED_PATTERNS.md` | DDD 타입 분리 / Symbol Reference / Type Flatten 고급 패턴 |
| `docs/VIBE_CODING_PROTOCOL.md` | Validate-and-Prune / L1/L2/L3 슬라이싱 / Agent-to-Agent Protocol |
| `.cursorrules` | Cursor AI 전용 규칙 파일 (TS Protocol §2, Vibe Coding §3 포함) |
| `.vscode/tasks.json` | TypeScript Type Check / Errors Only / Watch / Validate 태스크 |
| `scripts/type-check-slice.ps1` | tsc Error-Only Context 추출 자동화 (에러 라인 ±5줄 슬라이싱) |
| `scripts/types-extractor.ts` | ts-morph 기반 타입 정의만 추출 (Barrel Export 지원, Flatten 감지) |

### 수정된 파일

| 파일 | 주요 변경 |
| --- | --- |
| `CLAUDE.md` | 문서 위계 8단계 확장, 상황별 참조 규칙(TS/Vibe Coding), 자가 검증 2항목 추가 |
| `AI_GUIDELINES.md` | §5 TypeScript Protocol 전면 강화(DDD/Symbol Ref/L1L2L3/Validate-and-Prune), 중복 테이블 제거, §6 번호 충돌 수정, `{{TYPE_CHECK_COMMAND}}` 대체 |
| `.antigravityrules` | §6 TS Protocol 확장(DDD/Symbol Ref/Flatten), §7 Vibe Coding + Agent-to-Agent Protocol 신설 |
| `.vscode/settings.json` | TypeScript Language Service + 컨텍스트 오염 방지 경로 추가 |
| `docs/AI_COMMAND_PROTOCOL.md` | §8 TypeScript Error-Only 슬라이싱 패턴 신설 |
| `~/.claude/commands/go.md` | 문서 위계 +3, §3 타입 체크 3단계 루프, §2 TS/Vibe Coding SSOT 체크, HANDOFF 템플릿 +2항목 |
| `~/.claude/commands/plan.md` | §4 TypeScript 타입 수정 시 DDD 원칙 명시, Task 3 검증 명령 현행화, DoD §3 Error-Only 패턴 반영 |

### 핵심 아키텍처 결정

- **LLM 역할 분리 원칙 확립**: `tsc` = 검증, LLM = 수정. 컴파일러가 할 수 있는 일을 토큰으로 대체하지 않는다.
- **3단계 워크플로우**: `npm run type-check` → `type-check-slice.ps1` (Error-Only) → LLM Fix → 재검증
- **`@Codebase` 전면 금지**: `@Symbols` + `src/domain/index.ts` Barrel Export가 유일한 타입 컨텍스트 진입점
- **300라인 룰 준수**: `TS_TYPE_VALIDATION.md` 337라인 도달 → `TS_ADVANCED_PATTERNS.md`로 즉시 분리

### 진행 상황

- [x] 3-IDE 통합 TypeScript 타입 검증 전략 설계 및 반영
- [x] 바이브 코딩 Validate-and-Prune 프로토콜 설계 및 반영
- [x] 글로벌 커맨드(`/go`, `/plan`) 신규 전략 반영
- [x] 글로벌 룰(`CLAUDE.md`, `AI_GUIDELINES.md`) 정합성 동기화
- [x] memory.md 200라인 초과 → 아카이빙 및 50라인 이내 요약 완료

---

## [2026-03-18] 타 프로젝트 이식 프로세스 설계 (세션 2)

### 핵심 결정

- **이식 4단계 프로세스 확립**: Phase 1(범용 복사) → Phase 2(커스터마이징) → Phase 3(신규 초기화) → Phase 4(의존성)
- **복사 대상 분류**: 범용(수정 없이 복사) / 커스터마이징 필요 / 프로젝트별 신규 생성 3종류로 구분
- **1순위 대상 프로젝트**: `eco_pediatrics` 또는 `cheonggu` (TypeScript 비중 높은 쪽 우선)

### 진행 상황

- [x] 타 프로젝트 이식 체크리스트 설계 완료
- [ ] 실제 프로젝트(`eco_pediatrics` / `cheonggu`)에 이식 적용 및 검증
