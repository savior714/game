from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_LOADER = ROOT / "domains/reward/auth.js"
SYNC_LOADER = ROOT / "domains/reward/sync-engine.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

function run(order) {
  const appended = [];
  const listeners = {};
  const elementsById = {};

  class Event {
    constructor(type) { this.type = type; }
  }

  const window = {
    location: { href: 'https://example.test/index.html' },
    addEventListener(type, listener, options) {
      if (!listeners[type]) listeners[type] = [];
      listeners[type].push({ listener, once: Boolean(options && options.once) });
    },
    dispatchEvent(event) {
      const entries = (listeners[event.type] || []).slice();
      listeners[event.type] = (listeners[event.type] || []).filter((entry) => !entry.once);
      for (const entry of entries) entry.listener(event);
    },
  };

  const document = {
    currentScript: null,
    querySelector(selector) {
      if (selector.includes('reward/auth.js')) return { src: 'https://example.test/domains/reward/auth.js' };
      if (selector.includes('reward/sync-engine.js')) return { src: 'https://example.test/domains/reward/sync-engine.js' };
      return null;
    },
    createElement(tag) {
      return { tagName: tag.toUpperCase(), id: '', src: '', onload: null, onerror: null };
    },
    getElementById(id) { return elementsById[id] || null; },
    head: {
      appendChild(element) {
        appended.push(element.src);
        if (element.id) elementsById[element.id] = element;
        if (element.src.endsWith('/domains/auth/auth.js')) {
          window.Auth = { getUser() { return null; } };
          if (element.onload) element.onload();
        } else if (element.src.endsWith('/domains/sync/sync-engine.js')) {
          window.SyncEngine = { pushStats() {} };
          if (element.onload) element.onload();
        }
      },
    },
  };

  const context = vm.createContext({ window, document, Event, URL, console });
  const sources = {
    auth: fs.readFileSync(process.argv[2], 'utf8'),
    sync: fs.readFileSync(process.argv[3], 'utf8'),
  };
  const sourceUrls = {
    auth: 'https://example.test/domains/reward/auth.js',
    sync: 'https://example.test/domains/reward/sync-engine.js',
  };

  for (const name of order) {
    document.currentScript = { src: sourceUrls[name] };
    vm.runInContext(sources[name], context);
    document.currentScript = null;
  }
  for (const name of order) {
    document.currentScript = { src: sourceUrls[name] };
    vm.runInContext(sources[name], context);
    document.currentScript = null;
  }

  return {
    appended,
    hasAuth: Boolean(window.Auth),
    hasSync: Boolean(window.SyncEngine),
  };
}

console.log(JSON.stringify({
  syncFirst: run(['sync', 'auth']),
  authFirst: run(['auth', 'sync']),
}));
"""


def _node() -> str:
    node = shutil.which("node")
    assert node, "node is required"
    return node


def test_compat_loaders_resolve_canonical_paths_in_auth_then_sync_order(tmp_path: Path) -> None:
    harness = tmp_path / "harness.js"
    harness.write_text(HARNESS, encoding="utf-8")
    proc = subprocess.run(
        [_node(), str(harness), str(AUTH_LOADER), str(SYNC_LOADER)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip())
    expected = [
        "https://example.test/domains/auth/auth.js",
        "https://example.test/domains/sync/sync-engine.js",
    ]
    for lane in (result["syncFirst"], result["authFirst"]):
        assert lane["appended"] == expected
        assert lane["hasAuth"] is True
        assert lane["hasSync"] is True


def test_compat_loaders_are_syntax_valid() -> None:
    for script in (AUTH_LOADER, SYNC_LOADER):
        proc = subprocess.run(
            [_node(), "--check", str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
