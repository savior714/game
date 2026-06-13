from __future__ import annotations

import re

_MIN_GOAL_LENGTH = 15

_MIN_DONE_CONCLUSION_LENGTH = 25

PLAN_TASK_CLOSE_MARKER = "[closed-by:plan-task-close]"

_VAGUE_GOAL_WORDS = [
    "추가", "수정", "변경", "처리", "대응", "지원", "설정",
    "implement", "add", "update", "modify", "change", "handle",
]

_THIN_CONCLUSION_PATTERNS = [
    r"^\[PASS\]$",
    r"^\[FAIL\]$",
    r"^\[성공\]$",
    r"^\[실패\]$",
    r"^통과$",
    r"^완료$",
    r"^\[DONE\]$",
    r"^\[OK\]$",
]


def _lint_target_quality(task_idx: int, target: str) -> list[str]:
    """Check that Target is not empty."""
    issues: list[str] = []
    if not target:
        return issues
    return issues


def _lint_goal_quality(task_idx: int, goal: str) -> list[str]:
    """Goal must be specific and substantive, not a single verb."""
    issues: list[str] = []
    if not goal:
        return issues

    if len(goal) < _MIN_GOAL_LENGTH:
        issues.append(
            f"Task#{task_idx} Goal too short ({len(goal)} chars, min {_MIN_GOAL_LENGTH}) "
            f"'{goal}' — be specific about WHAT and WHERE"
        )

    cleaned = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", goal)
    words = cleaned.split()

    if len(words) <= 2:
        for word in words:
            if word.lower() in _VAGUE_GOAL_WORDS:
                issues.append(
                    f"Task#{task_idx} Goal '{goal}' is too vague "
                    f"(single verb '{word}') — specify entity, file, or domain"
                )
                break

    return issues


def _lint_conclusion_quality(
    task_idx: int,
    status: str,
    conclusion: str,
    *,
    require_closeout_marker: bool = True,
) -> list[str]:
    """Done task Conclusion must be substantive, not just a marker."""
    issues: list[str] = []
    if not conclusion or status != "done":
        return issues

    stripped = conclusion.strip()
    if (
        require_closeout_marker
        and stripped.startswith("[PASS]")
        and PLAN_TASK_CLOSE_MARKER not in stripped
    ):
        issues.append(
            f"Task#{task_idx} done Conclusion starting with [PASS] must include "
            f"{PLAN_TASK_CLOSE_MARKER} (use just plan-task-close)"
        )

    for pattern in _THIN_CONCLUSION_PATTERNS:
        if re.match(pattern, conclusion.strip()):
            issues.append(
                f"Task#{task_idx} Conclusion too thin — "
                f"'{conclusion[:40]}...' is not a meaningful summary."
            )
            break

    if len(conclusion.strip()) < _MIN_DONE_CONCLUSION_LENGTH:
        issues.append(
            f"Task#{task_idx} Conclusion too short ({len(conclusion.strip())} chars, "
            f"min {_MIN_DONE_CONCLUSION_LENGTH}) — include specific files/actions/verify results"
        )

    return issues


def _shell_chain_parts(text: str) -> list[str]:
    """Split one shell fragment on ; && || chain operators."""
    stripped = text
    bucket: list[str] = []

    def _mask(m: re.Match[str]) -> str:
        bucket.append(m.group(0))
        return f"\x00QSEG{len(bucket) - 1}\x00"

    stripped = re.sub(r"'[^']*'", _mask, stripped)
    stripped = re.sub(r'"[^"]*"', _mask, stripped)
    return [s.strip() for s in re.split(r";\s*|&&|\|\|", stripped) if s.strip()]


_RUNNER_TOKEN_PATTERNS: tuple[str, ...] = (
    r"uv run",
    r"npm run",
    r"bun run",
    r"pnpm(?:\s+exec)?",
    r"just",
    r"pytest",
    r"python3?",
    r"cd",
    r"rg",
    r"grep",
    r"test",
    r"wc",
    r"curl",
    r"bash",
)


def _verify_command_segments(verify: str) -> list[str]:
    """Split Verify into atomic shell segments."""
    segments: list[str] = []
    for match in re.finditer(r"`([^`]*)`", verify):
        inner = match.group(1)
        segments.extend(_shell_chain_parts(inner))
    if segments:
        return segments
    stripped = verify.strip()
    if not stripped:
        return []
    return _shell_chain_parts(stripped)


def _verify_segment_runner(segment: str) -> bool:
    """One invocation per segment."""
    if re.search(r"\buv run\b", segment, re.IGNORECASE):
        return True
    if re.match(
        r"^(cd|rg|grep|test|wc|curl|bash)\b",
        segment.strip(),
        re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(
            r"\b(just|pytest|pnpm(?:\s+exec)?|npm run|bun run|python3?)\b",
            segment,
            re.IGNORECASE,
        )
    )


def _lint_verify_quality(task_idx: int, verify: str) -> list[str]:
    """Verify must be an actual test/verification command, not a no-op."""
    issues: list[str] = []
    if not verify:
        return issues

    parts = _shell_chain_parts(verify.strip())
    if not parts:
        return issues

    noop_patterns = [
        r"^\s*echo\b",
        r"^\s*print\s*\(",
        r"^\s*printf\b",
        r"^\s*true\b",
        r"^\s*:\s*$",
    ]
    for part in parts:
        for pattern in noop_patterns:
            if re.match(pattern, part.strip(), re.IGNORECASE):
                issues.append(
                    f"Task#{task_idx} Verify is a no-op ('{part.strip()[:40]}') — "
                    "use actual test/verification command"
                )
                return issues

    if not any(_verify_segment_runner(part) for part in parts):
        issues.append(
            f"Task#{task_idx} Verify does not use a recognized runner "
            "(pytest, just, pnpm, uv, python3, etc.)"
        )

    return issues


def _validate_goal_atomicity_conjunctions(goal_text: str) -> list[str]:
    """Goal 원자성 검사 — 한국어 접속사 감지."""
    issues: list[str] = []
    if not goal_text:
        return issues

    forbidden_conjunctions = ["및", "그리고", "또한", "동시에"]

    for conj in forbidden_conjunctions:
        if re.search(rf"\s+{conj}\s+", goal_text):
            issues.append(
                f"Goal must be atomic. Found forbidden conjunction: '{conj}'"
            )

    return issues
