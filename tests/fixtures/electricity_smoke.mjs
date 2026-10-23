/*!
 * AIDEN POWER ISLAND 3D — Node ESM + Three.js 통합 스모크 하니스
 *
 * 브라우저 없이 실제 `three.module.min.js`, `world.js`, `audio.js`,
 * `electricity-physics.js`, `electricity.js` 전체 모듈 그래프를 적재해
 * 3D 씬 생성, 7개 발전 스테이션 목표 달성, 6단계 마을 점등, 테슬라 번개,
 * 날씨 전환, 정전/복구, 진행 저장까지 예외 없이 동작하는지 검증한다.
 */

import { readFileSync } from "node:fs";
import { register } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import vm from "node:vm";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const pageDir = path.join(root, "experiments", "electricity");
const vendorDir = path.join(root, "experiments", "space-explorer", "vendor", "three");

// index.html 의 importmap 과 동일하게 bare specifier "three" / "three/addons/" 해석
const loaderSource = `
export async function resolve(specifier, context, nextResolve) {
  if (specifier === "three") {
    return { shortCircuit: true, url: ${JSON.stringify(
      pathToFileURL(path.join(vendorDir, "build", "three.module.min.js")).href
    )} };
  }
  if (specifier.startsWith("three/addons/")) {
    const sub = specifier.slice("three/addons/".length);
    return { shortCircuit: true, url: ${JSON.stringify(
      pathToFileURL(path.join(vendorDir, "addons")).href + "/"
    )} + sub };
  }
  return nextResolve(specifier, context);
}
`;
register("data:text/javascript;charset=utf-8," + encodeURIComponent(loaderSource));

const errors = [];

/* ----------------------------------------------------------- canvas 2D */

function makeContext() {
  const gradient = { addColorStop() {} };
  const base = {
    createLinearGradient: () => gradient,
    createRadialGradient: () => gradient,
    measureText: () => ({ width: 12 }),
  };
  return new Proxy(base, {
    get(target, prop) {
      if (prop in target) return target[prop];
      const fallback = () => {};
      target[prop] = fallback;
      return fallback;
    },
    set(target, prop, value) {
      target[prop] = value;
      return true;
    },
  });
}

/* ------------------------------------------------------------- elements */

const allElements = [];
const rafQueue = [];

class ClassList {
  constructor() {
    this.set = new Set();
  }
  add(...names) {
    names.forEach((name) => this.set.add(name));
  }
  remove(...names) {
    names.forEach((name) => this.set.delete(name));
  }
  toggle(name, force) {
    if (force === undefined) {
      if (this.set.has(name)) this.set.delete(name);
      else this.set.add(name);
    } else if (force) {
      this.set.add(name);
    } else {
      this.set.delete(name);
    }
  }
  contains(name) {
    return this.set.has(name);
  }
}

class El {
  constructor(tagName, attrs, text) {
    this.tagName = tagName;
    this.attrs = attrs;
    this.id = attrs.id || "";
    this.classList = new ClassList();
    String(attrs.class || "")
      .split(/\s+/)
      .filter(Boolean)
      .forEach((name) => this.classList.add(name));
    this.textContent = text || "";
    this.hidden = Object.prototype.hasOwnProperty.call(attrs, "hidden");
    this.style = { setProperty() {}, removeProperty() {} };
    this.children = [];
    this.handlers = {};
    this.value = attrs.value === undefined ? "" : attrs.value;
    this.width = 0;
    this.height = 0;
    this.clientWidth = tagName === "canvas" && this.id === "island-canvas" ? 1280 : 320;
    this.clientHeight = tagName === "canvas" && this.id === "island-canvas" ? 800 : 112;
    this.parentNode = null;
    this.ownerDocument = null;
    if (tagName === "canvas") this.context = makeContext();
    allElements.push(this);
  }
  set className(value) {
    this.classList = new ClassList();
    String(value || "")
      .split(/\s+/)
      .filter(Boolean)
      .forEach((name) => this.classList.add(name));
  }
  get className() {
    return Array.from(this.classList.set).join(" ");
  }
  getRootNode() {
    return doc;
  }
  getContext(kind) {
    if (kind === "webgl" || kind === "webgl2" || kind === "experimental-webgl") {
      return null;
    }
    return this.context;
  }
  getBoundingClientRect() {
    return {
      left: 0,
      top: 0,
      width: this.clientWidth,
      height: this.clientHeight,
      right: this.clientWidth,
      bottom: this.clientHeight,
    };
  }
  addEventListener(type, handler) {
    if (!this.handlers[type]) this.handlers[type] = [];
    this.handlers[type].push(handler);
  }
  removeEventListener() {}
  dispatch(type, event) {
    const payload = Object.assign(
      {
        type,
        target: this,
        currentTarget: this,
        preventDefault() {},
        stopPropagation() {},
      },
      event
    );
    (this.handlers[type] || []).slice().forEach((handler) => {
      try {
        handler(payload);
      } catch (error) {
        errors.push(type + " on #" + this.id + ": " + error.message);
      }
    });
  }
  click() {
    this.dispatch("click", {});
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
  }
  getAttribute(name) {
    return this.attrs[name] === undefined ? null : this.attrs[name];
  }
  appendChild(child) {
    this.children.push(child);
    child.parentNode = this;
    child.ownerDocument = doc;
    return child;
  }
  set innerHTML(value) {
    this.children = [];
    const subMatch = String(value).match(/data-tag-val="([^"]+)"/);
    if (subMatch) {
      const em = new El("em", { "data-tag-val": subMatch[1] }, "");
      this.appendChild(em);
    }
  }
  get innerHTML() {
    return "";
  }
  get offsetWidth() {
    return this.clientWidth;
  }
  focus() {
    doc.activeElement = this;
  }
  setPointerCapture() {}
  releasePointerCapture() {}
  querySelector(selector) {
    return querySelector(selector, this);
  }
  querySelectorAll(selector) {
    return querySelectorAll(selector, this);
  }
}

function matchesSingle(element, sel) {
  if (sel.charAt(0) === "#") return element.id === sel.slice(1);
  if (sel.charAt(0) === ".") return element.classList.contains(sel.slice(1));
  const attr = sel.match(/^\[([\w-]+)(?:=["']?([^"'\]]*)["']?)?\]$/);
  if (attr) {
    const value = element.attrs[attr[1]];
    if (value === undefined) return false;
    return attr[2] === undefined || value === attr[2];
  }
  return element.tagName === sel;
}

function matches(element, selector) {
  const chain = selector.trim().split(/\s+/);
  let cur = element;
  for (let i = chain.length - 1; i >= 0; i -= 1) {
    if (!cur) return false;
    if (i === chain.length - 1) {
      if (!matchesSingle(cur, chain[i])) return false;
      cur = cur.parentNode;
    } else {
      while (cur && !matchesSingle(cur, chain[i])) {
        cur = cur.parentNode;
      }
      if (!cur) return false;
      cur = cur.parentNode;
    }
  }
  return true;
}

function descendants(root) {
  if (!root) return allElements;
  const out = [];
  const walk = (node) => {
    node.children.forEach((child) => {
      out.push(child);
      walk(child);
    });
  };
  walk(root);
  return out;
}

function querySelector(selector, root) {
  const parts = selector.split(",").map((part) => part.trim());
  for (const part of parts) {
    const found = descendants(root).find((element) => matches(element, part));
    if (found) return found;
  }
  return null;
}

function querySelectorAll(selector, root) {
  const parts = selector.split(",").map((part) => part.trim());
  return descendants(root).filter((element) => parts.some((part) => matches(element, part)));
}

/* -------------------------------------------------------------- document */

const doc = {
  readyState: "complete",
  activeElement: null,
  handlers: {},
  addEventListener(type, handler) {
    if (!this.handlers[type]) this.handlers[type] = [];
    this.handlers[type].push(handler);
  },
  removeEventListener() {},
  dispatch(type, event) {
    const payload = Object.assign({ type, preventDefault() {} }, event);
    (this.handlers[type] || []).slice().forEach((handler) => {
      try {
        handler(payload);
      } catch (error) {
        errors.push("document " + type + ": " + error.message);
      }
    });
  },
  createElement(tagName) {
    const el = new El(tagName, {}, "");
    el.ownerDocument = doc;
    return el;
  },
  getElementById(id) {
    return allElements.find((element) => element.id === id) || null;
  },
  querySelector(selector) {
    return querySelector(selector, null);
  },
  querySelectorAll(selector) {
    return querySelectorAll(selector, null);
  },
};

/* ---------------------------------------------------------------- window */

const storage = {};
const win = globalThis;
win.window = win;
win.document = doc;
win.innerWidth = 1280;
win.innerHeight = 800;
win.devicePixelRatio = 2;
win.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
// The standalone browser entry always loads auth-gate.js. The DOM-only smoke harness
// models the already-authenticated state so it can exercise the actual lazy boot path.
win.AidenAuthGate = { isLocked: () => false, getState: () => "unlocked" };
win.requestAnimationFrame = (callback) => {
  rafQueue.push(callback);
  return rafQueue.length;
};
win.addEventListener = () => {};
win.removeEventListener = () => {};
win.localStorage = {
  getItem: (key) => (Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : null),
  setItem: (key, value) => {
    storage[key] = String(value);
  },
};

/* -------------------------------------------------- index.html → DOM 트리 */

const html = readFileSync(path.join(pageDir, "index.html"), "utf8");
const VOID_TAGS = new Set(["input", "meta", "link", "br", "img", "hr", "source", "use"]);
const cleanHtml = html.replace(/<!--[\s\S]*?-->/g, "");
const tagPattern = /<(\/?)([a-zA-Z][\w-]*)((?:\s+[\w:-]+(?:="[^"]*")?)*)\s*(\/?)>/g;
const docRoot = new El("body", {}, "");
doc.body = docRoot;
doc.documentElement = docRoot;
const stack = [docRoot];
let match;
while ((match = tagPattern.exec(cleanHtml)) !== null) {
  const closing = match[1] === "/";
  const tagName = match[2].toLowerCase();
  if (closing) {
    if (stack.length > 1) stack.pop();
    continue;
  }
  const attrString = match[3] || "";
  const attrs = {};
  const attrPattern = /([\w:-]+)(?:="([^"]*)")?/g;
  let attrMatch;
  while ((attrMatch = attrPattern.exec(attrString)) !== null) {
    attrs[attrMatch[1]] = attrMatch[2] === undefined ? "" : attrMatch[2];
  }
  const element = new El(tagName, attrs, "");
  element.ownerDocument = doc;
  stack[stack.length - 1].appendChild(element);
  const after = cleanHtml.slice(match.index + match[0].length);
  const textEnd = after.indexOf("<");
  const text = textEnd > 0 ? after.slice(0, textEnd).trim() : "";
  if (text) element.textContent = text;
  if (tagName === "input" && attrs.value !== undefined) element.value = attrs.value;
  const selfClosing = match[4] === "/" || VOID_TAGS.has(tagName);
  if (!selfClosing) stack.push(element);
}

/* --------------------------------------------------------- 스크립트 실행 */

const physicsCode = readFileSync(path.join(pageDir, "electricity-physics.js"), "utf8");
vm.runInThisContext(physicsCode, { filename: path.join(pageDir, "electricity-physics.js") });
const hasPhysics = Boolean(win.PowerPhysics);
if (!hasPhysics) errors.push("PowerPhysics 전역 모듈이 등록되지 않았습니다");

await import(pathToFileURL(path.join(pageDir, "electricity.js")).href);
if (win.__electricityReady) await win.__electricityReady;
if (win.__electricityBootError) errors.push("boot: " + win.__electricityBootError);
const loadingRoot = doc.getElementById("world-loading");
const loadingProgress = doc.getElementById("world-loading-progress");
const bootLoadingSnapshot = {
  present: Boolean(loadingRoot),
  ariaBusy: loadingRoot ? loadingRoot.getAttribute("aria-busy") : null,
  progress: loadingProgress ? Number(loadingProgress.getAttribute("aria-valuenow")) : null,
  hasFrame: rafQueue.length > 0,
};

/* -------------------------------------------------------------- 시뮬레이션 */

let clock = 1000;

function frames(count) {
  for (let i = 0; i < count; i += 1) {
    clock += 16.7;
    const callbacks = rafQueue.splice(0, rafQueue.length);
    if (!callbacks.length) return;
    callbacks.forEach((callback) => {
      try {
        callback(clock);
      } catch (error) {
        errors.push("frame: " + error.message);
      }
    });
  }
}

function click(id) {
  const element = doc.getElementById(id);
  if (!element) {
    errors.push("missing element #" + id);
    return null;
  }
  element.dispatch("click", {});
  return element;
}

function clickAttr(attr, value) {
  const element = querySelectorAll("[" + attr + '="' + value + '"]')[0];
  if (!element) {
    errors.push("missing [" + attr + '="' + value + '"]');
    return null;
  }
  element.dispatch("click", {});
  return element;
}

function slide(id, value) {
  const element = doc.getElementById(id);
  if (!element) {
    errors.push("missing slider #" + id);
    return;
  }
  element.value = String(value);
  element.dispatch("input", {});
}

frames(4);

// 01 회로: 4.5V로 올리면 변전소 100% 개통
slide("voltage-range", 4.5);
frames(4);

// 03 과일 전지: 레몬 4개 직렬
click("cells-plus");
click("cells-plus");
click("cells-plus");
frames(4);

// 04 손잡이 발전기: 고속 부스트 회전
clickAttr("data-spin", "140");
frames(180);

// 05 태양광: 맑은 하늘 + 최적 각도
slide("cloud-range", 0);
slide("sun-range", 60);
slide("tilt-range", 30);
frames(4);

// 06 바람: 강풍 + 긴 블레이드
slide("wind-range", 10);
slide("blade-range", 0.5);
frames(4);

// 07 물: 만수위 + 최대 유량
slide("head-range", 2.5);
slide("flow-range", 5);
frames(4);

// 02 마찰 전기: 양모 패드 위에서 문지른 뒤 별 조각들 위로 이동
const staticCanvas = doc.getElementById("canvas-static");
if (staticCanvas) {
  staticCanvas.dispatch("pointerdown", { pointerId: 1, clientX: 58, clientY: 58 });
  for (let i = 0; i < 42; i += 1) {
    staticCanvas.dispatch("pointermove", {
      pointerId: 1,
      clientX: 58 + (i % 2 === 0 ? 9 : -9),
      clientY: 58 + (i % 3 === 0 ? 5 : -5),
    });
    frames(1);
  }
  for (let step = 0; step <= 32; step += 1) {
    const t = step / 32;
    staticCanvas.dispatch("pointermove", {
      pointerId: 1,
      clientX: 58 + (235 - 58) * t,
      clientY: 58 + (86 - 58) * t,
    });
    frames(1);
  }
  frames(60);
}

function snapshot() {
  const ids = ["circuit", "static", "fruit", "generator", "solar", "wind", "hydro"];
  const out = { stamps: {}, reads: {} };
  ids.forEach((id) => {
    const stamp = doc.getElementById("stamp-" + id);
    out.stamps[id] = stamp ? stamp.hidden === false : null;
    const read = doc.getElementById("read-" + id);
    out.reads[id] = read ? read.textContent : null;
  });
  return out;
}

const playSnapshot = snapshot();
const peakWatts = Number((doc.getElementById("stat-watts") || {}).textContent || 0);

// 스펙터클·날씨·테슬라·정전·복구·카메라 이동 검증
click("tesla-fire-btn");
frames(6);
clickAttr("data-weather", "storm");
frames(6);
clickAttr("data-weather", "day");
frames(4);
click("blackout-btn");
frames(4);
const blackoutWatts = Number((doc.getElementById("stat-watts") || {}).textContent || 0);
click("full-power-btn");
frames(6);
clickAttr("data-cam", "village");
frames(4);
clickAttr("data-cam", "overview");
frames(4);
click("sound-button");
click("help-button");
click("help-ok");
click("codex-button");
click("codex-ok");
doc.dispatch("keydown", { key: "Escape" });
click("reset-all");
frames(4);

const stationIds = ["circuit", "static", "fruit", "generator", "solar", "wind", "hydro"];
const result = {
  errors,
  loader: bootLoadingSnapshot,
  physics: hasPhysics,
  peakWatts,
  blackoutWatts,
  worldTags: querySelectorAll(".world-tag", null).length,
  play: playSnapshot,
  stamps: {},
  reads: {},
  stored: storage["aiden_electricity_lab_v1"] || null,
  energy: (doc.getElementById("stat-energy") || {}).textContent,
  watts: (doc.getElementById("stat-watts") || {}).textContent,
  foundCount: (doc.getElementById("stat-found") || {}).textContent,
  dots: (doc.getElementById("found-dots") || { children: [] }).children.length,
};
stationIds.forEach((id) => {
  const stamp = doc.getElementById("stamp-" + id);
  result.stamps[id] = stamp ? stamp.hidden === false : null;
  const read = doc.getElementById("read-" + id);
  result.reads[id] = read ? read.textContent : null;
});

process.stdout.write(JSON.stringify(result) + "\n");
