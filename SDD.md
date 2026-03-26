# SDD: 어린이 학습 게임 플랫폼

**버전**: 1.3
**작성일**: 2026-03-21 / **최종 수정**: 2026-03-22

---

## 게임 현황

| 폴더 | 과목 | 상태 | 스펙 |
|------|------|------|------|
| `math/` | 수학 (덧셈·뺄셈·곱셈) | ✅ 완성 | [specs/math.md](specs/math.md) |
| `english/` | 영어 (단어·문장) | ✅ 완성 | [specs/english.md](specs/english.md) |
| `korean/` | 국어 (받침·맞춤법·어휘) | ✅ 완성 | [specs/korean.md](specs/korean.md) |
| `science/` | 과학 (분류·개념) | 🔲 계획 중 | [specs/science.md](specs/science.md) |

---

## 스펙 문서

| 파일 | 내용 |
|------|------|
| [specs/platform.md](specs/platform.md) | 공통 아키텍처, 공통 시스템, 공통 UI 컴포넌트 |
| [specs/math.md](specs/math.md) | 수학 게임 — 개요, 상세 로직, 상수, 함수 목록 |
| [specs/english.md](specs/english.md) | 영어 게임 — 문제 유형, 단어 DB, 보기 생성, 강화학습 |
| [specs/korean.md](specs/korean.md) | 국어 게임 — 문제 유형 및 카테고리, 통계 스키마 |
| [specs/science.md](specs/science.md) | 과학 게임 — 문제 유형 (안), 통계 스키마 (계획) |

---

## 신규 게임 추가 절차

1. `specs/{subject}.md` 작성 (개요 / 문제 유형 / 난이도 기준 / 데이터 스키마)
2. 위 게임 현황 테이블 상태 최신화
3. `{subject}/` 폴더에 6파일 구현 — 상세 절차는 [specs/platform.md §0.7](specs/platform.md) 참조
