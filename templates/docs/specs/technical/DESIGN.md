---
version: 2.0.0
last_updated: 2026-04-24
author: Antigravity (Architect)
status: Active
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

# Design Specification: Legacy Game Style Import

이 문서는 과거 게임 디자인의 스타일 자산을 현재 루트 런타임 구조로 가져와 유지하기 위한 Design SSOT입니다.

## 1. 과거 디자인의 핵심 정체성

- **Warm + playful 학습 톤**: 베이스 배경은 `#F8F6F3`, 핵심 액션은 `#FF6B35` 계열.
- **라운드 중심 UI**: 배지/버튼은 pill radius(`100px`), 카드/모달은 큰 곡률(`24px~32px`).
- **모션 피드백 우선**: 정답(pop), 오답(shake), 긴급상태(pulse), 보상 등장(slide/bounce) 애니메이션.
- **게임-시스템 결합형 HUD**: 점수판/타이머/로켓패널/보상 인벤토리를 하나의 플레이 루프로 연결.

## 2. Import Source of Truth

아래 파일들이 과거 디자인의 실제 소스이며, 신규 UI는 이 패턴을 우선 상속한다.

- 기본 게임 레이아웃/타이포/버튼/모달: `math/base.css` (과목별 CSS도 동일 계열)
- 로켓 패널/우주 트랙/발사 애니메이션: `math/rocket.css`
- 전역 보상 인벤토리/보상 모달/토스트: `global/reward.css`

## 3. 스타일 Import 원칙

### 3.1 CSS 레이어 순서

아래 순서로 불러오는 것을 표준으로 한다.

```css
@import "../global/reward.css";
@import "./base.css";
@import "./rocket.css";
```

규칙:
- 전역 보상 계층(`reward.css`)은 페이지별 스타일보다 먼저 로드한다.
- 페이지별 오버라이드는 마지막 파일에서만 수행한다.

### 3.2 컴포넌트 토큰 매핑

- **Primary CTA**: `#FF6B35`, hover는 더 어두운 오렌지 계열.
- **Success/Error**: `#059669` / `#DC2626`.
- **Timer 위험 단계**: normal `#10B981` -> warn `#F59E0B` -> danger `#EF4444`.
- **Card surface**: white + soft border + drop shadow(`0 8px 32px rgba(0,0,0,0.08)` 계열).

## 4. 레거시 컴포넌트 카탈로그

- **Quiz Card**: 큰 숫자 문제(`3rem+`), 4-grid 답안 버튼, 하단 피드백 + 다음 버튼.
- **Rocket Panel**: 수직 트랙 + 지면/대기권/우주 그라데이션 + 흔들림/점화/발사 상태 클래스.
- **Stats Modal**: 반투명 백드롭 + 라운드 카드 + 난이도 배지 테이블.
- **Reward Inventory Bar**: 상단 고정, 블러 배경, 슬롯 카드, 상태 강조(보유/빈 슬롯).

## 5. 신규 페이지 적용 체크리스트

- Pretendard 폰트 계열을 기본 폰트로 설정했는가
- 버튼/배지/카드 radius가 기존 라운드 체계를 따르는가
- 정답/오답/시간위험 피드백 색과 모션이 동일한가
- 보상 인벤토리와 충돌하지 않도록 상단 여백 및 z-index를 맞췄는가

## 6. 비회귀 가드

- 과거 디자인 복원 기준은 `math/base.css`, `math/rocket.css`, `global/reward.css`의 시각 규칙을 우선한다.
- 신규 다크 테마(`styles.css`)는 홈/탐색 레이어에서만 사용하고, 레거시 게임 화면 톤을 임의로 치환하지 않는다.

## 7. Runtime Entry and Routing SSOT

현재 템플릿 기반 런타임의 진입점과 라우팅 기준은 아래를 단일 출처로 본다.

- 메인 엔트리: `index.html`
- 우주 탐험 엔트리: `space-explorer.html`
- 우주 탐험 모듈 엔트리: `space-explorer/main.js`
- 배포 rewrite 정책: `vercel.json`
  - `/space-explorer.html` -> `/space-explorer.html`
  - 루트(`/`) 및 광역 catch-all rewrite는 사용하지 않음 (메인 라우트 덮어쓰기 방지)

---
**Last Verified**: 2026-04-24 by Antigravity
