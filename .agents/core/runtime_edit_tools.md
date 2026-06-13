---
id: runtime_edit_tools
scope:
- .agents/core/**
- AGENTS.md
domain: core
status: active
last_verified: 2026-06-11
---
<!-- Language: ko -->

# Tri-Runtime 편집 도구 스키마 SSOT

`AGENTS.md`·`routing.md`·`opencode_tools.md`·[SPEC_TECH_tech_multi_agent_tooling.md](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md)를 **동시에** 읽는 멀티 에이전트 환경에서, **도구 이름·키 casing**이 상충한다. 공통 원칙(편집 전 읽기·단일 매칭·old≠new·실패 후 재읽기)은 세 런타임 동일.

**SSOT 범위**: (1) 런타임별 도구명·키·path 규칙 — 파일 I/O(§1.1) + 보조 도구(§1.2) (2) 공통 패치 전제 요약 (3) 증상별 에러 디코더 (4) 한글/특수문자 우회 (5) MCP `repo_*` 전환기. 상세 절차·WRONG/CORRECT 사례는 [routing.md §1](./routing.md) · [opencode_tools.md](./opencode_tools.md) · [error_patterns/detail/editing.md](error_patterns/detail/editing.md)에 위임.

**충돌 해소**: 문서 하나를 무시하지 않는다. **현재 세션에 노출된 도구**의 행만 따른다.

---

## 0. 런타임 판별 (치트시트)

세션 **도구 목록**을 보고 아래 행만 따른다.

| 도구 목록에 보이면 | 따를 행 |
| :--- | :--- |
| `Read` / `Write` / `StrReplace` | §1 Cursor |
| `read` / `write` / `edit` | §1 OpenCode |
| `view_file` / `write_to_file` / `replace_file_content` / `multi_replace_file_content` | §1 Antigravity |
| `AskQuestion` | §1.2.1 Cursor (구조화 선택) |
| `question` (선택 UI) | §1.2.1 OpenCode (구조화 선택) |
| `WebSearch` / `WebFetch` / `Task` / `TodoWrite` 등 | §1.2 · §1.2.2 (Cursor 전용·공통 보조) |
| `webfetch` / `task` / `todowrite` / `skill` | §1.2 · §1.2.2 (OpenCode) |
| `repo_patch` + `old_text` | §5 MCP |

`unavailable tool` 에러가 나면 **다른 런타임 스키마를 섞은 것** — §2 참고.

---

## 1. 런타임별 편집 스키마

### 1.1 핵심 I/O 매트릭스

| 런타임 | 주입·로드 | 읽기 | 부분 수정 (단일) | 부분 수정 (다중) | 신규·전체 | old/대상 키 | path 키 | path 형식 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Cursor IDE** | T0 `AGENTS.md` · lazy `routing.md` §1 | `Read` | `StrReplace` | N/A | `Write` | `old_string` (snake) | `path` | 프로젝트 루트 **상대** |
| **local LLM (OpenCode)** | `opencode.json` → `AGENTS.md` + [opencode_tools.md](./opencode_tools.md) | `read` | `edit` | N/A | `write` | `oldString` (camel) | `filePath` | **절대** |
| **Google Antigravity** | 플랫폼 시스템 프롬프트 · [SPEC §1](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md) | `view_file` | `replace_file_content` | `multi_replace_file_content` | `write_to_file` | `TargetContent` (Pascal) + `StartLine`/`EndLine` | `TargetFile` | **절대** |
| **MCP `emr-repo`** | `.mcp.json` · [§5](#5-stdio-mcp-repo_-연결-전환기) | `repo_read` | `repo_patch` | N/A (`replace_all` 옵션) | `repo_write` | `old_text` (snake) | `path` | 워크스페이스 루트 **상대** |

### 1.2 보조 도구 매핑 (읽기·쓰기·부분 수정 외)

| 기능 | Cursor | OpenCode | Antigravity |
| :--- | :--- | :--- | :--- |
| 터미널 | `Shell` | `bash` | `run_command` |
| 내용 검색 (regex) | `Grep` | `grep` | `grep_search` |
| 경로·파일 탐색 | `Glob` | `glob` | `list_dir` |
| 의미 검색 (코드) | `SemanticSearch` | — | — |
| 파일 삭제 | `Delete` | — | — |
| **구조화 선택 (의사결정)** | `AskQuestion` | `question` | — (§1.2.1 fallback) |
| 웹 메타 검색 | `WebSearch` | — | — |
| URL 본문 가져오기 | `WebFetch` | `webfetch` | — |
| 서브에이전트 | `Task` | `task` | — |
| 할 일 목록 | `TodoWrite` | `todowrite` | — |
| 스킬 로드 | `Read` (SKILL 경로) | `skill` | `Read`/`view_file` |
| 린트·진단 | `ReadLints` | — | — |
| 부분 수정 (다중 블록) | — | — | `multi_replace_file_content` (§1.1) |
| MCP 도구·리소스 | `CallMcpTool` · `FetchMcpResource` | — | — (§5 `repo_*` 별도) |
| 셸 백그라운드 폴링 | `Await` | — | — |
| 모드 전환 | `SwitchMode` | — | — |
| 노트북 셀 편집 | `EditNotebook` | — | — |
| 이미지 생성 | `GenerateImage` | — | — |

`—` = 해당 런타임에 네이티브 도구 **미노출** 또는 미문서화. 대안은 §1.2.2.

Golden Log `--tools`·도구명 정규화: [ai-log.md §도구명](../workflows/ai-log.md) · [normalize_tool_syntax.py](../../projects/ai-log/tools/normalize_tool_syntax.py).

### 1.2.1 구조화 선택 (의사결정) 스키마

저장소 지침의 **`AskQuestion`/`question`(병용)** 표기는 Cursor `AskQuestion`과 OpenCode `question`에 **동일 적용**한다. 공통 UX·권장 태그 규칙: [principles.md](./principles.md) §1.1.1.

| 런타임 | 도구명 | 제목·헤더 | 질문 본문 | 옵션 | 복수 선택 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cursor** | `AskQuestion` | `title` | `questions[].prompt` | `questions[].options[].id` + `.label` | `allow_multiple` |
| **OpenCode** | `question` | `questions[].header` | `questions[].question` | `questions[].options[].label` + `.description` | `multiple` |
| **Antigravity** | — | 네이티브 구조화 선택 **미문서화** | — | — | — |

**MUST**

- 세션에 노출된 도구의 **키만** 사용 — Cursor `prompt`를 OpenCode `question`에, OpenCode `description`을 Cursor `id`에 **혼용 금지**.
- native 도구로 호출 — assistant content에 pseudo JSON·`<tool_call>` 출력 **금지** ([principles.md](./principles.md) §1.1.1).
- 옵션 2~4개 · `(권장)` 1개 + 맥락 근거 1줄 · 비개발자 톤(경로 나열 금지).

**도구 미노출 시** (Antigravity 등): [principles.md](./principles.md) §1.1.1 — 채팅에 번호·A/B/C + 옵션별 기대 결과 한 줄 fallback.

**예시**

Cursor `AskQuestion`:

```json
{
  "title": "개선안 선택",
  "questions": [{
    "id": "fix-scope",
    "prompt": "어떤 범위로 수정할까요?",
    "options": [
      {"id": "high-priority", "label": "(권장) 치명적 문제만 즉시 수정"},
      {"id": "analysis-only", "label": "분석만 유지, 코드 수정 없음"}
    ]
  }]
}
```

OpenCode `question` ([opencode_tools.md](./opencode_tools.md) §question):

```json
{
  "questions": [{
    "question": "어떤 범위로 수정할까요?",
    "header": "개선안 선택",
    "options": [
      {"label": "(권장) 치명적 문제만 즉시 수정", "description": "잘못된 모킹·빈 assertion·flaky 대기"},
      {"label": "분석만 유지, 코드 수정 없음", "description": "리포트만 유지"}
    ],
    "multiple": false
  }]
}
```

### 1.2.2 기타 보조 도구 — 주의·스키마 차이

§1.2 표에서 `—`인 셀·런타임 전용 도구에 대한 보충이다. **세션 도구 목록에 없으면 호출하지 않는다.**

#### 공통 정책

| 주제 | 규칙 |
| :--- | :--- |
| **OpenCode 턴당 1도구** | local LLM은 한 assistant 턴에 도구 **1개만** — [opencode_tools.md](./opencode_tools.md) |
| **웹 조사** | 메타 검색 → 본문 확인 순 — [SPEC §공통](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md) (`WebSearch` → `WebFetch`/`webfetch`) |
| **레거시 별칭 금지** | `read_file`, `codebase_search`, `terminal`, `patch` 등 — §3 · [normalize_tool_syntax.py](../../projects/ai-log/tools/normalize_tool_syntax.py) |
| **스킬 로드** | Cursor는 `Read`로 `SKILL.md` 직접 읽기 · OpenCode는 `skill` 도구 (`name` 키) |

#### 검색·탐색 키 차이

| 기능 | Cursor | OpenCode | Antigravity |
| :--- | :--- | :--- | :--- |
| regex 검색 path | `path` (선택) | `path` + `include` (glob) | `grep_search` 전용 키 |
| 경로 탐색 | `Glob` — `glob_pattern` | `glob` — `pattern` | `list_dir` — 디렉터리 나열 (glob 아님) |
| 의미 검색 | `SemanticSearch` — `query`, `target_directories` | — | — |

#### 서브에이전트 · 할 일 · 웹 fetch

| 기능 | Cursor `Task` | OpenCode `task` |
| :--- | :--- | :--- |
| 공통 | `description`, `prompt`, `subagent_type` | 동일 |
| Cursor 전용 | `model`, `resume`, `readonly`, `run_in_background`, `interrupt` | — |
| OpenCode 전용 | — | `task_id` (resume) |

OpenCode `webfetch`: `url`, `format` (`markdown`), `timeout` — [opencode_tools.md §webfetch](./opencode_tools.md).

OpenCode `todowrite`: `todos[]` with `content`, `status`, `priority` (Cursor `TodoWrite`는 `id`·`merge` 등 스키마 상이 — 세션 스키마 따름).

#### Cursor 전용 (다른 런타임 대체 없음)

| 도구 | 용도 |
| :--- | :--- |
| `ReadLints` | 편집 파일 린트·타입 진단 |
| `Await` | 백그라운드 `Shell` 출력 폴링 |
| `SwitchMode` | Agent ↔ Plan 모드 전환 |
| `EditNotebook` | `.ipynb` 셀 편집 |
| `GenerateImage` | 사용자 **명시 요청** 시에만 이미지 생성 |
| `CallMcpTool` / `FetchMcpResource` | MCP 서버 도구·리소스 — stdio `repo_*`는 §5 |

#### Antigravity 편집 보조

- `view_file` **800라인 제한** — 큰 파일은 `grep_search`로 먼저 좁힌 뒤 읽기 ([SPEC §2](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md)).
- 동일 파일 비연속 다중 수정: `multi_replace_file_content` **단일 호출** — `replace_file_content` 병렬 다중 호출 **금지** (§1.1).

#### Antigravity — 미문서화 보조 (실측 전)

아래는 **저장소에 플랫폼 실측 SSOT가 없다**. 세션 도구 목록에 노출될 때만 사용한다.

| 기능 | 상태 | 대안 |
| :--- | :--- | :--- |
| 웹 메타 검색 | 미문서화 | Cursor `WebSearch` 세션이 아니면 공식 문서 URL·`docs/knowledge/` 직접 조회 |
| URL 본문 | 미문서화 | 터미널 `curl`/`run_command` 또는 Cursor `WebFetch` 세션 |
| 서브에이전트 | 미문서화 | Cursor `Task` / OpenCode `task` 세션으로 핸드오프 |
| 구조화 선택 | 미문서화 | §1.2.1 채팅 A/B/C fallback |
| MCP | §5 `repo_*`만 계약화 | 그 외 MCP는 플랫폼 노출 시에만 |

플랫폼에서 새 도구가 확인되면 본 절·[SPEC §1](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md)에 **실측 후** 행을 추가한다(추측 기입 금지).

### 1.3 공통 패치 전제조건 (tri-runtime)

상세·CLI 검증: [routing.md §1.2–§1.4](./routing.md#12-patch-preconditions-메타-금지-12) · [AGENTS.md §2.1](../../AGENTS.md).

| MUST | MUST NOT |
| :--- | :--- |
| 읽기 도구로 디스크 최신본 확보 → old/target을 본문에서 **그대로** 복사 (줄 번호·프롬프트 메타 제외) | `Read`/`view_file` 출력의 줄 번호를 `old_string`/`TargetContent`에 포함 |
| 치환 대상이 디스크에 **정확히 1번** 존재 | 매칭 0·2+ 상태에서 부분 수정 호출 |
| **old ≠ new** (Antigravity: `TargetContent ≠ ReplacementContent`) — 같으면 호출 금지 | `"No changes to apply"` 수신 후 **동일 쌍** 재호출 |
| 패턴 실패 시 **재읽기 → 범위 축소 → 단일 줄** 1회 재시도 | 실패 직후 더 넓은 블록·전체 `Write` 덮어쓰기 |
| 신규·전체 → 쓰기 도구 · 단일 연속 블록 → 부분 수정 도구 | 부분 수정 ↔ 전체 쓰기 **자동 전환** |
| `replace_all`/`replaceAll`은 **반드시 `false`** (단일 구간 치환) | `true`로 파일 전역 무차별 치환 |

**`"No changes to apply"` 수신 시**: 재읽기 → (a) 목표 내용 이미 있으면 완료 (b) 없으면 old/target·범위·new 중 하나 변경 후 **1회만** 재시도.

### Cursor — `StrReplace`

```json
{
  "path": "src/foo.ts",
  "old_string": "const x = 1",
  "new_string": "const x = 2",
  "replace_all": false
}
```

- `path`: 프로젝트 루트 기준 **상대** path.
- `old_string`: 파일 내 **정확히 1번** 매칭. 2건 이상 → `Found N matches` (§2).
- `replace_all`: 기본·권장 `false`. `true`는 의도적 전역 치환 때만.

Normative: [routing.md §1.1.3](./routing.md#113-cursor-ide-edit-rules-전용)

### local LLM (OpenCode) — `edit`

```json
{
  "filePath": "/abs/path/src/foo.ts",
  "oldString": "const x = 1",
  "newString": "const x = 2",
  "replaceAll": false
}
```

- `filePath`: 워크스페이스 **절대** path.
- `replaceAll`: **반드시 `false`** — `true`는 코드 손상 위험.

Normative: [opencode_tools.md §edit](./opencode_tools.md)

### Google Antigravity — `replace_file_content`

단일 연속 블록만. `TargetContent`는 디스크 본문과 **byte-identical** (공백·줄바꿈 포함). 비연속 다중 수정은 `multi_replace_file_content` — **동일 파일에 `replace_file_content` 병렬 다중 호출 금지** (디스크 쓰기 충돌).

```json
{
  "TargetFile": "/abs/path/src/foo.ts",
  "StartLine": 10,
  "EndLine": 10,
  "TargetContent": "const x = 1",
  "ReplacementContent": "const x = 2",
  "Instruction": "Update constant",
  "CodeMarkdownLanguage": "typescript",
  "Complexity": 3,
  "AllowMultiple": false
}
```

**`multi_replace_file_content`** (비연속 다중 블록, 단일 호출):

```json
{
  "TargetFile": "/abs/path/src/foo.ts",
  "ReplacementChunks": [
    {
      "StartLine": 10,
      "EndLine": 10,
      "TargetContent": "const x = 1",
      "ReplacementContent": "const x = 2"
    },
    {
      "StartLine": 25,
      "EndLine": 27,
      "TargetContent": "function old() {\n  return 1;\n}",
      "ReplacementContent": "function old() {\n  return 2;\n}"
    }
  ],
  "Instruction": "Update constant and function return",
  "CodeMarkdownLanguage": "typescript"
}
```

Normative: [routing.md §1.1.1](./routing.md#111-google-antigravity-edit-rules-전용) · [SPEC §1](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md)

---

## 2. 에러 디코더 (런타임 혼동·패치 실패)

WRONG/CORRECT 예시: [editing §1.6](error_patterns/detail/editing.md) · Cursor 상세: [routing.md §1.4·Terminal Response](./routing.md#14-editing-rules-replace--write-discipline)

### 2.1 스키마·도구 혼동

| 에러·증상 | 잘못 섞인 조합 | 조치 |
| :--- | :--- | :--- |
| `Missing key at ["oldString"]` | OpenCode `edit`에 `old_string` 또는 `newString`만 | `edit` + `oldString`/`newString`/`filePath` camelCase |
| `Missing key at ["old_string"]` | Cursor `StrReplace`에 `oldString` | `StrReplace` + snake_case |
| `unavailable tool 'edit'` | Cursor 세션에서 OpenCode 스키마 | `StrReplace` (§0) |
| `unavailable tool 'StrReplace'` | OpenCode 세션에서 Cursor 스키마 | `edit` (§0) |
| `unavailable tool 'view_file'` / `'replace_file_content'` | Cursor·OpenCode에서 Antigravity 도구 | §0 — 세션 도구 목록 확인 |
| `JSON parsing failed: Property name must be a string literal` | 한글·특수문자를 부분 수정 JSON에 직접 삽입 | [§4](#4-한글특수문자-본문-우회) |

### 2.2 패치·매칭 실패

| 에러·증상 | 원인 | 조치 |
| :--- | :--- | :--- |
| `Found N matches` (Cursor) | `old_string`이 파일에 2+ 회 | 블록을 넓혀 유일 구문으로 조정, 또는 범위 축소 후 재읽기 |
| `No changes to apply` (전 런타임) | old=new 또는 이미 반영됨 | **동일 쌍 재호출 금지** → 재읽기 → §1.3 분기 |
| Antigravity `TargetContent` mismatch | `view_file` 출력·메모리로 구성 | `view_file` 직후 디스크 본문 복사 · `StartLine`/`EndLine` 재확인 |
| old/target not found | 추측 문자열·CRLF·트레일링 공백 불일치 | 재읽기 → byte-identical 복사 |
| 동일 호출 + 동일 에러 **2회** | 스키마·인자·디스크 상태 미검증 | 재시도 중단 → 인자·스키마 점검 ([routing.md Repeated Failure](./routing.md#repeated-tool-failure-rule-extends-editing-rules)) |

### 2.3 MCP `repo_patch` code → 조치

| code | 조건 | 조치 |
| :--- | :--- | :--- |
| `INVALID_ARGS` | 필수 인자·path 샌드박스·키 누락 | `path` 상대·`old_text`/`new_text` snake_case 재확인 |
| `NO_CHANGE` | `old_text` === `new_text` | 호출 금지 — §1.3 동일 |
| `NOT_FOUND` | 본문에 `old_text` 없음 | 재읽기 → byte-identical |
| `NOT_UNIQUE` | `replace_all=false`인데 2+ 매칭 | old_text 범위 확대·유일화 |
| `IO_ERROR` | ENOENT·권한·인코딩 | path·파일 존재·샌드박스 확인 |

상세: [SPEC_TECH_repo_mcp_tools.md §4](../../docs/specs/technical/SPEC_TECH_repo_mcp_tools.md)

---

## 3. 금지 목록은 런타임 한정

| 금지 (문서) | 적용 런타임 | Antigravity·OpenCode에서는 |
| :--- | :--- | :--- |
| `edit`, `oldString` | Cursor ([routing.md §1.1](./routing.md)) | **정식** (OpenCode) |
| `view_file`, `replace_file_content` | Cursor | **정식** (Antigravity) |
| `StrReplace`, `old_string` | OpenCode·Antigravity 네이티브 | **정식** (Cursor) |
| `read_file`, `write_file`, `patch`, `apply_diff` | 전 런타임 (레거시 별칭) | §0·§1 정식명 사용 — [tools.md §4.5](error_patterns/detail/tools.md) |

한 런타임의 «금지»를 다른 런타임에 적용하지 않는다.

---

## 4. 한글/특수문자 본문 우회

호스트 **부분 수정 도구**는 ASCII-only JSON 파싱에 최적화되어, 한글·특수문자 본문을 JSON 인자에 그대로 넣으면 `JSON parsing failed` 등이 날 수 있다. ([AGENTS.md §4.1](../../AGENTS.md) · [opencode_tools.md §edit](./opencode_tools.md))

| 상황 | 권장 |
| :--- | :--- |
| 영문·코드만 변경 | 세션 네이티브 부분 수정 (§1) |
| 한글 포함 **대량** 콘텐츠 | 터미널 우회 — Cursor `Shell` · OpenCode `bash` · Antigravity `run_command` |
| 우회 패턴 | `cat > file << 'EOF'` … `EOF` 또는 `python3 -c` (heredoc·인자 이스케이프 안전) |
| macOS 금지 | `sed -i ''` + 한글 본문 (이스케이프 오류) |
| MCP 노출 시 | `repo_patch`의 `old_text`/`new_text`도 동일 제약 — 한글 대량은 터미널 우회 |

---

## 5. stdio MCP `repo_*` 연결 (전환기)

tri-runtime 네이티브 도구와 **병행**한다. 세션에 `repo_patch`가 노출되면 §1 네이티브 대신 MCP 계약을 우선한다. 장기 SSOT: [SPEC_TECH_repo_mcp_tools.md](../../docs/specs/technical/SPEC_TECH_repo_mcp_tools.md).

### 5.1 선택 기준

| 조건 | 사용 |
| :--- | :--- |
| 세션에 `repo_read`/`repo_patch`/`repo_write` 노출 | MCP (snake_case, 상대 `path`) |
| MCP 미노출 | §1 런타임 네이티브 행 |
| 한글 대량 본문 | §4 터미널 우회 (MCP·네이티브 공통) |

### 5.2 로컬 등록 (`.mcp.json`)

```json
{
  "mcpServers": {
    "emr-repo": {
      "command": "uv",
      "args": ["run", "python", "scripts/mcp_repo_server.py"]
    }
  }
}
```

### 5.3 계약 요약

- **서버**: `scripts/mcp_repo_server.py` (stdio)
- **읽기**: `repo_read` — `{ "path": "src/foo.ts" }`
- **부분 수정**: `repo_patch` — `{ "path": "src/foo.ts", "old_text": "…", "new_text": "…", "replace_all": false }`
- **신규·전체**: `repo_write` — `{ "path": "src/new.ts", "content": "…" }`
- **키**: snake_case `path`/`old_text`/`new_text`/`replace_all` — 벤더 중립
- **에러**: 5종 code — §2.3 · [SPEC §4](../../docs/specs/technical/SPEC_TECH_repo_mcp_tools.md)
- **샌드박스**: 워크스페이스 루트 상대 path만 (`EMR_WORKSPACE_ROOT` 또는 git root)

---

## 6. 관련 문서

- [routing.md §1](./routing.md) — Cursor 편집 규칙·Editing Rules·Terminal Response
- [opencode_tools.md](./opencode_tools.md) — OpenCode/local LLM 도구 목록·턴당 도구 1개
- [editing.md §1.6](error_patterns/detail/editing.md) — 세션 사례·의사결정 트리
- [tools.md §4.5](error_patterns/detail/tools.md) — 레거시 별칭·SchemaError
- [SPEC_TECH_tech_multi_agent_tooling.md](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md) — tri-runtime 역할·매핑
- [SPEC_TECH_repo_mcp_tools.md](../../docs/specs/technical/SPEC_TECH_repo_mcp_tools.md) — MCP canonical repo I/O 계약
