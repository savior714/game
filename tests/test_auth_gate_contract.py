"""로그인 gate 계약 — 로그인 session 없이는 child-facing 기능을 사용할 수 없다.

범위:
1. 허브·Core Quiz·주간 시험·실험 페이지는 ``domains/auth/auth-gate.js``를
   ``<body>`` 시작 직후 정확히 한 번 로드한다.
2. gate는 auth module 확인 전(pending), session 없음(locked), 확인 실패(error)를
   모두 fail-closed로 유지하고, 확인된 session에만 열린다.
3. 보호자 화면도 같은 gate를 쓰고, 관리자 화면과 standalone Ocean Rescue
   artifact는 자체 경계를 따른다.
4. ``auth.js``는 최초 session 확인 완료를 ``whenReady()``로 알리고, 중복 로드되어도
   Auth를 재정의하지 않는다.

브라우저 없이 Node VM의 최소 DOM으로 계약을 검증한다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# child-facing 기능 표면 → 페이지 기준 auth-gate.js 상대 경로
GATED_PAGES = {
    "index.html": "./domains/auth/auth-gate.js",
    "domains/math/index.html": "../../domains/auth/auth-gate.js",
    "domains/english/index.html": "../../domains/auth/auth-gate.js",
    "domains/english/weekly-test/index.html": "../../../domains/auth/auth-gate.js",
    "domains/korean/index.html": "../../domains/auth/auth-gate.js",
    "domains/science/index.html": "../../domains/auth/auth-gate.js",
    "experiments/bubble/index.html": "../../domains/auth/auth-gate.js",
    "experiments/electricity/index.html": "../../domains/auth/auth-gate.js",
    "experiments/magnet/index.html": "../../domains/auth/auth-gate.js",
    "experiments/marble/index.html": "../../domains/auth/auth-gate.js",
    "experiments/space-explorer/index.html": "../../domains/auth/auth-gate.js",
    "experiments/space-explorer/dino-escape.html": "../../domains/auth/auth-gate.js",
    "experiments/space-explorer/orbit-eclipse.html": "../../domains/auth/auth-gate.js",
    "experiments/space-explorer/paint-mixing.html": "../../domains/auth/auth-gate.js",
    "domains/reward/guardian/index.html": "../../../domains/auth/auth-gate.js",
}

# 별도 인증/권한 경계이거나 standalone artifact라 gate script를 넣지 않는다.
UNGATED_SURFACES = (
    "domains/auth/admin/index.html",
    "ocean-rescue/index.html",
)


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def node() -> str:
    executable = shutil.which("node")
    assert executable, "node is required"
    return executable


def run_harness(tmp_path: Path, name: str, source: str, script_path: Path) -> dict:
    harness = tmp_path / name
    harness.write_text(source, encoding="utf-8")
    proc = subprocess.run(
        [node(), str(harness), str(script_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip())


def test_every_child_facing_page_loads_the_gate_once_before_app_scripts() -> None:
    for rel_path, script_src in GATED_PAGES.items():
        html = read(rel_path)
        tag = f'<script src="{script_src}"></script>'

        assert html.count(tag) == 1, (
            f"{rel_path} must load auth-gate.js exactly once"
        )

        body_index = html.index("<body")
        gate_index = html.index(tag)
        assert body_index < gate_index, (
            f"{rel_path} must mount the gate inside <body>"
        )

        # gate는 body의 첫 script여야 한다. 앞에 다른 script가 있으면
        # 그 script가 잠금 이전에 실행될 수 있다.
        assert "<script" not in html[body_index:gate_index].lower(), (
            f"{rel_path} must run the gate before any other script"
        )

        resolved = (ROOT / rel_path).parent / script_src
        assert resolved.resolve() == (ROOT / "domains/auth/auth-gate.js").resolve(), (
            f"{rel_path} gate path must resolve to the canonical gate module"
        )


def test_auth_boundaries_without_the_gate_stay_explicit() -> None:
    for rel_path in UNGATED_SURFACES:
        assert "auth-gate.js" not in read(rel_path), (
            f"{rel_path} has its own auth/artifact boundary; do not add the shared gate"
        )


def test_security_owners_document_the_gate() -> None:
    for rel_path in (
        "PROJECT_RULES.md",
        "README.md",
        "docs/specs/product/ACTIVE_PRODUCT_SCOPE.md",
        "docs/agent-context/memory/MEMORY.md",
    ):
        assert "domains/auth/auth-gate.js" in read(rel_path), (
            f"{rel_path} must point at the canonical login gate"
        )


GATE_HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

class ClassList {
  constructor() { this.set = new Set(); }
  add(...names) { names.forEach((name) => this.set.add(name)); }
  remove(...names) { names.forEach((name) => this.set.delete(name)); }
  contains(name) { return this.set.has(name); }
  toggle(name, force) {
    const on = force === undefined ? !this.set.has(name) : Boolean(force);
    if (on) this.set.add(name); else this.set.delete(name);
    return on;
  }
}

function makeElement(tagName) {
  return {
    tagName: String(tagName).toUpperCase(),
    children: [],
    attributes: {},
    classList: new ClassList(),
    style: {},
    dataset: {},
    textContent: '',
    hidden: false,
    disabled: false,
    tabIndex: 0,
    type: '',
    id: '',
    src: '',
    className: '',
    listeners: {},
    appendChild(child) { this.children.push(child); return child; },
    append(...nodes) { nodes.forEach((node) => this.children.push(node)); },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    removeAttribute(name) { delete this.attributes[name]; },
    hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); },
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    removeEventListener(type, fn) {
      this.listeners[type] = (this.listeners[type] || []).filter((entry) => entry !== fn);
    },
    focus() { this.focused = true; },
    querySelectorAll() { return []; },
  };
}

function makeDom() {
  const documentElement = makeElement('html');
  const body = makeElement('body');
  const head = makeElement('head');
  const main = makeElement('main');
  body.appendChild(main);

  const document = {
    currentScript: { src: 'https://example.test/domains/auth/auth-gate.js' },
    documentElement,
    body,
    head,
    readyState: 'complete',
    activeElement: null,
    listeners: {},
    createElement: makeElement,
    getElementById(id) {
      return [...head.children, ...body.children].find((element) => element.id === id) || null;
    },
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
  };
  return { document, documentElement, body, main };
}

function makeWindow(document) {
  const listeners = {};
  return {
    document,
    location: { origin: 'https://example.test', reloaded: false, reload() { this.reloaded = true; } },
    supabaseClient: {},
    listeners,
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener(type, fn) {
      listeners[type] = (listeners[type] || []).filter((entry) => entry !== fn);
    },
    dispatchEvent(event) { (listeners[event.type] || []).slice().forEach((fn) => fn(event)); },
  };
}

function makeAuth(user) {
  let current = user;
  return {
    getUser() { return current; },
    whenReady() { return Promise.resolve(current); },
    signInGoogle(options) { this.lastSignIn = options; return Promise.resolve(true); },
    setUser(next) { current = next; },
  };
}

function findByTag(element, tagName) {
  if (element.tagName === tagName) return element;
  for (const child of element.children) {
    const found = findByTag(child, tagName);
    if (found) return found;
  }
  return null;
}

function classes(document) {
  return [...document.documentElement.classList.set];
}

const results = [];

async function scenario(name, setup, exercise) {
  const dom = makeDom();
  const window = makeWindow(dom.document);
  const auth = setup(window);
  const context = vm.createContext({
    window,
    document: dom.document,
    URL,
    console,
    setTimeout,
    clearTimeout,
    CustomEvent: class CustomEvent {
      constructor(type, init) { this.type = type; this.detail = init && init.detail; }
    },
    Event: class Event { constructor(type) { this.type = type; } },
    Promise,
    Object,
    Array,
    String,
    Boolean,
  });
  context.globalThis = context;
  vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), context);
  await new Promise((resolve) => setTimeout(resolve, 25));

  const gate = dom.body.children.find((element) => element.id === 'aiden-auth-gate');
  const result = await exercise(window, gate, auth, dom);
  results.push({ name, result });
}

(async () => {
  await scenario('no-auth', (window) => {
    delete window.Auth;
    return null;
  }, async (window, gate, auth, dom) => ({
    state: window.AidenAuthGate.getState(),
    locked: window.AidenAuthGate.isLocked(),
    gateHidden: gate.hidden,
    classes: classes(dom.document),
    title: findByTag(gate, 'H2').textContent,
    buttonHidden: findByTag(gate, 'BUTTON').hidden,
  }));

  await scenario('signed-out', (window) => {
    const auth = makeAuth(null);
    window.Auth = auth;
    return auth;
  }, async (window, gate, auth, dom) => {
    const title = findByTag(gate, 'H2');
    const button = findByTag(gate, 'BUTTON');
    const before = {
      state: window.AidenAuthGate.getState(),
      locked: window.AidenAuthGate.isLocked(),
      gateHidden: gate.hidden,
      classes: classes(dom.document),
      title: title.textContent,
      buttonText: button.textContent,
      buttonHidden: button.hidden,
      mainInert: dom.main.hasAttribute('inert'),
    };

    // Escape는 gate를 닫지 못한다.
    dom.document.listeners.keydown[0]({
      key: 'Escape',
      preventDefault() {},
      stopPropagation() {},
    });
    const afterEscape = window.AidenAuthGate.getState();

    window.dispatchEvent(new CustomEvent('auth-changed', { detail: { user: { id: 'u1' } } }));
    const unlocked = {
      state: window.AidenAuthGate.getState(),
      locked: window.AidenAuthGate.isLocked(),
      gateHidden: gate.hidden,
      classes: classes(dom.document),
      mainInert: dom.main.hasAttribute('inert'),
    };

    window.dispatchEvent(new CustomEvent('auth-changed', { detail: { user: null } }));
    const relocked = {
      state: window.AidenAuthGate.getState(),
      locked: window.AidenAuthGate.isLocked(),
      gateHidden: gate.hidden,
      classes: classes(dom.document),
    };

    return { before, afterEscape, unlocked, relocked };
  });

  await scenario('missing-client', (window) => {
    const auth = makeAuth(null);
    window.Auth = auth;
    delete window.supabaseClient;
    return auth;
  }, async (window, gate) => ({
    state: window.AidenAuthGate.getState(),
    locked: window.AidenAuthGate.isLocked(),
    title: findByTag(gate, 'H2').textContent,
    buttonText: findByTag(gate, 'BUTTON').textContent,
  }));

  await scenario('sign-in', (window) => {
    const auth = makeAuth(null);
    window.Auth = auth;
    return auth;
  }, async (window, gate, auth) => {
    findByTag(gate, 'BUTTON').listeners.click[0]();
    await new Promise((resolve) => setTimeout(resolve, 25));
    return {
      state: window.AidenAuthGate.getState(),
      signInArgs: auth.lastSignIn || null,
      buttonText: findByTag(gate, 'BUTTON').textContent,
    };
  });

  console.log(JSON.stringify(results));
  process.exit(0);
})();
"""


def test_gate_fails_closed_until_a_session_is_confirmed(tmp_path: Path) -> None:
    result = run_harness(
        tmp_path,
        "gate-harness.cjs",
        GATE_HARNESS,
        ROOT / "domains/auth/auth-gate.js",
    )
    scenarios = {entry["name"]: entry["result"] for entry in result}

    assert scenarios["no-auth"]["state"] == "pending"
    assert scenarios["no-auth"]["locked"] is True
    assert scenarios["no-auth"]["gateHidden"] is False
    assert "aiden-auth-pending" in scenarios["no-auth"]["classes"]

    signed_out = scenarios["signed-out"]
    assert signed_out["before"]["state"] == "locked"
    assert signed_out["before"]["locked"] is True
    assert signed_out["before"]["gateHidden"] is False
    assert "aiden-auth-locked" in signed_out["before"]["classes"]
    assert signed_out["before"]["title"] == "로그인이 필요해요"
    assert signed_out["before"]["buttonText"] == "구글로 로그인"
    assert signed_out["before"]["buttonHidden"] is False
    assert signed_out["before"]["mainInert"] is True
    assert signed_out["afterEscape"] == "locked"
    assert signed_out["unlocked"]["state"] == "unlocked"
    assert signed_out["unlocked"]["locked"] is False
    assert signed_out["unlocked"]["gateHidden"] is True
    assert signed_out["unlocked"]["classes"] == []
    assert signed_out["unlocked"]["mainInert"] is False
    assert signed_out["relocked"]["state"] == "locked"
    assert signed_out["relocked"]["locked"] is True

    missing = scenarios["missing-client"]
    assert missing["state"] == "error"
    assert missing["locked"] is True
    assert missing["title"] == "로그인을 확인할 수 없어요"
    assert missing["buttonText"] == "다시 시도"

    sign_in = scenarios["sign-in"]
    assert sign_in["state"] == "signing"
    assert sign_in["signInArgs"] == {
        "redirectTo": "https://example.test",
        "silent": True,
    }
    assert sign_in["buttonText"] == "이동 중…"


AUTH_HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

class Event { constructor(type) { this.type = type; } }
class CustomEvent extends Event {
  constructor(type, init) { super(type); this.detail = init && init.detail; }
}

function makeEnv(options) {
  const withSupabase = options.withSupabase !== false;
  const state = {
    current: options.user || null,
    changeHandlers: [],
    signInCalls: [],
    alerts: [],
    reloads: 0,
  };

  const listeners = {};
  const window = {
    location: { origin: 'https://example.test', reload() { state.reloads += 1; } },
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener(type, fn) {
      listeners[type] = (listeners[type] || []).filter((entry) => entry !== fn);
    },
    dispatchEvent(event) {
      (listeners[event.type] || []).slice().forEach((fn) => fn(event));
      return true;
    },
  };

  const document = {
    readyState: 'complete',
    addEventListener() {},
  };

  const client = {
    auth: {
      async getSession() {
        if (options.rejectSession) throw new Error('offline');
        return { data: { session: state.current ? { user: state.current } : null } };
      },
      onAuthStateChange(handler) {
        state.changeHandlers.push(handler);
        return { data: { subscription: { unsubscribe() {} } } };
      },
      async signInWithOAuth(signInOptions) {
        state.signInCalls.push(signInOptions);
        return { error: null };
      },
      async signOut() {
        state.current = null;
        state.changeHandlers.forEach((handler) => handler('SIGNED_OUT', null));
      },
    },
  };

  const context = vm.createContext({
    window,
    document,
    URL,
    console,
    supabase: withSupabase ? { createClient: () => client } : undefined,
    CustomEvent,
    Event,
    Promise,
    Object,
    Boolean,
    String,
    alert(message) { state.alerts.push(message); },
  });
  context.globalThis = context;

  return { window, document, context, state, client, listeners };
}

async function runAuthTwice(env) {
  const source = fs.readFileSync(process.argv[2], 'utf8');
  const moduleLoaded = [];
  const readyEvents = [];
  const changedEvents = [];

  env.window.addEventListener('aiden-auth-module-loaded', () => moduleLoaded.push(true));
  env.window.addEventListener('auth-ready', (event) => readyEvents.push(event.detail));
  env.window.addEventListener('auth-changed', (event) => changedEvents.push(event.detail));

  vm.runInContext(source, env.context);
  const firstAuth = env.window.Auth;
  vm.runInContext(source, env.context);
  const sameAuth = env.window.Auth === firstAuth;

  const readyUser = await env.window.Auth.whenReady();
  const restoredUser = await env.window.Auth.whenReady();

  return {
    moduleLoaded,
    readyEvents,
    changedEvents,
    sameAuth,
    readyUser,
    restoredUser,
    isReady: env.window.Auth.isReady(),
    hasWhenReady: typeof env.window.Auth.whenReady === 'function',
  };
}

(async () => {
  const signedIn = makeEnv({ user: { id: 'u1', email: 'kid@example.test' } });
  const signedInState = await runAuthTwice(signedIn);
  const signInResult = await signedIn.window.Auth.signInGoogle({
    redirectTo: 'https://example.test/domains/math/index.html',
    silent: true,
  });
  await signedIn.window.Auth.signOut();
  const signedInAfter = {
    signInResult,
    signInCalls: signedIn.state.signInCalls,
    userAfterSignOut: signedIn.window.Auth.getUser(),
    lastChanged: signedInState.changedEvents[signedInState.changedEvents.length - 1] || null,
  };

  const missingClient = makeEnv({ user: null, withSupabase: false });
  const missingState = await runAuthTwice(missingClient);
  const silentResult = await missingClient.window.Auth.signInGoogle({ silent: true });
  const loudResult = await missingClient.window.Auth.signInGoogle({ silent: false });

  const rejectedSession = makeEnv({ user: { id: 'u2' }, rejectSession: true });
  const rejectedState = await runAuthTwice(rejectedSession);

  console.log(JSON.stringify({
    signedIn: { ...signedInState, after: signedInAfter },
    missingClient: {
      ...missingState,
      silentResult,
      loudResult,
      alerts: missingClient.state.alerts,
    },
    rejectedSession: {
      readyUser: rejectedState.readyUser,
      isReady: rejectedState.isReady,
      changedEvents: rejectedState.changedEvents,
    },
  }));
  process.exit(0);
})();
"""


def test_auth_module_is_idempotent_and_reports_readiness(tmp_path: Path) -> None:
    result = run_harness(
        tmp_path,
        "auth-harness.cjs",
        AUTH_HARNESS,
        ROOT / "domains/auth/auth.js",
    )

    signed_in = result["signedIn"]
    assert signed_in["sameAuth"] is True, "auth.js must not redefine an existing Auth module"
    assert signed_in["moduleLoaded"], "auth.js must announce aiden-auth-module-loaded"
    assert signed_in["hasWhenReady"] is True
    assert signed_in["isReady"] is True
    assert signed_in["readyUser"]["email"] == "kid@example.test"
    assert signed_in["restoredUser"]["email"] == "kid@example.test"
    assert signed_in["readyEvents"][0]["user"]["id"] == "u1"
    assert signed_in["after"]["signInResult"] is True
    assert signed_in["after"]["signInCalls"] == [{
        "provider": "google",
        "options": {"redirectTo": "https://example.test/domains/math/index.html"},
    }]
    assert signed_in["after"]["userAfterSignOut"] is None
    assert signed_in["after"]["lastChanged"] == {"user": None}

    missing = result["missingClient"]
    assert missing["readyUser"] is None
    assert missing["isReady"] is True
    assert missing["silentResult"] is False
    assert missing["loudResult"] is False
    assert missing["alerts"] == ["Supabase 설정이 필요합니다."]

    rejected = result["rejectedSession"]
    assert rejected["isReady"] is True
    assert rejected["readyUser"] is None
    assert rejected["changedEvents"] == [{"user": None}]
