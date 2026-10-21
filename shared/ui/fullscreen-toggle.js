/* ─────────────────────────────────────────────────────────────
   Aiden Game Labs — 전체 화면(Fullscreen) 토글
   태블릿에서 브라우저 크롬 없이 화면 전체를 쓰고, 같은 버튼으로 되돌아온다.

   • HUD 우측 클러스터(.ag-hud__right) 안에 버튼 하나를 주입한다.
   • HUD가 없는 화면은 우하단 floating 버튼으로 붙는다.
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

  var button = doc.createElement("button");
  button.type = "button";
  button.className = "ag-fs-toggle";
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
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.setAttribute("aria-label", copy.aria);
    button.setAttribute("title", copy.aria);
    if (label) {
      label.textContent = copy.text;
    }
    root.classList.toggle("ag-is-fullscreen", active);
  }

  var pending = false;

  function toggle() {
    if (pending) {
      return;
    }
    pending = true;
    var action;
    try {
      action = isFullscreen()
        ? exitFullscreen.call(doc)
        : requestFullscreen.call(root, { navigationUI: "hide" });
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
      });
  }

  if (!blocked) {
    button.addEventListener("click", toggle);

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
    var cluster = doc.querySelector(".ag-hud__right");
    var header = doc.querySelector(".ag-hud");

    // 우측 클러스터가 없는 HUD(주간 시험·보호자 화면)도 같은 위치에 버튼을 둔다.
    if (!cluster && header) {
      cluster = doc.createElement("div");
      cluster.className = "ag-hud__right";
      header.appendChild(cluster);
    }

    if (cluster) {
      cluster.insertBefore(button, cluster.firstChild);
    } else {
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

  if (doc.body) {
    mount();
  } else {
    doc.addEventListener("DOMContentLoaded", mount, { once: true });
  }
})();
