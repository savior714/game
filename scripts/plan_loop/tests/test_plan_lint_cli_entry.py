import subprocess
import sys
from pathlib import Path


def test_plan_lint_non_md_argv_exits_one(tmp_path: Path) -> None:
    non_md_file = tmp_path / "test.txt"
    non_md_file.write_text("dummy")

    result = subprocess.run(
        [sys.executable, "scripts/plan_loop/plan_lint.py", str(non_md_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert "[SKIP]" in output
    assert "No .md" in output


def test_plan_lint_module_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "scripts.plan_loop.plan_lint", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Lint plan markdown" in result.stdout

