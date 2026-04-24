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
    ty check . || pyright .

test:
    pytest

# --- Utility ---

# Clean temporary files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    rm -rf .pytest_cache .ruff_cache .coverage
