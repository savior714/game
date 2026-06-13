#!/usr/bin/env python3
import sys
import yaml
import re
from pathlib import Path
from typing import List

# Constants
AGENTS_DIR = ".agents"
REQUIRED_YAML_FIELDS = ["scope", "domain"]  # 예시 필수 필드
LINK_REGEX = re.compile(r'\[.*?\]\((.*?)\)')

def verify_links(path: Path, content: str) -> List[str]:
    """
    Finds and verifies all internal markdown links in the content.
    """
    errors = []
    links = LINK_REGEX.findall(content)
    project_root = Path.cwd()

    for link in links:
        # Skip external links and non-file protocols
        if link.startswith(("http://", "https://", "mailto:", "tel:", "data:")):
            continue
            
        # Skip anchor-only links
        if link.startswith("#"):
            continue
            
        # Strip anchor part for existence check
        clean_link = link.split("#")[0]
        if not clean_link or clean_link in ['링크', '...'] or '...' in clean_link or 'path/to/' in clean_link:
            continue

        # Vendored open-design skills are fetched locally (gitignored) — not required in CI.
        if "vendor/open-design" in clean_link.replace("\\", "/"):
            continue
            
        # Handle file:/// protocol
        if clean_link.startswith("file:///"):
            # Strip file:/// and use as absolute or project-relative
            clean_link = clean_link.replace("file://", "")
            if clean_link.startswith("/"):
                target_path = Path(clean_link)
            else:
                target_path = project_root / clean_link
        else:
            # 1. Try relative to the current file
            target_path = (path.parent / clean_link).resolve()
            
            # 2. If not found, try relative to the project root
            if not target_path.exists():
                target_path = (project_root / clean_link).resolve()

        # Final check
        try:
            if not target_path.exists():
                errors.append(f"Broken link: '{link}' (Resolved to: {target_path})")
        except Exception as e:
            errors.append(f"Invalid link format: '{link}' ({e})")
            
    return errors

def verify_rule_file(path: Path) -> List[str]:
    """
    Verifies a single rule file for YAML frontmatter, Language Gate, and Links.
    Returns a list of error messages.
    """
    errors = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Failed to read file: {e}"]

    # 1. Check Language Gate
    if "<!-- Language: ko -->" not in content:
        errors.append("Missing Language Gate: <!-- Language: ko -->")

    # 2. Parse YAML Frontmatter
    if not content.startswith("---"):
        errors.append("Missing YAML Frontmatter (must start with ---)")
    else:
        try:
            # Find the second ---
            parts = content.split("---", 2)
            if len(parts) < 3:
                errors.append("Invalid YAML Frontmatter structure (missing closing ---)")
            else:
                yaml_content = parts[1]
                data = yaml.safe_load(yaml_content)
                if not isinstance(data, dict):
                    errors.append("YAML Frontmatter is not a valid dictionary")
                else:
                    # Check for required fields
                    for field in REQUIRED_YAML_FIELDS:
                        if field not in data:
                            errors.append(f"Missing required YAML field: '{field}'")
        except yaml.YAMLError as e:
            errors.append(f"YAML Parse Error: {e}")
        except Exception as e:
            errors.append(f"Unexpected error parsing YAML: {e}")

    # 3. Check Links (Task 2.1)
    link_errors = verify_links(path, content)
    errors.extend(link_errors)

    return errors

def get_rule_files(base_dir: str = AGENTS_DIR) -> List[Path]:
    """
    Recursively finds all .md files in the .agents directory.
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"Error: Directory {base_dir} not found.")
        return []
    
    # rglob for recursive globbing
    rule_files = []
    for p in base_path.rglob("*.md"):
        if "vendor" in p.parts:
            continue
        if p.name == "COMPILED.md":
            continue
        rule_files.append(p)
    return sorted(rule_files)

def main():
    """
    Main execution for rule verification.
    """
    print(f"🔍 Verifying rule files in {AGENTS_DIR}...")
    
    rule_files = get_rule_files()
    
    if not rule_files:
        print("❌ No rule files found.")
        sys.exit(1)
        
    total_files = len(rule_files)
    failed_files = 0
    total_errors = 0
    
    # Strict directories that MUST follow all rules
    STRICT_DIRS = {"core", "domains", "adaptive", "registry", "workflows"}
    
    for rule_file in rule_files:
        # Get the relative path part after .agents/
        rel_path = rule_file.relative_to(AGENTS_DIR)
        top_dir = rel_path.parts[0] if rel_path.parts else ""
        
        is_strict = top_dir in STRICT_DIRS
        
        errors = []
        if is_strict:
            errors = verify_rule_file(rule_file)
        else:
            # For non-strict files (like skills), only check links
            try:
                content = rule_file.read_text(encoding="utf-8")
                errors = verify_links(rule_file, content)
            except Exception as e:
                errors = [f"Failed to read file: {e}"]
            
        if errors:
            failed_files += 1
            total_errors += len(errors)
            print(f"❌ {rule_file}")
            for err in errors:
                print(f"  - {err}")
        # else:
        #    print(f"✅ {rule_file}") # Too verbose if many files
            
    print("\n" + "="*40)
    if total_errors == 0:
        print(f"✨ All {total_files} rule files passed verification!")
    else:
        print(f"⚠️ Verification failed for {failed_files}/{total_files} files.")
        print(f"Total errors found: {total_errors}")
        sys.exit(1)

if __name__ == "__main__":
    main()
