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
