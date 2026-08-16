# AidenGame Active Product Scope

- **Status:** `CANONICAL_ACTIVE_PRODUCT_SSOT`
- **Effective:** 2026-08-16
- **Owner:** product direction only
- **Does not own:** Git/workspace procedure, generic verification procedure, feature-internal implementation details

이 문서는 AidenGame의 **현재 제품 방향, 우선순위, 제품 경계와 다음 개발 sequence를 단독 소유하는 제품 SSOT**다.
제품 방향을 다른 README, runbook, 완료 보고, 과거 plan에 복제하지 않는다. 다른 문서는 이 파일을 가리킨다.

충돌 시 사용자의 현재 요청과 `AGENTS.md`의 실행 규칙을 우선하고, 제품 의미·우선순위에 대해서는 이 문서를 `PROJECT_RULES.md`와 개별 feature spec보다 먼저 해석한다.

## 1. Product definition

AidenGame은 **초등 저학년 어린이가 Galaxy Tab에서 스스로 매일 들어와 학습하고, 실제 세부 skill mastery를 높이며, 학습 완료 후 게임과 현실 보상을 얻는 개인용 local-first 학습 게임 플랫폼**이다.

제품 성공 우선순위는 다음과 같다.

1. 아이가 자발적으로 다시 들어온다.
2. 부모 도움 없이 핵심 학습 흐름을 사용할 수 있다.
3. 실제 학습 성취가 누적된다.

재미를 위해 학습 효과를 제거하지 않고, 학습 효과를 위해 제품을 숙제 UI로 만들지 않는다.

## 2. Primary user and device

- 현재 1차 운영 대상은 가족/개인 사용이다. 장기적으로 공개 서비스 가능성을 열어 두되, 현재 backend·account·규제 대응을 선행 개발하지 않는다.
- 초기 학습 기준은 초등 저학년이며, **실제 사용하는 아이의 현재 수준을 canonical target**으로 삼고 성장에 맞춰 범위를 확장한다.
- 기준 기기는 **Galaxy Tab S10급 Android 태블릿**이다.
- UX는 **landscape-first**로 설계하되 portrait, split-screen, resize에서 핵심 기능이 깨지지 않아야 한다.
- 읽기 능력은 기본 전제다. TTS는 접근성 또는 일부 과목 보조 기능이며 전면 voice-guided 제품을 목표로 하지 않는다.

## 3. Current development priority

현재 최우선 개발 방향은 **curriculum-aligned skill mastery와 adaptive daily learning loop**다.

첫 vertical slice는 **Math**다. 수학에서 모델을 검증한 뒤 English → Korean → Science로 확장한다. 네 과목 전체 taxonomy를 먼저 설계하지 않는다.

기존 4과목 문제풀이 reliability stabilization은 완료된 baseline이다. 동일 결함이 최신 main에서 재현되지 않는 한 다시 현재 제품 단계로 승격하지 않는다.

### Sequence

1. **Math skill model** — 기존 문제를 현행 교육과정 기반의 작은 `skillId` 집합에 매핑한다.
2. **Mastery Engine v1** — 설명 가능한 deterministic mastery update를 구현한다.
3. **Adaptive Daily Learning** — mastery에서 오늘의 skill goal과 다음 문제를 선택한다.
4. **Learning → Reward → Ocean Rescue** — 목표 완료가 보석과 자유시간을 부여하고 Ocean Rescue 접근을 연다.
5. **Guardian + persistence** — 약점/성장, preset 목표, 보상 상점, streak, export/import를 연결한다.
6. 수학에서 검증된 계약만 다른 과목으로 확장한다.

이 순서는 제품 dependency를 뜻한다. 진행률을 이 문서에 계속 기록하거나 완료 체크리스트로 사용하지 않는다.

## 4. Learning model

### 4.1 Skill representation

- 적응 단위는 과목 전체 난이도나 단순 level이 아니라 **세부 skill mastery**다.
- skill graph의 curriculum 기준은 **현행 대한민국 초등학교 교육과정**이다.
- skill ID는 안정적인 의미 단위여야 하고, UI 문구나 문제 번호를 identity로 사용하지 않는다.
- 처음에는 수학의 현재 문제 세트에 필요한 최소 skill만 만든다.

예시 형태:

```text
math.add.within_10
math.subtract.within_10
math.compare_numbers
math.add.within_20.no_carry
math.add.within_20.carry
```

정확한 skill 목록은 실제 현행 교육과정과 현재 콘텐츠를 대조해 별도 구현 작업에서 결정한다.

### 4.2 Evidence and mastery

학습 evidence는 최소 다음 정보를 보존한다.

- `skillId`
- correctness
- first-attempt 여부 또는 attempts
- response time
- practiced time
- 문제/콘텐츠 identity가 필요한 경우의 안정적 참조

Mastery v1은 deterministic하고 설명 가능해야 한다. correctness, 시도 수, 반응 시간, 최근 evidence와 spaced review를 사용할 수 있지만, 초기부터 복잡한 확률 모델을 도입하지 않는다.

충분한 실제 데이터가 축적된 뒤 BKT 계열 모델을 검토할 수 있다. 모델 변경 가능성을 위해 raw learning evidence를 버리지 않는다.

### 4.3 Adaptive selection

다음 문제 선택은 **약점 개선과 성공 경험의 균형**을 목표로 한다.

- 현재 학습 target
- 이미 숙달한 skill의 spaced review
- 아이가 성공 경험을 유지할 수 있는 적절히 쉬운 문제

을 섞는다. 고정 비율은 아직 제품 계약이 아니다.

숙달한 skill을 완전히 제거하지 않고 빈도를 낮춰 복습한다.

오답 후 재시도 또는 설명 후 유사 문제 제공은 runtime LLM 판단이 아니라 문제/skill metadata의 deterministic remediation policy를 따른다.

### 4.4 Child vs guardian presentation

- 아이 화면에는 mastery percentage나 약점 수치를 직접 노출하지 않는다.
- 아이 progression은 **오늘 목표, streak, 보석, collection/unlock** 중심이다.
- 보호자에게는 skill별 약점과 성장 정보를 더 자세히 제공한다.

## 5. Daily learning loop

- 시스템이 오늘의 **skill 목표**를 추천한다.
- 아이는 추천 외 다른 과목을 선택할 수 있다.
- 기본 completion 단위는 단순 문제 수나 시간 채우기가 아니라 skill goal이다.
- 현재 목표를 완료해야 Ocean Rescue 자유시간을 사용할 수 있다.
- 목표 완료는 보석과 자유시간을 부여한다. 정확한 보상량은 별도 product configuration으로 조정할 수 있으며 이 문서에 고정하지 않는다.

제품 loop:

```text
추천 skill goal
→ 문제 풀이
→ learning evidence 기록
→ mastery 갱신
→ goal 완료
→ gems + free-time
→ Ocean Rescue / 허용된 자유시간 콘텐츠
```

## 6. Ocean Rescue and game layer

Ocean Rescue는 **학습 문제를 내부에 삽입하는 교육게임이 아니라 학습 완료 후 즐기는 실제 보상 게임**이다.

- Core Quiz에서 학습한다.
- 학습 목표 완료가 Ocean Rescue 접근을 연다.
- Ocean Rescue gameplay 안에 산수/퀴즈 문제를 억지로 삽입하지 않는다.
- Ocean Rescue는 현재 제품의 active feature이며 차세대 게임 경험의 대표작이다.
- 다만 현재 기본 구현 우선순위는 Math mastery/adaptive loop다. 명시적 Ocean Rescue 범위 요청은 별도 feature work로 수행할 수 있다.

### Allowed game/reward depth

허용:

- gems
- streak
- cosmetic / collection
- game/content unlock
- 여러 학습 영역과 공유되는 단순 reward
- Guardian Shop의 현실 보상

지양/비목표:

- 캐릭터 레벨업 중심 구조
- 장비 stat과 power progression
- 거대한 월드/quest tree
- RPG식 끝없는 meta progression
- 복잡한 game economy 자체가 제품 목적이 되는 구조

보석은 Guardian Shop 현실 보상과 cosmetic/unlock에 사용할 수 있다. 현실 보상 구매 시 보석은 실제로 차감한다.

## 7. Guardian and streak

- 보호자는 복잡한 LMS가 아니라 **간단한 preset 목표**를 추가한다.
- 현재는 같은 태블릿에서 보호자 진입을 우선하고, 장기적으로 부모 스마트폰 접근을 검토한다.
- cloud sync가 없어도 보호 가능한 **export/import backup**을 제공하는 방향을 우선한다.
- streak를 놓쳤을 때 전부 0으로 초기화하지 않고 일부 감소시키는 방향을 사용한다.

## 8. Content and LLM boundary

- 콘텐츠는 사람 작성 또는 template/parameter generation을 중심으로 한다.
- LLM은 **콘텐츠 제작 보조**에 사용할 수 있지만 검증된 canonical content만 배포한다.
- runtime에서 LLM이 문제를 즉석 생성하지 않는다.
- runtime에서 LLM이 mastery, 난이도, remediation 또는 다음 문제를 판단하지 않는다.
- adaptive engine은 검증 가능하고 재현 가능한 deterministic 계약에서 시작한다.

## 9. Runtime and architecture direction

하나의 기술스택으로 통일하는 것을 제품 목표로 삼지 않는다.

- Core Quiz는 단순 HTML/CSS/JavaScript 구조를 유지할 수 있다.
- Ocean Rescue는 현재 복잡도에 맞는 Vite/TypeScript/PixiJS build/runtime 경계를 유지할 수 있다.
- 미래 게임은 제품 필요에 맞는 runtime을 선택할 수 있다.
- 공통화 우선 대상은 framework가 아니라 **skill, mastery, reward, free-time 같은 domain meaning과 persistence contract**다.
- 전체 TypeScript 전환, framework migration, backend 도입을 현재 milestone의 전제조건으로 만들지 않는다.

## 10. Persistence and network direction

- 현재 데이터 ownership은 **local-first**다.
- UX는 online-first여도 되며 완전 offline 제품을 현재 목표로 하지 않는다.
- cloud sync는 있으면 좋은 장기 기능이지 현재 필수 조건이 아니다.
- 현재 우선은 local persistence의 신뢰성 + export/import backup이다.
- 별도 backend API, account system, Google/Samsung account 연동을 지금 선행 개발하지 않는다.

## 11. Explicit non-goals for the current phase

다음은 현재 기본 개발 backlog로 만들지 않는다.

- 새로운 대형 게임 추가
- Space Explorer 신규 개발
- RPG/meta-game 확장
- 모든 runtime의 framework 통일
- 전체 TypeScript 전환
- backend/cloud sync/account system
- runtime LLM
- runtime AI 문제 생성
- BKT부터 시작하는 학습 모델 과설계
- 네 과목 전체 skill taxonomy 선설계
- offline-complete architecture
- 제품 loop와 무관한 전면 UI 리디자인
- 제품 기능과 무관한 governance/harness 확장

## 12. Feature status

| Surface | Current role |
|---|---|
| Math / English / Korean / Science Core Quiz | 운영중; reliability baseline 완료; adaptive learning의 학습 surface |
| Math mastery/adaptive loop | **현재 최우선 개발 영역** |
| Ocean Rescue | active reward-game product; 학습 완료 후 이용 |
| Guardian / Reward | active supporting product surface; mastery loop 뒤에서 통합 |
| Space Explorer | `PAUSED_REFERENCE_ONLY`; 명시적 방향 변경 전 신규 개발 금지 |
| YouTube/free-time | 별도 승인된 feature contract가 있을 수 있으나 현재 기본 priority를 자동 변경하지 않음 |

## 13. Current external baselines

제품 구현 시 날짜가 바뀔 수 있는 외부 기준은 작업 시 다시 검증한다. 2026-08-16 기준 최소 baseline은 다음과 같다.

- 2022 개정 교육과정은 2026-03-01부터 초등학교 5·6학년까지 적용되어 초등 전 학년 rollout 단계에 들어갔다. Skill graph 작성 시 과거 2015 교육과정이 아니라 현행 원문/개정 고시를 확인한다. 공식 안내: https://ncic.go.kr/board/B0031.cs?act=read&bwrId=1271&pageIndex=1&pageUnit=15
- Chrome 151 stable은 2026-07-28 배포되었고 Android를 포함한다. Galaxy Tab 브라우저 검증은 현재 stable Chrome을 기준으로 재확인한다. 공식 release note: https://developer.chrome.com/release-notes/151
- 향후 native Android wrapper를 도입하더라도 large-screen UX를 고정 orientation에 의존하지 않는다. Android 17은 큰 화면에서 orientation/resizability 제한을 더 강하게 무시하는 방향이다. 공식 안내: https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored

## 14. Change rule

이 문서는 다음 중 하나가 실제로 바뀔 때만 수정한다.

- 제품 목표 또는 핵심 사용자
- 학습↔게임 관계
- mastery/adaptive learning의 핵심 제품 계약
- reward/guardian 제품 경계
- active/frozen feature status
- 현재 큰 개발 sequence

개별 작업 완료, 커밋 SHA, 테스트 PASS 횟수, 다음 atomic task를 기록하기 위해 수정하지 않는다.
