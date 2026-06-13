---
status: handed-off
created: 2026-06-13
scope: LLM 양자화 한글 깨짐 재발 방지·검출
linked_plan: docs/plans/archive/games/PLAN_korean_quantization_detection.md
pending_ask: null
---
<!-- Language: ko -->

# DISCUSS: LLM 양자화 한글 깨짐 재발 방지

## 1. 현황 요약
- **이번 discuss에서 끝까지:** LLM 생성 한글의 양자화 깨짐을 검출·예방하는 안전장치 마련
- SPEC 파일(`SPEC_TECH_korean_quantization_artifacts.md`)에 원인·복구 절차 기록됨
- 현재 영향 3파일(`math/ui.js`, `milestone-tracker.js`, `growth-visualizer.js`)은 이미 UTF-8 정상 상태
- **재발 방지책 없음**: `\uXXXX` 검출 스크립트, CI 게이트, justfile 레시피 모두 미구현

## 2. 진행 중 결정 (누적)
- [확정] 현재 파일들은 이미 복구됨 — `\uXXXX` 패턴 검출 결과 0건
- [확정] 프로젝트에 `justfile`, CI 게이트, 한글 검출 자동화 없음
- [확정] D 선택 — `just lint-turn-end` → `verify.sh` → 새 스크립트 호출 구조
- [확정] 새 스크립트: `scripts/verify_korean_js.py` — 4검출 유형 구현
- [확정] 45개 JS 파일 스캔 결과 — 양자화 아티팩트 0건 (정상)

## 3. 합의된 방향 · 범위
- 방향: LLM이 생성하는 한글 콘텐츠의 양자화 깨짐을 **재발 전에 검출**하는 메커니즘
- 이번에 하는 것: `scripts/verify_korean_js.py` 스크립트 작성, `verify.sh`에 통합
- 안 하는 것: 양자화 모델 교체 (프로젝트 범위 밖), 토크나이저 교체, pre-commit 후크
- 완료 기준: `just lint-turn-end` 실행 시 한글 깨짐 검출 PASS
- 검출 유형:
  1. `\uXXXX` 유니코드 이스케이프 (warning/info)
  2.KNOWN_BROKEN 사전 기반 음절 조합 오류 (error)
  3. 반복 음절 검출 — KNOWN_GOOD_REPEATS 제외 (warning)
  4. 서로게이트 페어 깨짐 검출 (error)
- 엣지 케이스: 해당 없음 — 현재 파일들 정상, SPEC은 사후 문서화
- Ambiguity-Zero 체크:
  - [ ] 의도 명확
  - [ ] 범위 경계 명확
  - [ ] 용어 합의 완료
  - [ ] 완료 기준 명확
  - [ ] 열린 분기 0개
  - [ ] 숨은 가정 없음
  - [ ] 엣지 케이스 확인

## 4. 미해결 · 핸드오프
- 미해결 긴장: 검출 정밀도 vs 오경보 비율 (KNOWN_GOOD_REPEATS 확장 필요 시)
- 핸드오프: plan — 2026-06-13 → PLAN_korean_quantization_detection.md (handed-off, plan-lint PASS)
