from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from scripts.plan_loop.plan_lint.shared import (
    ALLOWED_RETRY,
    ALLOWED_STATUS,
    ATOMIC_UNIT_TAG,
    BLUEPRINT_REQUIRED_DOC_META_FIELDS,
    BLUEPRINT_REQUIRED_FIELDS,
    DEPRECATED_LEVEL_LOW_TAG,
    EXECUTOR_REQUIRED_FIELDS,
    FORBIDDEN_LEVEL_TAG_RE,
    KOREAN_CHAR_RE,
    _extract_doc_meta_fields,
    _is_blueprint_task,
    _is_unfilled_csf_hint,
    _parse_fields,
    _split_task_blocks,
    _task_unit_tag,
    extract_blueprint_title,
    is_blueprint_markdown,
)
from scripts.plan_loop.plan_lint.structural import (
    _lint_active_root_blueprint_governance,
    _lint_collaboration_summary,
    _lint_dod_checkbox_format,
    _lint_task_heading_numeric_phase_task,
    verify_structural_sequence,
)
from scripts.plan_loop.plan_lint.quality import (
    _lint_conclusion_quality,
    _lint_goal_quality,
    _lint_target_quality,
    _lint_verify_quality,
)
from scripts.plan_loop.plan_lint.verification import (
    _atomic_unit_contract_issues,
    _atomic_unit_size_warnings,
    _check_korean_first,
    _is_conclusion_placeholder,
    _is_placeholder_value,
    _lint_open_task_conclusion,
    _lint_preread_gate,
    _lint_rollup_summary_section,
    _lint_task_conclusion_slot,
    _lint_task_preread_block,
)


def _lint_blueprint_doc_meta_fields(text: str) -> list[str]:
    issues: list[str] = []
    doc_fields = _extract_doc_meta_fields(text)

    for required_meta in BLUEPRINT_REQUIRED_DOC_META_FIELDS:
        value = doc_fields.get(required_meta, "")
        if not value.strip():
            issues.append(
                f"Blueprint doc meta missing/empty required field: {required_meta}"
            )
    return issues


def lint_plan_text(text: str, file_path: Optional[Path] = None, is_archive_ready: bool = False) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    is_blueprint_doc = is_blueprint_markdown(text)

    # Structural checks
    if is_blueprint_doc:
        issues.extend(verify_structural_sequence(text))
        issues.extend(_lint_collaboration_summary(text))
        issues.extend(_lint_rollup_summary_section(text))
        issues.extend(_lint_task_heading_numeric_phase_task(text))
        issues.extend(_lint_preread_gate(text))
        governance_issues, governance_warnings = _lint_active_root_blueprint_governance(
            text, file_path
        )
        issues.extend(governance_issues)
        warnings.extend(governance_warnings)
        dod_issues, dod_warnings = _lint_dod_checkbox_format(text, file_path)
        issues.extend(dod_issues)
        warnings.extend(dod_warnings)

        title = extract_blueprint_title(text)
        if title and not KOREAN_CHAR_RE.search(title):
            issues.append(
                f"Blueprint title must contain Korean characters: '{title}'"
            )

    # Korean-first body check
    issues.extend(_check_korean_first(text))

    if is_archive_ready:
        if not re.search(r"관련 명세|docs/specs/", text, re.IGNORECASE):
            issues.append(
                "[Archive-Ready] Blueprint must contain a reference to related specs."
            )

    task_blocks = _split_task_blocks(text)
    if not task_blocks:
        no_tasks_msg = (
            "no task blocks found (expected '#### Task X.Y: ...')"
            if is_blueprint_doc
            else "no task blocks found (expected '#### Task: ...')"
        )
        if is_blueprint_doc:
            issues.append(no_tasks_msg)
            issues.extend(_lint_blueprint_doc_meta_fields(text))
            return (issues, warnings)
        issues.append(no_tasks_msg)
        return (issues, warnings)

    seen_ids: set[str] = set()
    for idx, block in enumerate(task_blocks, start=1):
        fields = _parse_fields(block)
        is_blueprint = _is_blueprint_task(block, fields)
        required = BLUEPRINT_REQUIRED_FIELDS if is_blueprint else EXECUTOR_REQUIRED_FIELDS
        if is_blueprint and not is_blueprint_doc:
            required = tuple(f for f in required if f != "Pre-read")

        missing = [field for field in required if not fields.get(field)]
        if missing:
            issues.append(f"Task#{idx} missing required fields: {', '.join(missing)}")

        if is_blueprint and not missing:
            if FORBIDDEN_LEVEL_TAG_RE.search(block):
                issues.append(
                    f"Task#{idx} forbidden level tag Medium/High — "
                    f"split into smaller tasks with '{ATOMIC_UNIT_TAG}' only"
                )
                continue
            unit_tag = _task_unit_tag(block)
            if not unit_tag:
                issues.append(
                    f"Task#{idx} missing required unit tag '{ATOMIC_UNIT_TAG}'"
                )
                continue

            warnings.extend(_atomic_unit_size_warnings(idx, fields))
            if is_blueprint_doc:
                issues.extend(_lint_task_preread_block(idx, block))
            issues.extend(_lint_task_conclusion_slot(idx, block))

            task_status = fields.get("Status", "todo")
            issues.extend(_lint_target_quality(idx, fields.get("Target", "")))
            issues.extend(_lint_goal_quality(idx, fields.get("Goal", "")))
            issues.extend(_lint_verify_quality(idx, fields.get("Verify", "")))
            issues.extend(_lint_conclusion_quality(idx, task_status, fields.get("Conclusion", "")))
            issues.extend(_atomic_unit_contract_issues(idx, fields))

        status = fields.get("Status", "todo")

        if is_archive_ready and status != "done":
            issues.append(f"[Archive-Ready] Task#{idx} is not marked as 'done' (current status: '{status}').")

        # Placeholder check
        for field, value in fields.items():
            if field == "Conclusion" and status in ("todo", "running"):
                issues.extend(_lint_open_task_conclusion(idx, status, value))
                continue
            if field == "Conclusion" and status == "done" and _is_unfilled_csf_hint(value):
                issues.append(
                    f"Task#{idx} field 'Conclusion' still has CSF hint; replace with measured summary before done: {value}"
                )
                continue

            if field == "Conclusion":
                if _is_conclusion_placeholder(value):
                    issues.append(f"Task#{idx} field '{field}' contains placeholder value: {value}")
            else:
                if _is_placeholder_value(value):
                    issues.append(f"Task#{idx} field '{field}' contains placeholder value: {value}")

        task_id = fields.get("Task-ID", "").strip()
        if task_id:
            if task_id in seen_ids:
                issues.append(f"Task#{idx} duplicate Task-ID: {task_id}")
            else:
                seen_ids.add(task_id)

        status_value = fields.get("Status", "").strip()
        if status_value and status_value not in ALLOWED_STATUS:
            issues.append(
                f"Task#{idx} invalid Status '{status_value}' (allowed: {', '.join(sorted(ALLOWED_STATUS))})"
            )

        retry_policy = fields.get("RetryPolicy", "").strip()
        if retry_policy and retry_policy not in ALLOWED_RETRY:
            issues.append(
                f"Task#{idx} invalid RetryPolicy '{retry_policy}' (allowed: {', '.join(sorted(ALLOWED_RETRY))})"
            )

    if is_blueprint_doc:
        issues.extend(_lint_blueprint_doc_meta_fields(text))

    return issues, warnings


def lint_plan_file(path: Path, is_archive_ready: bool = False) -> tuple[list[str], list[str]]:
    return lint_plan_text(path.read_text(encoding="utf-8"), file_path=path, is_archive_ready=is_archive_ready)
