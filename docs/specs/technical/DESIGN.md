---
version: 2.1.0
last_updated: 2026-08-06
status: STABLE_REFERENCE_NOT_CURRENT_PRIORITY
tokens:
  colors:
    legacy_brand:
      orange_primary: "#FF6B35"
      orange_soft_bg: "#FFF7F0"
      orange_soft_border: "rgba(255, 107, 53, 0.20)"
      deep_text: "#1A1A1A"
      muted_text: "#6B6B6B"
    legacy_feedback:
      success: "#059669"
      warning: "#F59E0B"
      danger: "#EF4444"
      error: "#DC2626"
    legacy_space:
      sky_top: "#9EC8EA"
      sky_mid: "#3F5EA9"
      sky_deep: "#0B1134"
      sky_void: "#030718"
      earth_green: "#557A20"
    neutral:
      background_warm: "#F8F6F3"
      surface: "#FFFFFF"
      border_soft: "rgba(0, 0, 0, 0.06)"
  typography:
    font_family:
      primary: "'Pretendard', 'Apple SD Gothic Neo', -apple-system, sans-serif"
    weights:
      normal: 400
      semibold: 600
      bold: 700
      black: 800
  radii:
    card: "24px"
    pill: "100px"
    modal: "28px"
---

# AidenGame Design Reference

이 문서는 기존 학습 게임의 시각 언어와 실제 runtime entry를 보존하기 위한 참고문서다.
현재 최우선 개발 방향은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`이며, 진행을 막는 usability 결함 외의 순수 시각 리디자인·장식·애니메이션 개선은 안정화 이후로 미룬다.

## 1. 기존 디자인 정체성

- **Warm + playful 학습 톤:** 기본 배경은 `#F8F6F3`, 핵심 액션은 `#FF6B35` 계열.
- **라운드 중심 UI:** 배지·버튼은 pill radius, 카드·모달은 큰 곡률.
- **즉각적인 상태 피드백:** 정답, 오답, 시간 위험, 보상 상태를 색·문구·동작으로 구분.
- **학습 흐름 중심 HUD:** 문제, 점수, 다음 행동, 결과를 어린이가 한눈에 이해할 수 있어야 함.

이 정체성은 신규 시각 작업을 시작하라는 지시가 아니라, 신뢰성 수정 중 기존 화면을 불필요하게 바꾸지 않기 위한 비회귀 기준이다.

## 2. Style Source of Truth

현재 과목 화면의 실제 style source는 코드다.

- 기본 게임 레이아웃·타이포·버튼·모달: `domains/math/base.css`와 각 과목의 `base.css`
- 로켓 패널·트랙·발사 상태: 각 과목의 `rocket.css`
- 보상 인벤토리·모달·토스트: `domains/reward/reward.css`
- 홈·탐색 레이어: 루트 `styles.css`

문서 token과 실제 CSS가 불일치하면 먼저 현재 product decision과 code를 확인한다. 문서만 보고 CSS를 대규모 통일하지 않는다.

## 3. Style 적용 원칙

### 3.1 CSS 로딩

페이지가 실제로 사용하는 `<link>`와 import 순서를 authority로 본다.
새로운 전역 import를 문서 예시만 보고 추가하지 않는다.

공용 reward style과 과목별 style이 함께 사용되는 경우:

- 공용 layer가 과목별 control state를 덮어쓰지 않아야 함
- 과목별 override는 가까운 feature CSS에 둠
- z-index, overlay, focus style의 실제 사용자 흐름을 확인함

### 3.2 상태 표현

- Primary CTA는 현재 페이지의 기존 accent 체계를 유지함
- success와 error는 색만이 아니라 문구·상태로 구분함
- disabled 상태는 실제 click 가능 상태와 일치해야 함
- feedback과 next action이 동시에 불명확하지 않아야 함
- animation이 필수 control을 가리거나 입력을 중복 처리하지 않아야 함

## 4. Component Reference

- **Quiz Card:** 문제, 답안 control, feedback, next action
- **Rocket Panel:** 학습 진행의 시각적 보상
- **Stats Modal:** 누적 기록과 reset control
- **Reward Inventory:** 보유 상태와 보호자 보상 연동
- **Result Screen:** 마지막 문제 이후 결과와 restart

컴포넌트 이름은 공통 runtime component가 존재한다는 뜻이 아니다. 실제 두 과목에서 동일한 책임과 계약이 확인되기 전에는 선제 공용화하지 않는다.

## 5. 신뢰성 단계의 디자인 범위

현재 포함:

- 터치 target이 작아 눌리지 않음
- focus 또는 keyboard 진행 불가
- disabled 상태와 실제 동작 불일치
- feedback이 없어 현재 상태를 알 수 없음
- overlay·animation이 필수 control을 가림
- 중복 입력이 상태를 두 번 전진시킴

현재 제외:

- 색상·그림자·배경 리디자인
- 신규 animation과 캐릭터 연출
- 기능과 무관한 layout 재설계
- 브랜드·테마 통일

## 6. 비회귀 원칙

- 신뢰성 수정은 기존 product tone을 가능한 한 보존한다.
- CSS 변경은 해당 failure mode를 닫는 최소 범위로 제한한다.
- 과목별 특수 feedback과 pedagogy를 공용 style 때문에 제거하지 않는다.
- 실제 viewport와 입력 방식에서 control 상태를 확인한다.
- 순수 디자인 debt를 현재 안정화 완료 조건에 추가하지 않는다.

## 7. Runtime Entry and Routing SSOT

현재 정적 runtime과 배포 경로는 다음과 같다.

- 메인 entry: `index.html`
- Space Explorer entry: `experiments/space-explorer/index.html`
- Space Explorer module entry: `experiments/space-explorer/main.js`
- Ocean Rescue production standalone artifact: `ocean-rescue/index.html`
- 배포 설정: `vercel.json`
- `vercel.json`의 현재 rewrite 설정: `"rewrites": []`

다음 경로는 현재 entry가 아니다.

- `/space-explorer.html`
- `experiments/space-explorer.html`

별도 rewrite가 없으므로 위 alias를 사용하거나 문서에서 redirect된다고 주장하지 않는다.
실제 routing 변경은 `index.html`, 대상 entry, `vercel.json`, routing test를 함께 검증한다.

## 8. 검증 참고

```bash
uv run pytest -q tests/test_docs_routing_ssot.py
uv run pytest -q tests/test_readme_identity.py
uv run pytest -q tests/test_active_technical_spec_consistency.py
```

이 문서는 시각 token 또는 runtime routing의 안정적인 계약이 실제로 변경된 경우에만 갱신한다.
