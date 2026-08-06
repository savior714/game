# Ocean Rescue Vite · ESM · TypeScript 마이그레이션 기술 참고

- **상태:** `PAUSED_REFERENCE_ONLY`
- **현재 단계:** `PAUSED`
- **다음 실행 work package:** `NONE_WHILE_PAUSED`
- **현재 실행 권위:** `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`
- **재개 조건:** 사용자가 현재 요청에서 명시적으로 Ocean Rescue를 재개하거나, 일반 과목 안정화 exit gate 이후 우선순위를 다시 결정한 경우
- **운영 예외:** 현재 배포를 막는 치명적 회귀, 데이터 손상, 보안 문제의 독립 수정

## 1. 이 문서의 역할

이 문서는 Ocean Rescue의 Vite 번들, ESM 그래프, strict TypeScript 경계와 rollback 구조를 설명하는 기술 참고문서다.
현재 일정, 다음 WP, 진행률, 완료 상태를 관리하지 않는다.
과거 WP 번호와 세부 완료 이력은 Git 커밋과 테스트에 보존되어 있으며 현재 작업 선택의 권위가 아니다.

일반 과목 문제풀이 안정화가 완료되기 전에는 다음을 시작하지 않는다.

- 추가 typed-controller ownership 이전
- 새로운 rescue mission 또는 콘텐츠
- 렌더링·애니메이션 고도화
- Vite/TypeScript/toolchain upgrade
- production artifact cutover 변경
- legacy rollback 제거
- 신규 browser evidence 확대 작업

최근 Ocean Rescue 커밋이 존재한다는 사실만으로 마이그레이션을 자동 재개하지 않는다.

## 2. 현재 아키텍처 기준선

### 2.1 실행 경계

| 역할 | 경로 |
|---|---|
| authoring/runtime source | `domains/ocean-rescue/src/` |
| 개발 entry | `domains/ocean-rescue/index.dev.html` |
| production build 설정 | `domains/ocean-rescue/vite.production.config.ts` |
| 개발 build 설정 | `domains/ocean-rescue/vite.config.ts` |
| package/toolchain | `domains/ocean-rescue/package.json`, lockfile, `.node-version` |
| production standalone artifact | `ocean-rescue/index.html` |
| production bundle metadata | `domains/ocean-rescue/dist/production-bundle-metadata.json` |
| legacy proof artifact | `domains/ocean-rescue/dist/legacy-rollback.html` |

실제 파일과 build pipeline이 이 문서보다 우선한다.

### 2.2 production과 rollback

- production은 Vite 기반 번들과 vendored rendering prerequisite를 사용한다.
- standalone `ocean-rescue/index.html`은 생성 artifact다.
- legacy ordered-script 경로는 rollback/proof 목적의 호환 경계다.
- 생성 artifact를 수동 편집하지 않고 source와 build pipeline을 통해 갱신한다.
- production artifact와 legacy proof artifact의 목적을 혼동하지 않는다.

### 2.3 TypeScript 경계

마이그레이션은 런타임 전체를 한 번에 다시 쓰지 않고, 검증 가능한 ownership 경계를 순차적으로 strict TypeScript로 이전해 왔다.

현재 참고 가능한 typed 영역에는 다음과 같은 범주가 있다.

- profile과 mission 선택
- 정적 mission/GUP/launch catalog
- core state와 travel
- shared runtime ABI
- pointer/renderer coordinate boundary
- launch/travel controller
- rescue-site/tutorial controller
- pause/timer/resume controller
- sea-turtle session, projection, pointer lifecycle controller

이 목록은 각 영역의 최신 완료 상태를 선언하지 않는다. 재개 시 실제 ESM import graph, 구현, focused test, production artifact를 다시 확인한다.

## 3. 안정적으로 보존해야 할 계약

### 3.1 단일 production authority

- production entry와 generated artifact의 소유권은 build pipeline에 있다.
- 개발용 entry, shadow/proof artifact, legacy rollback을 production entry로 오인하지 않는다.
- source 변경 후 artifact drift 검증이 필요한 경우에만 production artifact를 재생성한다.

### 3.2 canonical ESM과 legacy fallback

- 현재 production ESM 경로와 rollback용 ordered-script 경로는 목적이 다르다.
- typed ownership 이전은 canonical ESM 경로를 우선한다.
- legacy fallback은 명시적으로 제거하기 전까지 rollback 계약을 보존한다.
- fallback에 대한 변경은 production과 rollback을 함께 검증할 수 있는 별도 failure domain으로 수행한다.

### 3.3 controller ownership

- controller는 자신이 이전받은 상태, 이벤트, timer, cleanup의 소유권을 명확히 가져야 한다.
- host bridge는 필요한 최소 런타임 의존성만 전달한다.
- 동일 lifecycle의 source와 caller, cleanup, focused test는 강하게 결합된 한 failure domain으로 처리할 수 있다.
- 서로 다른 lifecycle, artifact 게시, browser proof, plan 상태 변경을 한 작업에 묶지 않는다.

### 3.4 pointer와 timer cleanup

- pointer ID와 capture acquisition/release를 일관되게 관리한다.
- `pointerup`, `pointercancel`, pause, menu shutdown에서 임시 상태를 정리한다.
- timer registry와 resume countdown은 중복 실행되지 않아야 한다.
- session shutdown 이후 listener, pointer capture, timer가 남지 않아야 한다.

### 3.5 deterministic artifact

- 동일한 source와 lockfile에서 production build가 결정적이어야 한다.
- tracked artifact가 clean rebuild와 일치해야 한다.
- build metadata와 artifact identity가 서로 정합해야 한다.

## 4. 동결 중 허용되는 작업

동결 중에는 다음 문제가 최신 main 또는 현재 production에서 실제로 재현될 때만 별도 failure domain으로 수정할 수 있다.

- production 페이지가 열리지 않음
- 사용자가 기존 rescue flow를 진행할 수 없는 배포 차단 치명적 회귀
- 데이터 손상
- 보안 또는 credential 노출
- 일반 과목 변경이 위 배포 차단 치명적 회귀를 직접 유발함

artifact drift, rollback 검증 실패 또는 테스트 실패만으로는 운영 예외가 성립하지 않는다. 이러한 신호가 위 배포 차단 치명적 회귀, 데이터 손상 또는 보안 문제를 직접 증명할 때만 해당 예외 범위에서 조사·수정한다.

허용된 수정은 재현된 원인 하나로 제한한다.
신규 ownership 이전이나 장기 마이그레이션 재개로 확장하지 않는다.

## 5. 명시적 재개 절차

Ocean Rescue가 다시 우선순위로 선택되면 과거의 “다음 WP”를 그대로 실행하지 않는다.

1. 최신 `origin/main`과 production artifact를 확인한다.
2. ESM import graph와 legacy fallback의 현재 역할을 확인한다.
3. typecheck, focused static test, browser proof, artifact drift의 현재 baseline을 측정한다.
4. 남은 runtime ownership을 실행 참조 기준으로 재검색한다.
5. 한 failure domain과 한 binary criterion을 선택한다.
6. source/caller/test/cleanup을 최소 범위로 수정한다.
7. 직접 영향 검증 후 필요할 때만 build·artifact·rollback 검증으로 확장한다.
8. 결과를 게시한 뒤 최신 main에서 다음 원인을 다시 선택한다.

과거 계획의 WP 순서, 완료 문자열, evidence 파일 존재는 재개 순서를 결정하지 않는다.

## 6. 작업 분해 원칙

재개 후 각 실행은 다음 형식을 따른다.

```text
한 작업
= 한 runtime ownership 또는 failure domain
= 한 재현 조건
= 한 binary criterion
= 한 독립 검증
```

예시:

- 특정 pointer lifecycle cleanup
- 특정 timer ownership
- 특정 projection sync
- 특정 session activation/shutdown
- 특정 ESM import boundary
- 특정 generated artifact drift
- 특정 rollback failure

아래 항목을 한 번에 묶지 않는다.

- 여러 동물 mission lifecycle
- controller 이전과 production artifact 게시
- browser evidence와 unrelated type cleanup
- runtime 변경과 일정 문서 상태 갱신
- migration 재계획과 구현

## 7. Target-device release와 성능 정책

이 정책은 일정 상태가 아니라 release acceptance와 후속 측정의 역할을 구분한다.

### WP-03A — Target-device release smoke

- 실제 지원 대상 기기에서 핵심 rescue flow와 입력·렌더링을 확인한다.
- **MVP release gate; not a WP-21 production-packaging cutover prerequisite.**
- WP-03A remains mandatory before MVP release.
- No canonical numeric frame-time or FPS SLA is defined.
- PASS 기준은 현재 사용자 흐름을 막는 입력 오류, page error, failed request, 치명적 렌더링 중단이 없는 것이다.

### WP-03B — Reproducible target-device performance harness

- **Classification:** `BACKLOG_NON_BLOCKING`
- 자동화 가능한 frame-time, long-task, memory 또는 interaction latency 측정을 재현 가능한 harness로 수집한다.
- thresholds adopted only after baseline review.
- production build와 target-device 접근이 준비된 뒤 별도 failure domain으로 수행한다.
- WP-03B가 없다는 이유로 현재 production packaging이나 일반 과목 안정화 작업을 차단하지 않는다.

두 항목을 하나의 일정 문자열로 결합하지 않는다. WP-03A는 release acceptance이고 WP-03B는 비차단 성능 계측이다.

## 8. 검증 참고

현재 저장소에 존재하는 대표 명령은 다음과 같다. 동결 중에는 재현된 예외에 직접 필요한 것만 실행한다.

```bash
just check-ocean-rescue-toolchain
just typecheck-ocean-rescue
just check-ocean-rescue-drift
just check-ocean-rescue-rollback
just check-ocean-rescue-sea-turtle-lifecycle-controller
```

실제 명령 이름과 포함 테스트는 최신 `Justfile`을 우선한다.
모든 Ocean Rescue 검증을 관성적으로 실행하지 않는다.

## 9. 문서와 evidence 규칙

- WP 계획·다음 WP·진행 상태는 대화에서 관리한다.
- `docs/plans/PLAN_ocean_rescue_wp*.md`를 만들지 않는다.
- 상태 전용 evidence를 만들지 않는다.
- 테스트에서 `다음 WP`, `현재 WP`, `WP COMPLETE` 같은 일정 상태를 검증하지 않는다.
- 제품 동작, 타입, 빌드, artifact, rollback 계약만 테스트한다.
- 이 문서는 실제 아키텍처 또는 재개 정책이 변경된 경우에만 수정한다.

## 10. 현재 결론

Ocean Rescue 마이그레이션은 삭제되거나 실패한 것이 아니라 **현재 제품 우선순위에 의해 일시 정지된 기술 영역**이다.
다음 실행 작업은 이 문서에서 정하지 않는다.
일반 과목 안정화 exit gate가 닫히거나 사용자가 명시적으로 방향을 바꾼 뒤 최신 저장소 증거로 다시 진단한다.
