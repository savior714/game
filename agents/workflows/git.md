---
situation: 저장소 상태를 파괴적으로 바꾸기 전의 안전 판정
level: Required
description: 소유권·의도·복구 가능성으로 Git 상태 전이의 안전을 판정하는 최소 파괴적 안전 kernel
version: 4.0.0
last_updated: 2026-10-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Git 안전 kernel

이 문서는 저장소 상태가 파괴적으로 바뀔 수 있는 전이의 최소 안전 경계만 소유한다. launcher, queue,
branch 이름 규칙, linked worktree, candidate protocol, 특정 Git workflow를 강제하지 않는다.

raw Git은 정상 개발 도구이며 local-agent `MODE: BUILD`에도 동일하게 적용된다. BUILD는 작업 모드이지
Git topology 의무가 아니다. 실제 workspace 선택·commit·게시 절차는
[`../core/execution.md`](../core/execution.md)가 소유한다.

## 1. 판정 기준: 소유권 × 의도 × 복구 가능성

잠재적으로 파괴적인 Git 전이 전에 다음 세 가지를 판정한다.

1. **소유권** — 변경되는 work, ref, worktree, index, stash가 누구 것인가. stash는 모든 linked worktree가
   공유하는 저장소 전체 `refs/stash` 한 개이므로 여기서 국소 판단으로 다루지 않는다.
2. **의도** — 그 상태를 보존하려는가, 변경하려는가, 폐기하려는가.
3. **복구 가능성** — 그 전이가 틀렸을 때 요구되는 상태를 되돌릴 수 있는가.

`dirty`, detached HEAD, worktree, branch, raw Git 명령은 그 자체로 위험하지 않다. clean workspace도
다른 주체의 상태를 덮어쓰면 위험하다.

## 2. 보호해야 할 상태

소유권과 의도가 불명확한 상태를 폐기하거나 덮어쓰지 않는다. unrelated 파일을 흡수하지 않는다. 현재 원격
상태를 확인하지 않고 공유 ref를 덮어쓰지 않는다. 명확한 의도 없이 공유 history를 다시 쓰지 않는다.
경계 없는 광범위 파괴 정리를 수행하지 않는다.

현재 task와 dirty 상태가 겹치면 그 상태를 보존하고 더 안전한 workspace를 선택한다.

## 3. 명령 blacklist 없음

안전은 명령 문자열이 아니라 상태 전이에 대한 것이다. 잠재적으로 파괴적인 명령도 소유권·의도·복구
가능성이 그 정확한 전이를 안전하게 만들 때 적절하다. 그렇지 않으면 명령의 철자가 아니라 결과로
금지된다.

## 4. 이 저장소가 금지하는 전이

아래는 저장소 경계에 대한 명시적 결정이며 §1의 일반 기준보다 강한 제품 계약이다. 소유권·의도·복구
가능성 판정과 무관하게 금지한다.

- 공유 ref에 대한 force push와 공유 history rewrite. `origin/main`이 유일한 통합·게시 기준이다.
- `--no-verify` 또는 동등한 우회로 필수 검증과 commit gate를 건너뛰는 것.
- 소유권이 다른 dirty·in-flight·unpublished 상태를 흡수하거나, 전역 stash·reset으로 덮는 것.
- 게시가 증명되지 않은 worktree의 unlock·제거, `git worktree remove --force`, worktree 경로의 `rm -rf`.

근거는 복구 가능성이 아니라 제품 계약이다. 복구 가능성 판단이 더 안전한 결론을 요구하면 더 안전한
workspace와 전이를 선택한다.

## 5. 게시와 동시성 경계

workspace 선택, staging과 commit 내용, main 이동·재적용 결정, 게시 종료와 정확한 remote read-back,
동시성 처리는 [`../core/execution.md`](../core/execution.md)가 소유한다. 이 kernel이 추가하는 것은
파괴적 경계뿐이다. 오래된 로컬 SHA나 게시 편의를 유지하기 위한 force push, history rewrite, 보호 상태
폐기는 진행하지 않는다.

## 6. 검증 경계

검증·acceptance 정책은 [`../core/verification.md`](../core/verification.md)와 해당 product·domain
authority가 소유한다. 검증 품질을 Git topology로 구현하지 않는다.

## 7. 거버넌스 유지

Git wrapper, guard, helper, hook, launcher는 존재한다는 이유만으로 권위 gateway가 아니다. 추가하거나
유지하는 machinery는 `PROJECT_RULES.md`의 복잡성 admission을 따른다.