import os
import re
import sys


def check_memory_hygiene(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return 1

    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()

    line_count = len(lines)
    print(f"Checking {file_path} (Lines: {line_count})")

    errors = []

    # 1. Line count check (Limit: 200)
    if line_count > 200:
        errors.append(f"Line count violation: {line_count} lines (Limit: 200)")

    # 2. Duplicate link check
    # Regex to find markdown links: [text](url)
    link_pattern = re.compile(r'\[.*?\]\((.*?)\)')
    links = []
    for line in lines:
        found = link_pattern.findall(line)
        links.extend(found)

    seen_links = set()
    duplicates = set()
    for link in links:
        if link in seen_links:
            duplicates.add(link)
        seen_links.add(link)

    if duplicates:
        errors.append(f"Duplicate links found: {', '.join(duplicates)}")

    if errors:
        print("\n--- Hygiene Violations Found ---")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Hygiene check passed!")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python memory_guard.py <file_path>")
        sys.exit(1)

    sys.exit(check_memory_hygiene(sys.argv[1]))
