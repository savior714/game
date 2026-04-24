from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_index_redirects_to_templates_main() -> None:
    index_html = ROOT / "index.html"
    assert index_html.exists()

    html = index_html.read_text(encoding="utf-8")
    assert "학습 게임 놀이터" in html
    assert "<nav" in html
