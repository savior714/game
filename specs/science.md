# 과학 게임 스펙

**소속**: SDD — 어린이 학습 게임 플랫폼  
**상태**: ✅ 완성 | **대상**: 초등 저학년  
**최종 수정**: 2026-03-29

---

## 1. 개요

과학 초등 저학년의 과학 개념(분류·특징·개념 O/X)을 게임 형태로 훈련하는 애플리케이션.  
공통 플랫폼 아키텍처(로켓 스트릭, 그물망, 적응형 난이도, 강화학습, 중복 방지)를 상속하며, 로켓·진행·UI는 `common/` 코어에 위임한다.

- **중복 방지**: 최근 10문제를 기억하여 연속 출제 차단 (`RECENT_LIMIT=10`)
- **데이터 품질**: 동음이의어·중의성 차단 규칙은 `docs/CRITICAL_LOGIC.md` §13–14 및 `science/verify_science_engine.js` 참고

---

## 2. 문제 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| 분류 | 동물/식물/무생물 분류 | `장미` → 식물 |
| 개념 | 과학 개념 O/X | 태양은 별이다 → O |
| 특징 | 이모지·그림 보고 이름 맞히기 | 🦋 → 나비 |

난이도별 선택지 개수(예: 3지·4지선다)는 `science/engine.js` 및 플랫폼 §중복 방지·유일 정답 원칙을 따른다.

---

## 3. 통계 스키마

**Key**: `scienceGameStats`

**카테고리 예시**: `animals`, `plants`, `weather`, `space`, `body` (구현 데이터와 일치)

```json
{
  "animals": { "attempts": 0, "correct": 0, "totalTime": 0 },
  "plants":  { "attempts": 0, "correct": 0, "totalTime": 0 },
  "weather": { "attempts": 0, "correct": 0, "totalTime": 0 },
  "space":   { "attempts": 0, "correct": 0, "totalTime": 0 },
  "body":    { "attempts": 0, "correct": 0, "totalTime": 0 }
}
```

---

## 4. 스트릭 보상 및 전역 보상

20연속 정답(`LAUNCH_STREAK=20`) 시 로켓 발사와 함께 **보석 💎 1개**가 지급되며, 유튜브·간식·마블 등은 `global/reward.js` 상점에서 보석으로 교환한다. (룰렛 UI는 사용하지 않음.)

상세 규칙: `docs/CRITICAL_LOGIC.md` §16, [docs/specs/reward_inventory_spec.md](../docs/specs/reward_inventory_spec.md).

---

## 5. 관련 문서

- DB·시드 구조: [docs/specs/science_db_spec.md](../docs/specs/science_db_spec.md) (해당하는 경우)
- 개발 체크리스트: [specs/platform.md](platform.md) §0.7
