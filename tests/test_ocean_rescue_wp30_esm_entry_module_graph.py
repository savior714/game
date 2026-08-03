"""WP-30 canonical ESM entry and module-graph contract.

WP-30 makes the ESM import graph authoritative for application dependency
ordering instead of the legacy manifest ``depends_on`` graph plus globals.
This test validates the structural contract of the canonical entry and the
temporary compatibility adapter graph:

- ``src/main.js`` is the single canonical entry, importing only ``./esm/app.js``;
- every ``src/esm/*.js`` adapter is a bounded compatibility shim that uses only
  static relative imports and exports one application namespace;
- unmigrated adapters import their direct application dependency adapters
  explicitly, side-effect-import exactly one legacy implementation file, read
  ``window.OceanRescue.<Name>``, throw when the namespace is absent, and export
  that namespace;
- migrated typed adapters import or re-export one canonical typed
  implementation, retain the temporary global ABI assertion, and must not
  import the rollback-only legacy implementation (WP-31A: only ``profile.js``);
- the module graph reachable from ``src/main.js`` is acyclic, single-rooted,
  uses only relative static imports, and covers every legacy implementation
  exactly once (nothing omitted, nothing imported twice);
- the canonical graph reaches the typed profile implementation and excludes the
  rollback-only ``src/profile.js``;
- legacy implementation files themselves import no modules (IIFE globals);
- the legacy ordered manifest is preserved as the rollback authority.

This is a static-source module-graph contract. Production cutover and
browser-parity remain downstream WP-30 verification bundled with the Vite
config change.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "src"
ESM_DIR = SRC_DIR / "esm"
MAIN_ENTRY = SRC_DIR / "main.js"
CANONICAL_MANIFEST = SRC_DIR / "build-manifest.json"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"

# Adapter file -> expected registered global (window.OceanRescue.<leaf>).
ADAPTER_NAMESPACES: Dict[str, str] = {
    "render-assets.js": "RenderAssets",
    "render-runtime.js": "RenderRuntime",
    "state.js": "State",
    "profile.js": "Profile",
    "missions.js": "Missions",
    "gups.js": "Gups",
    "launch.js": "Launch",
    "travel.js": "Travel",
    "terrain.js": "Terrain",
    "travel-scene.js": "TravelScene",
    "rescue.js": "Rescue",
    "sea-turtle.js": "SeaTurtle",
    "sea-turtle-scene.js": "SeaTurtleScene",
    "crab.js": "Crab",
    "crab-scene.js": "CrabScene",
    "young-whale.js": "YoungWhale",
    "mission-success.js": "MissionSuccess",
    "app.js": "App",
}

# Unmigrated adapter file -> legacy implementation file it side-effect imports.
ADAPTER_LEGACY_FILE: Dict[str, str] = {
    "render-assets.js": "render-assets.generated.js",
    "render-runtime.js": "render-runtime.js",
    "state.js": "state.js",
    "missions.js": "missions.js",
    "gups.js": "gups.js",
    "launch.js": "launch.js",
    "travel.js": "travel.js",
    "terrain.js": "terrain.js",
    "travel-scene.js": "travel-scene.js",
    "rescue.js": "rescue.js",
    "sea-turtle.js": "sea-turtle.js",
    "sea-turtle-scene.js": "sea-turtle-scene.js",
    "crab.js": "crab.js",
    "crab-scene.js": "crab-scene.js",
    "young-whale.js": "young-whale.js",
    "mission-success.js": "mission-success.js",
    "app.js": "app.js",
}

# Migrated typed adapter file -> canonical typed implementation it re-exports.
# WP-31A migrates only the profile module; the typed implementation must not
# import the rollback-only legacy `src/profile.js`.
MIGRATED_ADAPTER_TYPED_FILE: Dict[str, str] = {
    "profile.js": "profile/profile.ts",
}

# Rollback-only legacy implementation retained for the legacy manifest graph.
LEGACY_ROLLBACK_PROFILE_FILE = "profile.js"

# Adapter file -> set of adapter dependency files it must import explicitly.
ADAPTER_DEPS: Dict[str, Set[str]] = {
    "render-assets.js": set(),
    "render-runtime.js": {"render-assets.js"},
    "state.js": set(),
    "profile.js": set(),
    "missions.js": set(),
    "gups.js": set(),
    "launch.js": set(),
    "travel.js": set(),
    "terrain.js": set(),
    "travel-scene.js": {"render-runtime.js", "terrain.js", "gups.js"},
    "rescue.js": set(),
    "sea-turtle.js": set(),
    "sea-turtle-scene.js": {"render-runtime.js", "sea-turtle.js"},
    "crab.js": set(),
    "crab-scene.js": {"render-runtime.js", "crab.js"},
    "young-whale.js": set(),
    "mission-success.js": set(),
    "app.js": {
        "state.js",
        "render-runtime.js",
        "profile.js",
        "missions.js",
        "gups.js",
        "launch.js",
        "travel.js",
        "terrain.js",
        "rescue.js",
        "sea-turtle.js",
        "sea-turtle-scene.js",
        "crab.js",
        "travel-scene.js",
        "crab-scene.js",
        "young-whale.js",
        "mission-success.js",
    },
}

STATE_WHITE, STATE_GRAY, STATE_BLACK = 0, 1, 2


def _rel(path: Path) -> str:
    return path.resolve().relative_to(SRC_DIR).as_posix()


# Matches both side-effect imports (`import "x";`) and named imports
# (`import { A } from "x";`) with static string specifiers.
_IMPORT_SPECIFIER_RE = re.compile(
    r"^import\s+(?:\{[^}]*\}\s*from\s+)?[\"']([^\"']+)[\"']\s*;?\s*$"
)


def _static_imports(path: Path) -> List[Tuple[int, str]]:
    """Return (line_number, specifier) for pure static string imports."""
    out: List[Tuple[int, str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = _IMPORT_SPECIFIER_RE.match(raw.strip())
        if m:
            out.append((lineno, m.group(1)))
    return out


def _resolve(root_file: Path, spec: str) -> Path:
    base = (root_file.parent / spec).resolve()
    if base.is_file():
        return base
    for ext in (".ts", ".js"):
        candidate = Path(str(base) + ext)
        if candidate.is_file():
            return candidate
    return base


def _basename(key: str) -> str:
    return key.rsplit("/", 1)[-1]


def _build_graph() -> Tuple[Set[str], Dict[str, Set[str]]]:
    """Static transitive dep graph over modules reachable from main.js."""
    edges: Dict[str, Set[str]] = {}
    stack: List[Path] = [MAIN_ENTRY]
    while stack:
        cur = stack.pop()
        key = _rel(cur)
        if key in edges:
            continue
        edges[key] = set()
        for _, spec in _static_imports(cur):
            dep_key = _rel(_resolve(cur, spec))
            edges[key].add(dep_key)
            if dep_key not in edges:
                stack.append(SRC_DIR / dep_key)
    return set(edges), edges


# --- canonical entry ---


def test_main_entry_is_single_canonical_root() -> None:
    assert MAIN_ENTRY.exists(), "src/main.js missing"
    imports = _static_imports(MAIN_ENTRY)
    assert len(imports) == 1, f"main.js must import exactly one module, got {imports}"
    assert imports[0][1] == "./esm/app.js", (
        f"main.js must import ./esm/app.js, got {imports[0][1]}"
    )


# --- adapter shape ---


def test_adapter_directory_matches_expected_set() -> None:
    actual = {p.name for p in ESM_DIR.glob("*.js")}
    expected = set(ADAPTER_NAMESPACES)
    assert actual == expected, (
        f"esm/ adapter set mismatch; missing "
        f"{sorted(expected - actual)} / unexpected {sorted(actual - expected)}"
    )


def test_adapters_use_only_static_relative_imports() -> None:
    for name in sorted(ADAPTER_NAMESPACES):
        lines = (ESM_DIR / name).read_text(encoding="utf-8").splitlines()
        for lineno, raw in enumerate(lines, 1):
            stripped = raw.strip()
            if not stripped.startswith("import"):
                continue
            m = _IMPORT_SPECIFIER_RE.match(stripped)
            assert m, f"{name}:{lineno} invalid import: {stripped!r}"
            spec = m.group(1)
            assert spec.startswith(("./", "../")), (
                f"{name}:{lineno} must use a relative import, got {spec!r}"
            )
            assert not spec.startswith("/"), f"{name}:{lineno} absolute import {spec!r}"


def test_unmigrated_adapters_import_their_legacy_implementation_exactly_once() -> None:
    for name, legacy in ADAPTER_LEGACY_FILE.items():
        specs = [spec for _, spec in _static_imports(ESM_DIR / name)]
        legacy_resolved = _rel(SRC_DIR / legacy)
        count = sum(
            1 for s in specs if _rel(_resolve(ESM_DIR / name, s)) == legacy_resolved
        )
        assert count == 1, (
            f"{name} must import its legacy implementation exactly once "
            f"({legacy}), got {count}"
        )


def test_migrated_adapters_import_one_typed_implementation_only() -> None:
    legacy_resolved = {
        _rel(SRC_DIR / legacy) for legacy in ADAPTER_LEGACY_FILE.values()
    }
    for name, typed in MIGRATED_ADAPTER_TYPED_FILE.items():
        specs = [spec for _, spec in _static_imports(ESM_DIR / name)]
        resolved = [_rel(_resolve(ESM_DIR / name, s)) for s in specs]
        typed_resolved = _rel(SRC_DIR / typed)
        assert resolved.count(typed_resolved) == 1, (
            f"{name} must import the typed implementation exactly once "
            f"({typed}), got {resolved}"
        )
        assert not (set(resolved) & legacy_resolved), (
            f"{name} must not import a rollback-only legacy implementation"
        )


def test_each_adapter_has_namespace_guard_and_export() -> None:
    for name, leaf in ADAPTER_NAMESPACES.items():
        text = (ESM_DIR / name).read_text(encoding="utf-8")
        reader = re.search(
            r"const\s+(\w+)\s*=\s*window\.OceanRescue\?\.(\w+)\s*;", text
        )
        assert reader, f"{name} must read window.OceanRescue?.{leaf}"
        var, read_leaf = reader.group(1), reader.group(2)
        assert read_leaf == leaf, f"{name}: expected namespace {leaf}, read {read_leaf}"
        assert f'throw new Error("OceanRescue.{leaf} was not registered")' in text, (
            f"{name}: missing absent-namespace throw guard"
        )
        if name in MIGRATED_ADAPTER_TYPED_FILE:
            import_match = re.search(
                r"^import\s+\{\s*(\w+)\s*\}\s*from\s+[\"']([^\"']+)[\"']\s*;\s*$",
                text,
                re.MULTILINE,
            )
            assert import_match, f"{name}: missing typed implementation import"
            export_name = import_match.group(1)
            assert f"export {{ {export_name} }};" in text, (
                f"{name}: missing named re-export {export_name}"
            )
            assert (
                f"{export_name} !== {var}" in text or f"{var} !== {export_name}" in text
            ), f"{name}: missing global ABI identity assertion"
        else:
            assert f"export {{ {var} }};" in text, f"{name}: missing named export {var}"


# --- adapter dependency edges ---


def test_each_adapter_imports_all_direct_dependencies() -> None:
    for name, expected in ADAPTER_DEPS.items():
        specs = [spec for _, spec in _static_imports(ESM_DIR / name)]
        adapter_imports = {
            _basename(_rel(_resolve(ESM_DIR / name, s)))
            for s in specs
            if s.startswith("./") and s != "./" + name
        }
        assert adapter_imports == expected, (
            f"{name}: adapter dependency mismatch, expected {sorted(expected)}, "
            f"got {sorted(adapter_imports)}"
        )


def test_no_adapter_duplicate_or_bare_imports() -> None:
    for name in sorted(ADAPTER_NAMESPACES):
        specs = [spec for _, spec in _static_imports(ESM_DIR / name)]
        assert len(specs) == len(set(specs)), f"{name}: duplicate imports"
        for spec in specs:
            assert spec.startswith(("./", "../")), f"{name}: bare import {spec!r}"


# --- import-graph properties ---


def test_graph_is_acyclic() -> None:
    nodes, edges = _build_graph()
    color: Dict[str, int] = {}

    def visit(n: str, stack: List[str]) -> None:
        color[n] = STATE_GRAY
        stack.append(n)
        for m in edges.get(n, ()):
            if color.get(m) == STATE_GRAY:
                cycle = stack[stack.index(m) :] + [m]
                raise AssertionError(f"import cycle: {' -> '.join(cycle)}")
            if color.get(m) != STATE_BLACK:
                visit(m, stack)
        stack.pop()
        color[n] = STATE_BLACK

    for n in nodes:
        if color.get(n) != STATE_BLACK:
            visit(n, [])


def test_graph_reaches_every_adapter_from_main() -> None:
    nodes, _ = _build_graph()
    adapter_keys = {f"esm/{name}" for name in ADAPTER_NAMESPACES}
    missing = adapter_keys - nodes
    assert not missing, f"adapters unreachable from main.js: {sorted(missing)}"


def test_graph_uses_only_static_relative_imports() -> None:
    nodes, _ = _build_graph()
    for node in nodes:
        for _, spec in _static_imports(SRC_DIR / node):
            assert spec.startswith(("./", "../")), (
                f"{node} uses non-relative import {spec!r}"
            )


def test_implementation_modules_import_nothing() -> None:
    """Neither legacy implementations nor typed leaf modules import modules."""
    nodes, edges = _build_graph()
    for key, deps in sorted(edges.items()):
        if key.startswith("esm/") or key == "main.js":
            continue
        assert not deps, f"implementation module {key} must not import: {sorted(deps)}"


def test_canonical_graph_reaches_typed_profile_implementation() -> None:
    nodes, edges = _build_graph()
    for name, typed in MIGRATED_ADAPTER_TYPED_FILE.items():
        typed_key = _rel(SRC_DIR / typed)
        assert typed_key in nodes, f"{typed} is not reachable from main.js"
        adapter_key = f"esm/{name}"
        assert typed_key in edges.get(adapter_key, set()), (
            f"{name} adapter must reach {typed}"
        )
        assert edges.get(typed_key) == set(), "typed profile module must be a leaf"


def test_canonical_graph_excludes_rollback_profile_js() -> None:
    nodes, _ = _build_graph()
    rollback_key = _rel(SRC_DIR / LEGACY_ROLLBACK_PROFILE_FILE)
    assert rollback_key not in nodes, (
        "rollback-only legacy profile.js must not be in the canonical graph"
    )


# --- exactly-once coverage ---


def test_every_legacy_implementation_covered_exactly_once() -> None:
    nodes, edges = _build_graph()
    legacy_targets = set(ADAPTER_LEGACY_FILE.values())
    count: Counter = Counter()
    for src, deps in edges.items():
        for dep in deps:
            if dep.startswith("esm/"):
                continue
            if _basename(dep) in legacy_targets:
                count[_basename(dep)] += 1
    for target in sorted(legacy_targets):
        assert count[target] == 1, (
            f"legacy implementation {target} imported {count[target]} times "
            f"(expected exactly once)"
        )


def test_legacy_graph_has_lower_boundary_matching_adapter_targets() -> None:
    """No module outside src/ is reachable, and vendor and CSS stay out."""
    nodes, _ = _build_graph()
    for key in nodes:
        assert not key.startswith("../"), f"graph escapes src root: {key}"
        assert "/vendor/" not in key, f"vendored file reached in graph: {key}"


# --- manifest ownership ---


def test_canonical_manifest_is_contracted_to_vendor_entry_and_pins() -> None:
    data = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    assert set(data.keys()) == {
        "template",
        "styles",
        "vendor",
        "generated",
        "entry",
        "assets",
    }, f"canonical manifest keys changed: {sorted(data)}"
    assert "scripts" not in data, (
        "canonical manifest must not carry an ordered scripts list"
    )
    assert data["entry"] == "main.js", "canonical entry must be main.js"
    assert isinstance(data["vendor"], dict)
    assert data["vendor"]["kind"] == "vendor"
    assert len(data["vendor"]["sha256"]) == 64
    assert isinstance(data["generated"], dict)
    assert len(data["generated"]["sha256"]) == 64


def test_legacy_manifest_preserved_as_full_ordered_set() -> None:
    data = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    legacy_names = {e["file"] for e in data["scripts"]}
    assert len(data["scripts"]) >= len(legacy_names)
    assert "scripts" in data, "legacy manifest must retain the ordered scripts list"
    assert any(e["kind"] == "vendor" for e in data["scripts"]), (
        "legacy manifest must retain the vendored Pixi entry"
    )
    assert "vendor" not in data, (
        "legacy manifest must not adopt the canonical vendor key"
    )
    for key in ("entry", "generated"):
        assert key not in data, f"legacy manifest must not carry '{key}'"
    assert len(data["scripts"]) == 19, (
        "legacy manifest must keep the 19 ordered entries"
    )
    assert data["scripts"][-1]["file"] == "app.js", (
        "legacy manifest must end with app.js in canonical order"
    )
    assert data["scripts"][0]["kind"] == "vendor", (
        "legacy manifest must start with the vendored Pixi entry"
    )


def test_canonical_scripts_are_all_recorded_in_legacy_manifest() -> None:
    data = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    legacy_files = {e["file"] for e in data["scripts"]}
    expected_legacy = set(ADAPTER_LEGACY_FILE.values()) | {LEGACY_ROLLBACK_PROFILE_FILE}
    for raw in expected_legacy:
        assert raw in legacy_files, f"legacy manifest missing implementation file {raw}"
    assert "main.js" not in legacy_files, (
        "legacy manifest must not reference the ESM entry main.js"
    )
    assert LEGACY_ROLLBACK_PROFILE_FILE in legacy_files, (
        "legacy manifest must retain the rollback-only profile.js entry"
    )
