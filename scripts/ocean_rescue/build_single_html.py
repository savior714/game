#!/usr/bin/env python3
"""Ocean Rescue single-HTML builder.

Consumes a JSON build manifest, an HTML template, CSS and JS source files,
and binary assets, then produces a standalone HTML file with all content
inlined as data URIs.
"""

import argparse
import base64
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

ASSET_REF_RE = re.compile(r"asset://([a-zA-Z0-9_-]+)")

JS_FORBIDDEN_PATTERNS = [
    (re.compile(r"\bimport\s*\{"), "static import declaration (named)"),
    (re.compile(r'\bimport\s+["\']'), "static import declaration (string)"),
    (re.compile(r"\bimport\s+\*\s+as\s+"), "static import declaration (namespace)"),
    (re.compile(r"\bimport\s+\w+\s+from\s+"), "static import declaration (default)"),
    (re.compile(r"\bexport\s+"), "export declaration"),
    (re.compile(r"\bimport\s*\("), "dynamic import()"),
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
    """Load and validate the build manifest."""
    if not path.exists():
        raise BuildError(f"Manifest not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BuildError(f"Invalid JSON in manifest: {e}")

    if not isinstance(data, dict):
        raise BuildError("Manifest must be a JSON object")

    allowed_keys = {"template", "styles", "scripts", "assets"}
    unknown = set(data.keys()) - allowed_keys
    if unknown:
        raise BuildError(f"Unknown manifest key(s): {', '.join(sorted(unknown))}")

    if "template" not in data:
        raise BuildError("Missing required manifest key: template")
    if "styles" not in data:
        raise BuildError("Missing required manifest key: styles")
    if "scripts" not in data:
        raise BuildError("Missing required manifest key: scripts")

    _validate_manifest_types(data)

    _validate_styles(data)
    _validate_scripts(data)
    _validate_manifest_assets(data)

    return data


def _validate_manifest_types(data):
    if not isinstance(data["template"], str):
        raise BuildError("manifest.template must be a string")
    styles = data["styles"]
    if not isinstance(styles, list):
        raise BuildError("manifest.styles must be an array")
    for i, s in enumerate(styles):
        if not isinstance(s, str):
            raise BuildError(f"manifest.styles[{i}] must be a string")
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
    allowed_keys = {"file", "namespace", "depends_on"}
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


def validate_js_source(script_path, content):
    """Validate JavaScript source file content."""
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


def validate_no_runtime_network(output):
    """Validate the generated output has no runtime network dependencies."""
    scripts_seen = re.compile(r"<script>(.*?)</script>", re.IGNORECASE | re.DOTALL)
    script_contents = scripts_seen.findall(output)
    for script_content in script_contents:
        for pattern, desc in RUNTIME_NETWORK_PATTERNS:
            if pattern.search(script_content):
                raise BuildError(f"Generated output contains {desc}")

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

    css_url_re = re.compile(
        r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)',
        re.IGNORECASE,
    )
    for m in css_url_re.finditer(output):
        url = m.group(1)
        if not url.startswith("data:") and not url.startswith("#"):
            raise BuildError(f"Generated output contains external CSS url(): {url}")

    if ASSET_REF_RE.search(output):
        raise BuildError("Generated output contains unresolved asset:// reference")


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
        validate_js_source(script_path, content)
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

    validate_no_runtime_network(output)

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


def main():
    parser = argparse.ArgumentParser(description="Ocean Rescue single-HTML builder")
    parser.add_argument("--manifest", required=True, help="Path to build manifest JSON")
    parser.add_argument("--output", required=True, help="Path to output HTML file")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    try:
        build(manifest_path, output_path)
    except BuildError as e:
        die(str(e))
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
