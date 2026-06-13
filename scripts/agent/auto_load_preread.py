#!/usr/bin/env python3
"""
Auto-load Pre-read skills before implementation.

Scans the plan for Task Pre-read blocks and automatically loads all
must_read skills before starting implementation.

Usage:
    python3 scripts/agent/auto_load_preread.py docs/plans/PLAN_x.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Dict, Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# Pre-read marker pattern
TASK_PREREAD_MARKER = "plan-task-preread:v1"
TASK_PREREAD_BLOCK_RE = re.compile(
    r"^(- \*\*Pre-read\*\*:.*\n(?:  \d+\. [^\n]+\n)*)",
    re.MULTILINE,
)


def extract_preread_paths_from_block(block: str) -> List[str]:
    """Extract file paths from a Task Pre-read block."""
    paths: List[str] = []
    
    # Match lines like: 1. `[rule]` `.agents/core/execution.md`
    # Pattern: number. `[label]` `<path>`
    # Note: [label] is also in backticks, so we need to extract the second backtick group
    path_pattern = re.compile(r"^\s*\d+\.\s*`\[\w+\]`\s*`([^`]+)`")
    
    for line in block.splitlines():
        match = path_pattern.match(line)
        if match:
            path = match.group(1).strip()
            # Skip internal paths starting with _ or docs/plans/
            if path and not path.startswith("_") and "docs/plans/" not in path:
                paths.append(path)
    
    return sorted(set(paths))


def extract_task_blocks(content: str) -> List[Dict[str, Any]]:
    """Extract all Task blocks with their Pre-read sections."""
    tasks: List[Dict[str, Any]] = []
    
    # Match Task headings and their content
    task_heading_re = re.compile(r"^####\s+Task\s+\d+\.\d+:.*$", re.MULTILINE)
    matches = list(task_heading_re.finditer(content))
    
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        block = content[start:end]
        
        # Extract Task ID
        task_id_match = re.search(r"Task\s+(\d+\.\d+)", block)
        task_id = task_id_match.group(1) if task_id_match else f"Unknown.{i}"
        
        # Extract Pre-read block
        preread_match = TASK_PREREAD_BLOCK_RE.search(block)
        preread_block = preread_match.group(1) if preread_match else ""
        
        # Extract Target
        target_match = re.search(r"\*\*Target\*\*:\s*`?([^`|]+)`?", block, re.IGNORECASE)
        target = target_match.group(1).strip() if target_match else ""
        
        # Extract Goal
        goal_match = re.search(r"\*\*Goal\*\*:\s*([^|]+)", block, re.IGNORECASE)
        goal = goal_match.group(1).strip() if goal_match else ""
        
        tasks.append({
            "task_id": task_id,
            "block": block,
            "preread_block": preread_block,
            "target": target,
            "goal": goal,
        })
    
    return tasks


def load_preread_skills(plan_path: Path) -> List[str]:
    """
    Load all Pre-read skills from the plan file.
    
    Returns list of loaded skill paths.
    """
    content = plan_path.read_text(encoding="utf-8")
    tasks = extract_task_blocks(content)
    
    loaded_skills: List[str] = []
    
    for task in tasks:
        preread_paths = extract_preread_paths_from_block(task["preread_block"])
        
        if preread_paths:
            print(f"\n📚 Task {task['task_id']}: Loading {len(preread_paths)} Pre-read skills")
            print(f"   Target: {task['target'][:60]}...")
            
            for skill_path in preread_paths:
                # Convert relative path to absolute
                if not skill_path.startswith("/"):
                    skill_abs_path = _REPO_ROOT / skill_path
                else:
                    skill_abs_path = Path(skill_path)
                
                if skill_abs_path.exists():
                    loaded_skills.append(str(skill_abs_path))
                    print(f"   ✅ Loaded: {skill_path}")
                else:
                    print(f"   ⚠️  Not found: {skill_path}")
    
    return loaded_skills


def main(argv=None):
    if not argv:
        argv = sys.argv[1:]
    
    if len(argv) < 1:
        print("Usage: python3 scripts/agent/auto_load_preread.py docs/plans/PLAN_x.md")
        print("       just auto-preread plan=docs/plans/PLAN_x.md")
        return 1
    
    # Handle both direct path and plan=<path> format
    plan_arg = argv[0]
    if plan_arg.startswith("plan="):
        plan_arg = plan_arg[5:]  # Remove "plan=" prefix
    
    plan_path = Path(plan_arg)
    
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}")
        return 1
    
    print(f"🔍 Scanning Pre-read skills from: {plan_path.name}")
    
    loaded = load_preread_skills(plan_path)
    
    print(f"\n✅ Total {len(loaded)} Pre-read skills loaded")
    
    if loaded:
        print("\n💡 Tip: These skills are now available in your context.")
        print("   Read each skill's SKILL.md path from the plan Pre-read list.")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
