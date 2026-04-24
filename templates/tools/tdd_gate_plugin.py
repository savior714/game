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
    return {line.strip() for line in [*diff_unstaged, *diff_staged] if line.strip()}


def _is_test_file(path: str) -> bool:
    return path.startswith("tests/") and path.endswith(".py")


def _is_code_file(path: str) -> bool:
    # Adjust prefixes according to your project structure
    prefixes = ("src/", "app/", "backend/src/", "frontend/app/")
    suffixes = (".py", ".ts", ".tsx", ".js", ".jsx")
    return path.startswith(prefixes) and path.endswith(suffixes)


def _has_assertion(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(token in content for token in ("assert ", "pytest.raises", "self.assert"))


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


def _fail_or_warn(config: pytest.Config, level: str, code: str, message: str) -> None:
    if level == "hard":
        raise pytest.UsageError(f"[{code}] {message}")
    if level == "soft":
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

    if code_changed and not tests_changed:
        _fail_or_warn(
            config,
            level,
            "NO_TEST_DIFF",
            "코드 변경이 감지되었지만 tests 변경이 없습니다. 테스트를 먼저 추가하세요.",
        )

    for test_path in tests_changed:
        if not _has_assertion(Path(test_path)):
            _fail_or_warn(
                config,
                level,
                "ASSERT_MISSING",
                f"assertion 없는 테스트 파일은 허용되지 않습니다: {test_path}",
            )
