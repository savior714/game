# AidenGame: Octonauts Ocean Rescue — MVP 통합 PRD

- **Version:** v1.0 — Gameplay direction + AI Studio handoff foundation
- **Date:** 2026-08-25
- **Status:** Gameplay direction 확정 / AI Studio non-canonical implementation lane 정의 / Foundation tooling v1 구현 완료
- **Deployment:** 자녀 1인용 비공개·비상업 개인 게임
- **Primary device:** Galaxy Tab S10급 가로 화면 태블릿
- **Build constraint:** 개발 소스는 모듈화할 수 있으나 최종 배포물은 단일 HTML
- **Hosting:** 고정된 비공개 HTTPS URL

---

## 1. Product statement

6–7세 어린이가 옥토넛 신입 대원 **Aiden**이 되어 좋아하는 GUP을 선택하고, 2.5D 횡스크롤 바닷속 에피소드에서 **손가락으로 GUP을 직접 조종**하며 **맥락적 액션(Boost / Scan / Rescue)** 하나로 구조 도구를 직접 조작해 해양 생물을 안전하게 구조하는 개인용 게임.

## 2. Product goals

1. 어린이가 별도 설명 없이도 짧은 시각 안내를 보고 구조 조작을 이해한다.
2. 실패가 미션 중단이나 평가로 이어지지 않고, 현재 단계의 재시도와 점진적 도움으로 이어진다.
3. **이동 구간은 구조로 가는 여정이며, 좋은 travel play가 Rescue Readiness를 올린다.**
4. 구조된 생물이 안전을 되찾고 서식처나 가족에게 돌아가는 결과까지 보여준다.
5. 한 미션을 4–6분 안에 완료하고 즉시 재플레이하거나 다음 미션을 선택할 수 있다.

## 3. AI Studio development contract (non-canonical implementation lane)

사용자는 Google AI Studio의 무료 Build 사용량을 최대한 실제 개발에 쓰고 싶다.

### 선택된 방식

- **GitHub import/sync를 canonical workflow로 사용하지 않는다.**
- **Repository를 AI Studio에 직접 맡기지 않는다.**
- **작업 단위는 파일 하나가 아니라 30~90초 playable vertical slice다.**
- **Local에서 deterministic flatpack 하나를 만든다.**
- **사용자가 그 text를 AI Studio에 전달한다.** 전송 방식은 paste/file attachment 등 현재 UI가 허용하는 수단일 뿐이며, tooling은 undocumented AI Studio upload API에 의존하지 않는다.
- **AI Studio에서 Gemini가 설계/구현/preview/iteration을 적극적으로 수행한다.**
- **결과는 AI Studio의 ZIP export로 회수한다.**
- **ZIP은 untrusted candidate이며 canonical truth가 아니다.**
- **Local ingest가 exact-base와 boundary를 검증한 후에만 isolated BUILD worktree에 적용한다.**

### AI Studio의 역할과 경계

- **AI Studio는 vertical slice 안에서는 주 설계/구현 주체다.**
- **Local에서 gameplay API를 미리 과도하게 설계해 Gemini의 역할을 축소하지 않는다.**

### 허용되는 Protected surface 변경 제안

Gemini가 다음과 같은 protected surface 변경이 필요하다고 판단하는 것은 허용:

- Pointer normalization authority
- Global application phase-transition authority
- Progression persistence/schema authority
- Package/dependency/toolchain
- Vite/build/standalone packaging
- Ocean Rescue 바깥 AidenGame

하지만 이를 candidate에 조용히 변경하면 안 된다. 그 경우 **BOUNDARY_CHANGE_PROPOSAL로 이유/제안만 반환**하게 한다.

## 3. Gameplay balance and identity

### 3.1 Gameplay balance

Ocean Rescue의 게임플레이 비중:
- **Action 45%** — 손가락으로 GUP 직접 조종, 맥락적 액션(Boost/Scan/Rescue) 수행
- **Main Rescue 40%** — 구조 도구 직접 조작(밧줄 자르기, 바위 옮기기, 잔해 견인)
- **World Growth 15%** — 최초 구조 시 지역 회복, 구조한 동물 이후 월드에 등장, 다음 해역 해금

### 3.2 Mission identity — 같은 조작 언어, 다른 구조 능력

세 미션은 서로 다른 게임이 아니다. **같은 조작 언어 안에서 서로 다른 구조 능력**을 사용한다.

| Mission | Identity | Core ability |
|---------|----------|--------------|
| Sea Turtle | **Precision** | 찾아가서 밧줄을 정확하게 잘라 풀어주기 |
| Crab | **Handling** | Grabber로 잡아서 옮기기 |
| Young Whale | **Towing / Momentum** | 연결하고 직접 끌어서 길 만들기 |

### 3.3 Core experience principles

- **GUP을 아이가 손가락으로 직접 조종한다** — 단순 자동전진 관람 + 상하 보조조작을 중심 gameplay로 유지하지 않는다.
- **한 시점의 contextual action은 최대 하나다** — 예: BOOST / SCAN / RESCUE.
- **Contextual button 자체가 QTE나 주 gameplay가 되어서는 안 된다.**
- **구조물은 아이가 직접 조작한다.**

## 4. Mission episode pacing (대략 4–6분)

```
Launch → Action 1 → Discovery → Action 2 → Main Rescue → 짧은 동행/안전지역 이동 → World Reaction
```

## 5. Rescue Readiness

- 이번 mission session에만 존재하는 **내부 연속 상태**다.
- 아이에게 숫자, 점수, %, 별, 등급으로 **보여주지 않는다**.
- 화면에서는 **실제 구조 장비가 준비되는 것**으로 표현한다.
- **좋은 travel play가 readiness를 올린다.**
- **이미 준비 완료된 장비 milestone은 이후 실수로 다시 꺼지지 않는다.**
- **Collision은 아직 확정되지 않은 다음 준비 진행만 조금 늦출 수 있다.**
- **Readiness bonus와 실패 반복 시 adaptive assistance는 서로 다른 개념이다.**
- **Readiness가 낮아도 구조 성공이나 world progression을 막지 않는다.**

## 6. Mistake philosophy

- **Game over 없음**
- **Lives 없음**
- **별점/랭크/실패 횟수 없음**
- **전체 mission restart 강제 없음**
- **실수는 잠깐 늦추지만 이미 이룬 성취를 빼앗지 않는다.**
- **항상 현재 위치에서 회복 가능해야 한다.**
- **Travel collision은 짧은 밀림/흔들림/감속 후 다시 플레이로 복귀한다.**
- **Rescue interaction에서 반복적으로 어려워하면 tolerance/target/help를 점진적으로 넓힐 수 있다.**
- **이미 완료한 구조 단계는 실패 때문에 되돌리지 않는다.**

## 7. World progression

- **Canonical progression은 최초 mission completion이 움직인다.**
- **최초 구조 → 해당 지역 회복 → 구조한 동물이 이후 world에 존재 → 다음 구조 signal/해역 unlock.**
- **같은 mission 반복 횟수 grind로 다음 progression을 열지 않는다.**
- **Replay는 전에 구조한 동물 재등장, 더 건강한 환경, ambient life 등으로 살아있는 world를 보여준다.**
- **Replay 횟수 XP나 hidden grind를 만들지 않는다.**
- **Readiness 수준에 따라 canonical world recovery 양을 차등하지 않는다.**

## 8. Superseded legacy contracts

기존 PRD 중 아래 의미는 새 계약으로 **supersede**된다:

- ~~travel이 사실상 자동전진 보조 구간이라는 계약~~
- ~~이동 성과가 이후 gameplay에 아무 영향이 없다는 계약~~
- ~~세 mission 환경 차이가 시각/음향뿐이라는 계약~~

## 9. Maintained important existing intents

유지할 중요한 기존 의도:
- 6–7세 어린이
- Galaxy Tab S10급 landscape-first
- 4–6분 mission
- 구조 실패로 아이를 평가하거나 mission을 막지 않음
- 직접 구조
- GUP 간 stat/power 차이를 gameplay progression의 중심으로 만들지 않음
- 점수/별/등급/leaderboard 없음

## 3. Non-goals

MVP에는 다음 요소를 넣지 않는다.

- 점수
- 별 개수
- 등급
- 제한 시간
- 체력 또는 손상 수치
- 실패 횟수 표시
- 순위표
- 경쟁 요소
- 수집품
- 배지
- 도감
- 방 꾸미기
- 반복 플레이 랜덤 변형
- **Game over / Lives / 전체 mission restart 강제**
- **Readiness를 숫자/점수/%/별/등급으로 노출**
- **같은 mission 반복 횟수 grind로 progression 해금**
- **Readiness 수준에 따른 canonical world recovery 차등**
- **Travel을 단순 자동전진 관람 + 상하 보조조작으로만 구성**
- **Contextual button을 QTE나 주 gameplay로 만듦**

---

## 10. Target experience

### 10.1 Target user

- 연령: 6–7세
- 플레이어 이름: **Aiden**으로 고정
- 최초 한 번 선택하는 동물 캐릭터:
  - Arctic fox
  - Beaver
  - Red panda

### 10.2 Session structure

- 미션 길이: 4–6분
- 플레이와 컷신 목표 비율: 약 70:30
- 미션 기반 고정 진행
- 고정 측면 카메라
- 2.5D 시각 스타일
- 가로 화면 전용

### 10.3 Core loop

`미션 선택 → GUP 선택 → 출동 → Action 1 (직접 조종) → Discovery → Action 2 → Main Rescue (구조 도구 직접 조작) → 생물의 안전 확인 → 생태 메시지 → 동료·생물 후일담 → World Reaction → 다음 미션 해금 또는 재플레이`

---

## 11. Progression and replay

### 11.1 Mission order

미션은 고정 순서로 해금한다.

1. Sea turtle rescue
2. Crab rescue
3. Young whale rescue

### 11.2 First completion

최초 완료 시:

1. 구조 완료 애니메이션
2. 생태 메시지
3. 동료 후일담 한 문장
4. 구조된 생물의 이후 상태 한 문장
5. 다음 미션이 존재하면 `Next Mission Unlocked!`
6. `Continue` / `Replay`

### 11.3 Continue

`Continue`를 누르면:

- 옥토포드 미션 선택 화면으로 돌아간다.
- 새로 해금된 미션 카드까지 자동 이동한다.
- 새 미션 카드는 부드럽게 발광한다.
- `New!` 표시를 보여준다.
- 자동으로 다음 미션을 시작하지 않는다.
- 아이가 직접 미션 카드를 선택한다.
- `New!` 표시는 해당 미션을 처음 열어본 뒤 제거한다.

### 11.4 Replay

- 완료된 미션은 언제든 다시 플레이할 수 있다.
- 완료 카드의 `Replay`는 현재 GUP을 유지한 채 같은 미션을 다시 시작한다.
- 미션 선택 화면에서 다시 들어갈 때는 GUP을 새로 선택할 수 있다.
- 재플레이에서는 이미 획득한 해금 카드를 다시 표시하지 않는다.
- 장애물 위치와 구조 순서는 동일하게 유지한다.

### 11.5 World progression (canonical)

- **최초 mission completion이 canonical progression을 움직인다.**
- **최초 구조 → 해당 지역 회복 → 구조한 동물이 이후 world에 존재 → 다음 구조 signal/해역 unlock.**
- **같은 mission 반복 횟수 grind로 다음 progression을 열지 않는다.**
- **Replay는 전에 구조한 동물 재등장, 더 건강한 환경, ambient life 등으로 살아있는 world를 보여준다.**
- **Replay 횟수 XP나 hidden grind를 만들지 않는다.**
- **Readiness 수준에 따라 canonical world recovery 양을 차등하지 않는다.**

---

## 12. GUP selection and launch

### 12.1 Available GUPs

- GUP-C
- GUP-I
- GUP-X

### 12.2 GUP gameplay contract

- 모든 GUP은 모든 미션을 동일하게 완료할 수 있다.
- 속도, 충돌 판정, 구조 성능, 조작 난이도 차이는 없다.
- 차이는 외형과 소리뿐이다.
- **GUP 간 stat/power 차이를 gameplay progression의 중심으로 만들지 않는다.**

### 12.3 Selection flow

미션 카드를 누르면 항상 GUP 선택 화면을 보여준다.

- 마지막 사용 GUP을 기본 선택한다.
- 선택된 GUP은 확대, 윤곽선, 이름으로 표시한다.
- 다른 GUP을 누르면 미리보기와 엔진음을 변경한다.
- `Launch`를 눌러 출동한다.
- 선택 결과를 `Last GUP`으로 저장한다.

### 12.4 Re-entrancy protection

`Launch`, `Continue`, `Replay`, `Restart`, `Exit` 등 상태를 변경하는 버튼은:

- 첫 번째 유효 입력만 처리한다.
- 화면 전환 또는 상태 변경이 완료될 때까지 관련 버튼을 잠근다.
- 고정 시간 쿨다운이 아니라 실제 상태 전환 완료를 잠금 해제 기준으로 사용한다.
- 중복 미션 시작, 중복 저장, 연속 화면 전환을 허용하지 않는다.

### 12.5 Launch sequence

`Launch` 이후:

1. 옥토포드 출동구가 열린다.
2. 선택한 GUP이 바다로 출발한다.
3. 동료가 구조 대상, 문제, 첫 행동을 한 문장으로 안내한다.
4. 총 5–7초 뒤 **Action 1 (직접 조종) 플레이를 시작한다.**
5. 화면 탭으로 출동 연출을 건너뛸 수 있다.

미션별 브리핑:

- **Mission 1 / Peso:** `A sea turtle is trapped in a net. Let's find it and cut the ropes!`
- **Mission 2 / Tweak:** `A crab is trapped under some rocks. Let's move them with the grabber!`
- **Mission 3 / Captain Barnacles:** `A young whale's path is blocked. Let's tow the debris away!`

### 12.6 Goal banner

플레이 시작 직후 화면 상단에 약 3초간 표시한다.

- Mission 1: `Rescue the sea turtle!`
- Mission 2: `Help the trapped crab!`
- Mission 3: `Clear a path for the young whale!`

출동 연출을 건너뛴 경우에도 목표 배너는 항상 표시한다.

---

## 13. Action segments (Travel + Action beats)

### 13.1 Structure

각 미션은 두 개의 **Action beat**로 구성된다:

- **Action 1** (Launch 직후): 손가락으로 GUP 직접 조종, 장애물 회피, Boost/Scan 사용
- **Discovery**: 구조 대상 발견, 카메라 전환, 상황 안내
- **Action 2**: 두 번째 직접 조종 구간, Main Rescue 진입 전 준비
- **Main Rescue**: 구조 도구 직접 조작 (핵심 40% 경험)

### 13.2 Action beat 공통 계약

- **GUP을 아이가 손가락으로 직접 조종한다** — 단순 자동전진 관람 + 상하 보조조작이 아니다.
- **한 시점의 contextual action은 최대 하나** — BOOST / SCAN / RESCUE 중 하나.
- **Contextual button 자체가 QTE나 주 gameplay가 되어서는 안 된다.**
- **좋은 travel play가 Rescue Readiness를 올린다.**
- **Collision은 아직 확정되지 않은 다음 준비 진행만 조금 늦출 수 있다.**
- **이미 준비 완료된 장비 milestone은 이후 실수로 다시 꺼지지 않는다.**

### 13.3 Mission environments

#### Mission 1 — Coral reef

- 밝은 산호초
- 해초
- 작은 열대어

#### Mission 2 — Sandy reef

- 모래 바닥
- 낮은 암초
- 조개
- 작은 게의 흔적

#### Mission 3 — Rocky canyon

- 깊고 푸른 수역
- 큰 암벽
- 좁아 보이는 통로

**환경 차이는 시각·음향뿐만 아니라 장애물 배치와 Action beat 리듬에도 영향을 준다.**

### 13.4 Player control

- **Relative vertical drag**: 화면 안에서 위·아래로 드래그하면 이동량에 비례해 GUP 높이가 변함. 손가락을 놓으면 현재 높이를 유지. 자동 중앙 복귀 없음. 관성 이동 없음.
- **Contextual action (단일 버튼)**: 화면 우측에 맥락적 액션 버튼 하나만 표시. Boost(가속), Scan(구조 대상 탐지), Rescue(구조 도구 전환) 중 현재 상황에 맞는 하나만 활성화.
- **Tap assist**: 화면의 원하는 높이를 탭하면 GUP이 해당 높이로 부드럽게 이동. 수평 이동은 계속 유지. 탭 목표가 유효 범위를 벗어나면 범위 안으로 보정. 이동 중 드래그가 시작되면 탭 이동을 즉시 취소하고 수동 조작으로 전환.

### 13.5 Collision response

고정 지형과 충돌하면:

- GUP이 살짝 뒤로 밀린다.
- 짧게 흔들린다.
- 작은 충돌 효과음을 재생한다.
- 동료가 짧은 놀람 표정을 짓는다.
- 약 1초간 감속한다.
- 수직 조작권은 유지한다.
- 감속 후 정상 속도로 자동 회복한다.
- 동일 장애물과의 즉시 연속 충돌을 막기 위해 약 0.7초간 재충돌 판정을 비활성화한다.

**충돌로 발생하지 않는 것:**
- 체력 감소
- GUP 손상
- 미션 실패
- 이동 구간 재시작
- 구조 현장 진입 차단
- **이미 확정된 Readiness milestone 감소**

**충돌의 효과:**
- **아직 확정되지 않은 다음 Readiness 진행만 조금 늦출 수 있다.**

### 13.6 Companion speech during Action

- 출동 직후 브리핑 이후에는 추가 주행 대사를 넣지 않는다.
- 충돌 시 짧은 비언어 놀람 소리만 허용.
- 장애물 회피를 칭찬하거나 평가하지 않는다.
- 바닷속 환경음과 GUP 엔진음을 중심으로 구성한다.

- 출동 직후 브리핑 이후에는 추가 주행 대사를 넣지 않는다.
- 충돌 시 짧은 비언어 놀람 소리만 허용한다.
- 장애물 회피를 칭찬하거나 평가하지 않는다.
- 바닷속 환경음과 GUP 엔진음을 중심으로 구성한다.

---

## 14. Rescue Readiness

- 이번 mission session에만 존재하는 **내부 연속 상태**다.
- 아이에게 숫자, 점수, %, 별, 등급으로 **보여주지 않는다**.
- 화면에서는 **실제 구조 장비가 준비되는 것**으로 표현한다 (예: 커터 칼날이 빛남, 그래버 암이 예열됨, 견인 윈치가 돌아감).
- **좋은 travel play (충돌 회피, 부드러운 조종, Scan 활용)가 readiness를 올린다.**
- **이미 준비 완료된 장비 milestone은 이후 실수로 다시 꺼지지 않는다.**
- **Collision은 아직 확정되지 않은 다음 준비 진행만 조금 늦출 수 있다.**
- **Readiness bonus (좋은 travel play로 인한 가속)와 실패 반복 시 adaptive assistance (판정 범위 확대)는 서로 다른 개념이다.**
- **Readiness가 낮아도 구조 성공이나 world progression을 막지 않는다.** — 단지 구조 도구가 덜 준비된 상태에서 시작할 뿐이다.

---

## 15. Mistake philosophy

- **Game over 없음**
- **Lives 없음**
- **별점/랭크/실패 횟수 없음**
- **전체 mission restart 강제 없음**
- **실수는 잠깐 늦추지만 이미 이룬 성취를 빼앗지 않는다.**
- **항상 현재 위치에서 회복 가능해야 한다.**
- **Travel collision은 짧은 밀림/흔들림/감속 후 다시 플레이로 복귀한다.**
- **Rescue interaction에서 반복적으로 어려워하면 현재 구현처럼 tolerance/target/help를 점진적으로 넓힐 수 있다.**
- **이미 완료한 구조 단계는 실패 때문에 되돌리지 않는다.**
- **Adaptive assistance는 아이의 성공을 돕는 것이고, Readiness는 travel play의 품질을 반영하는 것이다. 둘을 혼동하지 않는다.**

---

## 16. World progression (canonical)

- **Canonical progression은 최초 mission completion이 움직인다.**
- **최초 구조 → 해당 지역 회복 → 구조한 동물이 이후 world에 존재 → 다음 구조 signal/해역 unlock.**
- **같은 mission 반복 횟수 grind로 다음 progression을 열지 않는다.**
- **Replay는 전에 구조한 동물 재등장, 더 건강한 환경, ambient life 등으로 살아있는 world를 보여준다.**
- **Replay 횟수 XP나 hidden grind를 만들지 않는다.**
- **Readiness 수준에 따라 canonical world recovery 양을 차등하지 않는다.**

---

## 17. Rescue site transition

구조 대상이 화면에 들어오면:

1. GUP이 자동 감속한다.
2. 지정 위치에서 완전히 정지한다.
3. 주행용 드래그와 탭 입력을 비활성화한다.
4. 카메라를 구조 대상과 도구가 함께 보이는 구도로 이동한다.
5. 동료가 현재 구조 상황을 한 문장으로 안내한다.
6. `Ready!`를 짧게 표시한다.
7. 구조 입력을 활성화한다.

전환 중 발생한 탭은 소비하고 구조 입력으로 전달하지 않는다.

---

## 9. Common rescue tutorial

구조 조작을 활성화하기 전에:

- 동료가 조작법을 한 문장으로 말한다.
- 같은 영어 자막을 화면 하단에 표시한다.
- 반투명 손가락이 첫 동작을 한 번 시연한다.
- 시연 종료 후 실제 구조 입력을 활성화한다.
- 재플레이에서도 기본적으로 표시한다.
- 화면 탭으로 즉시 건너뛸 수 있다.
- 시연 중 실제 게임 입력은 소비한다.
- TTS 실패 시에도 자막과 손가락 시연은 정상 작동한다.

미션별 문구:

- Mission 1: `Start here. Follow the rope to the end!`
- Mission 2: `Hold the rock. Move it. Release it in the zone!`
- Mission 3 connection: `Drag from the debris to the GUP hook!`
- Mission 3 towing: `Drag the GUP to the safe spot!`

---

## 10. Common rescue feedback

### 10.1 Successful input

성공 직후:

- 성공한 밧줄, 바위 또는 잔해가 약 0.3–0.5초간 부드럽게 빛난다.
- 짧고 자극적이지 않은 성공 효과음을 재생한다.
- 동료가 고개 끄덕임 또는 손짓으로 짧게 반응한다.
- 생물의 단계별 반응과 남은 단계 대사로 전환한다.
- 다음 구조 입력은 성공 피드백이 끝난 뒤 활성화한다.
- 화면 중앙을 가리는 `Great!` 팝업은 사용하지 않는다.

### 10.2 Incorrect input

잘못된 입력 직후:

- 현재 대상이 짧게 흔들린다.
- 낮고 짧은 재시도 효과음을 재생한다.
- 현재 단계의 대상만 시작 상태로 복귀한다.
- 동료가 꾸짖거나 부정적으로 평가하지 않는다.
- 이전에 성공한 단계는 유지한다.
- 점수 차감, 실패 횟수, 경고 팝업을 표시하지 않는다.

### 10.3 Progressive assistance

같은 구조 단계에서 반복 실패하면:

1. **첫 실패:** 반투명 손가락으로 올바른 동작을 다시 시연
2. **두 번째 실패:** 시작점과 목적지를 더 크고 밝게 강조
3. **세 번째 이상:** 허용 판정 범위를 넓히고 점선 이동 경로를 계속 표시

추가 규칙:

- 자동 완료는 제공하지 않는다.
- 아이가 직접 입력해 성공해야 한다.
- 도움 단계와 실패 횟수를 숫자로 표시하지 않는다.
- 현재 단계를 성공하면 실패 횟수와 강화 도움을 즉시 초기화한다.
- 다음 단계는 기본 판정 범위에서 시작한다.
- 미션 재시작 시 모든 임시 도움 상태를 초기화한다.

---

## 11. Mission 1 — Sea turtle rescue

### 11.1 Scenario

- 구조 대상: Sea turtle
- 문제: 버려진 그물의 밧줄 세 개에 얽힘
- 동료: Peso
- 도구: Cutter
- 환경: 밝은 산호초와 해초 지대

### 11.2 Structure

- 밧줄 3개
- 가장 가까운 밧줄부터 바깥쪽 밧줄까지 고정 순서
- 한 번에 밧줄 하나만 활성화
- 활성 밧줄의 시작점은 발광 표시
- 끝점은 별도 표시
- 시작점에서 끝점 방향으로 추적
- 넓은 허용 경로 사용

### 11.3 Alternative input

드래그 추적이 어려운 경우:

1. 시작점을 탭
2. 끝점을 탭

두 탭이 올바른 순서로 입력되면 같은 구조 성공으로 처리한다.

### 11.4 Failure boundary

- 현재 밧줄만 재시도한다.
- 이전에 자른 밧줄은 복원하지 않는다.
- 첫 실패 후 애니메이션 가이드를 표시한다.

### 11.5 Turtle reaction

- 각 밧줄이 성공적으로 잘릴 때마다 거북이가 점차 긴장을 푼다.
- 세 번째 밧줄이 잘리면 완전히 자유로워진다.

### 11.6 Dialogue

1. `Good start, Aiden! Two ropes left.`
2. `Well done! One rope left.`
3. `Great work, Aiden! The turtle is free!`

### 11.7 Completion items not yet specified

다음 항목의 정확한 내용은 아직 결정하지 않았다.

- 마지막 구조 완료 애니메이션의 세부 동작
- Mission 1 생태 메시지 문구
- Peso 후일담 문구
- 거북이의 이후 상태 문구

---

## 12. Mission 2 — Crab rescue

### 12.1 Scenario

- 구조 대상: Crab
- 문제: 작은 바위 세 개 아래에 갇힘
- 동료: Tweak
- 도구: Grabber arm
- 환경: 모래 바닥과 낮은 암초 지대

### 12.2 Structure

- 작은 바위 3개
- 고정 순서
- 현재 활성 바위 하나만 조작 가능
- 활성 바위를 약 0.4초간 길게 눌러 잡는다.
- 잡은 뒤 Grabber arm이 손가락을 직접 따라간다.
- 운반 중 추가 장애물은 없다.
- 화면 오른쪽 중간부터 아래쪽에 큰 보관 구역 하나를 둔다.

### 12.3 Success criterion

손을 놓는 순간 **바위 중심점이 보관 구역 안에 있으면 성공**한다.

- 바위 전체가 들어갈 필요는 없다.
- 바위 중심이 구역 밖이면 실패한다.
- 실패 시 현재 바위만 원래 위치로 돌아간다.

### 12.4 Alternative input

1. 활성 바위를 탭
2. 보관 구역을 탭

올바른 순서로 입력되면 같은 이동 성공으로 처리한다.

### 12.5 First failure hint

`Hold → Move → Release`

### 12.6 Crab reactions

1. 첫 번째 바위 제거: 게가 눈을 뜨고 주변을 살핀다.
2. 두 번째 바위 제거: 집게발을 움직이며 몸을 일으킨다.
3. 세 번째 바위 제거: 완전히 빠져나와 Aiden에게 집게발을 흔든다.

### 12.7 Tweak dialogue

1. `Great lift! Two rocks left, and the crab can see us.`
2. `One more rock! The crab is getting up.`
3. `All clear! The crab is free!`

### 12.8 Completion animation

- 마지막 바위가 치워진다.
- 게가 천천히 몸을 빼낸다.
- Aiden에게 집게발을 흔든다.
- 화면 옆의 작은 모래 굴로 걸어간다.
- 굴 입구에서 한 번 돌아본다.
- 굴 안으로 들어간다.

### 12.9 Ecology message

`Crabs need safe spaces under rocks and sand. Let’s keep their homes clean!`

### 12.10 Epilogue items not yet specified

- Tweak의 완료 후일담 정확한 문구
- 구조된 게의 이후 상태 문구

---

## 13. Mission 3 — Young whale rescue

### 13.1 Scenario

- 구조 대상: Young whale
- 문제: 잔해가 통로를 막고 있음
- 동료: Captain Barnacles
- 도구: Tow line
- 환경: 깊고 푸른 바위 협곡

### 13.2 Safety principle

- 견인줄은 잔해에만 연결한다.
- 어린 고래에는 절대로 연결하지 않는다.
- 구조팀은 통로만 확보한다.
- 고래가 스스로 빠져나가게 한다.

### 13.3 Debris order

고정 순서로 잔해 3개를 제거한다.

1. 입구를 막는 작은 잔해
2. 가운데 걸린 중간 잔해
3. 출구 가까이에 있는 큰 잔해

현재 잔해를 완료해야 다음 잔해의 연결점이 활성화된다.

### 13.4 Tow-line connection

1. 잔해의 빛나는 연결점을 누른다.
2. 손가락을 GUP 뒤쪽 견인 고리까지 드래그한다.
3. 고리 안에서 놓으면 연결한다.
4. 첫 실패 후 연결 경로 애니메이션을 표시한다.

### 13.5 Towing

연결 후:

- 잔해 반대편에 빛나는 안전 지점을 표시한다.
- GUP을 안전 지점까지 드래그한다.
- 잔해가 견인줄을 따라 이동한다.
- GUP이 안전 지점에 도달하면 현재 잔해 제거를 완료한다.

### 13.6 Towing failure

다음 경우 현재 견인 실패로 판정한다.

- 잘못된 방향으로 일정 거리 이상 이동
- 안전 지점에 도달하기 전에 손을 놓음

실패 시:

- GUP과 현재 잔해만 견인 시작 위치로 천천히 돌아간다.
- 견인줄 연결은 유지한다.
- 즉시 같은 견인 동작을 다시 시도할 수 있다.
- 첫 실패 후 반투명 GUP이 안전 지점까지 이동하는 경로를 보여준다.
- 이전에 치운 잔해는 복원하지 않는다.

### 13.7 Whale reactions

1. 첫 번째 잔해 제거: 고래가 눈을 크게 뜨고 구조팀을 바라본다.
2. 두 번째 잔해 제거: 몸을 움직이며 열린 통로 쪽으로 조금 다가간다.
3. 세 번째 잔해 제거: 길이 열린 것을 확인하고 스스로 헤엄쳐 나간다.

### 13.8 Captain Barnacles dialogue

1. `Good work, Aiden! Two pieces left. The whale knows we’re here.`
2. `Just one more! The whale is moving toward the opening.`
3. `The path is clear! Let’s give the whale room to swim.`

### 13.9 Completion animation

- 어린 고래가 열린 통로를 빠져나온다.
- 안전한 거리를 유지하며 GUP 주변을 천천히 한 바퀴 돈다.
- 짧은 고래 소리를 내며 지느러미를 흔든다.
- 멀리 기다리던 어미 고래에게 헤엄쳐 간다.
- 두 고래가 함께 화면 밖으로 이동한다.

### 13.10 Ecology message

`Whales need space to swim safely. Clear the way and watch from a distance!`

### 13.11 Epilogue items not yet specified

- Captain Barnacles의 완료 후일담 정확한 문구
- 어린 고래와 어미 고래의 이후 상태 문구

---

## 14. Completion narration

### 14.1 Format

각 미션의 후일담은 두 문장으로 구성한다.

1. 동료가 Aiden의 구조 행동을 칭찬하는 한 문장
2. 구조된 생물이 이후 안전하게 지내는 모습을 설명하는 한 문장

Aiden의 별도 대사는 넣지 않는다.

### 14.2 Playback

- 한 문장씩 순서대로 재생한다.
- 각 문장에 영어 자막을 표시한다.
- 첫 문장 음성이 끝나면 두 번째 문장으로 자동 전환한다.
- 첫 문장 중 탭하면 두 번째 문장으로 즉시 이동한다.
- 두 번째 문장 중 탭하면 완료 카드로 즉시 이동한다.
- 빠른 연속 탭으로 완료 화면을 중복 전환하지 않는다.
- 전체 목표 길이는 약 6–8초다.
- TTS 실패 시에도 자막과 화면 전환은 정상 진행한다.

---

## 15. Audio and captions

### 15.1 Voice

- 브라우저 TTS 사용
- 우선 언어·음성: en-GB
- 영어 자막 항상 표시
- TTS 실패는 미션 진행을 차단하지 않음

### 15.2 Pause during speech

대사, 브리핑 또는 후일담 음성 도중 Pause하면:

- 현재 문장을 중간부터 이어 재생하지 않는다.
- 재개 후 현재 문장의 자막과 TTS를 처음부터 다시 시작한다.
- 이미 완료된 이전 문장이나 장면은 반복하지 않는다.
- 브라우저의 TTS pause/resume 정확성에 의존하지 않고 문장 단위로 취소 후 재생한다.

### 15.3 Volume controls

Pause 메뉴에:

- `Sound` 0–100, 기본값 70
- `Voice` 0–100, 기본값 85

동작:

- `Sound`를 움직이면 짧은 효과음을 변경된 음량으로 재생한다.
- `Voice`를 움직이면 동료의 `Sound check!`를 변경된 음량으로 재생한다.
- 연속 조절 시 이전 미리듣기를 중단하고 최신 값만 재생한다.
- 손을 놓는 순간 값을 저장한다.
- 0 음량을 허용한다.
- TTS를 사용할 수 없으면 Voice 값은 저장하되 음성 미리듣기는 생략한다.

---

## 16. Pause system

### 16.1 Pause entry

- 화면 오른쪽 위에 큰 원형 Pause 버튼을 고정한다.
- 주행, 구조, 출동 연출, 완료 연출, 후일담에서 사용 가능하다.
- 충분한 화면 가장자리 안전 여백을 둔다.

Pause 시:

- 게임 로직 정지
- 애니메이션 정지
- 타이머 정지
- 효과음 정지
- TTS 중단
- 현재 화면을 그대로 유지
- 반투명 어두운 오버레이 위에 메뉴 표시

### 16.2 Active input cancellation

드래그 또는 홀드 중 Pause하면:

- 진행 중 입력을 안전하게 취소한다.
- 실패 횟수에 포함하지 않는다.
- 현재 미완료 단계만 시작 상태로 복귀한다.
- 이미 완료한 단계는 유지한다.

### 16.3 Pause menu

- Resume
- Restart Mission
- Exit to Octopod
- Sound slider
- Voice slider
- Enter Fullscreen — 현재 전체화면이 아닐 때

### 16.4 Resume

`Resume` 선택 후:

1. 메뉴와 어두운 오버레이 제거
2. `3 → 2 → 1 → Go!` 표시
3. 카운트다운 중 게임, 입력, 애니메이션, TTS는 계속 정지
4. `Go!`가 사라질 때 재개

카운트다운은 탭으로 건너뛸 수 없다.

### 16.5 Restart Mission

확인 창:

- `Restart this mission?`
- `Restart` / `Cancel`

`Restart` 선택 시:

- 현재 미션 임시 진행 초기화
- 출동 연출부터 다시 시작
- 현재 선택 GUP 유지
- 구조 단계 실패 횟수와 강화 도움 초기화
- 완료 미션, 해금, 프로필, 음량 설정 유지

`Cancel`은 Pause 메뉴로 돌아간다.

### 16.6 Exit to Octopod

확인 창:

- `Exit to the Octopod?`
- `Exit` / `Cancel`

`Exit` 선택 시:

- 옥토포드 미션 선택 화면으로 이동
- 현재 미션의 미완료 진행 폐기
- 중간 체크포인트 저장 없음
- 완료 미션, 해금, 동물 선택, 음량, 마지막 GUP 유지

`Cancel`은 Pause 메뉴로 돌아간다.

---

## 17. Automatic pause boundaries

### 17.1 App or tab hidden

`visibilitychange`에서 화면이 숨겨지면:

- 즉시 자동 Pause
- 진행 중 입력을 취소하되 실패로 기록하지 않음
- 복귀해도 자동 재개하지 않음
- Pause 메뉴 표시
- 사용자가 `Resume`을 선택한 뒤 카운트다운으로 재개
- 중단된 음성 문장은 처음부터 다시 재생

중복 자동 Pause 이벤트는 한 번만 처리한다.

### 17.2 Portrait orientation

세로 방향으로 전환되면:

- 즉시 자동 Pause
- `Turn your device sideways to play!` 표시
- 회전 아이콘 표시
- 세로 방향에서는 `Resume` 비활성화
- 가로 방향으로 돌아오면 회전 안내만 제거
- 자동 재개하지 않음
- `Resume`과 카운트다운을 거쳐 재개

### 17.3 Insufficient viewport

실제 CSS 게임 영역이 최소 유효 크기보다 작으면:

- 즉시 자동 Pause
- `Make the game window bigger to continue.` 표시
- 유효 크기가 회복되어도 자동 재개하지 않음
- 유효 크기에서만 `Resume` 활성화
- 미션 진행과 완료 단계는 유지

정확한 최소 픽셀 기준은 Galaxy Tab S10 실기 검증 후 확정한다.

---

## 18. Fullscreen behavior

### 18.1 Start request

`Start`를 누르면 전체화면을 한 번 요청한다.

- 성공 여부와 관계없이 게임을 시작한다.
- 실패 또는 미지원 시 `For the best view, use fullscreen.`를 짧게 표시한다.
- 전체화면 실패를 오류나 진행 차단으로 취급하지 않는다.
- Pause 메뉴에서 `Enter Fullscreen`을 다시 선택할 수 있다.

### 18.2 Fullscreen exit

플레이 도중 전체화면이 해제되면:

- 게임을 자동 Pause하지 않는다.
- `Fullscreen ended.`를 약 2초 표시한다.
- 가로 방향과 유효 화면 크기가 유지되면 계속 플레이한다.
- 자동 재요청하지 않는다.
- 재진입은 Pause 메뉴의 사용자 입력으로만 수행한다.

전체화면 해제와 동시에 세로 방향 또는 최소 화면 크기 위반이 발생하면 해당 자동 Pause 규칙을 적용한다.

---

## 19. Canvas and viewport contract

### 19.1 Fixed aspect ratio

- 게임 콘텐츠는 고정 16:9 좌표계를 사용한다.
- 화면 비율이 다르면 위·아래 또는 좌·우에 여백을 둔다.
- 장면을 잘라내거나 비율에 맞춰 늘이지 않는다.
- 여백은 장면과 어울리는 어두운 바닷빛으로 채운다.
- Pause 버튼을 포함한 UI는 16:9 안전 영역 안에 둔다.

### 19.2 Coordinate conversion

- 실제 화면 입력 좌표를 16:9 게임 좌표로 변환한다.
- 구조 대상과 판정 위치는 기기 비율과 무관하게 동일하다.

### 19.3 Letterbox input

- 여백에서 시작한 탭과 드래그는 모두 무시한다.
- 시각·음향 피드백도 표시하지 않는다.
- 캔버스 안에서 시작한 유효 드래그가 여백으로 이동한 경우에는 계속 추적한다.
- 손가락을 놓거나 취소할 때 입력을 종료한다.

---

## 20. Touch and pointer contract

### 20.1 Single gameplay pointer

- 첫 번째 유효 포인터 하나만 게임 입력 소유권을 가진다.
- 두 번째 이후 포인터는 게임 조작에 영향을 주지 않는다.
- 첫 포인터가 끝나거나 취소된 뒤 새 입력을 허용한다.
- 여러 구조 대상을 동시에 움직일 수 없다.
- 우발적 멀티터치를 실패로 기록하지 않는다.

### 20.2 Pause priority

Pause 버튼은 단일 게임 포인터 규칙의 유일한 명시적 예외다.

활성 드래그 중 다른 손가락으로 Pause를 누르면:

- Pause를 최우선으로 처리한다.
- 활성 게임 입력을 안전하게 취소한다.
- 같은 순간의 성공·실패 판정을 실행하지 않는다.
- 취소를 실패 횟수에 포함하지 않는다.

### 20.3 Pointer cancellation

`pointercancel`, OS 제스처, 화면 이탈 등 시스템 원인의 비정상 종료는 실패로 세지 않는다.

- 주행 드래그: 마지막 확정 높이 유지
- 밧줄 추적: 현재 밧줄 시작 상태로 복귀
- 바위 이동: 현재 바위 원위치 복귀
- 견인 연결: 연결 전 상태로 복귀
- 견인 이동: GUP과 현재 잔해를 견인 시작 위치로 복귀

완료된 이전 단계와 현재 도움 단계는 유지한다.

### 20.4 UI pointer ownership

버튼 안에서 시작한 포인터는 끝날 때까지 UI 입력으로만 처리한다.

- 버튼 밖으로 이동해도 게임 드래그로 전환하지 않는다.
- 같은 버튼 안에서 놓아야 실행한다.
- 버튼 밖에서 놓으면 취소한다.
- 취소된 UI 입력을 게임 실패로 기록하지 않는다.
- 실행 후 남은 포인터 이벤트가 게임 영역으로 전달되지 않게 소비한다.

### 20.5 Browser gestures

16:9 게임 캔버스 내부에서는:

- 핀치 줌 차단
- 화면 스크롤 차단
- 길게 눌러 텍스트 선택 차단
- 컨텍스트 메뉴 차단

캔버스 바깥 브라우저 영역의 기본 동작은 유지한다.

---

## 21. Save-data contract

지속 저장 대상:

- Schema version
- Chosen animal
- Fixed player name: Aiden
- Completed missions
- Unlocked missions
- Mission-card first-open / `New!` seen state
- Last GUP
- Sound volume
- Voice volume

저장하지 않는 대상:

- 현재 미션의 중간 위치
- 현재 구조 단계
- 현재 단계 실패 횟수
- 강화 도움 상태
- 출동 또는 후일담 재생 위치

추가 규칙:

- 프로필은 새로고침 후 유지한다.
- 완료·해금 데이터는 미션 재시작 또는 Exit로 삭제되지 않는다.
- 후속 스테이지 확장을 위해 schema version을 둔다.

---

## 22. Network behavior

- 고정된 비공개 HTTPS URL에서 실행한다.
- 열려 있는 미션 중 일시적인 네트워크 단절이 발생해도 현재 미션 진행을 차단하지 않아야 한다.
- PWA 또는 완전한 오프라인 시작은 MVP 범위에서 제외한다.

네트워크 단절 허용을 위한 정확한 asset-loading 전략은 아직 구현 명세로 확정하지 않았다.

---

## 23. High-level state flow

```text
START
  → FIRST_PROFILE_CHOICE (최초 1회)
  → OCTOPOD_MISSION_SELECT
  → GUP_SELECT
  → LAUNCH_SEQUENCE
  → ACTION_1 (직접 조종 + contextual action)
  → DISCOVERY (구조 대상 발견)
  → ACTION_2 (직접 조종 + contextual action)
  → RESCUE_SITE_TRANSITION
  → RESCUE_TUTORIAL
  → RESCUE_STEP_1
  → RESCUE_STEP_2
  → RESCUE_STEP_3
  → COMPLETION_ANIMATION
  → ECOLOGY_MESSAGE
  → COMPANION_EPILOGUE
  → ANIMAL_EPILOGUE
  → WORLD_REACTION (지역 회복, 동물 등장, 다음 해역 unlock)
  → RESULT_CARD
      ├─ CONTINUE → OCTOPOD_MISSION_SELECT
      └─ REPLAY → LAUNCH_SEQUENCE
```

공통 중단 상태:

```text
ANY_ACTIVE_STATE
  → PAUSED
  → RESUME_COUNTDOWN
  → PREVIOUS_SAFE_STATE
```

차단 오버레이:

- Portrait orientation block
- Insufficient viewport block

이들은 현재 미션 상태를 폐기하지 않는다.

---

## 24. MVP acceptance criteria

### 24.1 Profile and progression

- 최초 선택한 동물 캐릭터가 새로고침 후 유지된다.
- 플레이어 이름은 항상 Aiden이다.
- 미션은 1 → 2 → 3 순서로만 최초 해금된다.
- 완료된 미션을 다시 플레이할 수 있다.
- `New!` 상태가 해당 미션을 처음 열어본 뒤 제거되고 유지된다.

### 24.2 GUP parity

- GUP-C, GUP-I, GUP-X가 모든 미션에서 동일한 규칙과 난이도로 완료 가능하다.
- GUP 선택 차이가 외형과 소리 외의 판정에 영향을 주지 않는다.
- GUP 간 stat/power 차이를 gameplay progression의 중심으로 만들지 않는다.

### 24.3 Action segments (Travel + Action beats)

- 각 미션은 Launch → Action 1 → Discovery → Action 2 → Main Rescue 구조를 가진다.
- Action beat에서 GUP을 손가락으로 직접 조종한다 (자동전진 관람이 아님).
- 한 시점의 contextual action은 최대 하나 (BOOST / SCAN / RESCUE).
- Contextual button 자체가 QTE나 주 gameplay가 되지 않는다.
- 좋은 travel play (충돌 회피, 부드러운 조종, Scan 활용)가 Rescue Readiness를 올린다.
- 충돌은 약 1초 감속만 만들고 미션을 실패시키지 않는다.
- 충돌은 이미 확정된 Readiness milestone을 감소시키지 않는다.
- 충돌은 아직 확정되지 않은 다음 Readiness 진행만 조금 늦춘다.
- 배경 생물은 충돌이나 수집 판정을 만들지 않는다.
- 장애물 위치와 순서는 고정.

### 24.4 Rescue Readiness

- 내부 연속 상태이며 아이에게 숫자/점수/%/별/등급으로 보이지 않는다.
- 화면에서 실제 구조 장비 준비 상태로 표현된다.
- 이미 준비 완료된 장비 milestone은 이후 실수로 다시 꺼지지 않는다.
- Readiness가 낮아도 구조 성공이나 world progression을 막지 않는다.
- Readiness bonus와 adaptive assistance는 서로 다른 개념이다.

### 24.5 Rescue failure isolation

- 잘못된 구조 입력은 현재 구조 단계만 되돌린다.
- 이전 성공 단계는 유지한다.
- 시스템의 pointer cancellation은 실패로 기록하지 않는다.
- Pause로 취소된 입력은 실패로 기록하지 않는다.
- 반복 실패 도움은 현재 단계에만 적용되고 성공 후 초기화된다.
- 이미 완료한 구조 단계는 실패 때문에 되돌리지 않는다.

### 24.6 Mission-specific criteria

#### Mission 1 (Sea Turtle — Precision)

- 밧줄은 고정 순서로 하나씩 활성화된다.
- 넓은 추적 허용 범위가 적용된다.
- 탭 시작점·끝점 대안 입력으로도 완료 가능하다.
- 각 밧줄이 잘릴 때마다 거북이가 점차 긴장을 품.
- 세 번째 밧줄이 잘리면 완전히 자유로워진다.

#### Mission 2 (Crab — Handling)

- 바위를 약 0.4초 홀드해야 잡힌다.
- 바위 중심점이 보관 구역 안에 있을 때만 성공한다.
- 보관 구역 밖에서 놓으면 현재 바위만 원위치로 돌아간다.
- 탭 바위·탭 구역 대안 입력으로도 완료 가능하다.
- 바위 제거 시 게의 반응이 단계별로 진행된다.

#### Mission 3 (Young Whale — Towing / Momentum)

- 견인줄은 잔해에만 연결할 수 있다 (고래에 연결 불가).
- 잔해 3개는 고정 순서로 제거된다.
- 안전 지점에 도달해야 견인이 성공한다.
- 견인 실패 시 현재 잔해와 GUP만 시작 위치로 돌아가고 연결은 유지된다.
- 고래는 통로가 열린 뒤 스스로 빠져나간다.

### 24.7 Audio resilience

- 영어 자막은 항상 표시된다.
- TTS 실패가 미션 진행을 막지 않는다.
- Pause 후 현재 문장이 처음부터 재생된다.
- 음량 설정이 새로고침 후 유지된다.

### 24.8 Pause and environment recovery

- Pause는 모든 활성 게임 상태에서 동작한다.
- Resume은 3초 카운트다운 후 실행된다.
- 앱 전환과 탭 숨김이 자동 Pause를 발생시킨다.
- 세로 방향에서는 게임이 진행되지 않는다.
- 최소 화면 크기 미만에서는 게임이 진행되지 않는다.
- 전체화면 실패 또는 해제 자체는 미션을 차단하지 않는다.

### 24.9 Input safety

- 게임 조작은 한 번에 한 포인터만 소유한다.
- Pause 입력은 활성 게임 포인터보다 우선한다.
- 버튼 연타가 중복 화면 전환이나 중복 미션 시작을 만들지 않는다.
- 버튼 입력이 게임 드래그로 전환되지 않는다.
- 여백에서 시작한 입력은 무시된다.
- 캔버스 내부 브라우저 제스처가 게임 입력을 방해하지 않는다.

### 24.10 No evaluation mechanics

다음 UI와 로직이 존재하지 않는다.

- 점수
- 별
- 등급
- 타이머
- 체력
- 실패 횟수
- 순위표
- Game over
- Lives

---

## 25. Remaining product decisions

다음은 문서 작성 시점에 source와 Grill-me 결정만으로 확정되지 않은 항목이다.

### 25.1 Content

- Mission 1 완료 애니메이션 세부 동작
- Mission 1 생태 메시지
- 세 미션의 동료 후일담 정확한 문구
- 세 미션의 생물 후일담 정확한 문구
- 최초 프로필·동물 선택 화면의 정확한 카피와 연출

### 25.2 Visual and audio assets

- Aiden 세 동물형 캐릭터의 구체적 외형
- GUP-C, GUP-I, GUP-X의 구체적 미리보기 연출
- GUP별 엔진음
- 배경음악 유무와 트랙 구성
- 장애물과 구조 대상의 최종 아트 스타일
- 동료 캐릭터 애니메이션 세트

### 25.3 Technical validation

- 최소 유효 viewport의 픽셀 기준
- Galaxy Tab S10 실제 브라우저 성능 예산
- 목표 브라우저와 최소 버전
- TTS en-GB 음성 부재 시 fallback 우선순위
- 저장 매체와 schema migration의 구체적 구조
- 열린 미션의 네트워크 단절을 보장할 asset-loading 경계
- 단일 HTML 번들 크기 목표
- private HTTPS 접근 제어 방식

이 항목은 구현 전에 모두 한꺼번에 결정할 필요는 없다. 각각 독립적으로 검증 가능한 failure domain으로 분리한다.

---

## 26. Deferred beyond MVP

- 추가 스테이지
- PWA
- 네트워크 없이 새로 게임 시작
- 추가 GUP
- 추가 동물 캐릭터
- 배지
- 도감
- 방 꾸미기
- 수집품
- 랜덤 장애물
- 미션 변형
- 경쟁·점수 시스템

---

## 27. Change summary from v0.1

v0.2에서 추가로 닫힌 주요 요구사항:

- Mission 2의 게 반응, 대사, 완료 연출, 생태 메시지
- Mission 3의 연결, 견인, 실패, 반응, 대사, 완료 연출, 생태 메시지
- 공통 완료 화면과 해금 UX
- GUP 선택과 출동 UX
- 자동 전진의 정확한 길이, 장애물 수, 드래그·탭 조작
- 충돌과 무입력 진행 계약
- 구조 현장 전환과 튜토리얼
- 성공·실패 피드백과 점진적 도움
- Pause, Restart, Exit, 음량, Resume 계약
- 앱 전환, 화면 방향, 최소 viewport 자동 Pause
- 전체화면 실패·해제 처리
- 고정 16:9 캔버스와 여백 입력
- single-pointer, pointer cancellation, UI pointer ownership
- 버튼 연타 re-entrancy 방지
- 저장 대상과 비저장 중간 상태 구분

---

## 28. Change summary from v0.2 to v1.0 (Gameplay direction + AI Studio handoff foundation)

v1.0에서 확정된 주요 변경사항:

### Gameplay direction (supersedes legacy contracts)

- **Gameplay balance 명시**: Action 45% / Main Rescue 40% / World Growth 15%
- **Mission identity 정의**: Sea Turtle=Precision, Crab=Handling, Young Whale=Towing/Momentum — 같은 조작 언어, 다른 구조 능력
- **Core experience principles**: GUP 직접 조종, 단일 contextual action, 구조물 직접 조작
- **Episode pacing 구조**: Launch → Action 1 → Discovery → Action 2 → Main Rescue → World Reaction
- **Rescue Readiness 시스템**: 내부 연속 상태, 장비 준비 시각화, travel play 연동, milestone 보호, collision 효과 제한
- **Mistake philosophy 명시**: Game over/lives/점수/별/등급/강제 restart 없음, 성취 보존, 현재 위치 회복
- **World progression**: 최초 completion만 canonical progression 이동, replay는 살아있는 world 표현, grind 없음
- **Superseded legacy contracts**: 자동전진 보조 구간, 이동 성과 무영향, 환경 차이 시각/음향만

### AI Studio non-canonical implementation lane

- GitHub import/sync를 canonical workflow로 사용하지 않음
- 로컬 deterministic flatpack으로 AI Studio와 상호작용
- 작업 단위: 30-90초 playable vertical slice
- AI Studio는 vertical slice 안 주 설계/구현 주체
- ZIP export 회수 → 로컬 ingest가 exact-base/boundary 검증 후 isolated BUILD worktree에 적용
- Protected surface 변경 시 BOUNDARY_CHANGE_PROPOSAL로만 반환

### Foundation tooling v1 (scripts/ocean_rescue/)

- `ocean_ai.py prepare --spec <task.json> --out <dir>` — deterministic packet + manifest 생성
- `ocean_ai.py ingest --manifest <manifest.json> --zip <result.zip>` — 검증 후 isolated worktree 적용
- Deterministic/security/freshness 계약 자동 테스트로 증명
- Python stdlib 중심, 새 dependency 없음
