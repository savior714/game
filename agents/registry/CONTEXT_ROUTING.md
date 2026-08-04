# Context Routing

모든 작업은 루트 `AGENTS.md`를 먼저 읽는다. 다음 문서는 해당될 때만 추가로 읽는다.

| 작업 | 추가 문서 |
|---|---|
| 제품·아키텍처 경계 | `PROJECT_RULES.md`와 가장 가까운 spec |
| same hotspot·canonical runtime·generated artifact reservation | `agents/workflows/work-package-claim.md`, Issue #1 |
| Git·dirty·remote advance·publish | `agents/workflows/git.md` |
| 로컬 프롬프트 | `agents/prompts/TASK_DELTA_TEMPLATE.md` |
| 프로젝트 명령·stack | `agents/project/PROFILE.md` |
| 문서만 변경 | 참조되는 문서만 |

read-only 분석과 일반 병렬 mutation에는 reservation 문서나 board를 읽을 필요가 없다.
