# 국어 게임 스펙

**소속**: SDD — 어린이 학습 게임 플랫폼
**상태**: 🔲 계획 중 | **대상**: 초등 저학년
**최종 수정**: 2026-03-22

---

## 1. 개요

초등 저학년의 국어 능력(받침·맞춤법·어휘)을 게임 형태로 훈련하는 애플리케이션.
공통 플랫폼 아키텍처(로켓 스트릭, 적응형 난이도, 강화학습)를 그대로 상속한다.

---

## 2. 문제 유형 (안)

| 유형 | 설명 | 예시 |
|------|------|------|
| 받침 완성 | 올바른 받침 선택 | `나무` vs `나뭇` |
| 맞춤법 | 맞게 쓴 것 고르기 | `돼요` vs `되요` |
| 반대말 | 반의어 선택 | `크다` → `작다` |
| 높임말 | 문장 높임 변환 | `먹어` → `드세요` |

---

## 3. 통계 스키마 (안)

**Key**: `koreanGameStats`

**카테고리 (안)**: `spelling`, `antonym`, `honorific`, `punctuation`

```json
{
  "spelling":    { "attempts": 0, "correct": 0, "totalTime": 0 },
  "antonym":     { "attempts": 0, "correct": 0, "totalTime": 0 },
  "honorific":   { "attempts": 0, "correct": 0, "totalTime": 0 },
  "punctuation": { "attempts": 0, "correct": 0, "totalTime": 0 }
}
```

---

> 구현 시작 전 이 파일을 먼저 완성하고 `SDD.md` 게임 현황 테이블을 갱신한다.
> 개발 체크리스트는 [specs/platform.md](platform.md) §0.7 참조.
