# AI Command Protocol

## PowerShell 보안 제약 대응
- 일부 실행 환경에서는 PowerShell profile 정책에 의해 `Add-Content` 사용이 차단될 수 있다.
- 해당 정책이 감지되면 자동화 스크립트는 즉시 다음 우선순위로 전환한다:
  1. 에이전트 파일 수정 도구를 통한 직접 수정
  2. `Set-Content` 등 대체 가능한 안전 명령 사용
  3. 다중 명령 체인 대신 단계별 실행으로 실패 지점 최소화

## Git/검증 명령 실행 원칙
- 검증 명령은 PowerShell 호환 문법으로 작성한다. (`&&` 대신 세미콜론 + `$LASTEXITCODE` 체크)
- 통합 검증은 `node verify_all.js`를 기본 진입점으로 사용한다.
- 과목 공통 규칙 회귀 방지는 별도 검증 스크립트(`verify_net_logic.js`)를 반드시 포함한다.
