# Agent 문서 경로

AidenGame의 정식 agent 문서 경로는 `agents/`다.

- 실제 문서와 skill/workflow 파일은 모두 `agents/` 아래에서 관리한다.
- 개발·디버깅의 verification strategy를 선택할 때는 루트 `AGENTS.md`의 위험 기반 원칙과 `agents/RISK_DIRECTED_VERIFICATION.md`를 적용한다.
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
