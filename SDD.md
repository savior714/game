# SDD: 어린이 학습 게임 플랫폼

**버전**: 1.5  
**작성일**: 2026-03-21 / **최종 수정**: 2026-04-02

---

## 게임 현황

| 폴더 | 과목·역할 | 상태 | 스펙 |
|------|-----------|------|------|
| `math/` | 수학 (덧셈·뺄셈·곱셈) | ✅ 완성 | [specs/math.md](specs/math.md) |
| `english/` | 영어 (단어·문장) | ✅ 완성 | [specs/english.md](specs/english.md) |
| `korean/` | 국어 (받침·맞춤법·어휘) | ✅ 완성 | [specs/korean.md](specs/korean.md) |
| `science/` | 과학 (분류·개념) | ✅ 완성 | [specs/science.md](specs/science.md) |
| `marble/` | 마블 머지 (보상 소비) | ✅ 완성 | [docs/specs/marble_drop.md](docs/specs/marble_drop.md) 등 |
| `global/` | 보상·인증·동기화 | ✅ | [docs/specs/reward_inventory_spec.md](docs/specs/reward_inventory_spec.md), `README.md` |

---

## 스펙 문서

| 파일 | 내용 |
|------|------|
| [specs/platform.md](specs/platform.md) | 공통 아키텍처, 공통 시스템, 공통 UI, 전역 보상·동기화 개요 |
| [specs/math.md](specs/math.md) | 수학 게임 — 개요, 상세 로직, 상수, 함수 목록 |
| [specs/english.md](specs/english.md) | 영어 게임 — 문제 유형, 단어 DB, 보기 생성, 강화학습 |
| [specs/korean.md](specs/korean.md) | 국어 게임 — 문제 유형 및 카테고리, 통계 스키마, 보상(보석) |
| [specs/science.md](specs/science.md) | 과학 게임 — 문제 유형, 통계 스키마 |
| [docs/specs/shared_core_refactor_spec.md](docs/specs/shared_core_refactor_spec.md) | `common/*` 코어 위임 계약 |
| [docs/specs/reward_inventory_spec.md](docs/specs/reward_inventory_spec.md) | 전역 보석·인벤토리·상점 데이터 명세 |
| [docs/CRITICAL_LOGIC.md](docs/CRITICAL_LOGIC.md) | 난이도·그물망·보석·관리자 등 운영 규칙 SSOT |

---

## 문서 SSOT 경계

| 문서 | 역할 |
|------|------|
| `PROJECT_RULES.md` | 프로젝트 규칙/운영 SSOT |
| `docs/CRITICAL_LOGIC.md` | 핵심 결정/불변 정책 SSOT |
| `docs/specs/`, `specs/` | 요구사항/계약 SSOT |
| `docs/memory/MEMORY.md` | 세션 지식 인덱스 SSOT |
| `docs/memory.md` | 레거시 포인터(하위 호환) |

---

## 신규 게임 추가 절차

1. `specs/{subject}.md` 작성 (개요 / 문제 유형 / 난이도 기준 / 데이터 스키마)
2. 위 게임 현황 테이블 상태 최신화
3. `{subject}/` 폴더에 6파일 구현 — 상세 절차는 [specs/platform.md §0.7](specs/platform.md) 참조
4. `common/` 코어 위임 패턴을 기존 과목과 동일하게 맞추고 `node verify_all.js`로 검증
