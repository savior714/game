---
status: handed-off
created: 2026-06-14
scope: domains/english — 쇼핑 대화문 20개 템플릿 추가
linked_plan: docs/plans/archive/games/PLAN_english_shopping_dialogues.md
pending_ask: null
---
<!-- Language: ko -->

# DISCUSS: 영어 게임 쇼핑 대화문 추가

## 1. 현황 요약
- **이번 discuss에서 끝까지:** 영어 게임에 쇼핑 대화문 20개 템플릿을 추가해 단어 암기를 넘어 실제 사용 능력 기르기.
- 현재 영어 게임은 550+ 단어, 16 카테고리, 5가지 문제 유형 (한국어→영어, 철자, 유사단어, 문장빈칸, 직접입력)
- 문장빈칸 유형이 존재하지만 일상 대화문은 없음

## 2. 진행 중 결정 (누적)
- [확정] 방향: 문맥 학습 — 문장/대화 확장
- [확정] 유형: 상황 대화문 — 2~3줄 짧은 대화에서 빈칸 채우기
- [확정] 상황: 5대 일상 생활 (쇼핑/식사/여행/병원/학교)
- [확정] 시작 범위: 쇼핑 카테고리부터
- [확정] 형식: 2줄 대화 — 판매원 한 줄, 학습자 빈칸 한 줄
- [확정] UI: 기존 문장빈칸 UI 재사용 — 별도 UI 개발 없음
- [확정] 데이터 위치: advanced-questions.js에 SHOP_DIALOGUES 상수 추가
- [확정] 정답 방식: 단어 빈칸 — 기존 makeWordChoices 재사용
- [확정] 카테고리: clothing — 셔츠/재킷/바지/신발/모자
- [확정] 템플릿: 20개 — 5의류 × 4상황 (구매/사이즈/색상/가격)
- [확정] 데이터 구조: `{speaker, line, blank, answer}` 배열

## 3. 합의된 방향 · 범위
- 방향: clothing 쇼핑 대화문 20개 템플릿을 advanced-questions.js에 추가
- 이번에 하는 것: SHOP_DIALOGUES 상수 정의, engine.js에 shopping_dialogue 유형 추가, 기존 UI 재사용
- 안 하는 것: 식사/여행/병원/학교 상황 (다음 확장), 전용 대화 UI 개발, 외부 JSON 파일 분리
- 완료 기준: advanced-questions.js에 20개 템플릿 추가, engine.js에 유형 추가, 기존 문장빈칸 UI로 정상 출제
- 엣지 케이스: 해당 없음 — shopping_dialogue 유형은 기존 sentence 유형과 동일한 UI/플로우 재사용
- Ambiguity-Zero 체크:
  - [x] 의도 명확
  - [x] 범위 경계 명확
  - [x] 용어 합의 완료
  - [x] 완료 기준 명확
  - [x] 열린 분기 0개
  - [x] 숨은 assumption 없음
  - [x] 엣지 케이스 확인

## 4. 미해결 · 핸드오프
- 미해결 긴장: 없음
- 핸드오프: handed-off — 2026-06-14 → PLAN 작성 완료 (plan-lint PASS)
