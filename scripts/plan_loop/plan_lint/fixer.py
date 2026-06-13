"""Mechanical auto-fix for plan markdown contract issues."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from scripts.plan_loop.plan_lint.shared import (
    ATOMIC_UNIT_TAG,
    BLUEPRINT_REQUIRED_DOC_META_FIELDS,
    CANONICAL_TODO_CONCLUSION_SLOTS,
    DEPRECATED_LEVEL_LOW_TAG,
    REQUIRED_SECTION_HEADINGS,
    REQUIRED_SECTIONS,
    _parse_fields,
    _split_task_blocks,
)


def fix_plan_text(text: str, file_path: Optional[Path] = None) -> tuple[str, list[str]]:
    """Apply mechanical fixes and return (fixed_text, list_of_applied_fixes)."""
    fixes: list[str] = []
    result = text

    # 1. Doc meta defaults
    result, fix_meta = _fix_doc_meta_defaults(result, file_path)
    fixes.extend(fix_meta)

    # 2. Missing sections
    result, fix_sections = _fix_missing_sections(result)
    fixes.extend(fix_sections)

    # 3. CSF slot insertion
    result, fix_csf = _fix_empty_conclusion_slots(result)
    fixes.extend(fix_csf)

    # 4. Deprecated tag replacement
    result, fix_tags = _fix_deprecated_tags(result)
    fixes.extend(fix_tags)

    return result, fixes


def _fix_doc_meta_defaults(text: str, file_path: Optional[Path]) -> tuple[str, list[str]]:
    """Fill empty required blueprint doc meta fields with defaults."""
    fixes: list[str] = []

    if not re.search(r"^# 🗺️ Project Blueprint:", text, re.MULTILINE):
        return text, fixes

    meta_heading_match = re.search(
        r"(^## 문서 메타\s*\n)",
        text,
        re.MULTILINE,
    )
    if not meta_heading_match:
        return text, fixes

    after_heading = text[meta_heading_match.end():]
    next_section = re.search(r"^(?:## |#### Task)", after_heading, re.MULTILINE)
    if next_section is None:
        meta_end = len(text)
    else:
        meta_end = meta_heading_match.end() + next_section.start()
    meta_block = text[meta_heading_match.start() : meta_end]

    existing_fields: dict[str, str] = {}
    for line in meta_block.split("\n"):
        m = re.match(r"^\s*- \*\*([^*]+)\*\*:\s*(.+)$", line)
        if m:
            existing_fields[m.group(1).strip()] = m.group(2).strip()

    defaults = {
        "SSOT Check": "N/A",
        "Architectural Goal": "Blueprint",
        "Priority": "2",
    }

    new_field_lines: list[str] = []
    for field_name in BLUEPRINT_REQUIRED_DOC_META_FIELDS:
        existing_val = existing_fields.get(field_name, "").strip()
        if existing_val:
            new_field_lines.append(f"- **{field_name}**: {existing_val}")
        elif field_name in defaults:
            new_field_lines.append(f"- **{field_name}**: {defaults[field_name]}")
            fixes.append(f"Meta: filled empty/missing field '{field_name}' with '{defaults[field_name]}'")

    custom_lines: list[str] = []
    for line in meta_block.split("\n"):
        m = re.match(r"^\s*- \*\*([^*]+)\*\*:\s*(.+)$", line)
        if m and m.group(1).strip() not in BLUEPRINT_REQUIRED_DOC_META_FIELDS:
            custom_lines.append(line)

    new_meta_block = "## 문서 메타\n" + "\n".join(new_field_lines)
    if custom_lines:
        new_meta_block += "\n" + "\n".join(custom_lines)
    new_meta_block += "\n"

    text = text[: meta_heading_match.start()] + new_meta_block + text[meta_end:]
    return text, fixes


def _fix_missing_sections(text: str) -> tuple[str, list[str]]:
    """Insert missing REQUIRED_SECTIONS using canonical headings."""
    fixes: list[str] = []

    for idx, (pattern, name) in enumerate(REQUIRED_SECTIONS):
        if re.search(pattern, text, re.MULTILINE):
            continue

        heading_line = REQUIRED_SECTION_HEADINGS[idx]
        stub = f"\n{heading_line}\n\n[미완성]\n"

        insert_pos = len(text)
        for later_idx in range(idx + 1, len(REQUIRED_SECTIONS)):
            later_match = re.search(
                REQUIRED_SECTIONS[later_idx][0], text, re.MULTILINE
            )
            if later_match:
                insert_pos = later_match.start()
                break
        else:
            for earlier_idx in range(idx - 1, -1, -1):
                earlier_match = re.search(
                    REQUIRED_SECTIONS[earlier_idx][0], text, re.MULTILINE
                )
                if earlier_match:
                    insert_pos = earlier_match.end()
                    break

        text = text[:insert_pos] + stub + text[insert_pos:]
        fixes.append(f"Section: inserted missing '{name}' section")

    return text, fixes


def _fix_empty_conclusion_slots(text: str) -> tuple[str, list[str]]:
    """Fill empty Conclusion fields on todo/running tasks with canonical CSF slot."""
    fixes: list[str] = []

    task_blocks = _split_task_blocks(text)
    if not task_blocks:
        return text, fixes

    for block in task_blocks:
        fields = _parse_fields(block)
        status = fields.get("Status", "todo")

        if status not in ("todo", "running"):
            continue

        conclusion = fields.get("Conclusion", "").strip()
        if conclusion:
            continue

        conclusion_match = re.search(
            r"^(- (?:\*\*Conclusion\*\*|Conclusion):)\s*$",
            block,
            re.MULTILINE,
        )
        if conclusion_match:
            old_line = f"{conclusion_match.group(1)} "
            new_line = f"{conclusion_match.group(1)} {CANONICAL_TODO_CONCLUSION_SLOTS[0]}"
            text = text.replace(old_line, new_line, 1)
            fixes.append(
                f"Conclusion: filled empty CSF slot on {status} task "
                f"with '{CANONICAL_TODO_CONCLUSION_SLOTS[0]}'"
            )

    return text, fixes


def _fix_deprecated_tags(text: str) -> tuple[str, list[str]]:
    """Replace deprecated [Level: Low] with [Unit: Atomic]."""
    fixes: list[str] = []

    if DEPRECATED_LEVEL_LOW_TAG in text:
        count = text.count(DEPRECATED_LEVEL_LOW_TAG)
        text = text.replace(DEPRECATED_LEVEL_LOW_TAG, ATOMIC_UNIT_TAG)
        fixes.append(
            f"Tag: replaced {count} occurrence(s) of deprecated '{DEPRECATED_LEVEL_LOW_TAG}' "
            f"with '{ATOMIC_UNIT_TAG}'"
        )

    return text, fixes


def apply_fix_to_file(file_path: Path) -> tuple[str, list[str]]:
    """Read file, apply fixes, atomically replace on disk, return (new_content, fixes)."""
    original = file_path.read_text(encoding="utf-8")
    fixed, fixes = fix_plan_text(original, file_path)

    if fixes:
        tmp_path = file_path.parent / f".{file_path.name}.fix.tmp"
        tmp_path.write_text(fixed, encoding="utf-8")
        tmp_path.replace(file_path)

    return fixed, fixes
