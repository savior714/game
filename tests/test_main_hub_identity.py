from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def test_templates_index_is_aidengame_hub_page() -> None:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    assert "학습 게임 놀이터" in html
    assert "오늘은 어떤" in html
    assert "수학 놀이" in html
    assert "영어 놀이" in html
    assert "국어 놀이" in html
    assert "과학 놀이" in html
    assert "태양계 탐험 (실험)" in html
