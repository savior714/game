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

| 문서/경로 | 역할 |
|-----------|------|
| `PROJECT_RULES.md` | 규칙·운영·검증 프로토콜 SSOT |
| `docs/CRITICAL_LOGIC.md` | 설계 결정·불변 정책 SSOT (대안·채택 이유·증적) |
| `docs/specs/` 및 루트 `specs/` | 요구사항·계약(AC) SSOT — **신규·갱신 우선 위치는 `docs/specs/`**, 루트 `specs/`는 과목·레거시 계약 유지용으로 둔다 |
| `docs/memory/` | 세션 지식 SSOT (`docs/memory/MEMORY.md`는 **인덱스·링크 전용**, 200라인 또는 25KB 상한) |
| `docs/plans/` | 실행 계획·체크리스트(결정이 필요하면 `docs/CRITICAL_LOGIC.md`로 승격) |
| `docs/knowledge/` | 외부 조사·레퍼런스 요약 자산화(스펙/결정 문서에서 링크) |

- `docs/memory.md`는 레거시 포인터로만 유지하고, 신규 세션 지식 누적은 `docs/memory/` 하위 타입 파일에만 기록한다.
- 신규 기능은 반드시 스펙을 선반영한 뒤 구현하고, 결정 변경은 `docs/CRITICAL_LOGIC.md`에 근거와 함께 기록한다.
- **신규 문서** 생성 시 `docs/templates/DOC_SSOT_HEADER_TEMPLATE.md` 헤더를 기본으로 쓴다. 메타 블록은 `## 문서 메타 (Version SSOT)` 형식을 쓰고, 키 순서는 `Last Verified → Tested Version → Min Supported → Reference`로 고정한다.
- **MEMORY.md 갱신** 시 링크 목록만 조정하고, 설명 문장이 필요하면 본문 SSOT·changelog·`project_*.md`에 두고 인덱스에는 링크만 둔다 (`AGENTS.md` MEMORY Anti-Drift와 동일 원칙).

## 2. 주요 디렉토리 및 역할

**비즈니스 로직과 공용 인프라성 코드를 분리해 유지보수성과 검증 가능성을 확보한다.**

- `common/`: 전 과목 공용 코어 로직(`rocket-core.js`, `quiz-ui-core.js`, `progress-engine.js`)
- `global/`: 인증/동기화/보상 전역 로직(`auth.js`, `sync-engine.js`, `reward.js`)
- `math/`, `english/`, `korean/`, `science/`: 과목별 화면/문항/엔진 로직
  - 국어 문항 SSOT: `korean/data/words.json` (`window.WORDS`, `korean/ui.js`에서 로드)
  - 과학 문항 SSOT: `science/data/questions.json` (동일하게 `window.WORDS`로 로드)
- `marble/`: 보상 소비형 미니게임 로직
- `guardian/`: 보호자 상점/설정 UI
- `admin/`: 관리자 도구(허용 계정 접근)
- `supabase/`: 스키마/정책 SQL 및 백엔드 설정 산출물
- `docs/`: 아키텍처·결정·요구사항·메모리·지식 자산
- 루트 검증 스크립트: `verify_all.js`, `verify_net_logic.js`, `verify_shared_core_contract.js`
- `scripts/`: 운영·검증 보조 스크립트가 생기면 표준 위치로 둔다

## 3. 프로젝트 특화 규칙

**아래 규칙은 학습 품질, 공용 계약 안정성, 보호자 기능 신뢰성을 위한 필수 운영 기준이다.**

### SDD·레이어

- 신규 기능·규칙·계약 변경은 **구현 전에** 스펙(`docs/specs/` 우선)을 갱신한다.
- 구조적 결정(폴더 책임, 공용 API, 저장 키 의미)은 `docs/CRITICAL_LOGIC.md`에 대안·채택 이유를 남긴다.
- **도메인·학습 규칙**은 과목 엔진·`common/*` 쪽에 두고, **인프라·외부 연동**(Supabase 호출, 네트워크, 저장소 어댑터)은 `global/*` 및 해당 어댑터에서 처리한다. 과목 `ui.js`는 표현과 입력 수집에 가깝게 유지한다.

### 운영 규칙(번호 목록)

1. 과목별 `ui.js`와 `engine.js`에서 공용 흐름은 재구현하지 말고 `common/*` 코어를 호출하라.
2. 난이도/그물망/보상 정책을 변경할 때는 `docs/CRITICAL_LOGIC.md`에 대안과 채택 이유를 먼저 기록하라.
3. 새 과목/기능 추가 시 `docs/specs/` 또는 `specs/`에 계약(입력/출력/AC)을 먼저 확정하라.
4. 보호자/관리자 기능(`guardian/`, `admin/`)은 인증 상태 미확인 시 기능 실행을 차단하라.
5. Supabase 연동 코드(`global/auth.js`, `global/sync-engine.js`) 변경 시 오프라인 큐와 타임스탬프 병합 규칙의 역호환을 보장하라.
6. 과목별 UI 변경 시 학습 진행 지표(정답/오답/연속정답/레벨 상태)의 저장 키와 의미를 변경하지 마라.
7. 검증 스크립트에서 실패한 상태로 병합하지 마라. 실패 원인과 조치 결과를 PR/작업 로그에 남겨라.
8. 단일 파일이 **500라인을 초과**하면 즉시 기능 단위로 분리한다(완료 보고만 하고 방치하지 않는다).

## 4. 코드 수정 후 Verify 프로토콜 (필수)

**모든 수정은 계약 검증과 스모크를 분리 실행하고, 실패 시 원인 해결 전 종료하지 않는다.**

- 적용 범위: 모든 코드 변경(신규/수정/리팩터링/삭제) 직후, 사용자 응답 전에 검증한다.
- 검증 순서: **정적·계약 검증(Node) → 프론트 스모크(로컬 서버)** 를 고정한다.
- **통합 진입점**: 현재 저장소는 루트에 `verify.sh`가 없을 수 있다. 이 경우 아래 **4.0 Node 순서**가 단일 통합 절차다. 루트에 `verify.sh`(또는 동일 역할 스크립트)가 추가되면 그 스크립트가 단일 진입점이 되며, 산출물이 `verify-last-result.json`이면 **에이전트는 터미널 전체 로그 대신 Read로 JSON만** 읽는다(`AGENTS.md`와 동일).

### 4.0 통합 검증(Node, 작업 보고 전 필수)

```bash
node verify_net_logic.js
node verify_shared_core_contract.js
node verify_all.js
```

- 하나라도 실패하면 다음 작업을 중단하고, 실패 스크립트가 가리키는 계약 위반을 먼저 수정한다.
- 수정 후 **실패했던 명령부터** 재실행하고, 마지막에 `node verify_all.js`로 전체 회귀를 확인한다.
- 과목 엔진 등을 직접 수정했다면 해당 과목의 `verify_*_engine.js`(존재 시)도 영향 범위에 포함한다.

### 4.0.1 문서 인코딩 및 편집 도구(모지바케 방지)

- 프로젝트 문서는 **UTF-8(BOM 없음)** 을 원칙으로 한다.
- 문서 생성·수정 시 셸 리다이렉션(`>`)이나 인코딩이 불명확한 파이프로 한국어 본문을 쓰지 않는다. 에디터·에이전트 편집 도구로 저장해 인코딩을 유지한다.

### 4.1 프론트엔드 실행/스모크 검증

```bash
python serve_game.py --no-browser
```

- 서버 구동 후 `http://localhost:3000` 및 변경한 화면 경로를 열어 기본 렌더링·상호작용 오류가 없는지 확인한다.
- 페이지 로드 오류, 콘솔 예외, 핵심 버튼 동작 실패가 있으면 재현 경로를 짧게 기록하고 원인을 제거한다.
- Windows에서 `python` 이 없으면 `py -3 serve_game.py --no-browser` 를 사용한다.

### 4.2 실패 처리 원칙

- 검증 실패를 무시하고 커밋·배포하지 않는다.
- 임시 우회(주석 처리, 조건 무력화)로 통과시키지 않는다.
- 실패 원인, 수정 내용, 재검증 결과를 한 세트로 남겨 재현 가능성을 보장한다.

### 4.3 문서 및 추적성

- 명세 선반영: 신규 기능·규칙 변경은 `docs/specs/`(또는 해당 스펙 경로)를 먼저 갱신한다.
- 설계 판단은 `docs/CRITICAL_LOGIC.md`에 단계·근거를 남긴다.
- 세션 종료 시 `docs/memory/MEMORY.md`는 인덱스만 갱신하고, 상세는 `docs/memory/` 하위 타입 파일에 둔다.
- 동일한 수동 작업이 반복되면 `docs/CRITICAL_LOGIC.md`·메모리를 참고해 `.agents/workflows/` 에 워크플로우 승격을 검토한다.

### 4.4 완료 보고 템플릿(응답 직전)

에이전트·기여자는 사용자 응답에 아래를 **한국어**로 포함한다.

- **통합 검증**: 실행한 명령·결과 요약(실패 시 실패 스크립트명과 원인 한 블록). `verify-last-result.json`을 쓰는 경우 exitCode·`failedStep`·후속 조치.
- **변경 파일**: 경로 목록
- **정적/계약 검증**: 위 4.0과 중복되면 "4.0과 동일" 한 줄 가능
- **스모크**: 확인한 URL·시나리오·결과
- **리스크/후속**: 잔여 리스크, 실패 시 다음 액션(파일·테스트·스크립트명을 구체적으로)

### 4.5 규칙 변경 시 워크플로우 동기화

`PROJECT_RULES.md` 또는 `AGENTS.md` 등 핵심 규칙을 바꾼 경우, `.agents/workflows/` 내 관련 워크플로우(plan, go, git, audit, evidence 등)가 구식 절차를 가리키지 않는지 검토한다.

### 4.6 사전 검증(Pre-Guard)

코드 작성 전 아래를 점검한다.

- **계약·공용 코어**: `common/*`·`global/*` 시그니처와 검증 스크립트가 기대하는 패턴을 깨지 않는다.
- **저장 키·진행 상태**: 로컬/동기화 키 의미를 바꾸지 않는다(불가피하면 스펙·CRITICAL_LOGIC에 선행 기록).
- **인증 경로**: 보호자·관리자·유료 흐름은 인증 가드 누락이 없는지 확인한다.
- **문서**: UTF-8 유지, SSOT 중복 서술 금지.
- **테스트·검증**: 과목별 `verify_*` 또는 통합 스크립트가 있는 경우 변경 영역을 실행 목록에 넣는다.
