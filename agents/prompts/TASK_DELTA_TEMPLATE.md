# Local Work Package Template

`agents/RISK_DIRECTED_VERIFICATION.md`의 Risk-Directed Verification(RDV)을 적용한다. TDD는 기본 의무가 아니라 현재 `PRIMARY_CRITERION`을 가장 싸고 충분히 충실하게 판정할 때 선택하는 전략이다.

```text
OBJECTIVE:
<one coherent failure domain or verifiable hypothesis>

CURRENT_STATE:
<current failure, need, or observable behavior>

PRIMARY_CRITERION:
<one observable PASS/FAIL criterion fixed before mutation>

VERIFICATION_STRATEGY:
REPRODUCTION_FIRST | CONTRACT_OR_EXAMPLE_FIRST | CHARACTERIZATION_FIRST | IMPLEMENT_OR_RUNTIME_FIRST

PRIMARY_FIDELITY:
F0 | F1 | F2 | F3 | F4

WHY_THIS_STRATEGY:
<why this is the cheapest sufficiently faithful way to falsify PRIMARY_CRITERION>

ESCALATE_IF:
<condition proving the selected fidelity cannot decide PRIMARY_CRITERION; otherwise NONE>

WORKSPACE:
- SOURCE_WORKTREE: /Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>
- Open VS Code, OpenCode, LSP, uv/pnpm, tests, Docker, browser tooling, and generators from SOURCE_WORKTREE itself.
- Do not mix the main checkout, worktree, symlink aliases, /tmp, or /private/tmp paths.

IN_SCOPE:
- <root-cause owner, directly coupled caller/type/test/asset/config needed to close the same invariant>

OUT_OF_SCOPE:
- <different root cause, rollback boundary, future capability, or unrelated cleanup>

DO:
1. Fetch latest origin/main and confirm the current failure/expected contract plus PRIMARY_CRITERION before editing.
2. Select VERIFICATION_STRATEGY and PRIMARY_FIDELITY according to `agents/RISK_DIRECTED_VERIFICATION.md`; do not default to test-first merely because code will change.
3. Preserve unrelated work and create the isolated source worktree under the stable WORKSPACE path, never under OS temp.
4. Read the closest implementation, contract, tests, shared owner, and sibling surfaces that consume the same invariant. This inventory is read-only until root-cause ownership is established.
5. Record only the static/test/runtime baseline needed to interpret PRIMARY_CRITERION and direct impact from SOURCE_WORKTREE.
6. Choose the minimum coherent, root-cause-complete change for OBJECTIVE. Do not optimize for minimum LOC or minimum file count.
7. If the same root cause + invariant + rollback boundary requires a shared owner, directly coupled caller/type/fixture/test change, include those pieces in this package. If any discovered sibling needs an independent implementation or criterion, leave it as a separate failure domain.
8. Avoid under-fixing: do not add repeated leaf guards, duplicate normalization/validation/state rules, or a caller-specific workaround when the confirmed defect belongs to a shared owner.
9. A small refactor or testability seam is allowed only when required to express the current invariant or obtain sufficiently faithful evidence. Do not generalize for hypothetical future variation.
10. For a cheap deterministic known bug, prefer REPRODUCTION_FIRST. For stable deterministic domain/state contracts, CONTRACT_OR_EXAMPLE_FIRST is usually appropriate. For behavior-preserving refactors, use CHARACTERIZATION_FIRST when needed. For visual/game-feel/browser/rendering/runtime behavior where unit fidelity is low, use IMPLEMENT_OR_RUNTIME_FIRST.
11. Add or retain automated regression coverage only when it protects a named failure mode or stable contract with reasonable defect-detection value and maintenance cost. Do not add tests for coverage or ceremonial RED.
12. Run the focused verification bundle that directly decides PRIMARY_CRITERION and direct-impact closure. If the chosen layer cannot observe the failure mode, escalate only as specified by ESCALATE_IF.
13. Fix every static error introduced by the change and every error in modified or directly affected modules.
14. If a repository-wide/static gate exposes an independent failure domain, record it separately. Do not absorb or fix it inside this package unless it is proven to share the same root cause, invariant, rollback boundary, and primary criterion.
15. Before publish, fetch origin/main again.
16. Reapply onto latest main in another stable worktree and reverify the primary criterion/direct closure; adapt if related code moved.
17. Push fast-forward and retry after another session wins the push race.
18. Remove only clean, published worktrees created by this task; do not force-remove dirty or unpublished worktrees. Use git worktree prune only for stale metadata whose path is already gone.

DO_NOT:
- create a source checkout/worktree under /tmp, /private/tmp, $TMPDIR, or mktemp
- run LSP, package manager, tests, Docker, browser tooling, or generators from a different checkout than SOURCE_WORKTREE
- use generic `write tests first`, RED/GREEN ceremony, test count, or coverage as a success criterion
- accept a lower-fidelity GREEN when it cannot observe the actual browser/rendering/input/persistence failure mode
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
- PRIMARY_CRITERION passes at PRIMARY_FIDELITY or at an explicitly justified escalated fidelity
- the confirmed root cause is closed at the correct owner rather than bypassed by a leaf workaround
- the same invariant is not newly duplicated across directly affected callers
- changed and directly affected modules have zero introduced LSP/typecheck/lint errors
- no higher-fidelity or broad-suite verification is required unless there is concrete blast-radius evidence

VERIFY:
- <command/inspection/runtime evidence that directly decides PRIMARY_CRITERION>
- <directly affected typecheck/lint/test command>
- <higher-fidelity runtime/browser evidence only when required by the failure mode or ESCALATE_IF>

STOP:
- current main already satisfies OBJECTIVE, PRIMARY_CRITERION, and structural closure
- PRIMARY_CRITERION passes with direct-impact closure and required static checks, with no concrete reason to escalate fidelity
- required change would alter user-visible/domain behavior, authorization, or acceptance beyond the approved objective
- a discovered problem requires a different root cause, rollback boundary, or independent primary criterion; report it separately instead of fixing it now
- validator or runtime required for PRIMARY_CRITERION is unavailable and there is no equivalent sufficiently faithful verification
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
VERIFY: <one line, include PRIMARY_CRITERION and fidelity used>
COMMIT: <only when published>
BLOCKER: <only when blocked>
NEXT: <only when blocked>
```
