# 과학 게임 스펙

**소속**: SDD — 어린이 학습 게임 플랫폼
**상태**: 🔲 계획 중 | **대상**: 초등 저학년
**최종 수정**: 2026-03-22

---

## 1. 개요

과학 초등 저학년의 과학 개념(분류·특징·개념 O/X)을 게임 형태로 훈련하는 애플리케이션.
공통 플랫폼 아키텍처(로켓 스트릭, 적응형 난이도, 강화학습, 중복 방지)를 그대로 상속한다.
- **중복 방지**: 최근 10문제를 기억하여 연속 출제 차단 (`RECENT_LIMIT=10`)

---

## 2. 문제 유형 (안)

| 유형 | 설명 | 예시 |
|------|------|------|
| 분류 | 동물/식물/무생물 분류 | `장미` → 식물 |
| 개념 | 과학 개념 O/X | 태양은 별이다 → O |
| 특징 | 사진(이모지) 보고 이름 맞히기 | 🦋 → 나비 |

---

## 3. 통계 스키마 (안)

**Key**: `scienceGameStats`

**카테고리 (안)**: `animals`, `plants`, `weather`, `space`, `body`

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

> 구현 시작 전 이 파일을 먼저 완성하고 `SDD.md` 게임 현황 테이블을 갱신한다.
> 개발 체크리스트는 [specs/platform.md](platform.md) §0.7 참조.
