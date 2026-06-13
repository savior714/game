# Discover Loop 갈래 분리 패턴 (Impact / Hygiene Split)

## 개요

단일 큐(`debt_backlog_pilot.json`)를 **impact**와 **hygiene** 두 갈래로 분리하여, 사용자가 실서비스 개선과 코드 청소를 별도 작업 목록으로 받도록 하는 아키텍처 변경.

## 핵심 설계

### 1. 경로 분류 SSOT (`lane_filter.py`)

모든 seed/dead-seed/emit 문서가 동일 규칙을 참조하는 단일 진실 공급원.

```
impact  = src/, apps/*/src/, apps/renderer/e2e/, tests/api/, tests/infrastructure/
hygiene = tests/unit/, apps/*/tests/unit/, scripts/
exclude = docs/, docs/reports/ (양 갈래 공통)
```

**구현 패턴**:
- `DiscoverLane` enum (impact, hygiene)
- `lane_for_backlog_path(path)` — 백로그 경로 분류
- `lane_for_dead_code_path(path)` — dead-code 경로 분류
- `is_excluded_path(path)` — 제외 경로 체크

### 2. 큐 파일 분리

| 갈래 | 큐 파일 | Pointer 파일 |
| :--- | :--- | :--- |
| impact | `artifacts/discover/impact_pilot.json` | `latest_impact_implement_plan.txt` |
| hygiene | `artifacts/discover/hygiene_pilot.json` | `latest_hygiene_implement_plan.txt` |

### 3. CLI 인터페이스

```bash
# impact 갈래 시드 (백로그 → impact_pilot.json)
just discover-seed --lane impact --limit 10

# hygiene 갈래 시드 (ruff+vulture → hygiene_pilot.json)
just discover-dead-seed
# 또는
just discover-seed --lane hygiene --limit 10

# 갈래별 emit
just discover-emit --queue artifacts/discover/impact_pilot.json
just discover-emit --queue artifacts/discover/hygiene_pilot.json
```

## 구현 체크리스트

- [ ] `lane_filter.py`에 DiscoverLane enum + 3개 분류 함수
- [ ] `discover_seed.py`에 `--lane {impact,hygiene}` 인자 + 큐 경로 분기
- [ ] `discover_dead_seed.py` DEFAULT_QUEUE → `hygiene_pilot.json`
- [ ] `emit_implement_blueprint.py`에 `write_lane_pointer()` 함수 (queue stem 기반 분기)
- [ ] SKILL.md 메뉴를 impact/hygiene 2갈래로 교체, (권장) 태그 제거
- [ ] discover.md 워크플로에 `--lane` 사용법 반영

## TDD 검증 패턴

각 기능별 테스트 파일:
- `test_lane_filter.py` — enum, 분류 함수, exclude 패턴 (20+ 케이스)
- `test_discover_seed.py` — `--lane impact/hygiene` dry-run 경로 필터링
- `test_discover_dead_seed.py` — DEFAULT_QUEUE = hygiene_pilot.json
- `test_discover_emit_lane.py` — 갈래별 pointer 파일 생성/미생성
- `test_discover_lane_integration.py` — subprocess 기반 end-to-end dry-run

## 함정

- **TDD 게이트**: 새 파일 생성 시 `uv run pytest --tdd-gate off` 필요 (기존 미수정 코드가 git diff에 있어 NO_TEST_DIFF 차단)
- **emit pointer**: `write_lane_pointer()`는 queue stem(`impact`/`hygiene`) 기반 분기. 알 수 없는 큐명은 legacy pointer로 폴백.
- **hygiene 시드**: dead-code 시드는 항상 hygiene 갈래에 추가. `discover-seed --lane hygiene`도 가능하지만 백로그 기반.
