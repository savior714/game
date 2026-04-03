# 플랫폼 공통 아키텍처

**소속**: SDD — 어린이 학습 게임 플랫폼  
**최종 수정**: 2026-03-29

---

## 0. 플랫폼 공통 아키텍처

과목별 퀴즈는 `*/` 폴더에 두고, 로켓·난이도·UI 흐름은 `common/`으로, 계정·보상·동기화는 `global/`로 분리한다. 상세 비즈니스 규칙은 `docs/CRITICAL_LOGIC.md`가 SSOT이다.

### 0.0 게임 현황

| 폴더 | 과목 | 상태 |
|------|------|------|
| `math/` | 수학 (덧셈·뺄셈·곱셈) | ✅ 완성 |
| `english/` | 영어 (단어·문장) | ✅ 완성 |
| `korean/` | 국어 (받침·맞춤법·어휘) | ✅ 완성 |
| `science/` | 과학 (분류·개념) | ✅ 완성 |
| `marble/` | 마블 머지 미니게임 (보상 소비) | ✅ 완성 |
| `guardian/` | 보호자 맞춤 보상 상점 편집 | ✅ (구글 로그인 연동 시) |
| `admin/` | 운영자용 가입 계정 조회 | ✅ (허용 이메일만) |

### 0.1 파일 구조

각 과목 게임 폴더는 아래 6개 파일로 구성한다.

```
{subject}/
  index.html    ← HTML 구조 + CSS/JS 링크 (common/global 스크립트 선로드)
  base.css      ← 공통 레이아웃·UI 스타일
  rocket.css    ← 로켓 패널 + 애니메이션 스타일
  engine.js     ← 상수·통계·난이도·문제 생성 로직 (progress-engine 위임)
  rocket.js     ← RocketCore 설치·위임 (rocket-core / rocket-effects)
  ui.js         ← 타이머·정답확인·게임흐름·통계모달 (quiz-ui-core 위임)
```

저장소 루트 개략:

```
game/
  index.html           ← 과목 허브 (Tailwind, global/reward 로드)
  serve_game.py        ← 로컬 정적 서버 (포트 3000)
  SDD.md                 ← 플랫폼 인덱스
  specs/                 ← 과목·플랫폼 스펙 (이 파일 포함)
  docs/                  ← memory, CRITICAL_LOGIC, docs/specs/* 보조 명세
  common/                ← rocket-core, rocket-effects, progress-engine, quiz-ui-core
  global/                ← reward.js, reward_ui.js, auth.js, sync-engine.js
  supabase/              ← SQL·RLS (user_directory 등)
  math/, english/, korean/, science/
  marble/, guardian/, admin/
```

> **설계 결정 (2026-03-22)**: 과목별 폴더 6파일 분리.  
> **설계 결정 (2026-03-27~)**: 공용 코어(`common/`) 도입 및 `rocket-effects` 분리.  
> **설계 결정 (2026-03-28~)**: 룰렛 제거, 보석 화폐 + 상점(`global/reward*`).  
> **설계 결정 (2026-03-29)**: Supabase 구글 로그인 + `sync-engine` 오프라인 큐.

### 0.2 공통 시스템 (모든 게임 필수 구현)

| 시스템 | 설명 | 핵심 상수 / 위치 |
|--------|------|------------------|
| 로켓 스트릭 | 연속 정답 20개 → 발사 / 오답 → 폭발 추락(그물망 있으면 예외는 CRITICAL_LOGIC §7) | `LAUNCH_STREAK=20`, `common/rocket-core.js` |
| 그물망 (Net Shield) | 연속 정답 5회마다 1회 보호막 획득 | `NET_STREAK=5` |
| 적응형 숙련도 | 정답률+응답속도 기반 7단계 자동 조정 | `MIN_DATA=3`, `SUBJECT_DIFF_OPTS={up:0.85,down:0.75}`, `common/progress-engine.js` |
| 강화학습 | 틀린 패턴 재출제 (최대 5개 기억) | `REINFORCE_PROB=0.45` (과목 `engine.js`) |
| 중복 방지 | 최근 10문제 키 버퍼 | `RECENT_LIMIT=10` |
| 타이머 | 과목별 `TIME_LIMIT`(수학·과학 등 120초, 영어 120초 등) — 각 `engine.js` / UI 코어 | 진행바 경고 |
| 누적 통계 | `localStorage`, 모달 열람·초기화 | `{subject}GameStats` |
| 전역 보상·보석 | 20연속 정답 시 💎 1개 지급 → 상점에서 유튜브·간식·마블 등으로 교환 | `study_rewards`, `global/reward.js` |
| 동기화 (선택) | 로그인 시 Supabase와 `study_rewards` 등 병합 | `global/sync-engine.js`, `global/auth.js` |

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
| `recentQuestions` | array | 최근 출제된 문제 키 목록 (최대 10개) |

### 0.4 공통 localStorage 스키마

키 형식: `{subject}GameStats`

```json
{
  "{카테고리A}": { "attempts": 0, "correct": 0, "totalTime": 0 },
  "{카테고리B}": { "attempts": 0, "correct": 0, "totalTime": 0 }
}
```

파생 지표: **정답률** = `correct/attempts`, **평균응답시간** = `totalTime/attempts`

### 0.5 공통 숙련도 판정 (`getBaseDiffLevel`)

최소 4회 시도 후 활성화. 정답률 90% 이상 시 레벨 상승.

| 레벨 | 라벨 | 색상 |
|------|------|------|
| 0 | 입문 | #aed581 |
| 1 | 기초 | #66bb6a |
| 2 | 중급 | #4fc3f7 |
| 3 | 숙련 | #29b6f6 |
| 4 | 마스터 | #ffca28 |
| 5 | 초월 | #ab47bc |
| 6 | 전설 | #ef5350 |

유효 숙련도: `min(6, baseDiffLevel + globalBoost - penalty)`

### 0.8 중복 방지 엔진 (Anti-Repetition Engine)

학습의 다양성을 위해 최근 출제된 문제를 일정 기간 제외한다.

1. **저장 방식**: `recentQuestions` 배열에 문제의 고유 키(Key)를 저장.
2. **필터링 로직**: `generateQuestion` 시 후보군이 `recentQuestions`에 포함되어 있으면 재시도 (최대 20회).
3. **제외 한도**: 가용 가능한 전체 문제 수(N)가 `RECENT_LIMIT`보다 작을 경우, 필터링 대상은 `floor(N/2)`로 제한하여 선택 불가능한 상황을 방지한다.
4. **과목별 키 생성 규칙**:
   - **수학**: 연산자 + 정렬된 피연산자 (예: `3+5`와 `5+3`은 모두 `+3,5`로 저장).
   - **기타**: 질문 텍스트 또는 고유 단어/ID.

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
6. 메인 허브 `index.html` 및 전역 보상 스크립트 로드 순서는 기존 과목 페이지를 참고한다.

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
- 연산별 행: 연산 이름 / 시도 / 정답률% / 평균시간초 / 숙련도 배지
- 숙련도 배지 색상: 기초 `#66bb6a` / 중급 `#42a5f5` / 마스터 `#ffca28` / 데이터 부족 `#ccc`
- "기록 초기화" 클릭 시 `confirm()` 후 localStorage 삭제 + 테이블 재렌더

---

## 4. 개발 및 문서화 표준 (Standards)

본 프로젝트의 지속 가능한 유지보수를 위해 아래의 엄격한 규칙을 준수한다.

### 4.1 개발 제약 사항 (Fatal Constraints)
- **단일 파일 500라인 초과 금지**: 단일 파일이 500라인을 넘으면 즉시 하위 모듈이나 컴포넌트로 분리(Refactoring)해야 한다.
- **선(先) 설계 후(後) 구현**: 모든 신규 기능 및 게임 추가 시 `specs/` 내의 설계 문서를 먼저 업데이트한 후에 코드를 작성한다.
- **LocalStorage 네이밍**: `{subject}GameStats` 형식을 엄수하여 과목 간 데이터 충돌을 방지한다.

### 4.2 문서 관리 규칙 (SSOT Guard)
- **SDD.md (100라인)**: 플랫폼 인덱스 문서가 100라인을 초과하면 내용을 `specs/` 하위 문서로 분리하고 요약본만 남긴다.
- **docs/memory.md (200라인)**: 세션 기억 및 현재 상황 문서가 200라인을 초과하면 즉시 50라인 이내로 요약 후 아카이브한다. (최우선 순위)

### 4.3 AI 협업 프로토콜
- **에이전트 안전 수칙**: 특정 로컬 파일을 직접 열 수 없거나 해결이 불가능한 경우, 에이전트는 즉시 작업을 중단하고 사용자에게 수동 확인을 요청해야 한다.

### 4.4 기술 스택 및 라이브러리 정책
- **외부 CDN·라이브러리**: Tailwind CSS, Pretendard(폰트) 등 CDN 사용 가능. 핵심 게임 로직은 **Vanilla JS**. Supabase 클라이언트는 인증·동기화 경로에만 사용한다.
- **공통 시스템 변경**: 로켓·통계·보상·동기화 규칙을 바꿀 때는 `specs/platform.md`, `docs/CRITICAL_LOGIC.md`, 필요 시 `docs/specs/reward_inventory_spec.md`를 먼저 갱신한 뒤 코드를 맞춘다.

### 4.5 인증·백엔드 (선택 기능)
- **구글 로그인**: `global/auth.js` 환경 변수(Supabase URL/키) 필요.
- **관리자·디렉터리**: `supabase/user_directory.sql` RLS와 `ADMIN_EMAILS` 정책을 준수한다.
