---
description: "Discover Loop: 기술 부채/리팩토링 후보 탐색 및 실행 가능한 Implement Blueprint 발급"
globs: "*"
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# /discover 워크플로우

`.agents/skills/discover/SKILL.md`를 즉시 Read하고 지침에 따라 Discover Loop를 실행하세요.

- **목표**: `/discover` 실행 시 메뉴를 띄워 시나리오를 선택하게 하고, 선택된 시나리오의 Run Task를 기계적으로 돌려 `docs/plans/` 아래 **타임스탬프 Blueprint**를 매 Run 신규 발급합니다.
- **정본**: `.agents/skills/discover/SKILL.md` — 시나리오 메뉴 · impact/hygiene 갈래별 실행 절차.
- **에디트 규칙**: [AGENTS.md §2.1](AGENTS.md) · [runtime_edit_tools.md §1](../core/runtime_edit_tools.md) — 세션 **읽기 도구**로 디스크 확인 → **부분 수정 도구** 호출 전 old/target 문자열 존재·유일성·old≠new.

## 사용자 흐름 (실행 불릿)

1. `.agents/skills/discover/SKILL.md` §1 Read → **AskQuestion(`question` 병용)** (「제품에 체감되는 개선」 또는 「테스트·스크립트 청소」 — DISC·큐 파일명은 라벨에 넣지 않음). 선택 후 내부 lane `impact` / `hygiene` 매핑은 SKILL §1 부록.
2. 큐 채우기 — **체감 개선(`impact`) 권장**: `just discover-seed --lane impact --limit 10` (백로그 → impact_pilot.json, lane_filter 분류). **청소(`hygiene`)**: `just discover-seed --lane hygiene --limit 10` 또는 `just discover-dead-seed` (ruff+vulture → hygiene_pilot.json, 중복 skip). 필요 시 `just discover-prune`으로 수동 위생.
3. `just discover-validate --queue artifacts/discover/impact_pilot.json --min 3` exit 0 (또는 hygiene: `--queue artifacts/discover/hygiene_pilot.json --min 3`).
4. `just discover-validate --min 3` → `just discover-emit --queue artifacts/discover/impact_pilot.json` (plan-lint PASS 필수) → stdout·`artifacts/discover/latest_impact_implement_plan.txt` (또는 hygiene: `latest_hygiene_implement_plan.txt`) 의 Blueprint 경로 전달.
5. 사용자: emit된 `docs/plans/PLAN_discover_implement_*.md` 파일을 참조하여 `/plan` 후 Implement Task 실행.

## §4 검증 게이트

- **plan-lint**: `just discover-emit` 종료 시 `plan-lint` PASS 필수 — 실패 시 exit 1.
- **plan-close**: [AGENTS.md §2.2](AGENTS.md) — Blueprint Task `Status`/`Conclusion`은 `just plan-task-close` CLI만 사용, 에디터 직접 수정 금지.
- **plan-close 실행 순서**: `just docs-ssot-headers` → `just linear-sync` → `just plan-close`.
- **Conclusion 검증**: [AGENTS.md §4.4](AGENTS.md) — Conclusion은 최소 25자 이상, 실제 검증 결과 포함, 플레이스홀더 금지.
- **DoD 레시피 실존**: [AGENTS.md §4.5](AGENTS.md) — PLAN 파일 DoD에 명시된 `just <recipe>`는 실제 justfile에 존재해야 함.

## §5 닫힌 루프 (큐 수렴)

- `discover-split-verify` / `discover-dead-verify` 성공(exit 0) 시 해당 `evidence_path`가 impact·hygiene 큐에서 자동 제거된다.
- `discover-seed` / `discover-validate` 시작 시 이미 충족된 후보를 `prune_satisfied`로 정리하고 `discover progress: done=N pending=M pruned=K` 한 줄을 출력한다.
- 수동 위생: `just discover-prune` (기본 큐 `artifacts/discover/impact_pilot.json`).
- **DISC-R Run Task Verify**: `just discover-validate --plan docs/plans/archive/blueprints/PLAN_discover_loop.md --task DISC-R01 --min 1` — 해당 Run의 **Target** 경로가 큐에 있고 스키마·split 명세를 만족하는지 검사한다.
