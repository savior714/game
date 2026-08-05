# Local Work Package Template

```text
OBJECTIVE:
<coherent outcome>

CURRENT_STATE:
<current failure, need, or observable behavior>

WORKSPACE:
- SOURCE_WORKTREE: /Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>
- Open VS Code, OpenCode, LSP, uv/pnpm, tests, Docker, browser tooling, and generators from SOURCE_WORKTREE itself.
- Do not mix the main checkout, worktree, symlink aliases, /tmp, or /private/tmp paths.

IN_SCOPE:
- <source, caller, test, asset, config>

OUT_OF_SCOPE:
- <unrelated product behavior or path>

DO:
1. Fetch latest origin/main and confirm the current state.
2. Preserve unrelated work and create the isolated source worktree under the stable WORKSPACE path, never under OS temp.
3. Read the closest implementation, contract, and tests.
4. Record the relevant LSP/typecheck/lint baseline from SOURCE_WORKTREE.
5. Apply the minimum complete change for OBJECTIVE.
6. Run the focused verification bundle.
7. Fix every static error introduced by the change and every error in modified or directly affected modules.
8. If the repository static gate exposes another existing LSP/typecheck/lint failure, independently verify the current failure domain, then select the next static failure domain and resolve it separately. Do not pass it as out of scope.
9. Before publish, fetch origin/main again.
10. Reapply onto latest main in another stable worktree and reverify; adapt if related code moved.
11. Push fast-forward and retry after another session wins the push race.
12. Remove only the worktrees created by this task and run git worktree prune.

DO_NOT:
- create a source checkout/worktree under /tmp, /private/tmp, $TMPDIR, or mktemp
- run LSP, package manager, tests, Docker, browser tooling, or generators from a different checkout than SOURCE_WORKTREE
- ignore an LSP/typecheck/lint error merely because the file was not initially in scope
- combine unrelated static failure domains in one broad corrective patch
- broaden unrelated product scope
- hide failures with baseline, snapshot, skip, ignore, mock, broad suppression, or fail-open fallback
- force push or overwrite competing work
- add governance fields or validators
- report PASS for criteria that were not verified

ACCEPTANCE:
- <criterion>
- changed and directly affected modules have zero LSP/typecheck/lint errors
- the required repository static gate passes
- <additional criterion only when required by the same objective>

VERIFY:
- <focused command>
- <repository-defined typecheck/lint command>

STOP:
- current main already satisfies OBJECTIVE
- required change exceeds authorization or requires a destructive/security/data decision
- validator or runtime is unavailable
- an active exclusive reservation conflicts with the exact required resource
- a remaining static error requires a broad architectural rewrite or unsafe mutation; report the exact diagnostic and reproduction command as BLOCKED

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
