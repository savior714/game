# PROJECT_RULES.md — Policy Hub

## 0. Purpose
본 문서는 AidenGame 프로젝트 정책·스택·품질·아키텍처 제약(What)을 정의한다.
에이전트 실행 방식은 `AGENTS.md`를 따르며, 부트스트랩 코어 규칙은 `.agents/core/`를 따른다.

---
# 1. Architecture Rules
- **런타임 SSOT**: 사용자 화면은 루트 및 과목·실험 디렉터리의 정적 HTML/JS/CSS에 작성한다.
  - 메인 허브: `index.html`
  - 과목: `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/`
  - 실험: `experiments/space-explorer/`, `experiments/marble/` 등
  - 공용 로직: `shared/domain/`, `shared/ui/`
  - 지원 도메인: `domains/reward/`, `domains/auth/`, `domains/sync/`
- **배포**: `vercel.json` 기준 정적 호스팅. 로컬 미리보기는 정적 서버(예: `python3 -m http.server 8080`).

---
# 2. Stack & Runtime Policy
- **Language**: HTML/CSS/JavaScript (브라우저 런타임), Python (검증·테스트)
- **Package / env**: `uv`, `nix` (선택), `just`, `ruff`, `pytest`, `ty`/`pyright`
- **에이전트 거버넌스**: bootstrap kernel — `AGENTS.md`, `.agents/core/`, `.agents/registry/`

## 2.1 Client & Distribution MUST
- 신규·리팩터 UI는 해당 과목·실험 폴더 또는 루트 엔트리 HTML에만 추가한다.
- Next.js·Tauri·백엔드 API 스택은 **본 프로젝트 범위 밖**이다.
- 로컬 dev URL 참고값: `http://127.0.0.1:8080`

---
# 3. Verification & Quality Policy
- **TDD Red-First**: 구현 전 실패 테스트 — `tests/` 계약 우선.
- **Strict Lint**: `ruff check` / `ruff format --check` 통과 필수.
- **Code Quality Lifecycle**: [.agents/core/code_quality_lifecycle.md](.agents/core/code_quality_lifecycle.md)
- **Risky Operations (HITL)**: 삭제·배포·`git push` 등은 사용자 승인 후 실행.
- **Information Integrity & Honesty**: [.agents/core/execution.md](.agents/core/execution.md) §2.10

---
# 4. Security Policy
### 4.1 에이전트·채널 시크릿 (ZERO-LEAK)
에이전트·자동화 출력으로 API 키·토큰·`.env` 값 원문 노출을 **절대 금지**한다.
실행 절차 SSOT: [.agents/core/execution.md](.agents/core/execution.md) §2.9

---
# 5. Documentation & Communication
- 한국어 우선. 세션 핸드오프: `docs/agent-context/memory/MEMORY.md`
- 설계·스펙: `docs/`

---
# 6. SSOT Hub
| Purpose | SSOT |
|---|---|
| Project overview | `README.md` |
| Execution protocol | `AGENTS.md` |
| Project policy | `PROJECT_RULES.md` |
| Requirements contract | `tests/` |
| Session memory | `docs/agent-context/memory/MEMORY.md` |
| Rule registry | [.agents/registry/RULE_INDEX.md](.agents/registry/RULE_INDEX.md) |
