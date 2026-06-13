import unittest

from scripts.plan_loop.plan_lint import lint_plan_text


def _build_minimal_blueprint(goal_text: str, task_id: str = "[LINT-004]") -> str:
    """Build a minimal valid blueprint with the given goal."""
    return f"""<!-- Language: ko -->
# 🗺️ Project Blueprint: 테스트 계획서
## 문서 메타
- **SSOT Check**: ok
- **Project Status Link**: 신규
- **Architectural Goal**: 테스트
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
- Task-ID: {task_id} | Status: todo | RetryPolicy: none
- **Pre-read**: 이 Task 만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=0 must_read_installed=0 -->
- **Action**: Edit
- **Target**: file.py
- **Goal**: {goal_text}
- **Diagnostics**: none
- **Verify**: just lint
- **Conclusion**: done
- **Dependency**: None

## 🔁 Conclusion & Summary
- **Roll-up**: ok
- **Continuity**: ok

## ✅ Definition of Done (DoD)
1. Done.
"""


class TestGoalConjunctionValidation(unittest.TestCase):
    """Test that Goal field with Korean conjunctions is rejected."""

    def test_forbidden_conjunction_mit_detected(self):
        """Goal with '및' should be rejected."""
        content = _build_minimal_blueprint("fix lint 및 add tests")
        issues, _warnings = lint_plan_text(content)
        self.assertTrue(
            any("atomic" in issue.lower() and "conjunction" in issue.lower() for issue in issues),
            f"Goal with '및' should be rejected. Issues: {issues}"
        )

    def test_forbidden_conjunction_geuri_do_detected(self):
        """Goal with '그리고' should be rejected."""
        content = _build_minimal_blueprint("refactor code 그리고 add documentation")
        issues, _warnings = lint_plan_text(content)
        self.assertTrue(
            any("atomic" in issue.lower() and "conjunction" in issue.lower() for issue in issues),
            f"Goal with '그리고' should be rejected. Issues: {issues}"
        )

    def test_forbidden_conjunction_ttohum_detected(self):
        """Goal with '또한' should be rejected."""
        content = _build_minimal_blueprint("update API 또한 add integration tests")
        issues, _warnings = lint_plan_text(content)
        self.assertTrue(
            any("atomic" in issue.lower() and "conjunction" in issue.lower() for issue in issues),
            f"Goal with '또한' should be rejected. Issues: {issues}"
        )

    def test_atomic_goal_without_conjunctions_passes(self):
        """Goal without conjunctions should pass."""
        content = """
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
#### Task 1.1: Fix lint [Unit: Atomic]
- Task-ID: [LINT-007] | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: fix lint errors
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
            any("atomic" in issue.lower() and "conjunction" in issue.lower() for issue in issues),
            f"Atomic Goal should pass. Issues: {issues}"
        )

    def test_valid_goal_with_comma_passes(self):
        """Goal with comma (not conjunction) should pass."""
        content = """
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
- Task-ID: [LINT-008] | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: update, validate, test
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
            any("atomic" in issue.lower() and "conjunction" in issue.lower() for issue in issues),
            f"Goal with comma should pass. Issues: {issues}"
        )


if __name__ == "__main__":
    unittest.main()
