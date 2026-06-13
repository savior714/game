import json
import sys
import tomllib
from pathlib import Path

# SSOT: Snapshot location for detected dependencies
SNAPSHOT_PATH = Path(".agents/dependency_snapshot.json")

def get_python_deps():
    deps = set()
    # Find all pyproject.toml files excluding common ignored directories
    for pyproject_path in Path(".").rglob("pyproject.toml"):
        # Skip common build/env directories
        if any(part in pyproject_path.parts for part in [".venv", "venv", "node_modules", "dist", "build"]):
            continue
            
        try:
            with pyproject_path.open("rb") as f:
                data = tomllib.load(f)
            
            raw_deps = set()
            # project.dependencies
            project = data.get("project", {})
            raw_deps.update(project.get("dependencies", []))
            
            # dependency-groups (PEP 735)
            groups = data.get("dependency-groups", {})
            for group_deps in groups.values():
                raw_deps.update(group_deps)
                
            # tool.poetry.dependencies (Legacy if any)
            tool = data.get("tool", {})
            poetry = tool.get("poetry", {})
            raw_deps.update(poetry.get("dependencies", {}).keys())
            raw_deps.update(poetry.get("group", {}).get("dev", {}).get("dependencies", {}).keys())

            # Clean version specifiers
            for dep in raw_deps:
                if not isinstance(dep, str): continue
                # Split by standard specifiers: >=, ==, <=, ~=, <, >, [, ;
                name = dep.replace(" ", "")
                for op in [">=", "==", "<=", "~=", "<", ">", "[", ";"]:
                    name = name.split(op)[0]
                clean_name = name.strip().lower()
                if clean_name:
                    deps.add(clean_name)
        except Exception as e:
            print(f"ERROR: Failed to parse {pyproject_path}: {e}")
            sys.exit(1)
            
    return deps

def get_node_deps():
    deps = set()
    # Find all package.json files excluding common ignored directories
    for pj_path in Path(".").rglob("package.json"):
        if any(part in pj_path.parts for part in ["node_modules", "dist", "build", ".next"]):
            continue
            
        try:
            with pj_path.open("r") as f:
                data = json.load(f)
            
            # Collect all dependency keys
            for key in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
                deps.update(data.get(key, {}).keys())
                
            # Collect overrides/resolutions keys
            for key in ["overrides", "resolutions"]:
                deps.update(data.get(key, {}).keys())
                
        except Exception as e:
            print(f"ERROR: Failed to parse {pj_path}: {e}")
            sys.exit(1)
            
    return deps

def get_current_deps():
    python_deps = get_python_deps()
    node_deps = get_node_deps()
    return python_deps.union(node_deps)

def load_snapshot():
    if not SNAPSHOT_PATH.exists():
        return set()
    try:
        with SNAPSHOT_PATH.open("r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_snapshot(deps):
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_PATH.open("w") as f:
        json.dump(sorted(list(deps)), f, indent=2, ensure_ascii=False)

def research_library(lib_name):
    """
    Simulates or triggers research for a new library.
    In the agentic workflow, this outputs a request that the agent fulfills.
    """
    research_dir = Path(".agents/research")
    research_dir.mkdir(parents=True, exist_ok=True)
    research_file = research_dir / f"{lib_name}.json"
    
    if research_file.exists():
        print(f"  ℹ️  Research for '{lib_name}' already exists at {research_file}")
        return True

    print(f"  🔍 [RESEARCH_NEEDED] {lib_name}")
    print(f"     Target: {research_file}")
    # Return False to indicate research is still needed
    return False

def generate_rule_file(lib_name):
    """
    Generates a modular rule file (.md) from researched best practices.
    """
    research_file = Path(".agents/research") / f"{lib_name}.json"
    if not research_file.exists():
        return False
        
    try:
        with research_file.open("r") as f:
            data = json.load(f)
            
        rule_dir = Path(".agents/domains/tech-stack")
        rule_dir.mkdir(parents=True, exist_ok=True)
        rule_file = rule_dir / f"{lib_name}.md"
        
        scope = get_library_scope(lib_name)
        
        must_list = "\n".join([f"- {rule}" for rule in data["best_practices"]["MUST"]])
        must_not_list = "\n".join([f"- {rule}" for rule in data["best_practices"]["MUST_NOT"]])
        
        content = f"""---
scope: {json.dumps(scope)}
always_apply: false
priority: normal
description: {lib_name} 라이브러리 사용 지침 (자동 생성)
---

<!-- Language: ko -->
# {lib_name.capitalize()} Coding Rules

## MUST
{must_list}

## MUST NOT
{must_not_list}

## Recommended Pattern
```typescript
{data.get("recommended_pattern", "N/A")}
```
"""
        with rule_file.open("w") as f:
            f.write(content)
            
        register_rule_to_registry(lib_name, scope)
            
        print(f"  ✅ [RULE_GENERATED] {rule_file}")
        return True
    except Exception as e:
        print(f"  ❌ Error generating rule for {lib_name}: {e}")
        return False

def get_library_scope(lib_name):
    """
    Heuristic to determine the scope of a library.
    """
    frontend_libs = ["zustand", "react-query", "tanstack-query", "framer-motion", "lucide-react", "react", "next"]
    if any(k in lib_name.lower() for k in frontend_libs):
        return ["**/*.ts", "**/*.tsx"]
    return ["**/*.py"]

def register_rule_to_registry(lib_name, scope):
    """
    Automatically registers the new rule in RULE_INDEX.md and CONTEXT_ROUTING.md.
    """
    registry_dir = Path(".agents/registry")
    rule_index_path = registry_dir / "RULE_INDEX.md"
    context_routing_path = registry_dir / "CONTEXT_ROUTING.md"

    # 1. Update RULE_INDEX.md
    if rule_index_path.exists():
        content = rule_index_path.read_text(encoding="utf-8")
        if f"{lib_name}.md" not in content:
            lines = content.splitlines()
            target_line_idx = -1
            for i, line in enumerate(lines):
                if "## 🌐 Domain Specific Rules" in line:
                    for j in range(i + 1, len(lines)):
                        # Look for the end of the table
                        if lines[j].startswith("|") and (j + 1 >= len(lines) or not lines[j+1].startswith("|")):
                            target_line_idx = j + 1
                            break
                        if lines[j].startswith("##"):
                            target_line_idx = j
                            break
                    if target_line_idx != -1: break
            
            if target_line_idx != -1:
                new_row = f"| **Tech Stack** | [.agents/domains/tech-stack/{lib_name}.md](../specs/domains/tech-stack/{lib_name}.md) | {lib_name} 라이브러리 사용 지침 |"
                lines.insert(target_line_idx, new_row)
                rule_index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                print(f"  ✅ [REGISTRY] Added {lib_name} to RULE_INDEX.md")

    # 2. Update CONTEXT_ROUTING.md
    if context_routing_path.exists():
        content = context_routing_path.read_text(encoding="utf-8")
        if f"tech-stack/{lib_name}.md" not in content:
            lines = content.splitlines()
            target_line_idx = -1
            for i, line in enumerate(lines):
                if "## 🗺️ 경로별 동적 매핑" in line:
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("|") and (j + 1 >= len(lines) or not lines[j+1].startswith("|")):
                            target_line_idx = j + 1
                            break
                        if lines[j].startswith("##"):
                            target_line_idx = j
                            break
                    if target_line_idx != -1: break

            if target_line_idx != -1:
                scope_str = ", ".join([f"`{s}`" for s in scope])
                new_row = f"| {scope_str} | `tech-stack/{lib_name}.md` | {lib_name} specific rules |"
                lines.insert(target_line_idx, new_row)
                context_routing_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                print(f"  ✅ [ROUTING] Added {lib_name} to CONTEXT_ROUTING.md")

def main():
    print("🔍 Scanning for tech stack dependencies...")
    current_deps = get_current_deps()
    snapshot_deps = load_snapshot()
    
    if not snapshot_deps:
        print("💡 Initializing dependency snapshot (First run)...")
        save_snapshot(current_deps)
        print(f"✅ Baseline established with {len(current_deps)} dependencies.")
        print("   Run again after adding new libraries to detect changes.")
        return

    new_deps = current_deps - snapshot_deps
    removed_deps = snapshot_deps - current_deps
    
    if new_deps:
        print("\n🚀 [DETECTED] New dependencies found:")
        for dep in sorted(list(new_deps)):
            print(f"  + {dep}")
            if not research_library(dep):
                continue
            # If research exists, try to generate/update the rule file
            generate_rule_file(dep)
        
        print("\n💡 Tip: If you see [RESEARCH_NEEDED], perform research and save to .agents/research/<lib>.json, then run again.")
    else:
        print("\n✨ No new dependencies detected.")

    if removed_deps:
        print("\n🧹 [CLEANUP] Removed dependencies:")
        for dep in sorted(list(removed_deps)):
            print(f"  - {dep}")

if __name__ == "__main__":
    main()
