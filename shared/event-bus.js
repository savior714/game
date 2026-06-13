/**
 * GameEvents - 전역 이벤트 버스
 * emit / on / off 메서드 제공, 기존 window.dispatchEvent/addEventListener와 호환
 * @module GameEvents
 */
(function (global) {
  /** @type {Object.<string, Array<Function>>} */
  var listeners = {};

  /**
   * 이벤트 리스너 등록
   * @param {string} event - 이벤트 이름
   * @param {Function} callback - 콜백 함수
   * @returns {Function} unregister 함수
   */
  function on(event, callback) {
    if (!listeners[event]) {
      listeners[event] = [];
    }
    listeners[event].push(callback);

    return function () {
      listeners[event] = listeners[event].filter(function (cb) {
        return cb !== callback;
      });
    };
  }

  /**
   * 이벤트 리스너 해제
   * @param {string} event - 이벤트 이름
   * @param {Function} callback - 해제할 콜백 함수
   */
  function off(event, callback) {
    if (listeners[event]) {
      listeners[event] = listeners[event].filter(function (cb) {
        return cb !== callback;
      });
    }
  }

  /**
   * 이벤트 발생
   * @param {string} event - 이벤트 이름
   * @param {*} [data] - 이벤트 데이터
   */
  function emit(event, data) {
    if (listeners[event]) {
      for (var i = 0; i < listeners[event].length; i++) {
        listeners[event][i](data);
      }
    }
  }

  /**
   * GameEvents 전역 객체
   * @typedef {Object} GameEvents
   * @property {typeof on} on
   * @property {typeof off} off
   * @property {typeof emit} emit
   */

  /** @type {GameEvents} */
  global.GameEvents = { on: on, off: off, emit: emit };
})(window);
