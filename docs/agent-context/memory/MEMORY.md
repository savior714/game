---
id: MEMORY
type: MEM
status: active
last_verified: 2026-08-16
---

# Memory

**Product SSOT:** `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`

## Current direction

- 제품 목표는 초등 저학년 아이가 Galaxy Tab에서 자발적으로 매일 학습하고 실제 skill mastery를 높인 뒤 게임/현실 보상을 얻는 local-first 학습 게임 플랫폼이다.
- 성공 우선순위는 `자발적 진입 > 독립 사용 > 실제 학습 성취`다.
- 현재 기본 개발 priority는 **Math curriculum skill → mastery → adaptive daily goal** vertical slice다.
- Core Quiz 4과목 reliability stabilization은 완료된 baseline이며 같은 결함이 재현될 때만 회귀로 다시 다룬다.
- Ocean Rescue는 active reward game이다. 학습 문제를 게임 안에 삽입하지 않고, 학습 goal 완료 후 free-time으로 접근한다.
- Space Explorer는 `PAUSED_REFERENCE_ONLY`다.

## Product boundaries

- 세부 skill mastery를 사용하고, 초기 알고리즘은 deterministic/explainable하게 시작한다.
- correctness, attempts/first-try, response time, practiced time 같은 raw learning evidence를 보존한다.
- adaptive selection은 약점 개선 + 숙달 skill spaced review + 성공 경험의 균형을 목표로 한다.
- 아이에게 mastery percentage를 노출하지 않고, 보호자에게 약점/성장을 자세히 보여준다.
- LLM은 콘텐츠 제작 보조까지만 허용한다. runtime 문제 생성·mastery·next-question 판단에는 사용하지 않는다.
- game layer는 gems/streak/collection/unlock/현실 보상까지 허용하지만 RPG식 level/stat/quest/meta progression은 비목표다.
- persistence는 local-first + export/import backup을 먼저 한다. backend/cloud sync는 현재 필수가 아니다.
- 기준 기기는 Galaxy Tab S10급이며 landscape-first지만 portrait/split-screen/resize에서 핵심 흐름이 깨지지 않아야 한다.

## Verified baseline

- `shared/domain/progress-engine.js`에는 과목/level별 attempts, correct, totalTime, weakness tag와 최근 정답 흐름 기반 난이도 계산이 이미 존재한다. 새 mastery 작업은 이를 무조건 폐기하지 않고 현재 ownership과 migration boundary를 먼저 확인한다.
- `shared/domain/free-time-session.js`에는 독립적인 자유시간 세션 모델이 이미 존재한다. 학습→자유시간 integration에서 새 타이머 모델을 중복 만들지 않는다.
- Math, English, Korean, Science의 핵심 quiz journey reliability stabilization은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`에 완료 계약으로 보존된다.

## Next execution boundary

첫 구현 작업은 Math만 대상으로 한다.

1. 현행 Math 문제/문제 metadata와 현재 curriculum 관련 구조를 read-only inventory한다.
2. 실제 현재 문제를 표현하는 최소 `skillId` 집합을 현행 초등 교육과정과 대조해 제안한다.
3. 처음부터 네 과목 taxonomy를 만들지 않는다.
4. 기존 `ProgressEngine`의 raw evidence 보존/호환 경계를 확인한 뒤 skill mastery v1의 가장 작은 vertical slice를 선택한다.

한 작업에서는 skill taxonomy 전체 + mastery engine + daily goal + reward integration을 동시에 구현하지 않는다.

## Verify

```bash
uv run pytest -q tests/test_active_product_scope_policy.py
```
