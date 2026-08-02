# Context Routing

모든 작업은 루트 `AGENTS.md`를 먼저 읽는다.
아래 표에서 일치하는 문서만 추가로 읽으며 기본 최대 3개다.

| 경로 또는 작업 의미 | 추가 문서 | 검증 방향 |
|---|---|---|
| 모든 write, commit, push, dirty state, remote advance | `agents/workflows/git.md` | exact write set + targeted validation + push closure |
| 프로젝트 목적, stack, 실제 command | `agents/project/PROFILE.md` | declared command와 실제 config 대조 |
| 제품 범위 선택 또는 장기 작업 재개 | `docs/product/ACTIVE_SCOPE.md` | 현재 허용 범위 확인 |
| 문서만 변경 | 참조되는 문서만 | diff + path/link integrity |
| 배포 전 전체 검증 | `agents/project/PROFILE.md` | exact candidate commit에서 release command |
