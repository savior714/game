# PROJECT_RULES.md — AidenGame 프로젝트 정책

작업 절차는 `AGENTS.md`를 따른다. **현재 제품 목표·우선순위·active/frozen feature 상태의 단일 SSOT는 `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`다.** 이 문서는 제품 SSOT를 복제하지 않고 아키텍처·품질·보안 경계를 정의한다.

## 1. 제품 경계

AidenGame은 어린이를 위한 local-first 웹 기반 학습 게임 플랫폼이다.

현재 제품 의미와 개발 sequence는 반드시 `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`를 읽는다. 특히 다음 관계는 이 문서에서 재정의하지 않는다.

- skill mastery와 adaptive daily learning
- Core Quiz → 학습 완료 → reward/free-time → Ocean Rescue 관계
- Guardian/reward 경계
- Ocean Rescue active / Space Explorer frozen 상태
- 현재 milestone 순서와 non-goals

제품 SSOT가 변경되면 이 파일에는 그 결과로 아키텍처·품질 경계가 실제로 바뀐 경우만 반영한다.

## 2. 런타임과 경로

| 역할 | 경로 |
|---|---|
| 메인 허브 | `index.html` |
| 공용 스타일 | `styles.css` |
| 과목별 게임 | `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/` |
| 지원 도메인 | `domains/reward/`, `domains/auth/`, `domains/sync/` |
| 공용 로직 | `shared/domain/`, `shared/ui/`, `shared/event-bus.js` |
| Ocean Rescue source/package | `domains/ocean-rescue/` |
| Ocean Rescue production artifact | `ocean-rescue/index.html` |
| 실험 | `experiments/` |
| 보호자·관리 | `domains/reward/guardian/`, `guardian/`, `admin/` |
| 테스트 | `tests/` |
| 검증 | `verify.sh`, `scripts/`, `tools/` |

- 신규 UI와 로직은 가장 가까운 기능 디렉터리에 둔다.
- 여러 과목/기능이 실제로 공유하는 domain meaning과 로직만 `shared/`로 올린다.
- `shared/` 추출은 framework 통일보다 skill, mastery, reward, free-time 같은 공통 의미를 우선한다.
- Space Explorer는 제품 SSOT가 재개시키기 전까지 `experiments/`에 격리한다.
- 빈 `src/`를 새 runtime SSOT로 사용하지 않는다.
- Next.js, Tauri, 별도 백엔드 API는 현재 범위에 자동 추가하지 않는다.
- generated artifact와 authoring source를 구분한다.
- Ocean Rescue는 가장 가까운 product/technical spec과 build pipeline을 따른다.
- Core Quiz와 Ocean Rescue가 서로 다른 tooling을 사용하는 것은 허용된다. 기술스택 통일 자체를 migration 목표로 만들지 않는다.

## 3. 기술 스택

- Core Quiz 사용자 런타임: HTML, CSS, JavaScript
- 배포: `vercel.json` 기반 정적 호스팅
- 검증 도구: Python, `uv`, `just`, Ruff, type checker, Pytest
- Ocean Rescue build/runtime tooling은 해당 경로의 lockfile과 가장 가까운 spec이 authority다.
- dependency·toolchain upgrade는 별도 coherent package로 수행한다.
- runtime LLM, 별도 backend/cloud는 제품 SSOT에서 명시적으로 범위가 바뀌기 전에는 필수 architecture로 도입하지 않는다.

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

- 각 실행 작업은 하나의 failure domain, 하나의 검증 가능한 가설, 하나의 binary criterion으로 제한한다.
- 같은 failure domain을 완결하는 데 필요한 source, caller, test, asset, config는 함께 변경할 수 있다.
- 수정 전 재현 조건과 단일 판정 기준을 고정하고, 수정 후 해당 가설만 독립 검증한 뒤 다음 failure domain으로 이동한다.
- 서로 다른 LSP·typecheck·lint 원인이나 unrelated product cleanup을 한 패치에 섞지 않는다.
- 새 검증은 잡아낼 구체적 failure mode 또는 안정적으로 보존해야 할 제품 계약이 있을 때만 추가한다.
- full-suite는 실제 회귀 위험이나 cutover가 요구할 때만 실행한다.
- 완료된 reliability baseline을 관성적으로 다시 개발 backlog로 만들지 않는다. 동일 결함이 재현될 때 회귀로 다룬다.

### 5.1 정적 진단 closure

- 작업 시작 시 안정적인 worktree root에서 관련 LSP·typecheck·lint baseline을 확인한다.
- 현재 변경으로 새로 생긴 오류와 수정 파일·직접 영향 모듈의 오류는 현재 package에서 반드시 수정한다.
- 저장소 정적 게이트가 다른 기존 오류를 드러내면 현재 원인과 섞어 대규모 수정하지 않는다. 현재 failure domain을 같은 진단으로 독립 검증한 뒤 다음 정적 failure domain 하나를 선택해 순차 해결한다.
- 잘못된 workspace root, SDK/interpreter, 누락된 의존성, stale cache/index, generated/vendor 오분석이 원인이면 production code를 억지로 바꾸지 않고 환경·설정을 수정한 뒤 동일 진단을 재실행한다.
- broad ignore, `type: ignore`, `noqa`, ESLint disable, 검사 대상 축소, baseline·snapshot 갱신으로 녹색을 만들지 않는다.
- LSP·typecheck·lint 오류를 “pre-existing” 또는 “out of scope”라는 이유만으로 보고하고 PASS하지 않는다.
- 최종 PASS는 현재 변경과 직접 영향 범위의 정적 오류가 0이고 이번 작업에 요구되는 저장소 정적 게이트가 통과한 경우에만 허용한다. 안전하게 해결할 수 없는 정적 오류가 남으면 정확한 재현 명령과 원인을 포함해 `BLOCKED`로 보고한다.

### 5.2 Domain meaning and representation boundaries

- Domain state/object가 의미와 invariant를 소유한다. 외부·저장 표현의 불확실성을 runtime domain 전체에 전파하지 않는다.
- JSON, localStorage, URL/query, imported content, generated metadata 등 외부 또는 persisted representation은 사용 전에 검증·정규화하고, 계약이 다르면 runtime domain object와 명시적으로 분리한다.
- 문제·진행·mastery·보상·게임 상태의 생성·복원·재시작 경로는 같은 invariant를 보장해야 한다. 복원 경로가 invalid state를 우회 생성하지 않게 한다.
- 서로 배타적인 상태와 상태별 필수 값은 가능한 한 독립 boolean/null 조합보다 명시적 tag/state와 transition으로 표현한다.
- 의미가 다른 ID·code·skillId·score·quantity 같은 값의 혼동이 실제 오류가 되는 경우 현재 언어·도구가 지원하는 가장 단순한 semantic representation을 사용한다. TypeScript 전환이나 wrapper 전면 도입을 요구하지 않는다.
- type/JSDoc/schema 오류를 없애기 위해 optional/default/fallback을 임의 추가하거나 unchecked cast·broad object shape로 의미를 약화하지 않는다. producer → boundary/normalizer → domain consumer를 추적해 실제 owner를 고친다.
- 타입·상태 안정성 작업의 criterion은 “컴파일/검사가 통과한다”가 아니라 이름 붙인 invalid state가 더 이상 trusted runtime에 들어오거나 표현되지 않는다는 직접 증거로 잡는다.
- 학습 evidence와 derived mastery를 구분한다. 알고리즘을 바꿀 수 있도록 필요한 raw evidence를 derived score로 덮어쓰지 않는다.

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
- 기준 기기는 Galaxy Tab S10급 태블릿이고 landscape-first로 설계하되 portrait/split-screen/resize에서도 핵심 사용이 막히지 않게 한다.
- 핵심 흐름은 키보드와 보조 기술로도 사용할 수 있어야 한다.
- 시각 효과가 조작과 가독성을 방해하지 않게 한다.
- 아이에게 학습 약점 percentage를 직접 노출하는 대신 오늘 목표와 긍정적 progression을 우선한다.

## 7. 보안

- API 키, 토큰, 쿠키, `.env` 원문을 노출하지 않는다.
- 인증·동기화·보호자 기능은 권한이 불명확할 때 fail-closed한다.
- 외부 입력을 검증하고 안전한 DOM API를 사용한다.
- 가족/개인 local-first 범위를 공개 다중 사용자 서비스로 암묵적으로 확장하지 않는다.

## 8. 문서

| 목적 | SSOT / authority |
|---|---|
| 실행 규약 | `AGENTS.md` |
| **현재 제품 방향** | `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md` |
| 아키텍처·품질 경계 | `PROJECT_RULES.md` |
| 완료된 Core Quiz reliability 계약 | `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md` |
| Ocean Rescue 제품/기술 계약 | 대상 기능에 가장 가까운 `docs/specs/product/`·`docs/specs/technical/` 문서 |
| Space Explorer 동결 참고 | `docs/SPACE_EXPLORER_PLAN.md` |
| exclusive reservation | `agents/workflows/work-package-claim.md` + Issue #1 |
| Git·publish | `agents/workflows/git.md` |
| 요구사항·회귀 | `tests/` |
| 배포 | `vercel.json`과 실제 entry |

과거 Plan·Blueprint·runbook의 `ACTIVE`, WP 번호 또는 완료 보고가 `ACTIVE_PRODUCT_SCOPE.md`의 현재 제품 우선순위를 덮어쓰지 않는다.
