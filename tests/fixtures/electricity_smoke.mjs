/*!
 * AIDEN POWER LAB — Node DOM 스모크 하니스
 *
 * 브라우저 없이 `experiments/electricity` 페이지 스크립트를 실제로 실행해
 * 초기화·상호작용·프레임 루프에서 예외가 발생하지 않는지 확인한다.
 * 결과는 JSON 한 줄로.stdout에 출력한다.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const pageDir = path.join(root, "experiments", "electricity");

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
    this.style = {};
    this.children = [];
    this.handlers = {};
    this.value = attrs.value === undefined ? "" : attrs.value;
    this.width = 0;
    this.height = 0;
    this.clientWidth = 640;
    this.clientHeight = 400;
    this.parentNode = null;
    if (tagName === "canvas") this.context = makeContext();
    allElements.push(this);
  }
  getContext() {
    return this.context;
  }
  getBoundingClientRect() {
    return { left: 0, top: 0, width: 640, height: 400, right: 640, bottom: 400 };
  }
  addEventListener(type, handler) {
    if (!this.handlers[type]) this.handlers[type] = [];
    this.handlers[type].push(handler);
  }
  removeEventListener() {}
  dispatch(type, event) {
    const payload = Object.assign(
      { type: type, target: this, preventDefault() {}, stopPropagation() {} },
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
  setAttribute(name, value) {
    this.attrs[name] = String(value);
  }
  getAttribute(name) {
    return this.attrs[name] === undefined ? null : this.attrs[name];
  }
  appendChild(child) {
    this.children.push(child);
    child.parentNode = this;
    return child;
  }
  set innerHTML(value) {
    if (value === "") this.children = [];
  }
  get innerHTML() {
    return "";
  }
  get offsetWidth() {
    return 640;
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

function matches(element, selector) {
  const sel = selector.trim();
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
  dispatch(type, event) {
    const payload = Object.assign({ type: type, preventDefault() {} }, event);
    (this.handlers[type] || []).slice().forEach((handler) => {
      try {
        handler(payload);
      } catch (error) {
        errors.push("document " + type + ": " + error.message);
      }
    });
  },
  createElement(tagName) {
    return new El(tagName, {}, "");
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
// 브라우저와 같이 window === globalThis 로 두어 UMD 전역 등록이 그대로 반영되게 한다.
const win = globalThis;
win.document = doc;
win.devicePixelRatio = 2;
win.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
win.requestAnimationFrame = (callback) => {
  rafQueue.push(callback);
  return rafQueue.length;
};
win.addEventListener = () => {};
win.localStorage = {
  getItem: (key) => (Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : null),
  setItem: (key, value) => {
    storage[key] = String(value);
  },
};

/* -------------------------------------------------- index.html → DOM 트리 */

const html = readFileSync(path.join(pageDir, "index.html"), "utf8");
const VOID_TAGS = new Set(["input", "meta", "link", "br", "img", "hr", "source", "use"]);
const tagPattern = /<(\/?)([a-zA-Z][\w-]*)((?:\s+[\w:-]+(?:="[^"]*")?)*)\s*(\/?)>/g;
const docRoot = new El("body", {}, "");
const stack = [docRoot];
let match;
while ((match = tagPattern.exec(html)) !== null) {
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
  stack[stack.length - 1].appendChild(element);
  const after = html.slice(match.index + match[0].length);
  const textEnd = after.indexOf("<");
  const text = textEnd > 0 ? after.slice(0, textEnd).trim() : "";
  if (text) element.textContent = text;
  if (tagName === "input" && attrs.value !== undefined) element.value = attrs.value;
  const selfClosing = match[4] === "/" || VOID_TAGS.has(tagName);
  if (!selfClosing) stack.push(element);
}

/* --------------------------------------------------------- 스크립트 실행 */

globalThis.window = win;

function runScript(file) {
  const code = readFileSync(path.join(pageDir, file), "utf8");
  try {
    vm.runInThisContext(code, { filename: path.join(pageDir, file) });
  } catch (error) {
    errors.push(file + " threw: " + error.message);
  }
}

runScript("electricity-physics.js");
const hasPhysics = Boolean(win.PowerPhysics);
if (!hasPhysics) errors.push("PowerPhysics 전역 모듈이 등록되지 않았습니다");
runScript("electricity.js");

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

frames(3);

// 01 회로: 전압을 4.5V로 올리면 전구가 환하게 켜진다
slide("voltage-range", 4.5);
frames(3);

// 03 과일 전지: 레몬 4개를 직렬로
click("cells-plus");
click("cells-plus");
click("cells-plus");
frames(3);

// 04 손잡이 발전기: 빠르게 돌리기
clickAttr("data-spin", "140");
frames(200);

// 05 태양광: 최적 각도
slide("sun-range", 60);
slide("tilt-range", 30);
frames(3);

// 06 바람: 최대 바람 + 긴 날개
slide("wind-range", 10);
slide("blade-range", 0.5);
frames(3);

// 07 물: 높은 낙차 + 많은 물
slide("head-range", 2.5);
slide("flow-range", 5);
frames(3);

// 02 마찰 전기: 풍선을 문지른 뒤 종이 조각으로 이동
const staticCanvas = doc.getElementById("canvas-static");
if (staticCanvas) {
  staticCanvas.dispatch("pointerdown", { pointerId: 1, clientX: 100, clientY: 180 });
  for (let i = 0; i < 40; i += 1) {
    staticCanvas.dispatch("pointermove", {
      pointerId: 1,
      clientX: 100 + (i % 2 === 0 ? 7 : -7),
      clientY: 180 + (i % 3 === 0 ? 5 : -5),
    });
    frames(1);
  }
  for (let step = 0; step <= 30; step += 1) {
    const t = step / 30;
    staticCanvas.dispatch("pointermove", {
      pointerId: 1,
      clientX: 100 + (400 - 100) * t,
      clientY: 180 + (330 - 180) * t,
    });
    frames(1);
  }
  frames(180);
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

// 각 실험을 목표까지 조작한 직후 상태를 기록한다.
const playSnapshot = snapshot();

// 스위치·재료·도움말·소리·초기화 경로도 한 번씩 실행
clickAttr("data-material", "wood");
frames(2);
click("switch-circuit");
frames(2);
click("switch-circuit");
clickAttr("data-material", "copper");
frames(2);
click("rub-button");
frames(2);
click("discharge-button");
frames(2);
clickAttr("data-fruit", "potato");
click("cells-minus");
frames(2);
clickAttr("data-blades", "6");
frames(2);
click("tilt-auto");
frames(4);
click("sound-button");
click("help-button");
click("help-ok");
click("reset-circuit");
frames(4);

const generator = doc.getElementById("canvas-generator");
if (generator) {
  generator.dispatch("pointerdown", { pointerId: 2, clientX: 460, clientY: 250 });
  for (let i = 0; i < 20; i += 1) {
    const angle = (i / 20) * Math.PI * 2;
    generator.dispatch("pointermove", {
      pointerId: 2,
      clientX: 460 + Math.cos(angle) * 80,
      clientY: 250 + Math.sin(angle) * 80,
    });
    frames(1);
  }
  generator.dispatch("pointerup", { pointerId: 2 });
  generator.dispatch("keydown", { key: "ArrowRight" });
  staticCanvas.dispatch("keydown", { key: "ArrowRight" });
  staticCanvas.dispatch("keydown", { key: " " });
  frames(6);
}

doc.dispatch("keydown", { key: "Escape" });
click("reset-all");
frames(4);

/* ------------------------------------------------------------------ 결과 */

const stationIds = ["circuit", "static", "fruit", "generator", "solar", "wind", "hydro"];
const result = {
  errors: errors,
  physics: hasPhysics,
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

process.stdout.write(JSON.stringify(result));
