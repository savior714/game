---
status: handed-off
created: 2026-06-12
scope: 프로젝트 전체 폴더 구조 — DDD 방향성, 계층 분리, 유지보수성
linked_plan: docs/plans/archive/refactor/PLAN_ddd_structure_reorg.md
pending_ask: null
---
<!-- Language: ko -->

# DISCUSS: 프로젝트 구조 DDD 재편 및 클린 코드 보완

## 1. 현황 요약
- **이번 discuss에서 끝까지:** 과목별 학습 게임 프로젝트의 폴더 구조를 DDD 원칙에 맞추어 위계 역전이 없고 유지보수가 용이한 구조로 재편하는 방향을 논의한다.
- 정적 HTML/JS/CSS 기반 어린이 학습 게임 플랫폼 (4개 과목 + 실험 모듈)
- `common/`에 비즈니스 로직과 UI 유틸이 혼재, `global/`에 auth/reward/sync가 뭉쳐 있음
- 과목별 engine/ui 경계가 파일 내부에서만 구분될 뿐 폴더 구조상 분리 없음
- 루트에 독립 HTML 파일들이 산재하여 탐색성 저하

## 2. 진행 중 결정 (누적)
- [확정] 도메인 중심 구조 (domains/ + shared/) — 7개 도메인: math, english, korean, science, reward, auth, sync
- [확정] shared/domain (progress-engine), shared/ui (quiz-ui-core, rocket-core/effects) — 2계층
- [확정] 도메인 폴더 flat 구조 — math/engine.js, math/ui.js, math/index.html
- [확정] 실험 모듈을 experiments/ 폴더에 묶기
- [확정] 의존성 방향: domains/* → shared/domain/ui 허용, shared/* → domains/* 금지
- [확정] Event Bus 패턴으로 도메인 간 통신 중재 — shared/event-bus.js
- [확정] CSS 통합 — shared/ui/base.css + domains/*/theme.css
- [확정] auth 실패 시 기본 기능(게임 플레이, 로컬 통계)은 사용 가능
- [확정] 마이그레이션 순서: shared → domains → experiments → 루트 HTML 경로 업데이트

## 3. 합의된 방향 · 범위
- 방향: 도메인 중심 구조 재편
- 이번에 하는 것: domains/, shared/, experiments/ 폴더 생성 및 파일 이동, script 참조 경로 업데이트
- 안 하는 것: ES 모듈 도입, Next.js/백엔드 스택 추가, 프레임워크 변경
- 완료 기준: 모든 도메인이 shared/만 의존, 루트 HTML에서 domains/shared로 script 경로 변경 완료, 게임 동작 확인
- 엣지 케이스: auth 실패 시 기본 기능은 사용 가능 — 로그인 없이도 게임 플레이 + 로컬 통계 저장 가능
- Ambiguity-Zero 체크:
  - [x] 의도 명확
  - [x] 범위 경계 명확
  - [x] 용어 합의 완료
  - [x] 완료 기준 명확
  - [x] 열린 분기 0개
  - [x] 숨은 가정 없음
  - [x] 엣지 케이스 확인

## 4. 미해결 · 핸드오프
- 미해결 긴장: 없음
- 핸드오프: plan — 2026-06-12
