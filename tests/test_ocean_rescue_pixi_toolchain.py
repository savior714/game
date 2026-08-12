"""Contract tests for ocean-rescue package and Node tooling boundary.

Verifies that domains/ocean-rescue establishes the canonical pnpm/Node/Vite/
TypeScript build-time boundary while preserving the pre-existing package
identity and PixiJS exact pin.

The package boundary is the single pnpm authority under
domains/ocean-rescue. package-lock.json is removed; pnpm-lock.yaml is the only
package lockfile. no competitor lockfile (yarn, bun) is allowed. Root-level
package.json/lockfiles are not required as new authorities.

These are static contract tests only. They do not execute pnpm or Node;
runtime tool validation lives in the Justfile and the WP-10 verification
bundle.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
PACKAGE_JSON = DOMAIN_DIR / "package.json"
PACKAGE_LOCK = DOMAIN_DIR / "package-lock.json"
PNPM_LOCK = DOMAIN_DIR / "pnpm-lock.yaml"
NODE_VERSION = DOMAIN_DIR / ".node-version"
NPMRC = DOMAIN_DIR / ".npmrc"
TSCONFIG = DOMAIN_DIR / "tsconfig.json"
JUSTFILE = REPO_ROOT / "Justfile"

NAME = "@aidengame/ocean-rescue"
PNPM = "11.20.0"
NODE_EXACT = "24.19.0"
PIXI_EXACT = "8.19.0"
VITE_EXACT = "8.1.5"
TYPESCRIPT_EXACT = "7.0.2"

# Script keys that would imply a package-manager lifecycle hook.
LIFECYCLE_SCRIPT_KEYS = {
    "preinstall",
    "install",
    "postinstall",
    "prepare",
    "prepublish",
    "prepublishOnly",
    "prepack",
    "postpack",
    "publish",
    "postpublish",
    "preuninstall",
    "postuninstall",
}

# Version range markers that must never appear in dependency declarations.
VERSION_RANGE_MARKERS = {"^", "~", ">", "<", "|", "*", "x"}


def _load_package_json() -> dict:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


def _load_tsconfig() -> dict:
    return json.loads(TSCONFIG.read_text(encoding="utf-8"))


def _exact(value: str) -> bool:
    return not any(marker in value for marker in VERSION_RANGE_MARKERS)


# --- package.json identity and preserved contracts ---


def test_package_json_exists() -> None:
    assert PACKAGE_JSON.exists(), f"Missing: {PACKAGE_JSON}"


def test_package_json_is_valid_json() -> None:
    assert isinstance(_load_package_json(), dict), (
        "package.json root must be a JSON object"
    )


def test_package_json_identity_preserved() -> None:
    pkg = _load_package_json()
    assert pkg.get("name") == NAME, f"name must be {NAME}"
    assert pkg.get("private") is True, "package.json must declare private: true"
    assert pkg.get("version") == "0.0.0", "package version must be 0.0.0"
    assert pkg.get("type") == "module", "package.json must declare type: module"


def test_package_json_dependencies_exact_pixi() -> None:
    pkg = _load_package_json()
    deps = pkg.get("dependencies", {})
    assert set(deps.keys()) == {"pixi.js"}, (
        f"dependencies must contain only pixi.js, got {set(deps.keys())}"
    )
    assert deps["pixi.js"] == PIXI_EXACT, (
        f"pixi.js version must be {PIXI_EXACT}, got {deps['pixi.js']}"
    )


def test_package_json_no_devdependencies_pixi() -> None:
    pkg = _load_package_json()
    dev_deps = pkg.get("devDependencies", {})
    assert "pixi.js" not in dev_deps, "pixi.js must not be in devDependencies"


def test_package_json_dev_dependencies_exact() -> None:
    pkg = _load_package_json()
    dev_deps = pkg.get("devDependencies", {})
    assert dev_deps.get("vite") == VITE_EXACT, (
        f"vite devDependency must be {VITE_EXACT}, got {dev_deps.get('vite')}"
    )
    assert dev_deps.get("typescript") == TYPESCRIPT_EXACT, (
        f"typescript devDependency must be {TYPESCRIPT_EXACT}, "
        f"got {dev_deps.get('typescript')}"
    )


def test_package_json_no_lifecycle_scripts() -> None:
    pkg = _load_package_json()
    scripts = pkg.get("scripts", {})
    found = LIFECYCLE_SCRIPT_KEYS & set(scripts.keys())
    assert not found, f"Prohibited lifecycle scripts found: {found}"


def test_package_json_exact_versions_only() -> None:
    """All declared dependency versions are exact (no range markers)."""
    pkg = _load_package_json()
    declared = {
        **pkg.get("dependencies", {}),
        **pkg.get("devDependencies", {}),
    }
    assert declared, "expected at least one declared dependency"
    for dep, version in declared.items():
        assert _exact(version), (
            f"{dep} version {version!r} must be exact (no range markers)"
        )


# --- package-manager and engine contract ---


def test_package_manager_pnpm_pinned() -> None:
    pkg = _load_package_json()
    pm = pkg.get("packageManager", "")
    assert pm.startswith(f"pnpm@{PNPM}"), (
        f"packageManager must start with pnpm@{PNPM}, got {pm!r}"
    )


def test_engines_exact() -> None:
    pkg = _load_package_json()
    engines = pkg.get("engines", {})
    assert engines.get("node") == NODE_EXACT, (
        f"node engine must be {NODE_EXACT}, got {engines.get('node')}"
    )
    assert engines.get("pnpm") == PNPM, (
        f"pnpm engine must be {PNPM}, got {engines.get('pnpm')}"
    )


# --- Runtime-independent static config contract ---


def test_node_version_file() -> None:
    content = NODE_VERSION.read_text(encoding="utf-8").strip()
    assert content == NODE_EXACT, (
        f".node-version must contain exactly {NODE_EXACT}, got {content!r}"
    )


def test_npmrc_required_settings() -> None:
    text = NPMRC.read_text(encoding="utf-8")
    assert "engine-strict=true" in text, ".npmrc must set engine-strict=true"
    assert "save-exact=true" in text, ".npmrc must set save-exact=true"


def test_npmrc_no_credentials() -> None:
    text = NPMRC.read_text(encoding="utf-8")
    credential_markers = ("_authToken", "@registry", "always-auth", "//")
    for marker in credential_markers:
        assert marker not in text, f".npmrc must not contain credential {marker!r}"


def test_tsconfig_valid_json() -> None:
    cfg = _load_tsconfig()
    assert isinstance(cfg, dict), "tsconfig.json root must be a JSON object"


def test_tsconfig_baseline_options() -> None:
    cfg = _load_tsconfig()
    opts = cfg.get("compilerOptions", {})
    assert opts.get("allowJs") is True, "tsconfig must set allowJs: true"
    assert opts.get("checkJs") is False, "tsconfig must set checkJs: false"
    assert opts.get("noEmit") is True, "tsconfig must set noEmit: true"


def test_tsconfig_includes_source_with_exclusions() -> None:
    cfg = _load_tsconfig()
    assert "src/**/*.js" in cfg.get("include", []), "tsconfig must include src/**/*.js"
    exclusions = cfg.get("exclude", [])
    assert "src/vendor/**" in exclusions, "tsconfig must exclude src/vendor/**"
    assert "src/render-assets.generated.js" in exclusions, (
        "tsconfig must exclude src/render-assets.generated.js"
    )


# --- Lockfile and authority contract ---


def test_pnpm_lock_exists() -> None:
    assert PNPM_LOCK.exists(), f"Missing pnpm lockfile: {PNPM_LOCK}"


def test_pnpm_lock_pins_pixi() -> None:
    text = PNPM_LOCK.read_text(encoding="utf-8")
    assert "pixi.js@8.19.0" in text, "pnpm-lock.yaml must pin pixi.js@8.19.0"


def test_package_lock_removed() -> None:
    assert not PACKAGE_LOCK.exists(), (
        "package-lock.json must be removed (pnpm is the authority)"
    )


def test_no_competing_lockfiles() -> None:
    competing = [
        DOMAIN_DIR / "yarn.lock",
        DOMAIN_DIR / "bun.lock",
        DOMAIN_DIR / "bun.lockb",
        REPO_ROOT / "pnpm-lock.yaml",
        REPO_ROOT / "package-lock.json",
        REPO_ROOT / "yarn.lock",
        REPO_ROOT / "bun.lock",
        REPO_ROOT / "bun.lockb",
        REPO_ROOT / "package.json",
    ]
    for path in competing:
        assert not path.exists(), f"Competing lock/package file found: {path}"


# --- Justfile integration contract ---


def test_justfile_has_wp10_recipes() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")
    for recipe in (
        "check-ocean-rescue-node-version:",
        "check-ocean-rescue-pnpm-version:",
        "sync-ocean-rescue-node:",
        "typecheck-ocean-rescue:",
        "check-ocean-rescue-toolchain:",
    ):
        assert recipe in text, f"Justfile must define recipe {recipe!r}"
