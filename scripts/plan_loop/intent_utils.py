#!/usr/bin/env python3
"""Intent extraction utilities for plan preread manifest generation."""
from __future__ import annotations

import re

_INTENT_KEYWORDS = (
    ("리뷰", "리뷰"),
    ("review", "리뷰"),
    ("리팩터", "리팩터"),
    ("refactor", "리팩터"),
    ("접근성", "접근성"),
    ("a11y", "a11y"),
    ("디자인", "디자인"),
    ("design", "design"),
    ("ui", "ui"),
    ("ux", "ux"),
    ("보안", "보안"),
    ("security", "security"),
    ("e2e", "e2e"),
    ("playwright", "playwright"),
)


def extract_plan_intents(text: str) -> list[str]:
    """Extract intent keywords from plan text, including Task headings and goals."""
    # Extract Task headings (e.g., "Task 0.2: SPEC_ui_office.md 초안")
    task_heading_re = re.compile(r'^####\s+Task\s+\d+\.\d+:\s*(.+)$', re.MULTILINE)
    # Extract Goal fields (e.g., "- **Goal**: ...")
    goal_field_re = re.compile(r'-\s*\*\*Goal\*\*:\s*([^|]+)', re.MULTILINE)

    # Combine all text sources
    all_text = text.lower()
    for heading_match in task_heading_re.finditer(text):
        all_text += " " + heading_match.group(1).lower()
    for goal_match in goal_field_re.finditer(text):
        all_text += " " + goal_match.group(1).lower()

    out: list[str] = []
    seen: set[str] = set()
    for needle, label in _INTENT_KEYWORDS:
        if needle in all_text and label not in seen:
            seen.add(label)
            out.append(label)
    return out
