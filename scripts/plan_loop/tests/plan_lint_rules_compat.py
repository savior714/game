"""Re-export test classes and helpers from split modules for legacy compatibility."""

import unittest

from scripts.plan_loop.tests.test_blueprint_governance import (
    TestActiveRootBlueprintGovernance,
    _minimal_blueprint_body,
)
from scripts.plan_loop.tests.test_conclusion_placeholder import (
    TestConclusionPlaceholderDetection,
)
from scripts.plan_loop.tests.test_goal_conjunction import (
    TestGoalConjunctionValidation,
    _build_minimal_blueprint,
)
from scripts.plan_loop.tests.test_placeholder_detection import (
    TestPlaceholderDetectionWithTaskIDs,
)
from scripts.plan_loop.tests.test_task_id_pattern import TestTaskIDPatternRegex

# Module-level helpers kept for external consumers.
__all__ = [
    "TestActiveRootBlueprintGovernance",
    "TestConclusionPlaceholderDetection",
    "TestGoalConjunctionValidation",
    "TestPlaceholderDetectionWithTaskIDs",
    "TestTaskIDPatternRegex",
    "_build_minimal_blueprint",
    "_minimal_blueprint_body",
]

if __name__ == "__main__":
    unittest.main()
