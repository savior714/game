# Local LLM Delegation — AidenGame

## 목적

프론티어 모델은 사용자와 게임 방향·우선순위·완료 기준을 정하고, 로컬 LLM은 저장소 안에서 구현 방법을 자율 결정한다. 게시 후에는 프론티어 모델이 실제 diff와 브라우저 증거를 독립 리뷰한다.

이 문서는 root 지침과 가까운 product/spec 문서를 보완한다. 프롬프트에서 이미 자동 로드되는 공통 규칙을 반복하지 않는다.

## 기본 흐름

```text
사용자와 다음 작업 선택
→ 필요한 최신 지식만 짧게 보정
→ 로컬 LLM이 구현·focused 검증·main 게시
→ 실제 commit/diff/browser evidence 리뷰
→ 다음 작업 또는 단일 보완 작업 선택
```

## 지식 확인

구현 판단은 다음 순서를 따른다.

1. 최신 `origin/main`의 코드·테스트·설정·vendor artifact
2. 설치된 package의 source/type와 실제 browser behavior
3. 해당 버전의 공식 문서와 release note
4. Context7 같은 version-aware 문서 도구
5. 모델 기억

PixiJS, Playwright, browser API, Canvas/WebGL, timer·event lifecycle처럼 현재 버전 동작이 중요할 때만 외부 문서를 확인한다. 문서 도구 사용법은 매번 설명하지 않는다.

## 기본 프롬프트

보통 다음 세 부분이면 충분하다.

```text
TASK
<무엇을 고치거나 구현할지, 현재 확인된 증거와 함께 2~4문장>

CURRENT NOTES
<현재 버전에서 특히 주의할 점 0~3개. 없으면 생략>

DONE WHEN
<플레이어에게 보이는 단일 결과와 가장 짧은 직접 검증>

결과는 CHANGE / VERIFY / COMMIT만 보고한다.
```

기본 프롬프트에 다음을 자동으로 넣지 않는다.

- `IN_SCOPE`, `OUT_OF_SCOPE`, `DO`, `DO_NOT`, `STOP`, `PUBLISH` 고정 항목
- 파일별 구현 절차와 controller 정답
- 이미 저장소 지침에 있는 Git·worktree·보고 규칙
- 전체 WP roadmap
- 필요하지 않은 full-suite나 다중 브라우저 반복

구현 파일, owner, test 위치와 명령은 로컬 LLM이 저장소를 읽고 정한다.

## 제약을 추가할 때

다음처럼 게임 계약이나 회귀 위험이 큰 경우에만 명시적 경계를 추가한다.

- 점수·진행·저장·unlock·재시작
- 입력 한 번의 중복 handler/render/request
- timer·pause/resume·stale callback
- shared owner와 domain owner의 중복 소유
- persistence와 브라우저 fallback

이 경우에도 필요한 경계 한두 개와 직접 브라우저 검증만 적는다. 가능한 모든 금지사항을 미리 나열하지 않는다.

## 로컬 LLM의 재량

로컬 LLM은 목표와 게임 규칙을 바꾸지 않는 범위에서 다음을 자율 결정한다.

- 수정 owner와 파일
- 함수·module·controller 구조
- 필요한 sibling 조사 범위
- focused unit/browser test 배치
- 가장 짧은 실제 브라우저 검증

독립된 다른 결함은 현재 작업에 섞지 않고 보고만 한다.

## 게시 후 리뷰

프론티어 모델은 실제 증거를 확인한다.

- 최신 main의 실제 diff
- 현재 runtime에서 유효한 API인지
- 입력 한 번의 직접 효과가 한 번인지
- 점수·진행·저장·상태 전이 계약 유지 여부
- 테스트가 사용자에게 보이는 완료 조건을 판정하는지
- 불필요한 fallback·ignore·snapshot 갱신·범위 확장 여부

문제가 여러 개여도 다음 프롬프트에는 가장 중요한 한 가지 보완만 넣는다.
