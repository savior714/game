from __future__ import annotations

import re

from scripts.plan_loop.plan_lint.shared import (
    BAD_PATTERNS,
    CANONICAL_TODO_CONCLUSION_SLOTS,
    CJK_CHAR_RE,
    CONCLUSION_ALLOWED_MARKERS,
    KOREAN_CHAR_RE,
    LANG_KO_RE,
    TASK_ID_PATTERN,
    _is_unfilled_csf_hint,
    _is_valid_open_conclusion,
    _looks_like_premature_measured_conclusion,
    CONCLUSION_FIELD_LINE_RE,
    EXTRA_TASK_CONCLUSION_HEADING_RE,
)

UPPERCASE_BRACKET_PLACEHOLDER_RE = re.compile(r"^\[[A-Z][A-Z0-9_\s-]*\]$")
BRACKET_ONLY_VALUE_RE = re.compile(r"^\[[^\]]+\]$")


def _is_bracket_slot_placeholder(normalized: str) -> bool:
    """Bracket-only template values excluding Task-ID patterns."""
    if not BRACKET_ONLY_VALUE_RE.fullmatch(normalized):
        return False
    if TASK_ID_PATTERN.match(normalized):
        return False
    if UPPERCASE_BRACKET_PLACEHOLDER_RE.fullmatch(normalized):
        return True
    if normalized in CANONICAL_TODO_CONCLUSION_SLOTS or _is_unfilled_csf_hint(normalized):
        return True
    inner = normalized[1:-1]
    if len(inner) >= 25:
        return False
    return bool(KOREAN_CHAR_RE.search(inner))


def _check_korean_first(text: str) -> list[str]:
    """Korean-first check for files with Language: ko marker."""
    if not LANG_KO_RE.search(text):
        return []
    matches = CJK_CHAR_RE.findall(text)
    if not matches:
        return []
    unique = sorted(set(matches))
    return [f"한자 혼용 감지 ({', '.join(unique)}) — `<!-- Language: ko -->` 파일은 한국어 사용"]


def _is_placeholder_value(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return True

    if normalized in ("...", "…"):
        return True

    if TASK_ID_PATTERN.match(normalized):
        return False

    for pattern in BAD_PATTERNS:
        if re.search(pattern, normalized):
            return True

    return _is_bracket_slot_placeholder(normalized)


def _is_conclusion_placeholder(value: str) -> bool:
    """Conclusion 전용 placeholder 체크 — 결과 마커 허용."""
    normalized = value.strip()
    if not normalized:
        return True

    for marker in CONCLUSION_ALLOWED_MARKERS:
        if normalized.startswith(marker):
            return False

    for pattern in BAD_PATTERNS:
        if re.search(pattern, normalized):
            return True

    return _is_bracket_slot_placeholder(normalized)


def _lint_open_task_conclusion(task_idx: int, status: str, value: str) -> list[str]:
    """todo/running must keep CSF slot."""
    issues: list[str] = []
    if status not in ("todo", "running"):
        return issues
    if _looks_like_premature_measured_conclusion(value):
        issues.append(
            f"Task#{task_idx} Status={status!r} but Conclusion reads like post-Verify "
            "measured text; use CSF slot "
            "'[판정 — 비개발자용 요약. 검증 결과]' until Verify PASS, then Status: done"
        )
        return issues
    if not _is_valid_open_conclusion(value):
        issues.append(
            f"Task#{task_idx} Status={status!r}: Conclusion must be a CSF slot hint "
            "(e.g. '[판정 — 비개발자용 요약. 검증 결과]'), not narrative or predicted results"
        )
    return issues


def _lint_task_conclusion_slot(task_idx: int, block: str) -> list[str]:
    """FAIL if a blueprint task has duplicate Conclusion fields or extra headings."""
    issues: list[str] = []
    conclusion_lines = len(CONCLUSION_FIELD_LINE_RE.findall(block))
    if conclusion_lines > 1:
        issues.append(
            f"Task#{task_idx} has {conclusion_lines} Conclusion field lines — "
            "keep exactly one '- **Conclusion**:' and replace it in-place"
        )
    extra_headings = EXTRA_TASK_CONCLUSION_HEADING_RE.findall(block)
    if extra_headings:
        issues.append(
            f"Task#{task_idx} contains Conclusion heading inside the task block "
            f"({extra_headings[0]!r}) — use only a single '- **Conclusion**:' line"
        )
    return issues


def _lint_task_preread_block(task_idx: int, block: str) -> list[str]:
    """Task-level Pre-read check — optional for AidenGame."""
    return []


def _lint_preread_gate(content: str) -> list[str]:
    """Context Pre-read Gate — optional for AidenGame."""
    return []


def _extract_target_paths(target: str) -> list[str]:
    """Extract discrete repo paths from Target."""
    def _split_chunk(chunk: str) -> list[str]:
        return [p.strip() for p in re.split(r"[,·]|\s+", chunk) if p.strip()]

    backticks = re.findall(r"`([^`]+)`", target)
    if backticks:
        paths: list[str] = []
        for inner in backticks:
            paths.extend(_split_chunk(inner))
        return paths
    return [p.strip() for p in re.split(r"[,·]", target) if p.strip()]


def _atomic_unit_contract_issues(task_idx: int, fields: dict[str, str]) -> list[str]:
    """Hard FAIL: violates single-Verify atomic ticket."""
    issues: list[str] = []
    verify = (fields.get("Verify") or "").strip()
    if not verify:
        return issues

    # Skip chain check for python3 -c commands (semicolons inside are JS/Python, not shell chains)
    if verify.strip().startswith("`python3"):
        pass  # Allow python3 -c commands as single verify
    else:
        # Check Verify is not chained with ; && ||
        parts = [p for p in re.split(r";\s*|&&|\|\|", verify) if p.strip()]
        if len(parts) >= 2:
            issues.append(
                f"Task#{task_idx} Verify must be one shell command (found {len(parts)} segments "
                "from ;, &&, ||) — split into separate [Unit: Atomic] tasks"
            )

    goal = (fields.get("Goal") or "").strip()
    issues.extend(_validate_goal_atomicity_conjunctions(goal))

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


def _atomic_unit_size_warnings(task_idx: int, fields: dict[str, str]) -> list[str]:
    """WARN-only heuristics."""
    warnings: list[str] = []
    target = (fields.get("Target") or "").strip()

    if target:
        if re.search(
            r"\.\.\.|…|\b(multiple|several|various)\b|"
            r"\bTBD\b|\btbd\b|전체|모든\s|일괄",
            target,
            re.IGNORECASE,
        ):
            warnings.append(
                f"Task#{task_idx} Target looks vague — list concrete file path(s)"
            )

    return warnings


ROLLUP_SUMMARY_SECTION_RE = re.compile(
    r"^##\s*🔁\s*Conclusion\s*&\s*Summary\s*$",
    re.MULTILINE,
)

ROLLUP_PLACEHOLDER_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\(Roll-up:", re.IGNORECASE),
    re.compile(r"완료\s*후\s*기입"),
    re.compile(r"완료\s*후\s*갱신"),
    re.compile(r"\(Task\s+완료\s*후"),
    re.compile(r"closeout\s*후\s*기입", re.IGNORECASE),
    re.compile(r"^\[Roll-up\s*—", re.IGNORECASE),
    re.compile(r"^\-\s*\*\*Roll-up\*\*:\s*…\s*$"),
    re.compile(r"^\-\s*\*\*Roll-up\*\*:\s*\.\.\.\s*$"),
    re.compile(r"^\[완료\s*시\s*기입\]"),
)

_MIN_ROLLUP_SUMMARY_LENGTH = 25


def extract_rollup_summary_body(text: str) -> str | None:
    """Return non-heading body under ## Conclusion & Summary, or None if missing."""
    match = ROLLUP_SUMMARY_SECTION_RE.search(text)
    if not match:
        return None
    start = match.end()
    next_section = re.search(r"\n## ", text[start:])
    end = start + next_section.start() if next_section else len(text)
    return text[start:end].strip()


def is_rollup_summary_placeholder(body: str) -> bool:
    """True when Roll-up section is empty or still a template hint."""
    normalized = body.strip()
    if not normalized:
        return True
    if len(normalized) < _MIN_ROLLUP_SUMMARY_LENGTH:
        return True
    for line in normalized.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in ROLLUP_PLACEHOLDER_LINE_PATTERNS:
            if pattern.search(stripped):
                return True
        for bad in BAD_PATTERNS:
            if re.search(bad, stripped):
                return True
        if stripped in CANONICAL_TODO_CONCLUSION_SLOTS:
            return True
    return False


def _closeout_task_is_done(text: str) -> bool:
    """True when a Blueprint closeout task (Roll-up Goal + plan-close Verify) is done."""
    from scripts.plan_loop.plan_lint.shared import _parse_fields, _split_task_blocks

    for block in _split_task_blocks(text):
        fields = _parse_fields(block)
        goal = (fields.get("Goal") or "").lower()
        verify = (fields.get("Verify") or "").lower()
        status = (fields.get("Status") or "").lower()
        if "roll-up" in goal and "plan-close" in verify and status == "done":
            return True
    return False


def _lint_rollup_summary_section(text: str) -> list[str]:
    """FAIL when closeout Task is done but document Roll-up is still a placeholder."""
    if not ROLLUP_SUMMARY_SECTION_RE.search(text):
        return []
    body = extract_rollup_summary_body(text) or ""
    if not _closeout_task_is_done(text):
        return []
    if is_rollup_summary_placeholder(body):
        return [
            "Conclusion & Summary Roll-up is still a placeholder — "
            "write a measured 1-paragraph summary under "
            "'## 🔁 Conclusion & Summary' before closing the closeout Task"
        ]
    return []


def check_rollup_summary_for_close(text: str) -> list[str]:
    """plan-close gate: Roll-up section must be filled before plan completion."""
    body = extract_rollup_summary_body(text)
    if body is None:
        return ["missing section: ## 🔁 Conclusion & Summary"]
    if is_rollup_summary_placeholder(body):
        preview = body.splitlines()[0][:80] if body else "(empty)"
        return [
            "Conclusion & Summary Roll-up is still a placeholder — "
            f"current: {preview!r}. "
            "Write a measured 1-paragraph summary before running plan-close."
        ]
    return []
