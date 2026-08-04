# Local Work Package Template

```text
OBJECTIVE:
<one failure domain>

REPRODUCTION:
<current failure or observable need>

PASS_CRITERION:
<single decision criterion>

ALLOWED_PATHS:
- <path>

DO_NOT_TOUCH:
- <path or behavior>

DO:
1. Check latest origin/main.
2. Reproduce the issue.
3. Apply the minimum complete change.
4. Run focused verification.
5. Check overlap and publish fast-forward.

DO_NOT:
- fix unrelated failures
- update baseline/snapshot to hide failure
- force push or modify unrelated dirty state

VERIFY:
- <focused command>

STOP:
- issue already resolved
- required change exceeds allowed paths
- validator unavailable
- relevant origin/main change invalidates the work

OPTIONAL_PARALLEL_LOCK:
CLAIM_COMMENT: <id or NONE>
OWNER: <owner or NONE>
UNTIL: <UTC or NONE>
LOCK:
- path:<path>
- resource:<id>

REPORT:
RESULT: PASS | BLOCKED
CHANGE: <one line>
VERIFY: <one line>
COMMIT: <only when published>
BLOCKER: <only when blocked>
NEXT: <only when blocked>
```
