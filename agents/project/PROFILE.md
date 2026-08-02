# Project Profile — AidenGame

이 파일은 **project-owned overlay**다.
초기 생성 후 프로젝트가 직접 관리하며 Copier update가 기존 내용을 덮어쓰지 않는다.

## Identity

- Project name: `AidenGame`
- Project slug: `game`
- Canonical branch: `main`
- Package/build tool: `uv`

## Commands

이 section 이 프로젝트 실행 command 의 유일한 SSOT 다.
.agent-harness.yml 은 실행 command authority 가 아니다.

- Lint: `ruff check . && ruff format --check .`
- Typecheck: `ty . || pyright .`
- Targeted test: `uv run pytest tests`
- Release check: `just verify`

`NOT_CONFIGURED` command를 추측해서 실행하지 않는다.
실제 저장소 config를 확인한 뒤 이 파일을 갱신한다.

## Capabilities

- Runtime visual: `false`
- Database: `false`
- Content provenance: `false`
- Regulated domain: `false`

## Project-specific additions

AidenGame은 어린이를 위한 정적 웹 기반 학습 게임 플랫폼이다.

- 실제 디렉터리와 subsystem 경계:
  - 메인 허브: `index.html`
  - 과목별 게임: `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/`
  - 지원 도메인: `domains/reward/`, `domains/auth/`, `domains/sync/`
  - 공용 로직: `shared/domain/`, `shared/ui/`, `shared/event-bus.js`
  - 실험 기능: `experiments/`
  - 보호자 기능: `guardian/`
  - 관리 기능: `admin/`
  - 테스트: `tests/`
- 인증·DB·배포 구조: 정적 프로젝트 (Next.js, Tauri, 백엔드 API 없음)
- 고위험 도메인: 없음
- 추가 targeted validation: 없음
- 프로젝트에서만 적용되는 금지사항:
  - 빈 `src/` 디렉터리를 새로운 런타임 SSOT로 사용하지 않는다.
  - 현재 범위에 Next.js, Tauri, 별도 백엔드 API를 추가하지 않는다.
