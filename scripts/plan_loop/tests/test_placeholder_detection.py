import unittest

from scripts.plan_loop.plan_lint import lint_plan_text


class TestPlaceholderDetectionWithTaskIDs(unittest.TestCase):
    """Test that Task ID patterns like [PLAN-001] are NOT flagged as placeholders."""

    def test_plan_reference_not_flagged_as_placeholder(self):
        """[PLAN-001] should pass — it's a valid Task ID reference."""
        content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: ok
- Project Status Link: ok
- Architectural Goal: ok

## 🔍 Diagnosis & Findings
Symptoms...

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
||| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: Fix it [Unit: Atomic]
- Task-ID: [LINT-001] | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: fix placeholder detection
- Diagnostics: none
- Verify: just lint
- Conclusion: done
- Dependency: None

## 🔁 Conclusion & Summary
- Roll-up: ok

## ✅ Definition of Done (DoD)
1. Done.
"""
        issues, _warnings = lint_plan_text(content)
        # Should NOT have placeholder errors for [PLAN-001] or [LINT-001]
        self.assertFalse(
            any("placeholder" in issue.lower() for issue in issues),
            f"Task ID [LINT-001] should not be flagged as placeholder. Issues: {issues}"
        )

    def test_plan_link_in_goal_not_flagged(self):
        """[PLAN-001] in Goal should pass — it's a reference, not a placeholder."""
        content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: ok
- Project Status Link: ok
- Architectural Goal: ok

## 🔍 Diagnosis & Findings
See [PLAN-001] for context.

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
||| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: Fix it [Unit: Atomic]
- Task-ID: [LINT-002] | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: fix issue referenced in [PLAN-001]
- Diagnostics: none
- Verify: just lint
- Conclusion: done
- Dependency: None

## 🔁 Conclusion & Summary
- Roll-up: ok

## ✅ Definition of Done (DoD)
1. Done.
"""
        issues, _warnings = lint_plan_text(content)
        # Should NOT have placeholder errors
        self.assertFalse(
            any("placeholder" in issue.lower() for issue in issues),
            f"[PLAN-001] reference should not be flagged. Issues: {issues}"
        )

    def test_various_task_id_formats_not_flagged(self):
        """Test various Task ID formats are not flagged."""
        test_cases = [
            "[PLAN-001]",
            "[LINT-001]",
            "[TEM-001]",
            "[OBP-001]",
            "[RDP-001]",
            "[ABC-123]",
            "[XYZ-9999]",
        ]

        for task_id in test_cases:
            content = f"""
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: ok
- Project Status Link: ok
- Architectural Goal: ok

## 🔍 Diagnosis & Findings
...

## 🏗️ Architectural Deepening
...

## 📜 Conceptual Sketch
...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
||| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: Test [Unit: Atomic]
- Task-ID: {task_id} | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: test task id
- Diagnostics: none
- Verify: just lint
- Conclusion: done
- Dependency: None

## 🔁 Conclusion & Summary
- Roll-up: ok

## ✅ Definition of Done (DoD)
1. Done.
"""
            issues, _warnings = lint_plan_text(content)
            self.assertFalse(
                any("placeholder" in issue.lower() for issue in issues),
                f"Task ID {task_id} should not be flagged as placeholder. Issues: {issues}"
            )

    def test_actual_placeholder_still_detected(self):
        """[TBD] should still be flagged as placeholder."""
        content = """<!-- Language: ko -->
# 🗺️ Project Blueprint: 테스트 계획서
## 문서 메타
- **SSOT Check**: [TBD]
- **Project Status Link**: ok
- **Architectural Goal**: ok
- **Priority**: 3
- **Labels**: Test
- **Linear-Issue**: TEM-XXX

## 📋 업무 요약 (협업용)
### 개요
테스트

### staff·경영에서 바뀌는 점
테스트

### 끝났을 때 확인할 것
테스트

## 🧭 Context Pre-read Gate (실행 전 필수)
<!-- plan-preread:v1 generated=2026-01-01T00:00:00Z paths=0 must_read_installed=0 -->

### Read SSOT

### 재검증 (구현 세션에서 편집 전)
```bash
just route -- --json
```

## 🔍 Diagnosis & Findings
...

## 🏗️ Architectural Deepening
...

## 📜 Conceptual Sketch
...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
||| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: Test [Unit: Atomic]
- Task-ID: [LINT-003] | Status: todo | RetryPolicy: none
- **Pre-read**: 이 Task 만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=0 must_read_installed=0 -->
- Action: Edit
- Target: file.py
- Goal: test
- Diagnostics: none
- Verify: just lint
- Conclusion: done
- Dependency: None

## 🔁 Conclusion & Summary
- Roll-up: ok
- Continuity: ok

## ✅ Definition of Done (DoD)
1. Done.
"""
        issues, _warnings = lint_plan_text(content)
        # [TBD] is in doc meta, not task field - check for missing/empty error
        self.assertTrue(
            any("placeholder" in issue.lower() or "missing/empty" in issue.lower() for issue in issues),
            f"[TBD] should still be flagged as placeholder. Issues: {issues}"
        )


class TestRollupSummaryPlaceholder(unittest.TestCase):
    """Roll-up section placeholder detection (closeout Task done + plan-close gate)."""

    _BLUEPRINT_PREFIX = """
# 🗺️ Project Blueprint: Roll-up 테스트
## 문서 메타
- SSOT Check: ok
- Project Status Link: ok
- Architectural Goal: ok

## 🔍 Diagnosis & Findings
Symptoms...

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
| f | r |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: 구현 [Unit: Atomic]
- Task-ID: [RUP-001] | Status: done | RetryPolicy: none
- **Pre-read**: paths <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[rule]` `.agents/core/execution.md`
- Action: Edit
- Target: file.py
- Goal: 구현 완료
- Diagnostics: 0
- Verify: just lint
- Conclusion: [PASS] done [closed-by:plan-task-close]
- Dependency: None

### Phase 2 — Blueprint closeout
#### Task 2.1: Roll-up [Unit: Atomic]
- Task-ID: [RUP-099] | Status: {closeout_status} | RetryPolicy: none
- **Pre-read**: paths <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[rule]` `.agents/workflows/plan.md`
- Action: Document
- Target: docs/plans/PLAN_rollup_test.md
- Goal: Roll-up 1문단 작성 후 plan-close로 검증한다.
- Diagnostics: 0
- Verify: `just plan-close plan=docs/plans/PLAN_rollup_test.md`
- Conclusion: {closeout_conclusion}
- Dependency: RUP-001

## 🔁 Conclusion & Summary

{rollup_body}

## ✅ Definition of Done (DoD)
- `just lint`
"""

    def test_closeout_done_with_placeholder_rollup_fails_lint(self):
        content = self._BLUEPRINT_PREFIX.format(
            closeout_status="done",
            closeout_conclusion="[PASS] roll-up done [closed-by:plan-task-close]",
            rollup_body="(Roll-up: Task 2.1 closeout 후 기입.)",
        )
        issues, _warnings = lint_plan_text(content)
        self.assertTrue(
            any("Roll-up is still a placeholder" in issue for issue in issues),
            f"Expected rollup placeholder lint FAIL. Issues: {issues}",
        )

    def test_closeout_todo_with_placeholder_rollup_passes_lint(self):
        content = self._BLUEPRINT_PREFIX.format(
            closeout_status="todo",
            closeout_conclusion="[판정 — 비개발자용 요약. 검증 결과]",
            rollup_body="(Roll-up: Task 2.1 closeout 후 기입.)",
        )
        issues, _warnings = lint_plan_text(content)
        self.assertFalse(
            any("Roll-up is still a placeholder" in issue for issue in issues),
            f"Mid-plan placeholder should not FAIL lint. Issues: {issues}",
        )

    def test_filled_rollup_passes_lint_when_closeout_done(self):
        content = self._BLUEPRINT_PREFIX.format(
            closeout_status="done",
            closeout_conclusion="[PASS] roll-up done [closed-by:plan-task-close]",
            rollup_body=(
                "Child 플랜 완료: baseline 16건을 0으로 줄였고 "
                "test-coupling-gate·ddd-gate가 PASS입니다."
            ),
        )
        issues, _warnings = lint_plan_text(content)
        self.assertFalse(
            any("Roll-up is still a placeholder" in issue for issue in issues),
            f"Filled rollup should PASS. Issues: {issues}",
        )


if __name__ == "__main__":
    unittest.main()
