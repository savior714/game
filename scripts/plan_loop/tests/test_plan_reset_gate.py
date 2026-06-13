"""plan_reset_gate 단위 테스트."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.plan_loop.plan_reset_gate import run_reset_gate, validate_approval


class TestPlanResetGate(unittest.TestCase):
    def test_missing_approval_fails(self) -> None:
        with self.assertRaises(SystemExit):
            validate_approval("short")

    def test_valid_inputs_pass(self) -> None:
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write(
            """# Test Blueprint

#### Task 1.1: Gate task [Unit: Atomic]
- Task-ID: [GATE-001] | Status: done | Priority: 1
- **Goal**: test
- **Verify**: `python3 -c "import sys; sys.exit(0)"`
- **Conclusion**: [PASS] done
"""
        )
        plan.close()
        plan_path = Path(plan.name)
        try:
            run_reset_gate(
                plan_path=plan_path,
                task_id="GATE-001",
                sha="HEAD",
                approval="사용자가 TEM-216 재검증을 위해 리셋을 승인함",
                skip_verify=False,
            )
        finally:
            plan_path.unlink(missing_ok=True)

    def test_cli_missing_approval_exits_nonzero(self) -> None:
        script = Path(__file__).resolve().parents[1] / "plan_reset_gate.py"
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(script),
                "--plan",
                "docs/plans/archive/blueprints/PLAN_plan_todo_reset_sync.md",
                "--task",
                "PTRS-001",
                "--sha",
                "HEAD",
                "--approval",
                "short",
            ],
            cwd=str(Path(__file__).resolve().parents[3]),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("승인", result.stderr)


if __name__ == "__main__":
    unittest.main()
