"""
Verify that every subject domain's #stats-box exposes dialog semantics:
  role="dialog", aria-modal="true", and a non-empty aria-labelledby
  pointing to an existing, non-empty heading inside #stats-box.
"""

import os
from html.parser import HTMLParser
from pathlib import Path
import pytest

DOMAINS = ["korean", "math", "english", "science"]
ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Tiny attribute-tracking parser
# ---------------------------------------------------------------------------

class StatsBoxCollector(HTMLParser):
    """Collect id, role, aria-modal, aria-labelledby attributes of #stats-box,
    and the ids + text contents of every element inside it."""

    def __init__(self):
        super().__init__()
        self.stats_box_attrs: dict | None = None
        self.ids_inside: set[str] = set()
        self.text_inside: dict[str, str] = {}  # id -> text
        self._depth = 0
        self._in_stats_box = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if not self._in_stats_box:
            if attr_dict.get("id") == "stats-box":
                self._in_stats_box = True
                self.stats_box_attrs = attr_dict
                self._depth = 1
                return
        else:
            eid = attr_dict.get("id")
            if eid:
                self.ids_inside.add(eid)
                self.text_inside[eid] = ""

    def handle_endtag(self, tag):
        if self._in_stats_box:
            self._depth -= 1
            if self._depth <= 0:
                self._in_stats_box = False

    def handle_data(self, data):
        if self._in_stats_box:
            # Find the most recently opened element with an id inside stats-box
            for eid in reversed(list(self.ids_inside)):
                if self.text_inside.get(eid, "") == "":
                    self.text_inside[eid] = data
                    break


def _parse(path: Path) -> StatsBoxCollector:
    html = path.read_text(encoding="utf-8")
    p = StatsBoxCollector()
    p.feed(html)
    return p


# ---------------------------------------------------------------------------
# Per-domain fixture
# ---------------------------------------------------------------------------

@pytest.fixture(params=DOMAINS, ids=DOMAINS)
def stats_box(request) -> tuple[str, StatsBoxCollector]:
    domain = request.param
    path = ROOT / "domains" / domain / "index.html"
    assert path.exists(), f"missing {path}"
    collector = _parse(path)
    return domain, collector


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def test_stats_box_exists(stats_box):
    domain, c = stats_box
    assert c.stats_box_attrs is not None, (
        f"[{domain}] #stats-box not found"
    )


def test_stats_box_has_role_dialog(stats_box):
    domain, c = stats_box
    role = (c.stats_box_attrs or {}).get("role", "")
    assert role == "dialog", (
        f"[{domain}] expected role=dialog, got role={role!r}"
    )


def test_stats_box_has_aria_modal_true(stats_box):
    domain, c = stats_box
    val = (c.stats_box_attrs or {}).get("aria-modal", "")
    assert val == "true", (
        f"[{domain}] expected aria-modal=true, got aria-modal={val!r}"
    )


def test_stats_box_has_aria_labelledby(stats_box):
    domain, c = stats_box
    val = (c.stats_box_attrs or {}).get("aria-labelledby", "")
    assert val, f"[{domain}] aria-labelledby is empty or missing"


def test_labelledby_target_exists(stats_box):
    domain, c = stats_box
    ref = (c.stats_box_attrs or {}).get("aria-labelledby", "")
    assert ref in c.ids_inside, (
        f"[{domain}] aria-labelledby={ref!r} but no element with that id "
        f"exists inside #stats-box. Found ids: {sorted(c.ids_inside)}"
    )


def test_labelledby_target_has_text(stats_box):
    domain, c = stats_box
    ref = (c.stats_box_attrs or {}).get("aria-labelledby", "")
    text = c.text_inside.get(ref, "").strip()
    assert text, (
        f"[{domain}] labelledby target id={ref!r} has no visible text"
    )
