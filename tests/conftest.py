"""Bootstrap kernel — ensure repo root is importable for tools.tdd_gate_plugin and classify tests."""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

pytest_plugins = ["tools.tdd_gate_plugin"]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "browser: marks browser automation tests (Playwright)"
    )
    config.addinivalue_line(
        "markers", "live: marks tests requiring real Supabase or live network services"
    )
    config.addinivalue_line("markers", "slow: marks slow tests taking over 5 seconds")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Automatically tag tests based on file path, name, or module imports.

    This ensures that tests importing Playwright or hitting real external services
    are classified under `browser` or `live`, preventing accidental execution during
    standard fast unit/policy validation runs.
    """
    for item in items:
        file_path = str(item.fspath).lower()
        module = getattr(item, "module", None)
        module_source = ""
        if module and hasattr(module, "__file__") and module.__file__:
            try:
                if not hasattr(module, "_cached_source"):
                    module._cached_source = Path(module.__file__).read_text(
                        encoding="utf-8", errors="ignore"
                    )
                module_source = module._cached_source
            except Exception:
                pass

        # 1. Browser tests: playwright in imports or browser in filename
        is_browser = (
            "_browser" in file_path
            or "browser_" in file_path
            or "playwright" in file_path
            or "from playwright" in module_source
            or "import playwright" in module_source
        )
        # Exception: test_playwright_git_workflow_consistency.py is a pure markdown doc link check
        if "test_playwright_git_workflow_consistency.py" in file_path:
            is_browser = False

        if is_browser:
            item.add_marker(pytest.mark.browser)

        # 2. Live external services / real DB tests
        is_live = (
            "_real_db" in file_path
            or "real_db_" in file_path
            or "verify_live_supabase" in file_path
            or "test_supabase_production" in file_path
            or "test_live_" in file_path
            or "LIVE_SUPABASE_URL" in module_source
        )
        if is_live:
            item.add_marker(pytest.mark.live)
