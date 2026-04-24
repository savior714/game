#!/usr/bin/env bash
set -e

# ==========================================
# Agentic Development System Bootstrap
# ==========================================

echo -e "\033[0;34m🚀 Initializing Agentic Development System...\033[0m"

# 1. Environment Detection
if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
    LANG="Python"
elif [ -f "package.json" ]; then
    LANG="Node"
else
    LANG="Unknown"
fi

echo -e "Detected Language: \033[0;32m$LANG\033[0m"

# 1.5 Tool Check (Allowlist)
echo -e "🔍 Checking recommended tools..."
for tool in uv ruff nu just nix; do
    if command -v $tool > /dev/null 2>&1; then
        echo -e "  - $tool: \033[0;32mFound\033[0m"
    else
        echo -e "  - $tool: \033[0;33mNot Found\033[0m (Recommended)"
    fi
done

# 2. Directory Creation
echo -e "📦 Creating directory structure..."
mkdir -p docs/{specs,rules,memory,knowledge}
mkdir -p tests
mkdir -p tools
mkdir -p .agents/workflows

# 3. Inject Templates
TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/templates" && pwd)"

echo -e "💉 Injecting system files..."

# Helper to copy if not exists or prompt
safe_copy() {
    local src="$1"
    local dest="$2"
    if [ -f "$dest" ]; then
        echo -e "\033[0;33m⚠️  $dest already exists. Skipping.\033[0m"
    else
        cp "$src" "$dest"
        echo -e "✅ Created $dest"
    fi
}

safe_copy "$TEMPLATE_DIR/AGENTS.md" "AGENTS.md"
safe_copy "$TEMPLATE_DIR/PROJECT_RULES.md" "PROJECT_RULES.md"
safe_copy "$TEMPLATE_DIR/verify.sh" "verify.sh"
safe_copy "$TEMPLATE_DIR/tools/tdd_gate_plugin.py" "tools/tdd_gate_plugin.py"
safe_copy "$TEMPLATE_DIR/flake.nix" "flake.nix"
safe_copy "$TEMPLATE_DIR/Justfile" "Justfile"
safe_copy "$TEMPLATE_DIR/dev.nu" "dev.nu"
safe_copy "$TEMPLATE_DIR/.pre-commit-config.yaml" ".pre-commit-config.yaml"

# 3.1 Inject Design Perspective
mkdir -p docs/specs/technical
safe_copy "$TEMPLATE_DIR/docs/specs/technical/DESIGN.md" "docs/specs/technical/DESIGN.md"

if [ "$LANG" == "Python" ]; then
    safe_copy "$TEMPLATE_DIR/pytest.ini" "pytest.ini"
    safe_copy "$TEMPLATE_DIR/tests/conftest.py" "tests/conftest.py"
    safe_copy "$TEMPLATE_DIR/tests/test_initial.py" "tests/test_initial.py"
fi

# 4. Environment Sync
echo -e "🔄 Syncing environment..."
if command -v uv > /dev/null 2>&1; then
    uv sync
fi

# 5. Permissions
chmod +x verify.sh

# 6. Failure Simulation (Enforcement Check)
echo -e "🧪 Simulating failure (TDD Gate Check)..."
mkdir -p src
touch src/failure_trigger.py
git add src/failure_trigger.py || true

if ./verify.sh > /dev/null 2>&1; then
    echo -e "\033[0;31m❌ TDD Gate FAIL: 시스템이 테스트 없는 코드 변경을 차단하지 못했습니다.\033[0m"
    rm src/failure_trigger.py
    exit 1
else
    echo -e "\033[0;32m✅ TDD Gate OK: 테스트 없는 코드 변경이 정상적으로 차단되었습니다.\033[0m"
    rm src/failure_trigger.py
fi

# 7. Summary
echo -e "\n\033[0;32m✨ Bootstrap Complete!\033[0m"
echo -e "------------------------------------------------"
echo -e "Next steps to activate TDD Gate:"
if [ "$LANG" == "Python" ]; then
    echo -e "1. Install pytest: \033[0;36mpip install pytest\033[0m"
    echo -e "2. Run verification: \033[0;36m./verify.sh\033[0m"
    echo -e "3. See the initial test fail, then implement your logic!"
fi
echo -e "------------------------------------------------"
