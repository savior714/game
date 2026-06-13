"""plan_reset_apply 단위 테스트."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.plan_loop.plan_reset_apply import reset_task_in_markdown


class TestPlanResetApply(unittest.TestCase):
    def test_apply_resets_status_and_audit(self) -> None:
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write(
            """# Test Blueprint

#### Task 1.1: Reset task [Unit: Atomic]
- Task-ID: [RST-001] | Status: done | Priority: 1
- **Goal**: test
- **Conclusion**: [PASS] previously completed task verification passed.

## 🔁 Conclusion & Summary

- roll-up
"""
        )
        plan.close()
        plan_path = Path(plan.name)
        try:
            reset_task_in_markdown(
                plan_path,
                "RST-001",
                sha="deadbeef" * 5,
                approval="사용자 승인: 계획서만 되돌려 재검증 필요",
            )
            updated = plan_path.read_text(encoding="utf-8")
        finally:
            plan_path.unlink(missing_ok=True)

        self.assertIn("Status: todo", updated)
        self.assertIn("[판정 — 비개발자용 요약. 검증 결과]", updated)
        self.assertIn("## Task Reset Audit", updated)
        self.assertIn("| RST-001 |", updated)
        self.assertIn("deadbeef", updated)


if __name__ == "__main__":
    unittest.main()
