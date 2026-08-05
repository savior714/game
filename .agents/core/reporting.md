---
scope:
- '*'
always_apply: false
priority: 1
domain: core
---
<!-- Language: ko -->
# Reporting Protocol

이 문서는 에이전트의 간결한 진행·완료 보고 계약을 정의한다.
실행 규칙은 루트 `AGENTS.md`, 정적 검증 규칙은 [verification.md](verification.md)가 우선한다.
과거의 Blueprint·Linear·장문 상태 보고 절차는 일반 작업의 완료 조건이 아니다.

## 1. Reporting Principles

### 1.1 기본 보고

정상 완료 보고는 다음 필드만 사용한다.

```text
RESULT: PASS | BLOCKED
CHANGE: <무엇을 바꿨는지 한 문장>
VERIFY: <실행한 판정 기준과 결과 한 문장>
```

- 실제 게시 시에만 `COMMIT`을 추가한다.
- 중단 시에만 `BLOCKER`와 `NEXT`를 추가한다.
- claim ID, task key, lease, activation SHA, start window, dependency graph 같은 내부 조정 메타데이터를 반복하지 않는다.
- 변경 파일 목록이나 상세 로그는 실패 원인 또는 사용자가 요청한 경우에만 추가한다.

### 1.2 상세 보고

다음 경우에만 필요한 근거를 추가한다.

- 검증 실패 또는 실행 불가
- 안전하게 해결할 수 없는 blocker
- 게시 충돌이나 최신 main 재적용 실패
- 사용자가 상세 보고를 명시적으로 요청

상세 보고도 같은 내용을 여러 필드로 반복하지 않는다.

### 1.3 금지 사항

- 증거 없는 완료 선언
- 실행하지 않은 criterion의 PASS 처리
- `Final Completion Report` 같은 장문 템플릿
- task/claim/lease/SHA 목록이 실제 변경 설명보다 커지는 보고
- workaround를 정상 해결로 표현
- broad ignore, baseline, snapshot, skip, mock 또는 fail-open fallback으로 만든 녹색 결과를 PASS로 보고
- LSP·typecheck·lint 오류를 `pre-existing`, `unrelated`, `out of scope`라는 이유만으로 경고 처리하고 PASS

### 1.4 제안의 책임

아키텍처·스택·보안·workflow 정책을 변경하자는 제안에는 다음을 포함한다.

1. 확인된 필요성
2. 예상 위험과 방지책
3. 검증 가능한 근거 또는 저장소 contract

추측만으로 새 governance를 추가하지 않는다.

### 1.5 세션 종료 검증 — 필수

저장소 파일을 생성·수정·삭제한 뒤 완료 보고 전에 [verification.md](verification.md) §2.3을 따른다.

1. 안정적인 source worktree root에서 `just lint-turn-end` 또는 저장소가 요구하는 동등한 정적 게이트를 실행한다.
2. 현재 변경으로 새로 생긴 오류와 수정 파일·직접 영향 모듈의 오류를 먼저 하나의 failure domain으로 수정한다.
3. 같은 진단 명령으로 해당 failure domain이 사라졌는지 독립 검증한다.
4. 다른 파일의 기존 LSP·typecheck·lint 오류가 드러나면 단순 경고로 넘기지 않는다. 다음 정적 failure domain 하나를 선택해 순차적으로 해결한다.
5. 잘못된 workspace root, SDK/interpreter, dependency, stale cache/index, generated/vendor 오분석이 원인이면 production code를 억지로 바꾸지 말고 환경·설정을 수정한 뒤 같은 진단을 재실행한다.
6. 오류가 남았고 안전하게 해결할 수 없다면 `RESULT: BLOCKED`로 보고하고 정확한 진단·재현 명령·차단 원인을 남긴다.

다음 상태에서 `RESULT: PASS`를 금지한다.

- 현재 변경 또는 직접 영향 범위의 정적 오류가 남음
- 이번 작업에 요구되는 정적 게이트가 실패함
- 진단을 실행하지 않았거나 exit code를 무시함
- broad suppression이나 검사 범위 축소로만 녹색이 됨

### 1.6 사용자 응답

- 사용자가 개발 용어를 직접 사용하면 정확한 기술 용어로 답한다.
- 그렇지 않으면 무엇이 달라졌는지, 어떻게 검증했는지를 먼저 설명한다.
- 질문이 필요할 때만 결정 가능한 선택지를 제시한다.
- 완료 후 불필요한 후속 선택지나 장기 backlog를 자동으로 나열하지 않는다.

## 2. Workaround Accountability

임시 우회를 사용했다면 `PASS`로 포장하지 않는다.

```text
RESULT: BLOCKED
CHANGE: <안전하게 완료한 범위>
VERIFY: <확인된 결과>
BLOCKER: <근본 원인 또는 미충족 criterion>
NEXT: <재개에 필요한 단일 조건>
```

영구 fallback이 필요하면 별도의 제품 설계와 회귀 테스트가 있어야 한다.

## 3. Zero-Leak

보고·터미널 출력·로그에 API key, token, cookie, password, `.env` 원문을 포함하지 않는다.
민감값이 노출됐을 가능성이 있으면 값을 재인용하지 말고 즉시 중단·회전 절차를 따른다.
