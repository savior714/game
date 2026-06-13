---
scope:
- '*'
always_apply: false
priority: 1
domain: core
---
<!-- Language: ko -->
# Reporting Protocol
본 문서는 에이전트의 보고 원칙과 형식을 규정합니다. 전 구간 간결 보고를 유지하여 토큰 효율을 극대화합니다.
---
## 1. Reporting Principles
전 구간 간결 보고를 유지합니다. 중간 보고와 세션 종료 보고는 동일한 원칙을 따릅니다.

### 1.0 세션 종료 체크리스트 (저장소 수정 시)
**완료·마무리·이관** 응답 직전 순서 (에이전트 공통 SSOT):
| 순서 | 작업 내용 | 필수 명령 / 검증 절차 | 관련 규정 |
| :--- | :--- | :--- | :--- |
| 1 | **문서 헤더 및 규격 검증** | `just docs-ssot-headers` | [AGENTS.md](../../AGENTS.md) §4.3 / §4.5 |
| 2 | **Linear 원격 동기화** | `just linear-sync` | [AGENTS.md](../../AGENTS.md) §4.3 |
| 3 | **태스크 종료 및 플랜 닫기** | `just plan-close` | [AGENTS.md](../../AGENTS.md) §2.2 / §4.3 |
| 4 | **세션 최종 린트 및 빌드 검증** | `just lint-turn-end` | §1.5 / [verification.md](verification.md) §2.5 |
| 5 | **다음 작업 제안 (필요 시)** | `just plans-steer` (스냅샷 갱신 제안) | §1.0 아래 설명 / [ROADMAP.md](../../docs/plans/ROADMAP.md) |

Blueprint Task **3개 이상 연속 done**·plan-close·archive 직후에는 `just plans-steer`로 README Recommended next 스냅샷 갱신을 1줄 제안한다. 방향 SSOT는 [`ROADMAP.md`](../../docs/plans/ROADMAP.md).
`/go` 이관·`/spec-sync` 직전에도 동일. 상세: [execution.md](execution.md) §3.5 · [go.md](../workflows/go.md) §1.

### 1.1 기본 보고 (Default)
- 3~5줄 이내로 작성합니다.
- 한 줄 요약을 포함합니다.
- 필요 시 변경 파일 목록과 검증 결과를 한 줄로 요약합니다.
- 잔여 이슈가 있으면 한 줄 추가합니다.
- **Workaround Accountability**: 작업을 한 번에 끝내지 못하고 우회책(Workaround)을 사용했다면 발생 문제, 근본 원인(추정), 향후 해결 방안을 반드시 보고하고 사용자에게 결정(`AskQuestion`/`question` 병용)을 유도합니다.

### 1.2 상세 보고 (Detailed)
다음과 같은 경우에만 상세 보고를 수행합니다.
- 검증 실패 시
- 블로커(Blocker) 존재 시
- 사용자가 명시적으로 상세 보고를 요청했을 때

### 1.3 금지 사항 (Prohibited)
- 장문의 템플릿 보고
- 영문 전용(English-only) 리포트
- `Final Completion Report`와 같은 거창한 헤더 사용
- 증거(Evidence) 없는 "완료" 선언
- 사용자에게 폐기된 적응형 지침 명령(예: `just update-guidelines`)을 직접 실행하라고 요구하는 것
- 태스크 완료(`Conclusion`) 필드에 플레이스홀더 문자열(`[완료 시 기입]`, `[판정 — ...]` 등)을 남겨두는 행위 (상세: [AGENTS.md](../../AGENTS.md) §4.4)

### 1.4 제안의 책임 (Recommendation Accountability)
- 아키텍처, 스택, 워크플로, 보안 정책 변경을 제안할 때는 반드시 아래 3개 요소를 포함해야 합니다 (단순 확인이나 사실 설명 시에는 면제).
  1. **Rationale (근거)**: 제안의 배경과 합리적 근거
  2. **Risk (위험)**: 예상되는 잠재적 문제점과 우회/방지 대책
  3. **Evidence URL (출처)**: 신뢰할 수 있는 공식 문서나 RFC, 사내 스펙 문서 등의 URL
- 추측성 제안은 절대 하지 않습니다.
- 상세 규정: [PROJECT_RULES.md](../../PROJECT_RULES.md) §3

### 1.5 세션 종료 검증 (Lint / Type) — **필수**
저장소 파일을 **생성·수정·삭제**한 뒤 **작업 완료·마무리** 응답 직전, **완료 보고(§1.1/§1.2)보다 먼저**:
1. [verification.md](verification.md) §2.5 — `just lint-turn-end`
2. 실패가 있으면 **내가 변경한 파일의 오류만** 최소 패치로 0으로 만든다. 이번 세션에서 건드리지 않은 파일의 기존 오류는 보고에 블로커/경고로 명시한다. PASS 전 "완료" 선언 금지.
3. 보고에 검증 한 줄 포함 (예: `just lint-turn-end` ✅).
4. 이번 세션에서 I등급(500줄 초과) 파일을 수정했다면, 완료 보고에 분할 Blueprint 작성 여부(`plan-lint` 결과 포함)를 한 줄로 기록한다.
5. 플랜 태스크를 닫을 때 `Conclusion` 필드에 플레이스홀더를 남겨두지 말고, 최소 25자 이상으로 실제 검증된 결과(파일명, 테스트 성공 개수, 검증 명령 결과 등)를 기록합니다. (상세: [AGENTS.md](../../AGENTS.md) §4.4)
> SSOT 상세: verification §2.5
**진행 중 자가진단**: `lint-fe`(FE만) / `lint-be`(BE만) — 구현 중 확인용. 완료 선언 대체 불가.

### 1.6 사용자 응답 — 채팅은 행동 지시, 문서는 LLM용
문서 양식 SSOT: [markdown.md](../domains/documentation/markdown.md) 「Documentation Audience」. **기본**: 내부 Markdown은 LLM-first; `README.md` 등 사람·외부 노출 문서만 예외.

#### 1.6.0 일반 대화 톤 — 비개발자 친화 (기본)
**채팅 전반**(설명·진행 보고·질문·완료 요약)은 **조금** 업무·임상 언어를 기본으로 한다. 정확성은 유지하고, 개발 문서처럼 읽히지 않게 한다.
| 우선 | 채팅에서 |
|------|----------|
| 1 | **무엇이 달라졌는지** — 화면·업무·사용자 관점 한 줄 |
| 2 | **다음에 할 일** — 번호 3~7개, 명령형 짧은 문장 |
| 3 | **통과/실패** — 눈으로 볼 수 있는 기준 |
| 4 | **개발 참고** — 파일·함수·식별자는 맨 아래에만 (사용자가 기술을 물었을 때만 위로 올림) |
**말하기**:
- `hook`, `refactor`, `persist`, `endpoint` 등은 **쓰지 않거나** → 「저장」, 「화면」, 「서버에 보내기」로 풀어 쓴다.
- 제품 호칭·역할은 MSOT(`README.md`, Linear 자연어 구역)를 따른다 — 예: **진료실**, **원무**, **staff**.
- **모호함 해소의 기본값(Interactive Refine)**: 모호한 요구사항, 태스크 분할, 의사결정 등 질문이 필요한 모든 상황에서 서술형 질문("어떻게 할까요?")을 원천 금지합니다. 대신 [principles.md](principles.md) §1.1.1 **Interactive Refine & Quick Pick**에 따라 `AskQuestion`/`question` 도구(병용)를 활용해 2~4개의 구체적 선택지와 **(권장)** 태그를 제시하는 방식을 기본 소통 방식으로 사용합니다.
- **세션 완료 보고 시 추가 피드백/의사결정 요구 최우선**: 세션 완료 보고나 다음 세션을 위한 추가 피드백·결정이 필요할 경우에도, 서술형 질문 대신 **Quick Pick 스타일 의사결정 메뉴(AskQuestion/`question` 병용)**를 구성하여 소통하는 것을 최우선으로 한다.
**피하기**: 열린 서술형 질문 던지기, 식별자만 나열, 긴 표·코드 블록으로 답 종료, 「명세 §n 참고」만 던지기.
**예외 (개발 톤 허용)**: 사용자가 파일·에러·PR·테스트를 직접 언급했을 때, 디버깅·리뷰를 요청했을 때.
**강도**: 과한 유치함·장황한 비유 금지. 사용자가 「기술적으로」라고 하면 §1.6.1 QA 형식과 병행해도 된다.
질문 뱅크(Discuss): [plain-language-questions.md](../skills/discuss/references/plain-language-questions.md)
**저장소 문서**(`docs/reports/qa/`, `docs/specs/`, Blueprint)와 **채팅 응답**은 역할을 나눈다.
| 대상 | 목적 | 형식 |
|------|------|------|
| **Blueprint `## 📋 업무 요약 (협업용)`** | 원장·원무·기획이 **맥락만** 읽음 | `### 개요` · staff·경영 변화 · 끝났을 때 확인 — **경로·백틱·CLI 없음**. 뼈대: [TEMPLATE_blueprint_collaboration_summary.md](../../docs/templates/TEMPLATE_blueprint_collaboration_summary.md) · [plan.md](../workflows/plan.md) |
| **문서(기술 절)** | 에이전트·회귀·명세 동기화 | ID·표·교차 링크·합격 조건 (LLM이 파싱하기 쉬움) |
| **채팅** | 사용자가 **지금 당장** 할 일 | 명령형 짧은 문장·번호 목록·「통과 / 실패면」 한 줄 |

#### 1.6.1 QA·확인 답변 (기본)

**적용 순서**: Task `Verify`·QA·spec·Blueprint에 검증 절차 SSOT가 있는지 **먼저** 판단한다. 있으면 아래 **예외**를 따르고, 없거나 사용자가 채팅만으로 절차를 요청했을 때만 기본 3~7스텝 규칙을 쓴다.

**예외 — 검증 SSOT가 이미 문서에 있을 때** (활성 Blueprint `PLAN_*.md` Task·`Verify`, `docs/reports/qa/`, specs·Blueprint QA 절 등에 **눈으로 확인하는 절차·통과 기준**이 이미 정의됨):
- 채팅에 3~7스텝을 **억지로 풀어 쓰지 않아도 된다** — 해당 문서·Task가 SSOT.
- 채팅은 **무엇을 확인하는지 한 줄** + **문서·Task 링크 1개** + **통과/실패 한 줄** (§1.1 간결 보고)로 충분하다.
- 여전히 금지: 링크만 던지고 맥락·통과 기준을 생략하는 것, 식별자만 나열.

**채팅에서 QA·확인을 물을 때** (위 예외에 해당하지 않거나, 사용자가 채팅만으로 절차를 요청했을 때):
1. **문서 링크만으로 끝내지 않는다** — 맥락·통과 기준이 없이 `docs/reports/qa/...` 등만 제시하지 않음.
2. **본문에 그대로 적는다** — 예: 「진료실 → 편집 켜기 → 카드 하나를 빈 칸에 놓기 → 겹치면 실패」
3. **통과 기준은 눈으로 본다** — “겹치지 않음”, “놓은 칸과 비슷함”, “새로고침 후 그대로”
4. **한 번에 3~7스텝** (예외 적용 시 §1.1·위 예외 블록 준수) — 표·GEO-ID·파일 경로는 **맨 아래 「개발 참고」**에만 (사용자가 안 물었으면 생략 가능)
5. **질문이 좁으면 짧게** — “뭘 확인하면 돼?” → 확인 3줄 + 통과/실패만 (예외 적용 시 한 줄 맥락 + 링크 + 통과/실패)
**피하기 (채팅)**:
- QA-GRID-01, GEO-PAD-01, persist, compact 등 **식별자만** 나열
- 긴 표를 채팅에 복붙
- “명세 §8.4 참고”로 답변 종료
**문서 작성 시**: `docs/reports/qa/`·`docs/specs/`에는 **LLM이 파싱할 표·ID·교차 링크만** 둔다. 사람용 요약·「5분 확인」절을 문서에 **중복 작성하지 않음** (컨텍스트 낭비). 에이전트는 해당 문서를 Read한 뒤, §1.6.1 **예외**에 해당하면 링크·한 줄 맥락·통과 기준으로 충분하며, 해당하지 않으면 **세션 채팅에서** 명령형으로 요약한다.
**유지**: 사실 정확성, 커밋·PR·명세 본문은 기존 markdown 규칙.
