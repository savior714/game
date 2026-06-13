import unittest

from scripts.plan_loop.plan_lint import TASK_ID_PATTERN


class TestTaskIDPatternRegex(unittest.TestCase):
    """Test TASK_ID_PATTERN regex directly."""

    def test_valid_task_id_patterns(self):
        """Valid Task ID patterns should match."""
        valid_ids = [
            "[PLAN-001]",
            "[LINT-001]",
            "[TEM-001]",
            "[OBP-001]",
            "[ABC-123]",
            "[XYZ-9999]",
            "[AB-123]",  # Minimum: 2 letters, 3 digits
            "[LINT-SHR-001]",  # Multi-segment blueprint task IDs
        ]

        for task_id in valid_ids:
            self.assertTrue(
                TASK_ID_PATTERN.match(task_id),
                f"{task_id} should match TASK_ID_PATTERN"
            )

    def test_invalid_task_id_patterns(self):
        """Invalid patterns should NOT match."""
        invalid_ids = [
            "[TBD]",           # No dash
            "[TODO]",          # No dash
            "[PLAN-12]",       # Only 2 digits
            "[P-123]",         # Only 1 letter
            "[PLAN-ABC]",      # No digits
            "[plan-001]",      # Lowercase
            "[PLAN001]",       # No dash
            "[Plan-001]",      # Mixed case
        ]

        for task_id in invalid_ids:
            self.assertFalse(
                TASK_ID_PATTERN.match(task_id),
                f"{task_id} should NOT match TASK_ID_PATTERN"
            )

    def test_placeholder_patterns_not_matched(self):
        """Actual placeholders should NOT match TASK_ID_PATTERN."""
        placeholders = [
            "[TBD]",
            "[TODO]",
            "[VALUE]",
            "[판정 — 비개발자용 요약]",
            "[목표 이름]",
            "[절대 경로]",
        ]

        for placeholder in placeholders:
            self.assertFalse(
                TASK_ID_PATTERN.match(placeholder),
                f"{placeholder} should NOT match TASK_ID_PATTERN"
            )


if __name__ == "__main__":
    unittest.main()
