---
situation: "버그 및 성능 회귀 진단"
# trigger: /diagnose  ← catalog metadata only; Read this file before executing (error_patterns §16.1)
level: Recommended
description: "Matt Pocock diagnose 스킬 — 6단계 진단 루프: reproduce → minimise → hypothesise → instrument → fix → regression-test"
version: 1.0.0
last_updated: 2026-05-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Diagnose (`/diagnose`)

**프로토콜 SSOT**: [.agents/skills/diagnose/SKILL.md](../skills/diagnose/SKILL.md) — 실행 전 Read 후 Phase 1~6을 따른다.

## 언어 정책 (MUST)

- `/diagnose` 세션의 **모든 채팅 응답은 한국어**로 작성한다.
- Phase별 진행 보고·가설·근본 원인·수정·사후 분석 형식도 한국어 섹션 제목·본문을 따른다.
- 코드·로그·경로·식별자는 영문 유지 가능. **영문-only 단락·결론은 금지**.
- SSOT: 스킬 본문 **Response Language (MUST)**, [markdown.md](../domains/documentation/markdown.md) Korean First Policy.

## AidenGame 부록

- 코드베이스 탐색 시 **도메인 용어·ADR**: `docs/specs/`, `docs/plans/adr/` 등을 스킬의 “glossary / ADR” 지침에 맞춰 조회한다.
- HITL 루프 템플릿이 필요하면 `scripts/hitl-loop.template.sh`(스킬 Phase 1 항목 10) 존재 여부를 디스크로 확인한다.
- **Format mismatch / opaque API errors**: 파싱 실패(str vs dict 등) 시 원문 확인 순서 —
  1. `just api-response-errors` — `var/log/emr/hub/api_response_errors.jsonl`
  2. `just raw-logs` — `api_log.jsonl`, `tool_log.jsonl`
  3. 추측 캐스팅·타입 가드 추가 **전** raw body 확보 (Phase 3 instrument).
- **Phase 6 직후**: 라우트·`next.config`·`proxy.ts`·`src/app/**`·인증/프록시를 건드렸다면 **[`/spec-sync`](sync.md)** 를 **필수** 실행한다 (`just renderer-route-smoke` 포함). 이후 해결된 문제가 반복되거나 온보딩 가치가 있다면 `knowledge-asset` 스킬(`../skills/knowledge-asset/SKILL.md`)을 읽어 자산화를 검토한다.

## Anti-pattern at write (요약)

- **증상**: 재현 없이 추측 패치, 로그 없는 "원인 확정", 수정 후 회귀 테스트 누락.
- **원인**: diagnose 6단계(reproduce → minimise → hypothesise → instrument → fix → regression-test) 순서 미준수.
- ❌ WRONG: "아마 이거" 가설만으로 바로 코드 변경 후 종료 보고.
- ✅ CORRECT: 재현 증거와 계측 결과를 먼저 확보하고, 수정 뒤 동일 경로 회귀 테스트까지 확인.
- 공통 포맷 SSOT: [`docs/agent-context/ANTI_PATTERN_FORMAT.md`](../../docs/agent-context/ANTI_PATTERN_FORMAT.md)
