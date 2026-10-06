# Local LLM Delegation — AidenGame

<!-- Language: ko -->

이 문서가 로컬 실행 프롬프트의 발행 원칙과 구성 계약을 소유한다.
프론티어 모델은 사용자와 게임 방향·우선순위·완료 기준을 정하고, 로컬 LLM은 저장소 안에서 구현 방법을
자율 결정한다. 게시 후에는 프론티어 모델이 실제 diff와 브라우저 증거를 독립 리뷰한다.
실행 순서는 [`../core/execution.md`](../core/execution.md), 계획·WP 상태는
[`../core/planning.md`](../core/planning.md)가 함께 소유한다.

## 1. 기본 흐름

```text
사용자와 다음 작업 선택
→ 필요한 최신 지식만 짧게 보정
→ 로컬 LLM이 구현·focused 검증·main 게시
→ 실제 commit/diff/browser evidence 리뷰
→ 다음 작업 또는 단일 보완 작업 선택
```

## 2. 발행 원칙

- 로컬 LLM용 프롬프트는 사용자의 요청과 최신 저장소 증거로 objective, scope, criterion을 합리적으로
  확정할 수 있으면 별도의 의도 재확인·승인 요청 없이 즉시 발행한다.
- “제가 이렇게 해석했습니다. 이대로 진행해도 되는 게 맞습니까?”와 같은 확인 전용 turn, 승인 대기,
  범위 재진술 후 재승인을 기본 절차로 만들지 않는다.
- 사용자가 범위를 수정하면 최신 지시를 즉시 반영하고, 새 지시 자체가 실행 가능하면 다시 승인받지
  않는다.
- 사소한 모호성은 사용자의 현재 요청, 제품 SSOT인
  [`ACTIVE_PRODUCT_SCOPE.md`](../../docs/specs/product/ACTIVE_PRODUCT_SCOPE.md), 최신 `origin/main`,
  가장 가까운 technical spec과 기존 저장소 계약으로 해소하며 확인차 되묻지 않는다.
- 질문은 `verification.md` §10의 `DECISION_REQUIRED` 조건으로 제한한다. 그 외 구현 세부사항은 로컬
  작업자가 `DECISION BOUNDARY` 안에서 스스로 결정한다.
- 발행 전에 objective가 사용자의 명시적 범위 또는 제품 SSOT의 현재 개발 방향/active feature와 정합한지
  확인한다. 제품 SSOT에서 frozen인 범위는 사용자가 현재 요청에서 재개를 명시하지 않았다면 구현 프롬프트
  를 발행하지 않는다.
- 범위가 지정되지 않았다면 제품 SSOT의 current development priority를 기준으로 삼고, 과거 runbook,
  완료 보고, WP 번호만으로 다른 backlog를 자동 승격하지 않는다.

## 3. 프롬프트 구성

프롬프트는 아래 항목을 빠짐없이 전달한다. 구현 파일, owner, test 위치와 명령은 로컬 LLM이 저장소를
읽고 정하게 하며 프롬프트에 나열하지 않는다.

- 현재 objective와 대상 failure domain 또는 검증 가설
- 대상 저장소·기능과 변경 허용 범위
- included / excluded scope와 변경 금지 계약
- Do / Do not
- primary acceptance
- direct verification와 선택적 system smoke
- stop condition과 예상 최종 상태

짧게 전달할 때는 다음 최소 형태를 사용한다.

```text
TASK
<무엇을 고치거나 구현할지, 현재 확인된 증거와 함께 2~4문장>

CURRENT NOTES
<현재 버전에서 특히 주의할 점 0~3개. 없으면 생략>

DONE WHEN
<플레이어에게 보이는 단일 결과와 가장 짧은 직접 검증>
```

두 형태는 같은 계약을 표현한다. 최소 형태를 쓰더라도 objective, scope, acceptance와 stop condition은
생략하지 않는다.

## 4. Do / Do not

- `DO`에는 최소 diff를 지시하지 않는다. 수정 전 shared owner와 sibling contract를 읽어 under-fixing
  여부를 판정하고, 같은 root cause·invariant·rollback boundary이면 필요한 production/type/test 범위까지
  coherent하게 닫도록 명시한다.
- `DO_NOT`에는 미래 capability를 위한 speculative abstraction과 unrelated cleanup을 금지한다. 현재 root
  cause를 닫는 데 필요한 작은 refactor나 testability 개선은 금지하지 않는다.

## 5. Acceptance 기준

acceptance는 증상 한 건의 GREEN에 그치지 않는다.

- shared root cause가 leaf workaround로 남지 않았는가
- 동일 invariant가 새로 중복 구현되지 않았는가
- 실제 사용자 입력 경로에서 입력 한 번의 직접 효과가 정확히 한 번인가

## 6. 크기와 workspace 제약

- 현재 package에 필요한 delta만 포함하고 최대 700줄을 넘기지 않는다.
- source workspace는 안정적인 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>` 하나로
  고정한다.
- 일반 병렬 prompt에는 reservation metadata를 넣지 않는다. exclusive 자원이 실제로 필요한 경우에만
  [`../workflows/work-package-claim.md`](../workflows/work-package-claim.md)의 block을 넣는다.
- WP 작업 프롬프트에는 계획 파일, WP 상태 문서, 상태 전용 evidence 생성 지시를 넣지 않는다.
- 이미 저장소 지침에 있는 Git·worktree·보고 규칙 장문을 복사하지 않는다.

## 7. 지식 확인

구현 판단은 다음 순서를 따른다.

1. 최신 `origin/main`의 코드·테스트·설정·vendor artifact
2. 설치된 package의 source/type과 실제 browser behavior
3. 해당 버전의 공식 문서과 release note
4. Context7 같은 version-aware 문서 도구
5. 모델 기억

PixiJS, Playwright, browser API, Canvas/WebGL, timer·event lifecycle처럼 현재 버전 동작이 중요할 때만
외부 문서를 확인한다. 문서 도구 사용법은 매번 설명하지 않는다.

## 8. 제약을 추가할 때

다음처럼 게임 계약이나 회귀 위험이 큰 경우에만 명시적 경계를 추가한다.

- 점수·진행·저장·unlock·재시작
- 입력 한 번의 중복 handler/render/request
- timer·pause/resume·stale callback
- shared owner와 domain owner의 중복 소유
- persistence와 브라우저 fallback

이 경우에도 필요한 경계 한두 개와 직접 브라우저 검증만 적는다. 가능한 모든 금지사항을 미리 나열하지
않는다.

## 9. 로컬 LLM의 재량

로컬 LLM은 목표와 게임 규칙을 바꾸지 않는 범위에서 다음을 자율 결정한다.

- 수정 owner와 파일
- 함수·module·controller 구조
- 필요한 sibling 조사 범위
- focused unit/browser test 배치
- 가장 짧은 실제 브라우저 검증

독립된 다른 결함은 현재 작업에 섞지 않고 `DISCOVERED_FAILURE`로만 보고한다.

## 10. 게시 후 리뷰

프론티어 모델은 실제 증거를 확인한다.

- 최신 main의 실제 diff
- 현재 runtime에서 유효한 API인지
- 입력 한 번의 직접 효과가 한 번인지
- 점수·진행·저장·상태 전이 계약 유지 여부
- 테스트가 사용자에게 보이는 완료 조건을 판정하는지
- 불필요한 fallback·ignore·snapshot 갱신·범위 확장 여부

문제가 여러 개여도 다음 프롬프트에는 가장 중요한 한 가지 보완만 넣는다.