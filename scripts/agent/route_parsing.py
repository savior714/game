"""Parse CONTEXT_ROUTING markdown and project skill JSON."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

ROUTING_FILE = ".agents/registry/CONTEXT_ROUTING.md"
PROJECT_SKILL_ROUTING_FILE = ".agents/registry/PROJECT_SKILL_ROUTING.json"

_PROJECT_SKILL_PATH = re.compile(
    r"(\.agents/skills/[\w./-]+/SKILL\.md)",
    re.IGNORECASE,
)


def normalize_repo_rel(path: str) -> str:
    """Strip leading `./` only — preserve `.agents/` and other dot-prefixed segments."""
    rel = path.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def find_repo_root(start: Path | None = None) -> Path:
    """Directory that contains `.agents/registry/CONTEXT_ROUTING.md`."""
    here = (start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / ROUTING_FILE).is_file():
            return p
    return here


def expand_curly_braces(pattern: str) -> List[str]:
    """
    Expands curly braces in a glob pattern.
    Example: "**/*.{ts,tsx}" -> ["**/*.ts", "**/*.tsx"]
    """
    match = re.search(r"\{([^}]+)\}", pattern)
    if not match:
        return [pattern]

    prefix = pattern[: match.start()]
    suffix = pattern[match.end() :]
    options = match.group(1).split(",")

    results: List[str] = []
    for opt in options:
        results.extend(expand_curly_braces(prefix + opt.strip() + suffix))
    return results


def strip_pattern_annotation(pattern: str) -> str:
    """Remove trailing ` (note)` annotations from routing pattern cells."""
    s = pattern.strip()
    return re.sub(r"\s+\([^)]*\)\s*$", "", s).strip()


def extract_project_skill_paths(cell: str) -> List[str]:
    """`.agents/skills/.../SKILL.md` paths from a routing table cell."""
    return [m.group(1) for m in _PROJECT_SKILL_PATH.finditer(cell.replace("`", ""))]




def parse_context_routing_md(file_path: str = ROUTING_FILE) -> List[Tuple[str, str]]:
    """Parse CONTEXT_ROUTING path → domain rule column (column 2)."""
    path = Path(file_path)
    if not path.is_file():
        return []

    content = path.read_text(encoding="utf-8")
    mapping: List[Tuple[str, str]] = []

    table_row_pattern = re.compile(r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|")
    lines = content.splitlines()
    in_dynamic_mapping_section = False

    for line in lines:
        if "## 🗺️ 경로별 동적 매핑" in line:
            in_dynamic_mapping_section = True
            continue

        if in_dynamic_mapping_section:
            m = table_row_pattern.match(line.strip())
            if m:
                pattern_col = m.group(1).strip()
                rule_col = m.group(2).strip()

                if "파일 경로 패턴" in pattern_col or pattern_col.startswith(":---"):
                    continue

                parts = re.split(r",(?![^{]*\})", pattern_col)
                patterns = [strip_pattern_annotation(p).replace("`", "") for p in parts]
                rule = rule_col.replace("`", "").strip()

                for pattern in patterns:
                    if not pattern or pattern == "파일 경로 패턴 (Glob)":
                        continue
                    for expanded in expand_curly_braces(pattern):
                        mapping.append((expanded, rule))
            elif line.strip() == "" and mapping:
                break

    return mapping


def parse_context_routing_project_skill_globs(
    file_path: str = ROUTING_FILE,
) -> List[Tuple[str, List[str]]]:
    """CONTEXT_ROUTING rows whose rule column references project skills."""
    path = Path(file_path)
    if not path.is_file():
        return []

    content = path.read_text(encoding="utf-8")
    out: List[Tuple[str, List[str]]] = []
    table_row_pattern = re.compile(r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|")
    lines = content.splitlines()
    in_section = False

    for line in lines:
        if "## 🗺️ 경로별 동적 매핑" in line:
            in_section = True
            continue
        if in_section and line.startswith("## ") and "경로별" not in line:
            break
        if not in_section:
            continue
        m = table_row_pattern.match(line.strip())
        if not m:
            continue
        pattern_col, rule_col = m.group(1).strip(), m.group(2).strip()
        if "파일 경로 패턴" in pattern_col or pattern_col.startswith(":---"):
            continue
        skills = extract_project_skill_paths(rule_col)
        if not skills:
            continue
        pattern_col = pattern_col.split("—")[0].strip()
        parts = re.split(r",(?![^{]*\})", pattern_col)
        for raw in parts:
            raw = strip_pattern_annotation(raw).replace("`", "")
            if not raw:
                continue
            for expanded in expand_curly_braces(raw):
                out.append((expanded, skills))
    return out


def get_always_load_rules(file_path: str = ROUTING_FILE) -> List[str]:
    """Extracts rules from the 'Always Load' section in CONTEXT_ROUTING.md."""
    path = Path(file_path)
    if not path.is_file():
        return []

    content = path.read_text(encoding="utf-8")
    rules: List[str] = []
    lines = content.splitlines()
    in_section = False
    for line in lines:
        if "## 📌 상시 적용 규칙" in line:
            in_section = True
            continue
        if in_section:
            match = re.match(r"-\s*`([^`]+)`", line.strip())
            if match:
                rules.append(match.group(1))
            elif line.startswith("##"):
                break
    return rules


def load_project_skill_routing(repo_root: Path) -> Dict[str, object]:
    path = repo_root / PROJECT_SKILL_ROUTING_FILE
    if not path.is_file():
        return {"version": "0", "cap": 5, "priority": [], "path_routes": [], "intent_routes": []}
    return json.loads(path.read_text(encoding="utf-8"))
