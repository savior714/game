/**
 * @fileoverview 자유시간 시작 트랜잭션 — 복구 가능한 원자적 커밋
 * @module free-time-session-start-transaction
 *
 * 외부 탭 생성, 15분 차감, 세션 저장을 하나의 트랜잭션 경계로 수행한다.
 * Web Storage는 다중 키 원자적 커밋이 없으므로 복구 journal을 사용한다.
 * 모든 의존성(storage, openExternal, now, sessionId, FreeTimeSession)은 외부 주입이다.
 */

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.FreeTimeSessionStartTransaction = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const REWARD_STORAGE_KEY = "study_rewards";
  const SESSION_STORAGE_KEY = "study_youtube_free_time_session_v1";
  const JOURNAL_STORAGE_KEY = "study_youtube_free_time_start_tx_v1";

  const JOURNAL_SCHEMA_VERSION = 1;
  const CHARGE_MINUTES = 15;

  const RESULT = Object.freeze({
    STARTED: "started",
    ALREADY_ACTIVE: "already_active",
    INSUFFICIENT_TIME: "insufficient_time",
    POPUP_BLOCKED: "popup_blocked",
    CORRUPT_REWARD_STATE: "corrupt_reward_state",
    COMMIT_FAILED: "commit_failed",
    RECOVERY_REQUIRED: "recovery_required",
    CORRUPT_TRANSACTION_JOURNAL: "corrupt_transaction_journal",
    NO_PENDING_TRANSACTION: "no_pending_transaction",
    FINALIZED_COMMITTED_TRANSACTION: "finalized_committed_transaction",
    ROLLED_BACK_INCOMPLETE_TRANSACTION: "rolled_back_incomplete_transaction",
  });

  function _isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function _isValidJournal(j) {
    if (!_isPlainObject(j)) return false;
    if (j.version !== JOURNAL_SCHEMA_VERSION) return false;
    if (typeof j.transactionId !== "string" || j.transactionId.length === 0) return false;
    if (j.previousRewardRaw === undefined) return false;
    if (j.previousSessionRaw === undefined) return false;
    if (typeof j.targetRewardRaw !== "string") return false;
    if (typeof j.targetSessionRaw !== "string") return false;
    return true;
  }

  function _restoreRaw(storage, key, previousRaw) {
    if (previousRaw === null) {
      storage.removeItem(key);
    } else {
      storage.setItem(key, previousRaw);
    }
  }

  function _closeHandle(handle) {
    if (handle && typeof handle.close === "function") {
      try {
        handle.close();
      } catch (e) {
        // best-effort: close failure must not affect rollback result
      }
    }
  }

  function _rollbackStorage(storage, previousRewardRaw, previousSessionRaw) {
    try {
      _restoreRaw(storage, REWARD_STORAGE_KEY, previousRewardRaw);
      _restoreRaw(storage, SESSION_STORAGE_KEY, previousSessionRaw);
      try {
        storage.removeItem(JOURNAL_STORAGE_KEY);
      } catch (e) {
        // journal left for recovery
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  function recoverPendingTransaction(deps) {
    const storage = deps.storage;

    const journalRaw = storage.getItem(JOURNAL_STORAGE_KEY);
    if (journalRaw === null) {
      return { code: RESULT.NO_PENDING_TRANSACTION };
    }

    let journal;
    try {
      journal = JSON.parse(journalRaw);
    } catch (e) {
      return { code: RESULT.CORRUPT_TRANSACTION_JOURNAL };
    }

    if (!_isValidJournal(journal)) {
      return { code: RESULT.CORRUPT_TRANSACTION_JOURNAL };
    }

    const currentRewardRaw = storage.getItem(REWARD_STORAGE_KEY);
    const currentSessionRaw = storage.getItem(SESSION_STORAGE_KEY);

    const rewardMatches = currentRewardRaw === journal.targetRewardRaw;
    const sessionMatches = currentSessionRaw === journal.targetSessionRaw;

    if (rewardMatches && sessionMatches) {
      storage.removeItem(JOURNAL_STORAGE_KEY);
      let session = null;
      try {
        session = JSON.parse(journal.targetSessionRaw);
      } catch (e) {
        session = null;
      }
      return {
        code: RESULT.FINALIZED_COMMITTED_TRANSACTION,
        session: session,
      };
    }

    _restoreRaw(storage, REWARD_STORAGE_KEY, journal.previousRewardRaw);
    _restoreRaw(storage, SESSION_STORAGE_KEY, journal.previousSessionRaw);
    storage.removeItem(JOURNAL_STORAGE_KEY);

    return { code: RESULT.ROLLED_BACK_INCOMPLETE_TRANSACTION };
  }

  function attemptStart(deps) {
    if (!deps || typeof deps !== "object") {
      throw new TypeError("attemptStart: deps required");
    }

    const storage = deps.storage;
    const openExternal = deps.openExternal;
    const now = deps.now;
    const sessionId = deps.sessionId;
    const FreeTimeSession = deps.FreeTimeSession;

    if (
      !storage ||
      typeof storage.getItem !== "function" ||
      typeof storage.setItem !== "function" ||
      typeof storage.removeItem !== "function"
    ) {
      throw new TypeError("attemptStart: storage must implement getItem, setItem, removeItem");
    }
    if (typeof openExternal !== "function") {
      throw new TypeError("attemptStart: openExternal must be a function");
    }
    if (typeof now !== "number" || !Number.isFinite(now)) {
      throw new TypeError("attemptStart: now must be a finite number");
    }
    if (typeof sessionId !== "string" || sessionId.length === 0) {
      throw new TypeError("attemptStart: sessionId must be a non-empty string");
    }
    if (
      !FreeTimeSession ||
      typeof FreeTimeSession.start !== "function" ||
      typeof FreeTimeSession.restore !== "function" ||
      typeof FreeTimeSession.select !== "function"
    ) {
      throw new TypeError("attemptStart: FreeTimeSession must implement start, restore, select");
    }

    let recovery;
    try {
      recovery = recoverPendingTransaction({ storage });
    } catch (e) {
      return { code: RESULT.CORRUPT_TRANSACTION_JOURNAL };
    }
    if (recovery.code === RESULT.CORRUPT_TRANSACTION_JOURNAL) {
      return { code: RESULT.CORRUPT_TRANSACTION_JOURNAL };
    }

    const sessionRawIn = storage.getItem(SESSION_STORAGE_KEY);
    if (sessionRawIn !== null) {
      let savedSession = null;
      try {
        savedSession = JSON.parse(sessionRawIn);
      } catch (e) {
        savedSession = null;
      }
      if (savedSession) {
        const restored = FreeTimeSession.restore({ savedSession: savedSession, now: now });
        const selection = FreeTimeSession.select(restored, now);
        if (selection.active) {
          return {
            code: RESULT.ALREADY_ACTIVE,
            session: restored,
          };
        }
      }
    }

    const rewardRawIn = storage.getItem(REWARD_STORAGE_KEY);
    let reward;
    try {
      reward = JSON.parse(rewardRawIn);
    } catch (e) {
      return { code: RESULT.CORRUPT_REWARD_STATE };
    }
    if (!_isPlainObject(reward)) {
      return { code: RESULT.CORRUPT_REWARD_STATE };
    }
    const minutes = reward.youtube_minutes;
    if (
      typeof minutes !== "number" ||
      !Number.isFinite(minutes) ||
      minutes < CHARGE_MINUTES
    ) {
      return { code: RESULT.INSUFFICIENT_TIME };
    }

    let handle;
    try {
      handle = openExternal();
    } catch (e) {
      return { code: RESULT.POPUP_BLOCKED };
    }
    if (handle === null || handle === undefined) {
      return { code: RESULT.POPUP_BLOCKED };
    }

    const targetReward = Object.assign({}, reward, {
      youtube_minutes: minutes - CHARGE_MINUTES,
      last_updated: new Date(now).toISOString(),
      _updated_at: now,
    });
    const targetSession = FreeTimeSession.start({
      now: now,
      sessionId: sessionId,
      source: "reward",
    });

    const previousRewardRaw = rewardRawIn;
    const previousSessionRaw = sessionRawIn;
    const targetRewardRaw = JSON.stringify(targetReward);
    const targetSessionRaw = JSON.stringify(targetSession);

    const journal = {
      version: JOURNAL_SCHEMA_VERSION,
      transactionId: sessionId,
      previousRewardRaw: previousRewardRaw,
      previousSessionRaw: previousSessionRaw,
      targetRewardRaw: targetRewardRaw,
      targetSessionRaw: targetSessionRaw,
    };

    try {
      storage.setItem(JOURNAL_STORAGE_KEY, JSON.stringify(journal));
    } catch (e) {
      _closeHandle(handle);
      return { code: RESULT.COMMIT_FAILED };
    }

    try {
      storage.setItem(REWARD_STORAGE_KEY, targetRewardRaw);
    } catch (e) {
      const rollbackOk = _rollbackStorage(storage, previousRewardRaw, previousSessionRaw);
      _closeHandle(handle);
      return { code: rollbackOk ? RESULT.COMMIT_FAILED : RESULT.RECOVERY_REQUIRED };
    }

    try {
      storage.setItem(SESSION_STORAGE_KEY, targetSessionRaw);
    } catch (e) {
      const rollbackOk = _rollbackStorage(storage, previousRewardRaw, previousSessionRaw);
      _closeHandle(handle);
      return { code: rollbackOk ? RESULT.COMMIT_FAILED : RESULT.RECOVERY_REQUIRED };
    }

    try {
      storage.removeItem(JOURNAL_STORAGE_KEY);
    } catch (e) {
      // data already committed — journal cleanup failure does not invalidate success
    }

    return {
      code: RESULT.STARTED,
      session: targetSession,
      handle: handle,
    };
  }

  return Object.freeze({
    RESULT: RESULT,
    attemptStart: attemptStart,
    recoverPendingTransaction: recoverPendingTransaction,
  });
});
