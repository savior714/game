# CRITICAL_LOGIC.md — Bootstrap DevEnv 규칙 SSOT

> 이 파일은 bootstrap_repo의 모든 설계 결정과 규칙의 유일한 기준(Single Source of Truth)입니다.

---

## 1. 실행 환경 표준

| 항목       | 결정                                              | 이유                                                                        |
| ---------- | ------------------------------------------------- | --------------------------------------------------------------------------- |
| 런처       | `bootstrap.bat` 우클릭 → **관리자 권한으로 실행** | 스크립트 내 admin self-elevation 시 원본 창이 닫히는 현상 방지              |
| PS1 인코딩 | **UTF-8 no BOM**                                  | Windows PowerShell 5.1 및 7.x 간의 교차 호환성 및 현대적 파싱 도구와의 정렬 |
| bat 인코딩 | **ANSI (CP949)**                                  | Windows cmd 호환성 유지                                                     |

---

## 2. 패키지 그룹 구성 (현행)

| #   | 항목                                                    | 기본 선택 |
| --- | ------------------------------------------------------- | :-------: |
| 1   | Core — Git, Python 3.14, Node.js LTS, Rust (rustup), uv |    ✅     |
| 2   | VS Build Tools 2022 (MSVC + Windows SDK 26100)          |    ✅     |
| 3   | Windows Terminal                                        |    ✅     |
| 4   | Go                                                      |    ⬜     |
| 5   | Java (Temurin JDK 17 LTS)                               |    ⬜     |
| 6   | Android Studio                                          |    ⬜     |
| 7   | Docker Desktop                                          |    ⬜     |

**제거된 항목:**


- ~~PowerShell 7 (pwsh)~~ — PS7 미사용 환경이므로 제거 (그룹 #2였음)

---

## 3. 설계 결정 사항

### Admin 자동 승격 구조

- `Bootstrap-DevEnv.ps1` 실행 시 admin 아닐 경우 `Start-Process powershell -Verb RunAs`로 재실행 후 `exit 0`
- 이로 인해 **원본 bat 창이 닫히고 UAC 창 + 새 창이 열리는 것은 정상 동작**
- 해결책: bat 파일을 처음부터 관리자 권한으로 실행

### 메뉴 UI

- `$Host.UI.RawUI.ReadKey` 기반 인터랙티브 메뉴
- 숫자 키로 토글, `A`/`N`으로 전체 선택/해제, `Enter`로 설치 시작
- 그룹별 설명(Desc) 라인은 불필요하여 제거됨

### Post-install 자동화

`Add-ToUserPath` 헬퍼 함수: 경로 존재 확인 후 User PATH 중복 없이 등록, 현재 세션 즉시 반영

| 항목        | 자동화 내용                                                                                                                                                                         |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Rust**    | rustup stable toolchain 설치 및 default 설정                                                                                                                                        |
| **Java**    | `JAVA_HOME` 설정 (`$Script:JAVA_INSTALL_BASE\$Script:JAVA_VERSION_GLOB`) + `\bin` PATH 자동 추가. 경로 상수는 `config/paths.ps1` 참조. `JAVA_INSTALL_BASE` 환경 변수로 재정의 가능. |
| **Android** | `ANDROID_HOME` 설정 (`$Script:ANDROID_SDK_BASE`) + `platform-tools`, `emulator` PATH 자동 추가. 경로 상수는 `config/paths.ps1` 참조.                                                |

---

## 5. 환경 무결성 검증 엔진 (Integrity Engine)

개발 환경의 일관성을 유지하고 "Ghost Bug"를 방지하기 위한 검증 시스템입니다.

| 항목            | 상세 내용                                                                                      |
| --------------- | ---------------------------------------------------------------------------------------------- |
| **아키텍처**    | `scripts/check-env.ps1` (Main) + `scripts/lib/env-core.ps1` (Lib) 구조로 분리 (300L Rule 준수) |
| **Core CLI**    | Node.js, Git, npm, pnpm, yarn의 설치 및 가용성 확인                                            |
| **Config**      | `.npmrc` (Registry), `.gitconfig` (User Info, autocrlf) 무결성 확인                            |
| **File System** | 주요 파일의 인코딩(UTF-8 no BOM/with BOM, ANSI)을 `Test-FileEncoding` 함수로 정밀 검증         |
| **Hash Sync**   | `AI_GUIDELINES.md`와 `templates` 간 **MD5 Hash 비교**를 통해 내용의 비동기화 차단              |
| **IDE Sync**    | VSCode `settings.json`의 필수 항목(encoding, tabSize) 일관성 확인                              |
| **Tech Stack**  | `tsc`, `eslint`, `prettier` 바이너리 가용성 및 버전 조회를 통한 런타임 환경 검증               |
| **Shared Lint** | `shared_lint_rules.json`과 `eslint.config.js` 간의 정책 일치 여부 강제                         |

### 검증 결과 보고

- `scripts/check-env.ps1` 실행 시 `env_report.json` 생성
- IDE와의 연동을 위해 표준 JSON 스키마를 따름
- 위반 사항 발견 시 구체적인 복구 제안 제공

---

## 6. 전역 규칙 관리 표준 (AI & Quality)

프로젝트 간 개발 경험을 통일하고 동일한 에러의 재발을 방지하기 위한 전역 관리 시스템입니다.

### 행동 및 품질 규칙 구성

1. **AI 행동 지침 (Behavioral)**: `./AI_GUIDELINES.md` (Master), `templates/AI_GUIDELINES.md` (Deploy)
   - **Senior Architect Deep-Dive Version** (v2.0) 수립. AI가 코드를 작성하거나 디버깅할 때 반드시 준수해야 하는 행동 원칙.
   - **TPG Protocol v2.0**, **Stale Context Invalidation**, **SQL Idempotency**, **Surgical Edits** 등 고도화된 프로토콜 포함.
2. **사용자 제약 규칙 (Runtime Constraints)**: `./.antigravityrules`
   - 에이전트의 물리적 활동 범위를 제한하는 런타임 제약 조건 파일.
   - 행동 지침은 `AI_GUIDELINES.md`를 SSOT로 참조하며, 이 파일은 오직 물리적 차단 경로와 원자적 실행 수칙만을 정의함.

3. **기술 린트 정책 (Technical)**: `shared_lint_rules.json`
   - ESLint 등 도구가 프로젝트 소스 코드를 기계적으로 검증하는 규칙 모음.
   - 플랫폼 호환성 및 인코딩 사고 방지를 위한 엄격한 규칙 적용.

### 타 프로젝트 이식 및 참조 프로세스 (Portability)

- **온보딩**: 신규 프로젝트 이식 시 AI는 `AI_GUIDELINES.md` Section 11의 **Onboarding Checklist**를 즉시 실행하여 환경을 자발적으로 파악합니다.
- **배포**: `bootstrap.bat` 또는 동기화 도구에서 `templates/AI_GUIDELINES.md`를 타겟 프로젝트 루트로 복사합니다.
- **검증**: `scripts/check-env.ps1`의 Hash 비교 로직을 통해 로컬 지침이 마스터와 일치하는지 상시 확인합니다.
- **동기화**: 마스터 규범 업데이트 시 `templates/` 하위 파일도 동기화하며, 불일치 시 `check-env.ps1`이 자동으로 `Copy-Item` 기반의 Self-Healing을 제안합니다.

---

## 7. 별도 설치 도구 (스크립트 외)

- Antigravity IDE
- VS Code / Cursor AI
- Supabase CLI (Manual: `npm install -g supabase`)

---

## 8. Terminal Interaction Protocol

Antigravity 에이전트와 터미널 간의 안정적인 상호작용을 위한 프로토콜입니다.

| 항목                       | 내용                                                                                                               |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **세션 초기화 (SSOT)**     | `scripts/init-terminal.ps1`을 통한 UTF-8 인코딩 고정, `$ProgressPreference` 억제, 텔레메트리 차단 및 NO_COLOR 강제 |
| **NoProfile Mode**         | 모든 에이전트 내부 PowerShell 호출 시 `-NoProfile` 스위치를 사용하여 로컬 프로필 간섭 배제                         |
| **Loop Prevention**        | `.antigravityrules`를 통해 `node_modules`, `.git`, `dist` 등 대용량 경로에 대한 물리적 스캔을 원천 차단              |
| **Atomic Execution**       | 1 Task = 1 Tool Call 원칙을 고수하며, 각 작업 후 사용자 승인을 대기하여 실행 경로의 투명성 확보                    |
| **Shell Integration 차단** | 터미널 시퀀스(`\e]633;...`) 노이즈가 파싱을 방해하는 경우 환경 변수나 초기화 코드로 이를 명시적으로 억제           |
| **Syntax Check**           | `.ps1` 파일 수정 후 실행 전 `[System.Management.Automation.Language.Parser]::ParseInput()`을 이용한 정밀 구문 검증 |
| **Safe Execution**         | 100자 이상의 복잡한 명령이나 중첩 따옴표 포함 시 반드시 `.ps1` 임시 파일로 변환하여 실행                           |
| **Traffic Zero**           | 모든 CLI 도구에 `--quiet` 플래그를 강제하고, `Select-Object` 등을 통해 터미널 출력량을 물리적으로 제한             |
| **Get-Command Check**      | 외부 도구(`npm`, `git` 등) 호출 전 `Get-Command`로 가용성을 사전 확인하여 런타임 예외 방지                 |
| **Chaining Prohibition**  | 입출력 버퍼 오염 방지를 위해 한 번의 Tool Call에서 `;`, `&&` 등 명령어 체이닝 금지                            |
| **Strict Type Guarding**  | `unknown`, `any` 타입 변수 비교 전 `typeof`로 타입을 확정하여 **TS2365** 에러 사전 방지                      |
| **Pure Presenter**        | 비즈니스 로직과 UI/출력 렌더링을 엄격히 분리하여 로직 코드의 재사용성 및 무결성 확보                          |
| **Self-Verification**     | 주요 변경 전후로 `tsc --noEmit` 또는 `check-env.ps1`을 통한 시스템 무결성 자가 검증 수행                   |
| **Terminal Recovery**      | 파싱 불가 시 `TERMINAL_RECOVERY_MARKER` 구분자를 사용해 데이터 추출을 시도하며, 필요시 복구 SOP 가동      |
| **Native Command Guard**  | `$LASTEXITCODE` 기반의 실행 결과 신뢰 및 `NativeCommandError` 예외 처리 로직 준수                      |
| **Path Resilience**       | `Test-Path` 실패 시 `Get-ChildItem -Recurse` 자동 전환 및 `-LiteralPath` 사용으로 경로 해석 오류 방지  |
| **Atomic Provisioning**   | `New-Item` 등 자원 생성 시 `-Force` 플래그를 필수 사용하여 덮어쓰기 및 중복 생성 부작용 차단           |
| **SQL Idempotency**      | 모든 DB DDL/DML에 `IF NOT EXISTS` 및 `DO` 블록 사용을 강제하여 실행 안전성 확보                    |
| **Error RCA Protocol**   | 에러 발생 시 현상-원인-해결 3단계 분석 및 검증 커맨드 실행 의무화                                  |
| **Standardized Schema**  | 에러 응답 시 `Code`, `Message`, `Path` 필드를 포함한 표준 객체 응답 준수                           |

### 기술적 사양 (Technical Specification)

- **Encoding**: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
- **Session Init**: `$env:TERM = 'dumb'`, `$env:NO_COLOR = '1'`, `$env:POWERSHELL_TELEMETRY_OPTOUT = '1'`
- **AST Parser Logic**: 
  ```powershell
  $Errors = $null; [System.Management.Automation.Language.Parser]::ParseInput((Get-Content "file.ps1" -Raw), [ref]$null, [ref]$Errors)
  ```
- **Performance**: `$ProgressPreference = 'SilentlyContinue'`를 통해 진행 바 출력을 억제하여 파싱 렉 방지
- **NoProfile**: 모든 에이전트 명령은 `powershell -NoProfile -Command "..."` 형식을 SSOT 표준으로 함

---

## 9. Zero-Config Automation

사용자의 수동 개입 없이 `bootstrap.bat` 실행만으로 모든 환경을 전역 최적화하는 매커니즘입니다.

| 항목                     | 구현 내용                                                                                                  |
| ------------------------ | ---------------------------------------------------------------------------------------------------------- |
| **전역 경로 등록**      | `ANTIGRAVITY_BOOTSTRAP_PATH` 시스템 환경 변수를 현재 레포지토리 경로로 등록                                |
| **터미널 영구 안정화**  | 사용자 `$PROFILE`에 `init-terminal.ps1` 호출 코드를 자동 주입하여 모든 터미널 세션의 인코딩을 UTF-8로 고정 |
| **전역 도구 표준화**    | `git config --global core.autocrlf false`, `init.defaultBranch main` 등의 설정을 강제 적용                 |
| **Git 식별자 설정**     | `user.name`, `user.email`을 설치 후 단계에서 **대화형(Interactive)**으로 입력 및 확인                     |
| **무설정 에이전트 지침** | 에이전트가 `ANTIGRAVITY_BOOTSTRAP_PATH`를 감지하면 자동으로 해당 경로의 전역 지침을 로드하도록 설계        |

---

## 10. Encoding Standard & File Rules

범용적인 호환성과 인코딩 충돌을 방지하기 위한 소스 코드 및 설정 파일 관리 표준입니다.

| 규칙                  | 상세 내용                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Standard Encoding** | 모든 소스 코드(`.ps1`, `.js`, `.json`, `.md`)는 **UTF-8 no BOM**으로 통일함                                              |
| **No BOM Guarantee**  | PowerShell `Out-File` 또는 `Set-Content` 대신 `[System.IO.File]::WriteAllText()`를 사용하여 BOM 없는 UTF-8 저장을 보장함 |
| **Exception**         | `.bat` 파일은 `ANSI (CP949)`를 유지하여 CMD 호환성을 확보함                                                              |
| **IDE Enforcement**   | VSCode `settings.json`에 `files.encoding: "utf8"`, `files.autoGuessEncoding: false`를 강제하여 사용자 실수 방지          |
| **Integrity Check**   | `check-env.ps1`에서 `Test-FileEncoding` 함수를 통해 전수 조사를 수행하며, 위반 시 린트 에러로 간주함                     |
| **Boolean Syntax**    | PowerShell 조건문/할당 시 `$true`, `$false` 필수 사용 (프리픽스 없는 `True` 사용 엄금)                             |
| **Safe Raw IO**       | .NET IO 메소드 사용 시 `Test-Path` 선행 및 배열 인덱싱 전 Null 체크 필수 (`Null Safety`)                          |

### 파일 쓰기 권장 패턴 (PowerShell)

```powershell
# BOM 없는 UTF-8 파일 쓰기 표준 로직
$utf8NoBomEncoding = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($targetPath, $content, $utf8NoBomEncoding)
```
