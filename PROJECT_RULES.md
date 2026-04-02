# Project Context: AIDEN_GAME

## 1. 기술적 환경 (Tech Stack)

**이 프로젝트는 정적 웹 프론트엔드와 경량 로컬 서버, Supabase 기반 인증/동기화로 운영한다.**

- 프로젝트명: AIDEN_GAME
- 도메인/업종: GAME (어린이 학습 게임 플랫폼)
- 핵심 목표:
  - 과목별 학습 경험의 일관성과 난이도 적응 품질 유지
  - 보상/인벤토리/상점 흐름의 신뢰성 유지
  - Supabase 기반 계정/동기화 안정성 확보
- 팀 구성/개발 방식: SDD(Spec-Driven Design) 기반, 스펙 선행 후 구현
- 백엔드 스택:
  - Supabase (Auth, 데이터 저장, 정책/RLS)
  - Node.js 기반 검증 스크립트(`verify_*.js`)를 통한 공용 계약 검증
- 프론트엔드 스택:
  - Vanilla JavaScript + HTML + CSS (과목별 `engine.js`, `ui.js`)
  - 공용 코어 모듈(`common/*`) 위임 구조
- 인프라/배포 환경:
  - 로컬 개발 서버: Python `serve_game.py` (port 3000)
  - 웹 클라이언트 정적 서빙 + Supabase 연동

## 1.1 문서 SSOT 경계(작성 규약)

**문서는 역할별 SSOT를 엄격히 분리하고, 동일 본문을 중복 작성하지 않는다.**

- `PROJECT_RULES.md`: 규칙/운영 SSOT
- `docs/CRITICAL_LOGIC.md`: 결정/불변 SSOT
- `docs/specs/`: 요구사항/계약 SSOT
- `docs/memory/`: 세션 지식 SSOT (`docs/memory/MEMORY.md`는 인덱스 전용)
- `docs/memory.md`는 레거시 포인터로만 유지하고, 신규 세션 지식 누적은 `docs/memory/` 하위 타입 파일에만 기록한다.
- 신규 기능은 반드시 `docs/specs/` 선반영 후 구현하고, 결정 변경은 `docs/CRITICAL_LOGIC.md`에 근거와 함께 기록한다.

## 2. 주요 디렉토리 및 역할

**비즈니스 로직과 공용 인프라성 코드를 분리해 유지보수성과 검증 가능성을 확보한다.**

- `common/`: 전 과목 공용 코어 로직(`rocket-core.js`, `quiz-ui-core.js`, `progress-engine.js`)
- `global/`: 인증/동기화/보상 전역 로직(`auth.js`, `sync-engine.js`, `reward.js`)
- `math/`, `english/`, `korean/`, `science/`: 과목별 화면/문항/엔진 로직
- `marble/`: 보상 소비형 미니게임 로직
- `guardian/`: 보호자 상점/설정 UI
- `admin/`: 관리자 도구(허용 계정 접근)
- `supabase/`: 스키마/정책 SQL 및 백엔드 설정 산출물
- `docs/`, `specs/`: 아키텍처/결정/요구사항 문서
- 루트 검증 스크립트:
  - `verify_all.js`
  - `verify_net_logic.js`
  - `verify_shared_core_contract.js`

## 3. 프로젝트 특화 규칙

**아래 규칙은 학습 품질, 공용 계약 안정성, 보호자 기능 신뢰성을 위한 필수 운영 기준이다.**

1. 과목별 `ui.js`와 `engine.js`에서 공용 흐름은 재구현하지 말고 `common/*` 코어를 호출하라.
2. 난이도/그물망/보상 정책을 변경할 때는 `docs/CRITICAL_LOGIC.md`에 대안과 채택 이유를 먼저 기록하라.
3. 새 과목/기능 추가 시 `docs/specs/` 또는 `specs/`에 계약(입력/출력/AC)을 먼저 확정하라.
4. 보호자/관리자 기능(`guardian/`, `admin/`)은 인증 상태 미확인 시 기능 실행을 차단하라.
5. Supabase 연동 코드(`global/auth.js`, `global/sync-engine.js`) 변경 시 오프라인 큐와 타임스탬프 병합 규칙의 역호환을 보장하라.
6. 과목별 UI 변경 시 학습 진행 지표(정답/오답/연속정답/레벨 상태)의 저장 키와 의미를 변경하지 마라.
7. 검증 스크립트에서 실패한 상태로 병합하지 마라. 실패 원인과 조치 결과를 PR/작업 로그에 남겨라.
8. 단일 파일이 500라인에 근접하면 기능 단위로 분리해 테스트 가능성을 유지하라.

## 4. 코드 수정 후 Verify 프로토콜 (필수)

**모든 수정은 프론트엔드/백엔드 관점의 검증을 분리 실행하고, 실패 시 원인 해결 전 종료하지 않는다.**

### 4.1 백엔드/공용 로직 검증

```bash
node verify_net_logic.js
node verify_shared_core_contract.js
node verify_all.js
```

- 하나라도 실패하면 즉시 다음 작업을 중단하고, 실패 스크립트의 누락 패턴 또는 계약 위반을 먼저 수정하라.
- 수정 후 실패한 명령부터 재실행하고, 마지막에 `node verify_all.js`로 전체 회귀를 확인하라.

### 4.2 프론트엔드 실행/스모크 검증

```bash
python serve_game.py --no-browser
```

- 서버 구동 후 `http://localhost:3000` 및 변경한 화면 경로를 열어 기본 렌더링/상호작용 오류가 없는지 확인하라.
- 페이지 로드 오류, 콘솔 예외, 핵심 버튼 동작 실패가 있으면 코드 수정보다 먼저 재현 경로를 기록하고 원인을 제거하라.
- Windows 환경에서 `python` 명령이 없으면 `py -3 serve_game.py --no-browser`를 사용하라.

### 4.3 실패 처리 원칙

- 검증 실패를 무시하고 커밋/배포하지 마라.
- 임시 우회(주석 처리, 조건 무력화)로 통과시키지 마라.
- 실패 원인, 수정 내용, 재검증 결과를 한 세트로 남겨 재현 가능성을 보장하라.
