---
situation: 신규 기능 설계
# trigger: /plan  ← catalog metadata only; Read this file before executing (error_patterns §16.1)
level: Mandatory
description: 전략적 설계 및 문서화 - Blueprint 작성·실행·Task 종료
version: 1.4.0
last_updated: 2026-06-11
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# `/plan` Workflow SSOT

Blueprint(`docs/plans/PLAN_*.md`) 작성·실행·Task 종료. **트리거 시 본 문서 1회 Read.**

**계약·lint normative SSOT**: [planning.md](../core/planning.md) §2 — 본 문서는 **금지·CLI·게이트**만 유지한다.

---

## 금지

| 규칙 | 이유 |
| :--- | :--- |
| `just plan-lint` PASS 전 구현 착수 | 게이트 우회 시 Task·코드 불일치 |
| Task `Status`/`Conclusion` **에디터 직접 수정** | 인접 Task 오염·DAG 깨짐 |
| `just plan-task-close` 없이 Task 완료 선언 | SSOT·감사 추적 상실 |
| Blueprint Task 메타 **역방향 리셋** (승인·CLI 없이) | plan-only todo 리셋 사고 |
| 채팅에만 장문 계획 (Blueprint 없음) | 세션 간 SSOT 상실 — [planning.md](../core/planning.md) §0 |
| `plan-lint` PASS 후 **전체 실행** 중 Blueprint 구조 변경 | 실행 SSOT 붕괴 — `plan-task-close`·Closeout만 허용(§Blueprint 실행 동결) |

---

## CLI (권장 순서)

| 단계 | 명령 |
| :--- | --- |
| 신규 Blueprint | [`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md) Read → `docs/plans/PLAN_<slug>.md` 생성 |
| **Linear 이슈 생성 (MUST)** | `python3 scripts/linear_sync/ensure_plan_linear.py docs/plans/PLAN_<slug>.md` — Major product Blueprint는 **반드시** Linear 이슈 생성 전진행 |
| **Pre-read (MUST)** | `just plan-preread docs/plans/<file>.md --write` — **plan-lint 전 반드시 실행**. 누락 시 Task-level Pre-read FAIL |
| 구조 검증 | `just plan-lint docs/plans/<file>.md` → **PASS 전 구현 금지** (Linear ensure가 PASS 전제) |
| Task 종료 | `just plan-task-close plan=docs/plans/<file> task=<ID> conclusion="..."` |
| Task 종료 후 | `just plan-lint docs/plans/<file>.md` |
| **마지막 Closeout Task** | Roll-up 작성 → `just plan-close plan=docs/plans/<file>.md` → `just plan-task-close` |
| 플랜 마감 | `just plan-close plan=docs/plans/<file>.md verify="..."` (Closeout Task Verify와 동일) |
| 역방향 리셋 (예외) | `just plan-reset-gate plan=... task=... sha=<git-sha> approval="..."` → `--apply` |
| 세션 종료 | `just lint-turn-end` |

---

## 작성 — Origin Intent & Edge Case Trace (활성 Blueprint MUST — 문서)

`just plan-lint` **전**, Blueprint 본문에 아래를 반드시 채운다. **plan-lint HARD는 아님**(문서·워크플로 규범). 상세 필드·표·Phase 0 예시: [`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md) 「Origin Intent · Edge Case Trace」.

| 순서 | 액션 | 실패 시 |
| :---: | :--- | :--- |
| 1 | `## 🎯 Origin Intent` — 원래 목적 프롬프트·handoff·emit 출처를 1~3줄로 고정 | happy path만 Task화한 채 lint 진행 **금지** |
| 2 | `## ⚠️ Edge Case Trace` 표 — Origin·Risk·discuss `[열림]`·도메인 관례에서 엣지 케이스 **행 단위** 나열 | 표 생략 **금지** (`해당 없음` 1행은 허용) |
| 3 | **갭 감사** — 각 행에 `Task-ID` **또는** `범위 밖`(사유) 중 하나 필수 | 미매핑 행 남기고 구현 Task 착수 **금지** |
| 4 | 갭 있으면 **보완 Task 추가** 또는 `## 📋 업무 요약` 「이번에 안 하는 것」에 범위 밖 사유 기록 | `(선택)` Task·실행 중 AskQuestion 분기 **금지** — [planning.md](../core/planning.md) §0 |
| 5 | (권장) `Phase 0 — Edge case gap audit` Task 1개 — 표·보완 Task 반영 후 `just plan-preread --write` | — |

**엣지 케이스 발굴 체크리스트** (해당 시 행 추가): 빈 입력·null·경계값 · API/연동 실패·타임아웃 · 동시성·중복 요청 · UI 빈/오류/로딩 상태 · 권한·세션 만료 · 오프라인·프린트 · 시드/데이터 없음 — [code_quality_lifecycle.md](../core/code_quality_lifecycle.md) §2 I-4.

**출처별 Origin Intent 예시**:

| 출처 | Origin Intent에 적을 것 |
| :--- | :--- |
| discuss handoff | `docs/discussions/…` §3 방향·완료 기준 1줄 + 사용자 최초 요청 paraphrase |
| discover-emit | `evidence_path`·`verify_hint`·큐 lane(`impact`/`hygiene`) |
| research handoff | `docs/knowledge/research_results/…` 결론 1줄 |
| 직접 `/plan` | 채팅 첫 요청 문장(의도만, 경로·CLI 제외) |

**범위 밖 처리**: 인범위가 아닌 엣지는 Trace 표 `범위 밖` 열 + 업무 요약 「이번에 안 하는 것」에 **동일 문장** 반복. 후속 필요 시 **별도 `PLAN_*.md`**(OHT)로 분리 — 한 파일에 옵션 분기 Task 체인 금지.

---

## 작성 전 AskQuestion — Edge Case Design Gate (선제 유도)

사용자가 «엣지 케이스도 고려해줘»라고 **말하지 않아도**, Blueprint **저장·`plan-lint` 전** 아래를 따른다. **Decision Gate 시점**([planning.md](../core/planning.md) §0) — Task 실행 중 AskQuestion 분기는 여전히 금지.

| 조건 | 행동 |
| :--- | :--- |
| DISCUSS §3에 **엣지 케이스** 불릿·`[확정]`이 **1건 이상** | 답변을 Edge Case Trace 표에 **직접 반영** — 추가 AskQuestion **생략 가능** |
| DISCUSS handoff인데 §3 엣지 기록 **없음** | **AskQuestion 1턴** 필수 — [plain-language-questions.md](../skills/discuss/references/plain-language-questions.md) §엣지 케이스 선제 |
| 직접 `/plan`(discuss 없음) | 동일 **AskQuestion 1턴** 필수 |
| discover-emit | `verify_hint`·큐 맥락으로 Trace 채움 — AskQuestion **생략** |

**AskQuestion 규칙** (1턴 = 질문 1개, 옵션 3~4개):

1. Architectural Goal·업무 요약에서 **staff가 실제로 겪을 예외 상황** 2~3개를 **구체 문장**으로 제시(빈 목록·저장 실패·권한 없음·데이터 없음 등).
2. `(권장)` **1개** — route·도메인·DISCUSS 맥락에서 **가장 빈번한 실패 경로**.
3. 옵션 예: **「{상황A}도 이번에 포함」** / **「{상황B}도 포함」** / **「둘 다 이번 범위」** / **「이번엔 happy path만 — 예외는 범위 밖」**.
4. 답변 → Edge Case Trace 행 + 인범위면 Task 보완 · 범위 밖이면 「이번에 안 하는 것」.

**금지**: 사용자 미언급을 이유로 AskQuestion 생략 · happy path Task만 작성 후 Trace를 `해당 없음`으로 채우기.

**same-session plan** ([discuss/SKILL.md](../skills/discuss/SKILL.md) §Same-session plan): DISCUSS에 엣지 기록이 있으면 plan 단계 AskQuestion 생략; 없으면 PLAN 파일 작성 **직전** 본 게이트 1턴.

---

## 게이트 — Blueprint 실행 동결 (Execution Freeze)

**표준 사용 패턴**: Blueprint를 `just plan-lint` **PASS**까지 작성해 두고 → 사용자가 `@PLAN_*.md` **전체 진행**·「이 플랜 다 실행해줘」 등으로 **한 파일 전체**를 순차 실행해 달라고 요청한다. 이때 Blueprint는 **실행 SSOT**이며, Task마다 구조를 바꾸지 않는다.

| 시점 | Blueprint 편집 |
| :--- | :--- |
| **작성 단계** (`plan-lint` PASS 전) | Origin Intent · Edge Case Trace · Task 추가·Goal 수정 **허용** (설계·엣지 AskQuestion 포함) |
| **동결 시작** | `plan-lint` PASS **후** 사용자가 전체·Task 연속 실행을 요청한 시점 (또는 Task 1.1 착수) |
| **동결 중** (Task 1.1 ~ 마지막 구현 Task) | 아래 **허용**만 — 그 외 본문·Task 메타 **금지** |
| **Closeout Task** | Roll-up 줄만 편집 ([`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md) Agent Completion Contract) |

**동결 중 허용** (이것만):

| 액션 | 도구 |
| :--- | :--- |
| Task `Status`·`Conclusion` 갱신 | `just plan-task-close` **만** (에디터 직접 수정 금지) |
| Closeout Roll-up | Closeout Task Goal 범위의 `## 🔁 Conclusion & Summary` 1문단 |

**동결 중 금지** (사용자가 실행 중단·재설계를 **명시**하지 않는 한):

- Task **추가·삭제·재번호** · `Goal`/`Target`/`Dependency`/`Verify` 수정
- `## ⚠️ Edge Case Trace` · Origin Intent · 업무 요약 **구조 변경**
- 실행 중 `AskQuestion`/`question`으로 범위·엣지 **재협상** ([planning.md](../core/planning.md) §0 Zero-Choice)
- 발견한 갭을 이유로 **즉석 Blueprint 패치** — `Status: blocked` + Conclusion에 사유 기록 후 **사용자에게 보고**; 재설계는 **새 `PLAN_*.md`** 또는 `just plan-reset-gate`(본 문서 §CLI)

**Phase 0 (Edge case gap audit)**: Trace·보완 Task는 **작성 단계**(`plan-lint` PASS 전)에 끝내는 것이 표준. 파일에 Phase 0 Task가 남아 있으면 **전체 실행의 첫 Task 1개**로만 구조 보완 가능 — **완료 직후 동결**, 이후 Phase 1+에서 Blueprint 구조 변경 **금지**.

**에이전트 순서 (전체 실행 요청 시)**: `plan-lint` PASS 확인 → (Phase 0 있으면 1회만) → Task **Dependency 순**으로 1개씩: Pre-read → 코드/문서 편집 → Verify → `plan-task-close` → `plan-lint` → 다음 Task. 중간에 Blueprint 재작성·Task 분해 **하지 않음**.

---

## 게이트 — Task Closeout 4단계

코드·테스트만 Green이어도 Task 완료가 **아니다**. 아래 **순서대로** 수행한다.

| 순서 | 액션 | 실패 시 |
| :---: | :--- | :--- |
| 1 | Task `Verify` 셸 명령 **1개** 실행 → exit 0 | `blocked` 또는 재시도 |
| 2 | `just plan-task-close` 실행 | 에디터 직접 수정 **절대 금지** |
| 3 | 스크립트가 `Status`→`done` + `Conclusion` 갱신 | — |
| 4 | `just plan-lint` PASS | 채팅 「완료」는 **4 이후만** |

**Conclusion**: `todo`/`running` → CSF 슬롯만 · `done` → 실측 1줄 + Verify exit 0. 상세: [planning.md](../core/planning.md) §2.2.

**기존 Blueprint 수락**: `Status: done`이어도 `plan-lint` 구조 검증 생략 금지 — stdout `[WARN]` 없음 확인.

---

## 게이트 — 마지막 Closeout Task (신규 Blueprint)

구현 Task만 닫고 Roll-up·DoD·`plan-close`를 빼먹는 사고 방지. normative 필드·예시: [`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md) 「마지막 Closeout Task」.

| 순서 | 액션 |
| :---: | :--- |
| 1 | 선행 구현 Task 전부 `done` + Conclusion 실측 |
| 2 | Closeout Task: `## 🔁 Conclusion & Summary` **Roll-up 1문단** 작성 (해당 Task Goal 범위) |
| 3 | `just plan-close plan=docs/plans/<file>.md` → exit 0 (DoD 백틱 명령 **자동 실행**) |
| 4 | `just plan-task-close` → `just plan-lint` PASS |

**금지**: 구현 Task만 `done`으로 두고 Roll-up을 `(Task 완료 후 갱신)` placeholder에 방치한 채 플랜 완료 선언.

**DoD**: `[ ]` 수동 체크리스트 아님 — 백틱 명령 목록. Closeout Verify PASS = DoD 일괄 PASS.

---

## lazy (필요 시 Read)

| 주제 | SSOT |
| :--- | :--- |
| §1.9 필수 3항·lint HARD 13항 | [planning.md](../core/planning.md) §2.1 · [`plan_lint.py`](../../scripts/plan_loop/plan_lint.py) |
| Agent Completion Contract | [`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md) · [planning.md](../core/planning.md) §2.1 6c |
| Pre-read·installed 상한 5 | [planning.md](../core/planning.md) · `just plan-preread --help` |
| Task Reset Audit | [planning.md](../core/planning.md) §2 · 본 문서 §CLI `plan-reset-gate` |
| OHT·Decision Gate | [planning.md](../core/planning.md) §0 |
| DISCUSS same-session 핸드오프 | [discuss/SKILL.md](../skills/discuss/SKILL.md) |
| 협업용 업무 요약 | [`TEMPLATE_blueprint_collaboration_summary.md`](../../docs/templates/TEMPLATE_blueprint_collaboration_summary.md) |
| Closeout Task·Roll-up | [`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md) 「마지막 Closeout Task」 · 본 문서 §게이트 Closeout |
| Close gate 스크립트 | [`plan_close_gate.py`](../../scripts/verify/plan_close_gate.py) |
| Origin Intent · Edge Case Trace | 본 문서 §작성 — Edge Case Trace · [`TEMPLATE_blueprint.md`](../../docs/templates/TEMPLATE_blueprint.md) |
| Edge Case Design Gate (AskQuestion) | 본 문서 §작성 전 AskQuestion · [plain-language-questions.md](../skills/discuss/references/plain-language-questions.md) §엣지 케이스 선제 |
| Blueprint 실행 동결 | 본 문서 §게이트 — Blueprint 실행 동결 |
