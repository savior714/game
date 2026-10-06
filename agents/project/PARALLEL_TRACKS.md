---
scope: project
status: active
---
<!-- Language: ko -->

# A/B 병렬 개발 트랙

이 문서는 AidenGame 상시 병렬 A/B 개발 트랙의 정의, 트랙 간 경계, 트랙 런북 계약을 소유한다.
exclusive 자원 reservation 자체는
[`../workflows/work-package-claim.md`](../workflows/work-package-claim.md)가, 실행·게시 lifecycle은
[`../core/execution.md`](../core/execution.md)가 소유한다.

## 1. 트랙 선택

사용자가 `A트랙` 또는 `B트랙`이라고 지시하면 아래 정의를 고정된 의미로 사용한다. 새 세션이나 후속
작업에서 어느 하위 분야를 뜻하는지 다시 묻지 않는다.

명시적인 A/B 트랙 요청은 사용자가 현재 요청에서 개발 범위를 지정한 것으로 본다. 제품 SSOT의 범위
미지정 기본 방향과 다르더라도 이 트랙 계약을 따른다. 최신 `origin/main`과 가장 가까운 technical spec을
읽고, 해당 트랙의 쓰기 범위 안에서 다른 트랙과 독립적으로 완료할 수 있는 가치가 가장 높은 다음 작업
하나를 선정한다.

- **A — 게임 런타임·플레이**: 실제 게임 실행 중 플레이어에게 일어나는 동작을 소유한다. 전투, 월드,
  엔티티, 인벤토리, 진행, 경제·보상 규칙, 상태 머신(FSM), HUD, 입력·상호작용, controller,
  pause/timer/resume, 런타임 상태 전이, 실제 브라우저 플레이 동작과 DragonBones 등 이미 확정된 자산
  계약을 소비하는 런타임 loader·renderer가 A다. 자산을 어떻게 제작·생성하는지보다 게임이 그 자산을 어떻게
  읽고 표시하고 플레이 규칙에 연결하는지가 A의 책임이다.
- **B — 에셋·콘텐츠 제작·생성 파이프라인**: 게임 자산의 제작 원본부터 생성·검증·게시 가능한 산출물까지의
  생산 체인을 소유한다. DragonBones/GIMP 제작 도구, source/review/handoff 자산, asset metadata·schema,
  exporter/CLI, preview/validator, atlas·registry·manifest 생성, provenance, deterministic
  generation/rebuild, 생성 산출물의 무결성 검증이 B다. `domains/ocean-rescue/assets/source/**`,
  `assets/review/**`, `assets/handoff/**`, `assets/generated/**`처럼 생산 체인에 속하는 자산 경로는
  기본적으로 B 의미 영역으로 본다.

## 2. 트랙 경계 운영 규칙

- 다른 트랙의 코드·자산·테스트는 원인과 소비/생산 계약 확인을 위해 읽을 수 있지만 수정하지 않는다.
- `asset metadata/schema → manifest/atlas/registry → runtime loader/renderer`처럼 B가 생산하고 A가
  소비하는 계약은 두 트랙이 동시에 수정하지 않는다.
- 생산 계약 변경이 필요하면 B가 metadata/schema와 생성·검증 체인을 먼저 확정하고 직접 검증한 뒤
  `origin/main`에 게시한다. 그 다음 A가 게시된 계약만 기준으로 loader/renderer 소비 변경을 별도 단일
  작업으로 수행한다.
- A 작업자는 런타임 문제를 닫기 위해 B의 schema·manifest 형식·생성기를 임의로 바꾸지 않는다. B 작업자는
  파이프라인 문제를 닫기 위해 A의 플레이 상태·controller·런타임 loader 동작까지 확장하지 않는다.
- 예상 쓰기 범위가 A와 B 양쪽에 걸치면 현재 상시 병렬 작업으로 실행하지 않는다. 생산측 선행 계약 또는
  소비측 후속 작업으로 분리하고, 현재 트랙에서 독립 완료 가능한 다른 후보를 선택할 수 있다.
- 단순한 `origin/main` 선행이나 non-fast-forward는 트랙 충돌이 아니다. 최신 main에 재적용했을 때
  파일·계약 중첩이 없고 focused 검증이 유지되면 정상 병렬 진행으로 본다.
- 실제 충돌이 발견되면 추상적인 예방 규칙을 늘리지 않는다. 반복된 실제 사례를 근거로 특정 경로의 소유권,
  생산/소비 순서, 공용 직렬 영역 등 필요한 경계만 최소한으로 보정한다.
- 사용자가 `A트랙/B트랙에서 이어갈 다음 작업을 분석`하라고 하면 전투·HUD·DragonBones·atlas 같은 하위
  분야를 다시 선택하라고 묻지 않는다. 최신 저장소 상태와 최근 완료 작업을 기준으로 해당 트랙 안에서
  독립적으로 닫히는 다음 단일 failure domain을 스스로 선택한다. 로컬 프롬프트가 요청된 경우 작업 선택까지
  먼저 수행하고 [`LOCAL_LLM_DELEGATION.md`](LOCAL_LLM_DELEGATION.md)의 즉시 발행 원칙에 따라 재확인 없이
  프롬프트를 발행한다.

## 3. 트랙이 아닌 범위

root dependency/toolchain, 공용 lockfile, 저장소 전체 CI·verify 설정처럼 양쪽 트랙이 함께 소비하는
변경은 A/B 상시 병렬 작업 밖의 직렬 통합 작업으로 처리한다.

## 4. 명시적 트랙 런북의 10개 순차 작업 리필

사용자가 특정 A/B 트랙의 런북을 **작성하거나 갱신**하라고 명시적으로 요청한 경우에만, 일반적인 transient
queue 금지의 제한적 예외로 해당 런북의 pending 작업 목록을 최신 `origin/main`, 트랙 계약, 직접
테스트·runtime 근거, 관련 최근 commit에서 다시 구성한다.

- dependency 순서로 한 번에 하나씩 실행 가능한 pending work package를 **정확히 10개** 유지한다.
- 완료된 항목은 목록에서 제거하고 완료 이력으로 남겨 수를 채우지 않는다.
- 미완료이거나 보완이 필요한 항목은 기존 문구를 유지하지 않는다. 누락된 behavior·invariant·evidence
  gap·verification을 제목과 criterion에 명시한 새 보완 work package로 교체해 목록에 다시 넣는다.
- 각 항목은 하나의 failure domain, primary criterion, bounded write boundary, direct verification을
  가져야 한다.
- 비워진 자리는 최신 근거가 있는 항목만으로 채운다. stale label, 모호한 placeholder, fabricated work로
  10개를 채우지 않는다.

이 절은 명시적인 트랙 런북 작성·갱신 요청에만 적용하며, 일반 task 실행이나 unrelated repair를
자동으로 확장하지 않는다.

## 5. 검증과 보고

트랙 작업도 하나의 failure domain과 하나의 primary criterion을 유지한다. 판정과 보고 형식은
[`../core/verification.md`](../core/verification.md)와
[`../core/reporting.md`](../core/reporting.md)가 소유한다.