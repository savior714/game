---
scope: registry
domain: core
---
<!-- Language: ko -->

# 워크플로 · 스킬 색인 (Workflow & Skill Index)

슬래시 워크플로·키워드→Read·프로세스 스킬·FE 스킬의 **카탈로그 SSOT**.

| 레지스트리 | 역할 |
| :--- | :--- |
| [PROJECT_SKILL_ROUTING.json](PROJECT_SKILL_ROUTING.json) | 기계 intent·path glob (`just route-smart`) |
| [SKILL_CATALOG.json](SKILL_CATALOG.json) | 스킬 발견·한줄 요약 (vendor는 `open-design-frontend` 경유만) |
| [CONTEXT_ROUTING.md](CONTEXT_ROUTING.md) | Tier·domain glob·route 매니페스트 |

---

## 워크플로 (슬래시 라우터)

| Workflow | Usage | 스킬 | 라우터 (부록) |
| :--- | :--- | :--- | :--- |
| `/plan` | 통합 심층 설계 및 태스크 분해 | — | [plan.md](../workflows/plan.md) |
| `/diagnose` | 문제 진단 및 재현 (6-phase SSOT) | [diagnose/SKILL.md](../skills/diagnose/SKILL.md) | [diagnose.md](../workflows/diagnose.md) |
| `/investigate` | 경량 조사·원인 파악 (diagnose보다 얕음) | [investigate/SKILL.md](../skills/investigate/SKILL.md) | [investigate.md](../workflows/investigate.md) |
| `/review` | 코드·PR 리뷰 (correctness·risk) | [review/SKILL.md](../skills/review/SKILL.md) | [review.md](../workflows/review.md) |
| `/discuss` | 무코드 방향 합의 (AskQuestion(`question` 병용) → DISCUSS → 핸드오프) | [discuss/SKILL.md](../skills/discuss/SKILL.md) | [discuss.md](../workflows/discuss.md) |
| `/sync` · `/spec-sync` | 수정 후 스펙·Plan Conclusion 역검증 | [sync/SKILL.md](../skills/sync/SKILL.md) | [sync.md](../workflows/sync.md) |
| `/assess` | 분석·교차 검토 후 assessment 스펙 | [assessment-driven-planning/SKILL.md](../skills/assessment-driven-planning/SKILL.md) | [assess.md](../workflows/assess.md) |
| `/discover` | 기술 부채 탐색 → Implement Blueprint | [discover/SKILL.md](../skills/discover/SKILL.md) | [discover.md](../workflows/discover.md) |
| `/refactor` | 무코드 리팩토링 3단 (진단→심화→검증) | [refactor/SKILL.md](../skills/refactor/SKILL.md) | [refactor.md](../workflows/refactor.md) |
| `/deep_research` | 규제·거시기술 외부 리서치 루프 | [deep-research/SKILL.md](../skills/deep-research/SKILL.md) | [deep_research.md](../workflows/deep_research.md) |
| `/improve-codebase-architecture` | Shallow→Deep 모듈·아키텍처 진단 | [improve-codebase-architecture/SKILL.md](../skills/improve-codebase-architecture/SKILL.md) | [improve-codebase-architecture.md](../workflows/improve-codebase-architecture.md) |
| `/linear` | Blueprint ↔ Linear 동기화 | — | [linear.md](../workflows/linear.md) |
| `/playwright` | UI 탐색·E2E 문제 발견 | — | [playwright.md](../workflows/playwright.md) |
| `/ai-log` | 인지 로그 기록 + CVS/SFT 배치 (`log_task.py` → `just ai-log`) | — | [cognitive_logging.md](../adaptive/cognitive_logging.md) · [ai-log.md](../workflows/ai-log.md) |
| `/ai-log-reflect` | Golden Log → core/workflow 승격 | — | [self_evolution.md](../adaptive/self_evolution.md) §3 · [ai-log-reflect.md](../workflows/ai-log-reflect.md) |
| `/rule-bundle` | `.agents/` → `artifacts/share/` 합본 (외부 LLM) | [rule-bundle/SKILL.md](../skills/rule-bundle/SKILL.md) | [rule-bundle.md](../workflows/rule-bundle.md) |
| `/go` | 세션 산출물 동기화·다음 에이전트 이관 | — | [go.md](../workflows/go.md) |
| `/git` | 커밋·슬라이스·푸시 (`just commit-gate`) | — | [git.md](../workflows/git.md) |
| `/archive` | 완료 Blueprint → archive 이관 | — | [archive.md](../workflows/archive.md) |
| `/audit` | EMR 심사 평가·프로젝트 진단 | — | [audit.md](../workflows/audit.md) |
| `/bootstrap` | bootstrap 템플릿 ↔ 저장소 지침 동기화 | — | [bootstrap.md](../workflows/bootstrap.md) |
| `/directory_verify` | README 디렉토리 맵 검증 | — | [directory_verify.md](../workflows/directory_verify.md) |
| `/biome_onefile` | 단일 파일 Biome 재현→수정→스테이징 | — | [biome_onefile.md](../workflows/biome_onefile.md) |
| `/context_gap_scan` | 맥락·문서 갭 스캔 | — | [context_gap_scan.md](../workflows/context_gap_scan.md) |

**스킬 열 `—`**: 동행 `SKILL.md` 없음 — 워크플로 pointer만 Read. E2E·Playwright 도메인 규칙은 [testing/playwright.md](../domains/testing/playwright.md).

---

## 키워드 → Read (수동 자기 규제)

슬래시·키워드는 **IDE가 자동 실행하지 않음**. frontmatter `trigger:`는 **색인 메타**일 뿐이다. 아래 표의 workflow/skill 경로를 **Read** 도구로 1회 읽은 뒤 실행한다 ([error_patterns §16.1](../core/error_patterns/detail/workflow.md) · Quick Pick: [principles.md](../core/principles.md) §1.1).

| 키워드 (예) | Read |
| :--- | :--- |
| plan, blueprint, 설계, roadmap | [workflows/plan.md](../workflows/plan.md) · `ROADMAP.md` lazy ([LOAD_ORDER.md](LOAD_ORDER.md) Phase 3) |
| review, 리뷰, code review | [workflows/review.md](../workflows/review.md) · [skills/review/SKILL.md](../skills/review/SKILL.md) |
| debug, 버그, diagnose, 재현 | [workflows/diagnose.md](../workflows/diagnose.md) · [skills/diagnose/SKILL.md](../skills/diagnose/SKILL.md) |
| investigate (경량), 원인 파악 | [workflows/investigate.md](../workflows/investigate.md) · [skills/investigate/SKILL.md](../skills/investigate/SKILL.md) |
| spec-sync, 스펙 drift | [skills/sync/SKILL.md](../skills/sync/SKILL.md) · [workflows/sync.md](../workflows/sync.md) |
| discuss, 논의, DISCUSS_ | [skills/discuss/SKILL.md](../skills/discuss/SKILL.md) · [workflows/discuss.md](../workflows/discuss.md) |
| assess, assessment, 진단 스펙 | [workflows/assess.md](../workflows/assess.md) · [skills/assessment-driven-planning/SKILL.md](../skills/assessment-driven-planning/SKILL.md) |
| discover, 기술 부채 | [workflows/discover.md](../workflows/discover.md) · [skills/discover/SKILL.md](../skills/discover/SKILL.md) |
| refactor (3단), 리팩토링 설계 | [workflows/refactor.md](../workflows/refactor.md) · [skills/refactor/SKILL.md](../skills/refactor/SKILL.md) |
| deep_research, 규제·외부 리서치 | [workflows/deep_research.md](../workflows/deep_research.md) · [skills/deep-research/SKILL.md](../skills/deep-research/SKILL.md) |
| shallow→deep, 모듈 깊이 | [workflows/improve-codebase-architecture.md](../workflows/improve-codebase-architecture.md) · [skills/improve-codebase-architecture/SKILL.md](../skills/improve-codebase-architecture/SKILL.md) |
| tdd, red-first, 테스트 작성 | [domains/testing/tdd.md](../domains/testing/tdd.md) · [code_quality_lifecycle.md](../core/code_quality_lifecycle.md) |
| test analysis, 테스트 분석·품질·보완 | [skills/test-analysis/SKILL.md](../skills/test-analysis/SKILL.md) |
| playwright, e2e | [workflows/playwright.md](../workflows/playwright.md) · [domains/testing/playwright.md](../domains/testing/playwright.md) |
| archive, blueprint 이관 | [workflows/archive.md](../workflows/archive.md) |
| linear, 이슈 동기화 | [workflows/linear.md](../workflows/linear.md) |
| git, commit-gate, 커밋 | [workflows/git.md](../workflows/git.md) |
| 완료, 마무리, /go | [reporting.md](../core/reporting.md) §1.0 · [workflows/go.md](../workflows/go.md) |
| 하드픽스 후 지식화 | [skills/knowledge-asset/SKILL.md](../skills/knowledge-asset/SKILL.md) |
| anti-pattern, wrong/correct | [ANTI_PATTERN_FORMAT.md](../../docs/agent-context/ANTI_PATTERN_FORMAT.md) · [error_patterns.md](../core/error_patterns.md) |

**Discuss MUST**: 무코드 · **`AskQuestion`/`question`(병용) 필수** · 마무리 assess 옵션 금지 — [discuss/SKILL.md](../skills/discuss/SKILL.md) §철칙 0.

**Diagnose vs investigate**: 테스트·런타임 **실패 재현·근본 원인** → diagnose. 로그·코드만으로 **가설 정리·범위 좁히기** → investigate.

**Test analysis 경계**: 실패 원인 추적 → diagnose · PR/변경분 리스크 → review · 신규 기능 전체 커버리지 설계 → `/plan` — [test-analysis/SKILL.md](../skills/test-analysis/SKILL.md) §When to Use.

**기계 intent** (`route-smart` 번들): [PROJECT_SKILL_ROUTING.json](PROJECT_SKILL_ROUTING.json) `intent_routes` — 키워드·스킬 쌍의 **중복 정의 금지**(수동 표에 없는 intent 전용 키워드: `compound`, `boolean prop`, `ui/ux` 등은 JSON SSOT).

---

## 프로세스 · 인지 스킬 (`.agents/skills`)

슬래시 트리거 또는 동등 요청 시 **아래 `SKILL.md`를 Read**한다. 저장소 전용 경로·CLI는 동행 **워크플로** 부록에만 있다.

| 트리거 / 상황 | SSOT 스킬 | 라우터 (부록) |
| :--- | :--- | :--- |
| `/diagnose` | [diagnose/SKILL.md](../skills/diagnose/SKILL.md) | [diagnose.md](../workflows/diagnose.md) |
| `/investigate` | [investigate/SKILL.md](../skills/investigate/SKILL.md) | [investigate.md](../workflows/investigate.md) |
| `/review` | [review/SKILL.md](../skills/review/SKILL.md) | [review.md](../workflows/review.md) |
| `/spec-sync` | [sync/SKILL.md](../skills/sync/SKILL.md) | [sync.md](../workflows/sync.md) |
| `/improve-codebase-architecture` | [improve-codebase-architecture/SKILL.md](../skills/improve-codebase-architecture/SKILL.md) | [improve-codebase-architecture.md](../workflows/improve-codebase-architecture.md) |
| `/discuss` | [discuss/SKILL.md](../skills/discuss/SKILL.md) (무코드 방향·범위 합의) | [discuss.md](../workflows/discuss.md) |
| `/refactor` | [refactor/SKILL.md](../skills/refactor/SKILL.md) (파편화된 리팩토링 스킬 통합 3단계 가이드) | [refactor.md](../workflows/refactor.md) |
| `/deep_research` | [deep-research/SKILL.md](../skills/deep-research/SKILL.md) | [deep_research.md](../workflows/deep_research.md) |
| `/discover` | [discover/SKILL.md](../skills/discover/SKILL.md) | [discover.md](../workflows/discover.md) |
| `/assess` | [assessment-driven-planning/SKILL.md](../skills/assessment-driven-planning/SKILL.md) | [assess.md](../workflows/assess.md) |
| `/rule-bundle` | [rule-bundle/SKILL.md](../skills/rule-bundle/SKILL.md) | [rule-bundle.md](../workflows/rule-bundle.md) |
| `/diagnose` 종료 시 | [knowledge-asset/SKILL.md](../skills/knowledge-asset/SKILL.md) | [diagnose.md](../workflows/diagnose.md) |
| 테스트 분석, test quality | [test-analysis/SKILL.md](../skills/test-analysis/SKILL.md) (스킬 단독 — Vitest·MSW·Playwright 스택) | — |

스킬 추가·이름 변경 시 [SKILL_CATALOG.json](SKILL_CATALOG.json) · [PROJECT_SKILL_ROUTING.json](PROJECT_SKILL_ROUTING.json) · 본 문서를 함께 갱신한다.

---

## 프론트엔드 디자인 · 성능 스킬 (`.agents/skills`)

프론트엔드 작업(React, UI/UX, CSS) 시 **상황에 따라** 아래 스킬 `SKILL.md`를 Read한다. Glob·cap: [CONTEXT_ROUTING.md](CONTEXT_ROUTING.md) · [PROJECT_SKILL_ROUTING.json](PROJECT_SKILL_ROUTING.json).

| 스킬명 | SSOT 경로 | 주요 용도 |
| :--- | :--- | :--- |
| `open-design-frontend` | [open-design-frontend/SKILL.md](../skills/open-design-frontend/SKILL.md) | 화면 단위 UI — 로컬 디자인·성능 스킬 + vendored open-design 오케스트레이션 |
| `vercel-react-best-practices` | [frontend/vercel-react-best-practices/SKILL.md](../skills/frontend/vercel-react-best-practices/SKILL.md) | 성능, 번들, 데이터 페칭 |
| `frontend-design` | [frontend/frontend-design/SKILL.md](../skills/frontend/frontend-design/SKILL.md) | 프리미엄 UI, 타이포, 모션 |
| `web-design-guidelines` | [frontend/web-design-guidelines/SKILL.md](../skills/frontend/web-design-guidelines/SKILL.md) | A11y, 폼, 안티패턴 점검 |
| `vercel-composition-patterns` | [frontend/vercel-composition-patterns/SKILL.md](../skills/frontend/vercel-composition-patterns/SKILL.md) | 컴포넌트 아키텍처, React 19 패턴 (`/refactor` 3단과 별개 — API·compound 설계) |
| `typescript-advanced-types` | [typescript/typescript-advanced-types/SKILL.md](../skills/typescript/typescript-advanced-types/SKILL.md) | 고급 타입 설계 |

문서 스타일·링크 검증은 [markdown.md](../domains/documentation/markdown.md)를 따른다.

---

**Last Updated**: 2026-06-11
