---
scope:
- '*'
always_apply: false
priority: 1
domain: core
---
<!-- Language: ko -->

# Planning & Thinking Levels

본 문서는 프로젝트의 설계(Planning) 프로세스와 사고 수준(Thinking Levels), 그리고 계획 완료를 위한 게이트 규칙을 정의합니다.

---

## 0. Strategic Planning Rules
- **Granularity & Deepening Gate**: 파일 이름이 `PLAN_epic_` 이거나 내용이 거시적 기획인 문서의 Task는 직접 실행(Execute)해서는 안 되며, 반드시 `/plan` 워크플로우를 통해 하위 Blueprint(`PLAN_..._task_...md`)로 쪼개야 한다. (Task 1개가 3개 이상의 파일을 광범위하게 수정하거나, 구체적인 검증 수치가 없으면 Atomic이 아닌 것으로 간주)

- **Track Isolation**: 진행 중인 활성 트랙(`active blueprint`)을 함부로 덮어쓰거나 대규모로 수정하지 않는다. 대신 새로운 `PLAN_*.md` 파일을 생성하여 트랙을 분리하고 참조(Link)를 통해 연결한다.
- **Ordered Hypothesis Tracks (OHT)**: 근본 원인이 **복수 가설**로 남는 경우 **가설마다 별도 `PLAN_*.md`**를 두고, **대표 Blueprint 본문 표**에 실행 순서·선행 플랜으로 해결 시 **후행 미실행(단기회로)**를 명시한다. 활성 `docs/plans/` 루트에 `PLAN_*_INDEX.md`는 두지 않는다. 한 Blueprint에 옵션별 분기 태스크 체인을 넣지 않는다. SSOT: [.agents/workflows/plan.md](../workflows/plan.md) §0.6.
- **Artifact-First (채팅 전용 계획 금지)**: `/plan` 또는 동등한 설계·태스크 분해 요청이 있으면 **반드시** `docs/plans/*.md`에 Blueprint를 남긴다. 플랜 파일 없이 채팅에만 장문 계획을 쓰는 것은 **금지**이며, 설계 완료·게이트 통과로 인정하지 않는다(토큰 낭비·세션 간 SSOT 상실). 예외: 사용자가 문서 생략을 **명시적으로** 요청한 경우. 상세 절차는 [.agents/workflows/plan.md](../workflows/plan.md) 문서 상단 「산출물 강제」 절.
- **Zero-Choice Path (단일 경로 보장)**: **동일 Blueprint 파일 안에서** 실행 중 사용자에게 선택지(A or B)를 묻거나 분기하는 태스크 구성을 **엄격히 금지**한다. 각 파일은 즉시 실행 가능한 단일 파이프라인이어야 한다. **서로 다른 가설**에 대응하는 경로는 **OHT**로 별도 파일에 나누고, 대표 Blueprint 본문 표에서만 순서를 정한다. 단일 파일 내에서는 `Research-First`로 남은 불확실성을 없앤 뒤 태스크를 적는다.
- **Decision Gate (중대 결정 선보고)**: 아키텍처나 워크플로우에 중대한 영향을 미치는 선택지가 존재할 경우, Blueprint를 확정하기 전 사용자에게 옵션별 장단점을 보고하고 최종 결정을 요청해야 한다. 사용자의 결정이 내려진 후에만 단일 경로 Blueprint를 작성/수정한다. **OHT(§0.6)**로 복수 가설을 파일로 나눈 경우에는, 사용자에게 **실행 순서·단기회로 규칙**이 합리적인지 확인하는 것으로 Decision Gate를 충족할 수 있다.
- **Decision Gate vs Zero-Choice (타이밍 SSOT)**: **Blueprint 본문 작성·Task 실행 중**에는 Zero-Choice(단일 경로)만 허용 — 실행 중 `AskQuestion`/`question`(병용)으로 A/B 분기 금지. **Blueprint 확정 전 설계 단계**(범위·아키텍처·OHT 순서·가설 선택)에서는 Decision Gate·[principles.md](principles.md) §1.1.1 `AskQuestion`/`question`(병용)으로 옵션을 수렴한 뒤, 확정된 **한 경로**만 Blueprint에 기록한다. 복수 가설은 OHT로 **파일 분리**하고, 한 파일 안에 옵션별 Task 체인을 두지 않는다.
- **No Optional Tasks (모호한 선택적 태스크 금지)**: Blueprint의 태스크 제목이나 목표에 "(선택)", "(Optional)", "(필요 시)"와 같은 모호한 수식어를 사용하는 것을 **금지**한다. 계획에 포함된 태스크는 반드시 수행해야 하는 단계여야 하며, 수행 여부가 불확실한 작업은 계획에서 제외하거나 별도 트랙으로 분리해야 한다.
- **Linter-Friendly descriptions**: `Diagnostics`나 자연어 설명 섹션에서 `Status:`, `Task-ID:`와 같은 린터 예약 키워드를 직접 사용하는 것을 회피한다. (예: "Status: Proposed" 대신 "Proposed 상태임"으로 기술)
- **Target Path SSOT Gate**: Task **첫 실행 전** `Target`에 적힌 경로·export를 `rg`/Glob으로 **코드베이스에 실존** 확인. Blueprint-only 경로(과거 아카이브 잔재)면 Task를 `blocked`로 두고 경로 수정 Task를 선행한다.
- **Import graph spot-check**: "모든 X에 적용"류 Task는 mount/import **진입점**을 import 그래프로 확인한 뒤 범위를 확정한다 — [improve-codebase-architecture/SKILL.md](../skills/improve-codebase-architecture/SKILL.md) Single Entry Point.
- **Design Quality Gate**: Blueprint 작성 시 레이어 경계·SSOT·디렉터리 위계를 Task에 먼저 적는다 — [code_quality_lifecycle.md](../core/code_quality_lifecycle.md) §1.
- **Edge Case Trace Gate (문서 MUST)**: 활성 `docs/plans/PLAN_*.md`는 `just plan-lint` 전 `## 🎯 Origin Intent`·`## ⚠️ Edge Case Trace`를 채운다. 인범위 엣지는 Task-ID로 매핑하거나 Atomic Task로 보완하고, 범위 밖은 업무 요약 「이번에 안 하는 것」에 사유를 적는다 — [plan.md](../workflows/plan.md) §「작성 — Origin Intent & Edge Case Trace」·[`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md).
- **Edge Case AskQuestion Gate (설계 MUST)**: Blueprint **저장 전** 사용자가 엣지를 요청하지 않아도 [plan.md](../workflows/plan.md) §「작성 전 AskQuestion」·[discuss/SKILL.md](../skills/discuss/SKILL.md) §엣지 케이스 선제 유도로 **AskQuestion 1턴 이상** 거쳐 답을 Trace·Task에 반영한다(discuss §3 엣지 기록·discover-emit은 생략 가능). **Decision Gate 시점**에만 허용 — Task 실행 중 분기 금지(§0 Zero-Choice).
- **Blueprint Execution Freeze (실행 동결)**: `just plan-lint` PASS 후 사용자가 Blueprint **전체 실행**을 요청하면 본문·Task 구조는 **동결**한다. 허용은 `just plan-task-close`·Closeout Roll-up뿐. Task 추가·Goal/Target 변경·실행 중 엣지 재협상 **금지** — 막히면 `blocked` 후 새 `PLAN_*.md` 또는 `plan-reset-gate`. SSOT: [plan.md](../workflows/plan.md) §「Blueprint 실행 동결」.

---

## 1. Adaptive Thinking Levels

복잡도와 영향도에 따라 적절한 사고 수준을 적용합니다.

| Level | When |
|---|---|
| L1 | optional |
| L2 | recommended |
| L3 | mandatory: architecture, migration, data integrity, external integration, large refactor |

불확실하거나 범위가 커질수록 더 높은 레벨을 적용합니다.

---

## 2. Blueprint Contract & Plan Gate

### 2.1 Blueprint Contract 자동 검증
모든 plan 파일(`docs/plans/*.md`)의 생성 및 수정 시 즉시 `just plan-lint plan=<path>`를 실행하여 규격 정합성을 검증해야 합니다. 통과 전 저장/제출 금지.

#### 자동 감지 규칙
1. Task 헤딩은 `#### Task X.Y: 제목 [Unit: Atomic]` 형식을 SSOT로 한다 — **X·Y는 숫자만** (`Task D.1` 등 문자 접두는 `plan_lint` FAIL). (`[Level: Low]`는 전환기 deprecated alias — lint WARN)
2. `[Level: Medium]` / `[Level: High]` 금지 (난이도 등급이 아니라 **원자 실행 단위** 태그임)
3. Task `Verify`는 **셸 명령 1개** (`;` / `&&` / `||` 금지) — **FAIL**. `pytest`는 **한 가지 결과**만 (`-k` 또는 `::`) — **FAIL** (Single Proof). 장기 실행 큐 SSOT: [.agents/workflows/plan.md](../workflows/plan.md) §1.9–§1.10
4. Task **100개+** 허용; 칸마다 Verify→Conclusion→Status로 닫히는 것이 목표(개수 상한 없음)
5. 각 Task 필수 필드: `Task-ID`, `Pre-read`, `Action`, `Target`, `Goal`, `Diagnostics`, `Verify`, `Conclusion` — `Pre-read`는 `just plan-preread --write`로 Task `Target` 기준 생성(단일 Task 실행 SSOT: [.agents/workflows/plan.md](../workflows/plan.md) §1.11)
6. 문서 상단 필수 메타: `SSOT Check`, `Project Status Link`, `Architectural Goal`
6b. 전체 규격 Blueprint: `## 📋 업무 요약 (협업용)`(메타 직후) — 비개발자 자연어 3절; `plan_lint`가 백틱·경로 혼입 FAIL. SSOT: [plan.md](../workflows/plan.md) · [TEMPLATE_blueprint_collaboration_summary.md](../../docs/templates/TEMPLATE_blueprint_collaboration_summary.md)
6c. **활성 루트 Blueprint**(`docs/plans/PLAN_*.md`, `archive/` 제외): `## Agent Completion Contract` + Execution Plan `> **에이전트 스코프**` — `plan_lint` HARD. [`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md)는 **참고용**(전체 복붙 불필요) — [plan.md](../workflows/plan.md) §1.9.1
    - **Metadata Parsing**: `Linear-Issue`, `Project` 등의 메타데이터는 멀티라인(Bold/List variant)을 지원하므로 정규식 파싱 시 유연성을 확보해야 함.
7. Status 값: `blocked`, `done`, `failed`, `running`, `todo` (`completed` 금지). 실행 시 Verify 실패 반복은 `blocked`로 닫는다(plan.md §1.10)
8. `RetryPolicy`: `none`, `once_on_flake`
9. Dependency 누락 시 자동 추가 (선행 Task가 없으면 `None`)
10. **Verify 실수 방지**: 존재하지 않는 테스트 파일(`test_verify_task_*.py` 등) 실행 금지. `inspect`/`ast.parse` 기반 inline 검증 또는 실제 존재하는 `pytest -k <single_test_name>` 사용.

### 2.2 Conclusion 강제 게이트 (Hard Gate)
- **Task 레벨**: Task 완료 선언 전 `Conclusion` 필드에 실제 수행 내용을 반드시 기입합니다. Task당 `- **Conclusion**:` **1줄만**(`just plan-task-close` CLI 사용 강제; 직접 편집 금지, 중복·Task 내부 `## Conclusion` 헤딩은 `plan_lint` FAIL).
- **상태 일치**: `Status: todo`·`running`일 때 Conclusion은 CSF 슬롯(`[판정 — 비개발자용 요약. 검증 결과]` 등)만 허용 — `통과 —`·테스트 Green 등 실측 문장은 `Verify` PASS 후 `done`과 함께 기입([plan.md](../workflows/plan.md) §2.3).
- **문서 레벨**: 모든 Blueprint는 반드시 하단에 `## Conclusion` 또는 `## 🔁 Conclusion & Summary` 섹션을 포함해야 하며, 세션 종료 전 전체 진행 상황을 요약합니다.
- **SSOT Block**: 규칙 파일과 플랜 파일 간 지침이 상충할 경우, Blueprint 내에 명시적인 `Conclusion-on-done` 블록(Agent Scope)을 작성하여 이를 최종 SSOT로 삼습니다.
- `[완료 시 기입]` placeholder가 남아 있는 상태에서 `Status: done` 선언 금지.
- **완료 조건**: 최소 **25자 이상**, 구체적인 변경 파일명/행위/검증 결과(테스트 수, 명령어 결과) 포함.
- **플레이스홀더 절대 금지**: `just plan-lint`는 각 Task의 `Conclusion` 필드를 검증합니다. 아래 예시와 같이 의미 없는 플레이스홀더를 남겨둘 경우 검증 실패 처리됩니다.
  - `[판정 — 비개발자용 요약. 검증 결과]` (X)
  - `[완료 시 기입]` (X)
  - `Task 9.9에서 선행 Task 결과를 근거로 작성한다.` (X)
  - 올바른 예시: `SPEC_ui_billing.md에 청구 준비 점검 패널 요구사항 추가 완료. just docs-ssot-headers PASS.`
- ⚠️ **형식 주의**: Conclusion 값에 마크다운 표(`|`)를 사용하지 마십시오. linter의 pipe-split 로직과 충돌하여 내용이 유실됩니다. 텍스트 요약 형태로 작성하십시오.

### 2.3 Plan Update Hard Gate
다음 중 하나면 완료 선언 전 plan Conclusion 업데이트가 필수입니다.
1. plan 파일 수정 포함
2. `/plan` 워크플로우 트리거됨
3. 세션 내 plan 파일 read

### 2.4 Plan Close Gate
```bash
just plan-close plan=docs/plans/<target>.md verify="<cwd>::<cmd>|||..."
```
- **실행 순서 준수 (LIS-009)**: `just plan-close`는 반드시 다음 순서를 지켜서 실행해야 합니다. 순서를 어기고 `linear-sync` 없이 실행하면 `[FAIL] Linear synchronization required` 에러가 발생합니다.
  1. `just docs-ssot-headers` (docs 검증 및 레시피 실존 확인)
  2. `just linear-sync` (로컬 진행 상황을 Linear 리모트로 동기화)
  3. `just plan-close` (최종 plan close gate 실행)
- **DoD 재귀 금지**: Blueprint의 DoD(Definition of Done) 섹션 내 검증(verify) 명령어로 `just plan-close` 자체를 포함하는 것을 **엄격히 금지**합니다. `plan_close_gate.py`가 이를 추출하여 무한 루프나 재귀 타임아웃을 유발하는 원인이 됩니다.
- **DoD 레시피 실존 검증**: Blueprint의 DoD에 명시되는 모든 `just <recipe>` 명령어는 실제로 `justfile` 내에 정의되어 있어야 합니다. 작성 시 `just --list`로 존재 여부를 사전 확인하고, 존재하지 않으면 stub를 만들거나 실제 검증 스크립트로 대체해야 합니다.
- **Conclusion 선행**: 게이트 실행 전, 방금 완료한 Task들의 `- **Conclusion**:`을 채웠는지 확인한다. `plan_close_gate.py`는 문서 전역의 `[완료 시 기입]` 잔존과 `Status: done`(및 레거시 `completed`) 줄에 대응하는 Conclusion 비어 있음을 차단한다.
- `verify` exit ≠ 0 → 완료 금지
- `Script not found` 발생 → 완료 금지
- `artifacts/verify/verify-last-result.json` fail → 상태 `in_progress` 유지

### 2.7 Plan Archiving Gate
- **이관 프로세스 준수**: 완료된 Blueprint(`docs/plans/PLAN_*.md`)를 `archive/` 폴더로 이관할 때는 절대로 수동 복사/삭제를 하지 마십시오.
- **아카이브 CLI 실행**: 반드시 [archive.md](../workflows/archive.md) 워크플로우를 먼저 읽은 뒤, `scripts/archive_plans.py` 스크립트를 실행하여 참조 링크를 일괄 갱신하며 안전하게 이관해야 합니다.

### 2.5 Linear Sync Gate (LIS-008)
모든 신규 Blueprint(`PLAN_*.md`)는 최초 Task 실행 전 다음 절차를 반드시 완료해야 합니다.
1.  **실측 기반 Linear Issue 생성 및 조회 (최선행)**: Blueprint 내의 Linear-Issue 번호를 하드코딩하거나 추정하여 정하는 것을 **엄격히 금지**합니다. 반드시 `python3 scripts/linear_sync/ensure_plan_linear.py <path> --dry-run` 또는 관련 조회 API를 선행 실행하여 Linear 상의 최신 활성 이슈 상태와 사용 가능한 다음 번호를 물리적으로 조회합니다.
2.  **자동 발행 권장**: 수동 하드코딩 대신 `python3 scripts/linear_sync/ensure_plan_linear.py <path>` 스크립트를 기동하여 Linear 상에 신규 이슈를 자동으로 발행하고, Blueprint 마크다운에 발급된 정식 이슈 ID를 자동 기입받는 프로세스를 표준으로 삼습니다.
3.  **Mapping 연동**: Blueprint의 모든 Task 메타라인에 `Linear-Issue: TEM-[발급된번호]` 형식을 정확히 매핑하여 추가합니다.
4.  **동기화 확인**: `just linear-sync --dry-run plan=<path>`로 파싱·시뮬레이션을 확인한 뒤, 반영이 필요하면 **같은 명령에서 `--dry-run` 없이** 실행한다. 키는 루트 **`.env`**(또는 이미 export된 환경)에 두며, **셸에만 없다고 키가 없는 것은 아님** — [linear.md](../workflows/linear.md)「실행 절차 → API 키·`.env` SSOT Locker」.
    - **API Fix**: `issueUpdate` GraphQL 호출 시 `input: { stateId: "..." }` 형식을 사용한다. (ID를 input 내부에 넣는 레거시 방식은 400 에러 발생)
- `plan-lint`에서 `Linear-Issue` 누락 시 **Fatal Error**로 처리되어 실행이 차단됩니다.

### 2.5.1 내부 tooling Blueprint Linear 자동 발행 제외

에이전트·검증·discuss 같은 **내부 개선** 계획서는 로컬 Blueprint만으로 추적하며, Linear 이슈를 자동 생성하지 않습니다. 제품 기능·의료 업무 위주로만 보드가 가득 차는 것을 방지합니다.

**자동 스킵 대상**:
- 경로가 `.agents/`, `scripts/agent/`, `scripts/plan_loop/`, `scripts/discover_loop/`, `scripts/linear_sync/`, `scripts/dev_quality/`로 시작하는 Blueprint
- 문서 메타에 `Linear-Policy: internal`이 명시된 Blueprint

**권장 사항**:
- 제품 기능 Blueprint는 `plan-lint` ensure 경로를 통해 TEM 자동 발행을 권장합니다.
- 내부 Blueprint의 `Linear-Issue` 기본값은 `N/A`로 통일합니다.

### 2.6 Blueprint Execution Gates (Target · Dependency)

#### Target Path SSOT
- Task `Target` 경로는 **실측 1건 이상** 존재해야 실행한다 (`rg`·Glob·Read).
- 문서에만 남은 phantom path는 [execution.md](execution.md) §2.11 Honesty 위반 — `blocked` 후 경로 정정 Task 선행.

#### Dependency Semantics
- **Compile-time vs runtime**: FE DataProvider·Context·타입 정의는 BE 어댑터 **구현 완료**에 의존하지 않음 — 타입/스키마 SSOT만 있으면 `Dependency: None` 또는 문서 Task만 선행.
- **Parallel by default**: 동일 레이어·서로 다른 파일·공유 상태 없는 Task는 **수직 체인 금지** — 병렬 후 통합 테스트 Task 하나만 순차.
- **Integration test placement**: "적용" Task와 "통합 테스트" Task를 한 줄 체인으로 묶지 말고, 적용 병렬 → 테스트 단일 합류.
- **Client/endpoint ordering**: API 클라이언트·SDK 설정 Task는 **실제 엔드포인트/게이트웨이 스켈레톤** Task에 의존; 문서화 Task만으로는 선행 불가.

#### Strategic Pivot · Plan Cancellation
- 단일 환경·인프라 차단이 의존 체인 전체를 막으면 하위 Task를 **삭제하지 말고** `Status: cancelled`(또는 `blocked`) + **취소 사유 한 줄** + Plan `## Conclusion`에 방향 전환 기록.
- 장기 인프라 실험(벤치마크·외부 스택 PoC)은 **제품 Blueprint와 의존 분리** — 실패 시 제품 트랙 전체가 연쇄 취소되지 않게 설계.
