"""Content regression for Korean questions about words with a final consonant."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = REPO_ROOT / "domains" / "korean" / "data" / "words.json"
GENERAL_BATCHIM_PROMPT = "받침이 있는 단어를 고르세요."


def _has_batchim(word: str) -> bool:
    return any(
        0xAC00 <= ord(character) <= 0xD7A3 and (ord(character) - 0xAC00) % 28 != 0
        for character in word
    )


def test_general_batchim_question_has_exactly_one_valid_choice() -> None:
    catalog = json.loads(WORDS_PATH.read_text(encoding="utf-8"))
    questions = [
        question
        for question in catalog["spelling"]
        if question[0] == GENERAL_BATCHIM_PROMPT
    ]

    assert questions, "general batchim question must exist"

    for prompt, answer, choices, _grade, _skill in questions:
        matching_choices = [choice for choice in choices if _has_batchim(choice)]
        assert matching_choices == [answer], (
            f"{prompt!r} must have exactly one batchim choice matching {answer!r}; "
            f"got {matching_choices!r}"
        )
