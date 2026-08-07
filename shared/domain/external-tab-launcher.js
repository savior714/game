/**
 * @fileoverview 외부 탭 생성 어댑터 — noopener + 성공/차단 구분
 * @module external-tab-launcher
 *
 * window.open(url, '_blank', 'noopener') 방식은 표준상 null을 반환하므로
 * 성공과 차단을 구분할 수 없다. 이 어댑터는 두 단계로 이를 해결한다.
 *
 * 1. window.open('about:blank', '_blank') — 빈 탭 핸들 확보 (null이면 차단)
 * 2. handle.opener = null — opener 끊기
 * 3. handle.location.href = targetUrl — 대상 URL로 이동
 *
 * 모든 처리는 동기식이다. Promise/await/timer를 사용하지 않는다.
 */

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ExternalTabLauncher = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var BLANK_URL = "about:blank";

  function _closeHandle(handle) {
    if (handle && typeof handle.close === "function") {
      try {
        handle.close();
      } catch (e) {
        // best-effort
      }
    }
  }

  /**
   * 빈 탭 핸들을 확보한 후 opener를 끊고 대상 URL로 이동시킨다.
   * @param {Window} win — window.open을 호출할 window 객체
   * @param {string} targetUrl — 최종 이동 대상 URL
   * @returns {{ok: boolean, handle: Window|null}} 성공 시 ok=true + handle, 실패 시 ok=false
   */
  function launch(win, targetUrl) {
    if (!win || typeof win.open !== "function") {
      return { ok: false, handle: null };
    }

    // Step 1: 빈 탭 확보 — 첫 window.open() 호출
    var handle;
    try {
      handle = win.open(BLANK_URL, "_blank");
    } catch (e) {
      return { ok: false, handle: null };
    }

    // null = popup blocked
    if (handle === null || handle === undefined) {
      return { ok: false, handle: null };
    }

    // Step 2: opener 끊기 — navigation 전에 반드시 수행
    try {
      handle.opener = null;
    } catch (e) {
      _closeHandle(handle);
      return { ok: false, handle: null };
    }

    // Step 3: 대상 URL로 이동
    try {
      handle.location.href = targetUrl;
    } catch (e) {
      _closeHandle(handle);
      return { ok: false, handle: null };
    }

    return { ok: true, handle: handle };
  }

  /**
   * FreeTimeSessionStartTransaction의 openExternal DI와 호환되는 함수를 생성한다.
   * @param {Window} win — window 객체
   * @param {string} targetUrl — 열 대상 URL
   * @returns {function(): Window|null} 트랜잭션이 인자 없이 호출하는 openExternal
   */
  function createOpenExternal(win, targetUrl) {
    return function openExternal() {
      var result = launch(win, targetUrl);
      return result.ok ? result.handle : null;
    };
  }

  return Object.freeze({
    launch: launch,
    createOpenExternal: createOpenExternal,
  });
});
