# 효능감 강화 시스템 상세 Blueprint

## 1) 목표

학습 게임 플레이 후 아이가 **"나도 할 수 있다"**는 효능감(self-efficacy)을 느끼도록 하는 4개 시스템을 구축한다.

- **마일스톤 시스템**: 작은 성취를 즉시 피드백 (연속/누적/첫 도전)
- **일일 출석**: 학습 기록 기반 습관 형성 (+보석)
- **과목 다양성 보상**: 전과목 유도 (+보석)
- **성장 시각화 3종**: 난이도토스트 + 주간요약 + 숙련도바

---

## 2) 범위 정의

### In Scope

- `shared/domain/milestone-tracker.js` — 마일스톤 추적 모듈
- `shared/domain/daily-streak.js` — 일일 출석 추적 모듈
- `shared/domain/diversity-reward.js` — 과목 다양성 보상 모듈
- `shared/domain/growth-visualizer.js` — 성장 시각화 모듈
- 4개 과목 engine.js 수정 (마일스톤 연동)
- `reward.js` 수정 (보석 획득 경로 확장)
- `reward_ui.js` 수정 (성장 토스트/주간요약 UI)
- `guardian/index.html` 수정 (주간 성장 요약 탭 추가)

### Out of Scope

- 클라우드 동기화 확장 (localStorage만 사용, SyncEngine 연동은 추후)
- 모바일 앱 native 기능
- 소셜 공유/경쟁 기능

---

## 3) 아키텍처 개요

```
shared/domain/
  progress-engine.js        ← 기존 (난이도 계산, 통계 기록) — 수정 없음
  milestone-tracker.js      ← NEW (연속/누적/첫 도전 마일스톤)
  daily-streak.js            ← NEW (학습 기록 기반 출석 + 보석)
  diversity-reward.js        ← NEW (과목 다양성 보상)
  growth-visualizer.js       ← NEW (난이도토스트/주간요약/숙련도바)

domains/reward/
  reward.js                  ← 수정 (보석 획득 함수 확장)
  reward_ui.js               ← 수정 (성장 토스트/주간요약 UI)
  guardian/index.html        ← 수정 (주간 성장 요약 탭)

domains/{math,english,korean,science}/
  engine.js                  ← 수정 (마일스톤 연동)
```

### 데이터 흐름

```
engine.js:recordResult(correct)
  │
  ├─→ ProgressEngine.recordResultCore()      ← 기존: 통계 기록
  ├─→ RocketCore.updateStreak()              ← 기존: 로켓 스택
  ├─→ MilestoneTracker.record(correct)       ← NEW: 마일스톤 추적
  │     └─ emit 'milestone-achieved' event
  │
  ├─→ DailyStreak.record(subject, correct)   ← NEW: 출석 기록
  │
  └─→ DiversityReward.record(subject, correct) ← NEW: 과목 다양성
```

---

## 4) 상세 모듈 설계

### 4.1 Milestone Tracker (`shared/domain/milestone-tracker.js`)

#### 목적
연속 정답, 세션 누적, 첫 도전 마일스톤을 추적하고 토스트/배지로 피드백.

#### localStorage 키
```
aiden_milestones: {
  // 세션별 상태 (세션 시작 시 초기화, 종료 시 저장)
  session: {
    rocketStreak: 0,             // RocketCore와 공유 — 발사 시 리셋
    milestoneStreak: 0,          // 마일스톤 전용 — 세션/로켓 리셋 안 함
    sessionCorrect: 0,           // 세션 내 누적 정답 수
    firstAnswer: false,          // 첫 정답 달성 여부
    firstSubjectComplete: false, // 첫 과목 완료 여부
    firstRocket: false           // 첫 로켓 달성 여부
  },
  // 누적 통계 (세션 간 유지)
  lifetime: {
    totalCorrect: 0,             // 전체 누적 정답 수
    subjectsCompleted: [],       // 완료한 과목 목록 ['math', 'english', ...]
    totalRockets: 0              // 전체 로켓 발사 횟수
  },
  // 달성 이력 (토스트 표시 여부 추적)
  achieved: {
    // 연속 정답 마일스톤
    'streak_3': true,
    'streak_5': true,
    'streak_10': false,
    'streak_15': false,
    // 세션 누적 마일스톤
    'session_3': true,
    'session_5': false,
    'session_10': false,
    'session_20': false,
    // 첫 도전 마일스톤
    'first_answer': true,
    'first_subject_complete': false,
    'first_rocket': false
  }
}
```

#### API

```javascript
// 생성
const MilestoneTracker = {
  // 세션 시작 시 호출 (과목명)
  initSession(subject),
  
  // 정답/오답 기록 (recordResult 내부에서 호출)
  record(correct),
  
  // 세션 종료 시 호출 (10문제 풀이 후)
  endSession(),
  
  // 로켓 발사 시 호출 (RocketCore.launchRocket 후)
  onRocketLaunch(),
  
  // 과목 완료 시 호출 (10문제 풀이 후)
  onSubjectComplete(subject),
  
  // 마일스톤 달성 여부 확인
  getAchieved(milestoneKey),
  
  // 세션 데이터 리셋 (새 과목 진입 시)
  resetSessionData()
};
```

#### 마일스톤 임계값 및 피드백

| 키 | 조건 | 토스트 메시지 | 보석 |
|---|------|-------------|------|
| `streak_3` | 연속 3정답 | "3연속! 대단해! 🔥" | 0 |
| `streak_5` | 연속 5정답 | "5연속! 방패망 획득 준비! 🛡️" | 0 |
| `streak_10` | 연속 10정답 | "10연속! 무서워! 😱" | 0 |
| `streak_15` | 연속 15정답 | "15연속! 로켓 발사 임박! 🚀" | 0 |
| `session_3` | 세션 3정답 | "오늘 3문제 맞혔어! 👍" | 0 |
| `session_5` | 세션 5정답 | "세션 절반 이상! 5문제! 🌟" | +1 |
| `session_10` | 세션 10정답 | "완벽 세션! 10문제全정답! 💯" | +1 |
| `session_20` | 세션 20정답 | "20문제?! 진짜 천재야! 🏆" | +1 |
| `first_answer` | 첫 정답 | "첫 정답! 축하해! 🎉" | 0 |
| `first_subject_complete` | 첫 과목 완료 | "첫 과목 완료! 🎊" | 0 |
| `first_rocket` | 첫 로켓 | "첫 로켓 발사! 🚀✨" | 0 |

#### 구현 세부

- `record(correct)` 호출 시:
  - `correct`이면 `rocketStreak++`, `milestoneStreak++`, `sessionCorrect++`, `lifetime.totalCorrect++`
  - `correct`가 아니면 `rocketStreak = 0`, `milestoneStreak = 0`
  - 각 마일스톤 임계값 도달 시 `achieved` 체크 → 미달성 시 토스트 표시 + `achieved[key] = true`
- `initSession(subject)` 호출 시:
  - `sessionCorrect = 0` 리셋, `rocketStreak`/`milestoneStreak`는 유지
- `endSession()` 호출 시:
  - 세션 종료. 다음 과목 진입 전까지 상태 유지
- `onRocketLaunch()` 호출 시:
  - `lifetime.totalRockets++`, `first_rocket` 체크
  - `rocketStreak = 0` 리셋 (RocketCore와 동기화)
  - `milestoneStreak`는 **리셋 안 함** (마일스톤 계산용 별도 카운터)

#### streak 분리 관리 — RocketCore vs MilestoneTracker

**결정**: 연속 정답 streak를 2개로 분리하여 로켓 발사 시 마일스톤 영향 제거.

| 카운터 | 공유 대상 | 리셋 조건 | 용도 |
|--------|----------|----------|------|
| `rocketStreak` | RocketCore.updateStreak() | 로켓 발사 시 | 그물망/로켓 애니메이션 |
| `milestoneStreak` | MilestoneTracker 전용 | 오답 시만 | 마일스톤 토스트 (streak_3/5/10/15) |

- **이유**: RocketCore의 streak는 로켓 발사 시 0으로 리셋되는 것이 기존 동작. 마일스톤 streak도 함께 리셋되면 "수학 5연속 → 로켓 → 영어 3연속 = 총 0"이 되어 효능감이 떨어짐.
- **동기화**: `record(correct)`에서 두 streak를 동시에 증가시키되, 로켓 발사 시 `rocketStreak`만 리셋. `milestoneStreak`는 오답 시에만 0으로 리셋되어 세션/과목 전환 시에도 유지.
- **결과**: "수학 5연속 (로켓 발사, rocketStreak=0) → 영어 3연속 = milestoneStreak=3 → '3연속!' 토스트"

---

### 4.2 Daily Streak — 학습 기록 기반 (`shared/domain/daily-streak.js`)

#### 목적
하루에 정답 1개 이상 기록 = 출석 인정. 연속 일수 기반 보석 지급으로 학습 습관 형성.

#### localStorage 키
```
aiden_daily_streak: {
  currentStreak: 0,        // 현재 연속 출석 일수
  lastActiveDate: null,    // 마지막 활동 날짜 (YYYY-MM-DD)
  todayRecorded: false,    // 오늘 출석 기록 여부 (세션 내 중복 방지)
  history: {               // 과거 활동 기록 (최근 90일)
    '2026-06-01': true,
    '2026-06-02': true,
    '2026-06-03': false    // 누락일
  },
  gemAwarded: {            // 보석 지급 이력 (중복 지급 방지)
    '2026-06-01': 1,       // 날짜: 지급된 보석 수
    '2026-06-02': 1
  }
}
```

#### API

```javascript
const DailyStreak = {
  // recordResult 호출 시 (정답 시) — 중복 방지 포함
  recordAnswer(subject),
  
  // 자정 초기화 (page load 시 호출)
  checkMidnightReset(),
  
  // 현재 연속 일수 조회
  getCurrentStreak(),
  
  // 오늘 출석 여부
  isTodayActive()
};
```

#### 보석 지급 테이블

| 연속 일수 | 일일 보석 | 보너스 | 총 지급 |
|---------|----------|--------|--------|
| 1일 | +1 | — | +1 |
| 2일 | +1 | — | +1 |
| 3일 | +1 | +1 | **+2** |
| 4일 | +1 | — | +1 |
| 5일 | +1 | — | +1 |
| 6일 | +1 | — | +1 |
| 7일 | +1 | +1 | **+2** |
| 8일~ | +1 | — | +1 |

**규칙**:
- 누락 시 스택 **완전 리셋** (복구 없음)
- 하루에 **최대 1회만 보석 지급** (중복 방지)
- `lastActiveDate`가 어제이면: streak++
- `lastActiveDate`가 어제가 아니면(2일 전 이상): streak = 0 (리셋)
- 날짜 계산은 `YYYY-MM-DD` 문자열 비교 사용

#### 보석 경제 시뮬레이션 (하루 최대)

| 보상원 | 기존 | 새 계획 | 비고 |
|--------|------|--------|------|
| 로켓 (20연속) | +1 | +1 | 변경 없음 |
| 일일 출석 7일차 | — | **+2** | 3→2로 하향 |
| 과목 다양성 4과목 | — | **+2** | 3→2로 하향 |
| 마일스톤 session_20 | — | +1 | 변경 없음 |
| **하루 최대** | **+1** | **+5** | 기존 대비 5배 (허용 범위) |

> **결정**: 하루 최대 5보석으로 제한. 기존 로켓 1개 + α 4개. 일일 출석 7일차 보너스 3→2, 다양성 4과목 3→2로 하향 조정.

#### 구현 세부

```javascript
function getTodayKey() {
  return new Date().toISOString().split('T')[0]; // YYYY-MM-DD
}

function recordAnswer(subject) {
  const today = getTodayKey();
  
  // 오늘 이미 기록했으면 중복 방지
  if (state.todayRecorded && state.lastActiveDate === today) return;
  
  // 첫 활동이거나 연속 유지
  if (!state.lastActiveDate) {
    state.currentStreak = 1;
  } else {
    const last = new Date(state.lastActiveDate);
    const todayDate = new Date(today);
    const diffDays = Math.floor((todayDate - last) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) {
      // 연속 유지
      state.currentStreak++;
    } else if (diffDays > 1) {
      // 누락 — 완전 리셋
      state.currentStreak = 0;
    }
    // diffDays === 0 (같은 날) — 이미 기록됨 (위에서 return)
  }
  
  state.lastActiveDate = today;
  state.history[today] = true;
  
  // 보석 지급 (오늘 처음 기록인 경우만)
  if (!state.gemAwarded[today]) {
    const gems = calculateStreakGems(state.currentStreak);
    if (gems > 0) {
      state.gemAwarded[today] = gems;
      RewardSystem.add('gems', gems);
    }
  }
  
  save();
}

function calculateStreakGems(streak) {
  if (streak === 0) return 0;
  let gems = 1; // 기본 +1
  if (streak >= 3 && streak < 7) gems += 1; // 3일 연속 보너스 +1
  if (streak >= 7) gems += 1; // 7일 연속 보너스 +1 (3→2로 하향)
  return gems;
}
```

---

### 4.3 Diversity Reward (`shared/domain/diversity-reward.js`)

#### 목적
하루에 여러 과목에서 정답 기록 시 차등 보석 지급. 과목 편식 방지 + 전과목 유도.

#### localStorage 키
```
aiden_diversity: {
  today: '2026-06-13',       // 오늘 날짜 (YYYY-MM-DD)
  subjectsWithCorrect: [],   // 정답 기록 과목 목록 ['math', 'english']
  gemAwarded: false          // 오늘 보석 지급 여부
}
```

#### API

```javascript
const DiversityReward = {
  // recordResult 호출 시 (정답 시)
  recordCorrect(subject),
  
  // 자정 초기화
  checkMidnightReset(),
  
  // 오늘 과목 수 조회
  getTodaySubjectCount()
};
```

#### 보석 지급 테이블

| 과목 수 | 보석 | 조건 |
|--------|------|------|
| 1개 | 0 | 기본 — 보석 없음 |
| 2개 | +1 | 최소 다양성 달성 |
| 3개 | +2 | 적극적 학습 |
| 4개 | +2 | 전과목 정복! (3→2로 하향) |

**loophole 방지**: 정답 1개 이상 기록된 과목만 카운트 (오답만 풀면 카운트 안 됨).

#### 구현 세부

```javascript
function recordCorrect(subject) {
  checkMidnightReset();
  
  // 이미 기록된 과목이면 skip
  if (state.subjectsWithCorrect.includes(subject)) return;
  
  state.subjectsWithCorrect.push(subject);
  
  // 보석 지급 (오늘 처음 보석 받는 경우)
  if (!state.gemAwarded) {
    const gems = getDiversityGems(state.subjectsWithCorrect.length);
    if (gems > 0) {
      state.gemAwarded = true;
      RewardSystem.add('gems', gems);
    }
  }
  
  save();
}

function getDiversityGems(subjectCount) {
  if (subjectCount >= 4) return 2; // 3→2로 하향
  if (subjectCount >= 3) return 2;
  if (subjectCount >= 2) return 1;
  return 0;
}

function checkMidnightReset() {
  const today = getTodayKey();
  if (state.today !== today) {
    state.today = today;
    state.subjectsWithCorrect = [];
    state.gemAwarded = false;
    save();
  }
}
```

#### 과목명 매핑

각 engine.js에서 호출할 때 전달할 과목명:
- math → `'math'`
- english → `'english'`
- korean → `'korean'`
- science → `'science'`

---

### 4.4 Growth Visualizer (`shared/domain/growth-visualizer.js`)

#### 목적
3가지 성장 피드백: 난이도 상승 토스트, 주간 성장 요약, 숙련도 표시바.

#### API

```javascript
const GrowthVisualizer = {
  // 난이도 상승 감지 시 호출 (getDifficultyLevel 후 이전 레벨과 비교)
  checkLevelUp(subject, oldLevel, newLevel),
  
  // 숙련도 바 표시 (과목 진입 시 호출)
  showProficiencyBar(subject),
  
  // 주간 성장 요약 데이터 조회 (리워드 페이지 탭용)
  getWeeklySummary()
};
```

#### 4.4.1 난이도 상승 토스트

- **트리거**: `recordResult` 후 `getDifficultyLevel()` 호출. 이전 레벨과 비교하여 상승 시 토스트 표시.
- **토스트 메시지**: `"수학 2단계 → 3단계 올랐어! 🎉"` (숙련, 마스터 등 라벨 사용)
- **표시 위치**: 게임 화면 하단 (기존 net-banner 스타일 재활용)
- **중복 방지**: 세션당 1회만 표시 (같은 과목 연속 상승 시에도 1회)

#### 4.4.2 숙련도 표시바

- **트리거**: 과목 페이지 진입 시 (`askQuestion` 전)
- **계산 방식**: 각 과목의 전체 정확도 (correct / attempts * 100)
- **데이터 소스**: `ProgressEngine.loadStats()`로 localStorage에서 통계 로드
- **표시 위치**: 문제 상단 (q-count 옆 또는 대체)
- **디자인**: 0-100% 진행바. 색상: 레벨에 따라 변경 (기존 DIFF_COLORS 재활용)

```javascript
function showProficiencyBar(subject) {
  const statsKey = ProgressEngine.createStatsKey(subject);
  const domainKeys = getDomainKeysForSubject(subject); // engine.js마다 상이
  const stats = ProgressEngine.loadStats(statsKey, domainKeys);
  
  let totalAttempts = 0, totalCorrect = 0;
  
  for (const domain of domainKeys) {
    for (let level = 0; level <= 6; level++) {
      const lv = stats[domain]?.levels[level];
      if (lv) {
        totalAttempts += lv.attempts;
        totalCorrect += lv.correct;
      }
    }
  }
  
  const proficiency = totalAttempts > 0 
    ? Math.round((totalCorrect / totalAttempts) * 100) 
    : 0;
  
  // DOM에 진행바 삽입 (또는 기존 요소 업데이트)
  const bar = document.getElementById('proficiency-bar');
  if (bar) {
    bar.style.width = proficiency + '%';
    bar.textContent = `${proficiency}%`;
  }
}

function getDomainKeysForSubject(subject) {
  // engine.js마다 DOMAIN_KEYS가 다름 → GrowthVisualizer는 engine.js에서 주입받음
  // 예: window.__subjectDomainKeys['math'] = ['+', '-', '×']
  return window.__subjectDomainKeys?.[subject] || [];
}
```

> **변경**: 기존 `loadStatsForSubject()`/`getDomainKeys()` 미정의 문제 해결. ProgressEngine.loadStats() 직접 호출 + engine.js에서 DOMAIN_KEYS 주입 방식으로 변경.

#### 4.4.3 주간 성장 요약

- **트리거**: 리워드 페이지(guardian) 탭 전환 시
- **데이터 범위**: 최근 7일간의 세션별 학습 기록 (session-log 기반)
- **표시 방식**: 테이블 또는 카드 UI

##### 세션 로그 스키마 (신규)

시간별 기록이 없으므로, 세션 종료 시 `aiden_session_log`에 요약 기록을 남긴다.

```
aiden_session_log: {
  '2026-06-07': [
    {
      time: '2026-06-07T14:30:00.000Z',
      subject: 'math',
      correct: 8,
      total: 10,
      domains: { '+': { correct: 3, total: 4 }, '-': { correct: 3, total: 3 }, '×': { correct: 2, total: 3 } }
    },
    {
      time: '2026-06-07T15:00:00.000Z',
      subject: 'english',
      correct: 6,
      total: 10,
      domains: { animals: { correct: 2, total: 3 }, fruits: { correct: 4, total: 7 } }
    }
  ],
  '2026-06-10': [ ... ]
}
```

**기록 타이밍**: `MilestoneTracker.endSession()` 호출 시, 또는 10문제 풀이 완료 시.
**저장 크기**: 세션당 ~200바이트 × 하루 10세션 × 90일 = ~180KB (localStorage 제한 내).

##### 주간 요약 구현

```javascript
function getWeeklySummary() {
  const log = loadSessionLog();
  const subjects = ['math', 'english', 'korean', 'science'];
  const summary = {};
  
  const now = new Date();
  const thisWeekStart = new Date(now);
  thisWeekStart.setDate(now.getDate() - now.getDay()); // 이번 주 일요일
  
  const lastWeekStart = new Date(thisWeekStart);
  lastWeekStart.setDate(thisWeekStart.getDate() - 7); // 전주 일요일
  
  for (const subject of subjects) {
    // 이번 주 세션
    const thisWeekSessions = log.filter(entry => {
      const d = new Date(entry.time);
      return entry.subject === subject && d >= thisWeekStart && d <= now;
    });
    
    // 전주 세션
    const lastWeekSessions = log.filter(entry => {
      const d = new Date(entry.time);
      return entry.subject === subject && d >= lastWeekStart && d < thisWeekStart;
    });
    
    const thisWeekCorrect = thisWeekSessions.reduce((s, e) => s + e.correct, 0);
    const thisWeekTotal = thisWeekSessions.reduce((s, e) => s + e.total, 0);
    const lastWeekCorrect = lastWeekSessions.reduce((s, e) => s + e.correct, 0);
    
    summary[subject] = {
      thisWeekSessions: thisWeekSessions.length,
      lastWeekSessions: lastWeekSessions.length,
      sessionChange: thisWeekSessions.length - lastWeekSessions.length, // 세션 수 변화
      thisWeekCorrect,
      lastWeekCorrect,
      correctChange: thisWeekCorrect - lastWeekCorrect, // 정답 수 변화
      avgAccuracy: thisWeekTotal > 0 
        ? Math.round((thisWeekCorrect / thisWeekTotal) * 100) 
        : 0
    };
  }
  
  return summary;
}

function recordSessionEnd(subject, results) {
  // results: [{correct, total, domains}, ...] per domain
  const log = loadSessionLog();
  const today = getTodayKey();
  
  if (!log[today]) log[today] = [];
  
  for (const domain of Object.keys(results)) {
    log[today].push({
      time: new Date().toISOString(),
      subject,
      correct: results[domain].correct,
      total: results[domain].total,
      domains: { [domain]: { correct: results[domain].correct, total: results[domain].total } }
    });
  }
  
  // 최근 90일만 유지
  const dates = Object.keys(log).sort();
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 90);
  const cutoffKey = getTodayKeyFrom(cutoff);
  
  for (const date of dates) {
    if (date < cutoffKey) delete log[date];
  }
  
  saveSessionLog(log);
}
```

**UI 레이아웃 (guardian/index.html 탭 추가)**:

```
┌──────────────────────────────────────────┐
│  [수학] [영어] [국어] [과학] [성장]      │  ← 새 탭 추가
├──────────────────────────────────────────┤
│                                          │
│   📊 주간 성장 요약                       │
│   ──────────────────────────             │
│                                          │
│   📈 수학      +2세션  (85% 정확도)      │
│   → 영어      -1세션  (60% 정확도)       │
│   📈 국어      +1세션  (72% 정확도)      │
│   → 과학      →세션   (68% 정확도)       │
│                                          │
│   이번 주 총 학습: 4세션, 47문제          │
│   전주 대비 정답: +12문제                │
│                                          │
│   가장 강한 과목: 수학 (85% 정확도)      │
│   성장 필요 과목: 영어 (60% 정확도)      │
│                                          │
└──────────────────────────────────────────┘
```

> **변경 사유**: 기존 계획(7일 전 난이도 비교)은 시간별 기록이 없어 불가능. 세션 로그 스키마를 신규 추가하여 세션 수/정답 수 변화로 대체.

---

## 5) 통합 설계 — engine.js 연동점

### 5.1 연동 호출 위치

모든 4개 과목 engine.js의 `recordResult(correct, elapsed)` 함수에서:

```javascript
function recordResult(correct, elapsed) {
  // ── 기존 로직 (변경 없음) ──
  ProgressEngine.recordResultCore({ ... });
  saveStats();
  RocketCore.updateStreak(correct); // rocketStreak 관리 — 발사 시 리셋
  
  // ── NEW: 마일스톤 연동 (milestoneStreak 관리 — 리셋 안 함) ──
  if (typeof MilestoneTracker !== 'undefined') {
    MilestoneTracker.record(correct); // 내부에서 rocketStreak는 읽기만 함
  }
  
  // ── NEW: 일일 출석 연동 (정답 시만) ──
  if (correct && typeof DailyStreak !== 'undefined') {
    DailyStreak.recordAnswer(SUBJECT_NAME); // 예: 'math'
  }
  
  // ── NEW: 과목 다양성 연동 (정답 시만) ──
  if (correct && typeof DiversityReward !== 'undefined') {
    DiversityReward.recordCorrect(SUBJECT_NAME);
  }
  
  // ── 기존 로직 (변경 없음) ──
  // 그물망 시스템, 틀린 패턴 기록, etc.
}
```

> **중요**: `RocketCore.updateStreak()`와 `MilestoneTracker.record()`는 **별도 streak**를 관리. 로켓 발사 시 rocketStreak만 리셋, milestoneStreak는 유지.

### 5.2 과목명 상수 추가

각 engine.js에 과목명 상수 추가 (DOMAIN_KEY 대신 SUBJECT_NAME 사용):

```javascript
// math/engine.js
const SUBJECT_NAME = 'math';

// english/engine.js
const SUBJECT_NAME = 'english';

// korean/engine.js
const SUBJECT_NAME = 'korean';

// science/engine.js
const SUBJECT_NAME = 'science';
```

> **변경**: 기존 계획의 `DOMAIN_KEY` → `SUBJECT_NAME`. domainKey (예: '+', '-', '×')와 혼동 방지를 위해 명확한 명칭 사용.

### 5.3 난이도 상승 감지

`recordResult` 내 `saveStats()` 후 난이도 비교:

```javascript
// recordResult 내 saveStats() 후
const prevLevel = getDifficultyLevel(currentOp); // 또는 currentCat

// ... stats 업데이트 ...
saveStats();

const newLevel = getDifficultyLevel(currentOp); // 또는 currentCat

if (newLevel > prevLevel && typeof GrowthVisualizer !== 'undefined') {
  GrowthVisualizer.checkLevelUp(SUBJECT_NAME, prevLevel, newLevel);
}
```

### 5.4 스크립트 로드 순서

각 과목 index.html의 script 태그 순서:

```html
<!-- 기존 스크립트 -->
<script src="../../shared/event-bus.js"></script>
<script src="../../shared/domain/progress-engine.js"></script>
<script src="../../shared/ui/quiz-ui-core.js"></script>
<script src="../../shared/ui/rocket-core.js"></script>
<script src="../../shared/ui/rocket-effects.js"></script>
<script src="rocket.js"></script>

<!-- NEW: 효능감 시스템 (기존 이후 로드) -->
<script src="../../shared/domain/milestone-tracker.js"></script>
<script src="../../shared/domain/daily-streak.js"></script>
<script src="../../shared/domain/diversity-reward.js"></script>
<script src="../../shared/domain/growth-visualizer.js"></script>

<!-- 기존 엔진 -->
<script src="engine.js"></script>
<script src="ui.js"></script>
```

---

## 6) reward.js 확장

### 6.1 보석 획득 경로 통합

기존 `RewardSystem.add('gems', n)` 호출 위치:

| 현재 | 새 경로 | 비고 |
|------|--------|------|
| `showBoostBanner()` → `playEntranceAndAddGem()` → `add('gems', 1)` | 유지 (로켓 발사) | 변경 없음 |
| — | `DailyStreak.recordAnswer()` → `add('gems', 1~2)` | 7일차 보너스 3→2로 하향 |
| — | `DiversityReward.recordCorrect()` → `add('gems', 1~2)` | 4과목 보너스 3→2로 하향 |
| — | `MilestoneTracker` session_5/10/20 → `add('gems', 1)` | 변경 없음 |

**하루 최대 보석**: 기존 +1 (로켓) → 새 계획 +5 (로켓 1 + 출석 2 + 다양성 2)

### 6.2 수정 위치

`reward.js`의 `add()` 함수는 기존 유지. 새 모듈들이 `RewardSystem.add('gems', n)`을 직접 호출하면 됨. 추가 수정 불필요.

---

## 7) reward_ui.js 수정

### 7.1 성장 토스트 함수 추가

```javascript
// GrowthVisualizer에서 호출하는 토스트 표시 함수
function showGrowthToast(message) {
  const toast = document.createElement('div');
  toast.className = 'growth-toast'; // 별도 CSS 클래스
  toast.textContent = message;
  document.body.appendChild(toast);
  
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });
  
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 500);
  }, 3000);
}
```

### 7.2 CSS 추가

```css
/* growth-toast 스타일 (net-banner와 유사하지만 다른 색상) */
.growth-toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%) translateY(100px);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 24px;
  border-radius: 16px;
  font-size: 1.1rem;
  font-weight: bold;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
  z-index: 5000;
  opacity: 0;
  transition: all 0.4s cubic-bezier(0.2, 0.9, 0.2, 1);
}

.growth-toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* 숙련도 바 스타일 */
.proficiency-bar-container {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  margin-top: 8px;
  overflow: hidden;
}

.proficiency-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}
```

---

## 8) guardian/index.html 수정

### 8.1 주간 성장 요약 탭 추가

기존 보호자 페이지의 과목 탭(수학/영어/국어/과학) 옆에 **"주간 성장"** 탭 추가.

### 8.2 탭 레이아웃

```
┌──────────────────────────────────────────┐
│  [수학] [영어] [국어] [과학] [성장]      │  ← 새 탭 추가
├──────────────────────────────────────────┤
│                                          │
│   📊 주간 성장 요약                       │
│   ──────────────────────────             │
│                                          │
│   📈 수학      +2세션  (85% 정확도)      │
│   → 영어      -1세션  (60% 정확도)       │
│   📈 국어      +1세션  (72% 정확도)      │
│   → 과학      →세션   (68% 정확도)       │
│                                          │
│   이번 주 총 학습: 4세션, 47문제          │
│   전주 대비 정답: +12문제                │
│                                          │
│   가장 강한 과목: 수학 (85% 정확도)      │
│   성장 필요 과목: 영어 (60% 정확도)      │
│                                          │
└──────────────────────────────────────────┘
```

> **변경**: 기존 (난이도 변화) → (세션 수 변화 + 정답 수 변화). 세션 로그 스키마 기반.

### 8.3 구현 세부

- 기존 탭 구조에 `id="tab-growth"` 추가
- 탭 클릭 시 `GrowthVisualizer.getWeeklySummary()` 호출 → 데이터 렌더링
- 성장 탭은 읽기 전용 (수정 기능 없음)

---

## 9) 데이터 흐름 종합

```
사용자 정답 클릭
  │
  ├─→ engine.js: recordResult(correct)
  │     │
  │     ├─→ ProgressEngine.recordResultCore()
  │     │     └─ localStorage: aiden_{subject}_stats 업데이트
  │     │
  │     ├─→ RocketCore.updateStreak(correct)
  │     │     ├─ streak >= 20 → launchRocket() → RewardSystem.add('gems', 1)
  │     │     └─ netStreak >= 5 → hasNet = true
  │     │
  │     ├─→ MilestoneTracker.record(correct)
  │     │     ├─ streak_3/5/10/15 → 토스트 표시
  │     │     ├─ session_3/5/10/20 → 토스트 + 보석 (session_5+/10+/20+)
  │     │     └─ first_answer/subject_complete/rocket → 토스트
  │     │
  │     ├─→ DailyStreak.recordAnswer(subject) [correct일 때만]
  │     │     └─ streak 보석 지급 → RewardSystem.add('gems', n)
  │     │
  │     ├─→ DiversityReward.recordCorrect(subject) [correct일 때만]
  │     │     └─ diversity 보석 지급 → RewardSystem.add('gems', n)
  │     │
   │     └─→ GrowthVisualizer.checkLevelUp(subject, oldLv, newLv)
   │           └─ 난이도 상승 토스트 표시
   │
   └─→ (세션 종료 시)
         ├─→ MilestoneTracker.endSession()
         │     └─→ recordSessionEnd(subject, results) → aiden_session_log 저장
         └─→ MilestoneTracker.onSubjectComplete(subject)
```

---

## 10) edge cases & 고려사항

### 10.1 중복 보석 지급 방지

- **일일 출석**: `gemAwarded[today]` 체크로 하루 1회 제한
- **과목 다양성**: `gemAwarded` boolean으로 하루 1회 제한
- **마일스톤 세션누적**: `achieved` 객체로 세션 내 중복 방지
- **중복 가능 여부**: 일일 출석 + 다양성 + 마일스톤 보석은 **중복 지급 허용** (다른 조건이므로)

### 10.2 세션 간 상태 유지

- **마일스톤 streak (milestoneStreak)**: 세션 간 유지 (과목 전환 시에도 리셋 안 됨). 로켓 발사 시에도 리셋 안 됨. 오답 시에만 0으로 리셋.
- **로켓 streak (rocketStreak)**: RocketCore와 공유. 로켓 발사 시 0으로 리셋.
- **세션 누적 마일스톤**: 과목별 세션에서 리셋되지만, `session_5` 등 달성 시 `achieved`에 기록되어 재차 표시 안 됨.
- **일일 출석**: 날짜 기준 (YYYY-MM-DD). 자정 넘으면 새 streak 계산. `checkMidnightReset()`는 page load 시 + `visibilitychange` 이벤트 시 호출.
- **과목 다양성**: 날짜 기준. 자정 넘으면 초기화. `checkMidnightReset()`는 page load 시 + `visibilitychange` 이벤트 시 호출.
- **세션 로그**: 세션 종료 시 `aiden_session_log`에 기록. 최근 90일만 유지, 그 이상은 자동 삭제.

### 10.3 로컬스토리지 용량

- 마일스톤, 출석, 다양성, 성장 데이터 총 예상 크기: < 2KB
- 세션 로그: 세션당 ~200바이트 × 하루 10세션 × 90일 = ~180KB
- localStorage 제한 (5-10MB)에 무리 없음
- 세션 로그는 90일 초과 시 자동 삭제 (recordSessionEnd 내 로직)

### 10.4 SyncEngine 연동

- 현재 계획: localStorage만 사용
- `daily-streak.js`와 `diversity-reward.js`의 `save()`에서 `SyncEngine` 호출 추가 가능 (추후)
- `milestone-tracker.js`도 동일

### 10.5 검증 스크립트 호환성

- 기존 검증 스크립트(`verify_math_engine.js` 등)는 `MilestoneTracker`, `DailyStreak` 등이 undefined일 때 gracefully skip하도록 설계
- 모든 새 모듈은 `typeof ModuleName !== 'undefined'` 체크 후 호출

---

## 11) 구현 순서 및 의존성

### Phase 1: 마일스톤 시스템 (가장 독립적)

**파일**: `shared/domain/milestone-tracker.js`

1. MilestoneTracker 모듈 생성 (rocketStreak/milestoneStreak 분리)
2. 4개 과목 engine.js에 연동 (`MilestoneTracker.record()`)
3. index.html에 스크립트 로드 추가
4. 토스트 UI는 `reward_ui.js`에 함수로 추가

**의존성**: 없음 (RewardSystem의 보석 기능만 사용)

### Phase 2: 일일 출석

**파일**: `shared/domain/daily-streak.js`

1. DailyStreak 모듈 생성
2. `checkMidnightReset()`를 page load 시 + `visibilitychange` 이벤트 시 호출하도록 설계
3. 4개 과목 engine.js에 연동 (`DailyStreak.recordAnswer()`)
4. index.html에 스크립트 로드 추가

**의존성**: RewardSystem.add()

### Phase 3: 과목 다양성 보상

**파일**: `shared/domain/diversity-reward.js`

1. DiversityReward 모듈 생성
2. 4개 과목 engine.js에 연동 (`DiversityReward.recordCorrect()`)
3. index.html에 스크립트 로드 추가

**의존성**: RewardSystem.add()

### Phase 4: 성장 시각화

**파일**: `shared/domain/growth-visualizer.js`, `reward_ui.js`, `guardian/index.html`

1. GrowthVisualizer 모듈 생성
2. reward_ui.js에 성장 토스트 CSS/함수 추가
3. 4개 과목 engine.js에 난이도 상승 감지 연동
4. index.html에 스크립트 로드 추가
5. 숙련도 바 UI (index.html 또는 ui.js에 progress bar 요소 추가)
6. `recordSessionEnd()` 함수를 milestone-tracker.js의 endSession()에서 호출하도록 연동
7. guardian/index.html에 주간 성장 요약 탭 추가 (세션 로그 기반)

**의존성**: ProgressEngine (난이도 계산), reward_ui.js, milestone-tracker.js (세션 로그)

---

## 12) 테스트 계획

### 12.1 단위 테스트 (Python pytest — 로직 검증)

```
tests/
  test_milestone_logic.py      ← milestone-tracker.js streak 분리 로직 검증
  test_daily_streak_logic.py   ← daily-streak.js 보석 계산 로직 검증
  test_diversity_logic.py      ← diversity-reward.js 보석 계산 로직 검증
  test_session_log_logic.py    ← session log 저장/90일 자동삭제 로직 검증
```

각 테스트는 localStorage 시뮬레이션 없이, 모듈의 핵심 로직을 Python으로 재현하여 검증.
보석 지급 총량 시뮬레이션 포함 (하루 최대 5보석 확인).

### 12.2 통합 테스트 (브라우저 E2E — Playwright)

```
tests/
  test_efficacy_e2e.py         ← 브라우저 자동화 E2E 테스트
```

**테스트 시나리오**:

1. `test_milestone_streak_toast`: 수학 세션에서 3연속 정답 → "3연속!" 토스트 표시 확인
2. `test_milestone_session_gems`: 영어 세션에서 5문제 정답 → "5문제!" 토스트 + 보석 +1 확인
3. `test_diversity_reward`: 하루에 수학+영어 풀이 → 다양성 보석 +1 확인
4. `test_daily_streak_simulation`: 7일 연속 출석 시뮬레이션 → 보석 +2 확인 (3→2로 하향)
5. `test_level_up_toast`: 난이도 상승 시 → 토스트 표시 확인
6. `test_weekly_summary_tab`: guardian 페이지 성장 탭 → 세션 수/정답 수 변화 표시 확인
7. `test_streak_separation`: 로켓 발사 후 milestoneStreak 유지 확인 (rocketStreak만 리셋)
8. `test_gem_economy_cap`: 하루 최대 보석 5개 초과 지급 방지 확인

**구현 도구**: Playwright (또는 Puppeteer). `just lint-turn-end` 전 E2E 테스트 PASS 필수.

---

## 13) 리팩토링 고려사항 (추후)

### 13.1 engine.js의 recordResult 함수 통합

현재 4개 과목 engine.js의 `recordResult()`가 유사한 구조. 새 모듈 연동 후 공통 함수로 추출 고려:

```javascript
// shared/domain/game-session.js (NEW — 추후)
function createGameSession(subject, config) {
  return {
    recordResult(correct, elapsed) {
      // 공통 로직: ProgressEngine, RocketCore, MilestoneTracker, DailyStreak, DiversityReward
    }
  };
}
```

### 13.2 토스트/배지 UI 통합

현재 `reward_ui.js.showToast()`와 새 `showGrowthToast()`가 분리됨. 추후 통합 토스트 시스템으로 통합 고려.
