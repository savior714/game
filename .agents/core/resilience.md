---
scope:
- '*'
always_apply: false
priority: 1
domain: core
---
<!-- Language: ko -->

# Retry & Resilience

본 문서는 예외 상황(타임아웃, 연결 끊김 등) 발생 시 에이전트의 복구 및 재시도 전략을 정의합니다.

---

## 1. Retry Triggers

다음 상황이 발생하면 재시도 전략을 가동합니다.
- `terminated` (강제 종료)
- `timeout` (시간 초과)
- `context_length_exceeded` (컨텍스트 초과)
- `connection_reset` (연결 초기화)
- `rate_limit` (요청 제한)

---

## 2. Failure Classification

모든 tool 실패는 재시도 전 반드시 다음 중 하나로 분류합니다.

### Security Guard (non-retryable, immediate stop)

- **Credential Leak Risk**: 에러 메시지나 터미널 출력에 API Key, 비밀번호, 토큰 등 민감한 자격 증명이 포함되어 있을 가능성이 감지된 경우.
- Action:
  1. 즉시 재시도 및 모든 도구 호출을 중단한다.
  2. 사용자에게 비밀 값 노출 위험을 정직하게 알리고, 키 회전(재발급) 및 안전한 주입 방법을 안내한다.

### Infrastructure Failure (retryable)

- timeout
- connection_reset
- rate_limit (429)
- terminated (강제 종료)
- context_length_exceeded

Action: retry with backoff (per §3, Backoff)

### Structural Failure (non-retryable)

Indicators (any one):

- schema validation failure
- required field unexpectedly empty in error message (e.g., `Skill '' not found`)
- resource not found after successful lookup of same resource
- equivalent actions behave differently (e.g., `edit` OK, `patch` FAIL)
- identical non-transient error repeated with identical arguments
- **Tri-Runtime Incompatibility**: 부분 수정 도구가 ASCII 파싱 제한이나 한글/특수문자로 인해 JSON 파싱 에러를 반복하는 경우.

Action:

1. stop retrying immediately
2. exception: if failure is a read-only/idempotent lookup and eventual consistency is plausible,
   allow one delayed re-check before final structural classification
3. inspect tool schema via current environment's descriptor workflow
4. inspect successful variants of same tool
5. generate root-cause hypotheses (adapter defect, server validation, etc.)
6. change strategy (alternate workflow, different tool)

---

## 3. Resilience Strategies

상황별로 다음과 같이 대응합니다.

- **Text/Search**: 검색 범위나 텍스트 양을 줄여 분할 재시도(chunked retry)를 수행합니다.
- **Code**: 작업을 쪼개거나 파일 단위를 세분화하여(task/file split) 재시도합니다.
- **File edit** (부분 수정 — `StrReplace`/`edit`/`replace_file_content` 등):
  - 패턴 불일치는 "재시도"가 아니라 **재읽기 → 범위 축소 → 단일 줄** 복구이다. 넓은 블록 재시도·편집 도구 자동 전환은 [runtime_edit_tools.md](runtime_edit_tools.md) · [routing.md](routing.md) §1 금지.
  - **Tri-Runtime 한글/특수문자 에러 복구**: 부분 수정 도구에 한글이 포함되어 JSON 파싱 에러가 발생한 경우, ASCII 기반 부분 수정 도구 재시도를 중단하고 `run_command` (또는 각 호스트의 쉘 도구)를 통해 `cat << 'EOF'` 또는 파이썬 스크립트 작성 방식으로 안전하게 변경을 일괄 대체 적용한다.
  - **"No changes to apply" 발생 시**: 동일한 변경 내용으로 재시도하지 않는다. 즉시 읽기 도구로 파일의 최신 내용을 재조회하여 이미 반영되었는지 확인하고, 반영되지 않았다면 매칭 대상을 축소 조정한다.
- **Large Ops**: 대규모 작업을 그룹화하여(grouped retry) 순차적으로 처리합니다.
- **Backoff**: `rate_limit` 발생 시 지수 백오프(exponential backoff)를 적용합니다.
- **Logging**: 모든 재시도 이력(retry log)을 유지합니다.
- **Reporting**: 부분적 실패(partial failure) 발생 시 반드시 사용자에게 보고합니다.
