#!/usr/bin/env python3
"""Check for residual issues or follow-up tasks in a plan document.
Used by the /archive workflow to ensure no unresolved issues are lost.
"""

import argparse
import re
import sys
from pathlib import Path

def check_residual_issues(plan_path: Path):
    if not plan_path.exists():
        print(f"Error: File not found: {plan_path}")
        return None

    content = plan_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    residual_issues = []
    
    # 1. Look for specific follow-up sections
    followup_patterns = [
        r"##\s*🔁\s*후속 플랜 도출용 요약",
        r"##\s*Residual Issues",
        r"##\s*Future Tasks",
        r"##\s*Next Steps"
    ]
    
    in_followup_section = False
    for line in lines:
        if any(re.match(p, line, re.IGNORECASE) for p in followup_patterns):
            in_followup_section = True
            residual_issues.append(f"Section found: {line.strip()}")
            continue
        
        if in_followup_section:
            if line.startswith("## ") and not any(re.match(p, line, re.IGNORECASE) for p in followup_patterns):
                in_followup_section = False
            elif line.strip() and not line.startswith("#"):
                # Capture some content as evidence
                section_lines_count = sum(1 for x in residual_issues if x.startswith("  - "))
                if section_lines_count < 5: # Limit section preview
                    residual_issues.append(f"  - {line.strip()}")

    # 2. Look for unfinished tasks or deferred issues in Conclusions
    # Task pattern: Status: todo | Status: blocked | Status: running
    task_status_pattern = re.compile(r"(?:\*\*|)?Status(?:\*\*|)?:\s*(done|todo|blocked|running)", re.IGNORECASE)
    deferred_keywords = ["별도 플랜", "후속", "이관", "범위 외", "out of scope", "later", "deferred", "추후", "남겨둔", "남겨놓은"]
    
    for i, line in enumerate(lines):
        match = task_status_pattern.search(line)
        if match:
            status = match.group(1).lower()
            
            # Find the task title
            title = "Unknown Task"
            for j in range(i-1, max(-1, i-5), -1):
                if lines[j].strip().startswith("#### Task"):
                    title = lines[j].strip()
                    break

            if status in ["todo", "blocked", "running"]:
                residual_issues.append(f"Unfinished Task: {title} (Status: {status})")
            elif status == "done":
                # Scan Conclusion for deferred issues
                window = lines[i : min(i + 10, len(lines))]
                conclusion_line = next((w for w in window if "Conclusion" in w), "")
                if conclusion_line:
                    if any(kw in conclusion_line for kw in deferred_keywords):
                        residual_issues.append(f"Deferred Issue in {title}:")
                        residual_issues.append(f"  - {conclusion_line.strip()}")

    return residual_issues

def main():
    parser = argparse.ArgumentParser(description="Scan plan for residual issues.")
    parser.add_argument("plan", type=Path, help="Path to the plan markdown file")
    args = parser.parse_args()

    issues = check_residual_issues(args.plan)
    
    if issues:
        print(f"Found residual issues in {args.plan.name}:")
        for issue in issues:
            print(issue)
        sys.exit(1) # Signal that there are issues
    else:
        print(f"No residual issues found in {args.plan.name}.")
        sys.exit(0)

if __name__ == "__main__":
    main()
