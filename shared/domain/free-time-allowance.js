/**
 * @fileoverview 자유시간 일일 사용량 정책 — 순수 도메인 모듈
 * @module free-time-allowance
 *
 * 브라우저 API·저장소·타이머에 의존하지 않는 순수 도메인 모듈이다.
 * 현재 시각(epoch ms)은 외부에서 명시적으로 주입한다.
 */

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.FreeTimeAllowance = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SCHEMA_VERSION = 1;
  const STORAGE_KEY = "study_youtube_free_time_daily_usage_v1";

  const DURATION_CANDIDATES = Object.freeze([10, 20, 30]);
  const MAX_SESSION_MINUTES = 30;
  const MORNING_MAX_MINUTES = 30;
  const AFTERNOON_MAX_MINUTES = 30;
  const DAILY_MAX_MINUTES = 60;

  const PERIOD = Object.freeze({
    MORNING: "morning",
    AFTERNOON: "afternoon",
  });

  const REASON = Object.freeze({
    INVALID_DURATION: "invalid_duration",
    EXCEEDS_PERIOD_ALLOWANCE: "exceeds_period_allowance",
    EXCEEDS_DAILY_ALLOWANCE: "exceeds_daily_allowance",
    CROSSES_BOUNDARY: "crosses_boundary",
  });

  function _isFiniteNumber(val) {
    return typeof val === "number" && Number.isFinite(val);
  }

  function getDateKey(now) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("getDateKey: now must be a finite number");
    }
    const d = new Date(now);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function getPeriod(now) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("getPeriod: now must be a finite number");
    }
    const d = new Date(now);
    return d.getHours() < 12 ? PERIOD.MORNING : PERIOD.AFTERNOON;
  }

  function getHalfDayBoundaryEnd(now) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("getHalfDayBoundaryEnd: now must be a finite number");
    }
    const d = new Date(now);
    const year = d.getFullYear();
    const month = d.getMonth();
    const date = d.getDate();
    if (d.getHours() < 12) {
      return new Date(year, month, date, 12, 0, 0, 0).getTime();
    } else {
      return new Date(year, month, date + 1, 0, 0, 0, 0).getTime();
    }
  }

  function getFreshUsage(dateKey) {
    return {
      schemaVersion: SCHEMA_VERSION,
      dateKey: typeof dateKey === "string" ? dateKey : "1970-01-01",
      morningMinutes: 0,
      afternoonMinutes: 0,
    };
  }

  function isValidUsageSnapshot(usage) {
    if (!usage || typeof usage !== "object" || Array.isArray(usage)) {
      return false;
    }
    if (usage.schemaVersion !== SCHEMA_VERSION) {
      return false;
    }
    if (typeof usage.dateKey !== "string" || usage.dateKey.length === 0) {
      return false;
    }
    if (
      !_isFiniteNumber(usage.morningMinutes) ||
      usage.morningMinutes < 0 ||
      !_isFiniteNumber(usage.afternoonMinutes) ||
      usage.afternoonMinutes < 0
    ) {
      return false;
    }
    return true;
  }

  function restoreUsage({ savedUsage, now }) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("restoreUsage: now must be a finite number");
    }
    const targetDateKey = getDateKey(now);

    if (!isValidUsageSnapshot(savedUsage) || savedUsage.dateKey !== targetDateKey) {
      return getFreshUsage(targetDateKey);
    }

    return {
      schemaVersion: SCHEMA_VERSION,
      dateKey: targetDateKey,
      morningMinutes: savedUsage.morningMinutes,
      afternoonMinutes: savedUsage.afternoonMinutes,
    };
  }

  function isValidDuration(durationMinutes) {
    return (
      _isFiniteNumber(durationMinutes) &&
      DURATION_CANDIDATES.includes(durationMinutes) &&
      durationMinutes <= MAX_SESSION_MINUTES
    );
  }

  function evaluateStart({ usage, now, durationMinutes }) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("evaluateStart: now must be a finite number");
    }

    if (!isValidDuration(durationMinutes)) {
      return {
        allowed: false,
        reason: REASON.INVALID_DURATION,
      };
    }

    const boundaryEnd = getHalfDayBoundaryEnd(now);
    const endsAt = now + durationMinutes * 60 * 1000;
    if (endsAt > boundaryEnd) {
      return {
        allowed: false,
        reason: REASON.CROSSES_BOUNDARY,
      };
    }

    const currentUsage = restoreUsage({ savedUsage: usage, now: now });
    const period = getPeriod(now);

    if (period === PERIOD.MORNING) {
      if (currentUsage.morningMinutes + durationMinutes > MORNING_MAX_MINUTES) {
        return {
          allowed: false,
          reason: REASON.EXCEEDS_PERIOD_ALLOWANCE,
        };
      }
    } else {
      if (currentUsage.afternoonMinutes + durationMinutes > AFTERNOON_MAX_MINUTES) {
        return {
          allowed: false,
          reason: REASON.EXCEEDS_PERIOD_ALLOWANCE,
        };
      }
    }

    const dailyTotal =
      currentUsage.morningMinutes + currentUsage.afternoonMinutes + durationMinutes;
    if (dailyTotal > DAILY_MAX_MINUTES) {
      return {
        allowed: false,
        reason: REASON.EXCEEDS_DAILY_ALLOWANCE,
      };
    }

    const nextUsage = {
      schemaVersion: SCHEMA_VERSION,
      dateKey: currentUsage.dateKey,
      morningMinutes:
        period === PERIOD.MORNING
          ? currentUsage.morningMinutes + durationMinutes
          : currentUsage.morningMinutes,
      afternoonMinutes:
        period === PERIOD.AFTERNOON
          ? currentUsage.afternoonMinutes + durationMinutes
          : currentUsage.afternoonMinutes,
    };

    return {
      allowed: true,
      period: period,
      nextUsage: nextUsage,
    };
  }

  function getRemainingQuota({ usage, now }) {
    if (!_isFiniteNumber(now)) {
      throw new TypeError("getRemainingQuota: now must be a finite number");
    }
    const currentUsage = restoreUsage({ savedUsage: usage, now: now });
    const period = getPeriod(now);
    const morningRemaining = Math.max(
      0,
      MORNING_MAX_MINUTES - currentUsage.morningMinutes
    );
    const afternoonRemaining = Math.max(
      0,
      AFTERNOON_MAX_MINUTES - currentUsage.afternoonMinutes
    );
    const dailyRemaining = Math.max(
      0,
      DAILY_MAX_MINUTES -
        (currentUsage.morningMinutes + currentUsage.afternoonMinutes)
    );
    const periodRemaining =
      period === PERIOD.MORNING ? morningRemaining : afternoonRemaining;
    const boundaryEnd = getHalfDayBoundaryEnd(now);
    const boundaryRemainingMinutes = Math.max(
      0,
      Math.floor((boundaryEnd - now) / 60000)
    );

    return {
      dateKey: currentUsage.dateKey,
      period: period,
      morningMinutes: currentUsage.morningMinutes,
      afternoonMinutes: currentUsage.afternoonMinutes,
      morningRemaining: morningRemaining,
      afternoonRemaining: afternoonRemaining,
      periodRemaining: periodRemaining,
      dailyRemaining: dailyRemaining,
      boundaryRemainingMinutes: boundaryRemainingMinutes,
      maxAllowedDuration: Math.min(
        periodRemaining,
        dailyRemaining,
        boundaryRemainingMinutes,
        MAX_SESSION_MINUTES
      ),
    };
  }

  return Object.freeze({
    SCHEMA_VERSION: SCHEMA_VERSION,
    STORAGE_KEY: STORAGE_KEY,
    DURATION_CANDIDATES: DURATION_CANDIDATES,
    MAX_SESSION_MINUTES: MAX_SESSION_MINUTES,
    MORNING_MAX_MINUTES: MORNING_MAX_MINUTES,
    AFTERNOON_MAX_MINUTES: AFTERNOON_MAX_MINUTES,
    DAILY_MAX_MINUTES: DAILY_MAX_MINUTES,
    PERIOD: PERIOD,
    REASON: REASON,
    getDateKey: getDateKey,
    getPeriod: getPeriod,
    getHalfDayBoundaryEnd: getHalfDayBoundaryEnd,
    getFreshUsage: getFreshUsage,
    isValidUsageSnapshot: isValidUsageSnapshot,
    restoreUsage: restoreUsage,
    isValidDuration: isValidDuration,
    evaluateStart: evaluateStart,
    getRemainingQuota: getRemainingQuota,
  });
});
