# Agent 문서 경로

AidenGame의 정식 agent 문서 경로는 `agents/`다.

- 실제 문서와 skill/workflow 파일은 모두 `agents/` 아래에서 관리한다.
- 질문이 생기면 먼저 루트 `AGENTS.md`의 권위 라우팅에서 해당 owner를 찾는다. `AGENTS.md`는 라우팅과 실행 경계만 소유하고 세부 계약을 복제하지 않는다.
- 개발·디버깋의 verification strategy를 선택할 때는 `agents/core/verification.md`와 `agents/RISK_DIRECTED_VERIFICATION.md`를 적용한다.
- Git 파괴적 안전은 `agents/workflows/git.md`, workspace·commit·게시 절차는 `agents/core/execution.md`, 상시 병렬 A/B 트랙은 `agents/project/PARALLEL_TRACKS.md`를 따른다.
- 계획·runbook·다음 실행 candidate 공급은 `agents/core/planning.md`와 `agents/reviews/review-backlog.md`를 따른다. Discovery는 `review backlog → targeted review → broad review` 순서로 확장하고 모든 승격 후보는 latest `origin/main`에서 독립 재검증한다.
- `.agents/`는 과거 도구·스크립트·체크아웃의 경로를 깨뜨리지 않기 위한 호환 디렉터리다.
- `.agents/` 아래 항목은 `agents/`의 대응 디렉터리를 가리키는 상대 심볼릭 링크만 허용한다.
- 새 문서와 저장소 내부 참조는 `agents/`를 사용한다.
- 호환 링크를 실제 파일 복사본으로 되돌리거나 양쪽을 독립적으로 수정하지 않는다.

현재 호환 대상:

- `.agents/core` → `agents/core`
- `.agents/domains` → `agents/domains`
- `.agents/registry` → `agents/registry`
- `.agents/skills` → `agents/skills`
- `.agents/workflows` → `agents/workflows`
