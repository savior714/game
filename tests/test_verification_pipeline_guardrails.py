"""Tests for Verification Pipeline Guardrails and Timeout Safety.

Verifies:
1. pytest.ini configuration invariants:
   - Global timeout enabled (e.g. 30s) with thread method.
   - Tiering marker filter configured by default: -m "not browser and not live".
   - Required markers declared (browser, live, slow, ocean_rescue).
2. conftest.py classification hooks:
   - Automatically marks browser tests importing Playwright.
   - Automatically marks live external / real DB tests.
   - Preserves non-browser markdown workflow tests.
3. Timeout execution proof:
   - Proves hanging/infinite-waiting tests are terminated by pytest-timeout.
4. verify.sh and Justfile pipeline invariants:
   - verify.sh runs targeted core policy tests instead of unbounded full suite.
   - Justfile exposes tiered testing commands (test, test-browser, test-live, test-all).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTEST_INI = ROOT / "pytest.ini"
CONFTEST_PY = ROOT / "tests/conftest.py"
VERIFY_SH = ROOT / "verify.sh"
JUSTFILE = ROOT / "Justfile"


def test_pytest_ini_guardrails() -> None:
    """Verify pytest.ini has timeout and tiering markers configured."""
    assert PYTEST_INI.is_file(), "pytest.ini missing"
    content = PYTEST_INI.read_text(encoding="utf-8")

    # 1. Timeout enforcement
    assert "timeout =" in content or "--timeout=" in content
    assert "timeout_method = thread" in content

    # 2. Default tiering filter: browser and live tests excluded by default
    assert (
        '-m "not browser and not live"' in content
        or "-m 'not browser and not live'" in content
    )

    # 3. Declared markers
    assert "browser:" in content
    assert "live:" in content
    assert "ocean_rescue:" in content


def test_conftest_automatic_tagging_contract() -> None:
    """Verify conftest.py defines required tagging hooks."""
    assert CONFTEST_PY.is_file(), "conftest.py missing"
    code = CONFTEST_PY.read_text(encoding="utf-8")

    assert "pytest_collection_modifyitems" in code
    assert "pytest.mark.browser" in code
    assert "pytest.mark.live" in code
    assert "test_playwright_git_workflow_consistency.py" in code


def test_pytest_timeout_kills_hanging_test() -> None:
    """Prove that pytest-timeout kills a hanging sleep test within designated timeout."""
    with tempfile.TemporaryDirectory() as td:
        test_file = os.path.join(td, "test_hang_probe.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                """
import time
def test_sleep_infinite():
    time.sleep(15)
"""
            )

        res = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "--timeout=2",
                "--timeout_method=thread",
                "-q",
                test_file,
            ],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 1, (
            f"Expected timeout failure (1), got {res.returncode}"
        )
        combined = res.stdout + res.stderr
        assert "Timeout" in combined, "Output did not indicate Timeout"


def test_verify_sh_pipeline_invariants() -> None:
    """Verify verify.sh uses targeted test execution with timeouts."""
    assert VERIFY_SH.is_file(), "verify.sh missing"
    script = VERIFY_SH.read_text(encoding="utf-8")

    # 1. Core policy tests listed
    assert "CORE_POLICY_TESTS=(" in script
    assert "tests/test_active_product_scope_policy.py" in script
    assert "tests/test_core_agent_contract_consistency.py" in script
    assert "tests/test_git_workflow_guardrails.py" in script

    # 2. Timeout protection in test execution
    assert "--timeout=" in script


def test_justfile_tiered_test_recipes() -> None:
    """Verify Justfile defines tiered test recipes."""
    assert JUSTFILE.is_file(), "Justfile missing"
    just_content = JUSTFILE.read_text(encoding="utf-8")

    assert "verify *args=" in just_content
    assert "verify-all:" in just_content
    assert "test:" in just_content
    assert "test-browser:" in just_content
    assert "test-live:" in just_content
    assert "test-all:" in just_content
