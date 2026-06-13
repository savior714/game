---
id: MEMORY
type: MEM
status: active
last_verified: 2026-06-12
---

# Memory

**SSOT**: `docs/agent-context/memory/MEMORY.md` · 규정: [memory_hygiene.md](../../../.agents/core/memory_hygiene.md) (≤200줄)

---

- **Last update**: 2026-06-12
- **Scope**: bootstrap — `.agents/` 시스템 도입, `docs/memory/` 구버전 정리

## Done
- `.agents/core/memory_hygiene.md` — 메모리 위생 규정 수립
- `AGENTS.md` / `PROJECT_RULES.md` — `docs/agent-context/memory/MEMORY.md` 참조로 전환
- `.cursor/rules/` 삭제 (Cursor 전용 규칙 제거)
- Windows 레거시 문서 정리 — `CRITICAL_LOGIC.md`, `VIBE_CODING_PROTOCOL.md` 삭제; `go.md`/`archive.md`에서 구 결정 SSOT 제거; TS 문서 macOS·`.agents/core` 기준으로 갱신

## In progress / Blocked
- (없음)

## Next
- 실제 작업 루프에 맞춰 Scope·Done·Next 갱신
- `just memory-verify`로 주기적 위생 점검

## Refs
- branch: (로컬 기준)
- verify: `just memory-verify`
