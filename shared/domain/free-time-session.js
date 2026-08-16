/**
 * @fileoverview 자유시간 세션 — 순수 상태 모델
 * @module free-time-session
 *
 * 브라우저 API·저장소·타이머에 의존하지 않는 순수 도메인 모듈이다.
 * 현재 시각은 외부에서 명시적으로 주입한다.
 */

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.FreeTimeSession = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const DURATION_MS = 600000;
  const CHARGED_MINUTES = 10;
  const ALLOWED_DURATIONS = Object.freeze([10, 20, 30]);
  const SCHEMA_VERSION = 1;

  const STATUS = Object.freeze({
    INACTIVE: "inactive",
    RUNNING: "running",
    EXPIRED: "expired",
    ACKNOWLEDGED: "acknowledged",
  });

  function _isFiniteNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function _isValidSnapshot(session) {
    if (!session || typeof session !== "object") return false;
    if (session.schemaVersion !== SCHEMA_VERSION) return false;
    if (typeof session.sessionId !== "string") return false;
    if (
      !_isFiniteNumber(session.startedAt) ||
      !_isFiniteNumber(session.endsAt)
    ) {
      return false;
    }
    if (
      session.durationMs !== undefined &&
      !_isFiniteNumber(session.durationMs)
    ) {
      return false;
    }
    if (
      session.chargedMinutes !== undefined &&
      !_isFiniteNumber(session.chargedMinutes)
    ) {
      return false;
    }
    return true;
  }

  function _expiredSession(session, now) {
    const durationMs = _isFiniteNumber(session.durationMs)
      ? session.durationMs
      : DURATION_MS;
    const chargedMinutes = _isFiniteNumber(session.chargedMinutes)
      ? session.chargedMinutes
      : CHARGED_MINUTES;

    return {
      schemaVersion: session.schemaVersion,
      sessionId: session.sessionId,
      status: STATUS.EXPIRED,
      startedAt: session.startedAt,
      endsAt: session.endsAt,
      durationMs: durationMs,
      chargedMinutes: chargedMinutes,
      source: session.source,
      warningEmittedAt: session.warningEmittedAt,
      expiredAt: session.expiredAt == null ? now : session.expiredAt,
      acknowledgedAt: session.acknowledgedAt,
    };
  }

  function start({ now, sessionId, source, durationMinutes = 10 }) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("start: now must be a finite number");
    }
    if (typeof sessionId !== "string" || sessionId.length === 0) {
      throw new TypeError("start: sessionId must be a non-empty string");
    }
    const duration = durationMinutes === undefined ? 10 : durationMinutes;
    if (!ALLOWED_DURATIONS.includes(duration)) {
      throw new TypeError("start: durationMinutes must be 10, 20, or 30");
    }

    const durationMs = duration * 60000;
    const chargedMinutes = duration;

    return {
      schemaVersion: SCHEMA_VERSION,
      sessionId: sessionId,
      status: STATUS.RUNNING,
      startedAt: now,
      endsAt: now + durationMs,
      durationMs: durationMs,
      chargedMinutes: chargedMinutes,
      source: source == null ? null : source,
      warningEmittedAt: null,
      expiredAt: null,
      acknowledgedAt: null,
    };
  }

  function startIfInactive({ currentSession, now, sessionId, source, durationMinutes }) {
    if (currentSession && _isActive(currentSession, now)) {
      return {
        started: false,
        session: currentSession,
      };
    }

    return {
      started: true,
      session: start({
        now: now,
        sessionId: sessionId,
        source: source,
        durationMinutes: durationMinutes,
      }),
    };
  }

  function restore({ savedSession, now }) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("restore: now must be a finite number");
    }

    if (!_isValidSnapshot(savedSession)) {
      return {
        schemaVersion: SCHEMA_VERSION,
        sessionId: null,
        status: STATUS.INACTIVE,
        startedAt: null,
        endsAt: null,
        durationMs: DURATION_MS,
        chargedMinutes: CHARGED_MINUTES,
        source: null,
        warningEmittedAt: null,
        expiredAt: null,
        acknowledgedAt: null,
      };
    }

    const durationMs = _isFiniteNumber(savedSession.durationMs)
      ? savedSession.durationMs
      : DURATION_MS;
    const chargedMinutes = _isFiniteNumber(savedSession.chargedMinutes)
      ? savedSession.chargedMinutes
      : CHARGED_MINUTES;

    if (savedSession.status === STATUS.ACKNOWLEDGED) {
      return { ...savedSession, durationMs, chargedMinutes };
    }

    if (savedSession.endsAt > now) {
      return { ...savedSession, durationMs, chargedMinutes };
    }

    return _expiredSession(savedSession, now);
  }

  function _isActive(session, now) {
    return (
      _isValidSnapshot(session) &&
      session.status === STATUS.RUNNING &&
      session.endsAt > now
    );
  }

  function _isExpired(session, now) {
    if (!_isValidSnapshot(session)) return false;
    if (session.status === STATUS.ACKNOWLEDGED) return false;
    if (session.status === STATUS.EXPIRED) return true;
    return session.endsAt <= now;
  }

  function select(session, now) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("select: now must be a finite number");
    }

    const active = _isActive(session, now);
    const expired = _isExpired(session, now);
    const remainingMs = active ? Math.max(0, session.endsAt - now) : 0;

    return {
      active: active,
      expired: expired,
      remainingMs: remainingMs,
      sessionId: session && session.sessionId ? session.sessionId : null,
      status: session && session.status ? session.status : STATUS.INACTIVE,
    };
  }

  return Object.freeze({
    DURATION_MS: DURATION_MS,
    CHARGED_MINUTES: CHARGED_MINUTES,
    ALLOWED_DURATIONS: ALLOWED_DURATIONS,
    SCHEMA_VERSION: SCHEMA_VERSION,
    STATUS: STATUS,
    start: start,
    startIfInactive: startIfInactive,
    restore: restore,
    select: select,
  });
});
