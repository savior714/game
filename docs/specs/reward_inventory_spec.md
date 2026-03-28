# 전역 보상·보석 시스템 명세 (Reward & Gem Inventory Spec)

**최종 수정**: 2026-03-29  

이 문서는 모든 학습 페이지에서 공통으로 사용되는 **보석 화폐**, **교환 인벤토리**, **상점 UI**의 기술적 사양을 정의한다. 룰렛 기반 확정 보상은 **폐기**되었으며, `docs/CRITICAL_LOGIC.md` §16과 본 문서가 SSOT이다.

## 1. 저장소 (Storage)

- **키**: `localStorage`의 `study_rewards`
- **동기화**: `RewardSystem.save()` 시 `window.SyncEngine`이 있으면 `SyncEngine.pushStats('study_rewards', state)`로 큐잉(오프라인·병합은 `global/sync-engine.js`).

## 2. 데이터 구조 (Data Schema)

`global/reward.js`의 `initialState`와 병합 로드를 따른다.

```json
{
  "gems": 0,
  "youtube_minutes": 0,
  "snacks": 0,
  "marble_plays": 0,
  "shop_items": [
    { "id": "youtube", "icon": "📺", "label": "유튜브 15분", "desc": "…", "price": 1 },
    { "id": "snack", "icon": "🍪", "label": "간식 1개", "desc": "…", "price": 1 },
    { "id": "marble", "icon": "🎮", "label": "마블 게임", "desc": "…", "price": 1 }
  ],
  "custom_inventory": {},
  "theme": "modern",
  "last_updated": "ISO-8601",
  "_updated_at": 0
}
```

- **gems**: 로켓 20연속 정답(`LAUNCH_STREAK`) 시 1개씩 증가하는 화폐.
- **youtube_minutes / snacks / marble_plays**: 상점에서 보석으로 교환한 뒤 쌓이는 **사용권·잔량**(분/개/회).
- **shop_items**: 기본 고정 상점 + 보호자 커스텀 항목(가격은 보석 단위).
- **custom_inventory**: 커스텀 상품 ID별 잔여 횟수.

## 3. 핵심 API (`RewardSystem`, `global/reward.js`)

- `load()` / `save()`: 로컬 영속화 및 UI·동기화 트리거.
- `add(type, amount)`: `gems` | `youtube` | `snack` | `marble` 또는 커스텀 ID.
- `has(type, amount)` / `consume(type)`: 보유 확인 후 차감; 유튜브·간식·마블은 각 모달로 이어짐.
- 테마: `setTheme` — 저장 후 필요 시 전체 새로고침.

UI 갱신·모달·보상바 레이아웃 변수(`--reward-bar-height` 등)는 **`global/reward_ui.js`**가 담당한다.

## 4. 획득 규칙 (Gem Grant)

- **트리거**: 전 과목 공통, 연속 정답 `streak === LAUNCH_STREAK(20)` 도달 시 로켓 발사 직후.
- **지급**: 보석 **1개** 확정 (`add('gems', 1)`). 랜덤 룰렛 없음.

## 5. UI/UX (보상 바 · 상점)

- **보상 바**: 상단 고정 영역; 항목별 **고정 너비·간격·단위(개/분/회)** 로 정렬(`docs/CRITICAL_LOGIC.md` §18).
- **재고 0 표시**: `shop_items`에 등록된 비보석 항목은 **보유량이 0이어도** 바에 슬롯을 표시한다(시각적으로는 `empty-slot` 등으로 보석·보유량 있는 칸과 구분). 클릭 시 기존처럼 “보유 중인 보상이 없습니다” 흐름을 유지할 수 있다.
- **바 DOM 동기화**: `study_rewards`의 `shop_items` 배열이 바뀌면(항목 추가·삭제·메타 변경) `RewardSystemUI.syncInventoryBarWithState`가 상단 바를 재구성하여 슬롯과 `shop_items`가 일치하도록 한다. `RewardSystem.save()`·`cloud-sync-complete` 후 갱신 경로에서 호출된다.
- **상점**: 보석 클릭 또는 지정 진입점으로 모달 오픈 → `shop_items` 항목을 보석 가격에 구매 → 인벤토리 필드 증가.
- **유튜브**: 누적 **분**만 표시; 별도 강제 타이머 없이 부모 확인용(§4 구버전 정책과 동일 취지).

## 6. 보호자 커스텀 상점

- **진입**: `guardian/index.html` (구글 로그인·연동 환경 전제).
- 보호자가 등록한 보상은 `shop_items` 및 `custom_inventory`와 연동되며, 잔여 회수 로직은 구현체(`reward.js`)를 따른다.
- **편집**: 기본 프리셋(`youtube` / `snack` / `marble`)을 포함한 각 행에서 **아이콘·이름·설명·가격**을 편집할 수 있다. 내부 **id는 변경하지 않는다**(인벤토리 필드와의 매핑 유지).

## 7. 디자인 원칙 (Anti-Slop)

천편일률적인 AI 템플릿 스타일을 지양하고, 아동 친화적 질감·타이포·상호작용을 유지한다(`docs/specs/slop_workflow_spec.md` 참고).
