/* ─────────────────────────────────────────────────────────────
   Aiden Game Labs — 전체 화면(Fullscreen) 토글
   태블릿에서 브라우저 크롬 없이 화면 전체를 쓰고, 같은 버튼으로 되돌아온다.

   • HUD 우측 클러스터(.ag-hud__right) 안에 버튼 하나를 주입한다.
   • HUD가 없는 화면은 우하단 floating 버튼으로 붙는다.
   • shared/ui/hud.css를 읽지 않는 실험실·미니게임 화면에서도 동일한
     스타일이 적용되도록 자체 스타일 시트를 함께 보장한다.
   • Fullscreen API 자체가 없는 브라우저에서는 버튼을 만들지 않고,
     권한이 막힌 문서(iframe 등)에서는 눌리지 않는 상태로 표시한다.
   • 표시 상태는 fullscreenchange 이벤트로만 맞춘다(클릭 결과를 추측하지 않는다).
     → Esc, 브라우저 UI, 다른 스크립트로 전체 화면이 바뀌어도 라벨이 어긋나지 않는다.
   ───────────────────────────────────────────────────────────── */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;
  if (!root || doc.querySelector("[data-ag-fullscreen-toggle]")) {
    return;
  }

  var requestFullscreen =
    root.requestFullscreen ||
    root.webkitRequestFullscreen ||
    root.mozRequestFullScreen ||
    root.msRequestFullscreen;
  var exitFullscreen =
    doc.exitFullscreen ||
    doc.webkitExitFullscreen ||
    doc.mozCancelFullScreen ||
    doc.msExitFullscreen;
  // API 자체가 없는 브라우저(iOS Safari 등)에는 버튼을 만들지 않는다.
  if (
    typeof requestFullscreen !== "function" ||
    typeof exitFullscreen !== "function"
  ) {
    return;
  }

  // API는 있지만 지금 문서에서 막혀 있는 경우(iframe의 fullscreen 권한 없음 등)에는
  // 버튼을 숨기지 않고 "지금은 쓸 수 없음"으로 표시한다. 눌러도 아무 일도 없게 한다.
  var blocked =
    doc.fullscreenEnabled === false || doc.webkitFullscreenEnabled === false;

  var LABELS = {
    enter: { text: "전체 화면", aria: "전체 화면으로 보기" },
    exit: { text: "나가기", aria: "전체 화면 끄기" },
  };

  var ICON_ENTER =
    '<svg class="ag-fs-toggle__icon-enter" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    '<path d="M8 3H5a2 2 0 0 0-2 2v3"></path>' +
    '<path d="M16 3h3a2 2 0 0 1 2 2v3"></path>' +
    '<path d="M16 21h3a2 2 0 0 0 2-2v-3"></path>' +
    '<path d="M8 21H5a2 2 0 0 1-2-2v-3"></path>' +
    "</svg>";
  var ICON_EXIT =
    '<svg class="ag-fs-toggle__icon-exit" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    '<path d="M9 4v3a2 2 0 0 1-2 2H4"></path>' +
    '<path d="M15 4v3a2 2 0 0 0 2 2h3"></path>' +
    '<path d="M15 20v-3a2 2 0 0 1 2-2h3"></path>' +
    '<path d="M9 20v-3a2 2 0 0 0-2-2H4"></path>' +
    "</svg>";

  var FALLBACK_CSS =
    ".ag-hud__right { display: flex; align-items: center; justify-content: flex-end; gap: 0.55rem; flex-shrink: 0; min-width: 0; }" +
    "button.ag-fs-toggle { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; width: auto; height: auto; min-height: 36px; padding: 0.38rem 0.78rem; border-radius: 9999px; border: 1px solid rgba(255, 255, 255, 0.18); background-color: rgba(255, 255, 255, 0.08); color: #E2E8F0; font-family: 'Pretendard', 'Outfit', system-ui, -apple-system, sans-serif; font-size: 0.78rem; font-weight: 800; letter-spacing: 0.01em; line-height: 1.1; white-space: nowrap; cursor: pointer; flex: 0 0 auto; -webkit-tap-highlight-color: transparent; touch-action: manipulation; transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, transform 0.16s cubic-bezier(0.16, 1, 0.3, 1); }" +
    "button.ag-fs-toggle:hover { background-color: rgba(255, 255, 255, 0.15); border-color: rgba(255, 255, 255, 0.3); color: #FFFFFF; }" +
    "button.ag-fs-toggle:active { transform: scale(0.96); }" +
    "button.ag-fs-toggle:focus-visible { outline: 3px solid var(--subject-accent, #d7ff00); outline-offset: 2px; }" +
    'button.ag-fs-toggle[aria-pressed="true"] { background-color: rgba(215, 255, 0, 0.16); border-color: rgba(215, 255, 0, 0.45); color: #F4FFB0; }' +
    'button.ag-fs-toggle[aria-pressed="true"]:hover { background-color: rgba(215, 255, 0, 0.24); color: #FFFFFF; }' +
    ".paint-page button.ag-fs-toggle { border-color: rgba(36, 49, 73, 0.22); background-color: rgba(36, 49, 73, 0.08); color: #243149; }" +
    ".paint-page button.ag-fs-toggle:hover { background-color: rgba(36, 49, 73, 0.14); border-color: rgba(36, 49, 73, 0.36); color: #111827; }" +
    '.paint-page button.ag-fs-toggle[aria-pressed="true"] { background-color: #27344b; border-color: #27344b; color: #fffdf8; }' +
    '.paint-page button.ag-fs-toggle[aria-pressed="true"]:hover { background-color: #1e293b; color: #ffffff; }' +
    ".ag-fs-toggle__icon { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; }" +
    ".ag-fs-toggle svg { display: block; width: 16px; height: 16px; }" +
    ".ag-fs-toggle__icon-exit { display: none; }" +
    'button.ag-fs-toggle[aria-pressed="true"] .ag-fs-toggle__icon-enter { display: none; }' +
    'button.ag-fs-toggle[aria-pressed="true"] .ag-fs-toggle__icon-exit { display: block; }' +
    'button.ag-fs-toggle--blocked, button.ag-fs-toggle[aria-disabled="true"] { opacity: 0.55; cursor: not-allowed; }' +
    "button.ag-fs-toggle--blocked:hover, button.ag-fs-toggle--blocked:active { background-color: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.18); color: #E2E8F0; transform: none; }" +
    "button.ag-fs-toggle--floating { position: fixed; right: max(16px, env(safe-area-inset-right)); bottom: max(16px, env(safe-area-inset-bottom)); z-index: 90; background-color: rgba(14, 18, 28, 0.96); border-color: rgba(255, 255, 255, 0.22); backdrop-filter: blur(20px) saturate(125%); -webkit-backdrop-filter: blur(20px) saturate(125%); box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.55); }" +
    "@media (max-width: 720px) { button.ag-fs-toggle { min-width: 36px; padding: 0.45rem; gap: 0; } .ag-fs-toggle__label { display: none; } }" +
    "html:fullscreen { background: #07090e; } html:-webkit-full-screen { background: #07090e; } html:-moz-full-screen { background: #07090e; }" +
    "@media (prefers-reduced-motion: reduce) { button.ag-fs-toggle { transition: none; } button.ag-fs-toggle:active { transform: none; } }";

  function ensureStyles() {
    if (doc.getElementById("ag-fullscreen-toggle-styles")) {
      return;
    }
    var style = doc.createElement("style");
    style.id = "ag-fullscreen-toggle-styles";
    style.textContent = FALLBACK_CSS;
    var target = doc.head || doc.documentElement;
    if (target) {
      target.appendChild(style);
    }
  }

  var existingButton = doc.getElementById("btn-fullscreen");
  var button = existingButton || doc.createElement("button");
  button.type = "button";
  button.className = existingButton
    ? "ag-fs-toggle hud-icon-btn hud-icon-btn--fullscreen"
    : "ag-fs-toggle";
  button.removeAttribute("data-action");
  button.setAttribute("data-ag-fullscreen-toggle", "");
  button.innerHTML =
    '<span class="ag-fs-toggle__icon" aria-hidden="true">' +
    ICON_ENTER +
    ICON_EXIT +
    "</span>" +
    '<span class="ag-fs-toggle__label"></span>';

  var label = button.querySelector(".ag-fs-toggle__label");

  function fullscreenElement() {
    return (
      doc.fullscreenElement ||
      doc.webkitFullscreenElement ||
      doc.mozFullScreenElement ||
      doc.msFullscreenElement ||
      null
    );
  }

  function isFullscreen() {
    return Boolean(fullscreenElement());
  }

  function syncState() {
    var active = isFullscreen();
    var copy = active ? LABELS.exit : LABELS.enter;
    var currentRoot = doc.documentElement || root;
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.setAttribute("aria-label", copy.aria);
    button.setAttribute("title", copy.aria);
    if (label) {
      label.textContent = copy.text;
    }
    if (currentRoot && currentRoot.classList) {
      currentRoot.classList.toggle("ag-is-fullscreen", active);
    }
  }

  var pending = false;

  function toggle() {
    if (pending) {
      return;
    }
    pending = true;
    var currentRoot = doc.documentElement || root;
    var action;
    try {
      action = isFullscreen()
        ? exitFullscreen.call(doc)
        : requestFullscreen.call(currentRoot, { navigationUI: "hide" });
    } catch (error) {
      action = Promise.reject(error);
    }
    Promise.resolve(action)
      .catch(function (error) {
        // 브라우저가 거부해도 학습 흐름은 그대로다. 상태만 실제 값으로 되돌린다.
        if (window.console && typeof window.console.info === "function") {
          window.console.info("전체 화면으로 전환하지 못했어요.", error);
        }
      })
      .then(function () {
        pending = false;
        syncState();
        if (typeof window.dispatchEvent === "function") {
          window.dispatchEvent(new Event("resize"));
        }
      });
  }

  if (!blocked) {
    button.addEventListener("click", toggle);
    root.__agFsListenersBound = true;

    [
      "fullscreenchange",
      "webkitfullscreenchange",
      "mozfullscreenchange",
      "MSFullscreenChange",
    ].forEach(function (eventName) {
      doc.addEventListener(eventName, syncState);
    });
  }

  function mount() {
    ensureStyles();
    var currentRoot = doc.documentElement || root;
    if (!blocked && currentRoot && !currentRoot.__agFsListenersBound) {
      currentRoot.__agFsListenersBound = true;
      [
        "fullscreenchange",
        "webkitfullscreenchange",
        "mozfullscreenchange",
        "MSFullscreenChange",
      ].forEach(function (eventName) {
        doc.addEventListener(eventName, syncState);
      });
    }
    var cluster =
      doc.querySelector(".ag-hud__right") ||
      doc.querySelector(".hud-top-right") ||
      doc.querySelector(".lab-topbar .top-actions") ||
      doc.querySelector(".topbar .top-actions");
    var header =
      doc.querySelector(".ag-hud") ||
      doc.querySelector(".site-header") ||
      doc.querySelector(".lab-topbar") ||
      doc.querySelector(".game-top-hud") ||
      doc.querySelector(".hud-top") ||
      doc.querySelector("header");

    // 우측 클러스터가 없는 HUD(주간 시험·보호자·실험실·미니게임 화면)도 같은 위치에 버튼을 둔다.
    if (!cluster && header) {
      cluster = doc.createElement("div");
      cluster.className = "ag-hud__right";
      header.appendChild(cluster);
    }

    if (cluster) {
      button.classList.remove("ag-fs-toggle--floating");
      if (button.parentNode !== cluster) {
        cluster.insertBefore(button, cluster.firstChild);
      }
    } else if (doc.body) {
      button.classList.add("ag-fs-toggle--floating");
      doc.body.appendChild(button);
    }
    syncState();

    if (blocked) {
      button.classList.add("ag-fs-toggle--blocked");
      button.setAttribute("aria-disabled", "true");
      button.setAttribute("title", "이 화면에서는 전체 화면을 켤 수 없어요");
    }
  }

  window.AidenFullscreenToggle = {
    mount: mount,
    syncState: syncState,
  };

  if (doc.body) {
    mount();
  } else {
    doc.addEventListener("DOMContentLoaded", mount, { once: true });
  }
})();
