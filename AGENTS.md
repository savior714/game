# AGENTS.md — AidenGame 실행 규약

이 문서는 저장소 작업의 최소 실행 계약이다. Plan·Blueprint·라우팅 매니페스트·장문 보고는 일반 작업의 선행 조건이 아니다.

## 1. 우선순위

1. 사용자의 현재 요청
2. 이 문서
3. `PROJECT_RULES.md`
4. 대상 코드와 테스트
5. 기타 문서와 과거 계획

## 2. Git과 작업 단위

- canonical branch는 `origin/main`이며 기본 방식은 `main` 직접 수정과 fast-forward push다.
- PR과 feature branch는 사용자가 요청한 경우에만 사용한다.
- 병렬 mutation은 isolated worktree 또는 동등한 격리 공간을 사용한다.
- force push와 `--no-verify`는 금지한다.
- unrelated dirty state를 보존한다.
- 한 작업은 하나의 failure domain 또는 하나의 검증 가능한 가설로 제한한다.
- 수정 전 재현 조건과 단일 판정 기준을 정하고, 수정 후 그 기준만 독립 검증한다.
- 독립 문제는 다음 work package로 남긴다.

## 3. 병렬 작업: 최소 잠금

`agents/workflows/work-package-claim.md`는 작업 명세가 아니라 경로·공유자원 잠금이다.

- read-only 분석과 단일 mutation 세션에는 잠금이 필요하지 않다.
- 둘 이상의 mutation 세션 또는 shared browser/port/output 자원이 있을 때만 Issue #1에 잠금을 게시한다.
- 형식은 `OWNER / UNTIL / LOCK`만 사용한다.
- `path:`는 동일 경로 또는 부모·자식 경로가 겹치면 충돌한다.
- `resource:`는 값이 같으면 충돌한다.
- 충돌 claim 중 comment ID가 가장 작은 claim만 유효하다.
- dependency가 있는 작업은 병렬화하지 않고 순차 실행한다.
- task key, parent key, program, track, base SHA, expected transition과 activation 필드는 사용하지 않는다.

## 4. 작업 절차

1. 현재 실패 또는 변경 필요성을 재현한다.
2. allowed paths와 금지 범위를 정한다.
3. 최소 완결 변경을 적용한다.
4. focused verification으로 단일 criterion을 판정한다.
5. 최신 `origin/main`과 overlap을 확인한다.
6. fast-forward로 게시한다.

workaround, fail-open fallback, snapshot·baseline 갱신, unrelated cleanup으로 문제를 숨기지 않는다.

## 5. 검증

대표 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

모든 명령을 일괄 실행하지 않는다. 현재 failure domain에 직접 대응하는 최소 검증을 먼저 실행한다.

## 6. 프로젝트 경계

- 사용자 런타임은 정적 HTML/CSS/JavaScript다.
- 메인 허브는 `index.html`이다.
- 과목별 기능은 `domains/`, 공용 로직은 `shared/`에 둔다.
- 실험은 `experiments/`, 보호자·관리는 `guardian/`, `admin/`에 둔다.
- Next.js, Tauri, 별도 백엔드 API는 현재 범위 밖이다.
- Ocean Rescue 세부 계약은 가장 가까운 technical spec을 따른다.

## 7. 로컬 에이전트 위임

- 웹 세션에서 가능한 작업을 먼저 완료한다.
- 프롬프트는 최대 700줄이며 현재 failure domain에 필요한 delta만 전달한다.
- objective, reproduction, pass criterion, allowed paths, do/do not, verification, stop conditions를 포함한다.
- 잠금이 필요할 때만 `CLAIM_COMMENT / OWNER / UNTIL / LOCK`을 추가한다.
- 첫 mutation 전에 최신 `origin/main`과 active lock을 확인한다.

## 8. 완료 보고

```text
RESULT: PASS | BLOCKED
CHANGE: <one line>
VERIFY: <one line>
```

게시 시에만 `COMMIT`, 중단 시에만 `BLOCKER`와 `NEXT`를 추가한다. claim·lease·scope·SHA를 사용자 보고에 반복하지 않는다.
