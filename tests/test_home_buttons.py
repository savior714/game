"""명시적 홈 버튼 계약 — 아이는 로고가 홈 버튼이라는 사실을 모른다.

배경: 한동안 상단 크롬의 유일한 홈 동선은 "AIDEN GAME LABS" 워드마크 링크였다.
성인에겐 자연스러운 관례지만 아이에겐 로고일 뿐이라, 게임 화면에서 놀이터 홈으로
돌아오는 길을 찾지 못했다. 그래서 지금 계약은 다음을 강제한다.

1. 홈이 아닌 모든 사용자 화면의 상단 크롬에는 집 아이콘 + "홈" 라벨을 가진
   명시적 홈 버튼(``.ag-home-btn``)이 있다.
2. 그 버튼은 크롬의 **첫 번째** 앵커다 (항상 같은 자리 = 아이가 위치로 기억한다).
3. 버튼은 루트 ``index.html``로 해석되는 href를 갖고, iframe에 실리는 화면은
   ``target="_top"``을 붙인다.
4. 버튼 스타일은 공용 시트 ``shared/ui/home-button.css`` 한 곳만 소유한다.
5. 로고(brand) 링크는 보조 홈 동선으로 남지만, 홈 버튼이 primary control이다.
6. 메인 허브(``index.html``)는 이미 홈이므로 홈 버튼을 두지 않는다.

별도 맥락(인게임 일시정지/결과 화면, 시험 결과 화면)의 홈 CTA는 중복이 아니라
그 맥락의 유일한 종료 동선이므로 그대로 유지한다.
"""

from pathlib import Path
from html.parser import HTMLParser

REPO_ROOT = Path(__file__).parent.parent

HOME_BUTTON_CLASS = "ag-home-btn"
HOME_BUTTON_CSS = "shared/ui/home-button.css"

# 상단 크롬에 명시적 홈 버튼을 두는 페이지 → (홈 목적지, iframe 여부)
HOME_BUTTON_PAGES = [
    ("domains/math/index.html", "../../index.html", False),
    ("domains/english/index.html", "../../index.html", False),
    ("domains/korean/index.html", "../../index.html", False),
    ("domains/science/index.html", "../../index.html", False),
    ("domains/english/weekly-test/index.html", "../../../index.html", False),
    ("domains/reward/guardian/index.html", "../../../index.html", False),
    ("domains/auth/admin/index.html", "../../../index.html", False),
    ("experiments/space-explorer/index.html", "../../index.html", False),
    ("experiments/space-explorer/dino-escape.html", "../../index.html", False),
    ("experiments/space-explorer/orbit-eclipse.html", "../../index.html", False),
    ("experiments/space-explorer/paint-mixing.html", "../../index.html", False),
    ("experiments/magnet/index.html", "../../index.html", True),
    ("experiments/electricity/index.html", "../../index.html", True),
    ("experiments/bubble/index.html", "../../index.html", True),
    # marble은 HUD를 JS로 주입하므로 정적 <header>가 없다 → 소스 레벨로 확인한다.
    ("experiments/marble/index.html", "../../index.html", True),
]

# 정적 마크업에 <header>가 없어 소스 레벨로 확인하는 페이지
JS_INJECTED_CHROME_PAGES = {"experiments/marble/index.html"}

# 메인 허브는 이미 홈이다 → 홈 버튼을 두지 않는다.
HUB_PAGE = "index.html"

# brand cluster(워드마크 링크) 클래스 — 보조 홈 동선
BRAND_CLASSES = (
    "ag-hud__brand",
    "lab-brand",
    "brand-badge",
    "hud-brand",
    "admin-brand",
)

# 과거에 brand와 중복되던 죽은 홈 버튼 클래스. 다시 들여오지 않는다.
DEAD_HOME_CLASSES = (
    "ag-hud__home",
    "compact-hud-home",
    "top-home",
)


class ChromeAnchorParser(HTMLParser):
    """header(상단 크롬) 안의 앵커를 순서대로 수집한다 (href/class/라벨/아이콘)."""

    def __init__(self) -> None:
        super().__init__()
        self.chrome_anchors: list[dict[str, object]] = []
        self.all_anchors: list[dict[str, object]] = []
        self._header_depth = 0
        self._anchor_depth = 0
        self._current: dict[str, object] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "header":
            self._header_depth += 1
            return

        if tag == "a":
            attr_dict = dict(attrs)
            self._anchor_depth += 1
            self._current = {
                "href": attr_dict.get("href"),
                "target": attr_dict.get("target"),
                "class": (attr_dict.get("class") or "").split(),
                "label": "",
                "has_icon": False,
                "in_chrome": self._header_depth > 0,
            }
            self.all_anchors.append(self._current)
            if self._header_depth > 0:
                self.chrome_anchors.append(self._current)
            return

        if tag == "svg" and self._current is not None:
            self._current["has_icon"] = True

    def handle_data(self, data):
        if self._current is not None:
            self._current["label"] += data

    def handle_endtag(self, tag):
        if tag == "header":
            self._header_depth = max(0, self._header_depth - 1)
        elif tag == "a" and self._anchor_depth > 0:
            self._anchor_depth -= 1
            if self._anchor_depth == 0:
                self._current = None


def _parse(rel_path: str) -> ChromeAnchorParser:
    parser = ChromeAnchorParser()
    parser.feed((REPO_ROOT / rel_path).read_text(encoding="utf-8"))
    return parser


def _assert_button_shape(rel_path: str, anchor: dict[str, object], target: str) -> None:
    """홈 버튼은 집 아이콘과 사람이 읽는 "홈" 라벨을 함께 드러내야 한다."""
    assert anchor["href"] == target, (
        f"{rel_path} 홈 버튼은 {target}으로 가야 한다, got {anchor['href']}"
    )
    assert anchor["has_icon"] is True, f"{rel_path} 홈 버튼에 집 아이콘이 없습니다"
    assert "홈" in str(anchor["label"]), (
        f"{rel_path} 홈 버튼에 텍스트 라벨 '홈'이 없습니다 (아이콘만 있으면 아이가 못 읽습니다)"
    )


def test_every_subpage_chrome_has_an_explicit_home_button() -> None:
    """홈이 아닌 화면의 상단 크롬에는 .ag-home-btn 홈 버튼이 반드시 있다."""
    for rel_path, target, in_iframe in HOME_BUTTON_PAGES:
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"File missing: {rel_path}"
        content = file_path.read_text(encoding="utf-8")
        parser = _parse(rel_path)

        if rel_path in JS_INJECTED_CHROME_PAGES:
            # JS가 주입하는 크롬: 소스 레벨에서 홈 버튼 마크업을 확인한다.
            assert f'class="{HOME_BUTTON_CLASS}"' in content, (
                f"{rel_path} must inject the explicit home button"
            )
            assert f'href="{target}" target="_top" class="{HOME_BUTTON_CLASS}"' in content, (
                f"{rel_path} injected home button must point to {target} with target=_top"
            )
            assert "ag-home-btn__label" in content, (
                f"{rel_path} injected home button must keep its text label"
            )
            continue

        buttons = [
            anchor
            for anchor in parser.chrome_anchors
            if HOME_BUTTON_CLASS in anchor["class"]
        ]
        assert len(buttons) == 1, (
            f"{rel_path} 크롬에는 홈 버튼이 정확히 하나여야 합니다, got {len(buttons)}"
        )
        _assert_button_shape(rel_path, buttons[0], target)

        if in_iframe:
            assert buttons[0]["target"] == "_top", (
                f"{rel_path} 홈 버튼은 iframe 밖으로 열어야 합니다 (target=_top)"
            )


def test_home_button_is_the_first_control_in_chrome() -> None:
    """홈 버튼은 크롬의 첫 앵커다 — 위치가 매번 같아야 아이가 기억한다."""
    for rel_path, _target, _iframe in HOME_BUTTON_PAGES:
        if rel_path in JS_INJECTED_CHROME_PAGES:
            continue
        chrome_anchors = _parse(rel_path).chrome_anchors
        assert chrome_anchors, f"{rel_path} 상단 크롬에 앵커가 없습니다"
        classes = chrome_anchors[0]["class"]
        assert HOME_BUTTON_CLASS in classes, (
            f"{rel_path} 첫 번째 크롬 컨트롤은 홈 버튼이어야 합니다, got {classes}"
        )


def test_home_button_stylesheet_is_the_single_owner() -> None:
    """홈 버튼 스타일은 shared/ui/home-button.css만 소유하고 각 페이지가 읽는다."""
    css_path = REPO_ROOT / HOME_BUTTON_CSS
    assert css_path.is_file(), f"{HOME_BUTTON_CSS} must exist"
    css = css_path.read_text(encoding="utf-8")
    assert f".{HOME_BUTTON_CLASS}" in css, "home button class must be styled"
    assert f".{HOME_BUTTON_CLASS}__icon" in css, "home icon must be styled"
    assert f".{HOME_BUTTON_CLASS}__label" in css, "home label must be styled"
    assert ":focus-visible" in css, "home button must expose a keyboard focus ring"
    assert "prefers-reduced-motion" in css, "home button must respect reduced motion"

    for rel_path, _target, _iframe in HOME_BUTTON_PAGES:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert HOME_BUTTON_CSS in content, (
            f"{rel_path} must load {HOME_BUTTON_CSS}"
        )


def test_home_button_href_resolves_to_the_root_hub() -> None:
    """홈 버튼의 상대 경로가 실제로 루트 index.html을 가리킨는지 확인한다."""
    hub = REPO_ROOT / HUB_PAGE
    for rel_path, target, _iframe in HOME_BUTTON_PAGES:
        resolved = (REPO_ROOT / Path(rel_path).parent / target).resolve()
        assert resolved == hub.resolve(), (
            f"{rel_path} 홈 버튼 경로가 깨졌습니다: {target} -> {resolved}"
        )


def test_brand_link_remains_as_secondary_home_affordance() -> None:
    """로고 링크는 보조 홈 동선으로 남는다 (제거하면 성인 관례가 깨진다)."""
    for rel_path, target, _iframe in HOME_BUTTON_PAGES:
        if rel_path in JS_INJECTED_CHROME_PAGES:
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            assert 'class="brand-badge"' in content, (
                f"{rel_path} must keep the brand home link"
            )
            continue

        brand_links = [
            anchor
            for anchor in _parse(rel_path).chrome_anchors
            if anchor["href"] == target and any(c in BRAND_CLASSES for c in anchor["class"])
        ]
        assert brand_links, f"{rel_path} must keep the brand link to {target}"


def test_main_hub_does_not_need_a_home_button() -> None:
    """허브는 이미 홈이다 — 눌러도 제자리인 홈 버튼을 두지 않는다."""
    content = (REPO_ROOT / HUB_PAGE).read_text(encoding="utf-8")
    assert HOME_BUTTON_CLASS not in content, (
        "index.html must not show a home button on the home screen"
    )
    parser = _parse(HUB_PAGE)
    assert any(anchor["href"] == "./index.html" for anchor in parser.chrome_anchors), (
        "hub chrome must keep its self-referencing brand link"
    )


def test_no_dead_home_button_class_remains() -> None:
    """brand와 중복되던 옛 홈 버튼 클래스는 되살아나지 않는다."""
    pages = [rel for rel, _t, _i in HOME_BUTTON_PAGES] + [HUB_PAGE]
    for rel_path in pages:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        for dead in DEAD_HOME_CLASSES:
            assert dead not in content, (
                f"{rel_path} still declares dead home control '{dead}'"
            )
        assert 'data-action="go-home"' not in content, (
            f"{rel_path} must not keep a dead go-home action"
        )


def test_pages_without_brand_keep_explicit_home_link() -> None:
    """brand cluster가 없는 페이지에는 명시적 홈 링크가 남아야 한다."""
    explicit_home_pages = [
        ("ocean-rescue/index.html", "../index.html"),
        ("domains/ocean-rescue/index.html", "../../index.html"),
        ("domains/ocean-rescue/src/index.template.html", "../index.html"),
        ("domains/reward/reward_design_preview.html", "../../index.html"),
    ]
    for rel_path, target in explicit_home_pages:
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"File missing: {rel_path}"

        content = file_path.read_text(encoding="utf-8")
        parser = ChromeAnchorParser()
        parser.feed(content)
        assert any(a["href"] == target for a in parser.all_anchors), (
            f"{rel_path} must keep an explicit home link to {target}"
        )


def test_subject_chip_is_not_nested_inside_a_link() -> None:
    """과목/위치 칩은 링크 라벨이 아니다 (위치 표시에만 사용한다)."""
    for rel_path in (
        "index.html",
        "domains/math/index.html",
        "domains/english/index.html",
        "domains/korean/index.html",
        "domains/science/index.html",
        "domains/english/weekly-test/index.html",
        "domains/reward/guardian/index.html",
    ):
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "ag-hud__subject" in content, f"{rel_path} must have subject chip"

        parser = ChromeAnchorParser()
        parser.feed(content)
        for anchor in parser.all_anchors:
            classes = anchor["class"]
            assert "ag-hud__subject" not in classes, (
                f"{rel_path} subject chip must not be the link label itself"
            )


def test_main_page_core_quiz_subject_buttons_styling() -> None:
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


def test_guardian_home_button_replaces_the_dead_go_home_action() -> None:
    """보호자 화면의 홈 이동은 명시적 홈 버튼이 담당한다 (go-home 액션은 제거됨)."""
    guardian_html = (REPO_ROOT / "domains/reward/guardian/index.html").read_text(
        encoding="utf-8"
    )
    assert 'href="../../../index.html"' in guardian_html
    assert f'class="{HOME_BUTTON_CLASS}"' in guardian_html, (
        "guardian chrome must expose the explicit home button"
    )
    assert 'data-action="go-home"' not in guardian_html, (
        "guardian must not keep a dead go-home action"
    )

    for rel_path in (
        "domains/reward/guardian/guardian.js",
        "domains/reward/guardian/guardian-events.js",
    ):
        source = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "go-home" not in source, (
            f"{rel_path} must not keep a dead go-home handler"
        )


def test_reward_minigame_home_buttons_have_top_target() -> None:
    """Ensure Marble and Bubble home links use target='_top' to prevent iframe nesting."""
    for rel_path in ("experiments/marble/index.html", "experiments/bubble/index.html"):
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert 'href="../../index.html" target="_top"' in content, (
            f"Expected target='_top' on ../../index.html links in {rel_path}"
        )
