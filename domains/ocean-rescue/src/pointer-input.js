// @ts-check
/// <reference path="./contracts/ocean-rescue-global.d.ts" />

/**
 * Shared pointer-coordinate runtime boundary for Ocean Rescue (WP-32B).
 *
 * This module owns the exact browser-client -> Ocean Rescue logical
 * coordinate transformations that previously lived inline in `src/app.js`
 * plus the normalized scene pointer-intent constructors:
 *
 * - `mapTravelStageY(event, canvas)`: travel pointer event -> logical stage Y;
 * - `mapRescuePoint(event, canvas)`: rescue pointer event -> logical `{ x, y }`;
 * - `activeIntent(point)`: normalized `{ active: true, x, y }` intent;
 * - `inactiveIntent()`: normalized `{ active: false, x: null, y: null }` intent.
 *
 * Both the canonical ESM lane and the legacy ordered-script lane execute this
 * same implementation. The only RenderRuntime dependency is the minimal
 * coordinate-mapper subset (`isReady()` + `mapClientToLogical(clientX,
 * clientY)`); no other renderer method is read or invoked. The module is an
 * IIFE global with no imports, no dynamic imports, and no runtime network
 * access so it can run unchanged in the legacy rollback graph. Because the
 * legacy builder rejects the raw dynamic-import token in ordered-script
 * sources, the local checked-JS types are declared structurally with
 * `@typedef` here; the canonical ESM adapters carry the JSDoc type-reference
 * form against `src/contracts/pointer-input.ts`.
 */

/**
 * @typedef {object} LogicalPoint
 * @property {number} x
 * @property {number} y
 */

/**
 * @typedef {object} ClientCoordinateCarrier
 * @property {number} clientX
 * @property {number} clientY
 */

/**
 * @typedef {object} BoundingRect
 * @property {number} left
 * @property {number} top
 * @property {number} width
 * @property {number} height
 */

/**
 * @typedef {object} RectProvider
 * @property {() => BoundingRect} getBoundingClientRect
 */

/**
 * @typedef {object} ActivePointerIntent
 * @property {true} active
 * @property {number} x
 * @property {number} y
 */

/**
 * @typedef {object} InactivePointerIntent
 * @property {false} active
 * @property {null} x
 * @property {null} y
 */

(function () {
  "use strict";

  var RenderRuntime =
    window.OceanRescue && window.OceanRescue.RenderRuntime
      ? window.OceanRescue.RenderRuntime
      : null;

  /**
   * @param {unknown} value
   * @returns {boolean}
   */
  function finiteNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  /**
   * Map a travel pointer event to a logical stage Y, preserving the exact
   * validation order and results of the original `app.js` `mapClientYToStage`.
   *
   * @param {ClientCoordinateCarrier} event
   * @param {RectProvider | null | undefined} canvas
   * @returns {number | null}
   */
  function mapTravelStageY(event, canvas) {
    if (typeof event.clientY !== "number" || !isFinite(event.clientY)) {
      return null;
    }
    if (!canvas) {
      return null;
    }
    if (typeof canvas.getBoundingClientRect !== "function") {
      return null;
    }
    var rect = canvas.getBoundingClientRect();
    if (!rect || typeof rect !== "object") {
      return null;
    }
    if (
      typeof rect.height !== "number" ||
      !isFinite(rect.height) ||
      rect.height <= 0
    ) {
      return null;
    }
    if (RenderRuntime && RenderRuntime.isReady()) {
      var mapped = RenderRuntime.mapClientToLogical(
        typeof event.clientX === "number" ? event.clientX : rect.left,
        event.clientY
      );
      return isFinite(mapped.y) ? mapped.y : null;
    }
    return (event.clientY - rect.top) * (720 / rect.height);
  }

  /**
   * Map a rescue pointer event to a logical `{ x, y }` point, preserving the
   * exact validation order and results of the original `app.js`
   * `mapRescueCoordinates`. The renderer `inside` flag never alters
   * acceptance, exactly as before.
   *
   * @param {ClientCoordinateCarrier} event
   * @param {RectProvider | null | undefined} canvas
   * @returns {LogicalPoint | null}
   */
  function mapRescuePoint(event, canvas) {
    if (!canvas) {
      return null;
    }
    if (typeof canvas.getBoundingClientRect !== "function") {
      return null;
    }
    var rect = canvas.getBoundingClientRect();
    if (!rect || typeof rect !== "object") {
      return null;
    }
    if (typeof rect.left !== "number" || !isFinite(rect.left)) {
      return null;
    }
    if (typeof rect.top !== "number" || !isFinite(rect.top)) {
      return null;
    }
    if (
      typeof rect.width !== "number" ||
      !isFinite(rect.width) ||
      rect.width <= 0
    ) {
      return null;
    }
    if (
      typeof rect.height !== "number" ||
      !isFinite(rect.height) ||
      rect.height <= 0
    ) {
      return null;
    }
    var mapped = null;
    if (RenderRuntime && RenderRuntime.isReady()) {
      mapped = RenderRuntime.mapClientToLogical(event.clientX, event.clientY);
    } else {
      mapped = {
        x: (event.clientX - rect.left) * (1280 / rect.width),
        y: (event.clientY - rect.top) * (720 / rect.height)
      };
    }
    var x = mapped.x;
    var y = mapped.y;
    if (!isFinite(x) || !isFinite(y)) {
      return null;
    }
    return { x: x, y: y };
  }

  /**
   * Build a normalized active scene pointer intent.
   *
   * A valid finite `{ x, y }` point yields the exact literal the app used to
   * pass: `{ active: true, x, y }` with that key order. Invalid input (a
   * missing/null point or non-finite coordinates) yields the inactive intent;
   * this baseline is fixed by the WP-32B focused tests. The result is a fresh,
   * non-frozen plain object on every call.
   *
   * @param {LogicalPoint | null | undefined} point
   * @returns {ActivePointerIntent | InactivePointerIntent}
   */
  function activeIntent(point) {
    if (!point) {
      return inactiveIntent();
    }
    if (!finiteNumber(point.x) || !finiteNumber(point.y)) {
      return inactiveIntent();
    }
    return { active: true, x: point.x, y: point.y };
  }

  /**
   * Build a normalized inactive scene pointer intent: `{ active: false, x:
   * null, y: null }` with that exact key order. The result is a fresh,
   * non-frozen plain object on every call.
   *
   * @returns {InactivePointerIntent}
   */
  function inactiveIntent() {
    return { active: false, x: null, y: null };
  }

  window.OceanRescue = window.OceanRescue || {};
  window.OceanRescue.PointerInput = Object.freeze({
    mapTravelStageY: mapTravelStageY,
    mapRescuePoint: mapRescuePoint,
    activeIntent: activeIntent,
    inactiveIntent: inactiveIntent
  });
})();
