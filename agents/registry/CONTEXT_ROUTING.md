# Context Routing

모든 작업은 루트 `AGENTS.md`를 먼저 읽는다.
아래 표에서 일치하는 문서만 추가로 읽으며 기본 최대 4개다.

| 경로 또는 작업 의미 | 추가 문서 | 검증 방향 |
|---|---|---|
| 모든 mutation, commit, push, 장시간 canonical 실행 | `agents/workflows/work-package-claim.md`, Issue #1 comments, `agents/workflows/git.md` | claim owner + exact scope/resource + overlap-safe publish |
| 로컬 실행 프롬프트 생성·위임 | `agents/workflows/work-package-claim.md`, `agents/prompts/TASK_DELTA_TEMPLATE.md` | owner claim 확인 + 단일 delegated executor + release 책임 |
| 프로젝트 목적, stack, 실제 command | `agents/project/PROFILE.md` | declared command와 실제 config 대조 |
| 제품 범위 선택 또는 장기 작업 재개 | `PROJECT_RULES.md`, 대상과 가장 가까운 current plan/spec | 현재 허용 범위와 dependency 확인 |
| 문서만 변경 | 참조되는 문서만 | diff + path/link integrity |
| 배포 전 전체 검증 | `agents/project/PROFILE.md` | exact candidate commit에서 release command |

read-only 분석과 work-package 분해는 claim 없이 수행할 수 있다.
분석에서 mutation·publish·장시간 실행으로 전환하는 시점에 claim routing을 적용한다.
