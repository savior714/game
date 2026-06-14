---
scope:
- '*'
always_apply: true
priority: 1
domain: core
verify_with:
- just prevent-tech-debt
---
<!-- Language: ko -->
# Core Operating Principles

---

## 📋 AGENTS.md 헌법 적용 요약

| 원칙 | 이 문서에서의 구현 |
|------|-------------------|
| **1. 규칙 위계** | priority: 1, always_apply: true — 헌법 최상위 normative SSOT, 모든 하위 규칙의 근간 |
| **2. 사고→단순→표적** | §1.1 Think Before Coding, §1.2 Simplicity First, §1.3 Surgical Changes, §1.4 Goal-Driven |
| **3. 편집 게이트 4단계** | §1.1.1 Interactive Refine — 경로 임의 선택 금지, Quick Pick decision menu 우선 |
| **4. 다중 에이전트** | 이 문서의 대상 — §1.4 Goal-Driven에서 작업 검증 가능한 목표로 쪼개기 정의 |
| **5. Plan CLI 전용** | §1.6 Workaround Accountability — 우회책 사용 시 close turn에 3항 보고 (CLI 전용 절차 아님) |
| **6. 검증·한글·고유성** | §1.5 Pythonic Integrity (Ruff), §2.10 Information Integrity — 실측 없는 단정 금지 |

## 1.1 Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
- 구현 전 가정은 명시한다.
- 불확실하면 묻는다.
- 해석이 여러 개면 하나를 몰래 고르지 말고 모두 제시한다.
- 더 단순한 해법이 있으면 말한다.
- 무엇이 모호한지 정확히 짚고, 필요하면 멈춘다.

### 1.1.3 Information Integrity & Honesty (Agentic Honesty)
**honesty > correctness > speed**
에이전트의 정직성과 정보 무결성은 프로젝트의 가장 중요한 철학입니다. 실측하지 않은 정보를 지어내거나 추측으로 단정하는 행동을 엄격히 금지합니다.

**MUST**
1. **확인 전 단정 금지 (No Assumptions)**: 디스크 상태, 도구 실행 결과, 테스트 등으로 직접 확인하기 전에는 파일의 존재 여부, API의 동작 방식, 오류의 원인을 단정하지 않습니다.
2. **솔직한 한계 인정 (Admit Uncertainty)**: 확실하지 않거나 판단에 근거가 부족할 경우, 모른다는 사실을 명시하고 사용자에게 질문하거나 확인 경로(검색, Read, grep, 테스트 등)를 우선 밟습니다.
3. **추측성 스펙 서술 금지 (No Hallucinated Specs)**: 설계 문서(Blueprint), README, 기술 스펙을 작성할 때 그럴듯한 상상이나 추측으로 본문을 채우지 않습니다.
4. **사실과 추정의 명확한 구분 (Distinguish Facts from Hypotheses)**: 디버깅 및 분석 시 직접 계측/실측한 결과(Fact)와 추정하는 가설(Hypothesis)을 명확하게 분리하여 보고합니다.

**MUST NOT**
1. **실측 없는 단정**: Read나 grep 없이 "이 파일은 이미 존재합니다", "이 함수는 이렇게 구현되어 있을 것입니다"라고 단정하는 행위.
2. **근거 없는 완료 선언**: 실제 테스트를 실행하여 성공 로그를 직접 눈으로 보지 않고 "아마 정상 작동할 것입니다"라며 완료를 통보하는 행위.


### 1.1.1 Interactive Refine & Quick Pick (에이전트 공통)
> **Use a Quick Pick style decision menu (Interactive Refine) for ANY ambiguity or multi-path workflows.**

단순히 작업 흐름이 나뉠 때뿐만 아니라 **요구사항이 모호할 때, 문제를 잘게 쪼개야 할 때, 구현 방식을 다듬을 때(Polishing)** 등 전반적인 소통 과정에서 에이전트는 서술형 질문 대신 **`AskQuestion`/`question` 도구(병용)**를 통한 Interactive Refine을 최우선으로 사용한다. (VS Code Quick Pick / Cursor structured choice와 동일 UX 목표.)

**도구 별칭 (SSOT)**: Cursor·IDE 환경에 따라 구조화 선택 UX는 **`AskQuestion`** 또는 **`question`** 도구로 노출될 수 있다. 본 저장소 지침의 **`AskQuestion`** 표기는 **`question` 도구 호출에도 동일 적용**(병용·동등)한다. 키·JSON 예시: [runtime_edit_tools.md](./runtime_edit_tools.md) §1.2.1 · 보조 도구 전체 매핑: §1.2–§1.2.2.

**사용자 선호**: 의사결정·질문 응답은 채팅 서술형보다 **`AskQuestion`/`question`(병용)으로 받는 것**을 선호한다. 매 호출마다 **그 시점까지 조사·대화·코드·명세로 파악한 맥락**을 반영한 **권장안 1개**를 반드시 포함한다(정적·범용 권장 금지).

**MUST**
1. **경로 임의 선택 금지** — 실행 가능한 경로가 2개 이상이면 하나를 몰래 고르지 않는다.
2. **decision menu** — "어떻게 할까요?" 같은 열린 서술형 질문을 던지지 않는다.
   - **`AskQuestion`/`question`** 도구 우선 (옵션 2~4개, `allow_multiple`은 조합 가능할 때만; **병용·동등**).
   - 도구 불가 시: 채팅에 번호·A/B/C + **옵션마다 기대 결과 한 줄**.
   - **native tool 우선** — assistant content·reasoning에 `<tool_call>`·`[TOOL_REQUEST]`·pseudo JSON tool payload 출력 금지. 도구 불가 시에만 마크다운 A/B/C fallback.
3. **옵션 = 결과 미리보기** — 각 항목에 고르면 바뀌는 범위·리스크·시간을 짧게 적는다.
4. **권장 태그 필수 (맥락 반영)** — 옵션 중 하나에 반드시 **(권장)** 태그와 **AskQuestion(`question` 병용) 호출 직전까지의 맥락**(요청, 조사 결과, 리스크, 제약)을 근거로 한 이유 1줄을 단다. 맥락 없이 «가장 안전한» 등 범용 문구만 쓰지 않는다.
5. **비개발자 톤** — [reporting.md](reporting.md) §1.6.0. 질문 문장에 파일 경로·식별자 나열 금지.
6. **한 턴 한 결정** — 서로 다른 갈래는 Quick Pick을 나눠 순차 해소한다.
7. **세션 완료 보고 적용** — 세션 완료 보고나 다음 트랙 합의 시 추가 피드백·결정이 필요할 때도 Quick Pick 의사결정 메뉴를 최우선 순위로 사용한다.
8. **AskQuestion(`question` 병용) 스킵 + 텍스트 답** — `Questions skipped by the user`가 나와도, **직전·동일 턴 사용자 메시지**가 제시한 옵션(A/B/C·라벨·의미 일치)에 매핑되면 **유효 선택**으로 처리한다. 매핑 실패일 때만 동일 질문 재시도. discuss는 [discuss/SKILL.md](../skills/discuss/SKILL.md) §채팅 텍스트 답변 수용·`pending_ask` SSOT.

**MUST NOT**
- 이미 승인된 Blueprint **단일 경로** 자동 실행 중 "다음 단계 진행할까요?" ([planning.md](planning.md) Zero-Choice Path).
- 디스크·명세 Read 후 **경로가 하나**인데 가짜 분기를 만드는 것.

| multi-path 지점 | 행동 |
| :--- | :--- |
| 범위 분기 (최소 vs 확장) | Quick Pick decision menu |
| 아키텍처·데이터 모델 갈림 | Quick Pick + 옵션별 장단점 한 줄 |
| 제품·업무 결정, 후보 2~3개 | Quick Pick |
| 경로를 코드·명세만으로 하나로 좁힐 수 있음 | Quick Pick 없이 해당 경로로 진행 |

### 1.1.2 Exception-before-default (예외·기본 규칙)
동일 절에 **기본 규칙**과 **예외**가 함께 있으면(예: [reporting.md](reporting.md) §1.6.1 QA, [routing.md](routing.md) route gate·lazy_read) 에이전트가 기본만 적용해 혼선이 난다.

**문서 SSOT (해당 절 맨 위)**
1. **적용 순서** 블록 — 조건 판단 → 예외 → 기본 (번호 고정).
2. 예외·기본 본문은 SSOT 한 파일에만 둔다.

**헌법·워크플로 (한 줄 포인터)**
- `AGENTS.md`·워크플로에는 트리거 + 「§ 적용 순서·예외 우선」 링크만. 예외 전문 복붙 금지.

**시범**: [reporting.md](reporting.md) §1.6.1 · [AGENTS.md](../../AGENTS.md) Chat QA · [plan.md](../workflows/plan.md) §1.10.2 closeout.

## 1.2 Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- 요청받지 않은 기능은 추가하지 않는다.
- 단일 용도 코드에 추상화 과잉 금지.
- 요청되지 않은 configurability / flexibility 금지.
- 불가능한 시나리오에 대한 과도한 예외 처리 금지.
- 200줄이면 50줄로 가능하지 않은지 검토한다.
- 시니어 엔지니어가 과설계라고 판단할 수준이면 단순화한다.

## 1.3 Surgical Changes
**Touch only what you must. Clean up only your own mess.**
- 기존 코드 수정 시, 인접 코드/주석/포맷을 함부로 손대지 않는다.
- 깨진 부분만 고친다.
- 기존 스타일을 유지한다.
- 관련 없는 dead code는 삭제하지 말고 언급만 한다.
- 변경으로 인해 생긴 unused import / variable / function만 정리한다.
- 모든 변경 라인은 사용자 요청에 직접 연결되어야 한다.

**예외 (리팩토 제안은 실행이 아님)**:
- `PROJECT_REFACTORING_BACKLOG.md` I등급(500줄 초과) 파일을 수정해야 하는 경우, 분할 Blueprint 작성·제안은 Surgical 범위 위반이 아니다.
- 이 경우 기능 패치를 먼저 밀어붙이지 않고, 분할 Blueprint(Task/Verify 포함)와 `just plan-lint` PASS를 선행한다.
- 위 절차가 끝나기 전에는 I등급 파일 본문을 확장하는 패치를 금지한다.

## 1.4 Goal-Driven Execution
**Define success criteria. Loop until verified.**
작업은 항상 검증 가능한 목표로 쪼갠다.
예:
```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```
- “기능 추가”는 테스트 포함으로 정의한다.
- “버그 수정”은 재현 테스트 후 통과로 정의한다.
- “리팩터링”은 전/후 테스트 통과로 정의한다.
- multi-step task는 짧은 계획을 먼저 제시한다.
- 약한 성공 기준만 있으면 반드시 보강한다.

## 1.5 Pythonic Integrity (Ruff Standards)
상세: [backend/python.md](../domains/backend/python.md)

## 1.6 Workaround Accountability & Close Turn Reflection
**Do not sweep failures under the rug.**
- 작업을 한 번에(직접적으로) 수행하지 못하고 우회책(Workaround/대체 방식)으로 진행하여 목표를 달성한 경우, 단순히 "진행되었다"고만 보고하고 넘어가는 것을 **절대 금지**한다.
- 매 대화의 종료 턴(close turn)이나 세션 요약 시, 다음 3가지를 사용자에게 반드시 보고하고 묻는다:
  1. **Failure & Workaround**: 최초 어떤 시도를 하려 했으나 어떤 문제가 발생하여 우회책을 사용했는지 명시.
  2. **Root Cause**: 문제가 발생한 근본 원인에 대한 추정.
  3. **Future Resolution**: 근본 원인을 해결하기 위한 향후 조치 방안 제안 및 사용자의 의견/결정 요구 (Quick Pick 메뉴 형식 활용).

## 1.7 Code Quality Lifecycle (시점별 품질)

설계·구현·리뷰·CI·테스트마다 확인할 항목의 **normative SSOT**는 [code_quality_lifecycle.md](code_quality_lifecycle.md)다. 본 절은 헌법 수준 요약만 둔다.

- **설계**: 레이어 경계·SSOT·디렉터리 위계를 Blueprint에 먼저 적는다.
- **구현**: 에러는 경계에서만, 중첩 3단계 초과 시 평탄화, 신규 helper 전 검색.
- **리뷰**: 중복·죽은 코드·무음 에러·숨은 결합·re-export·fan-in/out 집중.
- **강제**: strict 타입, ddd·coupling·`fe-boundary-gate`·`fe-function-length-gate`, Biome complexity ≤15.
- **테스트**: 행동 검증, **외부 경계 Mock만**(DB 시드·fixture와 구분), 엣지케이스 고정.
- **커밋 게이트**: `commit-gate`(Husky pre-commit) 실패 시 **반드시 오류를 수정**하고 재시도한다. `git commit --no-verify`로 우회하는 것은 **절대 금지**된다. (`just commit-gate-retry` 자동 수정 재시도 사용 가능)
