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

# Run all checks without repeating verify.sh coverage
ci:
    @echo "Running AidenGame CI..."
    @just typecheck
    @just verify

# --- Steps ---

lint:
    uv run ruff check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
    uv run ruff format --check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py

typecheck:
    @targets="scripts/verify_korean_text.py scripts/verify_korean_js.py scripts/verify/lint_dotenv.py scripts/verify/staged_secret_gate.py tools/mcp_call_wrapper.py"; \
    if command -v ty >/dev/null 2>&1; then \
        ty check $targets; \
    elif command -v pyright >/dev/null 2>&1; then \
        pyright $targets; \
    else \
        echo "❌ required type checker unavailable: install ty or pyright"; \
        exit 1; \
    fi

test:
    uv run pytest tests

# Rebuild the tracked Ocean Rescue standalone artifact
build-ocean-rescue:
    uv run python scripts/ocean_rescue/validate_pixi_vendor.py
    uv run python scripts/ocean_rescue/validate_atlases.py \
        --packet domains/ocean-rescue/assets/source/art-packet.json \
        --approval domains/ocean-rescue/assets/source/art-approval.json \
        --generated-dir domains/ocean-rescue/assets/generated
    uv run python scripts/ocean_rescue/build_render_assets_registry.py \
        --atlas-dir domains/ocean-rescue/assets/generated \
        --output domains/ocean-rescue/src/render-assets.generated.js
    uv run python scripts/ocean_rescue/build_single_html.py \
        --manifest domains/ocean-rescue/src/build-manifest.json \
        --output ocean-rescue/index.html

# Verify that the tracked Ocean Rescue artifact matches a clean rebuild
check-ocean-rescue-drift:
    uv run pytest tests/test_ocean_rescue_artifact_drift.py -q

# Build Ocean Rescue deterministic 2× atlas pipeline
build-ocean-rescue-atlases:
    DYLD_LIBRARY_PATH=/opt/homebrew/opt/cairo/lib uv run python scripts/ocean_rescue/build_atlases.py \
        --packet domains/ocean-rescue/assets/source/art-packet.json \
        --approval domains/ocean-rescue/assets/source/art-approval.json \
        --output-dir domains/ocean-rescue/assets/generated

# Verify Ocean Rescue atlas pipeline
check-ocean-rescue-atlases:
    uv run pytest -q tests/test_ocean_rescue_atlas_pipeline.py

# Build render package (vendor + atlas registry + single HTML)
build-ocean-rescue-render-package:
    uv run python scripts/ocean_rescue/validate_pixi_vendor.py
    uv run python scripts/ocean_rescue/validate_atlases.py \
        --packet domains/ocean-rescue/assets/source/art-packet.json \
        --approval domains/ocean-rescue/assets/source/art-approval.json \
        --generated-dir domains/ocean-rescue/assets/generated
    uv run python scripts/ocean_rescue/build_render_assets_registry.py \
        --atlas-dir domains/ocean-rescue/assets/generated \
        --output domains/ocean-rescue/src/render-assets.generated.js
    uv run python scripts/ocean_rescue/build_single_html.py \
        --manifest domains/ocean-rescue/src/build-manifest.json \
        --output ocean-rescue/index.html

# Check render package integrity
check-ocean-rescue-render-package:
    uv run pytest -q \
        tests/test_ocean_rescue_render_packaging.py \
        tests/test_ocean_rescue_artifact_drift.py

# --- Ocean Rescue Node & build-tooling boundary (WP-10) ---

# Verify the active Node is exactly domains/ocean-rescue/.node-version
check-ocean-rescue-node-version:
    @expected="$(cat domains/ocean-rescue/.node-version)"; \
    actual="$(node -p 'process.versions.node')"; \
    if [ "$expected" != "$actual" ]; then \
        echo "❌ Node version mismatch: expected=$expected actual=$actual"; \
        exit 1; \
    fi; \
    echo "✅ Node $actual matches .node-version"

# Verify project pnpm (corepack) is exactly the packageManager pin
check-ocean-rescue-pnpm-version:
    @expected="$(python3 -c 'import json; print(json.load(open("domains/ocean-rescue/package.json"))["packageManager"].split("+")[0].split("@")[1])')"; \
    actual="$(cd domains/ocean-rescue && corepack pnpm --version)"; \
    if [ "$expected" != "$actual" ]; then \
        echo "❌ pnpm version mismatch: expected=$expected actual=$actual"; \
        exit 1; \
    fi; \
    echo "✅ project pnpm $actual matches packageManager"

# Sync Ocean Rescue Node dependencies from the frozen lockfile
sync-ocean-rescue-node:
    @just check-ocean-rescue-node-version
    @just check-ocean-rescue-pnpm-version
    @cd domains/ocean-rescue && corepack pnpm install --frozen-lockfile

# Run the Ocean Rescue TypeScript baseline (no source emit)
typecheck-ocean-rescue:
    @just check-ocean-rescue-node-version
    @just check-ocean-rescue-pnpm-version
    @cd domains/ocean-rescue && corepack pnpm exec tsc --project tsconfig.json --noEmit

# Verify the Ocean Rescue build-tooling boundary end to end
check-ocean-rescue-toolchain:
    @just check-ocean-rescue-node-version
    @just check-ocean-rescue-pnpm-version
    @cd domains/ocean-rescue && corepack pnpm install --frozen-lockfile
    @vite_actual="$(cd domains/ocean-rescue && corepack pnpm exec vite --version)"; \
    tsc_actual="$(cd domains/ocean-rescue && corepack pnpm exec tsc --version)"; \
    case "$vite_actual" in \
        vite/8.1.5*) echo "✅ Vite $vite_actual" ;; \
        *) echo "❌ Vite version mismatch: expected=vite/8.1.5 actual=$vite_actual"; exit 1 ;; \
    esac; \
    if [ "$tsc_actual" != "Version 7.0.2" ]; then \
        echo "❌ TypeScript version mismatch: expected=Version 7.0.2 actual=$tsc_actual"; \
        exit 1; \
    fi; \
    echo "✅ TypeScript $tsc_actual"
    @just typecheck-ocean-rescue

# Run the Ocean Rescue Vite development server (development-only; production pipeline untouched)
dev-ocean-rescue host="127.0.0.1" port="5173":
    @just check-ocean-rescue-node-version
    @just check-ocean-rescue-pnpm-version
    @echo "🧪 Starting Ocean Rescue Vite dev server on http://{{host}}:{{port}}/index.dev.html"
    @cd domains/ocean-rescue && corepack pnpm exec vite --config vite.config.ts --host "{{host}}" --port "{{port}}" --strictPort

# Run the focused WP-11 dev-server static and browser contract (self-managed ephemeral port)
check-ocean-rescue-dev-server:
    uv run pytest tests/test_ocean_rescue_wp11_dev_server.py -q

# --- Commit Gate ---

# hard gate: security checks only; --no-verify is prohibited
commit-gate-hard:
    @echo "🔒 Hard commit gate (security)..."
    @dotenv_files=""; \
    if [ -f .env.example ]; then dotenv_files="$dotenv_files .env.example"; fi; \
    if [ -f .env ]; then dotenv_files="$dotenv_files .env"; fi; \
    if [ -n "$dotenv_files" ]; then \
        uv run python scripts/verify/lint_dotenv.py $dotenv_files || { echo "❌ dotenv lint 실패"; exit 1; }; \
    else \
        echo "[skip] .env.example/.env 없음 — dotenv lint 건너뜀."; \
    fi
    @git diff --cached --quiet || uv run python scripts/verify/staged_secret_gate.py || { echo "❌ 민감 파일 스테이징 감지"; exit 1; }
    @echo "✅ Hard gate 통과."

# soft gate: reuse canonical non-mutating lint and typecheck recipes
commit-gate-soft:
    @echo "🔍 Soft commit gate (lint/typecheck)..."
    @just lint
    @just typecheck
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