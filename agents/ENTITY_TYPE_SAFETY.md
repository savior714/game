# Entity & Type Safety Contract

이 문서는 AidenGame의 durable entity/type-safety 계약이다. 현재 작업 큐, 완료 이력, SHA 같은 transient execution state는 기록하지 않는다. 실행 정책은 `AGENTS.md`와 `PROJECT_RULES.md`, 검증 전략은 기존 RDV 계약을 따른다.

## 1. 핵심 원칙

- Runtime Entity / Value Object와 asset manifest, save/load payload, UI view model, generated artifact representation을 같은 타입으로 사용하지 않는다. boundary representation은 명시적 mapping을 거쳐 runtime/domain state로 승격한다.
- entity/state를 생성·복원·load하는 모든 경로에서 핵심 invariant가 성립해야 한다. 이미 저장되었거나 manifest에 존재한다는 이유만으로 runtime-valid하다고 가정하지 않는다.
- 의미가 다른 ID와 값은 실제 혼동 위험이 있으면 branded/nominal type 또는 Value Object로 구분한다. 타입 수 증가 자체는 목적이 아니다.
- 서로 배타적인 게임 상태는 여러 boolean/nullable flag 조합보다 discriminated union 또는 명시적 FSM transition으로 표현한다.
- JSON, local storage/save data, asset manifest, atlas metadata, generated provenance, browser/worker message 등 trust boundary의 값은 runtime entity로 직접 cast하지 않는다. raw/`unknown`에서 검증 후 변환한다.
- `null`, `undefined`, property absence의 의미를 섞지 않는다. TypeScript 영역에서는 `strict` 계약을 유지하고 실제 invalid state 탐지 가치가 있는 경우 `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`의 의미를 보존한다.
- `Partial<Entity>`를 일반 update API로 사용하지 않는다. 의미 있는 action/command/transition input으로 변경 범위를 드러낸다.
- `as Entity`, `as unknown as Entity`, `any`, 불필요한 non-null assertion(`!`)은 타입 우회 신호다. 검증된 adapter boundary 등 좁은 예외 외에는 제거하고, 구조 적합성 확인에는 `satisfies` 같은 수단을 선호한다.

## 2. AidenGame 적용

- `PlayerId`, `EntityId`, `InventoryItemId`, `QuestId`, `RewardId`, `SceneId`, `AssetId` 등 서로 다른 identity를 plain string 하나로 확산시키지 않는다. 실제 caller 혼동 가능성이 있는 owner부터 순차 적용한다.
- Player / world entity / inventory / quest / reward 같은 runtime state와 JSON/asset/save representation을 분리한다.
- quiz/game FSM의 `idle`, `question`, `feedback`, `completed`, `restarting` 등 상호 배타적 상태를 boolean soup으로 표현하지 않는다. 특정 상태에서만 필요한 데이터는 해당 variant 안에 둔다.
- restart, wrong→next, session completion처럼 상태 초기화 의미가 중요한 transition은 임의 field mutation보다 명시적 transition owner가 책임지게 한다.
- atlas/manifest/contact-sheet/provenance 등 asset pipeline의 authoring input, validated manifest, generated artifact를 동일한 신뢰 수준으로 취급하지 않는다. validator를 통과한 representation만 downstream runtime/build 단계에 승격한다.
- generated artifact가 존재한다는 사실은 source/manifest invariant의 증명이 아니다. load/build boundary에서 필요한 구조·reference·provenance 계약을 별도로 검증한다.

## 3. 작업 단위와 판정 기준

타입 안정성을 이유로 여러 게임·asset subsystem을 한꺼번에 리팩터링하지 않는다.

- 한 작업 = 한 failure domain = 한 제거 대상 invalid state = 한 primary criterion.
- 수정 전 해당 invalid state가 현재 타입/상태 모델에서 실제로 표현 가능한지 재현하거나 구조적으로 증명한다.
- 수정은 그 state의 owner와 직접 mapping/boundary까지만 coherent하게 수행한다.
- focused compile/type/runtime verification으로 해당 criterion을 독립 검증한 뒤 다음 finding으로 이동한다.

좋은 criterion 예시:

- `SceneId`가 필요한 runtime owner에 `AssetId`를 전달하는 코드는 compile되지 않는다.
- `feedback` 상태는 현재 문제와 판정 결과 없이 표현될 수 없다.
- 검증되지 않은 asset manifest는 validated runtime asset descriptor로 직접 승격될 수 없다.
- restart transition 후 이전 session의 score/question-local state가 유효한 새 session state로 남을 수 없다.

## 4. 문서화 경계

이 문서에는 entity ownership, state invariant, representation mapping, trust-boundary validation처럼 장기 유효한 계약만 유지한다. ACTIVE/NEXT, 현재 SHA, 임시 발견, 일회성 검증 로그는 기록하지 않는다.
