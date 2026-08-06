---
scope:
- '*'
always_apply: false
priority: 1
domain: core
last_verified: 2026-08-06
verify_with:
- just commit-gate-hard
---
<!-- Language: ko -->

# 비밀정보와 자격 증명

이 문서는 AidenGame 저장소 작업에서 credential과 민감 정보가 로그·문서·커밋으로 노출되지 않도록 하는 실행 규칙이다.
정책 상위 권위는 [`PROJECT_RULES.md`](../../PROJECT_RULES.md)다.

## 1. 절대 금지

- `.env`, `.env.*`, key, token, cookie, password, PEM 내용을 채팅이나 도구 출력에 노출
- `cat .env`, `echo $TOKEN`, 환경 전체 dump처럼 민감값이 stdout/stderr에 실릴 수 있는 명령
- 비밀값을 source, test fixture, 문서, commit message에 하드코딩
- 로그에 포함된 credential을 오류 설명에서 재인용
- 검증을 통과시키기 위해 secret scan을 비활성화

## 2. 안전한 확인

내용을 읽지 않고 다음만 확인할 수 있다.

- 파일 존재 여부
- 필요한 key 이름의 문서화 여부
- 값이 비어 있는지 여부를 노출하지 않는 안전한 script 결과
- pre-defined command의 성공/실패

외부 서비스에 credential이 필요하면 저장소가 제공하는 안전한 주입 경계를 먼저 확인한다.
사용자가 직접 값을 채팅에 붙여넣도록 요구하지 않는다.

## 3. `.env` 형식

`.env`와 `.env.example`은 저장소의 실제 소비자가 지원하는 단순 `KEY=VALUE`와 주석 형식을 따른다.

- shell command, command substitution, redirect를 넣지 않는다.
- 예시 파일에는 실제 비밀값을 넣지 않는다.
- `.env`를 수정했다면 현재 linter의 실제 인자를 확인해 검증한다.

현재 저장소의 hard commit gate:

```bash
just commit-gate-hard
```

이 gate는 존재하는 dotenv 파일에 대해 `scripts/verify/lint_dotenv.py`와 staged secret 검사를 사용한다.

## 4. Git과 remote

- credential이 포함된 remote URL이나 command를 출력하지 않는다.
- token이 섞일 수 있는 full URL 대신 repository identity와 masked 상태만 사용한다.
- secret 파일을 stage하지 않는다.
- commit gate 실패 시 `--no-verify`로 우회하지 않는다.
- 과거 history에 노출된 비밀은 파일 삭제만으로 해결되지 않으므로 회전과 history 대응을 별도로 판단한다.

## 5. 로그와 오류

- stack trace와 request dump에서 header, query, environment를 확인하기 전에 민감값 가능성을 고려한다.
- 필요한 오류 코드와 실패 단계만 요약한다.
- 원문 로그 공유가 필요하면 credential field를 제거하거나 마스킹한다.
- 브라우저 storage, cookie, authorization header를 테스트 evidence에 포함하지 않는다.

## 6. 노출 발생 시

1. 추가 출력과 재시도를 중단한다.
2. 비밀값을 다시 보여주지 않는다.
3. 어떤 종류의 credential과 경로가 영향을 받았는지 설명한다.
4. credential 회전 또는 폐기를 안내한다.
5. commit·log·artifact·remote history 노출 범위를 확인한다.
6. 재발 방지 gate를 별도 failure domain으로 수정한다.

credential 자체를 검증 증거로 보존하지 않는다.

## 7. 테스트와 문서

- 테스트에는 synthetic placeholder만 사용한다.
- placeholder가 실제 credential 형식과 혼동되지 않게 명확히 표시한다.
- 문서에는 key 이름과 안전한 설정 방법만 기록한다.
- 외부 issue tracker나 특정 서비스 credential을 AidenGame 공통 필수 계약으로 강제하지 않는다.
