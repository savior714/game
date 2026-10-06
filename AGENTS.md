# AGENTS.md — AidenGame agent kernel

<!-- Language: ko -->

이 문서는 저장소 전체 에이전트가 알아야 하는 최소 우선순위, 권위 라우팅, 실행 경계만 소유한다.
제품·아키텍처·검증·Git·개발의 세부 계약은 각 subject owner가 소유한다. 이 문서는 질문을 owner에게
라우팅할 뿐 그 내용을 복제하지 않는다.

## 0. 프로젝트 불변식

- 브라우저/PixiJS architecture와 standalone deployable-artifact contract를 명시적 변경 없이 보존한다.
  새 engine, Next.js, separate backend, runtime-critical external network dependency를 도입하지 않는다.
- implementation, documentation, test, required runtime/development path에 paid tool, asset, service,
  API, font, plan을 도입하지 않는다. `flake.nix`가 존재해도 Nix는 active toolchain이 아니며, 정책 변경
  없이는 `flake.lock` 생성과 Nix pin·reproducibility 작업을 하지 않는다.
- deterministic source → raster/atlas → registry → bundle → standalone artifact chain을 보존한다.
  canonical pipeline을 우회하려고 hash, provenance, registry identity, atlas metadata, generated bundle
  output을 손으로 편집하지 않는다.
- canonical manual visual-asset handoff를 보존한다: untrusted inbox/source → structural/security
  validation → actual game scale proof → required explicit approval → canonical source registration →
  canonical artifact regeneration → PixiJS/runtime verification.
  상세 계약은
  [`AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`](docs/specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md)가
  소유한다.
- local text-only LLM이 approved SVG artwork를 조용히 재설계하게 하지 않는다.
- 저장소가 exact pin과 deterministic build step을 선언하면 이 문서의 오래된 버전 대신 현재 선언을
  따른다. unrelated asset/gameplay fix 중 renderer, dependency, tooling을 바꾸지 않는다.

## 1. 권위 순서와 언어

충돌 시 다음 순서를 적용한다.

1. 사용자의 현재 요청
2. 이 문서
3. 이 문서가 위임한 subject owner: `PROJECT_RULES.md`, 제품 SSOT, §2 표의 owner
4. 최신 `origin/main`의 코드·테스트·설정·runtime 증거

1–3은 instruction이고 4는 implementation evidence다. evidence와 활성 contract가 다르면 어느 쪽도
자동으로 다시 쓰지 말고 불일치를 조사한다. 과거 계획, 완료 보고, WP 문서는 현재 상태의 근거가 아니다.

응답 언어와 artifact 언어는 서로 독립이다.

- **응답 언어** — 채팅과 최종 보고는 한국어가 기본이다. 사용자의 현재 채팅 언어나 명시적 요청만 바꾼다.
- **artifact 언어** — 코드·주석·문서·제품 카피는 각 subject owner를 따른다. `<!-- Language: ko -->`
  표식은 그 artifact의 prose 언어만 선언하며 응답 언어를 바꾸지 않는다.

## 2. 권위 라우팅

| 질문 | Owner |
|---|---|
| 현재 제품 목표·우선순위·active/frozen feature 상태 | [`ACTIVE_PRODUCT_SCOPE.md`](docs/specs/product/ACTIVE_PRODUCT_SCOPE.md) |
| 아키텍처·경로·품질·보안 경계 | [`PROJECT_RULES.md`](PROJECT_RULES.md) |
| 실행 순서·workspace lifecycle·commit·게시 절차 | [`execution.md`](agents/core/execution.md) |
| 검증 선택·검증 계층·PASS/BLOCKED 판정 | [`verification.md`](agents/core/verification.md) |
| 판단 원칙·YAGNI·변경 범위 경계 | [`principles.md`](agents/core/principles.md) |
| 보고 형식과 PASS/BLOCKED 근거 | [`reporting.md`](agents/core/reporting.md) |
| Git 파괴적 안전 판정 | [`git.md`](agents/workflows/git.md) |
| exclusive 자원 reservation | [`work-package-claim.md`](agents/workflows/work-package-claim.md) |
| 상시 병렬 A/B 개발 트랙과 트랙 런북 | [`PARALLEL_TRACKS.md`](agents/project/PARALLEL_TRACKS.md) |
| 계획·WP 상태·저장소 Blueprint | [`planning.md`](agents/core/planning.md) |
| 로컬 실행 프롬프트 발행 | [`LOCAL_LLM_DELEGATION.md`](agents/project/LOCAL_LLM_DELEGATION.md) |
| 브라우저 실행 증거 | [`playwright.md`](agents/workflows/playwright.md) |
| 도구·컨텍스트 선택 | [`routing.md`](agents/core/routing.md) |
| 실제 구현 상태 | 코드·테스트·설정·runtime 증거 |

전체 문서 색인은 [`RULE_INDEX.md`](agents/registry/RULE_INDEX.md)를 따른다.
현재 failure domain에 직접 관련된 owner만 읽는다.

## 3. 실행·workspace 경계

작업 모드는 호출한 프롬프트가 정한다.

- `MODE: BUILD` — 범위가 지정된 구현 작업을 수행한다. 사용자 지정 구현에 저장소 수준의 추가 승인
  게이트를 추가하지 않는다. runtime이 read-only/Plan mode이면 그 mode를 존중하고, 저장소 지침이
  mutation을 승인한다고 가장하지 않는다.
- `MODE: PLAN_ONLY` — materially uncertain한 부분을 read-only로 조사하고 추적 상태를 변경하지 않는다.

`BUILD` mutation은 최신 `origin/main`에서 잘라낸 격리 workspace에서 수행하며 tracking `main`에서
수행하지 않는다. workspace 생성·lock·재적용·정리 절차는
[`execution.md`](agents/core/execution.md)가, 그 상태 전이가 안전한지는
[`git.md`](agents/workflows/git.md)가 소유한다.

조사 범위는 쓰기 권한을 넓히지 않는다. task, lane, execution, workspace, branch/ref, commit,
publication은 서로 다른 identity이며 task가 새 branch를 필요로 하지는 않는다. 사용자가 지정한
범위에 새 우선순위·거버넌스 게이트를 추가하지 않는다.

### Bounded execution invariants

1. **Proof stop rule** — 가장 가까운 정직한 proof가 통과하면, 아직 미해결인 필수 결정의 결과를 바꿀 수
   있을 때만 검증을 넓힌다. 확신 보강, 디렉터리 근접성, 키워드 일치를 이유로 suite를 넓히지 않는다.
2. **Differential failure gate** — 새로 만난 실패를 편집 전에 분류한다. 현재 변경이 만든 실패는 현재
   failure domain으로 닫는다. 시작·clean revision에서도 재현되는 실패는 현재 claim을 막지 않는 한
   흡수하지 않는다. 아직 분류되지 않으면 가장 작은 판별 read-only 관측을 먼저 수행한다.
3. **Observation integrity** — 음성 증거는 성공한 관측이 부재를 확립할 때만 유효하다. 실패하거나
   불완전한 측정은 `ERROR`/`UNKNOWN`으로 남긴다. 합성 proof 상태는 올바른 기준선과 비교하고 시나리오를
   격리하며, 그 상태가 proof 소유임이 증명된 뒤에만 정리한다.
4. **Decision-monotonic re-entry** — 직접 증거로 확립된 사실을 재사용한다. 권위, evidence 경계, 사용자
   지시, 도구 결과가 실질적으로 바뀐 경우에만 재확인한다. 재시작, compaction, 새 호출, 단순한 의심은
   완료된 작업을 반복할 이유가 아니다. 별도 decision registry를 두지 않는다.
5. **Closure-first scope control** — 현재 task가 만들거나 직접 대체한 상태만 정리한다. 발견된 개선은
   근접하다는 이유만으로 현재 task에 편입되지 않는다. 선언한 fix surface 중 하나라도 열려 있으면
   결과는 `PARTIAL`이며 남은 위치를 `file:line`으로 밝힌다.
6. **Revision-bound evidence** — 증거는 실제 관측한 revision에 묶인다. `origin/main` SHA 이동만으로
   완료된 의미 작업이나 영향 없는 proof가 무효가 되지 않는다. 다음 결정이 현재 원격 상태에 실제로
   의존할 때만 권위를 다시 관측하고, 이미 충족된 결과는 가장 작은 확인 후 중복 mutation을 멈춘다.
7. **Stop discipline** — bounded outcome, required proof, required publication/read-back, task-owned
   cleanup이 끝나면 멈춘다. 확신 보강용 fetch·proof 재실행·인접 정리를 덧붙이지 않는다. 정리만 실패했다면
   그 경계만 다시 연다.

## 4. Git-native 작업 실행

1. 사용자의 bounded task에서 시작하거나, autonomous 구현이 명시적으로 요청된 경우 현재 저장소 권위에서
   도출한 bounded task 하나에서 시작한다.
2. 최신 `origin/main` 권위를 확립하고 격리된 task-owned workspace에서 작업하며 foreign·dirty·in-flight
   state를 보존한다.
3. 독립 작업은 semantic·proof·mutation·integration 경계가 실질적으로 독립일 때만 병렬 실행한다.
   파일이 다르다는 사실은 독립의 증거가 아니고, 파일이 겹친다는 사실만으로 충돌도 아니다.
4. 의미적 신선도, proof 신선도, 게시 신선도를 분리해 판단하고 영향 없는 proof는 재사용한다.
5. 권한이 있는 mutation은 최소 root-cause-complete 구현 → 가장 가까운 정직한 proof → task-owned 잔여
   정리 → 게시 자격 → non-force 게시 → 정확한 remote read-back → task-owned workspace close 순서로
   닫고 현재 세션에서 결과를 직접 보고한다.
6. `origin/main` 이동과 다른 세션의 선행 게시는 blocker가 아니다. 최신 main에 재적용하고 영향받은
   proof만 다시 실행한 뒤 최소한의 게시 rebinding으로 재시도한다.
7. retired coordination queue, reservation, relay·report transport 같은 대안 control plane을 다시
   도입하지 않는다. Git-native 실행이 반드시 처리해야 하는 실패 클래스가 실제로 증명될 때만 가장 작은
   수단만 추가한다.

구체 명령·gate·정리 절차는 [`execution.md`](agents/core/execution.md)가 소유한다.

## 5. 증거와 외부 사실

- 파일·경로·symbol·명령·워크플로의 존재를 확인하기 전에 결함이나 capability를 단정하지 않는다.
- 검색 결과·요약·캐시·도구 출력은 발견 후보이지 권위가 아니다. PASS와 증거 의미는
  [`verification.md`](agents/core/verification.md)가 소유한다.
- URL·경로·파일명·API slug·host·도구 식별자는 검색 결과, 현재 공식 href, provenance이 있는 저장소
  URL, 사용자로부터 실제로 얻은 것만 사용한다. 직접 만들어내지 않는다. 무효한 URL은 그 URL만
  무효화하며 provider나 capability 부재를 증거하지 않는다.
- 실행하지 않은 검증을 PASS로 보고하지 않는다. workaround, fail-open fallback, broad ignore, 검사 대상
  축소, baseline·snapshot 갱신으로 실패를 숨기지 않는다.
- `BLOCKED`는 [`verification.md`](agents/core/verification.md)가 정의한 허용 사유에만 사용한다.
  remote advance, non-fast-forward, unrelated dirty, 시스템 smoke 실패, 새 독립 결함, 다른 세션의 선행
  게시는 blocker가 아니다.
- 연구·Blueprint·업로드 source·채팅 산출물은 그 자체로 evidence다. 구현이 새로 정한 제품·도메인·
  아키텍처 의미를 의존하기 전에 해당 canonical owner에 이미 반영됐는지 확인하고, 없으면 먼저 반영한다.

## 6. 거버넌스

새 coordination 규칙·validator·상태 머신·완료 보고 필드는 실제 충돌이 반복 재현되고 worktree, 고유
runtime identity, 게시 전 overlap 확인으로 닫히지 않을 때만 추가한다. 실제 충돌 사례 없이 추상적인 예방
규칙을 늘리지 않고, 반복된 사례가 있을 때 필요한 경계만 최소한으로 보정한다.

## 7. 완료 보고

형식과 PASS/BLOCKED 근거는 [`reporting.md`](agents/core/reporting.md)가 유일하게 소유한다.
이 문서는 완료 판정을 다시 정의하지 않는다. 실제 게시 시에만 `COMMIT`, 허용된 blocker로 중단할 때만
`BLOCKER`와 `NEXT`를 추가한다.