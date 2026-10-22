"""태블릿 전체 화면 토글 계약 — 버튼 하나로 전체 화면 진입과 되돌아오기를 보장한다.

버튼 마크업은 shared/ui/fullscreen-toggle.js가 HUD 우측 클러스터에 주입한다.
따라서 페이지마다 스크립트를 빠뜨리면 버튼이 조용히 사라진다 — 그 회귀를 막는다.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = {
    "index.html": "./shared/ui/fullscreen-toggle.js",
    "domains/math/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/english/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/korean/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/science/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/english/weekly-test/index.html": (
        "../../../shared/ui/fullscreen-toggle.js"
    ),
    "domains/reward/guardian/index.html": (
        "../../../shared/ui/fullscreen-toggle.js"
    ),
    "domains/auth/admin/index.html": (
        "../../../shared/ui/fullscreen-toggle.js"
    ),
    "experiments/space-explorer/index.html": "../../shared/ui/fullscreen-toggle.js",
    "experiments/space-explorer/orbit-eclipse.html": "../../shared/ui/fullscreen-toggle.js",
    "experiments/space-explorer/paint-mixing.html": "../../shared/ui/fullscreen-toggle.js",
    "experiments/space-explorer/dino-escape.html": "../../shared/ui/fullscreen-toggle.js",
    "experiments/magnet/index.html": "../../shared/ui/fullscreen-toggle.js",
    "experiments/electricity/index.html": "../../shared/ui/fullscreen-toggle.js",
    "experiments/bubble/index.html": "../../shared/ui/fullscreen-toggle.js",
    "experiments/marble/index.html": "../../shared/ui/fullscreen-toggle.js",
}


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_every_hud_page_wires_the_fullscreen_toggle_once() -> None:
    for rel_path, script_src in PAGES.items():
        html = read(rel_path)
        script_tag = f'<script src="{script_src}"></script>'
        assert script_tag in html, (
            f"{rel_path} must load the shared fullscreen toggle ({script_src})"
        )
        assert html.count("fullscreen-toggle.js") == 1, (
            f"{rel_path} must load the fullscreen toggle exactly once"
        )
        assert ("ag-hud__right" in html) or ("ag-hud" in html), (
            f"{rel_path} must provide an .ag-hud or .ag-hud__right target in its top HUD"
        )


def test_toggle_enters_and_returns_from_fullscreen() -> None:
    source = read("shared/ui/fullscreen-toggle.js")

    # 진입과 복귀가 같은 버튼 하나에 묶여 있어야 한다.
    assert "requestFullscreen" in source
    assert "exitFullscreen" in source
    assert "isFullscreen()" in source
    assert 'button.addEventListener("click", toggle)' in source

    # 벤더 prefix와 옛 API를 함께 처리한다.
    for prefix in ("webkit", "moz", "ms"):
        assert prefix in source, f"fullscreen toggle must support {prefix} prefixes"

    # 버튼 클릭 결과를 추측하지 않고 실제 fullscreen 상태로 라벨을 맞춘다.
    for event_name in (
        "fullscreenchange",
        "webkitfullscreenchange",
        "mozfullscreenchange",
        "MSFullscreenChange",
    ):
        assert event_name in source, (
            f"fullscreen state must re-sync on {event_name} (Esc · 브라우저 UI 포함)"
        )

    # 되돌아오기 라벨/역할이 명시되어야 한다.
    assert "전체 화면으로 보기" in source
    assert "전체 화면 끄기" in source
    assert "나가기" in source
    assert "aria-pressed" in source

    # Fullscreen API가 아예 없는 브라우저에서는 죽은 버튼을 만들지 않는다.
    assert 'typeof requestFullscreen !== "function"' in source
    assert 'typeof exitFullscreen !== "function"' in source

    # 권한이 막힌 문서(iframe 등)에서는 숨기지 않고 "쓸 수 없음"으로 표시하고 클릭을 배선하지 않는다.
    assert "fullscreenEnabled" in source
    assert "var blocked =" in source
    assert "if (!blocked)" in source
    assert "ag-fs-toggle--blocked" in source
    assert 'setAttribute("aria-disabled", "true")' in source

    # 단일 HUD 버튼: 중복 주입 방지와 HUD 부재 시 fallback이 있어야 한다.
    assert 'querySelector("[data-ag-fullscreen-toggle]")' in source
    assert 'querySelector(".ag-hud__right")' in source
    assert "ag-fs-toggle--floating" in source


def test_toggle_styles_are_shared_and_accessible() -> None:
    css = read("shared/ui/hud.css")

    # Tailwind preflight([type="button"])와 같은 specificity에서 밀리지 않도록
    # 클래스 단독 선택자가 아니라 button.ag-fs-toggle로 스타일한다.
    assert "button.ag-fs-toggle {" in css
    assert "background-color: rgba(255, 255, 255, 0.08);" in css
    assert 'button.ag-fs-toggle[aria-pressed="true"]' in css, (
        "active (되돌아오기) 상태 스타일이 있어야 한다"
    )
    assert "button.ag-fs-toggle:focus-visible" in css, (
        "키보드 포커스 표시가 필요하다"
    )
    assert "button.ag-fs-toggle--blocked" in css, (
        "fullscreen 권한이 막힌 상태의 표시가 필요하다"
    )
    assert "env(safe-area-inset-bottom)" in css, (
        "floating fallback은 태블릿 안전 영역을 피해야 한다"
    )
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "html:fullscreen" in css
    assert ".paint-page button.ag-fs-toggle" in css


def test_fullscreen_toggle_injects_self_contained_styles_for_standalone_pages() -> None:
    source = read("shared/ui/fullscreen-toggle.js")
    assert "ag-fullscreen-toggle-styles" in source
    assert "button.ag-fs-toggle" in source
    assert ".paint-page button.ag-fs-toggle" in source
    assert "AidenFullscreenToggle" in source


def test_reward_mini_game_iframes_allow_fullscreen() -> None:
    reward_ui = read("domains/reward/reward_ui.js")
    frames = re.findall(r"<iframe\b[^>]*reward-mini-game-frame[^>]*>", reward_ui)
    assert len(frames) >= 2
    for frame in frames:
        assert "allowfullscreen" in frame, (
            f"reward mini-game iframe ({frame}) must include allowfullscreen"
        )


def test_fullscreen_toggle_mounts_across_all_subpage_header_patterns() -> None:
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        return

    script_path = (ROOT / "shared" / "ui" / "fullscreen-toggle.js").resolve()
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync(process.argv[1], "utf8");

function runScenario({ hasExistingBtn = false, hasCluster = true, remountAfterRewrite = false }) {
  const listeners = {};
  let fullscreenEl = null;
  let requestCount = 0;
  let exitCount = 0;

  function makeEl(tag, id = "", className = "") {
    const attrs = {};
    const classSet = new Set(className.split(/\s+/).filter(Boolean));
    const el = {
      tagName: tag.toUpperCase(),
      id,
      type: "",
      textContent: "",
      innerHTML: "",
      parentNode: null,
      children: [],
      firstChild: null,
      clickListener: null,
      classList: {
        add(c) { classSet.add(c); el.className = Array.from(classSet).join(" "); },
        remove(c) { classSet.delete(c); el.className = Array.from(classSet).join(" "); },
        toggle(c, force) {
          if (force === undefined) {
            if (classSet.has(c)) classSet.delete(c); else classSet.add(c);
          } else if (force) {
            classSet.add(c);
          } else {
            classSet.delete(c);
          }
          el.className = Array.from(classSet).join(" ");
        },
        contains(c) { return classSet.has(c); },
      },
      set className(v) {
        classSet.clear();
        String(v || "").split(/\s+/).filter(Boolean).forEach((c) => classSet.add(c));
      },
      get className() {
        return Array.from(classSet).join(" ");
      },
      setAttribute(k, v) { attrs[k] = String(v); },
      getAttribute(k) { return attrs[k] ?? null; },
      removeAttribute(k) { delete attrs[k]; },
      hasAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k); },
      appendChild(child) {
        if (child.parentNode) {
          child.parentNode.children = child.parentNode.children.filter((x) => x !== child);
        }
        child.parentNode = el;
        el.children.push(child);
        el.firstChild = el.children[0] || null;
        return child;
      },
      insertBefore(child, ref) {
        if (child.parentNode) {
          child.parentNode.children = child.parentNode.children.filter((x) => x !== child);
        }
        child.parentNode = el;
        const idx = ref ? el.children.indexOf(ref) : -1;
        if (idx >= 0) el.children.splice(idx, 0, child);
        else el.children.push(child);
        el.firstChild = el.children[0] || null;
        return child;
      },
      addEventListener(ev, fn) {
        if (ev === "click") el.clickListener = fn;
      },
      querySelector(sel) {
        if (sel === ".ag-fs-toggle__label") {
          return { textContent: "" };
        }
        return null;
      },
    };
    return el;
  }

  let root = makeEl("html");
  root.requestFullscreen = function () {
    requestCount += 1;
    fullscreenEl = root;
    (listeners.fullscreenchange || []).forEach((fn) => fn());
    return Promise.resolve();
  };
  let head = makeEl("head");
  let body = makeEl("body");
  let header = makeEl("header", "", "site-header");
  let cluster = hasCluster ? makeEl("div", "", "ag-hud__right") : null;
  if (cluster) header.appendChild(cluster);
  body.appendChild(header);

  let existingBtn = null;
  if (hasExistingBtn && cluster) {
    existingBtn = makeEl("button", "btn-fullscreen", "hud-icon-btn hud-icon-btn--fullscreen");
    existingBtn.setAttribute("data-action", "toggle-fullscreen");
    cluster.appendChild(existingBtn);
  }

  const doc = {
    get documentElement() { return root; },
    get head() { return head; },
    get body() { return body; },
    get fullscreenElement() { return fullscreenEl; },
    fullscreenEnabled: true,
    exitFullscreen() {
      exitCount += 1;
      fullscreenEl = null;
      (listeners.fullscreenchange || []).forEach((fn) => fn());
      return Promise.resolve();
    },
    createElement(tag) { return makeEl(tag); },
    getElementById(id) {
      if (id === "ag-fullscreen-toggle-styles") {
        return head.children.find((c) => c.id === id) || null;
      }
      if (id === "btn-fullscreen") return existingBtn;
      return null;
    },
    querySelector(sel) {
      if (sel === "[data-ag-fullscreen-toggle]") {
        const all = [...(cluster ? cluster.children : []), ...header.children, ...body.children];
        return all.find((c) => c.hasAttribute && c.hasAttribute("data-ag-fullscreen-toggle")) || null;
      }
      if (sel === ".ag-hud__right") return cluster;
      if (sel === ".site-header" || sel === "header") return header;
      return null;
    },
    addEventListener(ev, fn) {
      listeners[ev] = listeners[ev] || [];
      listeners[ev].push(fn);
    },
  };

  const win = {
    document: doc,
    Event: function (type) { this.type = type; },
    dispatchEvent() {},
    console: { info() {} },
  };
  const ctx = vm.createContext({ window: win, document: doc, Promise, Event: win.Event });
  vm.runInContext(code, ctx);

  if (remountAfterRewrite) {
    Object.keys(listeners).forEach((k) => { listeners[k] = []; });
    root = makeEl("html");
    root.requestFullscreen = function () {
      requestCount += 1;
      fullscreenEl = root;
      (listeners.fullscreenchange || []).forEach((fn) => fn());
      return Promise.resolve();
    };
    head = makeEl("head");
    body = makeEl("body");
    header = makeEl("header", "", "game-top-hud");
    cluster = makeEl("div", "", "ag-hud__right");
    header.appendChild(cluster);
    body.appendChild(header);
    win.AidenFullscreenToggle.mount();
  }

  const mountedCluster = cluster || header.children.find((c) => c.className.includes("ag-hud__right"));
  const btn = mountedCluster.firstChild;
  btn.clickListener();

  return {
    styleInjected: Boolean(doc.getElementById("ag-fullscreen-toggle-styles")),
    adoptedExisting: hasExistingBtn ? btn === existingBtn : true,
    removedDataAction: !btn.hasAttribute("data-action"),
    hasToggleAttr: btn.hasAttribute("data-ag-fullscreen-toggle"),
    ariaPressedAfterClick: btn.getAttribute("aria-pressed"),
    requestCount,
    rootHasFullscreenClass: root.classList.contains("ag-is-fullscreen"),
  };
}

console.log(JSON.stringify({
  standard: runScenario({ hasExistingBtn: false, hasCluster: true }),
  autoCluster: runScenario({ hasExistingBtn: false, hasCluster: false }),
  dinoAdopt: runScenario({ hasExistingBtn: true, hasCluster: true }),
  marbleRemount: runScenario({ hasExistingBtn: false, hasCluster: true, remountAfterRewrite: true }),
}));
"""
    result = subprocess.run(
        [node, "-e", harness, str(script_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    for name, outcome in payload.items():
        assert outcome == {
            "styleInjected": True,
            "adoptedExisting": True,
            "removedDataAction": True,
            "hasToggleAttr": True,
            "ariaPressedAfterClick": "true",
            "requestCount": 1,
            "rootHasFullscreenClass": True,
        }, f"scenario {name} failed: {outcome}"


