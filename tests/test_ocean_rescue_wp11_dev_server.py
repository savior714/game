"""WP-11 dev-server compatibility lane contract.

Verifies the Vite development-only lane for the Ocean Rescue legacy
global-namespace source:

- static contract: entry/config/commands/tsconfig/package scripts;
- live contract: the Vite dev server serves a derived HTML from the canonical
  template and build manifest with identical classic script order;
- browser contract: representative sea-turtle flow parity through the dev
  server, zero external/API requests, clean console, and full reload on a
  relevant source change.

Production authority (build-manifest.json + Python standalone builder +
``ocean-rescue/index.html``) is never touched by these tests.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import (  # noqa: E402
    assert_evidence,
    collect_evidence,
)

REPO_ROOT = TESTS_DIR.parent
DOMAIN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
SRC_DIR = DOMAIN_DIR / "src"
MANIFEST = SRC_DIR / "build-manifest.json"
TEMPLATE = SRC_DIR / "index.template.html"
DEV_HTML = DOMAIN_DIR / "index.dev.html"
VITE_CONFIG = DOMAIN_DIR / "vite.config.ts"
PACKAGE_JSON = DOMAIN_DIR / "package.json"
TSCONFIG = DOMAIN_DIR / "tsconfig.json"
JUSTFILE = REPO_ROOT / "Justfile"

MARKER_CSS = "<!-- OCEAN_RESCUE_CSS -->"
MARKER_SCRIPTS = "<!-- OCEAN_RESCUE_SCRIPTS -->"
DEV_ENTRY_MARKER = "<!-- OCEAN_RESCUE_DEV_ENTRY -->"

STARTUP_TIMEOUT = 60.0
RELOAD_TIMEOUT = 30.0


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _load_package() -> dict:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


# --- static contract ---


def test_dev_entry_exists() -> None:
    assert DEV_HTML.exists(), "missing index.dev.html"


def test_vite_config_exists() -> None:
    assert VITE_CONFIG.exists(), "missing vite.config.ts"


def test_dev_entry_is_thin_marker_only() -> None:
    text = DEV_HTML.read_text(encoding="utf-8")
    parts = text.split(DEV_ENTRY_MARKER)
    assert len(parts) - 1 == 1, (
        "index.dev.html must contain exactly one dev entry marker"
    )
    assert "</script>" not in text.lower(), "index.dev.html must not inline scripts"
    assert "ocean-rescue-root" not in text, (
        "index.dev.html must not duplicate the production DOM markup"
    )


def test_package_has_dev_script() -> None:
    scripts = _load_pair_scripts()
    dev = scripts.get("dev")
    assert dev, "package.json must define a dev script"
    assert "vite" in dev
    assert "--config vite.config.ts" in dev
    assert "--host 127.0.0.1" in dev
    assert "--port 5173" in dev
    assert "--strictPort" in dev


def _load_pair_scripts() -> dict:
    return _load_package().get("scripts", {})


def test_package_no_build_or_preview() -> None:
    scripts = _load_pair_scripts()
    for key in ("build", "preview"):
        assert key not in scripts, f"package.json must not add a {key!r} script"


def test_tsconfig_includes_vite_config() -> None:
    cfg = json.loads(TSCONFIG.read_text(encoding="utf-8"))
    assert "vite.config.ts" in cfg.get("include", []), (
        "tsconfig must include vite.config.ts"
    )


def test_justfile_has_dev_recipes() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")
    assert "dev-ocean-rescue" in text, "Justfile must define dev-ocean-rescue"
    assert "check-ocean-rescue-dev-server" in text, (
        "Justfile must define check-ocean-rescue-dev-server"
    )


def test_vite_config_reads_canonical_manifest_and_template() -> None:
    text = VITE_CONFIG.read_text(encoding="utf-8")
    assert "build-manifest.json" in text, "vite.config.ts must read build-manifest.json"
    assert "index.template.html" in text, "vite.config.ts must read index.template.html"
    assert "OCEAN_RESCUE_SCRIPTS" in text, "config must target the canonical marker"


def test_browser_runtime_has_no_manifest_fetch() -> None:
    combined = DEV_HTML.read_text(encoding="utf-8") + VITE_CONFIG.read_text(
        encoding="utf-8"
    )
    assert "fetch(/src/build-manifest.json)" not in combined
    assert "fetch('/src/build-manifest.json')" not in combined


def test_vite_config_no_production_outdir() -> None:
    text = VITE_CONFIG.read_text(encoding="utf-8")
    assert "outDir" not in text, "vite.config.ts must not declare a build outDir"
    assert "build:" not in text, "vite.config.ts must not own a production build"


def test_no_competing_lockfile() -> None:
    competing = (
        DOMAIN_DIR / "package-lock.json",
        DOMAIN_DIR / "yarn.lock",
        DOMAIN_DIR / "bun.lock",
        DOMAIN_DIR / "bun.lockb",
    )
    for path in competing:
        assert not path.exists(), "competing lockfile present: " + str(path)


def test_manifest_and_template_placeholders() -> None:
    manifest = _load_manifest()
    template = TEMPLATE.read_text(encoding="utf-8")
    assert isinstance(manifest["styles"], list) and manifest["styles"]
    assert isinstance(manifest["vendor"], dict)
    assert manifest["entry"] == "main.js"
    assert template.count(MARKER_CSS) == 1, "template must have exactly one CSS marker"
    assert template.count(MARKER_SCRIPTS) == 1, (
        "template must have exactly one SCRIPTS marker"
    )


# --- live dev-server helpers ---


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ViteServerFixture:
    def __init__(self) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.proc: subprocess.Popen[str] | None = None

    def start(self) -> str:
        env = dict(os.environ)
        self.proc = subprocess.Popen(
            [
                "corepack",
                "pnpm",
                "exec",
                "vite",
                "--config",
                "vite.config.ts",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--strictPort",
            ],
            cwd=str(DOMAIN_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self._wait_ready()
        return self.base_url

    def _wait_ready(self) -> None:
        url = f"{self.base_url}/index.dev.html"
        deadline = time.time() + STARTUP_TIMEOUT
        last_log = ""

        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError("Vite exited during startup: " + self._output_text())
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    body = response.read().decode("utf-8", errors="replace")
                    last_log = f"status={response.status} {len(body)}b"
                    if response.status == 200 and "ocean-rescue-root" in body:
                        return
            except Exception as exc:  # noqa: BLE001
                last_log = str(exc)
            time.sleep(0.25)
        raise RuntimeError(
            "Vite dev server did not become ready within "
            f"{STARTUP_TIMEOUT:.0f}s (last: {last_log})\n{self._output_text()}"
        )

    def fetch_then_return_body(self, url: str) -> str:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            return f"<error> {exc}"

    def _output_text(self) -> str:
        text = ""
        stdouts: list[str] = []
        if self.proc is not None and self.proc.stdout is not None:
            stdouts.append(self.proc.stdout.read())
        if self.proc is not None and self.proc.stderr is not None:
            stdouts.append(self.proc.stderr.read())
        if stdouts:
            text = "\n".join(stdouts)
        return text

    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        finally:
            self.proc = None

    @property
    def dead(self) -> bool:
        return self.proc is None or self.proc.poll() is not None

    def __enter__(self) -> "ViteServerFixture":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()


def _derive_script_order(html: str) -> list[str]:
    return re.findall(r'<script[^>]*src="([^"]+)"[^>]*></script>', html)


def _assert_live_derivation(server: ViteServerFixture) -> None:
    manifest = _load_manifest()
    body = server.fetch_then_return_body(f"{server.base_url}/index.dev.html")
    assert "ocean-rescue-root" in body, "served HTML must contain the game root"
    assert '<link rel="stylesheet" href="/src/style.css">' in body, "missing stylesheet"
    script_tags = [
        tag for tag in _derive_script_order(body) if "@vite/client" not in tag
    ]
    vendor_file = manifest["vendor"]["file"]
    expected = [f"/src/{vendor_file}", f"/src/{manifest['entry']}"]
    assert script_tags == expected, f"script tags mismatch:\n{script_tags}\n{expected}"
    assert "src/build-manifest.json" not in body, (
        "served document must not fetch the manifest at runtime"
    )
    module_tags = re.findall(r'<script[^>]*type="module"[^>]*src="([^"]+)"', body)
    assert f"/src/{manifest['entry']}" in module_tags, (
        "module scripts must include the canonical ESM entry"
    )
    classic_tags = re.findall(r'<script(?! type="module")[^>]*src="([^"]+)"', body)
    classic_tags = [tag for tag in classic_tags if "@vite/client" not in tag]
    assert classic_tags == [f"/src/{vendor_file}"], (
        "exactly one classic script (vendored Pixi) must be present"
    )


def _run_browser_parity(server: ViteServerFixture) -> dict[str, object]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-background-networking", "--disable-component-update"],
        )
        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="ko-KR",
                timezone_id="Asia/Seoul",
            )
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            try:
                evidence = collect_evidence(
                    page,
                    server.base_url,
                    {"engine": "Playwright Chromium", "version": browser.version},
                    entry_path="/index.dev.html",
                )
                evidence["dev_document"] = page.evaluate(
                    """() => ({
                      url: location.href,
                      hasPixi: typeof window.PIXI !== 'undefined',
                      hasApp: !!(window.OceanRescue && window.OceanRescue.App),
                      hasRenderAssets:
                        !!(window.OceanRescue && window.OceanRescue.RenderAssets),
                      script_srcs:
                        Array.from(document.querySelectorAll('script[src]'))
                          .map(script => script.getAttribute('src'))
                    })"""
                )
            finally:
                page.close()
                context.close()
        finally:
            browser.close()
    return evidence


def _serve_startup_assertions(evidence: dict[str, object]) -> None:
    startup = evidence["startup"]
    assert startup["ready"] == "true"
    assert startup["pixi_version"] == "8.19.0"
    assert startup["renderer_backend"] in {"webgl", "canvas"}
    assert int(startup["canvas_width"]) == 1280
    assert int(startup["canvas_height"]) == 720


# --- parity + reload (separate failure domains, each self-managed server) ---


def test_dev_server_serves_derived_html_in_order() -> None:
    with ViteServerFixture() as server:
        _assert_live_derivation(server)


def test_dev_server_browser_parity() -> None:
    with ViteServerFixture() as server:
        evidence = _run_browser_parity(server)
        _serve_startup_assertions(evidence)
        doc = evidence["dev_document"]
        assert doc["url"].endswith("/index.dev.html"), "browser must load the dev entry"
        assert doc["hasPixi"] is True, "PIXI global must be present (vendor)"
        assert doc["hasApp"] is True, "OceanRescue.App must be present"
        assert doc["hasRenderAssets"] is True, (
            "OceanRescue.RenderAssets must be present"
        )
        assert_evidence(evidence, network_mode="dev")


def test_dev_server_full_reload_on_source_change() -> None:
    trigger = SRC_DIR / "__wp11_reload_trigger__.js"
    try:
        with ViteServerFixture() as server:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context()
                    page = context.new_page()
                    try:
                        page.goto(
                            f"{server.base_url}/index.dev.html",
                            wait_until="networkidle",
                        )
                        page.wait_for_selector(
                            "#ocean-rescue-root[data-ocean-rescue-ready=true]",
                            timeout=STARTUP_TIMEOUT,
                        )
                        page.evaluate("window.__wp11ReloadMarker = 1;")
                        trigger.write_text("/* wp11 reload trigger */\n")
                        deadline = time.time() + RELOAD_TIMEOUT
                        reloaded = False
                        while time.time() < deadline:
                            time.sleep(0.25)
                            try:
                                marker = page.evaluate(
                                    "() => window.__wp11ReloadMarker"
                                )
                                ready = page.evaluate(
                                    "() => document.getElementById("
                                    "'ocean-rescue-root').getAttribute("
                                    "'data-ocean-rescue-ready')"
                                )
                            except Exception:  # noqa: BLE001
                                continue
                            if marker is None and ready == "true":
                                reloaded = True
                                break
                        assert reloaded, (
                            "full reload not observed after relevant source change"
                        )
                    finally:
                        page.close()
                        context.close()
                finally:
                    browser.close()
    finally:
        trigger.unlink(missing_ok=True)
    assert trigger.exists() is False, "reload trigger file must be removed"
