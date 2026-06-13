import os
import sys

def process(dry_run=True):
    with open("knip_report.txt", "r") as f:
        lines = f.readlines()
        
    in_files = False
    files_to_delete = []
    for line in lines:
        if line.startswith("Unused files"):
            in_files = True
            continue
        if line.startswith("Unused dependencies") or line.startswith("Unused exports"):
            in_files = False
            continue
            
        if not in_files:
            continue
            
        if "src/" not in line:
            continue
            
        parts = line.strip().split()
        if not parts:
            continue
            
        file_path = parts[0]
        full_path = os.path.join("apps/renderer", file_path)
        if os.path.exists(full_path):
            files_to_delete.append(full_path)
            
    for f in files_to_delete:
        if dry_run:
            print(f"Would delete {f}")
        else:
            print(f"Deleting {f}")
            os.remove(f)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--write":
        process(dry_run=False)
    else:
        process(dry_run=True)
