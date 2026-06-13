from pathlib import Path

def main():
    archive_dir = Path("docs/plans/archive")
    files = list(archive_dir.rglob("*.md"))
    modified_count = 0
    
    for f in files:
        if not f.is_file(): continue
        
        content = f.read_text(encoding="utf-8")
        new_content = []
        changed = False
        
        for line in content.splitlines():
            # Only replace if it's a Task line (starts with - Task-ID: or contains Status: )
            if "Status: todo" in line or "Status: in_progress" in line:
                line = line.replace("Status: todo", "Status: done")
                line = line.replace("Status: in_progress", "Status: done")
                changed = True
            new_content.append(line)
            
        if changed:
            f.write_text("\n".join(new_content) + "\n", encoding="utf-8")
            modified_count += 1
            print(f"Fixed status in {f}")
            
    print(f"Total files modified: {modified_count}")

if __name__ == "__main__":
    main()
