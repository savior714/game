# 🛡️ AI Command Protocol — Zero-Error Terminal Guide

> **용도**: AI 에이전트(Antigravity, Cursor, Claude Code 등)가 PowerShell/Node.js 명령어를 실행할 때 반복 발생하는 오류를 원천 차단하기 위한 실증 기반 참조 문서.
> **적응 범위**: 이 파일을 프로젝트의 `docs/` 폴더에 두면 AI가 온보딩 시 자동으로 읽어 동일한 안전망이 작동합니다.

---

## 0. [CRITICAL] Tool-First & Zero-Shell Discovery & Navigation (전면 금지)

파일 탐색, 검색, 목록 조회 및 **경로 이동** 시 OS 쉘 명령어의 **사용을 전면 금지**합니다. 에이전트는 반드시 **IDE 전용 구조화 도구**만을 사용해야 합니다.

> **금지 근거**: 쉘 출력물은 비정형 텍스트로 Context Window를 오염시키고(Context Hygiene), 환경별로 결과가 달라지며(Determinism), 경로 오파싱으로 인한 치명적 Side Effect(오삭제, 오수정)를 유발합니다(Type-Safety). 특히 `cd`를 통한 상태 변경은 작업 환경의 불확실성을 가중시킵니다.

| 작업 유형           | 쉘 명령어 (**전면 금지**)                  | Claude Code         | Cursor / Antigravity                        | 설계 전략 (SSOT)                       |
| ------------------- | ------------------------------------------ | ------------------- | ------------------------------------------- | -------------------------------------- |
| 파일/폴더 검색      | `dir /s`, `find`, `Get-ChildItem -Recurse` | **`Glob`**          | **`find_by_name`**                          | **데이터 인지**(Data Perception)       |
| 파일 내 텍스트 검색 | `grep`, `Select-String`, `dir /s \| grep`  | **`Grep`**          | **`grep_search`**                           | **컨텍스트 위생**(Context Hygiene)     |
| 폴더 목록 조회      | `ls`, `dir`                                | **`Glob`**          | **`list_dir`**                              | **결정론 보장**(Determinism)           |
| 파일 내용 읽기      | `cat`, `type`, `Get-Content`               | **`Read`**          | **`view_file`**                             | **토큰 효율성**(Token Efficiency)      |
| 파일 생성/수정      | `Set-Content`, `echo >`, `Add-Content`     | **`Write`, `Edit`** | **`write_to_file`, `replace_file_content`** | **부수 효과 차단**(No Side Effects)    |
| **경로 이동**       | **`cd`, `Set-Location`, `pushd`, `popd`**  | **`run` (`Cwd`)**   | **`run_command` (`Cwd`)**                   | **환경 물리 격리**(Physical Isolation) |

> **예외**: 프로젝트 빌드(`npm run`), 타입 체크(`tsc`), 패키지 관리(`npm install`) 등 **전용 도구가 물리적으로 존재하지 않는 경우**에만 Section 1~7의 안전 수칙을 준수하여 PowerShell을 사용합니다. 이 경우에도 **실행 위치는 도구의 `Cwd` 매개변수로 지정**하며, `ls`/`dir` 등 **탐색형 명령어는 절대 혼용 금지**합니다.

---

## 1. File Guard — `cd`는 폴더 전용

### 증상

```
cd '...memory.md' 경로는 존재하지 않으므로 찾을 수 없습니다.
```

### 원인

`Set-Location` (`cd`)은 **디렉토리 전용** 명령어입니다. 파일 경로를 전달하면 PowerShell이 해당 이름의 폴더를 찾으려다 실패합니다.

### 올바른 명령

```powershell
# ❌ 잘못된 예시
cd 'c:\develop\project\docs\memory.md'

# ✅ 파일 내용 읽기
Get-Content -LiteralPath 'c:\develop\project\docs\memory.md' -TotalCount 50

# ✅ 파일이 있는 폴더로 이동
Set-Location 'c:\develop\project\docs'
```

---

## 2. Pipeline Guard — `Join-Path` 파이프 금지

### 증상

```
입력을 매개 변수에 바인딩할 수 없습니다. 매개 변수 "Path" 값 "..."을(를) "System.String" 형식으로 변환할 수 없습니다.
```

### 원인

`Join-Path`의 출력은 파이프라인으로 전달할 때 `Get-Content`가 어느 매개변수(`-Path` vs `-LiteralPath`)에 바인딩할지 결정하지 못하거나, 타입 변환에 실패합니다.

### 올바른 명령

```powershell
# ❌ 잘못된 예시
Join-Path "docs" "memory.md" | Get-Content

# ✅ 괄호(서브 익스프레션)로 실행 순서 명시
Get-Content (Join-Path "docs" "memory.md") -TotalCount 30

# ✅ 변수를 통한 명시적 분리 (가독성 우선)
$path = Join-Path $PSScriptRoot "docs" "memory.md"
Get-Content -LiteralPath $path -TotalCount 30
```

---

## 3. CLI Arg Guard — `next lint` 인자 오해석

### 증상

```
Invalid project directory provided, no such directory: C: \...\frontend\lint
```

### 원인

1. `npm run lint` 실행 시 `lint`라는 추가 인자가 전달됨 (예: `npm run lint lint`).
2. 또는 루트에 `package.json`이 없는 상태에서 쉘이 명령어 자체를 인자로 오인함.
3. **가장 빈번한 사례**: 에이전트가 `cd frontend; npm run lint`와 같이 쉘 명령어를 조합하여 실행하면서, 인자 파싱 과정에서 `lint`가 중복 전달됨.

### 올바른 명령

```json
// Antigravity run_command 호출 예시
{
  "CommandLine": "npm run lint",
  "Cwd": "c:\\develop\\eco_pediatrics\\frontend"
}
```

> **핵심**: `Set-Location`이나 `cd`를 절대 사용하지 마십시오. IDE 도구의 **`Cwd` 매개변수**를 사용하여 작업 디렉토리를 물리적으로 고정하는 것이 유일하고 안전한 해결책입니다.

> **실증 사례**: `Cwd`를 지정했음에도 `next lint`가 `\lint` 경로를 찾는 오류는 에이전트가 내부적으로 `npm run lint`에 실행 문맥상의 키워드를 인자로 중복 전달하거나, 쉘 환경 변수 오염으로 인해 발생할 수 있습니다. 이 경우 `npm run lint` 대신 `npx next lint`와 같이 바이너리를 직접 호출하거나, 환경 변수를 초기화하는 `npm run lint` (예: PowerShell에서 `$env:NODE_DEBUG=""; npm run lint`) 방식을 고려하십시오.

> **추천**: 서브패키지의 `package.json`에 `lint`, `type-check` 스크립트를 명시하여 루트에서 인자를 전달할 필요를 없애는 것이 가장 안전합니다.

---

## 4. npx Guard — 로컬 미설치 패키지 실행 차단

### 증상

```
This is not the tsc command you are looking for
```

### 원인

`npx`는 로컬 `node_modules`에 해당 패키지가 없을 경우 보안상 실행을 차단합니다. 즉, 현재 프로젝트에 `typescript`가 설치되어 있지 않은 상태입니다.

### 올바른 명령

```powershell
# ❌ 잘못된 예시 (로컬에 typescript 없으면 차단)
npx tsc --noEmit

# ✅ 패키지명을 명시하여 강제 실행
npx -p typescript tsc --noEmit

# ✅ package.json에 type-check 스크립트 정의 (근본 해결)
# "scripts": { "type-check": "tsc --noEmit" }
# 이후: npm run type-check

# ✅ 특정 tsconfig를 명시하는 경우
npx -p typescript tsc --noEmit --project frontend/tsconfig.json
```

---

## 5. File I/O Guard — 프로필 보안 정책에 의해 차단된 Cmdlet

### 증상

```
[Security] Add-Content 사용이 금지되었습니다. [System.IO.File]::AppendAllText를 사용하십시오.
```

### 원인

PowerShell `$PROFILE`에 `Add-Content`, `Set-Content`, `Out-File`에 대한 **보안 훅(Hook)**이 설정되어 있습니다.
이 cmdlet들은 호출 즉시 `RuntimeException`을 throw하고 작업이 중단됩니다.

### 올바른 명령

```powershell
# ❌ 잘못된 예시 (프로필 보안에 의해 차단됨)
Add-Content -Path 'docs\memory.md' -Value "`n새 로그 항목"
Set-Content -Path 'docs\memory.md' -Value $content
$output | Out-File -FilePath 'docs\memory.md'

# ✅ 파일 끝에 내용 추가 (Add-Content 대체)
[System.IO.File]::AppendAllText(
    'c:\develop\project\docs\memory.md',
    "`n새 로그 항목",
    [System.Text.Encoding]::UTF8
)

# ✅ 파일 전체 덮어쓰기 (Set-Content / Out-File 대체)
[System.IO.File]::WriteAllText(
    'c:\develop\project\docs\memory.md',
    $content,
    [System.Text.Encoding]::UTF8
)
```

> **주의**: 경로는 반드시 **절대 경로** 문자열로 전달해야 합니다. `$PSScriptRoot` 또는 `Join-Path`로 조합한 뒤 변수로 전달하세요.

```powershell
# ✅ 경로 조합 후 변수 사용 (권장 패턴)
$memoryPath = Join-Path 'c:\develop\project' 'docs\memory.md'
[System.IO.File]::AppendAllText($memoryPath, "`n로그 내용", [System.Text.Encoding]::UTF8)
```

---

## 6. CMD vs PowerShell Guard — `dir /s /b` 및 슬래시 기반 옵션 금지

### 증상

```powershell
dir /s /b src\lib\api.ts
# Get-ChildItem : 'src\lib\api.ts' 인수를 허용하는 위치 매개 변수를 찾을 수 없습니다.
# CategoryInfo : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
# FullyQualifiedErrorId : PositionalParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand
```

### 원인

PowerShell에서 `dir`, `ls`는 **CMD**나 **Bash**의 명령어가 아닌 `Get-ChildItem`의 **별칭(Alias)**입니다.

- **CMD 스타일**의 `/s`, `/b`, `/ad` 등 **슬래시(/) 기반 스위치**를 전혀 인식하지 못합니다.
- PowerShell은 하이픈(`-`) 기반의 명명된 매개변수(`-Recurse`, `-Filter`)를 사용해야 합니다.
- 인식할 수 없는 옵션이 들어오면 이를 위치 매개변수(Positional Parameter)로 오해하여 오류를 발생시킵니다.

### 올바른 명령

```powershell
# ❌ 잘못된 예시 (CMD/DOS 스타일)
dir /s /b src\lib\api.ts
ls -R | grep api.ts (PowerShell에서는 작동 방식이 다름)

# ✅ PowerShell 표준: 파일 검색 및 전체 경로 출력
(Get-ChildItem -Path "src" -Filter "api.ts" -Recurse).FullName

# ✅ PowerShell 표준: 디렉토리만 리스팅 (dir /ad 대체)
Get-ChildItem -Directory

# ✅ PowerShell 표준: 숨김 파일 포함 (dir /ah 대체)
Get-ChildItem -Force

# ✅ 최우선 권장: 전용 도구 활용
# Antigravity 환경에서는 find_by_name 또는 grep_search 도구를 사용하면 PowerShell 구문 오류를 완벽히 피할 수 있습니다.
```

---

## 7. Metric Guard — 물리적 라인 수 자가 검증

### 증상

"300라인 안 넘어요"라고 말했는데 실제로는 넘어서 룰 위반이 발생하는 경우.

### 원인

에이전트의 내부 토큰 계산과 물리적 파일의 Newline(`\n`) 계산 방식 차이로 인한 오차.

### 올바른 명령

```powershell
# ✅ 특정 파일의 라인 수 확인 (표준)
(Get-Content -LiteralPath 'docs\memory.md').Count

# ✅ 특정 파일이 300라인을 넘었는지 즉시 판별
$count = (Get-Content -LiteralPath 'src\lib\api.ts').Count; if ($count -gt 300) { Write-Host "REFAC REQUIRED: $count lines" }
```

---

## 요약 대조표

| #   | 오류 유형                                                                                                                            | 핵심 원인          | 즉각 해결책                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ----------------------------- |
| 1   | **파일에 `cd`**                                                                                                                      | `cd`는 폴더 전용   | `Get-Content -LiteralPath`    |
| 2   | **파이프라인 바인딩**                                                                                                                | 타입/바인딩 불일치 | `Get-Content (Join-Path ...)` |
| 3   | **`next- **Status\*\*: SSOT 반영 및 검증 완료. 린트 환경 이슈는 `Cwd` 준수에도 불구하고 발생할 수 있음을 확인하고 대응 지침 보강. ✅ |

- **결과**: `npm test`를 통한 로직 무결성 확인 및 린트 지침 고도화 완료.
  |
  | 4 | **`npx` 차단** | 로컬 패키지 미설치 | `npx -p typescript tsc` |
  | 5 | **`Add-Content` 차단** | 프로필 보안 정책 | `[System.IO.File]::AppendAllText()` |
  | 6 | **`dir /s /b`** | PowerShell에서 CMD 옵션 사용 | `Get-ChildItem -Recurse` |
  | 7 | **라인 수 오판** | 수동 계산 오류 | `(Get-Content <file>).Count` |

---

## 8. TypeScript Type Check Guard — Error-Only Context 패턴

> 상세 전략: [`docs/TS_TYPE_VALIDATION.md`](TS_TYPE_VALIDATION.md)

### 증상

```
LLM이 타입 에러를 고치는 데 토큰을 과도하게 소비하거나,
전체 파일을 다시 제출해도 동일한 에러가 반복 발생하는 경우.
```

### 원인

- 전체 `.ts` 파일을 LLM 컨텍스트에 주입하여 불필요한 구현부까지 분석하게 함
- `tsc` 없이 LLM에게 "이 코드 타입 맞아?"라고 질문 (LLM을 컴파일러로 오용)
- 에러 없는 파일까지 컨텍스트에 포함

### 올바른 명령 — Error-Only 슬라이싱

```powershell
# ✅ 에러 라인만 추출하여 LLM에 전달 (PowerShell)
powershell -NoProfile -Command "npx -p typescript tsc --noEmit 2>&1 | Select-String 'error TS' | Select-Object -First 20"

# ✅ 에러 수 카운트만 확인 (빠른 검증)
powershell -NoProfile -Command "(npx -p typescript tsc --noEmit 2>&1 | Select-String 'error TS').Count"

# ✅ 특정 파일만 타입 체크
powershell -NoProfile -Command "npx -p typescript tsc --noEmit --isolatedModules src/lib/api.ts 2>&1 | Select-String 'error TS'"

# ✅ Antigravity run_command 호출 예시
# {
#   "CommandLine": "powershell -NoProfile -Command \"npx -p typescript tsc --noEmit 2>&1 | Select-String 'error TS' | Select-Object -First 20\"",
#   "Cwd": "c:\\your-project"
# }
```

### 에러 코드별 최소 컨텍스트 전략

| 에러 코드 | 에러 명 | LLM에 전달할 최소 컨텍스트 |
| :--- | :--- | :--- |
| `TS2345` | Argument type mismatch | 함수 시그니처 + 호출 라인만 |
| `TS2339` | Property does not exist | 타입 정의 + 접근 라인만 |
| `TS2322` | Type not assignable | 할당 라인 + 양측 타입 정의 |
| `TS7006` | Implicit any | 파라미터 라인만 |
| `TS2365` | Operator not applicable | 비교 연산 라인 + typeof 확인 |

### 자동화 스크립트 활용

```powershell
# scripts/type-check-slice.ps1 — Error-Only Context 추출기
# 사용법: powershell -NoProfile -File scripts/type-check-slice.ps1 -ProjectPath "c:\your-project"
```

---

## 프로젝트 레벨 예방 설정

새 프로젝트에서 위 오류를 **구조적으로 예방**하려면 아래 설정을 심어두세요.

### `package.json` (서브패키지 기준)

```json
{
  "scripts": {
    "lint": "next lint",
    "type-check": "tsc --noEmit",
    "validate": "npm run lint && npm run type-check"
  }
}
```

### `.npmrc` (루트)

```ini
# 버전 고정 및 로컬 우선 실행
save-exact=true
prefer-offline=true
```

---

> **참조 문서**: [AI_GUIDELINES.md](../AI_GUIDELINES.md) 섹션 2 (TPG Protocol) / [.antigravityrules](../.antigravityrules) 섹션 3
