# AGENTS.md — AidenGame 저장소 계약

이 문서는 AidenGame 저장소에만 해당하는 계약만 담는다. 일반적인 에이전트 행동은 시스템 프롬프트를 따른다.

## 0. Web GPT canonical overlay (2026-08-08)

전역 개발 원칙은 Codex의 `developer_instructions`가 담당한다. 이 절은 기존
AidenGame workflow와 product contract를 대체하지 않는 프로젝트 고유 불변식이다.

- 브라우저/PixiJS architecture와 standalone deployable-artifact contract는
  명시적 변경이 없는 한 보존한다. 새 engine, Next.js, separate backend,
  runtime-critical external network dependency를 도입하지 않는다.
- implementation, documentation, test, required runtime/development path에 paid
  tool, asset, service, API, font, plan을 도입하지 않는다.
- `flake.nix`가 존재해도 Nix는 active toolchain이 아니다. 정책 변경 없이는
  `flake.lock` 생성, Nix pin upgrade/recommendation, Nix reproducibility work를
  하지 않는다.
- canonical manual visual-asset handoff를 보존한다:
  untrusted inbox/source → structural/security validation → actual game scale proof
  → required explicit approval → canonical source registration → canonical artifact
  regeneration → PixiJS/runtime verification.
- local text-only LLM이 approved SVG artwork를 조용히 재설계하게 하지 않는다.
- deterministic source → raster/atlas → registry → bundle → standalone artifact
  chain을 보존한다.
- canonical pipeline을 우회하려고 hash, provenance, registry identity, atlas
  metadata, generated bundle output을 손으로 편집하지 않는다.
- repository가 exact pin과 deterministic build step을 선언하면 이 문서의 오래된
  버전 대신 현재 선언을 따른다. unrelated asset/gameplay fix 중 renderer,
  dependency, tooling을 바꾸지 않는다.

## 1. 적용 순서

1. 사용자의 현재 요청
2. 이 문서
3. `PROJECT_RULES.md`와 대상 기능의 가장 가까운 product/technical spec
4. 최신 `origin/main`의 코드·테스트·설정

과거 계획과 완료 보고를 현재 상태의 근거로 사용하지 않는다.

## 2. WP 계획과 상태

- `WP-33E` 같은 이름은 대화와 실행 보고에서 사용하는 작업 라벨이다.
- 사용자가 저장소 문서화를 명시적으로 요청하지 않는 한 WP 계획·다음 WP·진행 상태·완료 상태는 대화에서만 관리한다.
- 일반 WP 작업을 위해 `docs/plans/PLAN_ocean_rescue_wp*.md` 또는 상태 전용 `docs/evidence/` 문서를 생성·수정하지 않는다.
- 테스트는 제품 동작·타입·빌드·배포 계약을 검증하며 `다음 WP`, `현재 WP`, `WP COMPLETE` 같은 일정 상태를 검증하지 않는다.
- 기존 migration plan과 과거 WP 문서는 참고 자료일 뿐 현재 일정의 권위가 아니다.
- Blueprint 절차는 사용자가 저장소 Blueprint를 명시적으로 요청한 경우에만 적용한다.

## 3. 현재 제품 방향

현재 기본 작업 선택은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`를 따른다.

- 우선 대상은 `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/`의 일반 문제풀이 신뢰성이다.
- 범위가 지정되지 않은 “다음 작업”, “이어서 진행”, 로컬 프롬프트 요청은 네 과목 공통 진단 또는 아직 닫히지 않은 일반 문제풀이 failure domain으로 해석한다.
- 최근 커밋이나 과거 대화가 Ocean Rescue였다는 이유만으로 Ocean Rescue 작업을 재개하지 않는다.
- 일반 과목 안정화 종료 전에는 Ocean Rescue와 `experiments/`의 신규 기능·구조 이전을 시작하거나 이를 위한 로컬 프롬프트를 발행하지 않는다.
- 예외는 사용자가 현재 요청에서 개발 방향을 명시적으로 변경했거나, 현재 배포를 막는 치명적 회귀·데이터 손상·보안 문제를 독립 failure domain으로 해결하는 경우다.
- 기존 테스트 파일이나 과거 PASS 보고만으로 과목 완료를 선언하지 않는다. 최신 main의 상태 계약과 실제 브라우저 증거를 함께 확인한다.
- 과목별 진행률·다음 과목·완료 체크는 저장소 문서에 누적하지 않는다. 현재 완료 근거는 코드, 테스트, 브라우저 증거, 게시 커밋이다.

## 4. Git과 workspace

- 통합·게시 기준은 `origin/main`이며 기본 게시 방식은 `main` fast-forward push다. PR·feature branch는 사용자가 요청한 경우에만 사용한다.
- mutation은 최신 `origin/main`에서 만든 isolated worktree 또는 동등한 격리 공간에서 수행한다.
- 기본 worktree 경로는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`다. 저장소 위치가 다르면 같은 개발 루트의 안정적인 `.worktrees/game/<task-slug>` sibling 경로를 사용한다.
- 새 primary/reapply task worktree는 생성과 동시에 `git worktree add --lock --reason`으로 잠가 현재 활성 workspace임을 Git metadata에 남긴다.
- lock reason에는 owner/tool, task 식별자, 생성 시각과 phase 같은 짧은 운영 식별자만 기록하고 PII, secret 또는 prompt 원문을 넣지 않는다.
- 게시에 성공하고 worktree가 clean이며 HEAD가 최신 `origin/main`에 포함되고 자신이 만든 worktree임을 확인한 뒤에만 unlock 후 plain `git worktree remove`로 회수한다. 중단·dirty·unpublished worktree는 unlock하거나 제거하지 않는다.
- `git worktree remove --force`와 worktree 경로의 `rm -rf`는 사용하지 않는다. `git worktree prune`은 이미 경로가 사라진 stale metadata 정리에만 사용한다.
- source worktree를 `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 아래에 만들지 않는다.
- IDE, LSP, uv, pnpm, Docker, 브라우저 E2E, generated artifact 검증은 모두 실제 작업 worktree 하나를 동일한 workspace root와 CWD로 사용한다.
- unrelated dirty state를 보존한다. force push, history rewrite, `--no-verify`, 필수 검증 우회는 금지한다.
- 게시 전 최신 `origin/main`을 다시 확인한다. non-fast-forward가 발생하면 최신 main에 재적용하고 직접 영향 검증을 다시 실행한다.
- 비중첩 remote advance와 다른 세션의 선행 게시는 blocker가 아니다. 최신 main 재적용, V1·필수 V2 재실행, 게시 재시도를 반복한다.
- 상세 생성·재적용·cleanup 절차는 `agents/workflows/git.md`를 따른다.

## 5. 병렬 실행과 reservation

일반 작업은 reservation 없이 격리된 worktree에서 병렬 실행한다. 다음 자원이 실제로 겹칠 때만 `agents/workflows/work-package-claim.md`와 Issue #1을 사용한다.

- 같은 semantic hotspot 또는 shared contract
- 같은 generated bundle·atlas·registry·publication destination
- 같은 browser/runtime identity, fixed port, profile, output directory
- 같은 migration·schema 자원

같은 파일이라는 이유만으로 reservation하지 않는다. reservation에는 `WORK / OWNER / EXPIRES / SCOPE`만 사용한다.

### AidenGame 상시 병렬 A/B 개발 트랙

사용자가 `A트랙` 또는 `B트랙`이라고 지시하면 아래 정의를 고정된 의미로 사용한다. 새 세션이나 후속 작업에서 어느 하위 분야를 뜻하는지 다시 묻지 않는다. 명시적인 A/B 트랙 요청은 §3의 범위 미지정 “다음 작업”과 달리 사용자가 현재 요청에서 개발 범위를 지정한 것으로 본다. 최신 `origin/main`과 가장 가까운 technical spec을 읽고 해당 트랙의 쓰기 범위 안에서 다른 트랙과 독립적으로 완료할 수 있는 가치가 가장 높은 다음 작업 하나를 선정한다.

- **A — 게임 런타임·플레이**: 실제 게임 실행 중 플레이어에게 일어나는 동작을 소유한다. 전투, 월드, 엔티티, 인벤토리, 진행, 경제·보상 규칙, 상태 머신(FSM), HUD, 입력·상호작용, controller, pause/timer/resume, 런타임 상태 전이, 실제 브라우저 플레이 동작과 DragonBones 등 이미 확정된 자산 계약을 소비하는 런타임 loader·renderer가 A다. 자산을 어떻게 제작·생성하는지보다 게임이 그 자산을 어떻게 읽고 표시하고 플레이 규칙에 연결하는지가 A의 책임이다.
- **B — 에셋·콘텐츠 제작/생성 파이프라인**: 게임 자산의 제작 원본부터 생성·검증·게시 가능한 산출물까지의 생산 체인을 소유한다. DragonBones/GIMP 제작 도구, source/review/handoff 자산, asset metadata·schema, exporter·CLI, preview·validator, atlas·registry·manifest 생성, provenance, deterministic generation/rebuild, 생성 산출물의 무결성 검증이 B다. `domains/ocean-rescue/assets/source/**`, `assets/review/**`, `assets/handoff/**`, `assets/generated/**`처럼 생산 체인에 속하는 자산 경로는 기본적으로 B 의미 영역으로 본다.

A/B 경계 운영 규칙:

- 다른 트랙의 코드·자산·테스트는 원인과 소비/생산 계약 확인을 위해 읽을 수 있지만 수정하지 않는다.
- `asset metadata/schema → manifest/atlas/registry → runtime loader/renderer`처럼 B가 생산하고 A가 소비하는 계약은 두 트랙이 동시에 수정하지 않는다.
- 생산 계약 변경이 필요하면 B가 metadata/schema와 생성·검증 체인을 먼저 확정하고 직접 검증한 뒤 `origin/main`에 게시한다. 그 다음 A가 게시된 계약만 기준으로 loader/renderer 소비 변경을 별도 단일 작업으로 수행한다.
- A 작업자는 런타임 문제를 닫기 위해 B의 schema·manifest 형식·생성기를 임의로 바꾸지 않는다. B 작업자는 파이프라인 문제를 닫기 위해 A의 플레이 상태·controller·런타임 loader 동작까지 확장하지 않는다.
- 예상 쓰기 범위가 A와 B 양쪽에 걸치면 현재 상시 병렬 작업으로 실행하지 않는다. 생산측 선행 계약 또는 소비측 후속 작업으로 분리하고, 현재 트랙에서 독립 완료 가능한 다른 후보를 선택할 수 있다.
- root dependency/toolchain, 공용 lockfile, 저장소 전체 CI·verify 설정처럼 양쪽 트랙이 함께 소비하는 변경은 A/B 상시 병렬 작업 밖의 직렬 통합 작업으로 처리한다.
- 단순한 `origin/main` 선행이나 non-fast-forward는 트랙 충돌이 아니다. 최신 main에 재적용했을 때 파일·계약 중첩이 없고 V1·필수 V2가 유지되면 정상 병렬 진행으로 본다.
- 실제 충돌이 발견되면 추상적인 예방 규칙을 늘리지 않는다. 반복된 실제 사례를 근거로 특정 경로의 소유권, 생산/소비 순서, 공용 직렬 영역 등 필요한 경계만 최소한으로 보정한다.
- 사용자가 `A트랙/B트랙에서 이어갈 다음 작업을 분석`하라고 하면 전투·HUD·DragonBones·atlas 같은 하위 분야를 다시 선택하라고 묻지 않는다. 최신 저장소 상태와 최근 완료 작업을 기준으로 해당 트랙 안에서 독립적으로 닫히는 다음 단일 failure domain을 스스로 선택한다. 로컬 프롬프트가 요청된 경우 작업 선택까지 먼저 수행하고 §8의 즉시 발행 원칙에 따라 재확인 없이 프롬프트를 발행한다.

## 6. 프로젝트 경계

- 사용자 런타임은 정적 HTML/CSS/JavaScript다.
- 메인 허브는 `index.html`이다.
- 과목별 기능은 `domains/`, 공용 로직은 `shared/`에 둔다.
- 실험은 `experiments/`, 보호자·관리 기능은 `guardian/`, `admin/`에 둔다.
- Next.js, Tauri, 별도 backend API는 현재 범위 밖이다.
- Ocean Rescue 세부 계약은 사용자가 해당 범위를 명시적으로 재개한 경우 대상 코드에서 가장 가까운 technical spec을 따른다.

## 7. 검증과 작업 판정

현재 방향 문서 정합성:

```bash
uv run pytest -q tests/test_core_quiz_reliability_policy.py
```

대표 저장소 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

### 위험 기반 개발·테스트 선택

정통 TDD를 모든 변경에 일률적으로 강제하지 않는다. TDD를 생략하는 것은 무검증 개발을 허용한다는 뜻이 아니다.

- 화면 구성, 스타일, 애니메이션, 조작감, 게임 감각, 콘텐츠 표현, 탐색적 신규 기능과 단순 dependency/toolchain 승격은 먼저 구현하고 실제 브라우저·입력·렌더링으로 직접 확인한 뒤 안정된 계약만 회귀 테스트로 고정할 수 있다.
- 입력 한 번에 효과 한 번, 이벤트 중복 연결, 점수·진행·저장 데이터, 복잡한 상태 전이, 재시작·복구, 공유 controller, 사용자 데이터 손상 가능성과 이미 발생한 회귀 버그는 테스트 우선 또는 구현과 동시에 테스트한다.
- 시각적 품질과 재미를 단위 테스트로 대신하지 않는다. 반대로 자동 검증 가능한 핵심 계약을 수동 확인만으로 남기지 않는다.
- 테스트는 구현 구조를 복제하지 않고 사용자에게 중요한 동작과 재발 방지에 집중한다.
- 모든 변경은 수정 전 재현 조건 또는 기대 동작과 단일 판정 기준을 정하고, 수정 후 해당 failure domain을 가장 짧은 독립 검증으로 판정한다.
- 형식적인 RED 증명, 고정 횟수 반복, 전 과목·전체 suite 실행을 모든 작업의 기본 절차로 삼지 않는다. 현재 위험이나 실제 불안정성이 요구할 때만 넓힌다.

### 형제 화면·공유 소유자 사전 점검

과목별 화면이나 공용 UI·controller의 동작을 수정하기 전에는 같은 사용자 계약을 제공하는 형제 범위를 읽기 전용으로 점검한다.

- 기본 형제 범위는 `domains/math/`, `domains/korean/`, `domains/english/`, `domains/science/`의 대응 control·flow와 이를 소유하는 `shared/` 구현이다.
- 재시작, 통계, 점수, 진행, 저장, 입력 이벤트처럼 같은 기능을 제공하는 위치와 동일 button/event binding을 먼저 검색한다.
- 이 점검은 누락·중복 소유자를 찾기 위한 조사 범위이며 authorized write scope를 자동으로 넓히지 않는다.
- 같은 shared owner의 한 수정으로 같은 root cause와 rollback boundary를 함께 닫을 수 있을 때만 하나의 failure domain에 포함한다.
- 과목별 독립 wiring이나 다른 root cause가 확인되면 현재 대상만 수정·검증하고 나머지는 `DISCOVERED_FAILURE` 또는 별도 objective로 분리한다.
- 현재 대상은 실제 사용자 입력 경로로 검증하며, 입력 한 번에 handler·render·request 같은 직접 효과가 정확히 한 번만 발생해야 한다.

### YAGNI와 변경 범위

- YAGNI는 아직 요구되지 않은 미래 capability, speculative abstraction, extension point와 unrelated cleanup을 만들지 않는 원칙이다. 현재 확인된 root cause를 최소 LOC나 최소 파일 수로만 봉합하라는 뜻이 아니다.
- 목표는 `minimum diff`가 아니라 `minimum coherent, root-cause-complete change`다. 파일 수보다 root cause, invariant, ownership, rollback boundary와 primary criterion의 일치 여부로 package 경계를 정한다.
- 같은 root cause와 invariant를 공유하고 한 shared owner에서 함께 닫을 수 있다면 production owner, 직접 sibling caller, type/contract, fixture와 focused regression은 하나의 failure domain에 포함할 수 있다.
- leaf local guard를 반복하거나 동일 normalization·validation·state rule을 여러 caller에 복제하는 방식, shared owner 결함을 남긴 채 한 화면만 우회하는 방식은 under-fixing 신호로 취급한다.
- 현재 invariant를 명확히 표현하고 testability를 확보하기 위한 작은 refactor는 YAGNI 위반이 아니다. 반면 미래 variation을 예상한 generalization, 현재 failure domain과 무관한 cleanup과 대형 재설계는 분리한다.
- sibling inventory는 넓게 수행할 수 있지만 mutation scope는 자동으로 넓히지 않는다. 같은 root cause·invariant·rollback boundary로 한 focused verification 아래 함께 판정할 수 없는 발견은 별도 failure domain으로 남긴다.

현재 작업 결과는 다음 두 항목으로만 판정한다.

- `PRIMARY_CRITERION`: 현재 단일 가설을 직접 판정하는 기준
- `DIRECT_IMPACT_CLOSURE`: 수정 파일과 직접 영향 범위의 lint·type·focused regression

검증 계층:

- V0 `BASELINE`: 수정 전 결함 재현
- V1 `PRIMARY`: 단일 가설 판정
- V2 `DIRECT`: 수정 파일과 직접 영향 closure
- V3 `SYSTEM_SMOKE`: 독립 결함 탐색; 현재 작업 PASS를 취소하지 않음
- V4 `RELEASE`: 명시적인 release candidate에서만 수행

현재 변경이 정상이어도 실패할 수 있는 broad smoke, full suite 또는 다른 과목·실험 영역의 실패는 primary criterion이 될 수 없다. V3에서 발견된 독립 실패는 현재 작업의 PASS를 취소하지 않고 `DISCOVERED_FAILURE`로 분리한다.

변경 위험에 직접 대응하는 가장 작은 검증부터 시작하며 모든 명령을 일괄 실행하지 않는다.

수정 파일과 직접 영향 모듈의 LSP·typecheck·lint 오류는 0이어야 한다. 환경·workspace·SDK·cache·generated/vendor 오분석을 production code 변경으로 우회하지 않는다.

workaround, fail-open fallback, broad ignore, 검사 대상 축소, baseline·snapshot 갱신, unrelated cleanup으로 실패를 숨기지 않는다. 실행하지 못한 V1·필수 V2 criterion은 PASS로 보고하지 않는다.

`BLOCKED`는 `DECISION_REQUIRED`, `PRIMARY_UNEVALUABLE`, `SEMANTIC_OVERLAP`, `SAFETY_BOUNDARY`, 또는 V1·필수 V2 실패를 현재 failure domain 안에서 안전하게 닫을 수 없는 경우에만 사용한다.

remote advance, non-fast-forward, unrelated dirty, V3 실패, 새 독립 결함, 다른 세션의 선행 게시는 blocker가 아니다.

## 8. 로컬 에이전트 위임

로컬 LLM용 프롬프트는 사용자의 요청과 최신 저장소 증거로 objective, scope와 criterion을 합리적으로 확정할 수 있으면 별도의 의도 재확인·승인 요청 없이 즉시 발행한다.

- 목표와 대상 failure domain 또는 검증 가설, 대상 저장소·기능과 변경 허용 범위, 포함·제외 범위와 변경 금지 계약, primary criterion, 직접 영향 검증, 게시 여부와 예상 최종 상태를 발행 전에 내부적으로 정합성 점검한다.
- 사소한 모호성은 사용자의 현재 요청, 최신 `origin/main`, 가장 가까운 technical spec과 기존 프로젝트 계약으로 해소하며 확인차 되묻지 않는다.
- “제가 이렇게 해석했습니다. 이대로 진행해도 되는 게 맞습니까?”와 같은 확인 전용 turn, 승인 대기, 범위 재진술 후 재승인을 기본 절차로 만들지 않는다.
- 사용자가 범위를 수정하면 최신 지시를 즉시 반영하고, 새 지시 자체가 실행 가능하면 다시 승인받지 않는다.
- 질문은 필수 정보가 없어 실행 자체가 불가능하거나, 서로 양립할 수 없는 해석이 결과를 크게 바꾸거나, user-visible behavior·제품 방향·수정 범위·acceptance criterion·사용자 데이터 무결성 또는 안전 경계를 바꿔야만 완료할 수 있을 때만 `DECISION_REQUIRED`로 제한한다.
- 로컬 작업자는 `DECISION BOUNDARY` 안의 구현 세부사항을 스스로 결정하며 확인을 요구하지 않는다.

- 프롬프트 발행 전 현재 objective가 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`의 포함 범위인지 확인한다.
- 포함 범위가 아니고 사용자가 현재 요청에서 방향 변경이나 허용 예외를 명시하지 않았다면 구현 프롬프트를 발행하지 않는다.
- 프롬프트에는 현재 objective, workspace, included/excluded scope, Do / Do not, primary acceptance, direct verification, optional system smoke, stop condition만 전달한다.
- `DO`에는 단순히 최소 diff를 지시하지 말고, 수정 전 shared owner와 sibling contract를 읽어 under-fixing 여부를 판정하며 같은 root cause·invariant·rollback boundary이면 필요한 production/type/test 범위까지 coherent하게 닫도록 명시한다.
- `DO_NOT`에는 미래 capability를 위한 speculative abstraction과 unrelated cleanup을 금지하되, 현재 root cause를 닫는 데 필요한 작은 refactor나 testability 개선을 금지하지 않는다.
- acceptance는 증상 한 건의 GREEN뿐 아니라 shared root cause가 leaf workaround로 남지 않았는지와 동일 invariant가 새로 중복 구현되지 않았는지를 포함한다.
- 현재 package에 필요한 delta만 포함하고 최대 700줄을 넘기지 않는다.
- source workspace는 안정적인 `.worktrees/game/<task-slug>` 하나로 고정한다.
- 일반 병렬 prompt에는 reservation metadata를 넣지 않는다.
- WP 작업 프롬프트에는 계획 파일·WP 상태·상태 전용 evidence 생성을 포함하지 않는다.

## 9. 거버넌스

새 coordination 규칙·validator·상태 머신·완료 보고 필드는 실제 충돌이 반복 재현되고 worktree·고유 runtime identity·게시 전 overlap 확인으로 해결되지 않을 때만 추가한다.

## 10. 완료 보고

```text
RESULT: PASS | BLOCKED
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED
DISCOVERED_FAILURE: <독립 failure domain 또는 NONE>
```

실제 게시 시에만 `COMMIT`, 허용된 blocker로 중단할 때만 `BLOCKER`와 `NEXT`를 추가한다.