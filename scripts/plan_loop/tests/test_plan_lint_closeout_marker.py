import unittest

from scripts.plan_loop.plan_lint import lint_plan_text


def _blueprint_with_conclusion(conclusion: str) -> str:
  return f"""<!-- Language: ko -->
# 🗺️ Project Blueprint: 테스트
## 문서 메타
- **SSOT Check**: ok
- **Project Status Link**: ok
- **Architectural Goal**: ok
- **Priority**: 1
- **Labels**: test

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
just route docs/plans/PLAN_test.md --json
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
|| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: closeout [Unit: Atomic]
- Task-ID: [LINT-901] | Status: done | RetryPolicy: none
- **Pre-read**: 이 Task 만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=0 must_read_installed=0 -->
- **MCP**: desktop-command
- **Action**: Edit
- **Target**: file.py
- **Goal**: closeout marker quality gate를 검증한다
- **Diagnostics**: none
- **Verify**: just lint
- **Conclusion**: {conclusion}
- **Dependency**: None

## 🔁 Conclusion & Summary
- **Roll-up**: ok

## ✅ Definition of Done (DoD)
1. Done.
"""


class TestPlanLintCloseoutMarker(unittest.TestCase):
  def test_done_conclusion_without_marker_fails(self):
    issues, _ = lint_plan_text(
      _blueprint_with_conclusion("[PASS] 파일 업데이트와 검증을 완료했다.")
    )
    self.assertTrue(
      any("closed-by:plan-task-close" in issue for issue in issues),
      issues,
    )

  def test_done_conclusion_with_marker_passes(self):
    issues, _ = lint_plan_text(
      _blueprint_with_conclusion(
        "[PASS] 파일 업데이트와 검증을 완료했다. [closed-by:plan-task-close]"
      )
    )
    self.assertFalse(
      any("closed-by:plan-task-close" in issue for issue in issues),
      issues,
    )


if __name__ == "__main__":
  unittest.main()
