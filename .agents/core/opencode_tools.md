---
id: opencode_tools
scope:
- .agents/core/**
domain: core
status: active
last_verified: 2026-06-08
---
<!-- Language: ko -->

# OpenCode Tool List — local LLM 편집 스키마 SSOT

> **Tri-Runtime**: `opencode.json`이 `AGENTS.md`와 **함께** 본 문서를 주입한다. `AGENTS.md`·[routing.md §1](./routing.md)(Cursor) · Antigravity `replace_file_content`도 **같이 읽히며** 도구·키만 충돌한다. **OpenCode/local LLM 세션**에서는 본 문서가 우선. 3런타임 매트릭스: [runtime_edit_tools.md §1](./runtime_edit_tools.md) · 보조 도구 전체: §1.2–§1.2.2 · 예시: [editing §1.6](error_patterns/detail/editing.md).

## OpenCode + LM Studio (Qwen3.6) — tool turn discipline

LM Studio는 모델 출력의 `<tool_call>` XML을 파싱해 OpenCode에 넘긴다. **한 assistant 턴에 `<tool_call>`을 여러 개 쓰면 파싱·실행이 실패**하고 XML이 채팅에 그대로 노출된 뒤 EOS로 끝난다.

**MUST (local LLM)**:

- **턴당 도구 1개만** — `git log` → 결과 확인 → 다음 턴에 `git status` (한 답에 묶지 않음)
- 도구가 필요하면 assistant 본문은 **단일** `<tool_call>…</tool_call>` 또는 호스트 native tool channel만 사용
- `[TOOL_REQUEST]` / `END_TOOL_REQUEST` / `{"name":...}` hybrid 출력 금지
- 도구 이름은 본 문서 표만 (`bash`, `edit`, `read`, `write`, `grep`, `glob` — `read_file`, `StrReplace` 금지)

## Available Tools

| Tool | Description |
|------|-------------|
| `bash` | Shell command execution |
| `edit` | File string replacement |
| `glob` | File pattern search |
| `grep` | File content regex search |
| `question` | Ask user questions |
| `skill` | Load a specialized skill |
| `task` | Launch sub-agent |
| `todowrite` | Manage task list |
| `webfetch` | Fetch URL content |
| `write` | Write/overwrite file |

## Tool Parameters

### bash
```json
{
  "command": "ls -la",
  "timeout": 30000,
  "workdir": "/Users/seungjulee/Desktop/Dev/emr",
  "description": "Lists files in current directory"
}
```

### edit

**Before calling `edit`:**

1. `read` the target file.
2. Verify `oldString` exists in disk content (byte-identical; watch trailing newlines / CRLF).
3. Ensure `oldString` ≠ `newString` — if equal, **do not call** `edit`.
4. **한글/특수문자 제한 ([AGENTS.md §4.1](../../AGENTS.md), [runtime_edit_tools.md §4](./runtime_edit_tools.md))**: `edit`는 ASCII-only JSON 파싱에 최적화되어 한글 본문에서 `JSON parsing failed` 등이 날 수 있습니다.
   - **영문/코드 변경**: `edit` 사용.
   - **한글 포함 대량 콘텐츠**: `bash` + `cat > file << 'EOF'` 또는 `python3 -c` (macOS `sed -i ''` + 한글 금지).
5. **무한 루프 방지 & 복구 (Terminal Response Rule)**:
   - `"No changes to apply"` 수신 시: 동일한 `oldString`/`newString` 쌍으로 **재호출 절대 금지**. 즉시 `read`로 디스크의 실제 상태를 다시 확인하십시오. 만약 목표 상태가 이미 반영되어 있다면 완료로 보고 다음 단계로 진행하고, 반영되지 않았다면 `oldString`의 범위나 `newString`을 변경하여 딱 1회만 다시 시도하십시오.
   - **2회 연속 실패 규칙**: 동일한 도구 호출이 동일한 에러로 2회 연속 실패할 경우, 즉시 재시도(retry)를 중단하고 인자를 재검토하거나 `write` 전체 덮어쓰기 전략 등 대안을 사용하십시오.

```json
{
  "filePath": "/path/to/file.ts",
  "oldString": "existing text",
  "newString": "replacement text",
  "replaceAll": false
}
```

### glob
```json
{
  "pattern": "**/*.ts",
  "path": "/Users/seungjulee/Desktop/Dev/emr"
}
```

### grep
```json
{
  "pattern": "function\\s+\\w+",
  "path": "/Users/seungjulee/Desktop/Dev/emr",
  "include": "*.ts"
}
```

### question
```json
{
  "questions": [{
    "question": "Which approach?",
    "header": "Choice",
    "options": [
      {"label": "Option A", "description": "Description A"},
      {"label": "Option B", "description": "Description B"}
    ],
    "multiple": false
  }]
}
```

### skill
```json
{
  "name": "frontend-design"
}
```

### task
```json
{
  "description": "Explore codebase",
  "prompt": "Find all API endpoints",
  "subagent_type": "explore",
  "task_id": "optional-resume-id"
}
```

### todowrite
```json
{
  "todos": [
    {"content": "Task 1", "status": "pending", "priority": "high"},
    {"content": "Task 2", "status": "in_progress", "priority": "medium"}
  ]
}
```

### webfetch
```json
{
  "url": "https://example.com",
  "format": "markdown",
  "timeout": 30
}
```

### write
```json
{
  "content": "file content here",
  "filePath": "/path/to/file.txt"
}
```
