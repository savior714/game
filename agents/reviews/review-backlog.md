# AidenGame Review Backlog

이 파일은 계획·runbook·local execution candidate를 위한 rolling evidence-grounded discovery cache다. Final truth는 latest `origin/main`의 production code, Git history와 direct test/runtime evidence다.

이 backlog는 truth cache, product roadmap, 완료 이력 또는 실행 queue가 아니다.

## Active findings

현재 기록된 finding 없음.

새 finding은 human-readable heading 아래에 다음만 기록한다.

- Failure domain:
- Current evidence:
- Likely owner:
- Primary risk / invariant:
- Revalidation anchors:

Revalidation anchor는 line number나 오래된 SHA보다 symbol, owner, boundary, focused test처럼 finding을 빠르게 falsify할 수 있는 의미 기반 포인터를 선호한다.

Lifecycle status, implementation recipe, patch plan, authorized scope, RED/GREEN history, 완료 항목과 filler는 넣지 않는다. 승격됐다는 이유만으로 제거하지 않고 latest main publication 뒤 primary criterion 만족이 확인될 때 제거한다.
