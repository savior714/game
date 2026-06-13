from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        out = exc.output
    return out.decode("utf-8", errors="replace").strip()


def _changed_files(base_ref: str) -> set[str]:
    diff_unstaged = _run(["git", "diff", "--name-only", base_ref]).splitlines()
    diff_staged = _run(["git", "diff", "--name-only", "--cached", base_ref]).splitlines()
    all_changed = {line.strip() for line in [*diff_unstaged, *diff_staged] if line.strip()}
    # 존재하지 않는 파일(삭제된 파일)은 제외
    return {f for f in all_changed if Path(f).exists()}


def _is_test_file(path: str) -> bool:
    if path.startswith("tests/mocks/"):
        return False
    p = Path(path)
    if path.startswith("tests/") and path.endswith(".py"):
        # conftest.py·__init__.py·helpers는 픽스처/유틸 전용
        if p.name == "conftest.py" or p.name == "__init__.py" or path.startswith("tests/helpers/"):
            return False
        return p.name.startswith("test_") or p.name.endswith("_test.py")

    # apps/*/tests 나 apps/*/e2e 등 — 실제 테스트 모듈만 (verify.sh·pytest 수집 규칙과 동일)
    if path.endswith(".spec.ts") or path.endswith(".test.ts") or path.endswith(".test.tsx"):
        return True
    if "/e2e/" in path:
        # Playwright fixture/support modules under e2e/fixtures are not test files
        if "/fixtures/" in path:
            return False
        return True
    if "/tests/" in path and path.endswith(".py"):
        return p.name.startswith("test_") or p.name.endswith("_test.py")

    return path.startswith("frontend/") and path.endswith(".spec.ts")


def _is_code_file(path: str) -> bool:
    prefixes = ("src/", "app/", "backend/src/", "frontend/app/", "apps/", "packages/", "services/")
    suffixes = (".py", ".ts", ".tsx", ".js", ".jsx", ".cs")
    return path.startswith(prefixes) and path.endswith(suffixes)


def _has_assertion(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(
        token in content
        for token in ("assert ", "pytest.raises", "self.assert", "expect(", "toBeVisible", "toContainText", "Assert.True", "Assert.Equal")
    )


def _is_reexport_or_support_module(path: Path) -> bool:
    """Skip TDD assertion gate for re-export shims and non-test support modules."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if "Re-export" in content or "re-export" in content:
        return True
    if path.name.endswith("_compat.py"):
        return True
    # Support modules under tests/ with no collected test cases
    if "def test_" not in content and "class Test" not in content:
        return True
    return False


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("tdd-gate")
    group.addoption(
        "--tdd-gate",
        action="store",
        default="hard",
        choices=["off", "soft", "hard"],
        help="TDD gate level: off | soft | hard",
    )
    group.addoption(
        "--tdd-base-ref",
        action="store",
        default="HEAD",
        help="Git base ref used for TDD diff checks",
    )
    group.addoption(
        "--tdd-require-red",
        action="store_true",
        default=False,
        help="Fail when changed tests are already green (strict red-first mode)",
    )


def _fail_or_warn(config: pytest.Config, level: str, code: str, message: str) -> None:
    if level == "hard":
        raise pytest.UsageError(message)
    if level == "soft":
        warnings = getattr(config, "issue_config_time_warning", None)
        if callable(warnings):
            config.issue_config_time_warning(pytest.PytestWarning(f"{code}: {message}"), stacklevel=2)
        else:
            print(f"[TDD Gate:{code}] {message}")


def pytest_sessionstart(session: pytest.Session) -> None:
    config = session.config
    level = config.getoption("--tdd-gate")
    if level == "off":
        return

    base_ref = config.getoption("--tdd-base-ref")
    changed = _changed_files(base_ref)
    if not changed:
        return

    tests_changed = sorted(path for path in changed if _is_test_file(path))
    code_changed = sorted(path for path in changed if _is_code_file(path))

    if not code_changed and not tests_changed:
        # Only non-code/non-test files (e.g. Markdown) changed. Skip gate.
        return

    if code_changed and not tests_changed:
        _fail_or_warn(
            config,
            level,
            "NO_TEST_DIFF",
            "코드 변경이 감지되었지만 tests 변경이 없습니다. 테스트를 먼저 추가하세요.",
        )

    for test_path in tests_changed:
        path = Path(test_path)
        if not _has_assertion(path):
            if _is_reexport_or_support_module(path):
                continue
            _fail_or_warn(
                config,
                level,
                "ASSERT_MISSING",
                f"assertion 없는 테스트 파일은 허용되지 않습니다: {test_path}",
            )


def pytest_collection_finish(session: pytest.Session) -> None:
    level = session.config.getoption("--tdd-gate")
    if level == "off":
        return
    if not session.items:
        _fail_or_warn(session.config, level, "NO_TESTS_COLLECTED", "수집된 테스트가 0개입니다.")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    level = config.getoption("--tdd-gate")
    require_red = config.getoption("--tdd-require-red")
    if level == "off":
        return

    base_ref = config.getoption("--tdd-base-ref")
    changed = _changed_files(base_ref)
    tests_changed = [path for path in changed if _is_test_file(path)]

    if tests_changed and exitstatus == 0 and require_red:
        _fail_or_warn(
            config,
            level,
            "RED_FIRST_REQUIRED",
            "변경된 테스트가 즉시 PASS입니다. red-first(TDD Step 2) 확인이 필요합니다.",
        )
