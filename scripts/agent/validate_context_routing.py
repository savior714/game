#!/usr/bin/env python3
"""Validate CONTEXT_ROUTING + PROJECT_SKILL_ROUTING for drift.

Checks:
  1. CONTEXT_ROUTING.md table rows → referenced files exist on disk.
  2. PROJECT_SKILL_ROUTING.json → glob patterns are valid fnmatch,
     referenced .SKILL.md files exist.
  3. JSON schema version/cap/priority/path_routes/intent_routes present.

Exit 0 = all clean, Exit 1 = drift found (printed to stdout).

Usage:
    uv run python scripts/agent/validate_context_routing.py
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

ROUTING_FILE = ".agents/registry/CONTEXT_ROUTING.md"
PROJECT_SKILL_ROUTING_FILE = ".agents/registry/PROJECT_SKILL_ROUTING.json"
SKILL_CATALOG_FILE = ".agents/registry/SKILL_CATALOG.json"

REPO_ROOT = Path(__file__).resolve().parents[2]


def validate_context_routing() -> list[str]:
    """Check CONTEXT_ROUTING.md referenced files exist."""
    issues: list[str] = []
    path = REPO_ROOT / ROUTING_FILE
    if not path.is_file():
        issues.append(f"CONTEXT_ROUTING.md missing at {path}")
        return issues

    content = path.read_text(encoding="utf-8")

    # Parse rule column entries from dynamic mapping section
    table_row_pat = re.compile(
        r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", re.MULTILINE
    )
    lines = content.splitlines()
    in_section = False
    rule_tokens: list[str] = []

    for line in lines:
        if "## 🗺️ 경로별 동적 매핑" in line:
            in_section = True
            continue
        if in_section and line.startswith("## ") and "경로별" not in line:
            break
        if not in_section:
            continue
        m = table_row_pat.match(line.strip())
        if not m:
            continue
        rule_col = m.group(2).strip().replace("`", "")
        # Collect rule tokens (comma-separated, may include globs)
        for token in re.split(r",(?![^{]*\})", rule_col):
            token = token.strip()
            if token and "파일 경로 패턴" not in token:
                rule_tokens.append(token)

    # Check each rule token resolves to a file
    for raw in rule_tokens:
        # Strip Korean annotations (e.g., "→ 본문이 지시하는 vendored 하위 스킬 Read")
        rel = raw.split("—")[0].strip()
        # Skip non-file tokens (e.g., "→ ...")
        if not re.search(r"\.md$|\.json$", rel):
            continue
        # Handle glob patterns like "adaptive/*.md"
        if "*" in rel:
            # Expand glob to check directory exists
            # Strip trailing /*.md or /**/*.md to get the base dir
            glob_base = rel
            for suffix in ("/**/*.md", "/*.md", "/**/*"):
                if glob_base.endswith(suffix):
                    glob_base = glob_base[: -len(suffix)]
                    break
            search_dir = REPO_ROOT / glob_base if glob_base else REPO_ROOT
            if not search_dir.is_dir():
                issues.append(f"CONTEXT_ROUTING glob dir missing: {search_dir}")
            continue
        # Plain file path — resolve relative to .agents/domains/ or keep as-is
        if rel.startswith(".agents/"):
            full = REPO_ROOT / rel
        elif "/" in rel:
            # Domain rules like "documentation/markdown.md" → ".agents/domains/documentation/markdown.md"
            full = REPO_ROOT / ".agents" / "domains" / rel
        else:
            # Single file like "markdown.md" → ".agents/core/markdown.md" or ".agents/domains/..."
            full = REPO_ROOT / ".agents" / "core" / rel
        if not full.is_file():
            issues.append(f"CONTEXT_ROUTING references missing file: {rel} (checked {full})")

    return issues


def validate_project_skill_routing() -> list[str]:
    """Check PROJECT_SKILL_ROUTING.json schema + referenced files."""
    issues: list[str] = []
    path = REPO_ROOT / PROJECT_SKILL_ROUTING_FILE
    if not path.is_file():
        issues.append(f"PROJECT_SKILL_ROUTING.json missing at {path}")
        return issues

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        issues.append(f"PROJECT_SKILL_ROUTING.json invalid JSON: {e}")
        return issues

    # Schema checks
    for key in ("version", "cap", "priority", "path_routes", "intent_routes"):
        if key not in data:
            issues.append(f"PROJECT_SKILL_ROUTING.json missing key: {key}")

    # Check priority entries exist
    for skill_path in data.get("priority", []):
        full = REPO_ROOT / skill_path
        if not full.is_file():
            issues.append(f"PROJECT_SKILL_ROUTING priority missing: {skill_path}")

    # Check path_routes globs and skills
    for route in data.get("path_routes", []):
        route_id = route.get("id", "?")
        globs = route.get("globs", [])
        skills = route.get("skills", [])

        # Validate globs are valid fnmatch patterns
        for glob_pat in globs:
            try:
                fnmatch.fnmatch("test/path.ext", glob_pat)
            except Exception as e:
                issues.append(
                    f"PROJECT_SKILL_ROUTING[{route_id}] invalid glob '{glob_pat}': {e}"
                )

        # Validate skill paths exist
        for skill_path in skills:
            full = REPO_ROOT / skill_path
            if not full.is_file():
                issues.append(
                    f"PROJECT_SKILL_ROUTING[{route_id}] missing skill: {skill_path}"
                )

    # Check intent_routes
    for route in data.get("intent_routes", []):
        route_id = route.get("id", "?")
        if "match_any" not in route:
            issues.append(f"PROJECT_SKILL_ROUTING intent[{route_id}] missing match_any")
        if "skills" not in route:
            issues.append(f"PROJECT_SKILL_ROUTING intent[{route_id}] missing skills")

    return issues


def validate_skill_catalog() -> list[str]:
    """Check SKILL_CATALOG.json project skill paths exist."""
    issues: list[str] = []
    path = REPO_ROOT / SKILL_CATALOG_FILE
    if not path.is_file():
        issues.append(f"SKILL_CATALOG.json missing at {path}")
        return issues
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data.get("project_skills", []):
        skill_path = entry.get("path", "")
        if not skill_path:
            issues.append(f"SKILL_CATALOG entry missing path: {entry!r}")
            continue
        full = REPO_ROOT / skill_path
        if not full.is_file():
            issues.append(f"SKILL_CATALOG missing skill: {skill_path}")
    return issues


def main() -> int:
    all_issues: list[str] = []

    print("🔍 Validating CONTEXT_ROUTING.md...")
    ctx_issues = validate_context_routing()
    all_issues.extend(ctx_issues)
    if ctx_issues:
        for issue in ctx_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ CONTEXT_ROUTING.md OK")

    print("🔍 Validating PROJECT_SKILL_ROUTING.json...")
    psr_issues = validate_project_skill_routing()
    all_issues.extend(psr_issues)
    if psr_issues:
        for issue in psr_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ PROJECT_SKILL_ROUTING.json OK")

    print("🔍 Validating SKILL_CATALOG.json...")
    catalog_issues = validate_skill_catalog()
    all_issues.extend(catalog_issues)
    if catalog_issues:
        for issue in catalog_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ SKILL_CATALOG.json OK")

    if all_issues:
        print(f"\n❌ {len(all_issues)} drift(s) found")
        return 1

    print("\n✅ All routing maps valid — no drift detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
