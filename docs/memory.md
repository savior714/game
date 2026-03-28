# Memory SSOT (Summary)

- **전 과목 적응형 7단계 엔진**:
  - 국어, 수학, 영어, 과학 전 과목 입문~전설 7단계 체계 및 Confidence Recovery (연속 오답 시 하향) 도입.
  - 중복 방지 엔진(최근 10문제 버퍼) 및 유일 정답 원칙 확립.
- **보석 경제 시스템 (2026-03-28)**:
  - 룰렛 시스템 제거 및 💎 보석 화폐 도입.
  - 20연속 정답(로켓 발사) 시 보석 1개 지급 및 보석 상점(유튜브/간식/마블) 운영.
  - **상단 보상바 UI 개선**: 고정 너비(92px), 고정 간격(12px), 단위 통일(개/분/회)을 통해 시각적 정합성 및 리듬감 확보.
  - **보상바·상점 UI (후속)**: 인벤토리 바를 그리드 3열(좌 레일·중앙 슬롯·우 로그인/설정)으로 재구성; 보석 상점 카드 호버 시 하단 테두리가 잘리던 현상을 호버 레이어 `z-index`로 수정.
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

- **문서 SSOT 정합성 (2026-03-29)**:
  - `README.md`, `SDD.md`, `specs/*`, `docs/specs/*`(보상 인벤토리·공용 코어·과학 DB), `docs/shared_logic_separation_audit.md`, `docs/net_overlap_diagnostic.md`를 보석 경제·공용 코어·동기화·그물망 구현 기준으로 최신화.

*이전 상세 기록은 `docs/archive/memory_20260328.md`를 참조하세요.*
