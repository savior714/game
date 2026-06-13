import sys
import re
from pathlib import Path
import json

def process(dry_run=True):
    with open("knip_report.txt", "r") as f:
        lines = f.readlines()
    
    in_exports = False
    files_to_modify = set()
    for line in lines:
        if line.startswith("Unused exports"):
            in_exports = True
            continue
        if line.startswith("Unused exported types") or line.startswith("Duplicate exports"):
            in_exports = False
            continue
            
        if not in_exports:
            continue
            
        if "components/consultation" not in line:
            continue
            
        parts = line.strip().split()
        if len(parts) < 2:
            continue
            
        export_name = parts[0]
        if export_name == "default":
            continue # Skip default exports for safety
            
        path_line = parts[-1]
        match = re.search(r'([^:]+):(\d+):', path_line)
        if not match:
            continue
            
        file_tail = match.group(1).replace("…", "")
        actual_path = None
        for p in Path("apps/renderer/src").rglob(Path(file_tail).name):
            if file_tail in str(p):
                actual_path = p
                break
                
        if not actual_path:
            continue
            
        line_num = int(match.group(2))
        
        with open(actual_path, "r") as f:
            file_lines = f.readlines()
            
        target_idx = line_num - 1
        if 0 <= target_idx < len(file_lines):
            if "export " in file_lines[target_idx]:
                files_to_modify.add(str(actual_path))
                if not dry_run:
                    print(f"Modifying {actual_path}:{line_num} for {export_name}")
                    file_lines[target_idx] = file_lines[target_idx].replace("export ", "", 1)
                    with open(actual_path, "w") as f:
                        f.writelines(file_lines)
                        
    if dry_run:
        print(json.dumps(list(files_to_modify)))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--write":
        process(dry_run=False)
    else:
        process(dry_run=True)
