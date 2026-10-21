"""보호자 페이지(guardian/index.html) 마크업 구조 계약.

배경
- de7b1e2(로컬 백업/복원 추가)에서 "보상 추가 폼 카드"의 닫는 </div>가 지워졌다.
- 그 결과 #reward-custom-section이 닫히지 않았고, 브라우저는 </main>을 만나서야 이
  div를 암묵적으로 닫는다. #growth-panel · #local-backup-section ·
  #backup-restore-modal이 모두 #reward-custom-section의 후손이 되어 버린다.
- guardian.js의 showGrowthTab()은 #reward-custom-section을 display:none으로 숨기므로,
  성장 탭에서는 성장 요약 패널과 백업 섹션까지 함께 사라졌다.
- 기존 테스트는 id 문자열의 존재만 확인해서 이 중첩 오류를 잡지 못했다.

이 테스트는 브라우저처럼 오류를 "고쳐서" 읽지 않고, 닫힘 누락을 그대로 보고하는
엄격한 트리 파서로 구조를 검증한다. (표준 라이브러리만 사용, 브라우저 불필요)
"""

from __future__ import annotations

from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN_HTML = ROOT / "domains" / "reward" / "guardian" / "index.html"

# 닫는 태그가 없는 HTML void 요소 — 열린 요소 스택에 올리지 않는다.
VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

# guardian.js의 showGrowthTab()은 #reward-custom-section을 display:none으로 숨기고
# 같은 순간 아래 패널을 보여 준다. 따라서 이 패널들은 #reward-custom-section의
# 후손이면 안 된다.
PEER_PANEL_IDS = ("growth-panel", "local-backup-section", "backup-restore-modal")


class Node:
    __slots__ = ("tag", "attrs", "line", "parent", "children")

    def __init__(
        self,
        tag: str,
        attrs: dict[str, str | None],
        line: int,
        parent: Node | None,
    ) -> None:
        self.tag = tag
        self.attrs = attrs
        self.line = line
        self.parent = parent
        self.children: list[Node] = []

    @property
    def label(self) -> str:
        element_id = self.attrs.get("id")
        return f"<{self.tag}#{element_id}>" if element_id else f"<{self.tag}>"

    def ancestors(self) -> Iterator[Node]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


class StrictTreeBuilder(HTMLParser):
    """닫힘 누락을 브라우저처럼 고치지 않고 그대로 기록하는 엄격한 트리 빌더."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, 0, None)
        self._current = self.root
        self.by_id: dict[str, Node] = {}
        self.problems: list[str] = []

    def _add(self, tag: str, attrs: list[tuple[str, str | None]]) -> Node:
        node = Node(tag, dict(attrs), self.getpos()[0], self._current)
        self._current.children.append(node)
        element_id = node.attrs.get("id")
        if element_id:
            self.by_id[element_id] = node
        return node

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = self._add(tag, attrs)
        if tag not in VOID_TAGS:
            self._current = node

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # <path ... />처럼 스스로 닫히는 요소: 하위로 내려가지 않는다.
        self._add(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        line = self.getpos()[0]
        unclosed: list[Node] = []
        node = self._current
        while node is not self.root and node.tag != tag:
            unclosed.append(node)
            assert node.parent is not None
            node = node.parent
        if node is self.root:
            self.problems.append(f"{line}행: 짝이 없는 </{tag}>")
            return
        for orphan in unclosed:
            self.problems.append(
                f"{line}행 </{tag}>: 닫히지 않은 요소 {orphan.label} "
                f"(열린 위치: {orphan.line}행)"
            )
        assert node.parent is not None
        self._current = node.parent

    def finish(self) -> None:
        self.close()
        node = self._current
        while node is not self.root:
            self.problems.append(
                f"문서 끝: 닫히지 않은 요소 {node.label} (열린 위치: {node.line}행)"
            )
            assert node.parent is not None
            node = node.parent


@pytest.fixture(scope="module")
def tree() -> StrictTreeBuilder:
    builder = StrictTreeBuilder()
    builder.feed(GUARDIAN_HTML.read_text(encoding="utf-8"))
    builder.finish()
    return builder


def _element(tree: StrictTreeBuilder, element_id: str) -> Node:
    assert element_id in tree.by_id, f"#{element_id} 요소를 찾을 수 없습니다"
    return tree.by_id[element_id]


def test_guardian_markup_is_well_nested(tree: StrictTreeBuilder) -> None:
    """모든 요소가 짝에 맞게 열고 닫혀야 한다 (브라우저의 암묵적 복구에 기대지 않는다)."""
    assert not tree.problems, "마크업 중첩 오류:\n" + "\n".join(tree.problems)


@pytest.mark.parametrize("panel_id", PEER_PANEL_IDS)
def test_peer_panels_are_not_inside_reward_section(
    tree: StrictTreeBuilder, panel_id: str
) -> None:
    """성장 탭에서 #reward-custom-section을 숨겨도 성장 패널·백업 섹션은 보여야 한다."""
    reward_section = _element(tree, "reward-custom-section")
    panel = _element(tree, panel_id)
    assert reward_section not in panel.ancestors(), (
        f"#{panel_id} 요소가 #reward-custom-section 안에 중첩돼 있습니다. "
        "showGrowthTab()은 #reward-custom-section을 display:none으로 숨기므로 "
        "이 요소도 함께 사라집니다."
    )


def test_reward_list_is_a_sibling_of_the_add_form_card(
    tree: StrictTreeBuilder,
) -> None:
    """보상 목록(#cr-list)은 '추가 폼 카드' 안이 아니라 그 형제여야 한다."""
    form_card = _element(
        tree, "cr-desc"
    ).parent  # 아이콘·이름·설명·가격 입력을 담은 카드
    assert form_card is not None
    reward_list = _element(tree, "cr-list")
    assert form_card not in reward_list.ancestors(), (
        "#cr-list 요소가 보상 추가 폼 카드 안에 들어가 있습니다. "
        "폼 카드를 닫는 </div>가 #cr-list 앞에 있어야 합니다."
    )
    assert reward_list.parent is form_card.parent, (
        "#cr-list와 보상 추가 폼 카드는 같은 부모를 가진 형제여야 합니다."
    )
