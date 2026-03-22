# 플랫폼 공통 아키텍처

**소속**: SDD — 어린이 학습 게임 플랫폼
**최종 수정**: 2026-03-22

---

## 0. 플랫폼 공통 아키텍처

### 0.0 게임 현황

| 폴더 | 과목 | 상태 |
|------|------|------|
| `math/` | 수학 (덧셈·뺄셈·곱셈) | ✅ 완성 |
| `english/` | 영어 (단어·문장) | ✅ 완성 |
| `korean/` | 국어 (받침·맞춤법·어휘) | 🔲 계획 중 |
| `science/` | 과학 (분류·개념) | 🔲 계획 중 |

### 0.1 파일 구조

각 게임 폴더는 아래 6개 파일로 구성한다.

```
{subject}/
  index.html    ← HTML 구조 + CSS/JS 링크
  base.css      ← 공통 레이아웃·UI 스타일
  rocket.css    ← 로켓 패널 + 애니메이션 스타일
  engine.js     ← 상수·통계·난이도·문제 생성 로직
  rocket.js     ← 로켓 UI·발사·추락 이펙트
  ui.js         ← 타이머·정답확인·게임흐름·통계모달
```

현재 구조:

```
game/
  CLAUDE.md            ← AI 협업 전역 규칙
  SDD.md               ← 플랫폼 인덱스 (스펙 링크 목록)
  specs/               ← 스펙 파일 디렉토리
    platform.md        ← 이 파일 (공통 아키텍처)
    math.md            ← 수학 게임 스펙
    english.md         ← 영어 게임 스펙
    korean.md          ← 국어 게임 스펙 (계획)
    science.md         ← 과학 게임 스펙 (계획)
  math/                ← 수학 게임 (완성, 6파일 분리)
  english/             ← 영어 게임 (완성, 6파일 분리)
  korean/              ← 국어 게임 (계획)
  science/             ← 과학 게임 (계획)
```

> **설계 결정 (2026-03-22)**: 과목별 폴더 구조로 전환.
> 기존 단일 파일(math-game.html 1385라인, english/index.html 1161라인) → 각 game/ 폴더 내 6개 파일로 분리.
> CSS: base/rocket, JS: engine/rocket/ui (로드 순서 준수). 외부 의존성 없음.
>
> **설계 결정 (2026-03-22)**: SDD.md를 인덱스로 경량화, 게임별 스펙을 `specs/` 디렉토리로 분리.

### 0.2 공통 시스템 (모든 게임 필수 구현)

| 시스템 | 설명 | 핵심 상수 |
|--------|------|-----------|
| 로켓 스트릭 | 연속 정답 20개 → 발사 / 오답 → 폭발 추락 | `LAUNCH_STREAK=20` |
| 적응형 난이도 | 정답률+응답속도 기반 3단계 자동 조정 | `MIN_DATA=4` |
| 강화학습 | 틀린 패턴 재출제 (최대 5개 기억) | `REINFORCE_PROB=0.45` |
| 타이머 | 20초 제한, 진행바 색상 경고 | `TIME_LIMIT=20` |
| 누적 통계 | localStorage, 모달 열람·초기화 | 게임별 고유 키 |

### 0.3 공통 런타임 상태 변수

| 변수 | 타입 | 설명 |
|------|------|------|
| `currentQ` | number | 현재 문제 번호 (0-based) |
| `score` | number | 현재 세션 정답 수 |
| `answer` | any | 현재 문제 정답 |
| `answered` | boolean | 중복 입력 방지 |
| `timeLeft` | number | 남은 시간(초) |
| `timerInterval` | number\|null | setInterval ID |
| `streak` | number | 연속 정답 수 (0 ~ LAUNCH_STREAK) |
| `globalBoost` | number | 발사 횟수 누적, 전체 난이도 가산 (0~2) |
| `launching` | boolean | 발사 애니메이션 진행 중 |
| `crashing` | boolean | 추락 애니메이션 진행 중 |
| `wrongPatterns` | array | 틀린 패턴 목록 (최대 5개) |

### 0.4 공통 localStorage 스키마

키 형식: `{subject}GameStats`

```json
{
  "{카테고리A}": { "attempts": 0, "correct": 0, "totalTime": 0 },
  "{카테고리B}": { "attempts": 0, "correct": 0, "totalTime": 0 }
}
```

파생 지표: **정답률** = `correct/attempts`, **평균응답시간** = `totalTime/attempts`

### 0.5 공통 난이도 판정 (`getBaseDiffLevel`)

최소 4회 시도 후 활성화.

| 조건 | 레벨 | 라벨 |
|------|------|------|
| 정답률 ≥ 75% AND 평균시간 ≤ 7초 | 2 | 어려움 |
| 정답률 ≥ 55% AND 평균시간 ≤ 11초 | 1 | 보통 |
| 그 외 (데이터 부족 포함) | 0 | 쉬움 |

유효 난이도: `min(2, baseDiffLevel + globalBoost)`

### 0.6 로켓 발사·추락 시퀀스

**발사** (streak = 20 도달):
1. 600ms 점화 — 로켓 강렬 진동, 화염 성장, 발사대 흔들림
2. 발사 — 화면 플래시, 배기 파티클, 별 워프, 로켓 상승 후 화면 밖
3. 리셋 — `globalBoost+1`, `streak=0`, 로켓 바닥 복귀, 부스트 배너

**추락** (오답, streak > 0):
1. 500ms 폭발 — 로켓 폭발 진동, 빨간 플래시, 방사형 파티클
2. 1050ms 추락 스핀 — 중력 가속 낙하, 회전, 연기 파티클
3. 450ms 충돌 바운스 — 착지 스쿼시, 먼지 파티클

### 0.7 신규 게임 개발 체크리스트

새 과목 게임을 추가할 때 순서대로 진행한다.

1. `specs/{subject}.md` 작성 (개요 / 문제 유형 / 난이도 기준 / 데이터 스키마)
2. `SDD.md` §게임 현황 테이블 상태 최신화
3. `{subject}/` 폴더 생성 후, `math/` 폴더의 파일 구조를 기반으로 6개 파일 작성
4. 과목 고유 로직(문제 생성, 보기 생성, 정답 판정)만 새로 작성
5. `localStorage` 키를 `{subject}GameStats` 형식으로 신규 정의

---

## 3. UI 컴포넌트 설계 (공통)

### 3.1 레이아웃 구조

```
body (flex column, center)
  ├── h1
  ├── #score-board (flex row)
  │     ├── .score-item (문제 N/10)
  │     ├── .score-item (점수 N)
  │     └── #stats-btn (통계 버튼)
  └── #main-area (flex row)
        ├── #rocket-panel
        │     ├── 🌌 레이블
        │     ├── #rp-track (64×380px, 그라디언트)
        │     │     ├── #rp-stars (JS 생성 별 18개)
        │     │     ├── .rp-cloud ×2
        │     │     ├── #rp-flame (화염)
        │     │     └── #rp-rocket (로켓)
        │     ├── 🌍 레이블
        │     └── #streak-badge
        └── #game-card (max-width 480px)
              ├── #game-area
              │     ├── #timer-label
              │     ├── #timer-wrap > #timer-bar
              │     ├── #question
              │     ├── #answer-buttons (4×2 grid)
              │     ├── #feedback
              │     └── #next-btn
              └── #result-screen
                    ├── #stars
                    ├── #result-title
                    ├── #result-msg
                    └── #restart-btn
```

### 3.2 로켓 트랙 그라디언트

| 높이 (from bottom) | 색상 | 의미 |
|--------------------|------|------|
| 0% | #3a5c1a | 땅 |
| 6% | #5a8a28 | 풀밭 |
| 18% | #87ceeb | 하늘 |
| 42% | #4a90d9 | 대기권 |
| 65% | #1a3a8a | 성층권 |
| 80% | #0d1540 | 우주 경계 |
| 100% | #030818 | 우주 |

### 3.3 통계 모달

- 배경 클릭으로 닫기 (`onModalBackdrop`)
- 연산별 행: 연산 이름 / 시도 / 정답률% / 평균시간초 / 난이도 배지
- 난이도 배지 색상: 쉬움 `#66bb6a` / 보통 `#ffa726` / 어려움 `#ef5350` / 데이터 부족 `#ccc`
- "기록 초기화" 클릭 시 `confirm()` 후 localStorage 삭제 + 테이블 재렌더
