#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path

import yaml

AGENTS_DIR = ".agents"
REQUIRED_YAML_FIELDS = ["scope", "domain"]
LANGUAGE_GATE = "<!-- Language: ko -->"

def fix_rule_file(path: Path, dry_run: bool = False, backup: bool = False) -> bool:
    """
    Fixes YAML header and Language Gate for a single rule file.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Failed to read {path}: {e}")
        return False

    dirty = False
    
    # 1. Strip existing Language Gate to normalize content
    # We'll re-insert it later in the correct position.
    has_gate = LANGUAGE_GATE in content
    # Remove gate and leading/trailing whitespace around it
    cleaned_content = content.replace(LANGUAGE_GATE, "").strip()
    
    # 2. Extract and Parse YAML
    header_data = {}
    body_content = cleaned_content
    
    if cleaned_content.startswith("---"):
        parts = cleaned_content.split("---", 2)
        if len(parts) >= 3:
            yaml_str = parts[1]
            body_content = parts[2].strip()
            try:
                header_data = yaml.safe_load(yaml_str) or {}
            except yaml.YAMLError:
                print(f"ERROR: Invalid YAML in {path}. Aborting.")
                sys.exit(1)
        else:
            # Malformed header
            print(f"ERROR: Malformed header in {path}. Aborting.")
            sys.exit(1)
    
    # 3. Ensure Required Fields
    # Determine defaults based on path
    defaults = {
        "scope": "core",
        "domain": "core"
    }
    
    if "workflows" in str(path):
        defaults["scope"] = "workflow"
        defaults["domain"] = "workflow"
    elif "domains" in str(path):
        defaults["scope"] = "domain"
        defaults["domain"] = path.parent.name
    elif "registry" in str(path):
        defaults["scope"] = "registry"
        defaults["domain"] = "core"
    elif "adaptive" in str(path):
        defaults["scope"] = "adaptive"
        defaults["domain"] = "core"

    for field in REQUIRED_YAML_FIELDS:
        if field not in header_data:
            header_data[field] = defaults[field]
            dirty = True

    # 4. Reconstruct File
    # Always sort keys to be consistent
    new_yaml_str = yaml.dump(header_data, sort_keys=False).strip()
    
    # The standard format: 
    # ---
    # scope: ...
    # domain: ...
    # ---
    # <!-- Language: ko -->
    # 
    # [Body]
    
    result = f"---\n{new_yaml_str}\n---\n{LANGUAGE_GATE}\n\n{body_content}\n"
    
    # Check if anything actually changed (normalize line endings for comparison)
    if result.strip() == content.strip():
        return False

    if dry_run:
        print(f"🔍 [Dry-Run] Would fix: {path}")
        return True

    # 5. Apply Changes
    if backup:
        shutil.copy(path, path.with_suffix(".md.bak"))
    
    try:
        path.write_text(result, encoding="utf-8")
        return True
    except Exception as e:
        print(f"❌ Failed to write {path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Fix agent rule files (YAML & Language Gate)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying")
    parser.add_argument("--backup", action="store_true", help="Create .bak files before modifying")
    parser.add_argument("--target", type=str, default=AGENTS_DIR, help="Target directory (default: .agents)")
    
    args = parser.parse_args()
    
    base_path = Path(args.target)
    if not base_path.exists():
        print(f"Error: {args.target} not found.")
        return

    rule_files = sorted(list(base_path.rglob("*.md")))
    fixed_count = 0
    
    print(f"🛠️ Fixing rule files in {args.target}...")
    
    for f in rule_files:
        if fix_rule_file(f, dry_run=args.dry_run, backup=args.backup):
            if not args.dry_run:
                print(f"✅ Fixed: {f}")
            fixed_count += 1
            
    if args.dry_run:
        print(f"\n[Dry-Run Done] {fixed_count} files would be fixed.")
    else:
        print(f"\nDone! Fixed {fixed_count} files.")

if __name__ == "__main__":
    main()
