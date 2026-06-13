---
scope: detail
domain: core
parent: .agents/core/error_patterns.md
lazy_load: true
---
<!-- Language: ko -->

> **역할**: WRONG/CORRECT 예시 전용. 규범(도구 분기·Editing Rules·패치 전제조건·MCP 호출 정책)은 [routing.md](../../routing.md) §1 SSOT — 본문에 재서술하지 않는다.
> **도구**: Cursor `Read`/`Write`/`StrReplace` · MCP `desktop-commander_*` — routing §1.1 표 · MCP 이름은 세션 `mcps/` 디스크립터 SSOT.

## 4. 도구 사용 실수

### 4.1 Write/write_file 부패 (os.getenv corruption / Read 라인 번호 아티팩트)

**증상 A**: `Write`/`write_file`로 파일을 쓰면 `os.getenv("TELEGRAM_TOKEN", "")` 같은 긴 함수 호출이 잘림.

**증상 B**: `Read`/`read_file` 출력의 라인 번호 접두사(예: `'560|'`)를 `old_string`에 그대로 포함시켜 파일에 아티팩트 삽입.

**원인 A**: 일부 쓰기 경로가 긴 문자열을 처리할 때 truncation 발생.

**원인 B**: 읽기 도구 출력에는 라인 번호 접두사가 붙지만, `StrReplace`/`edit_block`은 실제 파일 콘텐츠(라인 번호 없음)와 매칭해야 함.

```
❌ WRONG A: Write로 os.getenv 포함 파일 쓰기
Write(path, 'os.getenv("TELEGRAM_TOKEN", "")')
# → "*** \"\")" 이렇게 잘림

✅ CORRECT A: 부분 수정은 StrReplace
StrReplace(path, old_string='old_value', new_string='os.getenv("TELEGRAM_TOKEN", "")')

✅ CORRECT A: MCP
desktop-commander_write_file(path, content)

❌ WRONG B: Read 출력의 라인 번호를 old_string에 포함
# Read 출력: "    560|const x = 1"
StrReplace(old_string="    560|const x = 1", new_string="...")
# → 파일에 "    560|const x = 1" 이렇게 기록됨

✅ CORRECT B: StrReplace 전 Read로 최신 상태 재확인
# - Read 출력의 라인 번호 접두사(숫자+|)를 old_string에서 반드시 제거
# - 도구 출력을 직접 old_string으로 쓰지 않고, 디스크 본문에서 exact snippet 확보
```

### 4.2 Biome auto-fix (--auto-fix)로 import 이름 변경

**증상**: `frontend_biome_gate.sh --auto-fix` 후 TypeScript 에러 발생.

**원인**: biome이 import 이름을 재작성함 (예: `useLayoutPresetStore` → `useLayoutPreset`).

```
❌ WRONG: --auto-fix 사용
frontend_biome_gate.sh --auto-fix
# → import 이름이 변경됨

✅ CORRECT: single-file format만 사용
pnpm exec biome format --write <single-file>

✅ CORRECT: baseline 업데이트는 --update-baseline
frontend_biome_gate.sh --update-baseline
```

---

### 4.4 MCP 도구명 underscore/hyphen 불일치

**증상**: `Model tried to call unavailable tool 'desktop_commander_read_text_file'`

**원인**: 모델이 underscore 버전(`desktop_commander_read_file`) 또는 `_text_` variant(`read_text_file`)를 호출하지만, 실제 MCP 서버는 hyphen 버전(`desktop-commander_read_file`)만 노출.

```
❌ WRONG: underscore + _text_ variant 호출
desktop_commander_read_text_file(path)  # Tool not found
desktop_commander_write_text_file(path, content)  # Tool not found

✅ CORRECT: SSOT 참조 + hyphen 버전 사용
# 1. 세션 mcps/<server>/tools/*.json 디스크립터에서 정확한 도구명 확인 (또는 just mcp-tools-validate)
# 2. 실제 호출:
desktop-commander_read_file(path)
desktop-commander_write_file(path, content)
```

**대응** (예시 맥락):
1. MCP 도구명 — 세션 `mcps/` 디스크립터 또는 `just mcp-tools-validate`
2. 하위 호환성 별칭(underscore, `_text_`)은 존재하지 않음

### 4.5 Tri-Runtime 별칭 혼용 + SchemaError

**증상**: `unavailable tool 'read_file'` / `SchemaError(Missing key at ["oldString"])` / `Missing key at ["old_string"]` / Antigravity `TargetContent` mismatch

**원인**: `AGENTS.md`를 Cursor·OpenCode·Antigravity가 **함께** 읽어 도구·키가 섞임. Tri-Runtime 매트릭스: [runtime_edit_tools.md](../../runtime_edit_tools.md).

1. **다른 런타임 도구 이름**으로 호출 (`read_file`, `edit`, `view_file`, `replace_file_content` 등).
2. **부분 수정** 시 대상 문자열 키 누락 (`old_string` / `oldString` / `TargetContent`).
3. **키 casing 혼용** — Cursor snake vs OpenCode camel vs Antigravity Pascal.
4. **신규 파일**에 부분 수정 도구 호출.

```
❌ WRONG: Cursor 세션에서 OpenCode/Antigravity 도구
edit({ filePath: "...", newString: "..." })
replace_file_content({ TargetFile: "...", ReplacementContent: "..." })  # TargetContent 누락

❌ WRONG: OpenCode 세션에서 Cursor 키
StrReplace(path="...", old_string="...", new_string="...")  # unavailable 또는 wrong schema

❌ WRONG: Antigravity에 Cursor/OpenCode 스키마
StrReplace(path="...", old_string="...")

✅ CORRECT: Cursor — [routing.md §1.1](../../routing.md)
Read(path) → StrReplace(path, old_string="...", new_string="...")

✅ CORRECT: OpenCode — [opencode_tools.md](../../opencode_tools.md)
read → edit({ filePath, oldString, newString })

✅ CORRECT: Antigravity — [runtime_edit_tools.md §1](../../runtime_edit_tools.md)
view_file → replace_file_content({ TargetFile, StartLine, EndLine, TargetContent, ReplacementContent, ... })

✅ CORRECT: Blueprint MCP Task
desktop-commander_read_file → desktop-commander_edit_block(old_str, new_str)

✅ CORRECT: 신규 파일 — Write / write / write_to_file
```

**규범**: [runtime_edit_tools.md](../../runtime_edit_tools.md) · [routing.md §1.1](../../routing.md) · [editing §2.3](editing.md) · MCP — `mcps/` 또는 `just mcp-tools-validate`.

---

