# Context Routing

모든 작업은 루트 `AGENTS.md`를 먼저 읽는다. 다음 문서는 해당될 때만 추가로 읽는다.

| 작업 | 추가 문서 |
|---|---|
| 제품·아키텍처 경계 | `PROJECT_RULES.md`와 가장 가까운 spec |
| 병렬 mutation 또는 shared long run | `agents/workflows/work-package-claim.md`, Issue #1 |
| Git·dirty·remote advance·publish | `agents/workflows/git.md` |
| 로컬 프롬프트 | `agents/prompts/TASK_DELTA_TEMPLATE.md` |
| 프로젝트 명령·stack | `agents/project/PROFILE.md` |
| 문서만 변경 | 참조되는 문서만 |

read-only 분석에는 claim 문서를 읽을 필요가 없다. mutation 세션이 하나뿐이면 claim board도 필요하지 않다.
