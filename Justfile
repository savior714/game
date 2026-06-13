# Justfile - Single Entry Pipeline (AidenGame + bootstrap kernel)

default:
    @just --list

# --- Bootstrap kernel ---

verify:
    @bash verify.sh

lint-turn-end:
    @echo "Turn-end gate (AidenGame)"
    @just verify

# --- Development ---

# Sync dependencies and environment
sync:
    uv sync

# Run all checks (Lint, Type, Test, Verify)
ci:
    @echo "Running AidenGame CI..."
    @just lint
    @just typecheck
    @just test
    @just verify

# --- Steps ---

lint:
    ruff check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
    ruff format --check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py

typecheck:
    ty check . --exclude tests/ --exclude tools/tdd_gate_plugin.py --exclude templates/tools/tdd_gate_plugin.py || if command -v pyright >/dev/null 2>&1; then pyright .; else echo "pyright not found; skipping fallback"; fi

test:
    uv run pytest tests

# --- Commit Gate (git.md §5.0~§5.2) ---

# hard 게이트: 보안 선제 검증 (env-lint + staged_secret_gate) — --no-verify 금지
commit-gate-hard:
    @echo "🔒 Hard commit gate (security)..."
    @if [ -f .env.example ] || [ -f .env ]; then \
        uv run python scripts/verify/lint_dotenv.py || { echo "❌ dotenv lint 실패"; exit 1; }; \
    else \
        echo "[skip] .env.example/.env 없음 — dotenv lint 건너뜀."; \
    fi
    @git diff --cached --quiet || uv run python scripts/verify/staged_secret_gate.py || { echo "❌ 민감 파일 스테이징 감지"; exit 1; }
    @echo "✅ Hard gate 통과."

# soft 게이트: lint만 (ty pre-existing 99개 제외 — 별도 백로그)
commit-gate-soft:
    @echo "🔍 Soft commit gate (lint)..."
    @ruff check --fix tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py || { echo "❌ ruff check 실패"; exit 1; }
    @ruff format tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py || { echo "❌ ruff format 실패"; exit 1; }
    @echo "✅ Soft gate 통과."

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

# --- Blueprint / Plan ---

# 🧭 Blueprint: scan paths/stack → insert «Context Pre-read Gate» (run before plan-lint). Ex: `just plan-preread docs/plans/PLAN_x.md --write`
plan-preread plan="" *args="":
	@if [ -z "{{plan}}" ]; then echo "Usage: just plan-preread docs/plans/<file>.md --write"; exit 1; fi
	@uv run python scripts/plan_loop/plan_preread_manifest.py "{{plan}}" {{args}}

# 📝 Verify plan blueprint files
plan-lint plan="" *args="":
	@echo "🔍 Verifying plan blueprint files..."
	@if [ -z "{{plan}}" ]; then \
		echo "🔍 Checking all blueprints in docs/plans/..." ; \
		ls docs/plans/*.md | grep -v -E "README.md|ROADMAP.md|pre-read-verification-result.md|PLAN_discover" | xargs -n 1 uv run python scripts/plan_loop/plan_lint.py {{args}} ; \
	else \
		uv run python scripts/plan_loop/plan_lint.py "{{plan}}" {{args}} ; \
	fi

# `plan-lint` 과 동일하나 Linear ensure 훅 생략(CI·오프라인)
plan-lint-ci:
	@echo "🔍 Verifying all blueprints (no Linear ensure)..."
	@ls docs/plans/*.md | grep -v -E "README.md|ROADMAP.md|pre-read-verification-result.md|PLAN_discover" | xargs -n 1 uv run python scripts/plan_loop/plan_lint.py --skip-linear-ensure

# Git-touched active PLAN_* blueprints only (archive excluded)
plan-lint-touched:
	@uv run python scripts/plan_loop/plan_lint_touched.py

# ✅ Task 1개 완료 처리용 CLI (마크다운 인플레이스 갱신 안전장치)
plan-task-close plan="" task="" conclusion="":
	@if [ -z "{{plan}}" ] || [ -z "{{task}}" ] || [ -z "{{conclusion}}" ]; then \
		echo "❌ plan, task, conclusion 인자가 모두 필요합니다."; \
		echo "예: just plan-task-close plan=docs/plans/<file>.md task=XXX-001 conclusion=\"[PASS] ...\""; \
		exit 1; \
	fi
	@uv run python scripts/plan_loop/plan_task_close.py --plan "{{plan}}" --task "{{task}}" --conclusion "{{conclusion}}"

# ↩️ Blueprint Task 역방향 리셋 게이트 (승인·SHA·Verify 필수)
plan-reset-gate plan="" task="" sha="" approval="" apply="":
	@if [ -z "{{plan}}" ] || [ -z "{{task}}" ] || [ -z "{{sha}}" ] || [ -z "{{approval}}" ]; then \
		echo "❌ plan, task, sha, approval 인자가 모두 필요합니다."; \
		echo "예: just plan-reset-gate plan=docs/plans/<file>.md task=XXX-001 sha=$(git rev-parse HEAD) approval=\"승인 사유\""; \
		exit 1; \
	fi
	@uv run python scripts/plan_loop/plan_reset_gate.py --plan "{{plan}}" --task "{{task}}" --sha "{{sha}}" --approval "{{approval}}"
	@if [ "{{apply}}" = "true" ] || [ "{{apply}}" = "--apply" ]; then \
		uv run python scripts/plan_loop/plan_reset_apply.py --plan "{{plan}}" --task "{{task}}" --sha "{{sha}}" --approval "{{approval}}"; \
	fi

# Plan close gate (DoD verify + placeholder check)
plan-close plan="" verify="":
	@set -e; \
	if [ -z "{{plan}}" ]; then \
		echo "❌ plan 인자가 필요합니다. 예: just plan-close plan=docs/plans/<file>.md"; \
		exit 1; \
	fi; \
	uv run python scripts/verify/plan_close_gate.py --plan "{{plan}}" --verify "{{verify}}"

# --- Archive ---

# 아카이브된 플랜 인덱스 갱신 + check + guard-deleted
plans-index:
	@echo "📦 Updating plans index..."
	@uv run python scripts/archive_plans.py check || true
	@uv run python scripts/archive_plans.py guard-deleted || true

# 플랜 아카이브 (plans -> plans/archive/<분류>/)
archive-plan plan="":
	@if [ -z "{{plan}}" ]; then echo "❌ plan 인자가 필요합니다."; exit 1; fi
	@uv run python scripts/archive_plans.py archive -- "{{plan}}"

# 아카이브 dry-run
archive-plan-dry plan="":
	@if [ -z "{{plan}}" ]; then echo "❌ plan 인자가 필요합니다."; exit 1; fi
	@uv run python scripts/archive_plans.py archive --dry-run -- "{{plan}}"
