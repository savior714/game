---
name: discover
description: "Discover Loop: 기술 부채/리팩토링 후보 탐색 및 실행 가능한 Implement Blueprint 발급"
---
<!-- Language: ko -->

# 🗺️ Discover Loop Skill

이 스킬은 `/discover` 커맨드 또는 "discover 실행" 요청 시 트리거됩니다.

## 📚 참조 문서

- [`references/dead-code-pilot-implementation.md`](references/dead-code-pilot-implementation.md) — dead-code-pilot 구현 패턴 (ruff+vulture 파서, && 우회, 스코프 화이트리스트)
- [`references/lane-split-pattern.md`](references/lane-split-pattern.md) — impact/hygiene 갈래 분리 아키텍처, 구현 체크리스트, 함정

## 🎯 스킬 목적

- **목표**: 사용자가 `/discover` 명령어 입력 시 메뉴를 제시하고, 시나리오를 선택하면 대상(Run Task)을 탐색하여 **기계적으로 실행 가능한 1 Task 단위 Blueprint**를 `docs/plans/PLAN_discover_implement_<큐명>_<타임스탬프>.md` 로 **매 Run마다 신규 발급**합니다.
- **주요 대상**: I등급(500줄 초과) 파일 분할, 죽은 코드 제거, 테스트 파일 분리 등 반복적이고 명확한 기술 부채 해결.

## 1. 메뉴 표시 및 시나리오 선택 (AskQuestion(`question` 병용))

`/discover` 첫 턴에 사용자가 특정 Blueprint나 시나리오를 지정하지 않았다면, **반드시 다음 메뉴 중 1개를 선택하도록 AskQuestion(`question` 병용)**으로 묻습니다.

**AskQuestion(`question` 병용) 옵션** (`options[].label` — 일상어만, DISC·큐 파일명·내부 lane 키워드 금지):

| 사용자 라벨 | 한 줄 설명 (prompt 보조, 라벨에 붙이지 않음) |
| :--- | :--- |
| **제품에 체감되는 개선** | 실서비스·E2E·파일 분할·API 개선 후보 탐색 |
| **테스트·스크립트 청소** | 테스트 분할·죽은 코드·scripts 위생 |
| *(예약)* **야간 반복 루프** | 큐 채우기 + 구현 1건 반복 (Phase 6, 미구현) |

**에이전트 부록** (AskQuestion(`question` 병용) 라벨에 넣지 않음 — 선택 후 lane 매핑용):

| 내부 lane | Run Task | 큐 JSON | Min (최종 검증) |
| :--- | :--- | :--- | :---: |
| `impact` | DISC-R01~R10 | `artifacts/discover/impact_pilot.json` | 3 |
| `hygiene` | dead_code_pilot·DISC | `artifacts/discover/hygiene_pilot.json` | 3 |
| `night-loop` | Phase 6 | — | — |

> **💡 Rule**: AskQuestion(`question` 병용)에는 **「제품에 체감되는 개선」**·**「테스트·스크립트 청소」**만 노출한다. 사용자 선택 후 §2 실행 분기는 부록 **내부 lane**(`impact` / `hygiene`)으로 매핑한다.
>
> **💡 Rule**: 사용자가 `@docs/plans/archive/blueprints/PLAN_discover_loop.md` 를 첨부하고 "impact Run만 해줘" 또는 **제품에 체감되는 개선** Run만 해달라고 명시한 경우에는 메뉴 표시 단계를 생략하고 즉시 실행한다 (`impact` lane).

## 2. 시나리오 실행 (Discover Run)

사용자가 시나리오(예: `impact`)를 선택하면 아래 중 하나로 큐를 채운다.

### A. 백로그 자동 시드

```bash
just discover-seed --lane impact --limit 10
just discover-validate --min 3
just discover-emit --queue artifacts/discover/impact_pilot.json
```

- `PROJECT_REFACTORING_BACKLOG.md`에서 **act 버킷** 경로를 `lane_filter`로 분류하여 `impact_pilot.json`에 추가한다.
- 이미 큐에 있는 `evidence_path`는 건너뛴다 (`discover-append`도 중복 시 skip).
- `--dry-run`으로 추가 전 미리보기 가능.

### B. 수동 Run (레거시 pilot)

`docs/plans/archive/blueprints/PLAN_discover_loop.md` § **Discover Run** 의 **DISC-R01~R10** Task를 순차 실행합니다.

- **discover-lint** 대상. **코드 수정 금지** — 분석·Read만.
- **JSON 직접 편집 금지** — 후보 추가는 **`just discover-append` CLI만** 사용.
- **과정**: 각 Run Task마다 `evidence_path`·`priority`·`template`·`verify_hint`를 확정한 뒤 `just discover-append`로 큐에 1건 추가 → Task별 `just discover-validate --plan docs/plans/archive/blueprints/PLAN_discover_loop.md --task DISC-Rxx --min 1` exit 0.

### C. hygiene dead-code 자동 시드

ruff + vulture 정적 분석으로 tests·scripts 범위의 죽은 코드를 자동 발굴한다.

```bash
just discover-dead-seed
just discover-validate --queue artifacts/discover/hygiene_pilot.json --min 3
just discover-emit --queue artifacts/discover/hygiene_pilot.json
```

- `discover-dead-seed`는 ruff(F401,F841,F842) + vulture를 tests/·scripts/ 범위에서 실행해 `hygiene_pilot.json` 에 추가한다.
- 이미 큐에 있는 `evidence_path`는 건너뛴다.
- `--dry-run`으로 추가 전 미리보기 가능.
- 검증은 `--min 3` 필수.
- emit 출력: `docs/plans/PLAN_discover_implement_hygiene_pilot_<YYYYMMDD_HHMMSS>.md` (매 Run 신규)

## 3. Run 종료 후 Validate · Emit · 안내

모든 Run Task가 완료되면:

1. **검증**: `just discover-validate --min 3` (기본 큐 `artifacts/discover/impact_pilot.json`)
2. **발급**: `just discover-emit --queue artifacts/discover/impact_pilot.json` (종료 시 `plan-lint` PASS 필수 — 실패 시 exit 1). 기본 출력은 `docs/plans/PLAN_discover_implement_impact_pilot_<YYYYMMDD_HHMMSS>.md` — **기존 파일 덮어쓰기 없음**. 최신 경로는 `artifacts/discover/latest_impact_implement_plan.txt` 또는 `latest_hygiene_implement_plan.txt`.
3. **Implement 완료 검증**: 명세가 있는 Task는 `just discover-split-verify <evidence_path>` — 분할 파일 존재·원본 500줄 이하·분할 모듈 pytest.
4. **안내**: emit stdout·`latest_impact_implement_plan.txt` (또는 `latest_hygiene_implement_plan.txt`) 의 Blueprint 경로를 사용자에게 전달하고 `@` 멘션 + `/plan` 으로 Implement Task 실행을 안내합니다.

### 닫힌 루프 (큐 수렴)

- `discover-split-verify` / `discover-dead-verify` 성공(exit 0) 시 해당 `evidence_path`가 impact·hygiene 큐에서 자동 제거된다.
- `discover-seed`·`discover-validate` 시작 시 이미 충족된 후보를 `prune_satisfied`로 정리하고 `discover progress: done=N pending=M pruned=K` 한 줄을 출력한다.
- 수동 위생: `just discover-prune` (기본 큐 `artifacts/discover/impact_pilot.json`).

**DISC-R Run Task Verify**: `just discover-validate --plan docs/plans/archive/blueprints/PLAN_discover_loop.md --task DISC-R01 --min 1` — 해당 Run의 **Target** 경로가 큐에 있고 스키마·split 명세를 만족하는지 검사한다.

> "후보 탐색이 완료되었습니다. `docs/plans/PLAN_discover_implement_<큐명>_<타임스탬프>.md` 파일이 생성되었습니다 (경로: `artifacts/discover/latest_impact_implement_plan.txt` 또는 `latest_hygiene_implement_plan.txt`).
> 위 파일을 `@` 멘션하고 `/plan` 을 사용하여 구현 태스크를 순차적으로 실행해 주세요."
