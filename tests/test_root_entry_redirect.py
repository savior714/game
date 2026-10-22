from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_index_redirects_to_templates_main() -> None:
    index_html = ROOT / "index.html"
    assert index_html.exists()

    html = index_html.read_text(encoding="utf-8")
    assert "학습 게임 놀이터" in html
    # 허브 상단 크롬은 brand 링크가 홈을 담당한다 (허브에는 별도 홈 버튼을 두지 않는다)
    assert 'href="./index.html"' in html
    assert "ag-hud__brand-home" in html
