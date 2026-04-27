from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_justfile_exposes_wip_snapshot_recipe() -> None:
    justfile = (ROOT / "Justfile").read_text(encoding="utf-8")

    assert "wip name:" in justfile
    assert ".git-snapshots" in justfile
    assert "git status --short" in justfile
    assert "git diff --binary" in justfile


def test_verify_korean_text_script_exists_at_expected_path() -> None:
    script_path = ROOT / "scripts" / "verify_korean_text.py"

    assert script_path.exists()
    script_text = script_path.read_text(encoding="utf-8")
    assert "def main()" in script_text
    assert "--dir" in script_text


def test_justfile_typecheck_has_resilient_fallback_and_exclusions() -> None:
    justfile = (ROOT / "Justfile").read_text(encoding="utf-8")

    assert "ty check ." in justfile
    assert "--exclude tests/" in justfile
    assert "--exclude tools/tdd_gate_plugin.py" in justfile
    assert "command -v pyright" in justfile


def test_justfile_test_recipe_scopes_to_root_tests_only() -> None:
    justfile = (ROOT / "Justfile").read_text(encoding="utf-8")
    assert "pytest tests" in justfile
