---
scope: workflow
status: active
---

# Minimal Parallel Locks

## 목적

동시 mutation의 경로와 공유 실행 자원 충돌만 막는다. 작업 목적·dependency·검증·완료 보고는 각 work package와 프롬프트가 소유한다.

## 적용

잠금 필요:

- 둘 이상의 mutation·commit·push 세션
- shared browser profile, fixed port, output directory, generated artifact 또는 publication destination

잠금 불필요:

- read-only 분석·리뷰
- mutation 세션이 하나뿐인 일반 작업

## Board

- Repository: `savior714/game`
- Issue: `#1`

## Claim

```text
CLAIM
OWNER: <label>
UNTIL: <ISO-8601 UTC>
LOCK:
- path:<repo-relative path>
- resource:<stable id>
```

GitHub comment ID가 claim 식별자다.

## 충돌

- `path:`가 같거나 한쪽이 다른 쪽의 부모 경로이면 충돌한다.
- `resource:` 값이 같으면 충돌한다.
- active claim은 `UNTIL` 전이고 대응 `RELEASE`가 없는 claim이다.
- 충돌 집합에서 comment ID가 가장 작은 claim만 유효하다.

선행 의존성이 있으면 claim metadata를 추가하지 않고 순차 실행한다.

## 실행

- 첫 mutation, shared long run, publish 직전에 active lock을 확인한다.
- lock 밖 경로나 자원이 필요하면 release 후 새 claim을 게시한다.
- 최신 `origin/main`에서 문제가 남아 있는지 첫 mutation 전에 확인한다.
- claim은 isolated worktree, Git overlap 검사, focused verification과 fast-forward publish를 대체하지 않는다.

## Release

```text
RELEASE
CLAIM: <comment ID>
RESULT: PASS | BLOCKED | ABANDONED
COMMIT: <40-char SHA or NONE>
```

## 로컬 위임

```text
CLAIM_COMMENT:
OWNER:
UNTIL:
LOCK:
```

같은 claim을 여러 executor에 전달하거나 delegated executor가 중복 claim을 게시하지 않는다.

## Legacy

기존 claim은 expiry/release까지 유효하다. `WRITE_SCOPE`는 `path:`, `EXCLUSIVE_RESOURCES`는 `resource:`로만 해석하고 다른 필드는 무시한다.
