from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_describes_aidengame_product_identity() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "어린이 학습 게임 놀이터" in readme
    assert "Agentic Development System Bootstrap" not in readme
    assert "국어" in readme and "수학" in readme and "영어" in readme and "과학" in readme


def test_readme_tracks_current_runtime_and_verification_paths() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "`templates/index.html`" in readme
    assert "`templates/space-explorer.html`" in readme
    assert "`vercel.json`" in readme
    assert "`verify.sh`" in readme
