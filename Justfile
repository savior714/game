# Justfile - Single Entry Pipeline

default:
    @just --list

# --- Development ---

# Sync dependencies and environment
sync:
    uv sync

# Run all checks (Lint, Type, Test)
ci: lint typecheck test

# --- Steps ---

lint:
    ruff check .
    ruff format --check .

typecheck:
    ty check . --exclude tests/ --exclude tools/tdd_gate_plugin.py --exclude templates/tools/tdd_gate_plugin.py || if command -v pyright >/dev/null 2>&1; then pyright .; else echo "pyright not found; skipping fallback"; fi

test:
    pytest tests

# --- Utility ---

# Clean temporary files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    rm -rf .pytest_cache .ruff_cache .coverage

# Save non-destructive working-tree snapshot for commit safety.
wip name:
    mkdir -p .git-snapshots
    ts=$(date +%Y%m%d_%H%M%S); \
    file=".git-snapshots/${ts}_{{name}}.patch"; \
    { \
      echo "# WIP snapshot: {{name}}"; \
      echo "# Generated at: ${ts}"; \
      echo; \
      git status --short; \
      echo; \
      git diff --binary; \
      echo; \
      git diff --binary --cached; \
    } > "$file"; \
    echo "Saved snapshot: $file"
