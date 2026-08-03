#!/usr/bin/env python3
"""Ocean Rescue single-HTML builder.

Consumes a JSON build manifest, an HTML template, CSS and JS source files,
and binary assets, then produces a standalone HTML file with all content
inlined as data URIs.

Two manifest authorities exist (WP-30):

- ``build-manifest.json`` is the contracted canonical manifest: template,
  styles, a single vendored Pixi entry, the generated-assets pin, the ESM
  entry file, and assets. Production packaging consumes this.
- ``build-manifest.legacy.json`` is the immutable ordered-script rollback
  manifest. ``--mode legacy`` consumes this to reproduce the pre-cutover
  ordered-script artifact.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SUPPORTED_ASSETS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".woff2": "font/woff2",
}

MARKER_CSS = "<!-- OCEAN_RESCUE_CSS -->"
MARKER_SCRIPTS = "<!-- OCEAN_RESCUE_SCRIPTS -->"

# Canonical Vite production application-bundle boundary (WP-21).
PRODUCTION_BUNDLE_FILE = "ocean-rescue-app.js"
PRODUCTION_METADATA_FILE = "production-bundle-metadata.json"
PRODUCTION_METADATA_STATE = "PRODUCTION_BUNDLE"

# Default rollback manifest next to the canonical manifest (WP-30).
LEGACY_MANIFEST_FILE = "build-manifest.legacy.json"

ASSET_REF_RE = re.compile(r"asset://([a-zA-Z0-9_-]+)")

VALID_KINDS = {"app", "vendor", "generated-assets"}

JS_FORBIDDEN_PATTERNS = [
    (re.compile(r"\bimport\s*\{"), "static import declaration (named)"),
    (re.compile(r'\bimport\s+["\']'), "static import declaration (string)"),
    (re.compile(r"\bimport\s+\*\s+as\s+"), "static import declaration (namespace)"),
    (re.compile(r"\bimport\s+\w+\s+from\s+"), "static import declaration (default)"),
    (re.compile(r"\bexport\s+"), "export declaration"),
    (re.compile(r"\bimport\s*\("), "dynamic import()"),
]

GENERATED_ASSETS_FORBIDDEN_PATTERNS = [
    (re.compile(r"\bimport\s*\("), "dynamic import()"),
    (re.compile(r"\bfetch\s*\("), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\bWebSocket\b"), "WebSocket"),
    (re.compile(r"\bEventSource\b"), "EventSource"),
    (re.compile(r"\bPIXI\b"), "PIXI API call"),
    (re.compile(r"\beval\s*\("), "eval()"),
    (re.compile(r"\bFunction\s*\("), "Function constructor"),
]

JS_SAFETY_PATTERNS = [
    (re.compile(r"</script", re.IGNORECASE), 'contains "</script"'),
    (re.compile(r"<script[\s>]", re.IGNORECASE), 'contains "<script"'),
    (re.compile(r"<!--"), 'contains "<!--"'),
]

RUNTIME_NETWORK_PATTERNS = [
    (re.compile(r"\bimport\s*\("), "dynamic import()"),
    (re.compile(r"\bfetch\s*\("), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\bWebSocket\b"), "WebSocket"),
    (re.compile(r"\bEventSource\b"), "EventSource"),
]


class BuildError(Exception):
    """Build contract violation."""


def die(message, exit_code=1):
    """Print error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def load_manifest(path):
    """Load and validate a build manifest.

    Accepts both authorities:

    - contracted canonical (WP-30): ``template``, ``styles``, ``vendor``,
      ``generated``, ``entry``, ``assets``;
    - ordered legacy rollback: ``template``, ``styles``, ``scripts``, ``assets``.
    """
    if not path.exists():
        raise BuildError(f"Manifest not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BuildError(f"Invalid JSON in manifest: {e}")

    if not isinstance(data, dict):
        raise BuildError("Manifest must be a JSON object")

    allowed_keys = {"template", "styles", "scripts", "vendor", "generated", "entry", "assets"}
    unknown = set(data.keys()) - allowed_keys
    if unknown:
        raise BuildError(f"Unknown manifest key(s): {', '.join(sorted(unknown))}")

    if "template" not in data:
        raise BuildError("Missing required manifest key: template")
    if "styles" not in data:
        raise BuildError("Missing required manifest key: styles")
    if "assets" not in data:
        data = dict(data)
        data["assets"] = []

    has_scripts = "scripts" in data
    has_entry = "entry" in data
    has_vendor = "vendor" in data
    if has_scripts == has_entry:
        raise BuildError(
            "Manifest must declare exactly one of 'scripts' (legacy) or "
            "'entry' (canonical), found scripts=%s entry=%s"
            % (has_scripts, has_entry)
        )
    if has_entry and not has_vendor:
        raise BuildError("Canonical manifest requires a 'vendor' entry")
    if has_scripts and (has_vendor or "generated" in data):
        raise BuildError(
            "Legacy manifest must not carry canonical 'vendor'/'generated' keys"
        )
    if has_entry:
        if "generated" not in data:
            raise BuildError("Canonical manifest requires a 'generated' pin")

    _validate_manifest_types(data)

    _validate_styles(data)
    if has_scripts:
        _validate_scripts(data)
    if has_vendor:
        _validate_vendor(data)
    _validate_manifest_assets(data)

    return data


def _validate_vendor(data):
    vendor = data["vendor"]
    if not isinstance(vendor, dict):
        raise BuildError("manifest.vendor must be an object")
    allowed = {"file", "namespace", "kind", "sha256"}
    unknown = set(vendor.keys()) - allowed
    if unknown:
        raise BuildError(
            f"manifest.vendor unknown key(s): {', '.join(sorted(unknown))}"
        )
    for key in ("file", "namespace", "kind", "sha256"):
        if key not in vendor:
            raise BuildError(f"manifest.vendor missing required key: {key}")
        if not isinstance(vendor[key], str):
            raise BuildError(f"manifest.vendor.{key} must be a string")
    if vendor["kind"] != "vendor":
        raise BuildError("manifest.vendor.kind must be 'vendor'")
    if len(vendor["sha256"]) != 64:
        raise BuildError("manifest.vendor.sha256 must be 64 hex chars")

    generated = data.get("generated")
    if not isinstance(generated, dict):
        raise BuildError("manifest.generated must be an object")
    for key in ("file", "sha256"):
        if key not in generated:
            raise BuildError(f"manifest.generated missing required key: {key}")
        if not isinstance(generated[key], str):
            raise BuildError(f"manifest.generated.{key} must be a string")
    if len(generated["sha256"]) != 64:
        raise BuildError("manifest.generated.sha256 must be 64 hex chars")

    entry = data.get("entry")
    if not isinstance(entry, str) or not entry:
        raise BuildError("manifest.entry must be a non-empty string")


def _validate_manifest_types(data):
    if not isinstance(data["template"], str):
        raise BuildError("manifest.template must be a string")
    styles = data["styles"]
    if not isinstance(styles, list):
        raise BuildError("manifest.styles must be an array")
    for i, s in enumerate(styles):
        if not isinstance(s, str):
            raise BuildError(f"manifest.styles[{i}] must be a string")
    if "scripts" in data:
        scripts = data["scripts"]
        if not isinstance(scripts, list):
            raise BuildError("manifest.scripts must be an array")
        for i, entry in enumerate(scripts):
            if not isinstance(entry, dict):
                raise BuildError(f"manifest.scripts[{i}] must be an object")
    if "assets" in data:
        if not isinstance(data["assets"], list):
            raise BuildError("manifest.assets must be an array")
        for i, entry in enumerate(data["assets"]):
            if not isinstance(entry, dict):
                raise BuildError(f"manifest.assets[{i}] must be an object")


def _validate_styles(data):
    pass


def _validate_scripts(data):
    allowed_keys = {"file", "namespace", "depends_on", "kind", "sha256"}
    seen_namespaces = set()
    for i, entry in enumerate(data["scripts"]):
        unknown = set(entry.keys()) - allowed_keys
        if unknown:
            raise BuildError(
                f"manifest.scripts[{i}] unknown key(s): {', '.join(sorted(unknown))}"
            )
        if "file" not in entry:
            raise BuildError(f"manifest.scripts[{i}] missing required key: file")
        if "namespace" not in entry:
            raise BuildError(f"manifest.scripts[{i}] missing required key: namespace")
        if not isinstance(entry["file"], str):
            raise BuildError(f"manifest.scripts[{i}].file must be a string")
        if not isinstance(entry["namespace"], str):
            raise BuildError(f"manifest.scripts[{i}].namespace must be a string")
        ns = entry["namespace"]
        if ns in seen_namespaces:
            raise BuildError(f"Duplicate namespace: {ns}")
        seen_namespaces.add(ns)

        kind = entry.get("kind", "app")
        if kind not in VALID_KINDS:
            raise BuildError(
                f"manifest.scripts[{i}].kind must be one of {sorted(VALID_KINDS)}, "
                f"got '{kind}'"
            )

        if kind in ("vendor", "generated-assets"):
            if "sha256" not in entry:
                raise BuildError(
                    f"manifest.scripts[{i}] with kind '{kind}' must have 'sha256'"
                )
            if not isinstance(entry["sha256"], str):
                raise BuildError(f"manifest.scripts[{i}].sha256 must be a string")
            if len(entry["sha256"]) != 64:
                raise BuildError(f"manifest.scripts[{i}].sha256 must be 64 hex chars")

        if "depends_on" in entry:
            deps = entry["depends_on"]
            if not isinstance(deps, list):
                raise BuildError(f"manifest.scripts[{i}].depends_on must be an array")
            for j, d in enumerate(deps):
                if not isinstance(d, str):
                    raise BuildError(
                        f"manifest.scripts[{i}].depends_on[{j}] must be a string"
                    )


def _validate_manifest_assets(data):
    if "assets" not in data:
        return
    allowed_keys = {"id", "file", "mime"}
    seen_ids = set()
    for i, entry in enumerate(data["assets"]):
        unknown = set(entry.keys()) - allowed_keys
        if unknown:
            raise BuildError(
                f"manifest.assets[{i}] unknown key(s): {', '.join(sorted(unknown))}"
            )
        if "id" not in entry:
            raise BuildError(f"manifest.assets[{i}] missing required key: id")
        if "file" not in entry:
            raise BuildError(f"manifest.assets[{i}] missing required key: file")
        if "mime" not in entry:
            raise BuildError(f"manifest.assets[{i}] missing required key: mime")
        if not isinstance(entry["id"], str):
            raise BuildError(f"manifest.assets[{i}].id must be a string")
        if not isinstance(entry["file"], str):
            raise BuildError(f"manifest.assets[{i}].file must be a string")
        if not isinstance(entry["mime"], str):
            raise BuildError(f"manifest.assets[{i}].mime must be a string")
        aid = entry["id"]
        if aid in seen_ids:
            raise BuildError(f"Duplicate asset ID: {aid}")
        seen_ids.add(aid)


def resolve_manifest_path(base, file_path):
    """Resolve a file path relative to the manifest directory."""
    p = Path(file_path)
    if p.is_absolute():
        raise BuildError(f"Absolute path not allowed: {file_path}")
    if ".." in p.parts:
        raise BuildError(f"Path traversal not allowed: {file_path}")

    candidate = (base / file_path).resolve()
    source_root = base.resolve()

    try:
        candidate.relative_to(source_root)
    except ValueError:
        raise BuildError(f"Path escapes source root: {file_path}")

    if not candidate.exists():
        raise BuildError(f"File not found: {file_path}")

    return candidate


def validate_template(template_path):
    """Validate and return the template content."""
    content = template_path.read_text(encoding="utf-8")

    stripped = content.strip()
    if not stripped.lower().startswith("<!doctype html"):
        raise BuildError("Template must start with <!doctype html>")

    if re.search(r"<script\s+[^>]*src\s*=", content, re.IGNORECASE):
        raise BuildError("Template must not contain external <script src>")

    link_stylesheet = re.compile(
        r'<link[^>]*rel=["\']stylesheet["\'][^>]*href\s*=',
        re.IGNORECASE,
    )
    if link_stylesheet.search(content):
        raise BuildError("Template must not contain external stylesheet <link>")

    if re.search(r"<script[\s>]", content, re.IGNORECASE):
        raise BuildError(
            "Template must not contain inline scripts outside designated markers"
        )
    if "</script>" in content.lower():
        raise BuildError(
            "Template must not contain inline scripts outside designated markers"
        )

    css_count = content.count(MARKER_CSS)
    script_count = content.count(MARKER_SCRIPTS)

    if css_count == 0:
        raise BuildError("Missing CSS marker in template")
    if css_count > 1:
        raise BuildError("Duplicate CSS marker in template")
    if script_count == 0:
        raise BuildError("Missing script marker in template")
    if script_count > 1:
        raise BuildError("Duplicate script marker in template")

    return content


def validate_js_source(script_path, content, kind="app"):
    """Validate JavaScript source file content."""
    if kind == "vendor":
        for pattern, desc in JS_SAFETY_PATTERNS:
            if pattern.search(content):
                raise BuildError(f"Vendor script {script_path.name} {desc}")
        return

    if kind == "generated-assets":
        for pattern, desc in GENERATED_ASSETS_FORBIDDEN_PATTERNS:
            if pattern.search(content):
                raise BuildError(
                    f"Generated assets script {script_path.name} contains {desc}"
                )
        for pattern, desc in JS_SAFETY_PATTERNS:
            if pattern.search(content):
                raise BuildError(f"Generated assets script {script_path.name} {desc}")
        return

    for pattern, desc in JS_FORBIDDEN_PATTERNS:
        if pattern.search(content):
            raise BuildError(f"Script {script_path.name} contains forbidden {desc}")

    for pattern, desc in JS_SAFETY_PATTERNS:
        if pattern.search(content):
            raise BuildError(f"Script {script_path.name} {desc}")

    if ASSET_REF_RE.search(content):
        raise BuildError(f"Script {script_path.name} contains asset:// reference")


def validate_dependencies(scripts):
    """Validate script dependencies."""
    namespaces = {e["namespace"]: i for i, e in enumerate(scripts)}

    for i, entry in enumerate(scripts):
        for dep in entry.get("depends_on", []):
            if dep not in namespaces:
                raise BuildError(
                    f"Script '{entry['namespace']}' depends on unknown namespace: {dep}"
                )
            dep_idx = namespaces[dep]
            if dep_idx >= i:
                raise BuildError(
                    f"Forward dependency: '{entry['namespace']}' "
                    f"depends on '{dep}' which appears after it "
                    f"in manifest order"
                )


def encode_asset(asset_path, mime_type):
    """Encode an asset file as a data URI."""
    data = asset_path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def validate_asset_mime(file_path, declared_mime):
    """Validate that declared MIME matches the file extension."""
    ext = file_path.suffix.lower()
    expected = SUPPORTED_ASSETS.get(ext)
    if expected is None:
        raise BuildError(f"Unsupported asset extension: {ext} for {file_path.name}")
    if expected != declared_mime:
        raise BuildError(
            f"MIME mismatch for {file_path.name}: "
            f"declared '{declared_mime}', "
            f"expected '{expected}' for extension '{ext}'"
        )


def collect_assets(manifest_data, manifest_base):
    """Collect and encode all assets. Returns {id: (data_uri,)}."""
    assets = {}
    for entry in manifest_data.get("assets", []):
        asset_id = entry["id"]
        file_rel = entry["file"]
        mime = entry["mime"]

        asset_path = resolve_manifest_path(manifest_base, file_rel)
        validate_asset_mime(asset_path, mime)

        data_uri = encode_asset(asset_path, mime)
        assets[asset_id] = (data_uri,)

    return assets


def resolve_asset_references(content, assets, context=""):
    """Replace asset:// sentinels with data URIs."""

    def replacer(match):
        asset_id = match.group(1)
        if asset_id not in assets:
            raise BuildError(f"Unresolved asset://{asset_id} reference")
        return assets[asset_id][0]

    return ASSET_REF_RE.sub(replacer, content)


def validate_no_runtime_network(output, script_entries=None):
    """Validate the generated output has no runtime network dependencies."""
    ext_script = re.compile(
        r"<script\s+[^>]*src\s*=",
        re.IGNORECASE,
    )
    if ext_script.search(output):
        raise BuildError("Generated output contains external <script src>")

    ext_link = re.compile(
        r'<link[^>]*rel=["\']stylesheet["\'][^>]*href\s*=',
        re.IGNORECASE,
    )
    if ext_link.search(output):
        raise BuildError("Generated output contains external stylesheet <link>")

    for attr in ["src", "poster"]:
        attr_re = re.compile(
            rf'{attr}\s*=\s*["\']((?:https?|//)[^"\']+)["\']',
            re.IGNORECASE,
        )
        for m in attr_re.finditer(output):
            raise BuildError(
                f"Generated output contains external HTML {attr}: {m.group(1)}"
            )

    srcset_re = re.compile(r'srcset\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    for m in srcset_re.finditer(output):
        val = m.group(1)
        for part in val.split(","):
            url = part.strip().split(None, 1)[0]
            if re.match(r"^(https?:|//)", url):
                raise BuildError(
                    f"Generated output contains external HTML srcset URL: {url}"
                )

    style_re = re.compile(r"<style>(.*?)</style>", re.IGNORECASE | re.DOTALL)
    for style_match in style_re.finditer(output):
        style_content = style_match.group(1)
        css_url_re = re.compile(
            r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)',
            re.IGNORECASE,
        )
        for m in css_url_re.finditer(style_content):
            url = m.group(1)
            if not url.startswith("data:") and not url.startswith("#"):
                raise BuildError(f"Generated output contains external CSS url(): {url}")

    if ASSET_REF_RE.search(output):
        raise BuildError("Generated output contains unresolved asset:// reference")

    if script_entries is None:
        return

    script_re = re.compile(r"<script>(.*?)</script>", re.IGNORECASE | re.DOTALL)
    all_scripts = script_re.findall(output)

    app_indices = [
        i for i, e in enumerate(script_entries) if e.get("kind", "app") == "app"
    ]

    for idx in app_indices:
        if idx < len(all_scripts):
            for pattern, desc in RUNTIME_NETWORK_PATTERNS:
                if pattern.search(all_scripts[idx]):
                    raise BuildError(
                        f"App script '{script_entries[idx]['namespace']}' "
                        f"contains {desc}"
                    )


def sha256_hex(data):
    """Compute SHA-256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def build(manifest_path, output_path):
    """Main build function."""
    manifest_base = manifest_path.parent.resolve()

    manifest_data = load_manifest(manifest_path)

    template_rel = manifest_data["template"]
    template_path = resolve_manifest_path(manifest_base, template_rel)
    template_content = validate_template(template_path)

    validate_dependencies(manifest_data["scripts"])

    js_contents = []
    for entry in manifest_data["scripts"]:
        script_path = resolve_manifest_path(manifest_base, entry["file"])
        content = script_path.read_text(encoding="utf-8")

        kind = entry.get("kind", "app")
        validate_js_source(script_path, content, kind)

        if kind in ("vendor", "generated-assets"):
            actual_sha = sha256_hex(content.encode("utf-8"))
            expected_sha = entry.get("sha256")
            if actual_sha != expected_sha:
                raise BuildError(
                    f"Script '{entry['namespace']}' hash mismatch: "
                    f"expected {expected_sha}, got {actual_sha}"
                )

        js_contents.append(content)

    css_contents = []
    used_assets = set()

    for match in ASSET_REF_RE.finditer(template_content):
        used_assets.add(match.group(1))

    for style_rel in manifest_data["styles"]:
        style_path = resolve_manifest_path(manifest_base, style_rel)
        css_raw = style_path.read_text(encoding="utf-8")
        for match in ASSET_REF_RE.finditer(css_raw):
            used_assets.add(match.group(1))
        css_contents.append(css_raw)

    declared_assets = {}
    for entry in manifest_data.get("assets", []):
        declared_assets[entry["id"]] = entry

    for asset_id in used_assets:
        if asset_id not in declared_assets:
            raise BuildError(f"Referenced but undeclared asset: {asset_id}")

    for asset_id in declared_assets:
        if asset_id not in used_assets:
            raise BuildError(f"Declared but unused asset: {asset_id}")

    assets = collect_assets(manifest_data, manifest_base)

    template_content = resolve_asset_references(template_content, assets, "template")

    resolved_css = []
    for css_content in css_contents:
        resolved_css.append(resolve_asset_references(css_content, assets, "css"))

    css_html = ""
    if resolved_css:
        css_html = "<style>\n" + "\n".join(resolved_css) + "\n</style>"

    scripts_html_parts = []
    for content in js_contents:
        scripts_html_parts.append("<script>\n" + content + "\n</script>")
    scripts_html = "\n".join(scripts_html_parts)

    output = template_content.replace(MARKER_CSS, css_html)
    output = output.replace(MARKER_SCRIPTS, scripts_html)

    validate_no_runtime_network(output, manifest_data["scripts"])

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_path.parent),
        prefix=".build_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(output)
        os.replace(tmp_path, output_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def atomic_write(output_path, content):
    """Atomically replace the output file with the given text content."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_path.parent),
        prefix=".build_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, output_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _load_legacy_manifest(manifest_path):
    """Load the ordered-script rollback manifest beside the canonical manifest."""
    legacy_path = manifest_path.parent / LEGACY_MANIFEST_FILE
    if not legacy_path.exists():
        raise BuildError(f"Legacy rollback manifest not found: {legacy_path}")
    return load_manifest(legacy_path)


def _load_vendor_content(manifest_base, manifest_data):
    """Load, safety-check and SHA-verify the single vendored Pixi entry."""
    vendor = manifest_data.get("vendor")
    if not isinstance(vendor, dict):
        raise BuildError("Production manifest requires a single 'vendor' object")
    if vendor.get("kind") != "vendor":
        raise BuildError("Production manifest 'vendor.kind' must be 'vendor'")
    for key in ("file", "namespace", "sha256"):
        if key not in vendor:
            raise BuildError(f"Production manifest vendor missing '{key}'")
    script_path = resolve_manifest_path(manifest_base, vendor["file"])
    content = script_path.read_text(encoding="utf-8")
    validate_js_source(script_path, content, "vendor")
    actual_sha = sha256_hex(content.encode("utf-8"))
    expected_sha = vendor.get("sha256")
    if actual_sha != expected_sha:
        raise BuildError(
            f"Vendor '{vendor['namespace']}' hash mismatch: "
            f"expected {expected_sha}, got {actual_sha}"
        )
    return content


def _validate_generated_assets_hash(manifest_base, manifest_data):
    """SHA-verify the single generated-assets pin declared in the manifest."""
    generated = manifest_data.get("generated")
    if generated is None:
        raise BuildError(
            "Production manifest requires a 'generated' generated-assets pin"
        )
    if not isinstance(generated, dict):
        raise BuildError("Production manifest 'generated' must be an object")
    if "file" not in generated or "sha256" not in generated:
        raise BuildError(
            "Production manifest 'generated' requires 'file' and 'sha256'"
        )
    script_path = resolve_manifest_path(manifest_base, generated["file"])
    content = script_path.read_text(encoding="utf-8")
    actual_sha = sha256_hex(content.encode("utf-8"))
    expected_sha = generated.get("sha256")
    if actual_sha != expected_sha:
        raise BuildError(
            f"Generated assets script '{generated['file']}' hash mismatch: "
            f"expected {expected_sha}, got {actual_sha}"
        )


def _load_production_metadata(metadata_path):
    """Load and structurally validate the production bundle metadata."""
    if not metadata_path.exists():
        raise BuildError(f"Production bundle metadata not found: {metadata_path}")
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BuildError(f"Invalid production bundle metadata JSON: {e}")
    if not isinstance(data, dict):
        raise BuildError("Production bundle metadata must be a JSON object")
    return data


def _validate_bundle_boundary(manifest_base, manifest_data, bundle_path, metadata, legacy_data):
    """Fail closed unless the bundle is cryptographically bound to the manifest.

    Rejects missing bundles, altered bundles/metadata, membership drift against
    the ordered legacy manifest, sourcemap or extra-chunk declarations, dynamic
    imports, and any vendor boundary violation. The canonical ESM entry drives
    the bundle; the legacy manifest records the expected application script
    membership for rollback-boundary validation.
    """
    required_keys = {
        "schema_version",
        "state",
        "format",
        "target",
        "minifier",
        "sourcemap",
        "bundle_file",
        "bundle_bytes",
        "bundle_sha256",
        "entry",
        "vendor",
        "legacy_script_count",
        "application_scripts",
        "expected_namespaces",
        "actual_module_files",
        "dynamic_import_count",
        "output_files",
    }
    missing = required_keys - set(metadata.keys())
    if missing:
        raise BuildError(
            "Production bundle metadata missing key(s): "
            + ", ".join(sorted(missing))
        )

    if metadata.get("state") != PRODUCTION_METADATA_STATE:
        raise BuildError(
            "Production bundle metadata state must be "
            f"{PRODUCTION_METADATA_STATE}, got {metadata.get('state')!r}"
        )
    if metadata.get("format") != "iife":
        raise BuildError(
            f"Production bundle format must be iife, got {metadata.get('format')!r}"
        )
    if metadata.get("minifier") != "oxc":
        raise BuildError(
            f"Production bundle minifier must be oxc, got {metadata.get('minifier')!r}"
        )
    if metadata.get("sourcemap") is not False:
        raise BuildError("Production bundle sourcemap must be disabled")
    if metadata.get("dynamic_import_count") != 0:
        raise BuildError(
            "Production bundle dynamic import count must be zero, got "
            f"{metadata.get('dynamic_import_count')!r}"
        )
    if metadata.get("bundle_file") != PRODUCTION_BUNDLE_FILE:
        raise BuildError(
            "Production bundle_file must be "
            f"{PRODUCTION_BUNDLE_FILE}, got {metadata.get('bundle_file')!r}"
        )
    if metadata.get("entry") != "main.js":
        raise BuildError(
            "Production bundle entry must be 'main.js', "
            f"got {metadata.get('entry')!r}"
        )

    declared = set(metadata.get("output_files") or [])
    expected_files = {PRODUCTION_BUNDLE_FILE, PRODUCTION_METADATA_FILE}
    if declared != expected_files:
        raise BuildError(
            "Production bundle output_files declaration mismatch: "
            f"expected {sorted(expected_files)}, got {sorted(declared)}"
        )

    vendor = metadata.get("vendor")
    if not isinstance(vendor, dict) or vendor.get("external") is not True:
        raise BuildError("Production bundle vendor must be declared external")

    manifest_vendor = manifest_data.get("vendor") or {}
    vendor_files = [manifest_vendor.get("file")] if manifest_vendor.get("file") else []
    if any(vf in (metadata.get("application_scripts") or []) for vf in vendor_files):
        raise BuildError("Vendored Pixi must not be part of the application bundle")

    legacy_app_scripts = [
        entry["file"]
        for entry in legacy_data.get("scripts", [])
        if entry.get("kind") != "vendor"
    ]
    if metadata.get("application_scripts") != legacy_app_scripts:
        raise BuildError(
            "Production bundle application membership does not match the "
            "ordered legacy manifest"
        )
    if metadata.get("legacy_script_count") != len(legacy_app_scripts):
        raise BuildError(
            "Production bundle legacy_script_count mismatch: "
            f"expected {len(legacy_app_scripts)}, "
            f"got {metadata.get('legacy_script_count')!r}"
        )
    if metadata.get("expected_namespaces") != [
        entry["namespace"]
        for entry in legacy_data.get("scripts", [])
        if entry.get("kind") != "vendor"
    ]:
        raise BuildError(
            "Production bundle expected_namespaces do not match the legacy manifest"
        )
    actual_modules = metadata.get("actual_module_files") or []
    if not actual_modules:
        raise BuildError("Production bundle actual_module_files must be non-empty")
    for raw in actual_modules:
        if ".." in raw.split("/"):
            raise BuildError(f"Module file escapes src root: {raw}")
        candidate = (manifest_base / raw).resolve()
        try:
            candidate.relative_to(manifest_base.resolve())
        except ValueError:
            raise BuildError(f"Module file escapes src root: {raw}")
    if any(vf in actual_modules for vf in vendor_files):
        raise BuildError("Vendored Pixi must not be part of actual_module_files")

    if not bundle_path.exists():
        raise BuildError(f"Production bundle not found: {bundle_path}")
    bundle_bytes = bundle_path.read_bytes()
    actual_sha = sha256_hex(bundle_bytes)
    if actual_sha != metadata.get("bundle_sha256"):
        raise BuildError("Production bundle SHA-256 does not match its metadata")
    if len(bundle_bytes) != metadata.get("bundle_bytes"):
        raise BuildError("Production bundle byte size does not match its metadata")
    return bundle_bytes.decode("utf-8")


def _validate_bundle_content(content, name):
    """Validate the minified application bundle content directly."""
    for pattern, desc in JS_SAFETY_PATTERNS:
        if pattern.search(content):
            raise BuildError(f"Application bundle {name} {desc}")
    for pattern, desc in JS_FORBIDDEN_PATTERNS:
        if pattern.search(content):
            raise BuildError(
                f"Application bundle {name} contains forbidden {desc}"
            )
    for pattern, desc in RUNTIME_NETWORK_PATTERNS:
        if pattern.search(content):
            raise BuildError(f"Application bundle {name} contains {desc}")
    if ASSET_REF_RE.search(content):
        raise BuildError(
            f"Application bundle {name} contains an asset:// reference"
        )
    if "sourceMappingURL" in content:
        raise BuildError(f"Application bundle {name} references a source map")


def validate_production_document(output):
    """Validate the final production standalone document shape."""
    ext_script = re.compile(r"<script\s+[^>]*src\s*=", re.IGNORECASE)
    if ext_script.search(output):
        raise BuildError("Generated output contains external <script src>")
    module_script = re.compile(
        r'<script\b[^>]*type\s*=\s*["\']module["\']', re.IGNORECASE
    )
    if module_script.search(output):
        raise BuildError("Generated output contains a module <script>")
    script_re = re.compile(r"<script>(.*?)</script>", re.IGNORECASE | re.DOTALL)
    blocks = script_re.findall(output)
    if len(blocks) != 2:
        raise BuildError(
            "Generated output must contain exactly two inline script blocks, "
            f"found {len(blocks)}"
        )
    validate_no_runtime_network(output)


def build_production(manifest_path, output_path, bundle_path, metadata_path):
    """Package vendor + validated Vite bundle + CSS + template into one HTML."""
    manifest_base = manifest_path.parent.resolve()
    manifest_data = load_manifest(manifest_path)

    entry_rel = manifest_data.get("entry")
    if entry_rel != "main.js":
        raise BuildError(
            f"Production manifest entry must be 'main.js', got {entry_rel!r}"
        )

    template_rel = manifest_data["template"]
    template_path = resolve_manifest_path(manifest_base, template_rel)
    template_content = validate_template(template_path)

    legacy_data = _load_legacy_manifest(manifest_path)

    vendor_content = _load_vendor_content(manifest_base, manifest_data)
    _validate_generated_assets_hash(manifest_base, manifest_data)

    metadata = _load_production_metadata(metadata_path)
    bundle_content = _validate_bundle_boundary(
        manifest_base, manifest_data, bundle_path, metadata, legacy_data
    )
    _validate_bundle_content(bundle_content, bundle_path.name)

    css_contents = []
    used_assets = set()
    for match in ASSET_REF_RE.finditer(template_content):
        used_assets.add(match.group(1))
    for style_rel in manifest_data["styles"]:
        style_path = resolve_manifest_path(manifest_base, style_rel)
        css_raw = style_path.read_text(encoding="utf-8")
        for match in ASSET_REF_RE.finditer(css_raw):
            used_assets.add(match.group(1))
        css_contents.append(css_raw)

    declared_assets = {}
    for entry in manifest_data.get("assets", []):
        declared_assets[entry["id"]] = entry
    for asset_id in used_assets:
        if asset_id not in declared_assets:
            raise BuildError(f"Referenced but undeclared asset: {asset_id}")
    for asset_id in declared_assets:
        if asset_id not in used_assets:
            raise BuildError(f"Declared but unused asset: {asset_id}")

    assets = collect_assets(manifest_data, manifest_base)
    template_content = resolve_asset_references(template_content, assets, "template")

    resolved_css = []
    for css_content in css_contents:
        resolved_css.append(resolve_asset_references(css_content, assets, "css"))

    css_html = ""
    if resolved_css:
        css_html = "<style>\n" + "\n".join(resolved_css) + "\n</style>"

    scripts_html = (
        "<script>\n" + vendor_content + "\n</script>\n"
        "<script>\n" + bundle_content + "\n</script>"
    )

    output = template_content.replace(MARKER_CSS, css_html)
    output = output.replace(MARKER_SCRIPTS, scripts_html)

    validate_production_document(output)

    atomic_write(output_path, output)


def main():
    parser = argparse.ArgumentParser(description="Ocean Rescue single-HTML builder")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["production", "legacy"],
        help="Packaging mode: production (Vite bundle) or legacy (ordered scripts)",
    )
    parser.add_argument("--manifest", required=True, help="Path to build manifest JSON")
    parser.add_argument("--output", required=True, help="Path to output HTML file")
    parser.add_argument(
        "--bundle",
        help="Path to Vite application bundle (required in production mode)",
    )
    parser.add_argument(
        "--metadata",
        help="Path to Vite bundle metadata (required in production mode)",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    try:
        if args.mode == "production":
            if not args.bundle:
                die("--bundle is required in production mode")
            if not args.metadata:
                die("--metadata is required in production mode")
            build_production(
                manifest_path,
                output_path,
                Path(args.bundle),
                Path(args.metadata),
            )
        else:
            build(manifest_path, output_path)
    except BuildError as e:
        die(str(e))
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
