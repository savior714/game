---
situation: 플랜 아카이브
# trigger: /archive  ← catalog metadata only; Read this file before executing (error_patterns §16.1)
level: Recommended
description: 완료된 docs/plans Blueprint를 archive로 이관하고 저장소 참조를 일괄 갱신
version: 1.0.0
last_updated: 2026-05-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# 완료 플랜 아카이브 워크플로우 (/archive)

진행이 끝난 **`docs/plans/*.md`** 를 **`docs/plans/archive/`** 로 옮기고, `docs/agent-context/memory/`, `docs/specs/`, `docs/knowledge/` 등에 흩어진 **동일 파일명 링크를 한 번에** `plans/archive/` 경로로 맞춥니다.

## 언제 쓰는가

- Blueprint·시장 비교 문서의 **Task/DoD가 모두 완료**되어 루트 `docs/plans/` 를 비우고 싶을 때
- 삭제 대신 **git 이력·경로 추적성**을 유지하고 싶을 때 (삭제는 참조 끊김 위험이 큼)

## 사전 조건

- 대상 파일이 **`docs/plans/` 루트**에 존재해야 함 (이미 `archive/` 에만 있으면 `unarchive` 또는 수동 복구).
- **끊긴 링크 점검**: 저장소 루트에서 `python3 scripts/archive_plans.py check` 실행
  - **성공 시**: "No broken links found" 메시지 확인 → 아카이브 진행
  - **실패 시**: 누락 파일 목록 확인 → 해당 파일을 먼저 정리하거나, 아카이브 후 `docs/plans/archive/README.md`를 통해 사용자에게 안내

## 실행 절차 (에이전트/휴먼 공통)

1. **이관할 파일명 확정** (예: `20260411_interop_hardening_blueprint.md`).
2. **[필수] 파일 위치 확인** — 이미 archive 에 있는 경우 중복 작업을 방지합니다.
   - `find docs/plans -name "<파일명>.md" 2>/dev/null` 실행
   - `docs/plans/archive/<카테고리>/<파일명>.md` → **이미 아카이브됨**, README 업데이트만
   - `docs/plans/<파일명>.md` → **루트에 있음**, 아카이브 진행
3. **[자동화] Phase 1 & 2: 구현 완결성 및 명세 역검증 (Pre-flight Hard Block)**
   - `archive_plans.py` 실행 시 자동으로 `plan_lint.py --archive-ready`가 호출되어 다음을 강제합니다:
     - 모든 `Task`의 `Status`가 `done`이어야 함
     - 각 `done` 태스크에 구체적인 `Conclusion`이 작성되어야 함
     - Blueprint 내에 `[관련 명세]` 또는 `docs/specs/` 링크가 반드시 포함되어야 함
   - 위 조건 위반 시 아카이브가 **즉시 중단(Exit 1)** 되며 파일이 이동하지 않습니다.
   - 에이전트는 아카이브 실패 메시지를 확인하고, 남은 Task 상태를 갱신하거나 누락된 명세 링크를 채운 후 다시 시도해야 합니다.
   - *참고:* 시스템 린트 외에도 회귀 테스트(`just verify`) 및 잔여 이슈 검증(`scripts/verify/check_residual_issues.py`)이 필요한 경우 사전에 실행하는 것을 권장합니다.
4. **[필수] Phase 3: 검증 결과 기록**
   - 아카이브 이동 전, 위 검증 결과를 Blueprint 하단에 `[아카이브 전 최종 검증 리포트]` 섹션으로 추가한다.
   - 리포트 포함 내용: 검증 일시, 검증자, 실행한 테스트 목록 및 결과, Specs 반영 여부.
4.5. **[권장] Phase 3.5: 로드맵 전방 제안 (steer) 및 ROADMAP changelog 자동 갱신**
   - 아카이브 성공 직후 `just plans-steer`가 `docs/plans/README.md` Recommended next 스냅샷을 갱신한다 (`archive_plans.py`가 1회 호출).
   - **[자동화] ROADMAP changelog 자동 갱신**: 아카이브 실행 시 `scripts/sync_roadmap_changelog.py append_from_archived_plan`이 Archived Blueprint Conclusion 을 읽어 `docs/plans/ROADMAP.md`의 `<!-- roadmap-changelog:v1 -->` 마커 아래 1행을 삽입한다 (`move.py` 훅에서 자동 호출).
   - 세션 HANDOFF·다음 구현 선택은 [`ROADMAP.md`](../../docs/plans/ROADMAP.md)(방향) + README 스냅샷 또는 `just plans-steer` stdout을 따른다(수동 추측 금지).
   - **[필수] 자연어 로드맵 동기화 (ROADMAP.md)**: 아카이브를 수행할 때 반드시 [`ROADMAP.md`](../../docs/plans/ROADMAP.md) 파일을 함께 열어 현재 개발 상황에 맞게 진행 단계(현재 집중 영역, 기대 효과 등)를 한국어 자연어로 갱신한다. (맥락 유지 목적 — )
5. **Dry-run 및 실행**
   - `python3 scripts/archive_plans.py archive --dry-run <파일명>`
   - `python3 scripts/archive_plans.py archive -- <파일명>`
6. **[자동화] 인덱스 및 정합성 갱신**
   - `just plans-index` 실행 (`archive_plans.py check`·`guard-deleted` 포함)
   - **Unified Sync (플랜 이동 전 1회)**: `archive` 명령이 **첫 플랜 파일 이동 전**에 **`just sync --check`와 동일한** `scripts/agent/sync.py --check`를 자동 실행한다 (code-lock 해시 + 스펙 역검증). FAIL이면 파일이 archive로 옮겨지지 않으며, Phase 2에서 누락된 `docs/specs/` 갱신 후 재실행한다. 문서화된 사유가 있을 때만 `--skip-unified-sync`(이동 전 검사도 생략)를 쓰고, **사후** `just sync --check`로 재검사한다.
   - 수동 점검: `just sync --check` → drift·후보 스펙 확인 → 필요 시 Phase 2 본문 갱신 → `archive` 재실행
7. **Git 반영**
   - `git add .` -> `git diff` 확인 -> `git commit -m "docs: archive completed plans with verification report"`

## 스크립트 동작 요약

| 명령 | 동작 |
|------|------|
| `check` | `docs/plans/` 및 `docs/plans/archive/` 어느 쪽에도 없는 `*.md` 를 가리키는 참조 나열 |
| `archive` | **이동 전** 루트 `.env`의 `LINEAR_API_KEY`로 `sync_engine.py --plan … --strict`를 실행해 Linear에 Task 상태를 반영(Done 등). 실패 시 **파일을 옮기지 않음**. 오프라인은 `--skip-linear-sync`. **첫 플랜 이동 전** `scripts/agent/sync.py --check`(= `just sync --check`, code-lock·스펙 역검증) 1회 — FAIL 시 exit ≠ 0·파일 유지. 이후 `docs/plans/X` → `docs/plans/archive/<분류>/X` 로 이동(분류 SSOT: `scripts/plan_archive_classify.py`)하고, 텍스트 내 `docs/plans/X`, `/plans/X` 형태를 `.../archive/<분류>/X` 로 치환. 완료 후 `archive/` 루트에 남은 `*.md`가 있으면 자동 `sweep`. 긴급·오프라인만 `--skip-unified-sync`(이동 전 검사 생략, 사후 `just sync --check` 권장) |
| `sweep` | `archive/` 루트에만 남은 `*.md`(README 제외)를 동일 분류 규칙으로 하위 폴더로 이동 + 참조 갱신 (수동 정리·레거시 보정용) |
| `unarchive` | `docs/plans/archive/**/X` → `docs/plans/X` 로 복구 (하위 폴더·루트 레거시 경로 모두 탐색) |
| `repair` | `docs/plans/<old>.md` 끊김 참조를 `archive/`·`docs/archive/plans/` SSOT 경로로 일괄 치환 (`PLAN_BASENAME_ALIASES` 리네임 포함) |
| `guard-deleted` | `git` 추적 중인 `docs/plans/archive/**/*.md` 가 워킹트리에서 삭제됐는지 감지 (`git restore docs/plans/archive/` 로 복구) |

치환 대상 확장자: `.md`, `.mdx`, `.mjs`, `.js`, `.ts`, `.tsx`, `.py`, `.html`, `.json`, `.yml`, `.yaml` (제외 디렉터리: `.git/`, `.venv/`, `node_modules/`, `dist/`, `build/`).

## MEMORY Anti-Drift

- [memory_hygiene.md](../core/memory_hygiene.md) 1.1절 — `docs/agent-context/memory/MEMORY.md` 에 장문 절차를 넣지 말고, **이 파일(워크플로우) + `docs/plans/archive/README.md`** 로만 링크합니다.

## 자동화 (Shell Alias)

`.zshrc`에 `archive()` 함수가 정의되어 있음. 이 함수는 아카이브 후 자동으로 `just plans-index`를 실행한다.

```bash
# 사용법
archive PLAN1.md [PLAN2.md ...]

# 예시
archive PLAN_HAPI_FHIR_DOCKER_STABILIZATION.md PHASE2_chain_execution.md
```

## SSOT

- **아카이브 폴더 안내**: [`docs/plans/archive/README.md`](../../docs/plans/archive/README.md) - 아카이브된 플랜 목록, 아카이브 날짜, 관련 이슈/PR 링크
- **구현**: [`scripts/archive_plans.py`](../../scripts/archive_plans.py) - 파일 이동 + 링크 치환 + 누락 링크 점검 + **플랜 이동 전 unified sync 1회**
- **Unified Sync**: [sync.md](sync.md) · `just sync` · `just archive-plan` (아카이브 + `plans-index`)

## 누적 방지 (Anti-drift)

| 계층 | 명령 | 시점 |
| :--- | :--- | :--- |
| 커밋 | `archive_plans.py guard-deleted` + `check` | `.husky/pre-commit` (자동) |
| 인덱스 | `just plans-index` | 아카이브 직후·주기적 (`guard-deleted` + `check` 포함) |
| 레거시 누적 청소 | `python3 scripts/archive_plans.py repair` | `check` 실패 시 1회성 일괄 치환 |
| 워킹트리 삭제 | `git restore docs/plans/archive/` | `guard-deleted` FAIL 시 **삭제 커밋 금지** — archive 파일은 삭제하지 말고 이동·아카이브만 |

`check`는 `docs/plans/`·`docs/plans/archive/`·`docs/archive/plans/` 및 `PLAN_BASENAME_ALIASES` 를 SSOT로 본다. 단위 테스트용 경로는 `tests/fixtures/plans/` (스캔 대상 아님).

## 리스크 및 주의사항

- **작업 전 확인**: 아카이브 전에 `git status`를 확인하고, 작업 중인 변경사항이 있다면 먼저 커밋하거나 stash 해주세요
- **archive 물리 삭제 금지**: `docs/plans/archive/` 아래 추적 파일을 로컬에서 지우면 링크·`find_archived_plan` 이 동시에 깨진다. 정리는 `archive`/`sweep`/`repair` 만 사용한다.
- **병렬 작업 금지**: 아카이브 작업 중에는 다른 사람이 docs/plans/를 수정하지 않도록 혼선 방지
- **MEMORY.md 갱신**: 이 워크플로우 파일만 링크하고, `docs/agent-context/memory/MEMORY.md`는 갱신하지 않음
- **복구 가능성**: `unarchive` 명령으로 아카이브를 취소할 수 있으나, 아카이브 후 다른 사람이 수정한 내용이 있다면 충돌 가능성 있음
- **PR 생성 금지**: 1인 개발자이므로 아카이브 변경사항은 직접 커밋만 한다. `git push` 후 PR 생성하지 않음
