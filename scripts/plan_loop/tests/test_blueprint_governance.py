import unittest
from pathlib import Path

from scripts.plan_loop.plan_lint import lint_plan_text


def _minimal_blueprint_body(
    *,
    with_contract: bool,
    with_scope: bool,
    scope_text: str | None = None,
) -> str:
    contract = """
## Agent Completion Contract

|| 허용 | 금지 |
| :--- | :--- |
| Conclusion 갱신 | 선행 Task 건너뛰기 |

**Task 완료 정의**: Verify → Conclusion → done → plan-lint.
""" if with_contract else ""
    if scope_text is not None:
        scope = f"{scope_text}\n\n" if scope_text else ""
    elif with_scope:
        scope = (
            "> **에이전트 스코프**: Task 1개씩. `Verify` PASS → **본 파일** "
            "`Conclusion` → `Status: done` → `just plan-lint docs/plans/PLAN_test.md`.\n\n"
        )
    else:
        scope = ""
    return f"""<!-- Language: ko -->

# 🗺️ Project Blueprint: 테스트

## 문서 메타
- **SSOT Check**: ok
- **Project Status Link**: ok
- **Architectural Goal**: ok
- **Linear-Issue**: TEM-999

## 📋 업무 요약 (협업용)

### 개요

테스트.

### staff·경영에서 바뀌는 점

- 없음

### 끝났을 때 확인할 것

- 없음

## 🔍 Diagnosis & Findings

- **현상**: x

## 🏗️ Architectural Deepening

- **Seam**: x

## 📜 Conceptual Sketch

```
sketch
```

## 🛡️ Risk & Strategy

- **Risk**: x — **Strategy**: y

## 🔍 Impact Scope

| f | r |
| :--- | :--- |
| a | b |

{contract}
## 🛠️ Step-by-Step Execution Plan

{scope}#### Task 1.1: Fix [Unit: Atomic]
- Task-ID: [TST-001] | Status: todo | RetryPolicy: none
- **Pre-read**: none
- **Action**: Edit
- **Target**: file.py
- **Goal**: fix
- **Diagnostics**: 0
- **Verify**: `just lint`
- **Conclusion**: [판정 — 비개발자용 요약. 검증 결과]
- **Dependency**: None

## 🔁 Conclusion & Summary

- **Roll-up**: ok

## ✅ Definition of Done (DoD)

- `just lint`
"""


class TestActiveRootBlueprintGovernance(unittest.TestCase):
    """Reference template: Contract + agent scope mandatory for active root plans only."""

    def test_active_root_missing_contract_warns(self):
        body = _minimal_blueprint_body(with_contract=False, with_scope=True)
        path = Path("docs/plans/PLAN_test_governance.md")
        issues, warnings = lint_plan_text(body, file_path=path)
        self.assertFalse(
            any("Agent Completion Contract" in i for i in issues),
            issues,
        )
        self.assertTrue(
            any("Agent Completion Contract" in w for w in warnings),
            warnings,
        )

    def test_active_root_missing_scope_fails(self):
        body = _minimal_blueprint_body(with_contract=True, with_scope=False)
        path = Path("docs/plans/PLAN_test_governance.md")
        issues, _ = lint_plan_text(body, file_path=path)
        self.assertTrue(
            any("agent scope" in i.lower() for i in issues),
            issues,
        )

    def test_active_root_incomplete_scope_fails(self):
        path = Path("docs/plans/PLAN_test_governance.md")
        planlint_only = _minimal_blueprint_body(
            with_contract=True,
            with_scope=False,
            scope_text=(
                "> **에이전트 스코프**: Task 1개씩. `Verify` PASS → "
                "`just plan-lint docs/plans/PLAN_test.md`."
            ),
        )
        conclusion_only = _minimal_blueprint_body(
            with_contract=True,
            with_scope=False,
            scope_text=(
                "> **에이전트 스코프**: Task 1개씩. `Verify` PASS → "
                "`Conclusion` → `Status: done`."
            ),
        )
        for body in (planlint_only, conclusion_only):
            with self.subTest(body=body[:80]):
                issues, _ = lint_plan_text(body, file_path=path)
                self.assertTrue(
                    any(
                        "Conclusion" in i and "plan-lint" in i
                        for i in issues
                    ),
                    issues,
                )

    def test_active_root_with_governance_passes_governance_rules(self):
        body = _minimal_blueprint_body(with_contract=True, with_scope=True)
        path = Path("docs/plans/PLAN_test_governance.md")
        issues, _ = lint_plan_text(body, file_path=path)
        governance = [
            i
            for i in issues
            if "Agent Completion Contract" in i or "agent scope" in i.lower()
        ]
        self.assertEqual(governance, [], issues)

    def test_archive_path_skips_governance(self):
        body = _minimal_blueprint_body(with_contract=False, with_scope=False)
        path = Path("docs/plans/archive/PLAN_test_governance.md")
        issues, _ = lint_plan_text(body, file_path=path)
        self.assertFalse(
            any("Agent Completion Contract" in i for i in issues),
            issues,
        )

    def test_active_root_dod_checkbox_fails(self):
        body = _minimal_blueprint_body(with_contract=True, with_scope=True).replace(
            "- `just lint`",
            "1. [ ] `just lint`",
        )
        path = Path("docs/plans/PLAN_test_dod_checkbox.md")
        issues, warnings = lint_plan_text(body, file_path=path)
        self.assertTrue(any("checkbox format" in i for i in issues), issues)
        self.assertFalse(any("checkbox format" in w for w in warnings), warnings)

    def test_archive_dod_checkbox_warns_only(self):
        body = _minimal_blueprint_body(with_contract=True, with_scope=True).replace(
            "- `just lint`",
            "1. [ ] `just lint`",
        )
        path = Path("docs/plans/archive/PLAN_test_dod_checkbox.md")
        issues, warnings = lint_plan_text(body, file_path=path)
        self.assertFalse(any("checkbox format" in i for i in issues), issues)
        self.assertTrue(any("checkbox format" in w for w in warnings), warnings)


if __name__ == "__main__":
    unittest.main()
