---
id: opencode_tools
scope:
- .agents/core/**
domain: core
status: active
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_auxiliary_core_contract_consistency.py
---
<!-- Language: ko -->

# OpenCode · local LLM 실행 규율

이 문서는 LM Studio와 OpenCode를 사용하는 local LLM이 AidenGame 작업을 안정적으로 수행하기 위한 최소 규율을 정의한다.
실제 tool 이름과 인자는 현재 OpenCode 세션의 schema가 authority다.

## 1. 도구 호출 안정성

- local model이 여러 tool call을 한 응답에 안정적으로 직렬화하지 못하면 한 assistant turn에 도구 하나만 호출한다.
- tool call이 필요할 때 pseudo JSON, XML marker, 설명문을 사용자 본문에 섞지 않는다.
- 도구 결과를 확인한 뒤 다음 호출을 결정한다.
- 동일 오류에 동일 인자로 반복 호출하지 않는다.
- structural schema 오류는 retry보다 인자와 tool descriptor 재확인이 우선이다.

## 2. workspace

- 작업 root는 최신 `origin/main`에서 만든 안정적인 game worktree다.
- 기본 경로는 `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`다.
- 다른 저장소 경로나 OS 임시 디렉터리를 source root로 사용하지 않는다.
- read, edit, lint, test, browser가 같은 workspace와 CWD를 사용해야 한다.

## 3. 기본 작업 순서

1. `git status`와 현재 branch/HEAD를 확인한다.
2. `AGENTS.md`, `PROJECT_RULES.md`, 가장 가까운 spec을 읽는다.
3. 대상 구현과 focused test를 읽는다.
4. 한 failure domain과 binary criterion을 고정한다.
5. 최소 수정한다.
6. 직접 검증한다.
7. diff scope와 최신 remote main을 확인한다.
8. fast-forward로만 게시한다.

범위가 없는 요청은 현재 일반 과목 안정화 방향을 따른다.
Ocean Rescue와 실험 기능을 최근 커밋만 보고 자동 재개하지 않는다.

## 4. 읽기와 검색

- glob은 경로 후보를 찾는 데 사용한다.
- grep은 symbol·문구·실행 참조를 찾는 데 사용한다.
- read 결과에서 직접 수정할 exact block을 확보한다.
- 검색 결과가 존재한다는 사실만으로 결함 판정을 만들지 않는다.
- 큰 파일은 symbol 또는 관련 구간으로 좁혀 읽는다.

## 5. 편집

현재 OpenCode 세션에 `edit`와 `write`가 제공되는 경우:

- 기존 파일의 부분 수정은 `edit`를 우선한다.
- 신규 파일 또는 검증된 전체 교체만 `write`를 사용한다.
- 현재 tool schema가 요구하는 path와 key casing을 그대로 따른다.
- old text는 최신 파일과 정확히 일치해야 한다.
- no-change 응답이면 재호출하지 않고 파일을 다시 읽는다.
- 한글이나 긴 Markdown 때문에 tool parser가 실패하면 안전한 shell heredoc 또는 Python writer를 사용할 수 있으나 후보 diff를 반드시 확인한다.

도구 이름이나 인자를 이 문서의 과거 예시로 추측하지 않는다.

## 6. 질문

- 저장소 증거로 해소할 수 있는 질문은 local model이 먼저 조사한다.
- 사용자 답에 따라 동작·계약·범위·합격 기준이 달라질 때만 질문한다.
- 한 번에 결정축 하나만 묻는다.
- 권장안은 정확히 하나로 표시한다.
- 이미 주어진 답을 다시 묻지 않는다.

## 7. 로컬 프롬프트 소비

프론티어 모델이 준 프롬프트에서 다음만 실행한다.

- 현재 objective
- included / excluded scope
- Do / Do not
- 쓰기 허용 범위
- verification
- binary criterion
- stop condition

향후 단계나 과거 이력을 자체적으로 확장하지 않는다.
허용 파일 범위는 쓰기 경계이며 조사·읽기 범위와 혼동하지 않는다.

## 8. 결과 보고

```text
RESULT: PASS | BLOCKED
CHANGE: <한 문장>
VERIFY: <한 문장>
```

실제 push 시에만 `COMMIT`, 중단 시에만 `BLOCKER / NEXT`를 추가한다.
실행하지 않은 테스트를 PASS로 보고하지 않는다.
