from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

COLLABORATION_SUBSECTIONS: tuple[tuple[str, str], ...] = (
    (r"^### 개요\s*$", "개요"),
    (r"^### staff·경영에서 바뀌는 점\s*$", "staff·경영에서 바뀌는 점"),
    (r"^### 끝났을 때 확인할 것\s*$", "끝났을 때 확인할 것"),
)

AGENT_COMPLETION_CONTRACT_RE = re.compile(
    r"^## Agent Completion Contract\s*$",
    re.MULTILINE,
)

EXECUTION_PLAN_HEADING_RE = re.compile(
    r"^## 🛠️ Step-by-Step Execution Plan\s*$",
    re.MULTILINE,
)

AGENT_SCOPE_BLOCKQUOTE_RE = re.compile(
    r"^>\s*\*\*에이전트 스코프\*\*",
    re.MULTILINE,
)


from scripts.plan_loop.plan_lint.shared import (
    LETTER_PREFIX_TASK_HEADING_RE,
    REQUIRED_SECTIONS,
    is_blueprint_markdown,
)


def _lint_task_heading_numeric_phase_task(content: str) -> list[str]:
    """Blueprint Task headings must be #### Task {phase}.{seq}: (digits only)."""
    if not is_blueprint_markdown(content):
        return []
    issues: list[str] = []
    for match in LETTER_PREFIX_TASK_HEADING_RE.finditer(content):
        issues.append(
            "Task heading must use numeric Phase.Task (#### Task 1.1:), "
            f"not letter prefix — found: {match.group(0).strip()}."
        )
    return issues


def _lint_collaboration_summary(content: str) -> list[str]:
    """Blueprint collaboration summary — plain Korean, no code/paths."""
    # Find collaboration summary block
    match = re.search(r"##\s*📋\s*업무\s*요약", content, re.MULTILINE)
    if not match:
        return []
    start = match.end()
    next_h2 = re.search(r"\n## [^#]", content[start:])
    end = start + next_h2.start() if next_h2 else len(content)
    block = content[start:end]

    issues: list[str] = []
    for pattern, name in COLLABORATION_SUBSECTIONS:
        if not re.search(pattern, block, re.MULTILINE):
            issues.append(f"업무 요약: missing subsection '### {name}'")
    if "`" in block:
        issues.append(
            "업무 요약: backtick/code in natural-language zone — "
            "use plain Korean; paths/commands belong below Context Pre-read Gate"
        )
    return issues


def _is_active_root_blueprint_path(path: Optional[Path]) -> bool:
    """True for docs/plans/PLAN_*.md at repo root plans dir (not archive/)."""
    if path is None:
        return False
    posix = path.as_posix()
    if "/archive/" in posix or "/plans/archive" in posix:
        return False
    if not path.name.startswith("PLAN_") or path.suffix != ".md":
        return False
    if path.parent.name != "plans":
        return False
    parts = path.resolve().parts
    try:
        docs_idx = parts.index("docs")
    except ValueError:
        return False
    return (
        docs_idx + 2 < len(parts)
        and parts[docs_idx + 1] == "plans"
        and len(parts) == docs_idx + 3
    )


def _lint_dod_checkbox_format(text: str, file_path: Optional[Path]) -> tuple[list[str], list[str]]:
    """DoD must use backtick command lists, not GitHub checkbox markers."""
    lines = text.splitlines()
    in_dod = False
    dod_lines: list[str] = []
    for line in lines:
        if re.match(r"^##\s*✅\s*Definition of Done\s*\(\s*DoD\s*\)", line):
            in_dod = True
            continue
        if in_dod and re.match(r"^##\s", line):
            break
        if in_dod:
            dod_lines.append(line)

    if not dod_lines:
        return [], []

    checkbox_re = re.compile(r"^\s*(?:\d+\.\s+|-\s+)\[[ xX]\]")
    if not any(checkbox_re.match(line) for line in dod_lines):
        return [], []

    message = (
        "DoD uses `[ ]`/`[x]` checkbox format — use backtick command list only"
    )
    if _is_active_root_blueprint_path(file_path):
        return [message], []
    return [], [message]


def _lint_active_root_blueprint_governance(
    content: str, file_path: Optional[Path]
) -> tuple[list[str], list[str]]:
    """Agent Completion Contract + Agent Scope for active root blueprints."""
    if not _is_active_root_blueprint_path(file_path):
        return ([], [])
    issues: list[str] = []
    warnings: list[str] = []
    contract_match = AGENT_COMPLETION_CONTRACT_RE.search(content)
    exec_match = EXECUTION_PLAN_HEADING_RE.search(content)
    if not contract_match:
        warnings.append(
            "Active root blueprint missing section: "
            "## Agent Completion Contract (before Execution Plan)"
        )
    elif exec_match and contract_match.start() > exec_match.start():
        warnings.append(
            "## Agent Completion Contract must appear before "
            "## 🛠️ Step-by-Step Execution Plan"
        )
    if exec_match:
        exec_start = exec_match.start()
        exec_block = content[exec_start:]
        first_task = re.search(r"^#### Task \d+\.\d+:", exec_block, re.MULTILINE)
        scope_region = (
            exec_block[: first_task.start()] if first_task else exec_block[:2000]
        )
        if not AGENT_SCOPE_BLOCKQUOTE_RE.search(scope_region):
            issues.append(
                "Execution Plan missing mandatory agent scope blockquote "
                "(> **에이전트 스코프**: Verify → Conclusion → done → plan-lint)"
            )
        elif not (
            re.search(r"Conclusion", scope_region)
            and re.search(r"plan-lint", scope_region)
        ):
            issues.append(
                "Agent scope blockquote must mention Conclusion and plan-lint"
            )
    return issues, warnings


def verify_structural_sequence(content: str) -> list[str]:
    issues = []
    last_pos = -1
    for pattern, name in REQUIRED_SECTIONS:
        match = re.search(f"^{pattern}", content, re.MULTILINE)
        if not match:
            if name == "Conclusion":
                match = re.search(r"^##\s+🔁", content, re.MULTILINE)
            if not match:
                issues.append(f"Missing mandatory section: {name}")
                continue
        if match.start() < last_pos:
            issues.append(f"Incorrect section order: '{name}' should appear after previous sections")
        else:
            last_pos = match.start()
    return issues
