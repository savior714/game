#!/usr/bin/env python3
"""
베스트 프랙티스 마크다운 지침 파일에서 Rule Definition Matrix 테이블을 파싱하는 모듈.
"""

from __future__ import annotations

import re
from pathlib import Path

MATRIX_HEADING = re.compile(
    r"^#{1,6}\s+.*rule\s+definition\s+matrix",
    re.IGNORECASE,
)
TABLE_ROW = re.compile(r"^\s*\|.+\|\s*$")
TABLE_SEPARATOR_CELL = re.compile(r"^[-:\s]+$")

HEADER_MAPPING: dict[str, list[str]] = {
    "rule_id": ["규칙 id", "규칙id", "rule id", "rule_id"],
    "glob": ["적용 경로", "적용경로", "glob", "pattern", "적용 경로 (glob)"],
    "precondition": ["준수 조건", "준수조건", "precondition"],
    "action": ["필수 액션", "필수액션", "action"],
    "pass_criteria": [
        "검증 로직",
        "검증로직",
        "pass criteria",
        "pass_criteria",
        "검증 로직 (pass criteria)",
    ],
}


def clean_cell(cell: str) -> str:
    """셀 텍스트의 공백 및 마크다운 장식(볼드·인라인 코드)을 제거한다."""
    val = cell.strip()
    # 인라인 코드는 glob(**/*) 등에 *가 포함되므로 먼저 보존 추출
    val = re.sub(r"`([^`]+)`", r"\1", val)
    # 셀 전체가 **...** 로 감싼 경우만 볼드 제거 (부분 ** 는 glob용으로 유지)
    if val.startswith("**") and val.endswith("**") and len(val) > 4:
        val = val[2:-2].strip()
    return val.strip()


def normalize_header(raw_name: str) -> str:
    normalized = raw_name.lower().strip()
    normalized = re.sub(r"[\*_`]", "", normalized)
    for key, aliases in HEADER_MAPPING.items():
        if normalized in aliases or any(alias in normalized for alias in aliases):
            return key
    return ""


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(TABLE_SEPARATOR_CELL.match(cell) for cell in cells)


def split_table_row(line: str) -> list[str]:
    return [clean_cell(part) for part in line.strip().split("|")[1:-1]]


def extract_matrix_section(file_content: str) -> str:
    """## Rule Definition Matrix 절 본문만 반환. 없으면 전체 본문."""
    lines = file_content.splitlines()
    start: int | None = None
    heading_level = 2

    for idx, line in enumerate(lines):
        if MATRIX_HEADING.match(line.strip()):
            start = idx + 1
            level_match = re.match(r"^(#+)", line.strip())
            if level_match:
                heading_level = len(level_match.group(1))
            break

    if start is None:
        return file_content

    section_lines: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            level_match = re.match(r"^(#+)", stripped)
            if level_match and len(level_match.group(1)) <= heading_level:
                break
        section_lines.append(line)

    return "\n".join(section_lines)


def parse_markdown_rules(file_content: str) -> list[dict]:
    """마크다운 본문에서 Rule Definition Matrix 테이블을 파싱하여 규칙 목록을 반환한다."""
    scoped = extract_matrix_section(file_content)
    rules: list[dict] = []
    lines = [line.rstrip() for line in scoped.splitlines()]

    in_table = False
    header_indices: dict[str, int] = {}

    for line in lines:
        stripped = line.strip()
        if not TABLE_ROW.match(stripped):
            in_table = False
            header_indices = {}
            continue

        cells = split_table_row(stripped)
        if not cells:
            continue

        if is_separator_row(cells):
            continue

        if not in_table:
            header_indices = {}
            for idx, header in enumerate(cells):
                key = normalize_header(header)
                if key:
                    header_indices[key] = idx
            if "rule_id" in header_indices and "pass_criteria" in header_indices:
                in_table = True
            continue

        rule_data: dict[str, str] = {}
        for key, idx in header_indices.items():
            rule_data[key] = cells[idx] if idx < len(cells) else ""

        rule_id = rule_data.get("rule_id", "").strip()
        if not rule_id or rule_id.startswith("<!--"):
            continue

        rule_data.setdefault("glob", "**/*")
        rules.append(rule_data)

    return rules


def parse_rules_from_file(file_path: Path | str) -> list[dict]:
    """파일 경로로부터 규칙 테이블을 파싱한다."""
    path = Path(file_path)
    if not path.is_file():
        msg = f"규칙 파일을 찾을 수 없습니다: {file_path}"
        raise FileNotFoundError(msg)

    content = path.read_text(encoding="utf-8")
    return parse_markdown_rules(content)


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        print(f"--- Parsing: {arg} ---")
        for rule in parse_rules_from_file(arg):
            print(rule)
