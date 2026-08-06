---
scope: detail
domain: core
parent: .agents/core/error_patterns.md
lazy_load: true
---
<!-- Language: ko -->

> **역할**: WRONG/CORRECT 예시 전용. 규범은 [runtime_edit_tools.md](../../runtime_edit_tools.md) · Cursor 상세 [routing.md](../../routing.md) §1 — 본문에 재서술하지 않는다.
> **도구**: 세션 호스트 읽기·부분 수정·쓰기 ([runtime_edit_tools.md §1](../../runtime_edit_tools.md)). 아래 예시의 `StrReplace`/`old_string`은 Cursor 표기.

---

## 1. 편집 전 (Pre-edit)

#### 도구 선택 분기

**규칙**: 부분 수정 → 호스트 부분 수정 도구, 전체 재작성 → 호스트 쓰기 도구, 한글 대량 → `bash`/`Shell` + `cat << 'EOF'`

> **Normative**: [runtime_edit_tools.md §1](../../runtime_edit_tools.md) · Cursor [routing.md §1.1](../../routing.md#11-file-edit-tool-schema) · [§1.4](../../routing.md#14-editing-rules)

```
❌ WRONG: Write로 justfile 수정 (전체 덮어쓰기)
Write(path, "# new content")
# → 기존 1165줄이 모두 사라짐

✅ CORRECT: 부분 수정은 StrReplace (old_string 필수)
StrReplace(path, old_string="const x = 1", new_string="const x = 2")

✅ CORRECT: Write 사용 시 반드시 먼저 Read로 전체 내용 확인
content = Read(path)  # → 전체 내용 확보 (라인 번호 제외)
Write(path, content + "\n# new section")

✅ CORRECT: 한글 대량 콘텐츠는 bash + cat << 'EOF' (edit 도구 ASCII 최적화)
bash: cat > file << 'EOF'
# 한글 포함 본문
EOF
```

### 1.1 Read → Write 직행 (가장 흔함)

**증상**: `Read`(또는 `desktop-commander_read_file`) 출력을 그대로 `Write`/`write_file`에 넣으면 파일이 망가짐.

**원인**: 읽기 도구 출력에는 라인 번호 접두사가 붙습니다 (`    111|content`). 이를 쓰기 도구에 넣으면 파일에 라인 번호가 그대로 기록됩니다.

```
❌ WRONG: Read 출력 그대로 Write
Read(path) → "    111|const x = 1\n    112|const y = 2"
Write(path, "    111|const x = 1\n    112|const y = 2")
# 파일에 "    111|const x = 1" 이렇게 기록됨

✅ CORRECT: 부분 수정은 StrReplace (old_string 필수)
StrReplace(path, old_string="const x = 1", new_string="const x = 2")

✅ CORRECT: Write 사용 시 디스크 본문만 (줄 번호 제외)
# Read 후 old_string은 도구 출력이 아닌 파일 본문에서 추출
```

### 1.2 StrReplace old_string uniqueness 검증 안 함

**증상**: `StrReplace`/`edit_block`이 "Found N matches" 에러를 반복하거나, `replace_all=true`로 파일이 망가짐.

**원인**: `old_string`이 파일에서 여러 곳에 등장하는데, uniqueness를 확인하지 않고 호출함.

```
❌ WRONG: old_string이 4군데 등장하는데 확인 안 함
StrReplace(old_string="Conclusion: [판정 — 비개발자용 요약. 검증 결과]", new_string="...")
# Error: Found 4 matches
StrReplace(old_string="Conclusion: [판정 — 비개발자용 요약. 검증 결과]", new_string="...")
# Error: Found 4 matches (같은 에러!)

✅ CORRECT: StrReplace 전 반드시 확인
assert old_string in content
assert content.count(old_string) == 1

✅ CORRECT: 여러 군데면 Write/write_file로 전체 재작성
Write(path, content.replace(/old_pattern/g, "new_value"))
```

---

## 2. 편집 중 (In-edit)

### 1.3 StrReplace 실패 후 같은 old_string 재시도

**증상**: `StrReplace`/`edit_block`이 "Could not find a match"를 반복.

**원인**: 외부 자동화(`just plan-task-close` 등)가 파일을 수정한 후, 에이전트가 stale content로 재시도함.

```
❌ WRONG: 외부 수정 후 stale content로 재시도
# just plan-task-close가 Conclusion을 채움
StrReplace(old_string="[placeholder]", new_string="...")
# Error: Could not find a match

✅ CORRECT: 실패 시 반드시 재읽기
Read(path)  # → 현재 실제 상태 확인
# Conclusion이 이미 채워져 있으면 StrReplace 건너뜀
```

### 1.4 JSX/TSX StrReplace 누적으로 구조 망가짐

**증상**: 여러 StrReplace를 연속으로 적용하면 closing tag 순서가 뒤섞이거나 중복 태그가 생김.

**원인**: 각 StrReplace는 마지막 성공한 편집의 파일 상태를 기준으로 적용됨. 실패한 편집이나 부분 적용은 무시됨.

```
❌ WRONG: 여러 StrReplace 연속 (JSX)
StrReplace("targetType === 'X' && (", "...")  # 성공
StrReplace(")})" , ")}")  # 실패 (파일 상태 다름)
StrReplace("sibling", "...")  # 성공하지만 closing tag가 이미 망가짐

✅ CORRECT: 2회 이상 실패 시 Write/write_file로 전체 재작성
Read(path)  # → 현재 실제 상태 확인
Write(path, fullContent)  # → closing tag 순서 보장
```



### 1.5 레거시 regex replace newline corruption (역사 사례)

**증상**: MCP regex mode로 여러 줄을 치환하면 literal `\n`이 파일에 기록됨.

**원인**: 레거시 `replace_content(mode='regex')`로 multi-line 치환.

**WRONG**: regex repl=`const {\n ...}`

**CORRECT**: `StrReplace` / `edit_block` — 리터럴 old_string만.

---
### 1.6 SchemaError — Tri-Runtime 도구·키 혼동 (Cursor · local LLM · Antigravity)

**증상**: `The edit tool was called with invalid arguments: SchemaError(Missing key at ["oldString"])` 또는 `Missing key at ["old_string"]`.

**핵심**: 에러 메시지의 **따옴표 안 키 이름**이 곧 런타임이 기대하는 필드명이다. `["oldString"]`이면 camelCase `oldString`이 비어 있거나 키 자체가 없다는 뜻이다.

#### 에러 → 원인 → 수정 (디코더)

전체 매트릭스: [runtime_edit_tools.md §2](../../runtime_edit_tools.md).

| 에러·증상 | 노출 런타임 | 흔한 실수 | 올바른 호출 |
| :--- | :--- | :--- | :--- |
| `Missing key at ["oldString"]` | OpenCode `edit` | `newString`만 · `old_string`으로 보냄 | `edit` + `filePath`/`oldString`/`newString` camelCase |
| `Missing key at ["old_string"]` | Cursor `StrReplace` | `new_string`만 · `oldString`으로 보냄 | `StrReplace` + `path`/`old_string`/`new_string` snake_case |
| `TargetContent` mismatch | Antigravity `replace_file_content` | `view_file` 출력·메모리로 구성 | `TargetContent` byte-identical · `StartLine`/`EndLine` 재확인 |
| `unavailable tool 'edit'` | Cursor | OpenCode 스키마로 호출 | `StrReplace` |
| `unavailable tool 'StrReplace'` | OpenCode | Cursor 스키마로 호출 | `edit` ([opencode_tools.md](../../opencode_tools.md)) |
| `unavailable tool 'replace_file_content'` | Cursor·OpenCode | Antigravity 도구 호출 | 세션 런타임 확인 · [runtime_edit_tools.md](../../runtime_edit_tools.md) |

#### Tri-Runtime 지침 충돌 (셋 다 읽되, 도구·키만 갈린다)

`AGENTS.md`는 Cursor·local LLM(OpenCode)·Antigravity가 **함께** 읽는다. lazy-load로 [routing.md §1](../../routing.md)도 들어온다. **문서는 모두 필수**이나 **부분 수정 도구 이름·키 casing·Antigravity 줄 범위**만 상충한다.

| 읽는 문서 | 런타임 | 부분 수정 | 대상 문자열 키 | path 키 |
| :--- | :--- | :--- | :--- | :--- |
| [routing.md §1.1](../../routing.md#11-file-edit-tool-schema) | Cursor IDE | `StrReplace` | `old_string` | `path` |
| [opencode_tools.md §edit](../../opencode_tools.md) | local LLM (OpenCode) | `edit` | `oldString` | `filePath` |
| [runtime_edit_tools.md §1](../../runtime_edit_tools.md) · [SPEC §1](../../../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md) | Google Antigravity | `replace_file_content` | `TargetContent` (+ `StartLine`/`EndLine`) | `TargetFile` |

**공통 (충돌 없음)**: 편집 전 읽기 · 단일 매칭 · old/target ≠ replacement · 실패 후 재읽기 · 신규 파일은 write만.

**충돌 (런타임별 분기)**: **현재 세션에 노출된 도구** 행만 따른다 — 한 문서를 무시하지 않는다.

#### Tri-Runtime 추가 패턴

1. **부분 수정인데 대상 문자열 키 생략** — `new_string`/`newString`/`ReplacementContent`만 → SchemaError 또는 mismatch.
2. **키 casing만 바꿔 재시도** — `old_string` ↔ `oldString` ↔ `TargetContent` 순환 → **도구 이름부터** 맞춘다 (`StrReplace` vs `edit` vs `replace_file_content`).
3. **Antigravity에 Cursor/OpenCode 스키마 적용** — `StrReplace`/`edit` 호출 → unavailable tool. `view_file`로 읽은 뒤 `replace_file_content` + PascalCase.
4. **신규 vs 부분 혼동** — 신규는 `Write`/`write`/`write_to_file`만.
5. **동일 SchemaError 2회** — [routing.md Repeated Tool Failure Rule](../../routing.md): 인자 재시도 금지 → 세션 도구 목록 확인 → [runtime_edit_tools.md](../../runtime_edit_tools.md) 행 대조.

```
❌ WRONG: edit에 newString만 (Missing key at ["oldString"])
edit({ filePath: "src/foo.ts", newString: "const x = 2" })

❌ WRONG: Cursor StrReplace인데 camelCase (Missing key at ["old_string"])
StrReplace(path="src/foo.ts", oldString="const x = 1", newString="const x = 2")

❌ WRONG: edit인데 routing.md snake_case
edit({ filePath: "src/foo.ts", old_string: "const x = 1", new_string: "const x = 2" })

❌ WRONG: 부분 수정인데 old 키 없음
StrReplace(path="src/foo.ts", new_string="const x = 2")

✅ CORRECT: Cursor IDE — StrReplace + snake_case (routing.md SSOT)
Read(path="src/foo.ts")
StrReplace(path="src/foo.ts", old_string="const x = 1", new_string="const x = 2")

✅ CORRECT: OpenCode / local LLM — camelCase (opencode_tools.md)
read(filePath="/path/src/foo.ts")
edit({ filePath: "/path/src/foo.ts", oldString: "const x = 1", newString: "const x = 2" })

✅ CORRECT: Google Antigravity — PascalCase + 줄 범위
view_file(TargetFile="/path/src/foo.ts", ...)
replace_file_content({
  TargetFile: "/path/src/foo.ts", StartLine: 10, EndLine: 10,
  TargetContent: "const x = 1", ReplacementContent: "const x = 2",
  Instruction: "...", CodeMarkdownLanguage: "typescript", Complexity: 3, AllowMultiple: false
})

✅ CORRECT: 신규 파일 — old/target 키 불필요
Write(path="src/foo.ts", contents="export const x = 1\n")
```

**교차 참조**: [runtime_edit_tools.md](../../runtime_edit_tools.md) · [tools §4.5](tools.md) · [routing.md §1.1](../../routing.md#11-file-edit-tool-schema) · [opencode_tools.md §edit](../../opencode_tools.md)

#### StrReplace 매칭 실패 — 줄바꿈·CRLF 불일치

**증상**: `StrReplace`/`edit`가 "Could not find a match"를 반환하거나, "No changes to apply"만 반복 (old/new는 다르게 생각했지만 실제로는 동일).

**원인**: `old_string`이 디스크 본문과 byte-identical하지 않음 — trailing newline 누락·추가, `\n` vs `\r\n`, 블록 끝 빈 줄 차이.

```
❌ WRONG: 메모리·이전 Read 출력으로 old_string 구성
StrReplace(old_string="Status: Active", ...)  # 파일은 "Status: Active\n\n"

✅ CORRECT: Read 직후 디스크 본문에서 그대로 추출
Read(path)
# 줄 번호 접두사 제외, trailing newline·CRLF 포함해 old_string 복사
StrReplace(old_string="Status: Active\n\n", new_string="Status: Active\n")
```

**호출 전**: `old_string` ≠ `new_string` — 같으면 호출하지 않는다 ([routing.md §1.2](../../routing.md)).

**`"No changes to apply"` vs `"Could not find a match"` 구분:**
- `"No changes to apply"` → old/new 동일 — 재시도 금지, 다음 단계
- `"Could not find a match"` → old_string 불일치 — 재읽기 후 범위 축소 또는 `Write` 전략 전환

#### StrReplace 실패 → 재읽기 → Write 의사결정 트리

**증상**: `StrReplace`/`edit`가 "Could not find a match", "No changes to apply", "Found N matches"를 반복.

**원인**: stale content, 줄바꿈 불일치, old/new 동일, uniqueness 미검증 등 다양한 원인이 중복됨.

**의사결정 트리:**
```
StrReplace 실패
  ├─ "No changes to apply" → old/new 동일 → 재시도 금지, 다음 단계
  │     └─ 원인: old_string과 new_string이 실제로 동일하거나 이미 파일이 목표 상태
  ├─ "Could not find a match" → 재읽기 후 확인
  │     ├─ 이미 목표 상태 → 건너뜀 (외부 자동화 실행 후 stale content 재시도)
  │     └─ old_string 불일치 → 범위 축소 또는 Write 전략 전환
  │           └─ 원인: trailing newline/CRLF 차이, byte-identical 아님
  └─ "Found N matches" → uniqueness 확인
        ├─ N == 1 → old_string 정확히 복사 후 재시도 (1회만)
        └─ N > 1 → Write/write_file로 전체 재작성
```

**핵심 규칙:**
- 2회 이상 실패 시 `StrReplace` 고집 금지 → `Read` + `Write`로 전환
- 외부 자동화(`just plan-task-close`) 실행 후 → 반드시 `Read`로 최신본 확인
- **"No changes to apply" vs "Could not find a match" 구분:**
  - `"No changes to apply"` → old/new 동일 — 재시도 금지, 다음 단계
  - `"Could not find a match"` → old_string 불일치 — 재읽기 후 범위 축소 또는 `Write` 전략 전환

**규범**: [routing.md §1.2·Terminal Response Rule](../../routing.md) · [error_patterns.md §메타 금지 9](../../error_patterns.md)

### 1.7 부분 수정 도구 호출 전 필수 검증 (통합)

1. **최신본 확보**: `Read` / `read` / `view_file` 로 최신 디스크 상태를 읽는다.
2. **유일성 검증**: 치환 대상이 지정 범위나 디스크 내에 **정확히 1번**만 나타나는지 검증한다.
   - Cursor: `content.count(old_string) == 1`
   - OpenCode: `content.count(oldString) == 1`
   - Antigravity: `StartLine` ~ `EndLine` 범위 내 `TargetContent`가 **정확히 1번** 매치.
3. **동일 체크 (old != new)**: 치환하려는 원래 문자열과 바꾸려는 새 문자열이 서로 동일하지 않아야 한다. 동일할 경우 부분 수정 도구 호출을 즉시 생략하고 편집 단계를 마친다.
   - Cursor: `old_string != new_string`
   - OpenCode: `oldString != newString`
   - Antigravity: `TargetContent != ReplacementContent`
4. **Byte-Identical 복사**: 디스크의 공백 및 줄바꿈 문자를 포함하여 원래 텍스트와 완벽하게 동일하도록 치환 대상(`old_string` / `oldString` / `TargetContent`)을 구성한다.
5. **한글/인코딩 오류 방지**: 부분 수정 도구가 ASCII 파싱에 최적화되어 한글이 포함된 JSON 전송 시 파싱 에러(`JSON parsing failed`)가 발생하는 환경(예: OpenCode/Antigravity 특정 버전)인 경우:
   - **영문/코드만 변경**: 정식 부분 수정 도구 사용.
   - **한글 포함 다량 콘텐츠**: `bash` + `cat > file << 'EOF'` 혹은 `python3 -c` 스크립트를 사용하여 파일 변경을 적용.
   - **macOS `sed -i ''` 주의**: macOS sed는 한글과 함께 사용 시 깨질 수 있으므로 `cat << 'EOF'`를 권장.

**에러 메시지 구분:**
- `"No changes to apply"` (또는 동등한 변화 없음 상태) → 치환 대상과 결과가 이미 동일함. **재시도 금지**, 다음 단계 진행.
- `"Could not find a match"` / `TargetContent mismatch` → 치환 대상 불일치. 재읽기 후 대상을 축소하거나 `Write`/`write`/`write_to_file`로 전환.

**규범**: [routing.md §1.2·1.4](../../routing.md) · [error_patterns.md §메타 금지 9](../../error_patterns.md)

---

### 1.8 Antigravity 전용 편집 도구 (replace_file_content / multi_replace_file_content) 오류

**증상**: `replace_file_content` 또는 `multi_replace_file_content` 호출 시 `StartLine`/`EndLine` 범위 불일치 에러, `TargetContent`가 지정 범위 내에서 유일하지 않음 에러, 혹은 동일 파일에 대해 병렬 호출 시 발생하는 수정 유실 에러.

**원인**:
1. **범위 오차**: `StartLine`과 `EndLine` 범위 내에 `TargetContent` 문자열이 존재하지 않거나, 범위 바깥에 있는 줄을 타겟으로 삼음.
2. **고유성 미달**: 지정한 줄 범위 내에 `TargetContent`와 완벽히 똑같은 문자열이 여러 번 나타남.
3. **병렬 호출 충돌**: 동일한 파일에 대해 여러 개의 replace 도구를 병렬로 동시 호출하여 디스크 쓰기 충돌이나 상태 불일치 발생.

```
❌ WRONG: 동일 파일에 대해 여러 replace_file_content를 동시에 병렬 호출
// 병렬로 동시 실행되면 먼저 끝난 작업이 다음 작업에 의해 덮어씌워지거나 에러 발생
Promise.all([
  replace_file_content({ TargetFile: "src/foo.ts", StartLine: 5, EndLine: 5, TargetContent: "A", ReplacementContent: "B" }),
  replace_file_content({ TargetFile: "src/foo.ts", StartLine: 20, EndLine: 20, TargetContent: "X", ReplacementContent: "Y" })
])

❌ WRONG: StartLine/EndLine 범위 안에 TargetContent가 완벽하게 들어맞지 않음
replace_file_content({
  TargetFile: "src/foo.ts",
  StartLine: 10, EndLine: 12, // 실제 TargetContent는 13번째 줄에 있음
  TargetContent: "const data = 1;",
  ReplacementContent: "const data = 2;"
})

✅ CORRECT: 비인접 다중 편집은 단일 multi_replace_file_content 호출로 묶어서 실행
multi_replace_file_content({
  TargetFile: "src/foo.ts",
  ReplacementChunks: [
    { StartLine: 5, EndLine: 5, TargetContent: "A", ReplacementContent: "B", AllowMultiple: false },
    { StartLine: 20, EndLine: 20, TargetContent: "X", ReplacementContent: "Y", AllowMultiple: false }
  ],
  Instruction: "..."
})

✅ CORRECT: 범위(StartLine/EndLine)를 TargetContent가 정확히 1개만 포함되도록 좁혀서 지정
// 10번째 줄에 위치한 대상을 정확하게 10줄만 범위로 설정하여 고유성 확보
replace_file_content({
  TargetFile: "src/foo.ts",
  StartLine: 10, EndLine: 10,
  TargetContent: "const data = 1;",
  ReplacementContent: "const data = 2;"
})
```


---

### 1.9 OpenCode(local LLM) 부분 수정(edit) replaceAll 오용 및 경로 오류

**증상**: `edit` 도구 호출 시 파일 내부의 예상치 못한 위치까지 한꺼번에 치환되어 코드가 깨지거나, `filePath` 경로 문제로 인해 리소스를 찾지 못하는 오류.

**원인**:
1. **replaceAll 오용**: 파일 내에 여러 번 매칭되는 패턴을 부분 치환하기 위해 `edit`를 사용하면서 `replaceAll: true`로 설정하여 원치 않는 중복 줄까지 모두 덮어씌움.
2. **상대 경로 전달**: local LLM 환경에서 호스트 `edit`/`read` 도구가 절대 경로를 기대함에도 불구하고 프로젝트 루트 기준 상대 경로를 인자로 넘김.

```
❌ WRONG: 단일 블록 치환이 목적이나 replaceAll을 true로 지정해 파일 전체 중복 구문 훼손
edit({ filePath: "/abs/path/src/foo.ts", oldString: "const x = 1;", newString: "const x = 2;", replaceAll: true })

❌ WRONG: filePath에 상대 경로를 제공하여 resource not found 발생
edit({ filePath: "src/foo.ts", oldString: "const x = 1;", newString: "const x = 2;", replaceAll: false })

✅ CORRECT: 단일 치환을 위해 replaceAll을 false로 지정하고 전체 절대 경로 사용
edit({ filePath: "/abs/path/src/foo.ts", oldString: "const x = 1;", newString: "const x = 2;", replaceAll: false })
```

---

### 1.10 Cursor 부분 수정(StrReplace) 상대 경로 및 old_string 고유성 오류

**증상**: `StrReplace` 도구 호출 시 `Found N matches` 에러가 나면서 수정이 취소되거나, 경로 에러가 발생하여 실패함.

**원인**:
1. **경로 형식 오인**: Cursor IDE가 프로젝트 루트 기준 상대 경로를 원함에도 호스트 파일의 절대 경로를 전달함.
2. **고유성 미달**: 지정한 `old_string`이 파일 내에 중복(2회 이상) 존재하여 도구가 어떤 것을 수정할지 판단할 수 없음.

```
❌ WRONG: StrReplace에 절대 경로 전달
StrReplace(path="/abs/path/src/foo.ts", old_string="const x = 1;", new_string="const x = 2;")

❌ WRONG: 파일 내에 여러 번 나타나는 문자열을 단순하게 old_string으로 지정
StrReplace(path="src/foo.ts", old_string="  return x;", new_string="  return y;") // Found 4 matches

✅ CORRECT: 상대 경로를 사용하고, 유일하게 식별될 수 있도록 줄 바꿈과 부모 컨테이너 구문을 포함해 고유성 확보
StrReplace(
  path="src/foo.ts",
  old_string="function calculate() {\n  return x;\n}",
  new_string="function calculate() {\n  return y;\n}"
)
```

---


## 3. React 실수

### 3.1 useEffect 내 setTimeout/debounce unmount 누락

**증상**: 페이지 이탈 후에도 timer/debounce가 실행됨.

**원인**: `useEffect`에서 timer 설정 후 cleanup(`return clear`) 생략.

**CORRECT**: `return () => clearTimeout(timer)` / `debounce.cancel()`

---

### 3.2 Fast Refresh full reload after session expiry

**증상**: 세션 만료 시 매 mount마다 redirect → full reload.

**원인**: `isAuthenticated` 변화마다 무조건 redirect.

**CORRECT**: `useRef`로 이전 auth 추적 — **true→false** 전환 때만 redirect.

---

## 4. 편집 후 (Post-edit / Recovery)

### 7.1 Write/write_file로 justfile 등 추적되지 않은 파일 덮어쓰기

**증상**: `Write`/`write_file`로 파일을 쓰면 기존 내용이 완전히 사라짐.

**원인**: 쓰기 도구는 파일을 완전히 덮어씁니다. git에 추적되지 않은 파일(예: justfile)은 `git checkout`으로 복구할 수 없음.

```
❌ WRONG: Write로 justfile 수정
Write(path, "# 📝 Error patterns management\nerror-pattern-add:\n\t@echo ...")
# → 기존 1165줄이 모두 사라짐

✅ CORRECT: 부분 수정은 StrReplace
StrReplace(path, old_string="old content", new_string="new content")

✅ CORRECT: Write 사용 시 반드시 먼저 Read로 전체 내용 확인
content = Read(path)  # → 전체 내용 확보
Write(path, content + "\n# new section")
```

### 7.2 git checkout으로 추적되지 않은 파일 복구 시도

**증상**: `git checkout -- justfile`이 "did not match any file(s) known to git" 에러.

**원인**: 파일이 git에 추적되지 않으면 `git checkout`으로 복구할 수 없음.

```
❌ WRONG: git checkout으로 복구 시도
git checkout -- justfile
# error: pathspec 'justfile' did not match any file(s) known to git

✅ CORRECT: git status로 먼저 확인
git status justfile  # → Untracked files인지 확인

✅ CORRECT: 백업이 없으면 수동 복구
# git stash, reflog, 또는 다른 저장소에서 내용 찾기
```

### 7.3 archive_plans.py — DISCUSS 종속 아카이브 시 plans-index broken reference

**증상**: `archive_plans.py archive` 실행 후 `just plans-index` 가 `"누락된 플랜 파일을 가리키는 참조"` 에러.

```
누락된 플랜 파일을 가리키는 참조:

  PLAN_tem_216_r1_layout_grid_preset.md  → 제안: docs/plans/archive/frontend/PLAN_tem_216_r1_layout_grid_preset.md
    - docs/discussions/archive/DISCUSS_tem_216_r1_layout_grid_preset.md
  PLAN_tem_216_r1_layout_server_sync.md
    - docs/discussions/archive/DISCUSS_tem_216_r1_layout_grid_server_sync.md
```

**원인**: PLAN 아카이브 시 종속 DISCUSS 파일도 함께 archive 로 이동되는데, 그 DISCUSS 파일 본문에 plan 파일을 참조하는 텍스트가 있음.
- 참조가 `docs/plans/PLAN_xxx.md` 같은 절대 경로가 아닌 **단순 텍스트**(예: `` `PLAN_xxx.md` ``) 로 작성된 경우
- 해당 plan 파일이 이미 archive 에 있거나 존재하지 않는 경우

**방지법**:
1. `archive_plans.py archive` 실행 후 `just plans-index` 가 broken reference 를 보고하면 **pre-existing issue 인지 확인**
2. DISCUSS 파일 내 plan 참조가 단순 텍스트(`PLAN_xxx.md`) → 상대 링크(`[PLAN_xxx](../plans/archive/.../PLAN_xxx.md)`) 로 수정 필요
3. plan 파일이 아예 존재하지 않는 경우 → DISCUSS 참조 줄 삭제 또는 "미발행" 주석 추가
4. **이 오류는 아카이브 워크플로 자체의 실패가 아님** — archive 는 정상 완료됨

#### 7.3.1 복구 절차

1. `just plans-index` 실행 → broken reference 확인
2. DISCUSS 파일 grep → 단순 텍스트 참조 찾기: `rg 'PLAN_\w+\.md' docs/discussions/archive/`
3. 상대 링크로 변환 또는 삭제: `sed -i '' 's/`PLAN_\(.*?\)`/[PLAN_\1](../plans/archive\/...\/PLAN_\1)/g' <file>`
4. `just plans-index` 재실행 → PASS 확인

**2026-06-01 세션 기록**: `PLAN_tem_216_r1_layout_preset_entry.md` 아카이브 시 종속 DISCUSS 3 개도 이동. `DISCUSS_tem_216_r1_layout_grid_preset.md` 가 `` `PLAN_tem_216_r1_layout_grid_preset.md` `` 텍스트 참조 포함 — plan 파일은 root 에 존재하지만 링크 포맷이 상대 경로 아님. `just plans-index` 가 누락으로 오인.

---
