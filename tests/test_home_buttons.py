from pathlib import Path
from html.parser import HTMLParser

REPO_ROOT = Path(__file__).parent.parent


class HomeLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in ("a", "button"):
            attr_dict = dict(attrs)
            self.links.append((tag, attr_dict))


def test_home_buttons_exist_in_all_pages():
    pages_and_expected_hrefs = [
        ("domains/math/index.html", "../../index.html"),
        ("domains/english/index.html", "../../index.html"),
        ("domains/english/weekly-test/index.html", "../../../index.html"),
        ("domains/korean/index.html", "../../index.html"),
        ("domains/science/index.html", "../../index.html"),
        ("domains/reward/guardian/index.html", None),  # uses data-action="go-home"
        ("domains/auth/admin/index.html", "../../index.html"),
        ("experiments/bubble/index.html", "../../index.html"),
        ("experiments/marble/index.html", "../../index.html"),
        ("experiments/space-explorer/index.html", "../../index.html"),
        ("experiments/space-explorer/dino-escape.html", "../../index.html"),
        ("experiments/space-explorer/orbit-eclipse.html", "../../index.html"),
        ("experiments/space-explorer/paint-mixing.html", "../../index.html"),
        ("ocean-rescue/index.html", "../index.html"),
    ]

    for rel_path, expected_href in pages_and_expected_hrefs:
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"File missing: {rel_path}"

        content = file_path.read_text(encoding="utf-8")
        assert "홈으로" in content or 'data-action="go-home"' in content, (
            f"Home button text/action missing in {rel_path}"
        )

        parser = HomeLinkParser()
        parser.feed(content)

        if expected_href:
            found_in_html = any(
                attrs.get("href") == expected_href
                or expected_href in attrs.get("onclick", "")
                for tag, attrs in parser.links
            )
            found_in_js = expected_href in content
            assert found_in_html or found_in_js, (
                f"Expected home link with href '{expected_href}' in {rel_path}"
            )


def test_main_page_core_quiz_subject_buttons_styling():
    index_path = REPO_ROOT / "index.html"
    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")

    assert "core-subject-grid" in content
    assert "core-subject-btn" in content
    assert "수학 놀이" in content
    assert "영어 놀이" in content
    assert "국어 놀이" in content
    assert "과학 놀이" in content

    styles_path = REPO_ROOT / "styles.css"
    assert styles_path.exists()
    styles_content = styles_path.read_text(encoding="utf-8")

    assert ".core-subject-grid" in styles_content
    assert ".core-subject-btn" in styles_content
