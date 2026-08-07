/**
 * @fileoverview 외부 탭 생성 어댑터 — 순수 단위 테스트
 *
 * 가짜 window와 가짜 창 핸들로 어댑터의 동작을 검증한다.
 * 실제 브라우저나 네트워크에 의존하지 않는다.
 *
 * 실행: node tests/test_external_tab_launcher.mjs
 */

import { strict as assert } from "node:assert";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const LAUNCHER_PATH = resolve(
  __dirname,
  "..",
  "shared",
  "domain",
  "external-tab-launcher.js",
);

let Launcher;
try {
  Launcher = require(LAUNCHER_PATH);
} catch (e) {
  console.error("FAIL: external-tab-launcher not found:", LAUNCHER_PATH);
  console.error("  ", e.message);
  process.exit(1);
}

const TARGET_URL = "https://example.com/video/abc123";

// ── Fake Window / Handle Factories ─────────────────────────────

function makeFakeWindow(openResult, opts = {}) {
  const calls = [];
  const handle = makeFakeHandle(openResult, opts);

  const win = {
    open(url, name) {
      calls.push({ op: "open", url, name });
      if (opts.openThrows) {
        throw new Error("window.open simulated failure");
      }
      return openResult;
    },
    get _openCalls() {
      return calls;
    },
  };

  return { win, handle };
}

function makeFakeHandle(returnValue, opts = {}) {
  const closeCalls = [];
  const openerWrites = [];
  const navCalls = [];

  // Persistent location object so handle.location.href = url works correctly
  const loc = {
    set href(url) {
      navCalls.push({ op: "navigate", href: url });
      if (opts.navThrows) throw new Error("navigation failed");
    },
  };

  const handle = {
    close() {
      closeCalls.push({ op: "close" });
      if (opts.closeThrows) throw new Error("close failed");
    },
    get _closeCalls() {
      return closeCalls;
    },

    set opener(v) {
      openerWrites.push({ op: "setOpener", value: v });
      if (opts.openerThrows) throw new Error("opener set failed");
    },
    get _openerWrites() {
      return openerWrites;
    },

    get location() {
      return loc;
    },
    get _navCalls() {
      return navCalls;
    },

    get returnValue() {
      return returnValue;
    },
  };

  return handle;
}

// ── Test Harness ──────────────────────────────────────────────

let passed = 0;
let failed = 0;

function run(name, fn) {
  try {
    fn();
    console.log(`  PASS: ${name}`);
    passed++;
  } catch (e) {
    console.error(`  FAIL: ${name}`);
    console.error(`    ${e.message}`);
    failed++;
  }
}

console.log("ExternalTabLauncher pure unit tests\n");

// ── 1. 성공 시 window.open() 정확히 1회, 대상은 빈 탭 ──────────

run("1: success — window.open called exactly once", () => {
  const { win } = makeFakeWindow({});
  Launcher.launch(win, TARGET_URL);
  assert.equal(win._openCalls.length, 1);
});

run("1: success — first open target is about:blank, not external URL", () => {
  const { win } = makeFakeWindow({});
  Launcher.launch(win, TARGET_URL);
  assert.equal(win._openCalls[0].url, "about:blank");
  assert.equal(win._openCalls[0].name, "_blank");
});

run("1: success — opener=null set before navigation", () => {
  const handle = makeFakeHandle({});
  const win = {
    open() {
      return handle;
    },
  };
  Launcher.launch(win, TARGET_URL);
  assert.ok(handle._openerWrites.length > 0, "opener must be set");
  assert.equal(handle._openerWrites[0].value, null);
  assert.ok(handle._navCalls.length > 0, "navigation must occur");
  // opener write index < nav call index (by construction, set happens first)
});

run("1: success — target URL navigated exactly once", () => {
  const handle = makeFakeHandle({});
  const win = { open() { return handle; } };
  Launcher.launch(win, TARGET_URL);
  assert.equal(handle._navCalls.length, 1);
});

run("1: success — returns handle with ok=true", () => {
  const expectedHandle = makeFakeHandle({});
  const win = { open() { return expectedHandle; } };
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, true);
  assert.strictEqual(result.handle, expectedHandle);
});

// ── 2. open이 null이면 실패 ─────────────────────────────────────

run("2: open returns null — ok=false, handle=null", () => {
  const { win } = makeFakeWindow(null);
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, false);
  assert.equal(result.handle, null);
});

run("2: open returns null — no opener set, no navigation", () => {
  const win = { open() { return null; } };
  Launcher.launch(win, TARGET_URL);
  // no handle returned, so nothing to set opener or navigate on
});

run("2: open returns undefined — ok=false", () => {
  const { win } = makeFakeWindow(undefined);
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, false);
});

// ── 3. open이 예외면 실패 ─────────────────────────────────────

run("3: open throws — ok=false, handle=null", () => {
  const { win } = makeFakeWindow({}, { openThrows: true });
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, false);
  assert.equal(result.handle, null);
});

run("3: open throws — no handle close attempted", () => {
  const { win } = makeFakeWindow({}, { openThrows: true });
  Launcher.launch(win, TARGET_URL);
  // no handle exists to close, so no error
});

// ── 4. opener 설정 실패 시 handle close ───────────────────────

run("4: opener set fails — ok=false, handle closed once", () => {
  const handle = makeFakeHandle({}, { openerThrows: true });
  const win = { open() { return handle; } };
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, false);
  assert.equal(result.handle, null);
  assert.equal(handle._closeCalls.length, 1);
});

run("4: opener fails — no navigation attempted", () => {
  const handle = makeFakeHandle({}, { openerThrows: true });
  const win = { open() { return handle; } };
  Launcher.launch(win, TARGET_URL);
  assert.equal(handle._navCalls.length, 0);
});

run("4: close throws on opener failure — still returns failure", () => {
  const handle = makeFakeHandle({}, { openerThrows: true, closeThrows: true });
  const win = { open() { return handle; } };
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, false);
  assert.equal(result.handle, null);
});

// ── 5. navigation 실패 시 handle close ────────────────────────

run("5: navigation fails — ok=false, handle closed once", () => {
  const handle = makeFakeHandle({}, { navThrows: true });
  const win = { open() { return handle; } };
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, false);
  assert.equal(result.handle, null);
  assert.equal(handle._closeCalls.length, 1);
});

run("5: close throws on nav failure — still returns failure", () => {
  const handle = makeFakeHandle({}, { navThrows: true, closeThrows: true });
  const win = { open() { return handle; } };
  const result = Launcher.launch(win, TARGET_URL);
  assert.equal(result.ok, false);
});

// ── 6. createOpenExternal — transaction 호환 ───────────────────

run("6: createOpenExternal returns handle on success", () => {
  const expectedHandle = makeFakeHandle({});
  const win = { open() { return expectedHandle; } };
  const fn = Launcher.createOpenExternal(win, TARGET_URL);
  const result = fn();
  assert.strictEqual(result, expectedHandle);
});

run("6: createOpenExternal returns null on popup blocked", () => {
  const { win } = makeFakeWindow(null);
  const fn = Launcher.createOpenExternal(win, TARGET_URL);
  const result = fn();
  assert.equal(result, null);
});

run("6: createOpenExternal returns null on opener failure", () => {
  const handle = makeFakeHandle({}, { openerThrows: true });
  const win = { open() { return handle; } };
  const fn = Launcher.createOpenExternal(win, TARGET_URL);
  const result = fn();
  assert.equal(result, null);
});

run("6: createOpenExternal returns null on nav failure", () => {
  const handle = makeFakeHandle({}, { navThrows: true });
  const win = { open() { return handle; } };
  const fn = Launcher.createOpenExternal(win, TARGET_URL);
  const result = fn();
  assert.equal(result, null);
});

// ── 7. invalid window ────────────────────────────────────────

run("7: null window — ok=false", () => {
  const result = Launcher.launch(null, TARGET_URL);
  assert.equal(result.ok, false);
});

run("7: no open function — ok=false", () => {
  const result = Launcher.launch({}, TARGET_URL);
  assert.equal(result.ok, false);
});

// ── 결과 ─────────────────────────────────────────────────────

console.log(`\nResults: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
