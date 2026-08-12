---
situation: 사용자가 기존 Blueprint 아카이브를 명시적으로 요청함
level: Conditional
description: 기존 plan 문서의 안전한 이동과 링크 정합성 검증
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Blueprint 아카이브 워크플로우

이 워크플로우는 사용자가 **기존 저장소 Blueprint의 아카이브를 명시적으로 요청한 경우에만** 적용한다.
현재 일반 WP 계획과 다음 작업은 채팅에서 관리하므로, 진행이 끝날 때마다 plan 파일을 새로 만들거나 자동 아카이브하지 않는다.

## 1. 진입 조건

다음을 모두 확인한다.

- 대상 파일이 실제로 존재한다.
- 파일이 현재 실행 권위인지 동결 기술 참고인지 과거 기록인지 분류돼 있다.
- 다른 문서와 테스트가 해당 경로를 참조하는지 확인했다.
- 이동이 현재 제품 방향이나 실행 규칙을 바꾸지 않는다.
- 사용자가 삭제가 아니라 아카이브 이동을 요청했다.

현재 authority 문서인 `AGENTS.md`, `PROJECT_RULES.md`, 활성 product spec, `MEMORY.md`는 이 workflow로 아카이브하지 않는다.

## 2. 도구 확인

과거 문서의 명령을 그대로 실행하지 않는다.
최신 `Justfile`과 `scripts/`에서 실제 archive tooling의 존재와 인자를 확인한다.

전용 스크립트가 존재하고 현재 대상 형식을 지원하면 dry-run을 먼저 사용한다.
스크립트가 없거나 계약이 맞지 않으면 파일 이동과 참조 갱신을 하나의 명시적 patch로 수행한다.

외부 issue tracker, API key, roadmap generator, shell alias를 필수 전제로 가정하지 않는다.

## 3. 실행 절차

1. 최신 `origin/main`과 clean mutation 경계를 확인한다.
2. 대상 문서의 현재 역할과 링크를 조사한다.
3. destination을 기존 archive 구조에 맞춰 결정한다.
4. dry-run 또는 후보 diff로 이동·링크 변경 범위를 확인한다.
5. 대상 파일을 이동한다.
6. 저장소 내부의 정확한 링크만 갱신한다.
7. 깨진 링크와 중복 파일이 없는지 확인한다.
8. 문서 내용이 과거 상태를 현재 일정 권위처럼 표현하지 않는지 확인한다.
9. 최신 main 이동 여부를 재확인하고 fast-forward로 게시한다.

아카이브를 위해 제품 테스트의 수용 기준을 변경하지 않는다.
문서의 Task 상태를 억지로 완료 처리해 archive gate를 통과시키지 않는다.

## 4. 검증

최소 검증은 다음을 포함한다.

- source 경로에 대상 파일이 남지 않음
- destination에 정확히 한 파일 존재
- 이전 경로를 가리키는 활성 링크가 남지 않음
- 새 링크 대상이 실제로 존재
- authority 색인과 README가 필요한 경우에만 갱신됨
- 현재 product spec과 동결 정책이 유지됨

문서 authority 관련 focused test:

```bash
uv run pytest -q tests/test_document_authority_classification.py
uv run pytest -q tests/test_agent_registry_consistency.py
```

실제 archive script를 사용했다면 해당 script의 직접 테스트도 실행한다.

## 5. MEMORY와 handoff

아카이브 자체는 제품 방향 변경이 아니다.
다음 실행 경계나 authority가 바뀌지 않았다면 `MEMORY.md`를 수정하지 않는다.

handoff에는 다음만 기록한다.

- 이동한 파일
- 갱신한 직접 링크
- 실행한 검증
- 게시 커밋

아카이브된 plan의 전체 Task 이력을 복사하지 않는다.

## 6. 금지

- 사용자 요청 없이 plan 일괄 아카이브
- archive 전 Task 상태·Conclusion 조작
- 존재하지 않는 automation 명령 실행
- 외부 서비스 동기화를 무조건 요구
- roadmap이나 추천 다음 작업을 자동 갱신
- 전체 스테이징으로 unrelated 변경 포함
- archive 파일 물리 삭제 후 링크를 방치
- 현재 authority 문서를 과거 기록과 같은 위치로 이동
