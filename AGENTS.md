# AGENTS.md — AidenGame 저장소 계약

이 문서는 AidenGame 저장소에만 해당하는 계약만 담는다. 일반적인 에이전트 행동은 시스템 프롬프트를 따른다.

## 1. 적용 순서

1. 사용자의 현재 요청
2. 이 문서
3. `PROJECT_RULES.md`와 대상 기능의 가장 가까운 technical spec
4. 최신 `origin/main`의 코드·테스트·설정

과거 계획과 완료 보고를 현재 상태의 근거로 사용하지 않는다.

## 2. WP 계획과 상태

- `WP-33E` 같은 이름은 대화와 실행 보고에서 사용하는 작업 라벨이다.
- 사용자가 저장소 문서화를 명시적으로 요청하지 않는 한 WP 계획·다음 WP·진행 상태·완료 상태는 대화에서만 관리한다.
- 일반 WP 작업을 위해 `docs/plans/PLAN_ocean_rescue_wp*.md` 또는 상태 전용 `docs/evidence/` 문서를 생성·수정하지 않는다.
- 테스트는 제품 동작·타입·빌드·배포 계약을 검증하며 `다음 WP`, `현재 WP`, `WP COMPLETE` 같은 일정 상태를 검증하지 않는다.
- 기존 migration plan과 과거 WP 문서는 참고 자료일 뿐 현재 일정의 권위가 아니다.
- Blueprint 절차는 사용자가 저장소 Blueprint를 명시적으로 요청한 경우에만 적용한다.

## 3. Git과 workspace

- 통합·게시 기준은 `origin/main`이며 기본 게시 방식은 `main` fast-forward push다. PR·feature branch는 사용자가 요청한 경우에만 사용한다.
- mutation은 최신 `origin/main`에서 만든 isolated worktree 또는 동등한 격리 공간에서 수행한다.
- 기본 worktree 경로는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`다. 저장소 위치가 다르면 같은 개발 루트의 안정적인 `.worktrees/game/<task-slug>` sibling 경로를 사용한다.
- source worktree를 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 아래에 만들지 않는다.
- IDE, LSP, uv, pnpm, Docker, 브라우저 E2E, generated artifact 검증은 모두 실제 작업 worktree 하나를 동일한 workspace root와 CWD로 사용한다.
- unrelated dirty state를 보존한다. force push, history rewrite, `--no-verify`, 필수 검증 우회는 금지한다.
- 게시 전 최신 `origin/main`을 다시 확인한다. non-fast-forward가 발생하면 최신 main에 재적용하고 직접 영향 검증을 다시 실행한다.

## 4. 병렬 실행과 reservation

일반 작업은 reservation 없이 격리된 worktree에서 병렬 실행한다. 다음 자원이 실제로 겹칠 때만 `agents/workflows/work-package-claim.md`와 Issue #1을 사용한다.

- 같은 semantic hotspot 또는 shared contract
- 같은 generated bundle·atlas·registry·publication destination
- 같은 browser/runtime identity, fixed port, profile, output directory
- 같은 migration·schema 자원

같은 파일이라는 이유만으로 reservation하지 않는다. reservation에는 `WORK / OWNER / EXPIRES / SCOPE`만 사용한다.

## 5. 프로젝트 경계

- 사용자 런타임은 정적 HTML/CSS/JavaScript다.
- 메인 허브는 `index.html`이다.
- 과목별 기능은 `domains/`, 공용 로직은 `shared/`에 둔다.
- 실험은 `experiments/`, 보호자·관리 기능은 `guardian/`, `admin/`에 둔다.
- Next.js, Tauri, 별도 backend API는 현재 범위 밖이다.
- Ocean Rescue 세부 계약은 대상 코드에서 가장 가까운 technical spec을 따른다.

## 6. 검증

대표 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

변경 위험에 직접 대응하는 가장 작은 검증부터 시작하며 모든 명령을 일괄 실행하지 않는다.

수정 파일과 직접 영향 모듈의 LSP·typecheck·lint 오류는 0이어야 한다. 환경·workspace·SDK·cache·generated/vendor 오분석을 production code 변경으로 우회하지 않는다.

workaround, fail-open fallback, broad ignore, 검사 대상 축소, baseline·snapshot 갱신, unrelated cleanup으로 실패를 숨기지 않는다. 실행하지 못한 필수 criterion은 PASS로 보고하지 않는다.

## 7. 로컬 에이전트 위임

- 프롬프트에는 현재 objective, workspace, included/excluded scope, Do / Do not, acceptance, verification, stop condition만 전달한다.
- 현재 package에 필요한 delta만 포함하고 최대 700줄을 넘기지 않는다.
- source workspace는 안정적인 `.worktrees/game/<task-slug>` 하나로 고정한다.
- 일반 병렬 prompt에는 reservation metadata를 넣지 않는다.
- WP 작업 프롬프트에는 계획 파일·WP 상태·상태 전용 evidence 생성을 포함하지 않는다.

## 8. 거버넌스

새 coordination 규칙·validator·상태 머신·완료 보고 필드는 실제 충돌이 반복 재현되고 worktree·고유 runtime identity·게시 전 overlap 확인으로 해결되지 않을 때만 추가한다.

## 9. 완료 보고

```text
RESULT: PASS | BLOCKED
CHANGE: <한 문장>
VERIFY: <한 문장>
```

실제 게시 시에만 `COMMIT`, 중단 시에만 `BLOCKER`와 `NEXT`를 추가한다.
