# Local Work Package Template

```text
OBJECTIVE:
<one coherent failure domain or verifiable hypothesis>

CURRENT_STATE:
<current failure, need, or observable behavior>

WORKSPACE:
- SOURCE_WORKTREE: /Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>
- Open VS Code, OpenCode, LSP, uv/pnpm, tests, Docker, browser tooling, and generators from SOURCE_WORKTREE itself.
- Do not mix the main checkout, worktree, symlink aliases, /tmp, or /private/tmp paths.

IN_SCOPE:
- <root-cause owner, directly coupled caller/type/test/asset/config needed to close the same invariant>

OUT_OF_SCOPE:
- <different root cause, rollback boundary, future capability, or unrelated cleanup>

DO:
1. Fetch latest origin/main and confirm the current failure/reproduction and one primary criterion.
2. Preserve unrelated work and create the isolated source worktree under the stable WORKSPACE path, never under OS temp.
3. Read the closest implementation, contract, tests, shared owner, and sibling surfaces that consume the same invariant. This inventory is read-only until root-cause ownership is established.
4. Record the relevant LSP/typecheck/lint baseline from SOURCE_WORKTREE.
5. Choose the minimum coherent, root-cause-complete change for OBJECTIVE. Do not optimize for minimum LOC or minimum file count.
6. If the same root cause + invariant + rollback boundary requires a shared owner, directly coupled caller/type/fixture/test change, include those pieces in this package. If any discovered sibling needs an independent implementation or criterion, leave it as a separate failure domain.
7. Avoid under-fixing: do not add repeated leaf guards, duplicate normalization/validation/state rules, or a caller-specific workaround when the confirmed defect belongs to a shared owner.
8. A small refactor or testability seam is allowed when it is required to express or verify the current invariant. Do not generalize for hypothetical future variation.
9. Run the focused verification bundle for the primary criterion and direct-impact closure.
10. Fix every static error introduced by the change and every error in modified or directly affected modules.
11. If a repository-wide/static gate exposes an independent failure domain, record it separately. Do not absorb or fix it inside this package unless it is proven to share the same root cause, invariant, rollback boundary, and primary criterion.
12. Before publish, fetch origin/main again.
13. Reapply onto latest main in another stable worktree and reverify; adapt if related code moved.
14. Push fast-forward and retry after another session wins the push race.
15. Remove only clean, published worktrees created by this task; do not force-remove dirty or unpublished worktrees. Use git worktree prune only for stale metadata whose path is already gone.

DO_NOT:
- create a source checkout/worktree under /tmp, /private/tmp, $TMPDIR, or mktemp
- run LSP, package manager, tests, Docker, browser tooling, or generators from a different checkout than SOURCE_WORKTREE
- optimize for the smallest diff when that leaves the confirmed shared root cause or invariant drift in place
- add local guards or duplicate domain knowledge merely to avoid touching the real shared owner
- treat sibling inventory as automatic authorization to modify every sibling
- combine different root causes, rollback boundaries, or independent acceptance criteria in one corrective patch
- add speculative abstractions, extension points, future capabilities, or unrelated cleanup
- hide failures with baseline, snapshot, skip, ignore, mock, broad suppression, or fail-open fallback
- force push or overwrite competing work
- add governance fields or validators without a repeated demonstrated need
- report PASS for criteria that were not verified

ACCEPTANCE:
- <one behavioral primary criterion>
- the confirmed root cause is closed at the correct owner rather than bypassed by a leaf workaround
- the same invariant is not newly duplicated across directly affected callers
- changed and directly affected modules have zero LSP/typecheck/lint errors
- <additional direct criterion only when required by the same objective>

VERIFY:
- <focused command that directly decides the primary criterion>
- <directly affected typecheck/lint/test command>
- <runtime/browser evidence only when the same failure domain requires it>

STOP:
- current main already satisfies OBJECTIVE and structural closure
- required change would alter user-visible/domain behavior, authorization, or acceptance beyond the approved objective
- a discovered problem requires a different root cause, rollback boundary, or independent primary criterion; report it separately instead of fixing it now
- validator or runtime required for the primary criterion is unavailable and there is no equivalent verification
- an active exclusive reservation conflicts with the exact required resource
- closing the root cause requires a broad redesign that cannot remain a bounded coherent package; report the exact reason as BLOCKED

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
