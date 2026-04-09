# PROJECT_RULES.md 템플릿 (다른 프로젝트 이식용)

이 파일은 **다른 저장소에 복사한 뒤** `PROJECT_RULES.md`로 이름을 바꾸고, 아래 **적용 절차**대로 채워 넣을 때 사용합니다. freeEMR의 `PROJECT_RULES.md`와 **동일한 뼈대(섹션 번호·역할)**를 유지합니다.

---

## 이 템플릿을 쓰는 방법

1. **복사**: 이 파일 전체를 대상 프로젝트 루트에 `PROJECT_RULES.md`로 저장합니다.
2. **치환**: `{{...}}` 플레이스홀더를 모두 실제 값으로 바꿉니다. (검색: `{{`)
3. **선택 블록**: `<!-- 선택: 시작` … `선택: 끝 -->` 안의 내용은 해당되지 않으면 **통째로 삭제**합니다.
4. **도메인 규칙**: §3의 “프로젝트 특화 규칙”은 스택·보안·UI 도구에 맞게 **항목을 추가/삭제**합니다. (예: FastAPI가 없으면 라우팅 절 삭제)
5. **검증 스크립트**: §4는 저장소에 실제로 있는 `verify.ps1`/`verify.bat`와 동일한 명령·산출물명으로 맞춥니다. 없으면 §4.0을 “수동 절차만”으로 줄이고 4.1·4.2만 남깁니다.
6. **Cursor 규칙**: `.cursor/rules/Project-Rules.mdc` 등에서 이 파일을 참조하도록 한 줄 링크를 두면 에이전트와 규칙이 동기화됩니다.

**플레이스홀더 표기**

| 토큰 | 의미 |
|------|------|
| `{{PROJECT_DISPLAY_NAME}}` | 문서 제목용 표시명 (예: freeEMR) |
| `{{PROJECT_ONE_LINER}}` | 한 줄로 비전/범위 (도메인·규제·통합 목표) |
| `{{BACKEND_ROOT}}` | 백엔드 루트 폴더명 (예: `backend`) |
| `{{FRONTEND_ROOT}}` | 프론트 루트 폴더명 (예: `frontend`) |
| `{{...}}` | 그 외 각주석에 적힌 대로 채움 |

---

아래부터 **`PROJECT_RULES.md` 본문 템플릿**입니다. (복사 시 위 “이 템플릿을 쓰는 방법” 절은 삭제하거나 `docs/templates/`에 원본만 남겨도 됩니다.)

---

# Project Context: {{PROJECT_DISPLAY_NAME}} ({{PROJECT_TAGLINE}})

{{PROJECT_ONE_LINER}}

## 1. 기술적 환경 (Tech Stack)

### **Backend**

- **언어**: **{{BACKEND_LANGUAGE_VERSION}}**
- **프레임워크**: **{{BACKEND_FRAMEWORK}}**
- **런타임/서버(개발)**: **{{DEV_SERVER_OR_RUNTIME}}** (없으면 “해당 없음” 또는 로컬 실행 명령만)
- **아키텍처**: **{{ARCHITECTURE_STYLE}}** (예: SDD 기반 레이어 분리)
  - `{{BACKEND_ROOT}}/src/domain/`: 도메인 규칙/정책/SSOT
  - `{{BACKEND_ROOT}}/src/application/`: 유스케이스/서비스 계층
  - `{{BACKEND_ROOT}}/src/infrastructure/`: DB/캐시/외부시스템 어댑터
  - `{{BACKEND_ROOT}}/src/main/`: API 엔트리포인트/라우터(Interface)
- **데이터/검증**: {{VALIDATION_STACK}} (예: Pydantic v2)
- **DB 접근**: {{DB_ACCESS_STACK}}
- **캐시/세션/큐**: {{CACHE_QUEUE_STACK}} (없으면 “해당 없음”)
- **보안/암호화**: {{SECURITY_LIBS}} (없으면 “프로젝트 정책에 따름”)

<!-- 선택: 시작 — 백엔드에만 해당하는 추가 규격(예: FHIR, gRPC, 이벤트 스키마) -->
- **{{OPTIONAL_BACKEND_CONTRACT}}**: {{OPTIONAL_BACKEND_CONTRACT_DETAIL}}
<!-- 선택: 끝 -->

### **Frontend**

- **기반 기술**: **{{FRONTEND_FRAMEWORK_VERSION}}**
- **언어**: {{FRONTEND_LANGUAGE}} (예: TypeScript, `strict: true`)
- **UI Framework**: **{{UI_FRAMEWORK}}**
- **레이아웃/그리드**: {{LAYOUT_LIBS}} (없으면 “해당 없음”)
- **품질 도구**: {{FE_QUALITY_TOOLS}}
- **E2E 테스트**: {{E2E_STACK}} (없으면 “미도입” 또는 계획 한 줄)

### **Infrastructure & Tools**

- **Database (목표/스펙)**: {{DB_PRODUCT_VERSION}}
- **Local Sandbox**: {{LOCAL_DB_OR_MOCK}} (없으면 “해당 없음”)
- **Cache / Queue**: {{INFRA_CACHE_QUEUE}}
- **문서 SSOT**: `docs/specs/`, `docs/CRITICAL_LOGIC.md`, `docs/memory/`
- **로컬 기동**: `{{DEV_START_SCRIPT}}` (없으면 README의 “로컬 실행” 절을 링크)

## 1.1 문서 SSOT 경계(작성 규약)

프로젝트 문서의 역할을 아래처럼 **분리**합니다. “같은 내용이 여러 곳에 중복”되면, 반드시 **SSOT 쪽만 남기고 나머지는 링크로 대체**합니다.

- **`PROJECT_RULES.md` (규칙/운영 SSOT)**: “항상 지켜야 하는 규칙”과 “검증/운영 프로토콜”, 디렉토리 역할, 도구 사용 원칙 등 **지속 규범**을 기록합니다.
  - 예) 검증 순서, 파일 {{MAX_LINES_PER_FILE}}라인 가드레일, Docs-First 원칙, 라우팅 회귀 방지 규칙, 마킹 규약
- **`docs/CRITICAL_LOGIC.md` (결정/핵심 불변 SSOT)**: “왜 그렇게 했는지”가 중요한 **핵심 결정(대안/채택 이유/증적 경로)**과, 회귀 시 치명적인 **불변 정책(상태 머신/계약/SSOT 고정점)**을 Decision Log로 기록합니다.
- **`docs/specs/` (요구사항/계약 SSOT)**: 기능·도메인·기술의 **요구사항/인터페이스/수용 기준(AC)**을 명세합니다. 구현 중 설계 판단이 생기면 `docs/CRITICAL_LOGIC.md`에 먼저 결정으로 남기고, 스펙은 “결정된 결과”로 업데이트합니다.
- **`docs/memory/` (세션 지식 SSOT)**: 진행 상황/회의 요약/작업 맥락 등 **세션성 정보**를 저장합니다. `docs/memory/MEMORY.md`는 **인덱스(링크·최소 메타)만** 유지합니다. **장문 요약·Task 서술·기술 메모·긴 괄호 설명**은 본문 SSOT에 두고 `MEMORY.md`에는 넣지 않습니다(**`AGENTS.md` §2.1.1 MEMORY Anti-Drift**).
- **`docs/plans/` (작업 계획)**: 실행 계획/체크리스트/영향 범위를 관리합니다. 계획에서 결정이 필요해지면 `docs/CRITICAL_LOGIC.md`로 승격합니다.
- **`docs/knowledge/` (외부 지식 자산)**: 웹 검색/레퍼런스 요약을 저장하고, 필요 시 관련 스펙/결정 문서에서 링크합니다.

### 신규 문서 작성 체크리스트(재발 방지)
- `MEMORY.md` 갱신 시: **링크 목록만** 추가·삭제하고, 설명 문장을 쓰려면 본문 SSOT에 기록한 뒤 인덱스에는 링크만 둡니다.
- 신규 문서 생성 시 `docs/templates/DOC_SSOT_HEADER_TEMPLATE.md`의 헤더를 먼저 붙입니다.
- 메타 헤더는 `## 문서 메타 (Version SSOT)`를 사용하고, 키 순서를 `Last Verified -> Tested Version -> Min Supported -> Reference`로 고정합니다.
- 문서 유형별 본문 위치를 고정합니다:
  - 규칙/운영 변경: `PROJECT_RULES.md`
  - 설계 결정/불변 정책: `docs/CRITICAL_LOGIC.md`
  - 요구사항/계약: `docs/specs/`
  - 세션성 기록: `docs/memory/`
- 동일 주제를 두 문서에 중복 서술하지 않고, SSOT 본문 1곳 + 링크 참조로 정리합니다.

## 2. 주요 디렉토리 및 역할

- `{{BACKEND_ROOT}}/`: {{BACKEND_ROLE_ONE_LINE}}
  - `{{BACKEND_ROOT}}/src/main/`: 앱 엔트리포인트 및 라우팅(Interface)
  - `{{BACKEND_ROOT}}/src/application/`: 서비스/유스케이스/DTO
  - `{{BACKEND_ROOT}}/src/domain/`: 도메인 규칙/모델/정책(비즈니스 SSOT)
  - `{{BACKEND_ROOT}}/src/infrastructure/`: DB/외부 연동(인프라 구현)
- `{{FRONTEND_ROOT}}/`: {{FRONTEND_ROLE_ONE_LINE}}
  - `{{FRONTEND_ROOT}}/app/`: Next.js App Router 라우트
  - `{{FRONTEND_ROOT}}/src/`: 재사용 컴포넌트/컨텍스트/피처/스타일
- `docs/`:
  - `specs/`: 기능/도메인/기술 스펙 (SDD의 근간)
    <!-- 선택: 시작 — 스펙 하위 구조를 프로젝트에 맞게 나열 -->
    - `specs/{{SPEC_SUBFOLDER_1}}/`: {{SPEC_SUBFOLDER_1_ROLE}}
    - `specs/{{SPEC_SUBFOLDER_2}}/`: {{SPEC_SUBFOLDER_2_ROLE}}
    <!-- 선택: 끝 -->
  - `memory/`: 세션/프로젝트 지식(SSOT)
  - `memory/MEMORY.md`: 프로젝트 상태 요약 및 인덱스 (**{{MEMORY_INDEX_MAX_LINES}}라인 제한**)
  - `CRITICAL_LOGIC.md`: 핵심 설계 결정 및 로직/근거(SSOT)
  - `knowledge/`: 외부 지식 자산화(필요 시)
- `tests/`: {{TESTS_SCOPE}}
- `scripts/`: 운영/검증/보조 스크립트(존재 시 여기를 표준 위치로 간주)

## 3. 프로젝트 특화 규칙

<!-- 선택: 시작 — 규제·안전·컴플라이언스가 핵심인 도메인일 때 -->
### **핵심 목표 준수({{COMPLIANCE_OR_SAFETY_LABEL}})**

- **추적성**: 기능 추가/변경은 반드시 `docs/specs/`에서 해당 요구사항/지표와 연결(근거 포함)합니다.
- **안전성 우선**: {{SAFETY_PRIORITIZED_AREAS}} 관련 로직은 “편의”보다 “정합성/재현성/감사 가능성”을 우선합니다.
<!-- 선택: 끝 -->

### **SDD 고수 (Docs-First)**

- 신규 기능/규칙 변경/계약 변경은 **구현 전에** `docs/specs/`를 갱신합니다.
- 구조적 결정(폴더 이동, 추상화 도입, 계약 변경)은 `docs/CRITICAL_LOGIC.md`에 **대안/채택 이유**까지 기록합니다.

### **레이어 분리(비즈니스 vs 인프라)**

- 도메인 규칙/정책/정합성 판단은 `{{BACKEND_ROOT}}/src/domain/` 및 `{{BACKEND_ROOT}}/src/application/`에 둡니다.
- DB/HTTP 라우팅/외부 API 등은 `{{BACKEND_ROOT}}/src/infrastructure/` 및 `{{BACKEND_ROOT}}/src/main/`에서 “실현”만 합니다.

<!-- 선택: 시작 — 웹 API 프레임워크가 정적/동적 라우트 순서에 민감할 때 -->
### **{{API_FRAMEWORK_NAME}} 라우팅 회귀 방지**

- **정적 라우트 우선**: `GET /X/today-queue` 같은 정적 세그먼트는 `GET /X/{id}`보다 **반드시 먼저 선언**합니다.
- 문서/프론트가 참조하는 경로가 런타임에서 동적 매칭에 흡수되면 SSOT가 깨집니다.
<!-- 선택: 끝 -->

<!-- 선택: 시작 — 프론트가 백엔드에 직접 붙는 정책을 쓸 때 -->
### **Frontend API 통신 정책**

- {{FRONTEND_API_POLICY_ONE_LINE}}
- 인증 헤더/쿠키 유실 등 회귀가 발생하면, 우선 이 정책 위반 여부를 점검합니다.
<!-- 선택: 끝 -->

<!-- 선택: 시작 — 개발용 DOM 마킹/인스펙터 도구를 쓸 때 -->
### **{{DEV_MARKING_TOOL_NAME}} 마킹 규약(개발 도구 안정성)**

- **명시적 마킹 우선순위**: DOM `data-dev-*` 속성이 Fiber 정보보다 우선합니다.
- **권장 속성**:
  - `data-dev-component="{ComponentName}"`
  - `data-dev-src="{relative/path/or_filename}"`
  - `data-dev-line="{number}"` (권장)
- **루트 컨테이너 규약**: 가능한 한 “단일 최외곽 컨테이너”를 반환합니다(최외곽 Fragment 지양).
<!-- 선택: 끝 -->

### **파일 크기/리팩터링 가드레일**

- 단일 파일이 **{{MAX_LINES_PER_FILE}}라인을 초과**하면 즉시 하위 모듈로 분리합니다(완료 보고 금지).

## 4. 코드 수정 후 Verify 프로토콜 (필수)

- **적용 범위**: 모든 코드 변경(신규/수정/리팩터링/삭제) 직후, 사용자 응답 전에 반드시 검증합니다.
- **검증 순서**: `정적 검증 -> 단위/통합 테스트 -> 스모크 검증 -> 결과 기록` 순서를 고정합니다.
- **실패 처리 원칙**: 검증 실패 시 즉시 수정 후 재검증하며, 실패 상태에서 완료 보고를 금지합니다.

### 4.0.2 macOS/Windows 문서 인코딩 및 셸 사용 주의사항 (Mojibake 방지)

- **원칙**: 모든 프로젝트 문서는 **UTF-8 (BOM 없음)** 인코딩을 강제합니다.
- **셸 작업 금지**: 문서 생성/수정 시 셸의 리다이렉션(`>`)이나 PowerShell의 `Set-Content` 명령을 **사용하지 않습니다**.
- **이유**: 특정 셸 환경(Windows PowerShell 5.1 등)의 기본 인코딩으로 인해 한국어 텍스트가 깨질 수 있으며, 복구 불가능한 오염을 초래합니다.
- **권장 도구**: 반드시 `write_to_file`, `replace_file_content`와 같은 에이전트 전용 도구를 사용합니다.

### 4.0.1 한국어 텍스트 Hallucination 및 인코딩 검증

- **목적**: AI 생성 문서에서 의도치 않게 혼입된 한자(CJK), 일본어(가나) 문자를 탐지합니다.
- **실행 명령**: `python scripts/verify_korean_text.py --dir docs --fail-on-issue`
- **결과 처리**: 문제가 발견되면 즉시 수정 후 재검증합니다.

### 4.0 통합 검증 `verify.sh` (또는 `verify.ps1`) (작업 보고 전 필수)

- **단일 진입**: 저장소 루트에서 `.\verify.bat` 또는 `powershell -NoProfile -ExecutionPolicy Bypass -File .\verify.ps1` 를 실행합니다. ({{VERIFY_SCRIPT_STEPS_SUMMARY}})
- **산출물(저토큰 읽기)**:
  - 항상 생성: **`verify-last-result.json`** — `exitCode`, `failedStep`, `steps[]`, `pytestFailedTests`(실패 시), `agentHint`
  - pytest 실패 시 추가: **`verify-pytest-failures.txt`** — 마지막 구간의 요약(전체 로그 대신 이 파일만 읽을 것)
- **`agentHint`와 한글 안내의 분리**: JSON의 `agentHint`는 **영문만** 둡니다. **절차·주의사항의 한글 설명은 본 절(4.0)과 `AGENTS.md`에만** 둡니다.
- **에이전트 필수 절차(Read 우선)**: 보고용으로 검증 맥락을 가져올 때 **반드시 Read 도구로 `verify-last-result.json`을 읽고**, pytest 실패 시에만 필요한 만큼 **`verify-pytest-failures.txt`를 Read**합니다. **전체 로그를 채팅에 붙이지 않습니다.**
- **에이전트/리뷰어 규칙(요약)**: 위 두 파일의 내용 또는 JSON의 `pytestFailedTests`만 사용자 응답에 인용합니다.
- **수동 분할 실행**: `verify`를 돌릴 수 없는 환경일 때만 아래 4.1·4.2절의 명령을 동일 순서로 대체합니다.

### 4.1 Frontend 변경 시 (`{{FRONTEND_ROOT}}/`)

- **정적/타입 검증**:
  - `{{FE_LINT_CMD}}`
  - `{{FE_TSC_CMD}}`
- **빌드 검증**: `{{FE_BUILD_CMD}}`
- **E2E(변경 영향 있을 때)**: `{{FE_E2E_CMD}}`
- **스모크 검증**: 변경된 페이지 1회 이상 진입 + 핵심 위젯 1회 상호작용 확인

### 4.2 Backend 변경 시 (`{{BACKEND_ROOT}}/`)

- **정적 검증(최소선)**:
  - `{{BE_COMPILE_CMD}}`
- **테스트 검증**:
  - `{{BE_TEST_CMD}}`
  - (범위 축소가 필요하면) 영향 파일/기능에 대응하는 `tests/` 선택 실행
- **로컬 구동 스모크(권장)**:
  - 통합: `{{BE_OR_FULLSTACK_DEV_CMD}}`
  - 개별(예): `{{BE_SINGLE_PROCESS_CMD}}`

### 4.3 문서 및 추적성 업데이트

- **명세 선반영 원칙**: 신규 기능/규칙 변경은 `docs/specs/`를 먼저 갱신하고 구현합니다.
- **의사결정 기록**: 설계 판단이 발생하면 `docs/CRITICAL_LOGIC.md`에 단계(대안/채택 이유 포함)를 명시하여 기록합니다.
- **세션 기록**: 작업 종료 시 `docs/memory/MEMORY.md`는 **링크(인덱스)만 갱신**하고, 상세는 `docs/memory/` 하위 문서에서 업데이트합니다. `MEMORY.md`가 {{MEMORY_INDEX_MAX_LINES}}라인/25KB 초과 시 50라인 이내로 즉시 요약하고 세부 내용을 분산합니다.
- **자기 최적화(Self-Optimization)**: 에이전트는 `CRITICAL_LOGIC.md` 및 메모리 파일의 반복 패턴을 상시 분석하여, 3회 이상 중복되는 작업은 신규 워크플로우(`.md`) 생성을 제안합니다.

### 4.4 완료 보고 템플릿 (응답 직전 체크)

응답에는 아래 형식의 **Verify Report**를 포함합니다.

- `통합 검증`: `verify.ps1` **exitCode** + `verify-last-result.json`의 `failedStep`(있으면) + (실패 시) `pytestFailedTests` 또는 `verify-pytest-failures.txt` 요약 **한 블록 이내**
- `변경 파일`: 경로 목록
- `정적 검증`: 실행 명령 + 결과(성공/실패) — 통합 검증과 중복되면 “4.0과 동일”으로 한 줄 처리 가능
- `테스트`: 실행 범위 + 결과
- `스모크 검증`: 시나리오 + 결과
- `리스크/후속`: 잔여 리스크, **검증 실패 시 수정 계획 또는 다음 세션에서 할 일**(원인·파일·테스트명을 구체적으로)

### 4.6 사전 검증(Pre-Guard) — 코드 작성 전 필수 확인

코드 수정·신규 작성 전, 아래 패턴에 대해 **"이 코드가 verify에서 깨질 가능성이 있는가?"** 를 먼저 자가격리하고, 해당 가능성이 있다면 **원천 차단하는 방식**으로 설계합니다.

#### 4.6.1 라우팅 순서 가드
- **정적 경로 우선**: 고정 세그먼트는 동적 매칭보다 **반드시 먼저 선언**합니다.
- **라우터 내부 스캔**: 라우터를 수정할 때 선언 순서가 깨지지 않았는지 `grep` 등으로 확인합니다.

#### 4.6.2 레이어 경계 가드 (Domain vs Infrastructure)
- **도메인 계층**: DB 모델(ORM), HTTP 클라이언트, 특정 인프라 의존성(Redis/Vault 등)을 배제합니다.
- **인프라 계층**: 비즈니스 규칙 판단이나 상태 머신 전이 결정을 배제합니다.

#### 4.6.3 TypeScript strict 모드 가드
- **Nullable 처리**: 백엔드 응답은 항상 nullable로 간주하고 타입 가드를 적용합니다.
- **성공/실패 명시**: API 인터페이스 정의 시 에러 케이스를 포함합니다.

#### 4.6.4 문서 인코딩 가드
- **전용 도구 사용**: `write_file` 등을 사용하여 UTF-8 인코딩을 유지합니다. 셸 파이프라인 사용을 엄격히 금지합니다.

#### 4.6.5 테스트 격리 가드
- **상태 공유 금지**: 각 테스트는 독립적인 fixture를 사용하며 순서에 의존하지 않습니다.
- **DB 격리**: 테스트용 DB와 개발 DB가 파일 경로/인스턴스 면에서 분리되었는지 확인합니다.

#### 4.6.6 추적성 가드
- **지표 명시**: 핵심 로직 및 테스트에 인증 지표/요구사항 번호를 주석으로 남깁니다.

### 5. {{TROUBLESHOOTING_SECTION_TITLE}} 트러블슈팅 가이드

{{TROUBLESHOOTING_CONTEXT}} 등을 보고할 때 아래 절차를 따른다.

| 오류 메시지 | 발생 지점 | 의미 |
|------------|----------|------|
| {{ERROR_MSG_1}} | {{ERROR_LOC_1}} | {{ERROR_MEANING_1}} |
| {{ERROR_MSG_2}} | {{ERROR_LOC_2}} | {{ERROR_MEANING_2}} |

#### 해결 절차 (예시)
1. **Step 1 — 서버 상태 확인**: `{{HEALTH_CHECK_CMD}}`
2. **Step 2 — 데이터 상태 확인**: `{{DB_CHECK_CMD}}`
3. **Step 3 — 복구 실행**: `{{RECOVERY_CMD}}`

### 4.5 글로벌 워크플로우 동기화 (Rule Change 시 필수)

`PROJECT_RULES.md` 또는 `AGENTS.md` 등 프로젝트 핵심 규칙이 변경된 경우, 아래 글로벌 워크플로우를 즉시 검토하여 최신 규칙에 맞게 일괄 업데이트합니다.

- **대상 워크플로우**(`.agents/workflows/` 또는 글로벌 경로):
  - `/plan`: 설계 및 원자적 분해
  - `/go`: 세션 이관 프로토콜
  - `/git`: 커밋 및 SSOT 동기화
  - `/audit`: 심사 평가 리포트 생성
  - `/evidence`: 지표 증적 생성
- **동기화 체크리스트**:
  - [ ] 최신 `verify.sh` 프로토콜 반영
  - [ ] `MEMORY.md`의 {{MEMORY_INDEX_MAX_LINES}}라인 제약 및 인덱스 전용 원칙 준수
  - [ ] 신규 문서 생성 시 `DOC_SSOT_HEADER_TEMPLATE.md` 적용 여부
  - [ ] 자기 최적화(Self-Optimization) 분석 단계 포함 여부
