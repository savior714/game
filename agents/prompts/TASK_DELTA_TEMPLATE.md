# Coherent Work-Package Delta Template

claim-required 실행 프롬프트는 웹 GPT 세션이 Issue #1에서 owner가 된 뒤에만 이 형식으로 발급한다.
read-only 분석은 `EXECUTION_CLAIM: NOT_REQUIRED`로 사용할 수 있다.

```text
TASK_ID:
<short stable id>

PROGRAM:
<current product or closure axis>

PARENT_KEY:
<parent axis or NONE for read-only>

TASK_KEY:
<bounded lowercase kebab key or NONE for read-only>

EXECUTION_CLAIM:
NOT_REQUIRED | WEB_OWNER_DELEGATED

CLAIM_ID:
<claim id or NONE>

OWNER_LABEL:
<user-visible owner label or NONE>

CLAIM_DELEGATION:
WEB_OWNER_TO_SINGLE_LOCAL_EXECUTOR | NONE

BASE_SHA:
<40-char origin/main SHA>

EXPIRES_AT_UTC:
<lease expiry or NONE>

WORK_PACKAGE_OBJECTIVE:
<one coherent independently verifiable objective>

EXPECTED_TRANSITION:
<observable before -> after transition>

INCLUDED_SCOPE:
- <owned source, caller, type, test, config boundary>

EXCLUDED_SCOPE:
- <explicit non-goals>

WRITE_SCOPE:
- <exact paths or logical boundary>

EXCLUSIVE_RESOURCES:
- <port, browser profile, output path, runner identity or NONE>

DEPENDS_ON:
- <completed task key or NONE>

VERIFICATION_BUNDLE:
- <focused commands and browser assertions>

ACCEPTANCE_CHECKLIST:
- <criterion>
- <criterion>

STOP_CONDITIONS:
- claim expired, released, lost or board owner recheck failed
- write/resource overlap with another active claim
- unmet dependency
- required validator unavailable
- scope expansion beyond declared package
- destructive or irreversible action outside user authorization

STEPS:
1. Read AGENTS.md, agents/workflows/work-package-claim.md, agents/workflows/git.md and the closest implementation/test.
2. Preserve unrelated dirty state and use an isolated worktree for parallel mutation.
3. For delegated execution, do not post a duplicate claim. Verify the supplied claim or rely on the coordinating web owner when board access is unavailable.
4. Reproduce or confirm the stated current condition.
5. Apply the minimum complete change for the coherent objective within WRITE_SCOPE.
6. Run the VERIFICATION_BUNDLE and decide every acceptance item independently.
7. Recheck claim and origin/main overlap before long runs and publish.
8. Publish by fast-forward only when validation and overlap checks pass.
9. Report the exact result; the coordinating web owner posts RELEASE when the local executor cannot.

REPORT:
RESULT / VERDICT / CONFIDENCE / BLOCKER /
PROGRAM / PARENT_KEY / TASK_KEY / CLAIM_ID / CLAIM_STATUS / OWNER_LABEL /
WORK_PACKAGE_OBJECTIVE / INCLUDED_SCOPE / EXCLUDED_SCOPE /
ACCEPTANCE_CHECKLIST / VERIFICATION / CHANGED_PATHS /
GIT_PUBLICATION_STATUS / MUTATION_PERFORMED / RELEASE_POSTED /
REMAINING_WORK / HANDOFF
```

공통 계약을 반복해 프롬프트를 불필요하게 늘리지 않는다. 현재 package에 필요한 delta와 exact
scope·resource·verification만 추가한다.
