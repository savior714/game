# 수학 게임 스펙

**소속**: SDD — 어린이 학습 게임 플랫폼
**상태**: ✅ 완성 | **대상**: 초등 저학년
**최종 수정**: 2026-03-22

---

## 1. 개요

### 1.1 목적

초등학교 저학년 수준의 수학 능력을 게임 형태로 훈련하는 애플리케이션.
덧셈·뺄셈·곱셈을 8지선다 버튼, 20초 타이머, 세션 10문제로 구성.
아이의 실제 풀이 데이터(정답률, 응답 속도)를 누적 분석하여 난이도를 자동 조정한다.

### 1.2 기능 요약

| 기능 | 설명 |
|------|------|
| 문제 출제 | 덧셈(+), 뺄셈(-), 곱셈(×) 중 선택, 8지선다 버튼 |
| 타이머 | 20초 제한, 진행도 바 색상으로 긴장감 표현 |
| 연산별 숙련도 자동 조정 | 정답률 + 평균 응답시간 기반 7단계 |
| 연산별 출제 비율 조정 | 약한 연산 가중치 상향 |
| 강화학습 재출제 | 틀린 패턴을 기억하여 유사 문제 반복 출제 | `REINFORCE_PROB=0.45` |
| 중복 방지 | 최근 10문제를 기억하여 연속 출제 차단 | `RECENT_LIMIT=10` |
| 연속 정답 추적 | 20연속 정답 시 로켓 발사 + 전체 난이도 강제 상승 |
| 누적 통계 | localStorage 저장, 모달에서 열람 및 초기화 |

### 1.3 기술 스택

- **파일 구조**: `math/` 폴더 내 6파일 분리 (index.html / base.css / rocket.css / engine.js / rocket.js / ui.js)
- **영속성**: `localStorage` (key: `mathGameStats`)
- **렌더링**: DOM 조작, CSS 애니메이션

### 1.4 모듈 구조

```
[HTML 구조]
  ├── 타이틀 + 스코어보드
  ├── #main-area (flex row)
  │     ├── #rocket-panel   : 연속 정답 진행도 시각화
  │     └── #game-card      : 게임 영역 + 결과 화면
  └── #stats-modal          : 통계 오버레이

[JavaScript 모듈 섹션]
  ├── 상수 (TOTAL, TIME_LIMIT, ...)
  ├── 게임 상태 변수
  ├── 통계 (localStorage CRUD)
  ├── 난이도 계산
  ├── 연산 선택 (가중치)
  ├── 문제 생성
  ├── 강화학습 (틀린 패턴 재출제)
  ├── 보기 생성
  ├── 문제 표시 (askQuestion)
  ├── 결과 기록 (recordResult)
  ├── 타이머
  ├── 정답 확인 (checkAnswer)
  ├── 연속 정답 & 로켓
  ├── 게임 흐름 (nextQuestion, showResult, startGame)
  ├── 통계 모달
  └── 초기화 (initRocketPanel, startGame)
```

### 1.5 상태 전이도

```
[startGame]
     |
     v
[askQuestion] <─────────────────────┐
     |                              |
     | (타이머 시작)                 |
     v                              |
[사용자 클릭 or 타이머 만료]         |
     |                              |
     v                              |
[checkAnswer / timeOut]             |
     |                              |
     ├── recordResult()             |
     │     ├── saveStats()          |
     │     ├── updateStreak()       |
     │     └── addWrongPattern()    |
     │           or                 |
     │         removeWrongPattern() |
     |                              |
     v                              |
[피드백 표시 + "다음 문제" 버튼]     |
     |                              |
     | (클릭)                       |
     v                              |
[nextQuestion]                      |
     |                              |
     ├── currentQ < TOTAL ──────────┘
     |
     └── currentQ >= TOTAL
           |
           v
       [showResult]
```

---

## 2. 상세 로직

### 2.1 수학 전용 런타임 변수

| 변수 | 타입 | 설명 |
|------|------|------|
| `currentOp` | string | 현재 문제 연산자 (`'+'` `'-'` `'×'`) |
| `currentQData` | object\|null | `{ op, level, a, b }` — 패턴 기록용 |

### 2.2 통계 스키마

**Key**: `mathGameStats`

```json
{
  "+": { "attempts": 0, "correct": 0, "totalTime": 0 },
  "-": { "attempts": 0, "correct": 0, "totalTime": 0 },
  "×": { "attempts": 0, "correct": 0, "totalTime": 0 }
}
```

### 2.3 wrongPatterns 항목

```js
{ op: '+' | '-' | '×', level: 0|1|2, a: number, b: number }
```

최근 틀린 순(unshift), 최대 5개. 세션 내 메모리 전용(localStorage 저장 안 함).

### 2.4 난이도별 문제 범위 (7단계)

**덧셈(+)**

| 레벨 | a 최대 | b 최대 | 합 최대 | 태그 |
|------|--------|--------|---------|------|
| 0 | 5 | 5 | 10 | basic_add |
| 1 | 10 | 10 | 20 | basic_add |
| 2 | 20 | 20 | 40 | basic_add/carry |
| 3 | 35 | 25 | 60 | carry_over |
| 4 | 70 | 40 | 100 | carry_over |
| 5 | 100 | 60 | 150 | carry_over |
| 6 | 150 | 80 | 200 | carry_over |

**뺄셈(-)**

| 레벨 | a 범위 | b 범위 | 태그 |
|------|--------|--------|------|
| 0 | 3 ~ 8 | 1 ~ a-1 | basic_sub |
| 1 | 7 ~ 20 | 1 ~ a-1 | basic_sub |
| 2 | 15 ~ 40 | 1 ~ a-1 | basic_sub/borrow |
| 3 | 30 ~ 80 | 1 ~ a-1 | borrowing |
| 4 | 60 ~ 120 | 1 ~ a-1 | borrowing |
| 5 | 100 ~ 160 | 1 ~ a-1 | borrowing |
| 6 | 150 ~ 200 | 1 ~ a-1 | borrowing |

**곱셈(×)**

| 레벨 | 사용 단(a) | 배수(b) 범위 | 태그 |
|------|---------|-----------|------|
| 0 | 2, 5, 10 | 2 ~ 10 | mult_table |
| 1 | 2, 3, 5, 10 | 2 ~ 10 | mult_table |
| 2 | 2 ~ 9단 | 2 ~ 10 | mult_table |
| 3 | 11 ~ 15단 | 2 ~ 19 | mult_complex |
| 4 | 16 ~ 19단 | 2 ~ 19 | mult_complex |
| 5 | 21 ~ 30단 | 2 ~ 19 | mult_complex |
| 6 | 31 ~ 47단 | 2 ~ 19 | mult_complex |

곱셈은 `+`/`-` 누적 시도 합산 8회 이상부터 출제.

### 2.5 연산 선택 가중치 (`pickOperation`)

기본 가중치:

| 연산 | 기본 가중치 | 조건부 가중치 추가 |
|------|-------------|-------------------|
| `+` | 0.45 | 정답률 < 50%이면 +0.15 |
| `-` | 0.35 | 정답률 < 50%이면 +0.15 |
| `×` | 0.20 (조건부) | 정답률 < 50%이면 +0.15 |

가중치 합산 후 정규화하여 weighted random 선택.

### 2.6 강화학습 재출제 (`generateQuestion`)

```
generateQuestion():
  if wrongPatterns.length > 0 AND random() < REINFORCE_PROB(0.45):
    pattern = random pick from wrongPatterns
    return generateSimilar(pattern)
  else:
    op    = pickOperation()
    level = getDifficultyLevel(op)
    return generateByOpLevel(op, level)
```

#### 유사 문제 생성 (`generateSimilar`)

원래 문제의 피연산자를 ±3 범위 내에서 변형. 레벨 범위를 벗어나지 않도록 클램핑.

- **`+`**: newA = clamp(a ± rand, 1, maxA[level]), newB = clamp(b ± rand, 1, min(maxSum-newA, maxB[level]))
- **`-`**: newA = clamp(a ± rand, minA[level], maxA[level]), newB = clamp(b ± rand, 1, newA-1)
- **`×`**: 같은 단(base=a) 유지, 배수만 새로 랜덤

#### 패턴 소멸 조건

- 해당 `{ op, a, b }` 조합을 정답으로 맞히면 `wrongPatterns`에서 즉시 제거
- `wrongPatterns`는 세션 내 메모리에만 존재 (localStorage 저장 안 함)

### 2.7 보기 생성 (`makeChoices`)

정답 근처에서 plausible한 오답 7개를 생성하여 총 8지선다 구성.

- spread(오답 허용 범위):
  - `×`: 고정 ±18
  - `+`/`-`: 레벨별 `[8, 13, 20]`
- 정답 ± spread 내의 랜덤 정수 (음수 제외)
- 300회 시도 후 부족하면 1부터 순차 보완

### 2.8 타이머 로직

- 20초, 250ms 간격 tick (0.25초씩 감소)
- UI 색상 전환:

| 남은 시간 비율 | 타이머 바 색상 | 추가 효과 |
|---------------|---------------|-----------|
| > 50% | 초록 (#66bb6a) | — |
| 25% ~ 50% | 노랑 (#ffa726) | — |
| ≤ 25% | 빨강 (#ef5350) | 바 펄스 + 카드 테두리 플래시 |

- 0초 도달 시 `timeOut()` 호출 → 오답 처리, elapsed = TIME_LIMIT 기록

### 2.9 중복 방지 엔진 (수환법칙 대응)

수학은 문제의 순서가 달라도 동일한 개념인 경우 중복으로 간주한다.

1. **중복 키 생성**: `[sorted_operands].join(',') + currentOp`
   - 예: `3 + 5` → `3,5+`
   - 예: `5 + 3` → `3,5+` (중복으로 필터링됨)
2. **범위 기반 필터링**: 해당 레벨/연산의 전체 가능 조합 수(N)가 10개 미만인 경우, 최근 5문제만 중복 방지.

---

## 4. 상수 레퍼런스

| 상수 | 값 | 설명 |
|------|----|------|
| `TOTAL` | 10 | 세션당 문제 수 |
| `TIME_LIMIT` | 20 | 문제당 제한 시간(초) |
| `MIN_DATA` | 4 | 난이도 조정 활성화 최소 시도 횟수 |
| `LAUNCH_STREAK` | 20 | 로켓 발사 트리거 연속 정답 수 |
| `MAX_WRONG_PATTERNS` | 5 | 기억할 틀린 패턴 최대 개수 |
| `REINFORCE_PROB` | 0.45 | 틀린 패턴 재출제 확률 |
| `ROCKET_MAX_BOTTOM` | 330 | 로켓 최대 이동 높이(px) |
| `STATS_KEY` | `'mathGameStats'` | localStorage 키 |

---

## 5. 함수 목록

| 함수 | 역할 |
|------|------|
| `emptyStats()` | 기본 통계 객체 생성 |
| `loadStats()` | localStorage에서 통계 로드 |
| `saveStats()` | localStorage에 통계 저장 |
| `resetStats()` | 통계 초기화 + 모달 테이블 갱신 |
| `getBaseDiffLevel(op)` | 통계 기반 연산별 기초 난이도(0~2) 계산 |
| `getDifficultyLevel(op)` | globalBoost 가산 후 유효 난이도 반환 |
| `pickOperation()` | 가중치 기반 연산자 선택 |
| `generateByOpLevel(op, level)` | op + level에 따른 문제 생성 |
| `addWrongPattern(data)` | 틀린 패턴 목록에 추가 |
| `removeWrongPattern(op, a, b)` | 맞힌 패턴 목록에서 제거 |
| `generateSimilar(pattern)` | 틀린 패턴 기반 유사 문제 생성 |
| `generateQuestion()` | 강화학습 / 일반 문제 분기 |
| `makeChoices(correct, op, level)` | 8개 보기 생성 |
| `askQuestion()` | 문제 화면 렌더링 + 타이머 시작 |
| `recordResult(correct, elapsed)` | 통계 기록 + 연속 정답 + 패턴 갱신 |
| `startTimer()` | 타이머 시작 |
| `stopTimer()` | 타이머 정지 + UI 초기화 |
| `updateTimerUI()` | 타이머 바 상태 갱신 |
| `timeOut()` | 시간 초과 처리 |
| `checkAnswer(val, btn)` | 정답 확인 및 피드백 |
| `nextQuestion()` | 다음 문제 or 결과 화면 전환 |
| `showResult()` | 결과 화면 렌더링 |
| `startGame()` | 세션 초기화 + 첫 문제 출제 |
| `updateStreak(correct)` | 연속 정답 갱신 + 발사 트리거 |
| `updateRocketUI()` | 로켓 위치 + 배지 갱신 |
| `launchRocket()` | 발사 애니메이션 + globalBoost 증가 |
| `showBoostBanner()` | 난이도 상승 배너 표시 |
| `openStats()` | 통계 모달 열기 |
| `closeStats()` | 통계 모달 닫기 |
| `renderStatsTable()` | 통계 테이블 DOM 렌더링 |
| `confirmResetStats()` | 초기화 confirm + 실행 |
| `initRocketPanel()` | 별 생성 + 초기 로켓 위치 설정 |
| `spawnConfetti()` | 색종이 이모지 낙하 효과 |
| `crashRocket()` | 추락 애니메이션 (폭발→스핀→충돌) |
| `flashScreenRed()` | 빨간 화면 플래시 (추락 시) |
| `spawnExplosion()` | 방사형 폭발 파티클 생성 |
| `spawnSmoke()` | 추락 중 연기 파티클 생성 |
| `spawnImpactDust()` | 충돌 먼지 파티클 생성 |
| `flashScreen()` | 흰 화면 플래시 (발사 시) |
| `spawnExhaust()` | 발사 배기 파티클 생성 |
| `playCorrect()` | 정답 효과음 (상행 3음) |
| `playWrong()` | 오답 효과음 (하행 버저) |
| `playTimeout()` | 시간초과 효과음 |
| `playDrop()` | 구슬 드롭 효과음 |
| `playMerge(level)` | 구슬 합체 효과음 (레벨별 음높이) |
| `showMarbleGame()` | 마블 머지 미니게임 모달 열기 |
| `closeMarbleGame()` | 마블 머지 모달 닫기 |
| `onMbInput(e)` | 캔버스 클릭/터치 → 구슬 드롭 |

---

## 6. 마블 머지 미니게임

### 6.1 개요

20연속 정답 달성 시 로켓 발사 후 score-board에 "마블 게임!" 버튼이 활성화된다.
버튼 클릭 시 Canvas 기반 물리 퍼즐 미니게임 모달이 열린다.

### 6.2 구슬 등급표

| 레벨 | 반지름 | 색상 | 합체 점수 |
|------|--------|------|-----------|
| 1 | 18px | `#FFB3BA` (분홍) | 10 |
| 2 | 26px | `#FFCE9A` (복숭아) | 30 |
| 3 | 35px | `#FFF89A` (노랑) | 60 |
| 4 | 46px | `#BAFFC9` (연두) | 100 |
| 5 | 58px | `#BAE1FF` (하늘) | 150 |
| 6 | 71px | `#D4BAFF` (보라) | 250 |
| 7 | 85px | `#FFB3B3` (빨강) | 600 |

레벨 7 + 레벨 7 충돌 시 두 구슬 소멸 + 보너스 1200점.

### 6.3 물리 파라미터

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `MB_G` | 0.35 | 중력 가속도 (px/frame²) |
| `MB_D` | 0.985 | 선형 감속 (공기저항) |
| `MB_R` | 0.22 | 탄성 계수 (restitution) |
| `DLINE` | 65px | 게임오버 위험선 |
| `OVR_MS` | 3000ms | 위험선 초과 유예 시간 |

### 6.4 추가 파일

| 파일 | 내용 |
|------|------|
| `math/sound.js` | Web Audio API 효과음 (정답·오답·합체·드롭) |
| `math/marble.js` | 마블 머지 미니게임 물리 엔진 + 렌더링 |
