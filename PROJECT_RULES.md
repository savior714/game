# PROJECT_RULES.md — AidenGame 프로젝트 정책

작업 절차는 `AGENTS.md`를 따른다. 이 문서는 제품·아키텍처·품질 경계만 정의한다.

## 1. 제품 목적

AidenGame은 어린이를 위한 정적 웹 기반 학습 게임 플랫폼이다. 단순한 학습 흐름, 즉각적인 피드백, 성취감, 보호자 통제를 우선한다.

## 2. 런타임과 경로

| 역할 | 경로 |
|---|---|
| 메인 허브 | `index.html` |
| 공용 스타일 | `styles.css` |
| 과목별 게임 | `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/` |
| 지원 도메인 | `domains/reward/`, `domains/auth/`, `domains/sync/` |
| 공용 로직 | `shared/domain/`, `shared/ui/`, `shared/event-bus.js` |
| 실험 | `experiments/` |
| 보호자·관리 | `guardian/`, `admin/` |
| 테스트 | `tests/` |
| 검증 | `verify.sh`, `scripts/`, `tools/` |

- 신규 UI와 로직은 가장 가까운 기능 디렉터리에 둔다.
- 여러 과목이 공유하는 로직만 `shared/`로 올린다.
- 실험은 안정화 전까지 `experiments/`에 격리한다.
- 빈 `src/`를 새 runtime SSOT로 사용하지 않는다.
- Next.js, Tauri, 별도 백엔드 API는 현재 범위에 추가하지 않는다.
- generated artifact와 authoring source를 구분한다.
- Ocean Rescue는 가장 가까운 technical spec을 따른다.

## 3. 기술 스택

- 사용자 런타임: HTML, CSS, JavaScript
- 배포: `vercel.json` 기반 정적 호스팅
- 검증 도구: Python, `uv`, `just`, Ruff, type checker, Pytest
- Ocean Rescue build tooling은 해당 경로의 lockfile과 spec이 authority다.
- dependency·toolchain upgrade는 별도 coherent package로 수행한다.

## 4. 개발·배포

- 통합·게시 기준 브랜치는 `origin/main`이다.
- `main` fast-forward push가 기본이다.
- PR·feature branch는 요청 시에만 사용한다.
- 일반 작업은 안정적인 프로젝트 전용 경로의 isolated worktree에서 reservation 없이 병렬 실행한다.
- source checkout/worktree는 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 하위에 만들지 않는다.
- 기본 worktree root는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`이며, 실제 저장소가 다른 개발 루트에 있으면 같은 상위 디렉터리의 안정적인 `.worktrees/game/<task-slug>` sibling 경로를 사용한다.
- VS Code·OpenCode·LSP·`uv`·`pnpm`·Docker·브라우저 E2E·generated artifact 검증은 모두 실제 작업 worktree 하나를 동일한 workspace root와 CWD로 사용한다. main checkout, worktree, symlink alias, `/tmp`와 `/private/tmp` 경로를 혼합하지 않는다.
- OS temp는 prompt transport, patch/diff, 다운로드·압축 해제, 테스트 fixture와 폐기 가능한 비소스 산출물에만 사용한다. 그 안의 source tree를 LSP나 프로젝트 실행 루트로 사용하지 않는다.
- hotspot·runtime identity·generated artifact처럼 충돌 비용이 큰 자원만 `agents/workflows/work-package-claim.md`로 예약한다.
- 게시 직전 최신 main에 재적용하고 focused verification과 정적 진단 closure를 다시 실행한다.
- generated artifact는 source of truth와 build pipeline을 통해 갱신한다.
- 원격 상태나 필수 검증이 불명확하면 publish하지 않는다.
- 게시 또는 중단 후 자신이 만든 worktree만 제거하고 `git worktree prune`을 실행한다.

## 5. 품질

- work package는 coherent objective와 rollback 경계를 가진다.
- 강하게 결합된 source, caller, test, asset, config는 함께 변경할 수 있다.
- 하나의 failure domain·가설·binary criterion을 모든 제품 작업에 형식적으로 강제하지 않는다.
- 다만 서로 다른 LSP·typecheck·lint 원인은 한 패치에 섞지 않고, 하나의 failure domain을 수정·독립 검증한 뒤 다음 failure domain으로 이동한다.
- unrelated product cleanup은 포함하지 않는다.
- 새 검증은 잡아낼 구체적 failure mode가 있을 때만 추가한다.
- full-suite는 실제 회귀 위험이나 cutover가 요구할 때만 실행한다.

### 5.1 정적 진단 closure

- 작업 시작 시 안정적인 worktree root에서 관련 LSP·typecheck·lint baseline을 확인한다.
- 현재 변경으로 새로 생긴 오류와 수정 파일·직접 영향 모듈의 오류는 현재 package에서 반드시 수정한다.
- 저장소 정적 게이트가 다른 기존 오류를 드러내면 현재 원인과 섞어 대규모 수정하지 않는다. 현재 failure domain을 같은 진단으로 독립 검증한 뒤 다음 정적 failure domain 하나를 선택해 순차 해결한다.
- 잘못된 workspace root, SDK/interpreter, 누락된 의존성, stale cache/index, generated/vendor 오분석이 원인이면 production code를 억지로 바꾸지 않고 환경·설정을 수정한 뒤 동일 진단을 재실행한다.
- broad ignore, `type: ignore`, `noqa`, ESLint disable, 검사 대상 축소, baseline·snapshot 갱신으로 녹색을 만들지 않는다.
- LSP·typecheck·lint 오류를 “pre-existing” 또는 “out of scope”라는 이유만으로 보고하고 PASS하지 않는다.
- 최종 PASS는 현재 변경과 직접 영향 범위의 정적 오류가 0이고 이번 작업에 요구되는 저장소 정적 게이트가 통과한 경우에만 허용한다. 안전하게 해결할 수 없는 정적 오류가 남으면 정확한 재현 명령과 원인을 포함해 `BLOCKED`로 보고한다.

대표 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

## 6. 사용자 경험

- 어린이가 이해할 수 있는 짧고 명확한 문구를 사용한다.
- 실패보다 재시도와 성취 피드백을 강조한다.
- 터치 환경과 작은 화면을 기본으로 고려한다.
- 핵심 흐름은 키보드와 보조 기술로도 사용할 수 있어야 한다.
- 시각 효과가 조작과 가독성을 방해하지 않게 한다.

## 7. 보안

- API 키, 토큰, 쿠키, `.env` 원문을 노출하지 않는다.
- 인증·동기화·보호자 기능은 권한이 불명확할 때 fail-closed한다.
- 외부 입력을 검증하고 안전한 DOM API를 사용한다.

## 8. 문서

| 목적 | SSOT |
|---|---|
| 실행 규약 | `AGENTS.md` |
| 프로젝트 정책 | `PROJECT_RULES.md` |
| exclusive reservation | `agents/workflows/work-package-claim.md` + Issue #1 |
| Git·publish | `agents/workflows/git.md` |
| 요구사항·회귀 | `tests/` |
| 배포 | `vercel.json`과 실제 entry |
| 기능 설계 | 대상 기능에 가장 가까운 `docs/` 문서 |

과거 Plan·Blueprint 상태 관리와 coordination 문서가 제품 변경보다 우선하지 않는다.
