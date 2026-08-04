# Local Work Package Template

```text
OBJECTIVE:
<coherent outcome>

CURRENT_STATE:
<current failure, need, or observable behavior>

IN_SCOPE:
- <source, caller, test, asset, config>

OUT_OF_SCOPE:
- <unrelated behavior or path>

DO:
1. Fetch latest origin/main and confirm the current state.
2. Preserve unrelated work and use an isolated worktree.
3. Apply the minimum complete change for OBJECTIVE.
4. Run the focused verification bundle.
5. Before publish, fetch origin/main again.
6. Reapply onto latest main and reverify; adapt if related code moved.
7. Push fast-forward and retry after another session wins the push race.

DO_NOT:
- fix unrelated work
- hide failures with baseline/snapshot changes
- force push or overwrite competing work
- add governance fields or validators

ACCEPTANCE:
- <criterion>
- <criterion>

VERIFY:
- <focused command>

STOP:
- current main already satisfies OBJECTIVE
- required change exceeds scope or authorization
- validator is unavailable
- destructive/security/data decision requires user input

OPTIONAL_EXCLUSIVE_RESERVATION:
RESERVATION_COMMENT: <id or NONE>
WORK: <name or NONE>
OWNER: <owner or NONE>
EXPIRES: <UTC or NONE>
SCOPE:
- <typed scope token or NONE>

REPORT:
RESULT: PASS | BLOCKED
CHANGE: <one line>
VERIFY: <one line>
COMMIT: <only when published>
BLOCKER: <only when blocked>
NEXT: <only when blocked>
```
