# Ocean Rescue 개발 동결 공통 공지

- **상태:** `PAUSED_REFERENCE_ONLY`
- **발효일:** 2026-08-06
- **현재 실행 권위:** `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`
- **적용 범위:** Ocean Rescue product·rendering·architecture·asset handoff 문서

## 1. 목적

Ocean Rescue 관련 spec은 이미 확정된 제품·렌더링·개발 구조·asset handoff 계약을 보존한다. 문서 내부의 `IMPLEMENTATION_READY`, `CANONICAL`, `locked`, `production readiness` 같은 표시는 해당 문서의 **내부 계약 성숙도**를 뜻하며 현재 저장소의 실행 우선순위나 자동 재개 지시가 아니다.

현재 최우선 목표는 Math, English, Korean, Science 일반 문제풀이 신뢰성 안정화다. 네 과목의 exit gate가 닫히기 전에는 Ocean Rescue 신규 기능·콘텐츠·렌더링 개선·typed ownership 이전·asset 제작·migration을 시작하지 않는다.

## 2. 적용 문서

| 문서 | 보존되는 계약 | 현재 실행 상태 |
|---|---|---|
| [`AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`](product/AIDENGAME_OCEAN_RESCUE_MVP_PRD.md) | MVP 사용자 흐름, mission, progression, safety·accessibility 제품 계약 | 동결 참고 |
| [`AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`](product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md) | PixiJS, visual slice, atlas, renderer fallback, rendering acceptance | 동결 참고 |
| [`AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md`](technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md) | authoring source, build-time tooling, runtime·artifact 경계 | 동결 참고 |
| [`AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`](technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md) | manual SVG source, validation, approval, atlas handoff 계약 | 동결 참고 |

문서 본문을 과거 기록으로 폐기한 것은 아니다. 재개 시 제품·기술 acceptance의 출발점으로 사용하되 최신 main의 code, tests, build config, generated artifact와 drift를 먼저 확인한다.

## 3. 현재 금지 범위

사용자의 현재 명시적 방향 변경이 없으면 다음을 시작하지 않는다.

- 신규 mission, rescue mechanic, progression 또는 reward
- 신규 rendering slice, character animation, visual effect 또는 scene expansion
- 추가 TypeScript·ESM controller ownership 이전
- PixiJS·Vite·TypeScript·pnpm toolchain upgrade
- production artifact cutover 또는 legacy rollback 제거
- 신규 SVG/cutout/atlas production asset 제작
- 과거 plan의 next WP 재개
- 문서의 내부 status를 근거로 local LLM 구현 프롬프트 발행

## 4. 허용 예외

다음 문제가 최신 main 또는 현재 production에서 실제로 재현될 때만 독립 failure domain으로 수정할 수 있다.

- 배포 entry가 열리지 않음
- 사용자가 기존 rescue flow를 진행할 수 없는 치명적 회귀
- source, build metadata, tracked artifact의 명확한 drift
- rollback 불능
- 데이터 손상
- 보안 또는 credential 노출
- 일반 과목 변경이 Ocean Rescue 운영 entry를 직접 깨뜨림

예외 수정은 재현된 원인 하나에 한정하며 신규 feature나 장기 migration으로 확장하지 않는다.

## 5. 재개 절차

Ocean Rescue가 다시 우선순위로 선택되면 문서의 과거 implementation sequence나 next WP를 그대로 실행하지 않는다.

1. 사용자가 현재 요청에서 재개 범위를 명시하거나 일반 과목 안정화 exit 이후 우선순위를 다시 결정한다.
2. 최신 `origin/main`의 runtime entry, import graph, build config, lockfile, artifact를 확인한다.
3. 네 문서의 stable contract와 현재 code/test/config를 claim 단위로 비교한다.
4. `MATCH`, `DOC_STALE`, `IMPLEMENTATION_VIOLATION`, `UNVERIFIED`로 분류한다.
5. 첫 failure domain과 binary criterion 하나를 선택한다.
6. source·caller·test·cleanup을 최소 범위로 수정한다.
7. 필요한 typecheck, browser, build, artifact, rollback 검증을 직접 위험에 맞게 실행한다.
8. 게시 후 최신 main에서 다음 원인을 새로 선택한다.

## 6. 우선순위 해석 규칙

- `IMPLEMENTATION_READY` ≠ 지금 구현 시작
- `CANONICAL` ≠ 현재 제품 최우선
- `locked` ≠ 최신 code와 drift 확인 불필요
- `production readiness pending` ≠ 현재 asset 작업 요청
- 과거 migration plan의 단계 ≠ 현재 next work

현재 실행 우선순위는 항상 다음 순서를 따른다.

1. 사용자의 현재 요청
2. `AGENTS.md`
3. `PROJECT_RULES.md`와 가장 가까운 active product/technical spec
4. 최신 `origin/main`의 code, tests, config

## 7. 검증

이 공지와 문서 색인은 다음을 검증한다.

- 적용 대상 네 문서가 실제로 존재함
- 네 문서가 색인에 빠짐없이 분류됨
- 내부 성숙도 라벨과 실행 우선순위가 분리됨
- 재개 조건과 허용 예외가 현재 `AGENTS.md`·`PROJECT_RULES.md`와 일치함
- 과거 plan이나 internal status가 자동 실행 지시로 사용되지 않음

관련 focused test:

```bash
uv run pytest -q tests/test_ocean_rescue_spec_freeze_classification.py
```

이 공지는 Ocean Rescue product contract가 변경되거나 현재 동결 정책이 해제될 때만 수정한다.
