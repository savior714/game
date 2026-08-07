# Local LLM Delegation — AidenGame

## 목적

프론티어 코디네이터는 최신 저장소와 현재 라이브러리 지식을 보정하고, 로컬 LLM은 그 경계 안에서 구현·검증·게시한다. 이후 코디네이터가 실제 커밋과 브라우저 증거를 독립 리뷰한다.

이 문서는 root `AGENTS.md`, `PROJECT_RULES.md`, 현재 product direction과 가장 가까운 spec을 보완한다.

## 협업 역할 모델

이 문서의 프론티어 코디네이터는 세부 구현 명령을 작성하는 감독자가 아니라, 사용자와 게임의 방향·우선순위·완료 기준을 함께 정하는 페어 프로그래머이자 로컬 결과의 독립 리뷰어다.

역할은 다음처럼 나눈다.

- 사용자와 프론티어 코디네이터는 플레이 경험, 학습 의미, 현재 결함의 실제 영향, 작업 우선순위와 acceptance criterion을 함께 정한다.
- 프론티어 코디네이터는 latest `origin/main`, 현재 브라우저·라이브러리 동작과 실제 product direction을 확인해 로컬 모델의 지식 공백만 보정한다.
- local executor는 authorized write scope 안에서 owner, controller/module 구조, 테스트 위치와 구현 방법을 자율 결정한다.
- 프론티어 코디네이터는 게시된 commit, diff와 실제 browser/runtime evidence를 다시 읽고 게임 규칙, exactly-once 입력 효과, 상태 전이, 회귀 위험과 사용자 체감을 판정한다.
- PASS이면 사용자와 다음 우선 작업을 고른다. 보완이 필요하면 가장 중요한 다음 failure domain 하나만 선택해 짧은 delta prompt로 재위임한다.
- 좁은 수정은 프론티어 코디네이터가 직접 처리할 수 있지만, 기본 협업 모델은 방향·판정·리뷰와 구현 실행을 분리한다.

짧은 프롬프트는 자유 방임이 아니다. 구현 전에 제품 계약과 판정 기준을 고정하고, 구현 후에는 실제 브라우저 증거로 엄격하게 검토한다.

## 기본 순환

```text
사용자와 frontier coordinator가 게임 방향·우선순위·판정 기준을 함께 결정
→ latest origin/main과 실제 버전 조사
→ 최신 주의점과 단일 failure domain을 짧게 전달
→ local executor가 자율 구현·focused 검증·main 게시
→ 실제 commit/diff/runtime 독립 리뷰
→ 사용자와 다음 우선 작업을 고르거나 남은 다음 단일 failure domain만 delta prompt로 전달
```

## 지식 근거 우선순위

1. latest `origin/main`의 code, tests, config, vendor artifact와 spec
2. 실제 설치·vendored package의 local source, type와 runtime behavior
3. exact version 공식 문서, migration guide와 release note
4. Context7 같은 version-aware documentation tool
5. 모델의 기존 기억

문서 도구의 이름과 호출 형식을 영구 고정하지 않는다. 실행 시 현재 MCP/CLI schema와 help를 확인한다. Context7 사용 시 가능한 경우 exact version을 고르고, 한 질의에는 한 개념만 넣는다.

## 프론티어 코디네이터가 프롬프트 전에 할 일

- 사용자와 현재 결함의 실제 플레이 영향, 우선순위와 완료 기준 정렬
- 최신 main에서 현재 objective와 product direction 확인
- manifest, vendor bundle, runtime file, browser target 확인
- 작업에 필요한 최신 변경점·주의점만 2~5개로 압축
- 한 failure domain, 한 재현 조건, 한 primary criterion 선택
- authorized write scope, out-of-scope, 변경 금지 계약과 direct verification 고정

파일별 구현 정답이나 전체 WP roadmap은 기본 프롬프트에 넣지 않는다.

## 로컬 executor의 자율 범위

자율 결정 가능:

- 허용 범위 안의 함수·module·controller 구조
- shared owner와 domain owner 중 적합한 수정 위치
- focused test와 browser fixture 배치
- 가장 짧은 재현·검증 명령
- 같은 root cause와 rollback boundary의 strongly coupled source/test 수정

변경 금지:

- 문제풀이·게임 규칙과 콘텐츠 의미
- 점수·진행·저장·unlock·재시작 계약
- 입력 한 번에 직접 효과 한 번이라는 계약
- supported browser/device와 정적 HTML/CSS/JavaScript 경계
- authorized write scope와 acceptance criterion
- 기존 Canvas/WebGL, 접근성 또는 persistence 경계를 근거 없이 제거하는 변경

변경 금지 대상을 바꿔야 완료할 수 있으면 `BLOCKER: DECISION_REQUIRED`로 중단한다.

## 외부 문서를 확인할 조건

다음이 구현 판단에 중요하면 모델 기억만 사용하지 않는다.

- PixiJS, Playwright, browser API, Canvas/WebGL, bundler 또는 test runner
- deprecated API, changed default, event/lifecycle semantics
- pointer/touch/keyboard, timer, animation, pause/resume, visibility
- renderer/resource ownership, DPR, resize 또는 fallback
- 현재 브라우저와 test harness의 차이

공식 근거가 불충분하면 새 fallback을 추측으로 추가하지 말고 actual runtime과 직접 브라우저 evidence로 판정한다.

## 프로젝트별 sibling inventory

일반 문제풀이 작업 전 읽기 전용으로 확인:

- `domains/math/`, `domains/korean/`, `domains/english/`, `domains/science/`
- 대응하는 `shared/` UI, state, storage와 event owner
- 직접 관련 browser/unit tests

Ocean Rescue를 사용자가 명시적으로 재개한 경우 확인:

- lifecycle/controller와 host bridge
- mission FSM, persistence와 unlock
- renderer/scene/resource owner와 Canvas fallback
- input, timer, pause/resume와 stale callback 경계
- 직접 관련 runtime/browser tests

inventory는 쓰기 범위를 자동 확대하지 않는다. 같은 shared owner 수정으로 같은 root cause와 rollback boundary를 닫을 때만 하나의 failure domain에 포함한다.

## 짧은 프롬프트 형식

```text
OBJECTIVE
CURRENT EVIDENCE
VERSION / CURRENT-DOC NOTES
IN_SCOPE
OUT_OF_SCOPE
DO
DO_NOT
PRIMARY_CRITERION
DIRECT_VERIFY
OPTIONAL_SYSTEM_SMOKE
STOP
PUBLISH
REPORT
```

프롬프트는 root `AGENTS.md`, 이 파일, 가장 가까운 spec을 먼저 읽으라고 명시한다.

## 위험 기반 검증

테스트 우선 또는 구현과 동시에 테스트:

- 이벤트 중복 연결과 ownership 충돌
- 입력 한 번의 중복 handler/render/request
- 점수·진행·저장·unlock 데이터
- 재시작·복구·중단 후 재개
- 복잡한 상태 전이와 stale timer/callback
- 이미 발생한 회귀

구현 우선 후 실제 브라우저 검증 가능:

- 화면 구성과 스타일
- 애니메이션과 게임 감각
- 시각 효과와 콘텐츠 표현
- 탐색적 UI
- 단순 dependency/toolchain patch

현재 작업은 V1 primary criterion과 V2 direct-impact closure로 판정한다. V3의 독립 실패는 `DISCOVERED_FAILURE`로 분리한다.

## 커밋 이후 리뷰

코디네이터는 다음을 확인한다.

- 커밋이 최신 main에 실제 게시됐는가
- diff가 허용 범위 안인가
- API와 runtime 사용법이 actual version에서 유효한가
- shared/domain owner의 중복 ownership이 남았는가
- 실제 입력 한 번의 직접 효과가 정확히 한 번인가
- 테스트가 사용자 계약을 판정하는가
- baseline, snapshot, broad ignore, fallback 또는 unrelated cleanup으로 실패를 숨기지 않았는가
- 사용자와 합의한 플레이 경험과 실제 결과가 일치하는가

여러 문제가 발견되어도 다음 프롬프트에는 한 failure domain만 넣는다. 이전 전체 프롬프트와 완료된 단계를 반복하지 않는다. 현재 결과를 판정한 뒤 사용자와 다음 우선 작업을 고른다.

## 완료 보고

```text
RESULT: PASS | BLOCKED
CHANGE: <one sentence>
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED
DISCOVERED_FAILURE: <one independent failure domain or NONE>
COMMIT: <sha, only when published>
```
