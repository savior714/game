# Ocean Rescue Vite · ESM · TypeScript 기술 참고

- **상태:** `STABLE_TECHNICAL_REFERENCE_NOT_CURRENT_PRIORITY`
- **제품 방향 SSOT:** `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`
- **역할:** Ocean Rescue의 현재 build/runtime/rollback 기술 경계 참고

Ocean Rescue feature 자체는 `ACTIVE_PRODUCT_SCOPE.md`에서 **active reward game**으로 분류된다. 이 문서가 stable reference라는 뜻은 Ocean Rescue가 동결되었다는 뜻이 아니다.

반대로 Ocean Rescue가 active라는 이유로 이 문서의 과거 migration 단계나 WP를 자동 재개하지 않는다. 현재 기본 제품 priority는 Math skill/mastery adaptive loop이며, Ocean Rescue 내부 작업은 사용자가 해당 feature/A·B track을 명시적으로 선택했거나 제품 dependency가 실제로 요구할 때 수행한다.

## 1. 현재 architecture baseline

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

실제 최신 파일, import graph, lockfile, build pipeline이 이 참고보다 우선한다.

## 2. 보존할 계약

### Production authority

- `ocean-rescue/index.html`은 generated production artifact다.
- source 변경은 build pipeline을 통해 artifact에 반영한다.
- generated bundle, provenance, registry identity, atlas metadata를 수동 우회 편집하지 않는다.

### ESM과 legacy fallback

- canonical production ESM 경로와 rollback/proof ordered-script 경로는 목적이 다르다.
- legacy fallback은 명시적으로 제거하기 전까지 rollback/proof 계약을 보존한다.
- production과 rollback을 한 원인에서 함께 바꿀 때는 둘의 직접 검증이 필요하다.

### Typed/controller ownership

- TypeScript/ESM 이전 자체를 목표로 삼지 않는다.
- controller는 자신이 소유한 state/event/timer/cleanup 경계를 명확히 가져야 한다.
- host bridge는 필요한 최소 runtime dependency만 전달한다.
- 같은 lifecycle의 source/caller/cleanup/focused test는 하나의 coherent failure domain으로 닫을 수 있다.

### Pointer/timer cleanup

- pointer ID와 capture acquire/release를 일관되게 관리한다.
- `pointerup`, `pointercancel`, pause, menu shutdown에서 transient state를 정리한다.
- timer/resume countdown은 중복 실행되지 않아야 한다.
- session shutdown 뒤 listener, capture, timer가 남지 않아야 한다.

### Deterministic artifact

- 동일 source/lockfile에서 production build가 결정적이어야 한다.
- tracked artifact가 요구될 때 clean rebuild와 일치해야 한다.
- build metadata와 artifact identity를 서로 정합하게 유지한다.

## 3. 제품 관계

Ocean Rescue는 학습 문제를 내부에 넣는 교육게임이 아니다.

```text
Core Quiz skill goal 완료
→ gems + free-time
→ Ocean Rescue 접근
```

이 cross-feature 관계는 이 기술 참고가 아니라 `ACTIVE_PRODUCT_SCOPE.md`가 소유한다. Ocean Rescue PRD는 게임 내부 mission/interaction을 소유한다.

## 4. 작업 선택 규칙

Ocean Rescue 범위가 명시적으로 선택되면 과거 “다음 WP”를 그대로 실행하지 않는다.

1. 최신 `origin/main`과 production artifact 확인
2. 현재 ESM import graph, fallback, focused tests 확인
3. 실제 제품/런타임 gap 하나 선택
4. 한 failure domain + 한 binary criterion으로 수정
5. 필요한 typecheck/browser/build/artifact/rollback 검증만 직접 위험에 맞춰 실행
6. 게시 후 다음 원인은 최신 main에서 다시 선택

A/B track runbook의 내부 `ACTIVE` 문자열은 명시적 A/B 요청 안에서만 의미가 있으며 범위 미지정 default priority를 만들지 않는다.

## 5. 대표 검증 명령

```bash
just check-ocean-rescue-toolchain
just typecheck-ocean-rescue
just check-ocean-rescue-drift
just check-ocean-rescue-rollback
```

모든 Ocean Rescue 검증을 관성적으로 실행하지 않고 현재 변경 위험에 직접 필요한 범위부터 실행한다.

## 6. Target-device policy

- 실제 지원 대상 태블릿에서 핵심 rescue flow와 입력·렌더링을 release acceptance로 확인한다.
- canonical numeric FPS SLA는 현재 고정하지 않는다.
- 입력 오류, page error, failed request, 치명적 렌더링 중단이 사용자 흐름을 막지 않아야 한다.
- reproducible performance harness는 실제 필요/측정 가설이 생길 때 별도 작업으로 수행한다.

## 7. 문서 규칙

- 이 문서에 WP 진행률이나 다음 작업을 누적하지 않는다.
- 상태 전용 evidence를 만들지 않는다.
- 제품 priority는 `ACTIVE_PRODUCT_SCOPE.md`를 따른다.
- architecture/build/rollback 경계가 실제로 바뀐 경우에만 이 문서를 수정한다.
