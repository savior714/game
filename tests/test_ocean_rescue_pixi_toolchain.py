"""Contract tests for ocean-rescue PixiJS toolchain bootstrap.

Verifies that domains/ocean-rescue/package.json and package-lock.json
exist, pin pixi.js to exact 8.19.0, and contain no prohibited metadata.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
PACKAGE_JSON = DOMAIN_DIR / "package.json"
PACKAGE_LOCK = DOMAIN_DIR / "package-lock.json"

PIXI_EXACT = "8.19.0"

SUPPORTED_LOCKFILE_VERSIONS = {1, 2, 3}


def _load_package_json() -> dict:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


def _load_package_lock() -> dict:
    return json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))


# --- package.json contract ---


def test_package_json_exists() -> None:
    assert PACKAGE_JSON.exists(), f"Missing: {PACKAGE_JSON}"


def test_package_json_is_valid_json() -> None:
    pkg = _load_package_json()
    assert isinstance(pkg, dict), "package.json root must be a JSON object"


def test_package_json_private() -> None:
    pkg = _load_package_json()
    assert pkg.get("private") is True, "package.json must declare private: true"


def test_package_json_type_module() -> None:
    pkg = _load_package_json()
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


def test_package_json_no_lifecycle_scripts() -> None:
    pkg = _load_package_json()
    scripts = pkg.get("scripts", {})
    lifecycle_keys = {
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
    found = lifecycle_keys & set(scripts.keys())
    assert not found, f"Prohibited lifecycle scripts found: {found}"


# --- package-lock.json contract ---


def test_package_lock_exists() -> None:
    assert PACKAGE_LOCK.exists(), f"Missing: {PACKAGE_LOCK}"


def test_package_lock_is_valid_json() -> None:
    lock = _load_package_lock()
    assert isinstance(lock, dict), "package-lock.json root must be a JSON object"


def test_lockfile_version_supported() -> None:
    lock = _load_package_lock()
    version = lock.get("lockfileVersion")
    assert version in SUPPORTED_LOCKFILE_VERSIONS, (
        f"lockfileVersion must be one of {SUPPORTED_LOCKFILE_VERSIONS}, got {version}"
    )


def test_lockfile_root_dependency_exact() -> None:
    lock = _load_package_lock()
    root_deps = lock.get("packages", {}).get("", {}).get("dependencies", {})
    assert root_deps.get("pixi.js") == PIXI_EXACT, (
        f"lockfile root pixi.js must be {PIXI_EXACT}, got {root_deps.get('pixi.js')}"
    )


def test_lockfile_installed_version_exact() -> None:
    lock = _load_package_lock()
    pixi_entry = (
        lock.get("packages", {}).get("node_modules/pixi.js", {})
    )
    assert pixi_entry.get("version") == PIXI_EXACT, (
        f"installed pixi.js version must be {PIXI_EXACT}, "
        f"got {pixi_entry.get('version')}"
    )


def test_lockfile_resolved_present() -> None:
    lock = _load_package_lock()
    pixi_entry = (
        lock.get("packages", {}).get("node_modules/pixi.js", {})
    )
    resolved = pixi_entry.get("resolved", "")
    assert resolved, "pixi.js resolved field must be non-empty"
    assert resolved.startswith("https://"), (
        f"resolved must be HTTPS URL, got {resolved[:60]}"
    )


def test_lockfile_integrity_present() -> None:
    lock = _load_package_lock()
    pixi_entry = (
        lock.get("packages", {}).get("node_modules/pixi.js", {})
    )
    integrity = pixi_entry.get("integrity", "")
    assert integrity, "pixi.js integrity field must be non-empty"
    assert integrity.startswith("sha"), (
        f"integrity must start with sha, got {integrity[:20]}"
    )


def test_package_json_and_lockfile_dependency_match() -> None:
    pkg = _load_package_json()
    lock = _load_package_lock()
    pkg_version = pkg.get("dependencies", {}).get("pixi.js")
    lock_version = (
        lock.get("packages", {}).get("node_modules/pixi.js", {}).get("version")
    )
    assert pkg_version == lock_version, (
        f"package.json ({pkg_version}) != lockfile ({lock_version})"
    )


def test_no_prohibited_package_manager_metadata() -> None:
    """Verify no pnpm-lock, yarn.lock, or bun.lock was introduced."""
    prohibited = [
        REPO_ROOT / "pnpm-lock.yaml",
        REPO_ROOT / "yarn.lock",
        REPO_ROOT / "bun.lock",
        REPO_ROOT / "bun.lockb",
    ]
    for path in prohibited:
        assert not path.exists(), f"Prohibited file found: {path}"
