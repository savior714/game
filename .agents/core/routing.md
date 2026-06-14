---
scope:
- '*'
always_apply: false
priority: 2
domain: core
verify_with:
- just prevent-tech-debt
---
<!-- Language: ko -->
# 도구 라우팅 및 파일 접근 규칙

이 문서는 에이전트의 도구 선택·라우팅 정책과 편집 전 컨텍스트 라우팅 절차를 규정합니다.
핵심 실행 원칙은 [execution.md](./execution.md) 를 참조.

---

## 📋 AGENTS.md 헌법 적용 요약

| 원칙 | 이 문서에서의 구현 |
|------|-------------------|
| **1. 규칙 위계** | priority: 2 — `PROJECT_RULES.md` 다음, `.agents/domains/`보다 우선 |
| **2. 사고→단순→표적** | §1.3 라인 번호 안전 규칙 — 구조 기반 탐색 우선, 라인 번호 기반 수정 금지 |
| **3. 편집 게이트 4단계** | §1.2 Patch Preconditions — 읽기 → 단일매칭 → old≠new → 재시도 1회 |
| **4. 다중 에이전트** | §2.7 세션 매니페스트 — `route-gate-check-touched`로 편집 경로 검증 |
| **5. Plan CLI 전용** | 이 문서의 대상 — 편집 게이트를 위한 `just route` CLI 전용 절차 |
| **6. 검증·한글·고유성** | §1.4 Terminal Response Rule — `"No changes"` 재시도 금지, 한글 우회 가이드 |

---

## 1. File Edit Tool Schema & Editing Rules

> **Tri-Runtime (Cursor · local LLM · Antigravity)**: 본 절 §1.1–§1.4의 **도구 이름·키 스키마**는 **Cursor IDE** 기준이다. `AGENTS.md`는 세 런타임이 **함께** 읽으며, 편집 스키마만 다르다 — local LLM: [opencode_tools.md](./opencode_tools.md) (`edit`/`oldString`), Antigravity: `replace_file_content`/`TargetContent` ([runtime_edit_tools.md](./runtime_edit_tools.md) · [SPEC §1](../../docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md)). **문서는 모두 읽되**, 충돌 시 **현재 세션에 노출된 도구** 행만 따른다. 예시: [editing §1.6](error_patterns/detail/editing.md).

저장소, 코드베이스, 파일시스템, 개발, 디버깅 관련 작업 시 다음 원칙을 반드시 준수한다.

1. **파일 I/O**: Cursor 내장 도구(`Read` / `Write` / `StrReplace` / `Grep` / `Glob` / `SemanticSearch`)를 사용한다. *(다른 런타임 매핑: [runtime_edit_tools.md §1](./runtime_edit_tools.md))*
2. **터미널·검증·런타임 조사**: 내장 Shell로 **실측**한다. prior knowledge·추측으로 대체하지 않는다.
3. **Never assume** file contents, project structure, configs, APIs, or implementation details without inspection (`Read` 등).

### 1.1 File Edit Tool Schema (편집 도구 SSOT)

부분 수정과 신규/전체 쓰기를 **반드시** 분기한다. 런타임별로 지원되는 고유 편집 도구 및 필수 인자를 준수해야 하며, 부적절한 도구/인자 사용 시 `SchemaError`가 발생한다.

| 작업 | Cursor 내장 | OpenCode (local LLM) | Google Antigravity | 필수 인자 (Antigravity) |
| :--- | :--- | :--- | :--- | :--- |
| 읽기 | `Read` | `read` | `view_file` | `AbsolutePath` |
| 신규·전체 | `Write` | `write` | `write_to_file` | `TargetFile`, `CodeContent` |
| 부분 수정 (단일) | `StrReplace` | `edit` | `replace_file_content` | `TargetFile`, `TargetContent`, `ReplacementContent`, `StartLine`, `EndLine` |
| 부분 수정 (다중) | N/A | N/A | `multi_replace_file_content` | `TargetFile`, `ReplacementChunks` |

**금지 (런타임 한정)**: 현재 세션에 노출되지 않은 타 런타임 도구는 호출할 수 없다. (예: Cursor IDE 내에서는 `replace_file_content` 사용 금지, Antigravity 내에서는 `StrReplace` 사용 금지). 상세한 금지 및 호환 목록은 [runtime_edit_tools.md §3](./runtime_edit_tools.md)를 참조한다.

**흐름**: 읽기 → 디스크 본문에서 old 문자열 추출(줄 번호 제외) → 부분 수정 도구 호출. 신규 파일은 `Write`만 사용.

### 1.1.1 Google Antigravity Edit Rules (전용)

Google Antigravity 런타임 환경에서는 `replace_file_content` 및 `multi_replace_file_content` 사용 시 아래 규칙을 반드시 준수한다.

- **replace_file_content (단일 연속 블록)**: 단일 구간을 수정할 때 사용한다. `StartLine`과 `EndLine`으로 탐색 범위를 지정하며, 이 범위 안에 위치한 `TargetContent`는 디스크 본문과 공백 및 줄바꿈을 포함하여 바이트 단위로 완벽하게 일치(byte-identical)해야 한다.
- **multi_replace_file_content (비연속 다중 블록)**: 동일 파일에 대해 서로 다른 여러 위치를 한 번에 수정할 때 사용한다. 동일 파일에 대해 개별 `replace_file_content` 도구를 병렬(Promise.all 등)로 여러 번 호출하는 것을 **엄격히 금지**하며(디스크 쓰기 충돌 유발), 반드시 `multi_replace_file_content` 단일 호출 하위의 `ReplacementChunks`로 묶어서 처리해야 한다.
- **범위 및 고유성 검증**: `replace_file_content` 호출 전, `StartLine`과 `EndLine` 범위 내에 `TargetContent`가 **정확히 1번**만 나타나는지 검증한다. 지정한 범위 내에 여러 개의 동일 문자열 매치가 존재하거나, 타겟 문자열이 실제 지정 범위 밖에 있으면 에러가 발생한다. 따라서 탐색 범위를 수정하려는 대상을 정확하게 포함하도록 좁게(예: 동일 줄 번호) 설정해야 한다.
- **동일 체크 (TargetContent ≠ ReplacementContent)**: 타겟과 치환 문자열이 서로 동일하면 호출하지 않는다. (도구가 `"No changes to apply"` 에러를 반환하여 루프에 빠질 수 있음).

### 1.1.2 OpenCode (local LLM) Edit Rules (전용)

local LLM(OpenCode) 런타임 환경에서는 `edit` 및 `write` 도구 사용 시 아래 규칙을 반드시 준수한다.

- **edit (부분 수정)**: 기존 파일 수정 시 사용한다. 
  - 필수 인자로 `filePath`, `oldString`, `newString`을 camelCase로 입력해야 한다. (casing 오류 시 `SchemaError` 발생)
  - `filePath`는 절대 경로 형식이어야 하므로, 시스템에서 감지된 워크스페이스 절대 경로를 접두어로 붙여 사용한다.
  - `replaceAll`: 특정 단일 구간을 치환할 때는 **반드시 `replaceAll`을 `false`로 설정**한다. 이를 `true`로 설정하면 파일 전체에서 해당 패턴이 무차별적으로 치환되어 코드베이스가 손상될 위험이 크다.
  - `oldString`은 파일 본문과 공백 및 줄바꿈을 포함하여 완전히 일치(byte-identical)해야 한다.
- **write (신규·전체 쓰기)**: 신규 파일을 생성하거나 전체 내용을 다시 쓸 때만 사용하며, `filePath`와 `contents`를 인자로 받는다.

### 1.1.3 Cursor IDE Edit Rules (전용)

Cursor IDE 런타임 환경에서는 `StrReplace` 및 `Write` 도구 사용 시 아래 규칙을 반드시 준수한다.

- **StrReplace (부분 수정)**: 기존 파일 수정 시 사용하며, `path`, `old_string`, `new_string`을 snake_case 인자로 입력해야 한다.
  - `path`는 프로젝트 루트를 기준으로 한 상대 경로 형식이어야 한다.
  - `old_string`은 파일 내에서 **정확히 1번**만 매칭되어야 한다. 2번 이상 등장할 경우 `Found N matches` 에러가 발생하므로, 탐색 유일성을 위해 구간 블록을 더 넓게 잡거나 unique한 구문이 되도록 조정한다.
- **Write (신규·전체 쓰기)**: 신규 파일 생성 및 전체 덮어쓰기 시 사용하며, `path`와 `contents`를 인자로 받는다.

### 1.2 Patch Preconditions (메타 금지 1·2)

- **Disk State First**: 파일 수정 전 디스크 최신본을 `Read`/`view_file`로 확보한다. 읽기 도구 출력(줄 번호·프롬프트)을 파일 본문이나 치환 대상 문자열(`old_string` / `TargetContent`)에 넣지 않는다.
- **단일 매칭 (유일성 보장)**: `StrReplace`/`edit` / `replace_file_content` 호출 전 대상이 디스크에 존재하고 개수가 정확히 1개여야 한다.
  - Cursor/OpenCode: `assert old_string in content` 및 `assert content.count(old_string) == 1` 만족 필수.
  - Antigravity: `StartLine` ~ `EndLine` 범위 내에서 `TargetContent`가 정확히 1번 매칭되어야 한다.
  - 미충족 시 수정 금지 — 탐색 범위를 축소(줄 번호 범위 좁히기)하거나 `Write`/`write_to_file` 전략으로 전환한다.
- **편집 전 필수 읽기**: `Read`/`view_file` → 디스크 본문에서 치환 대상을 **그대로** 복사(byte-identical, 공백 및 줄바꿈 포함) → 부분 수정 도구 호출.
- **치환 대상과 결과의 차별성 (old ≠ new)**: 치환하려는 원래 문자열과 새 문자열이 동일하면 **도구를 호출하지 않는다** (도구가 `"No changes to apply"` 등을 반환하여 무한 루프를 돌 수 있음).
- **동일 체크 루프 방지**: 호출 전 반드시 `old_string != new_string` (Antigravity의 경우 `TargetContent != ReplacementContent`)을 검증한다. 이미 파일이 목표 상태에 도달해 있다면 편집 단계를 즉시 완료하고 다음 단계로 진행한다.
- **CLI 검증 (선택)**: `just route-gate-check <paths> --file <path> --old-string '<snippet>' [--new-string '<snippet>']` — `old≠new` 및 패턴 1.2 유일성 ([check_old_string.py](../../scripts/error_patterns/check_old_string.py)).

❌✅ 세션 사례·증상별 예시: [error_patterns §1](error_patterns.md#1-파일-편집-실수) lazy-load. AGENTS.md §2.1 pointer는 본 절로 위임한다.

### 1.3 Line Number Safety Rule

라인 번호는 탐색용 정보일 뿐이며 수정 기준이 될 수 없다.

**금지**: `lines[i]` · `lines[i-1]` · `grep -n` 결과만으로 patch · 특정 행 번호 기반 수정.

구조 기반 탐색(`Grep`, `SemanticSearch`, 심볼·블록 단위)을 우선한다.

### Mandatory Behavior
- Always inspect relevant files before proposing modifications (`Read`).
- MUST use the platform-appropriate read/edit tool before quoting or modifying file contents.
- Prefer Shell/`just` for executable verification instead of theoretical assumptions.
- Avoid broad regex/string replacement tools (`sed`, `perl -pi`, `mass replace`) unless explicitly requested. Prefer symbol-aware or AST-aware edits with minimal scoped diffs.
- Never use `sed -i` across multiple files.

### 1.4 Editing Rules (replace / write discipline)
세션의 활성 편집 도구(Cursor `StrReplace` / OpenCode `edit` / Antigravity `replace_file_content` 등)로 저장소를 수정할 때 다음을 **MUST**로 따른다.

1. **No broad retry after pattern failure**: 치환 도구가 패턴 불일치로 실패하면, **더 넓은 old_string / 더 큰 블록 / 더 넓은 라인 범위**로 즉시 재시도하지 않는다.
2. **Failure recovery sequence**: 실패 시 (a) 대상 구간 **재읽기** (b) 치환 범위 및 `StartLine`/`EndLine` **축소** (c) **정확히 일치하는 단일 줄**만으로 재시도한다.
3. **No automatic tool hopping**: 한 도구 실패만으로 부분 수정 도구 ↔ 전체 쓰기 도구(`Write` / `write_to_file`)를 **자동 전환하지 않는다**. 전환은 재읽기·원인 파악 후 **명시적 판단**이 있을 때만 수행한다.
4. **Validate parameters first**: 도구 호출 전 (a) 대상 파일 최신본 확인 (b) 치환 대상이 디스크 본문에 존재 (c) **치환 대상 ≠ 치환 결과** (동일할 시 호출 금지) (d) 스키마 필수 매개변수·타입 검증. 누락·오류 상태로 호출하지 않는다.
5. **신규 vs 부분 수정 분기**: 
  - 신규 파일 및 전체 재작성 → `Write` / `write` / `write_to_file`
  - 단일 연속 블록 수정 → `StrReplace` / `edit` / `replace_file_content`
  - 비연속 다중 블록 수정(Antigravity) → `multi_replace_file_content` (병렬 개별 호출 절대 금지)
  - 대형 블록이나 파일 전체를 덮어쓰는 것은 최후의 수단으로 제한한다.

**MUST NOT**
- 패턴 실패 직후 "혹시 모르니" 전체 파일 쓰기 도구(`Write`/`write_to_file`)로 덮어쓰기.
- 디스크 재읽기 없이 추측 치환 대상 문자열로 연속 수정 시도.
- 동일 실패에 대해 서로 다른 편집 도구를 무작위 순환 호출.

**Reasoning Policy:**
- Prioritize root-cause analysis over workarounds.
- Verify assumptions through tools whenever possible.
- Avoid hallucinating APIs, file paths, configs, or command outputs.
- When uncertain, inspect first rather than infer.

### Repeated Tool Failure Rule (extends Editing Rules)

동일한 도구 호출 + 동일한 에러 + 2회 반복 → **retry 금지**

```
same tool + same args + same non-transient error + 2 occurrences
=> retry prohibited
   (unless Editing Rules recovery path is exhausted)
```

**Required next steps:**

1. inspect arguments (verify required fields are populated)
2. inspect schema (check field names, types)
3. compare behavior across action variants of same tool
4. generate root-cause hypothesis (adapter defect, server validation, etc.)
5. alternative workflow (e.g., `Write` for new file)

Applies to all tool calls, not just file edits.

**예시:**

```
ToolFoo(action='patch', id='x') → Not found
ToolFoo(action='patch', id='x') → Not found

=> retry prohibited
=> inspect: why does id become ''?
=> compare: alternate action variant with same id → OK?
=> hypothesis: adapter/implementation defect for action='patch'
=> strategy: use session-native partial-edit tool ([runtime_edit_tools.md §1](./runtime_edit_tools.md)), or report to user
```

### Terminal Response Rule (무한 루프 방지)

특정 도구 응답은 **재시도가 아닌 종료 신호**이다. 이 응답을 보고 동일 도구를 다시 호출하면 무한 루프가 발생한다.

**터미널/도구 응답 3종** (재시도 금지, 즉시 중단):

| 응답 | 도구 | 행동 |
|------|------|------|
| `"No changes to apply: oldString and newString are identical"` 또는 변화 없음 에러 | `StrReplace`/`edit`/`replace_file_content` | **동일 old/new (Target/Replacement) 재호출 금지** → `Read`/`view_file` → 목표 내용 있으면 완료·없으면 입력값/범위 중 하나 변경 후 edit 1회 (아래 분기) |
| `"PASS"` (lint/test/verify) | `just plan-lint`, `pytest`, `just route-gate-check` 등 | 게이트 통과. 다음 단계로 진행. |
| 동일 stdout 재출력 (bash) | `bash` | 명령이 이미 성공했거나 상태 변경 없음. 다음 작업으로 진행. |

```
❌ WRONG: 터미널/도구 응답을 재시도 신호로 해석
StrReplace(old_string="status: handed-off", new_string="status: handed-off")
# → "No changes to apply: oldString and newString are identical"
StrReplace(old_string="status: handed-off", new_string="status: handed-off")
# → 같은 에러 (무한 루프)

❌ WRONG: Antigravity replace_file_content 동일 호출
replace_file_content(TargetContent="status: handed-off", ReplacementContent="status: handed-off", ...)
# → "No changes to apply" 계열 혹은 변화 없음 에러
replace_file_content(TargetContent="status: handed-off", ReplacementContent="status: handed-off", ...)
# → 무한 루프

✅ CORRECT: "No changes to apply" 분기 (동일 쌍 재호출 금지)
Read(path) / view_file(TargetFile)  # 디스크 재확인
# 목표 내용이 이미 있으면 → 편집 완료, 다음 단계
# 없으면 → old_string(TargetContent)·범위·new_string(ReplacementContent) 중 하나 이상 변경 후 1회 시도

✅ CORRECT: 기타 터미널 종료 신호
# "PASS" → 게이트 통과, 다음 Task로 진행
# 동일 stdout 재출력 → 상태 변경 없음, 다음 작업으로 진행
```

**`"No changes to apply"` (또는 동등한 변화 없음 상태) 수신 시 분기** (normative):

1. 같은 입력값(`old_string`/`new_string` 또는 `TargetContent`/`ReplacementContent`)으로 **재호출하지 않는다**.
2. `Read`/`view_file`로 파일을 다시 확인한다.
3. 목표 내용이 **이미 있으면** → 편집 완료 처리, 다음 단계.
4. **없으면** → 입력값·범위 중 하나 이상을 바꿔 **새 편집 1회**만 시도 (동일 쌍 재시도 금지).

**부분 수정 도구 호출 전 필수 검증** (precondition):

1. `Read`/`view_file`로 파일 최신본 확보.
2. 치환 대상이 디스크/지정 범위에 **정확히 1번** 등장하는지 확인.
   - Cursor/OpenCode: `content.count(old_string) == 1`
   - Antigravity: `StartLine` ~ `EndLine` 범위 내에 `TargetContent`가 **정확히 1번** 존재.
3. **치환 대상 ≠ 치환 결과** (Cursor/OpenCode: `old_string != new_string`, Antigravity: `TargetContent != ReplacementContent`) — 동일하면 호출 금지, 다음 단계 진행.
4. 한글/인코딩 문제 시 `edit`/`replace_file_content` 대신 `bash` + `cat << 'EOF'` 또는 `python3 -c` 사용.

**규범**: [error_patterns.md §메타 금지 8-9](error_patterns.md) — 동일 입력 무한 재시도 금지, 터미널 응답 종료 신호 인식.

### Successful Variant Comparison

동일 도구의 다른 action 이 성공했다면, 먼저 "내 프롬프트 문제"보다
"tool 구현 차이"를 의심합니다.

```
tool X(action='A') → 성공
tool X(action='B') → 실패

=> 내 argument 가 잘못된 것이 아님
=> action B 의 구현에 특수 조건이 있을 가능성 높음
```

**Action:**

1. 성공한 action 과 실패한 action 의 차이 확인
2. 실패한 action 의 스키마/필수 인자 재확인
3. 동일 argument 로 다른 action 이 성공했다면 retry 하지 말고 대체 action 사용

---

## 2. Context Route Gate (편집 전 강제, IDE 공통)

**적용**: 저장소 내 파일을 **생성·수정·삭제**하기 전. (Read-only 조사·`just route` 자체 실행은 제외.)

**금지 (정책 위반)**:
- `just route` 없이 도메인 규칙·베스트 프랙티스 스킬을 "알고 있다"고 가정하고 패치하는 것
- `must_read` 일부만 읽고 나머지를 생략하는 것
- `must_read` 미완료 상태에서 완료 선언·PR 제출

**필수 절차 (순서 고정)**:
1. 이번 턴에 건드릴 **모든** 대상 경로를 repo-relative 로 나열한다.
2. 터미널에서 실행한다 (`route` 직후에 `--` 넣지 않음):
   ```bash
   just route <path1> <path2> ... --write-manifest
   ```
3. 터미널 **`[Next Action for Agent]`** 블록을 **JSON 파싱 없이 순서대로 복붙 실행**한다:
   - **`just route-read …`** — 나열된 must_read 경로를 Read 직후 1회 실행
   - **`just route-gate-check <paths>`** — exit 0 확인 후에만 호스트 쓰기·부분 수정·삭제 ([runtime_edit_tools.md §1](./runtime_edit_tools.md))
   - **lazy Read 각주** — Next Action 블록 하단 2줄을 따른다. 상세: [.agents/registry/CONTEXT_ROUTING.md](../registry/CONTEXT_ROUTING.md) 「2단계 스킬 lazy-load」
4. 의도(리뷰·리팩터·UI 등)가 있으면 `--intent` 를 붙인다. 예: `just route src/foo.tsx --intent 리뷰 --write-manifest`

### 초경량·의도 라우팅 (선택)
- `just route <paths> --tight` — Always Load 생략, 프로젝트 스킬 cap=2.
- `just route-smart '<query>' <paths>` 또는 `python3 scripts/agent/route_smart.py "<query>" <paths>` — 쿼리 의도 분류 + 짧은 쿼리 시 tight 자동 제안. 쿼리에 공백이 있으면 **쉘에서 쿼리 전체를 한 인자로** 인용한다.

### 해석 SSOT
- 도메인 규칙: [.agents/registry/CONTEXT_ROUTING.md](../registry/CONTEXT_ROUTING.md)
- 프로젝트 스킬: [.agents/registry/PROJECT_SKILL_ROUTING.json](../registry/PROJECT_SKILL_ROUTING.json)
- 엔진: `scripts/agent/route_context.py` (`get_route_bundle`)

### 검증
편집 직전 턴 로그에 `just route` 출력(가이드라인) 또는 `must_read_paths` 목록이 있어야 한다. 없으면 게이트 미통과.

### 세션 매니페스트 (멀티 에이전트·IDE 공통, SSOT: `scripts/agent/route_gate.py`)
Cursor 훅이 아닌 **`just` 명령**으로 "필독 완료"를 기록·검증한다. 매니페스트 기본 경로: `.agent/route/session-manifest.json` (gitignore). 환경 변수: `ROUTE_MANIFEST_PATH`, `ROUTE_SESSION_KEY`, `ROUTE_AGENT_ID`.

| 시점 | 명령 (예) |
| :--- | :--- |
| **첫 턴** (선읽기) | `just route-smart '<사용자 메시지 요약>' <paths…> --full --write-manifest --phase turn1` |
| **편집 준비** | `just route-prep <paths>` (= `route … --write-manifest --phase pre_edit`) |
| **턴 종료** | `just route-gate-check-touched` — git 변경 경로에 대해 manifest 검증(매니페스트 없으면 skip). `ROUTE_GATE_SKIP=1` 로 생략. 편집 경로 합집합이 마지막 번들과 다를 때 live route heal 을 실행하고, stale 즉시 차단 대신 `healed` 플래그와 Δmust_read 만 반환한다. |

- **질문·심문·리뷰만**(저장소 미편집): `route-gate-check` **호출하지 않음**.
- **실패(exit 1)**: 해당 턴에서 편집 도구 중단; 누락 경로를 Read 한 뒤 `route-read` 재실행.
- **상태 확인**: `just route-manifest-status`
- **Renderer TSX**: `apps/renderer/**/*.tsx` 편집 시 lazy `detail_path` 도 gate 대상(자동).
- **번들 heal**: 편집 경로 집합이 바뀌면 `route-gate-check` 가 **live route** 로 번들을 자동 갱신하고, **현재 번들의 `reads`** 에 없는 must_read 만 추가로 요구한다(stale 즉시 차단 없음). 세션 `all_reads` 만으로는 통과하지 않는다.
- **편집 직전 strict**: `route-gate-check` 통과에는 **해당 편집 경로의 pre_edit 번들**에 `route-read` 기록이 있어야 한다. 번들이 없거나 번들 `reads` 가 비어 있으면 FAIL이며, session-reads-only 우회는 없다.

---

## 3. File Access Priority

1. **Built-in File I/O**: `Read` / `Write` / `StrReplace` / `Grep` / `Glob` / `SemanticSearch`. 부분 수정은 §1.1 `StrReplace` + `old_string`.
2. **Command orchestration**: Justfile (`just <command>`)을 통해 복잡한 쉘 파이프라인 및 도구 체인을 추상화해 실행한다. (권장)
3. **Shell direct**: batch / system-level / permissions 필요 시에만 직접 호출한다.
