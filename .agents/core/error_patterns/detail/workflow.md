---
scope: detail
domain: core
parent: .agents/core/error_patterns.md
lazy_load: true
---
<!-- Language: ko -->

## 6. 기타 실수

### 6.1 mermaid/긴 표/로드맵 금지 (discuss 워크플로)

discuss 세션에서 mermaid·긴 표·로드맵 금지. **규칙 SSOT**: [discuss/SKILL.md](../../../skills/discuss/SKILL.md) §철칙. 불릿 A/B만 사용.

### 6.2 AskQuestion/`question`(병용) 없이 close 종료

**증상**: "정리" 또는 "끝" 으로 턴 종료 — AskQuestion(`question` 병용) 미사용.

**원인**: discuss SKILL close 규칙 위반.

**사례**: `"정리 완료"` → 턴 끝.

**해결**: AskQuestion(`question` 병용) 으로 표준 메뉴 A/B (discuss SKILL §close).

### 6.3 MEMORY.md에 임시 정보 저장

**증상**: MEMORY.md에 PR 번호, 커밋 해시, "Phase N 완료" 같은 임시 정보를 기록함.

**원인**: MEMORY.md는 장기 메모리용이지 작업 로그가 아님.

```
❌ WRONG: MEMORY.md에 임시 정보 저장
"PR #123 제출함"
"Phase 2 완료"
"파일 50개 수정"

✅ CORRECT: session_search로 검색 가능하게
session_search(query="PR 123")  # → 과거 세션에서 검색 가능
```

### 6.4 converge «계획으로» 직후 Blueprint 재질문 (이중 handoff)

**증상**: «계획»·`direction-set` 후 Blueprint `AskQuestion`/`question`(병용) 재노출.
**해결**: same-session plan 직행(메뉴 A 생략) → plan-lint 후 메뉴 B. discuss SKILL §턴 판별.

### 6.5 direction·polish 턴에서 Blueprint·메뉴 A 조기 권장

**증상**: 결정 1~2개만 쌓였거나 §3·Ambiguity-Zero를 채운 직후, close 트리거 없이 「방향과 범위는 맞춰 두었습니다」+ **실행 계획(Blueprint) `(권장)`** 또는 `status: direction-set` 갱신.

**원인**: (1) plain-language 메뉴 A 본문 예시를 **close 전제 없이** direction 턴에 복붙. (2) §3 갱신 = close로 착각. (3) Anti-rush(철칙 0)와 close 메뉴 A(Blueprint 필수 권장) 규칙을 **턴 판별 없이** 동시 적용.

**사례**: CI 방향 합의 후 노트 `direction-set` + `AskQuestion(Blueprint 권장)` — 사용자는 아직 converge·예외 논의 중.

```
❌ WRONG: §3 채움 → status direction-set → "방향 확정 → Blueprint (권장)"
❌ WRONG: direction 턴 — "원인 정리됐습니다. 다음은 Blueprint (권장)?"

✅ CORRECT: direction — status discussing 유지, 다음 분기 AskQuestion(`question` 병용) (Blueprint 언급 없음)
✅ CORRECT: converge — «{예외·오프라인} 더 논의» (권장); «계획으로»는 (권장) 아님
✅ CORRECT: converge «계획» 선택 → same-session plan 직행 (메뉴 A 생략) → 메뉴 B
✅ CORRECT: 텍스트 close ("끝" 등) → 메뉴 A Blueprint (권장)
```

**해결**: discuss SKILL §**턴 판별 결정 트리** — close 트리거 없으면 Blueprint·메뉴 A 금지. `direction-set`은 close 1단계에서만.

### 6.6 Workaround(우회책) 사용 후 근본 원인 및 대안 보고 누락

**증상**: 원래 계획했던 방식을 우회하여 문제를 해결한 뒤, "완료되었습니다"라고만 보고하고 세션을 종료/이관함.

**원인**: `principles.md`의 Workaround Accountability 지침 위반. 임시방편(우회책)으로 문제를 덮고 넘어가 기술 부채를 유발함.

**사례**: "A 시도 중 오류가 발생하여 B 방식으로 우회 처리했습니다. 다음 작업을 진행할까요?" (원인 분석 및 향후 해결 방안 질문 없음)

**해결**: 세션/대화 종료 시 발생한 문제, 우회책 내용, 추정되는 근본 원인(Root Cause), 이를 해결할 향후 대안(Future Resolution)을 반드시 사용자에게 보고하고(`AskQuestion`/`question`(병용) 활용) 조치를 논의해야 함.

### 6.7 AskQuestion(`question` 병용) 스킵 후 텍스트 답 무시·무한 재질문

**증상**: 사용자가 채팅으로 A/B/옵션 이름을 답했는데 `Questions skipped by the user`만 보고 동일 `AskQuestion`/`question`(병용)을 반복하거나, 매핑 없이 다음 분기로 추진함.

**원인**: Cursor UI가 채팅 전송 시 대기 중 질문 카드를 닫음. discuss SKILL이 스킵을 «답 없음»으로만 처리.

```
❌ WRONG: 스킵 → «동일 질문 재시도 예정» → 사용자가 이미 «B»라고 타이핑했는데 또 카드
❌ WRONG: 스킵 → route 맥락만으로 (권장) 옵션 확정

✅ CORRECT: 스킵 + 사용자 «B» → pending_ask 옵션 b 매핑 → [확정] 기록 → 다음 분기
✅ CORRECT: 스킵 + 모호한 서술 → 2지 확인 AskQuestion(`question` 병용) 1회만
✅ CORRECT: 스킵 + 매핑 실패 → 입력 안내 + 동일 질문 1회 재시도
```

**해결**: discuss SKILL §**채팅 텍스트 답변 수용**·§**AskQuestion(`question` 병용) 스킵 시**·DISCUSS `pending_ask`. [principles.md](../../principles.md) §1.1.1 항 8.

---


---

## 16. 프롬프트 라우팅 실패

### 16.1 워크플로 실행 요청 시 파일 Read 누락 → 동일 도구 무한 반복

**증상**: 사용자가 "~ workflow 돌려줘" 요청 시 에이전트가 .agents/workflows/<name>.md 를 먼저 Read 하지 않고, 추측으로 도구 호출 → 실패 → 동일 도구 + 동일 인자 반복.

**원인**: AGENTS.md §2.3 "실패 후 동일 입력 금지" 및 워크플로 Read 누락 ([error_patterns.md](../../error_patterns.md) TOP 7) 위반.

**대응**: 워크플로·스킬 실행 요청 수신 시 **Read** 도구로 `.agents/workflows/<name>.md` 또는 `.agents/skills/<name>/SKILL.md`를 1회 읽기 → 핵심 단계 추출 → 단계별 실행. frontmatter `trigger:`는 색인 메타일 뿐 자동 실행되지 않음. 동일 도구 3회 반복 시 즉시 중단 + 전략 전환.

### 16.2 텍스트 툴 마커 오용 → 호스트 파싱 실패·턴 정지

**증상**: 어시스턴트 **content·reasoning**에 tool 호출을 텍스트 마커·XML·JSON 조각으로 쓰면, 호스트가 structured tool로 인식하지 못해 **실행 0건**으로 턴이 끝남.

**원인**: Claude Code·Hermes·SFT 로그 등에서 본 **텍스트 tool syntax**를 현재 호스트 native API에 그대로 적용함.

| 환경 | 실행 경로 |
| :--- | :--- |
| **Cursor** | 내장 `tool_use` / MCP structured tool call |
| **공통 금지** | content·reasoning에 tool syntax 텍스트 출력 |

```
❌ WRONG: content/reasoning에 tool 마커·XML·pseudo JSON (어느 호스트든 미실행)
   - [TOOL_REQUEST] / [END_TOOL_REQUEST] bracket 태그 + JSON payload
   - <function=…>, <tool_call>, Hermes invoke XML
   - {"name":"bash","arguments":{…}} 만 단독 출력

✅ CORRECT: 호스트가 제공하는 native structured tool API만 호출
   - Cursor: Read/Shell/AskQuestion·question 등 tool call 도구(병용)
   - 도구 불가 시: [principles.md](../../principles.md) §1.1 마크다운 A/B/C fallback (XML·마커 금지)
```

**대응**: 텍스트 tool 마커 일체 금지. normative: [principles.md](../../principles.md) §1.1 · [error_patterns.md](../../error_patterns.md) TOP 6.

---
