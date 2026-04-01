# Memory SSOT (Summary)

- **전 과목 적응형 7단계 엔진**:
  - 국어, 수학, 영어, 과학 전 과목 입문~전설 7단계 체계 및 Confidence Recovery (연속 오답 시 하향) 도입.
  - 중복 방지 엔진(최근 10문제 버퍼) 및 유일 정답 원칙 확립.
- **보석 경제 시스템 (2026-03-28)**:
  - 룰렛 시스템 제거 및 💎 보석 화폐 도입.
  - 20연속 정답(로켓 발사) 시 보석 1개 지급 및 보석 상점(유튜브/간식/마블) 운영.
  - **상단 보상바 UI 개선**: 고정 너비(92px), 고정 간격(12px), 단위 통일(개/분/회)을 통해 시각적 정합성 및 리듬감 확보.
  - **보상바·상점 UI (후속)**: 인벤토리 바를 그리드 3열(좌 레일·중앙 슬롯·우 로그인/설정)으로 재구성; 보석 상점 카드 호버 시 하단 테두리가 잘리던 현상을 호버 레이어 `z-index`로 수정.
  - **보상바 겹침 (CSS)**: 인벤토리 바를 Grid 대신 Flex 한 행으로 두고 `inventory-center`에 `flex: 1 1 0`·`min-width: 0`·가로 스크롤, 우측은 `flex: 0 0 auto`, 빈 좌측 레일 폭 0, `inventory-auth` 가변 너비·말줄임(`global/reward.css`).
  - **보상바 세로 스크롤 (CSS)**: `inventory-center`에 `overflow-y: hidden` — 호버 `translateY` 시 세로 스크롤바 깜빡임 방지(`global/reward.css`).
- **공용 코어 아키텍처 (2026-03-27)**:
  - `rocket-core`, `rocket-effects`, `progress-engine`, `quiz-ui-core`로 중복 로직 통합 및 분리.
  - 전 과목 `index.html`, `engine.js`, `ui.js`가 코어 인터페이스를 위임 호출하도록 개편.
- **그물망 보호 시스템 (Net Shield)**:
  - 5연속 정답 시 그물망 획득, 추락 시 1회 튕겨 복귀하는 아동 보호 로직 전 과목 동기화.
- **데이터 정합성 및 검증 로직**:
  - `verify_all.js`를 통한 전 과목 데이터 및 코어 계약 무결성 자동화 검증 체계 구축.

- **구글 로그인 및 오프라인-온라인 동기화 (2026-03-29)**:
  - Supabase 기반 구글 로그인 인증 스택(`global/auth.js`) 추가.
  - 오프라인 큐 및 타임스탬프 비교(최종 완료 기록 우선 병합)를 제공하는 분산 데이터 동기화 엔진(`global/sync-engine.js`) 장착.
  - 전역 스토리지 매니저(`progress-engine`, `reward`)에 클라우드 자동 델리게이트 훅 연결 완료.
  - **관리자 전용**: `ADMIN_EMAILS` + `user_directory` 테이블·RLS(`supabase/user_directory.sql`)로 가입 구글 계정 목록을 `admin/index.html`에서만 조회.

- **보상 상점 커스터마이징 (2026-03-28)**:
  - 보호자가 구글 로그인 연동 환경에서 커스텀 보상(아이콘, 문구, 가격)을 1보석 단위로 자유롭게 등록/삭제할 수 있는 동적 상점(`reward.js`, `reward_ui.js`) 및 관리 UI(`guardian/index.html`) 구축. 잔여 보상 회수 로직 추가 완료.
  - **바·편집 (동일 일자 후속)**: `shop_items` 항목은 재고 0이어도 상단 바에 슬롯 노출(`empty-slot` 스타일); `syncInventoryBarWithState`로 상점 배열 변경 시 바 DOM 재구성. 보호자 목록에서 기본 프리셋 포함 **편집** 모달(아이콘·이름·설명·가격, 내부 id 고정).
  - **보호자 상점 UX (2026-03-29)**: 목록 이모지 클릭으로 편집 모달 진입, 빈 아이콘 저장 시 기본값(선물 이모지), 추가 폼 아이콘 필드 리셋. 아이콘 입력란에 Windows **Win + .** 이모지 패널 안내 문구(`guardian/index.html`, `guardian/guardian.js`).
  - **보호자 설정 진입 (2026-03-29)**: 구글 로그인 세션이 있으면 인벤토리 바 `checkGuardian`이 곱셈 확인(`prompt`) 없이 `guardian/index.html`로 이동; 비로그인 시 기존 산술 게이트 유지(`global/reward_ui.js`).

- **데이터 동기화 및 난이도 안정성 보강 (2026-03-29)**:
  - `global/sync-engine.js`: 서버 데이터를 덮어쓰지 않고 로컬과 합산하는 `mergeGameStatsPayload` (딥 머지) 도입하여 계정 간 진행도 유실 방지.
  - `common/progress-engine.js`: 승급(90%)과 하강(80%) 임계치를 분리한 히스테리시스(Hysteresis) 설계로 '난이도 널뛰기' 현상 해결.
  - `docs/CRITICAL_LOGIC.md`: 분산 데이터 병합 규칙(섹션 20) 및 난이도 보정 상세 수치 업데이트.

- **전 과목 시간 제한 상향 (2026-03-29)**:
  - 모든 게임(수학, 과학, 영어, 국어)의 `TIME_LIMIT`을 60초에서 120초로 일괄 상향하여 학습자(어린이)의 심리적 압박 감소 및 풀이 여유 확보.
  - `specs/platform.md`, `math.md`, `english.md` 및 각 과목 `engine.js` 내 상수 동기화 완료.

- **영어 주간 시험 단어 레이아웃 개선 (2026-03-31)**:
  - **레이아웃**: `.q-blanked`에 `flex-wrap: nowrap` 및 `gap: 4px` 적용하여 긴 단어("responsibility" 등)가 한 줄로 노출되도록 고정.
  - **동적 스케일링**: 11자 이상의 단어 출제 시 `.q-long` 클래스를 통해 폰트 크기를 자동으로 축소(`2rem` -> `1.6rem`)하여 카드 너비(480px) 내 정합성 확보.
  - **블록 최적화**: 개별 글자 블록(`.sl`)의 `min-width`를 `0.9em`으로 줄여 가로 밀착도 향상.

- **영어 고급 문제 유형 (2026-04-01)**:
  - `minimal_pair`(레벤슈타인 1~3 우선 오답), `sentence`(카테고리별 영문장 `_____` + 4지선다), `typing`(직접 입력·정규화 채점) 추가. `english/advanced-questions.js` 분리, 난이도 레벨별 5유형 가중치·주간 단어 5유형 순환은 `specs/english.md`·`docs/CRITICAL_LOGIC.md` §22 참조.

- **보석 지급 안정성 보강 (2026-04-01)**:
  - **20연속 보상 지급은 UI 연출 성공 여부와 무관하게 코어에서 보장**하도록 `global/reward.js`의 `playEntranceAndAddGem`에 fallback(`add('gems', 1)`) 적용.
  - `RewardSystemUI` 미로딩/런타임 예외 시에도 보석 누락이 발생하지 않도록 방어 로직 추가.

*이전 상세 기록은 `docs/archive/memory_20260328.md`를 참조하세요.*
