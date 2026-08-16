/**
 * @fileoverview AidenGame 로컬 백업 및 복원 코어 모듈 (Local Backup & Restore Core v1)
 * @module reward/guardian/local-backup
 *
 * 브라우저 localStorage의 핵심 사용자 데이터(수학 학습 증거, 일일 목표, 보상/영수증, 보호자 설정 등)를
 * 버전 관리된 단일 JSON 백업 파일로 내보내고, 사전 검증 및 안전한 롤백을 통해 복원하는 순수 로직.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.LocalBackupCore = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const FORMAT_MARKER = 'aidengame-local-backup';
  const SCHEMA_VERSION = 1;
  const APP_IDENTIFIER = 'AidenGame';

  const STORAGE_KEYS = Object.freeze({
    MATH_EVIDENCE: 'aiden_math_learning_evidence_v1',
    MATH_DAILY_GOAL: 'aiden_math_daily_goal_v1',
    MATH_GOAL_PREFERENCE: 'aiden_math_goal_preference_v1',
    MATH_STREAK: 'aiden_math_streak_v1',
    STUDY_REWARDS: 'study_rewards',
    RECEIPT_PREFIX: 'aiden_receipt_',
    WEEKLY_WORDS: 'englishWeeklyWords',
    SUBJECT_STATS_MATH: 'aiden_math_stats',
    SUBJECT_STATS_ENGLISH: 'aiden_english_stats',
    SUBJECT_STATS_KOREAN: 'aiden_korean_stats',
    SUBJECT_STATS_SCIENCE: 'aiden_science_stats',
    SESSION_LOG: 'aiden_session_log',
    SYNC_QUEUE: 'sync_queue',
  });

  const SUBJECT_STAT_KEYS = Object.freeze([
    STORAGE_KEYS.SUBJECT_STATS_MATH,
    STORAGE_KEYS.SUBJECT_STATS_ENGLISH,
    STORAGE_KEYS.SUBJECT_STATS_KOREAN,
    STORAGE_KEYS.SUBJECT_STATS_SCIENCE,
  ]);

  function _getStorage(customStorage) {
    if (customStorage) return customStorage;
    if (typeof localStorage !== 'undefined') return localStorage;
    return null;
  }

  function _safeJsonParse(str) {
    if (!str || typeof str !== 'string') return null;
    try {
      return JSON.parse(str);
    } catch (e) {
      return null;
    }
  }

  function _findReceiptKeys(storage) {
    const receiptKeys = [];
    if (!storage) return receiptKeys;

    if (typeof storage.length === 'number' && typeof storage.key === 'function') {
      for (let i = 0; i < storage.length; i++) {
        const k = storage.key(i);
        if (k && k.startsWith(STORAGE_KEYS.RECEIPT_PREFIX)) {
          receiptKeys.push(k);
        }
      }
    } else if (typeof storage === 'object') {
      for (const k of Object.keys(storage)) {
        if (k.startsWith(STORAGE_KEYS.RECEIPT_PREFIX)) {
          receiptKeys.push(k);
        }
      }
    }
    return receiptKeys;
  }

  /**
   * 1. 현재 로컬 스토리지 상태로부터 버전 관리된 백업 스냅샷 객체 생성
   * @param {Object} [options]
   * @returns {Object} Backup Snapshot JSON
   */
  function createBackupSnapshot(options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const now = typeof opts.now === 'number' ? opts.now : Date.now();
    const isoDate = new Date(now).toISOString();

    const snapshot = {
      format: FORMAT_MARKER,
      schemaVersion: SCHEMA_VERSION,
      app: APP_IDENTIFIER,
      exportedAt: isoDate,
      datasets: {},
    };

    if (!storage || typeof storage.getItem !== 'function') {
      return snapshot;
    }

    // 1. Math Evidence
    const rawMathEvidence = storage.getItem(STORAGE_KEYS.MATH_EVIDENCE);
    if (rawMathEvidence) {
      const parsed = _safeJsonParse(rawMathEvidence);
      snapshot.datasets.mathEvidence = {
        storageKey: STORAGE_KEYS.MATH_EVIDENCE,
        present: Boolean(parsed),
        data: parsed,
      };
    } else {
      snapshot.datasets.mathEvidence = {
        storageKey: STORAGE_KEYS.MATH_EVIDENCE,
        present: false,
        data: null,
      };
    }

    // 2. Math Daily Goal
    const rawDailyGoal = storage.getItem(STORAGE_KEYS.MATH_DAILY_GOAL);
    if (rawDailyGoal) {
      const parsed = _safeJsonParse(rawDailyGoal);
      snapshot.datasets.mathDailyGoal = {
        storageKey: STORAGE_KEYS.MATH_DAILY_GOAL,
        present: Boolean(parsed),
        data: parsed,
      };
    } else {
      snapshot.datasets.mathDailyGoal = {
        storageKey: STORAGE_KEYS.MATH_DAILY_GOAL,
        present: false,
        data: null,
      };
    }

    // 2.5 Math Goal Preference
    const rawGoalPref = storage.getItem(STORAGE_KEYS.MATH_GOAL_PREFERENCE);
    if (rawGoalPref) {
      const parsed = _safeJsonParse(rawGoalPref);
      snapshot.datasets.mathGoalPreference = {
        storageKey: STORAGE_KEYS.MATH_GOAL_PREFERENCE,
        present: Boolean(parsed),
        data: parsed,
      };
    } else {
      snapshot.datasets.mathGoalPreference = {
        storageKey: STORAGE_KEYS.MATH_GOAL_PREFERENCE,
        present: false,
        data: null,
      };
    }

    // 2.6 Math Streak
    const rawStreak = storage.getItem(STORAGE_KEYS.MATH_STREAK);
    if (rawStreak) {
      const parsed = _safeJsonParse(rawStreak);
      snapshot.datasets.mathStreak = {
        storageKey: STORAGE_KEYS.MATH_STREAK,
        present: Boolean(parsed),
        data: parsed,
      };
    } else {
      snapshot.datasets.mathStreak = {
        storageKey: STORAGE_KEYS.MATH_STREAK,
        present: false,
        data: null,
      };
    }

    // 3. Study Rewards
    const rawRewards = storage.getItem(STORAGE_KEYS.STUDY_REWARDS);
    if (rawRewards) {
      const parsed = _safeJsonParse(rawRewards);
      snapshot.datasets.studyRewards = {
        storageKey: STORAGE_KEYS.STUDY_REWARDS,
        present: Boolean(parsed),
        data: parsed,
      };
    } else {
      snapshot.datasets.studyRewards = {
        storageKey: STORAGE_KEYS.STUDY_REWARDS,
        present: false,
        data: null,
      };
    }

    // 4. Math Receipts (individual aiden_receipt_* records)
    const receiptKeys = _findReceiptKeys(storage);
    if (receiptKeys.length > 0) {
      const receiptsData = {};
      for (const rk of receiptKeys) {
        const raw = storage.getItem(rk);
        const parsed = _safeJsonParse(raw);
        if (parsed) {
          receiptsData[rk] = parsed;
        }
      }
      snapshot.datasets.mathReceipts = {
        present: Object.keys(receiptsData).length > 0,
        data: receiptsData,
      };
    } else {
      snapshot.datasets.mathReceipts = {
        present: false,
        data: {},
      };
    }

    // 5. Guardian Weekly Words
    const rawWords = storage.getItem(STORAGE_KEYS.WEEKLY_WORDS);
    if (rawWords) {
      const parsed = _safeJsonParse(rawWords);
      snapshot.datasets.guardianWeeklyWords = {
        storageKey: STORAGE_KEYS.WEEKLY_WORDS,
        present: Boolean(parsed),
        data: parsed,
      };
    } else {
      snapshot.datasets.guardianWeeklyWords = {
        storageKey: STORAGE_KEYS.WEEKLY_WORDS,
        present: false,
        data: null,
      };
    }

    // 6. Guardian Subject Stats
    const statsData = {};
    let hasStats = false;
    for (const sk of SUBJECT_STAT_KEYS) {
      const raw = storage.getItem(sk);
      if (raw) {
        const parsed = _safeJsonParse(raw);
        if (parsed) {
          statsData[sk] = parsed;
          hasStats = true;
        }
      }
    }
    snapshot.datasets.guardianSubjectStats = {
      present: hasStats,
      data: statsData,
    };

    // 7. Guardian Session Log
    const rawLog = storage.getItem(STORAGE_KEYS.SESSION_LOG);
    if (rawLog) {
      const parsed = _safeJsonParse(rawLog);
      snapshot.datasets.guardianSessionLog = {
        storageKey: STORAGE_KEYS.SESSION_LOG,
        present: Boolean(parsed),
        data: parsed,
      };
    } else {
      snapshot.datasets.guardianSessionLog = {
        storageKey: STORAGE_KEYS.SESSION_LOG,
        present: false,
        data: null,
      };
    }

    return snapshot;
  }

  /**
   * 2. 백업 데이터 유효성 검사 (Validate Before Write)
   * @param {*} payload
   * @returns {{ valid: boolean, errors: string[], summary: Object }}
   */
  function validateBackup(payload) {
    const errors = [];
    const summary = {
      format: null,
      schemaVersion: null,
      exportedAt: null,
      mathEvidenceCount: 0,
      hasDailyGoal: false,
      dailyGoalDate: null,
      mathGoalPresetId: null,
      hasMathStreak: false,
      mathCurrentStreak: 0,
      gems: 0,
      youtubeMinutes: 0,
      rewardItemsCount: 0,
      receiptsCount: 0,
      weeklyWordsCount: 0,
      hasSubjectStats: false,
      hasSessionLog: false,
    };

    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return {
        valid: false,
        errors: ['백업 데이터가 올바른 JSON 객체 형식이 아닙니다.'],
        summary: summary,
      };
    }

    // 포맷 마커 확인
    if (payload.format !== FORMAT_MARKER) {
      errors.push(`지원하지 않는 백업 파일 형식입니다. (format: ${payload.format || '없음'})`);
    } else {
      summary.format = payload.format;
    }

    // 스키마 버전 확인
    if (payload.schemaVersion !== SCHEMA_VERSION) {
      errors.push(`지원하지 않는 백업 스키마 버전입니다. (v${payload.schemaVersion}, 현재 지원: v${SCHEMA_VERSION})`);
    } else {
      summary.schemaVersion = payload.schemaVersion;
    }

    // 생성 날짜 확인
    if (typeof payload.exportedAt === 'string' && payload.exportedAt.length > 0) {
      summary.exportedAt = payload.exportedAt;
    } else {
      errors.push('백업 생성 시각(exportedAt)이 누락되었습니다.');
    }

    // Datasets 객체 확인
    const datasets = payload.datasets;
    if (!datasets || typeof datasets !== 'object' || Array.isArray(datasets)) {
      errors.push('백업 데이터셋(datasets)이 누락되었거나 올바르지 않습니다.');
      return { valid: false, errors: errors, summary: summary };
    }

    // 1. Math Evidence 검증
    if (datasets.mathEvidence) {
      if (datasets.mathEvidence.present) {
        const data = datasets.mathEvidence.data;
        if (!data || typeof data !== 'object' || !Array.isArray(data.items)) {
          errors.push('수학 학습 기록 데이터(mathEvidence)의 구조가 올바르지 않습니다.');
        } else {
          summary.mathEvidenceCount = data.items.length;
        }
      }
    }

    // 2. Math Daily Goal 검증
    if (datasets.mathDailyGoal) {
      if (datasets.mathDailyGoal.present) {
        const data = datasets.mathDailyGoal.data;
        if (!data || typeof data !== 'object' || typeof data.date !== 'string') {
          errors.push('수학 일일 목표 데이터(mathDailyGoal)의 구조가 올바르지 않습니다.');
        } else {
          summary.hasDailyGoal = true;
          summary.dailyGoalDate = data.date;
        }
      }
    }

    // 2.5 Math Goal Preference 검증
    if (datasets.mathGoalPreference) {
      if (datasets.mathGoalPreference.present) {
        const data = datasets.mathGoalPreference.data;
        if (!data || typeof data !== 'object' || typeof data.presetId !== 'string') {
          errors.push('수학 목표 설정 데이터(mathGoalPreference)의 구조가 올바르지 않습니다.');
        } else {
          summary.mathGoalPresetId = data.presetId;
        }
      }
    }

    // 2.6 Math Streak 검증
    if (datasets.mathStreak) {
      if (datasets.mathStreak.present) {
        const data = datasets.mathStreak.data;
        if (!data || typeof data !== 'object' || typeof data.currentStreak !== 'number') {
          errors.push('수학 연속 학습 데이터(mathStreak)의 구조가 올바르지 않습니다.');
        } else {
          summary.hasMathStreak = true;
          summary.mathCurrentStreak = data.currentStreak;
        }
      }
    }

    // 3. Study Rewards 검증
    if (datasets.studyRewards) {
      if (datasets.studyRewards.present) {
        const data = datasets.studyRewards.data;
        if (!data || typeof data !== 'object') {
          errors.push('보상 상점 데이터(studyRewards)의 구조가 올바르지 않습니다.');
        } else {
          summary.gems = Number.isFinite(Number(data.gems)) ? Number(data.gems) : 0;
          summary.youtubeMinutes = Number.isFinite(Number(data.youtube_minutes)) ? Number(data.youtube_minutes) : 0;
          if (Array.isArray(data.shop_items)) {
            summary.rewardItemsCount = data.shop_items.length;
          }
        }
      }
    }

    // 4. Math Receipts 검증
    if (datasets.mathReceipts) {
      if (datasets.mathReceipts.present) {
        const data = datasets.mathReceipts.data;
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
          errors.push('영수증 데이터(mathReceipts)의 구조가 올바르지 않습니다.');
        } else {
          summary.receiptsCount = Object.keys(data).length;
        }
      }
    }

    // 5. Guardian Weekly Words 검증
    if (datasets.guardianWeeklyWords) {
      if (datasets.guardianWeeklyWords.present) {
        const data = datasets.guardianWeeklyWords.data;
        if (!Array.isArray(data)) {
          errors.push('영어 주간 단어 데이터(guardianWeeklyWords)가 배열 형식이 아닙니다.');
        } else {
          summary.weeklyWordsCount = data.length;
        }
      }
    }

    // 6. Guardian Subject Stats 검증
    if (datasets.guardianSubjectStats) {
      if (datasets.guardianSubjectStats.present) {
        const data = datasets.guardianSubjectStats.data;
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
          errors.push('과목별 통계 데이터(guardianSubjectStats)의 구조가 올바르지 않습니다.');
        } else {
          summary.hasSubjectStats = true;
        }
      }
    }

    // 7. Guardian Session Log 검증
    if (datasets.guardianSessionLog) {
      if (datasets.guardianSessionLog.present) {
        const data = datasets.guardianSessionLog.data;
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
          errors.push('세션 로그 데이터(guardianSessionLog)의 구조가 올바르지 않습니다.');
        } else {
          summary.hasSessionLog = true;
        }
      }
    }

    return {
      valid: errors.length === 0,
      errors: errors,
      summary: summary,
    };
  }

  /**
   * 3. 백업 데이터 복원 실행 (Point-in-time Snapshot Replacement)
   * @param {*} payload
   * @param {Object} [options]
   * @returns {{ success: boolean, reason?: string, restoredKeys?: string[], errors?: string[] }}
   */
  function restoreBackup(payload, options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);

    if (!storage || typeof storage.setItem !== 'function' || typeof storage.getItem !== 'function') {
      return { success: false, reason: 'storage_unavailable', errors: ['로컬 스토리지를 사용할 수 없습니다.'] };
    }

    // 1단계: 사전 검증
    const validation = validateBackup(payload);
    if (!validation.valid) {
      return { success: false, reason: 'validation_failed', errors: validation.errors };
    }

    const datasets = payload.datasets;
    const restoredKeys = [];

    // 2단계: 롤백용 기존 상태 스냅샷 저장
    const rollbackMap = new Map();
    const existingReceiptKeys = _findReceiptKeys(storage);

    const keysToTrack = [
      STORAGE_KEYS.MATH_EVIDENCE,
      STORAGE_KEYS.MATH_DAILY_GOAL,
      STORAGE_KEYS.MATH_GOAL_PREFERENCE,
      STORAGE_KEYS.MATH_STREAK,
      STORAGE_KEYS.STUDY_REWARDS,
      STORAGE_KEYS.WEEKLY_WORDS,
      STORAGE_KEYS.SESSION_LOG,
      ...SUBJECT_STAT_KEYS,
      ...existingReceiptKeys,
    ];

    for (const k of keysToTrack) {
      rollbackMap.set(k, storage.getItem(k));
    }

    function _performRollback() {
      try {
        for (const [k, val] of rollbackMap.entries()) {
          if (val === null) {
            storage.removeItem(k);
          } else {
            storage.setItem(k, val);
          }
        }
      } catch (rollbackErr) {
        console.error('[LocalBackupCore] Rollback failed:', rollbackErr);
      }
    }

    // 3단계: 결정론적 쓰기 (Deterministic Restore Writes)
    try {
      // 1. Math Evidence
      if (datasets.mathEvidence) {
        const k = STORAGE_KEYS.MATH_EVIDENCE;
        if (datasets.mathEvidence.present && datasets.mathEvidence.data) {
          storage.setItem(k, JSON.stringify(datasets.mathEvidence.data));
          restoredKeys.push(k);
        } else {
          storage.removeItem(k);
        }
      }

      // 2. Math Daily Goal
      if (datasets.mathDailyGoal) {
        const k = STORAGE_KEYS.MATH_DAILY_GOAL;
        if (datasets.mathDailyGoal.present && datasets.mathDailyGoal.data) {
          storage.setItem(k, JSON.stringify(datasets.mathDailyGoal.data));
          restoredKeys.push(k);
        } else {
          storage.removeItem(k);
        }
      }

      // 2.5 Math Goal Preference
      if (datasets.mathGoalPreference !== undefined) {
        const k = STORAGE_KEYS.MATH_GOAL_PREFERENCE;
        if (datasets.mathGoalPreference && datasets.mathGoalPreference.present && datasets.mathGoalPreference.data) {
          storage.setItem(k, JSON.stringify(datasets.mathGoalPreference.data));
          restoredKeys.push(k);
        } else if (datasets.mathGoalPreference && datasets.mathGoalPreference.present === false) {
          storage.removeItem(k);
        }
      }

      // 2.6 Math Streak
      if (datasets.mathStreak !== undefined) {
        const k = STORAGE_KEYS.MATH_STREAK;
        if (datasets.mathStreak && datasets.mathStreak.present && datasets.mathStreak.data) {
          storage.setItem(k, JSON.stringify(datasets.mathStreak.data));
          restoredKeys.push(k);
        } else if (datasets.mathStreak && datasets.mathStreak.present === false) {
          storage.removeItem(k);
        }
      }

      // 3. Study Rewards
      if (datasets.studyRewards) {
        const k = STORAGE_KEYS.STUDY_REWARDS;
        if (datasets.studyRewards.present && datasets.studyRewards.data) {
          storage.setItem(k, JSON.stringify(datasets.studyRewards.data));
          restoredKeys.push(k);
        } else {
          storage.removeItem(k);
        }
      }

      // 4. Math Receipts (기존 receipt 키 정리 후 백업 데이터의 receipt 키 주입)
      for (const rk of existingReceiptKeys) {
        storage.removeItem(rk);
      }
      if (datasets.mathReceipts && datasets.mathReceipts.present && datasets.mathReceipts.data) {
        for (const [rk, rData] of Object.entries(datasets.mathReceipts.data)) {
          if (rk.startsWith(STORAGE_KEYS.RECEIPT_PREFIX) && rData) {
            storage.setItem(rk, JSON.stringify(rData));
            restoredKeys.push(rk);
          }
        }
      }

      // 5. Guardian Weekly Words
      if (datasets.guardianWeeklyWords) {
        const k = STORAGE_KEYS.WEEKLY_WORDS;
        if (datasets.guardianWeeklyWords.present && datasets.guardianWeeklyWords.data) {
          storage.setItem(k, JSON.stringify(datasets.guardianWeeklyWords.data));
          restoredKeys.push(k);
        } else {
          storage.removeItem(k);
        }
      }

      // 6. Guardian Subject Stats
      if (datasets.guardianSubjectStats) {
        for (const sk of SUBJECT_STAT_KEYS) {
          if (datasets.guardianSubjectStats.present && datasets.guardianSubjectStats.data && datasets.guardianSubjectStats.data[sk]) {
            storage.setItem(sk, JSON.stringify(datasets.guardianSubjectStats.data[sk]));
            restoredKeys.push(sk);
          } else {
            storage.removeItem(sk);
          }
        }
      }

      // 7. Guardian Session Log
      if (datasets.guardianSessionLog) {
        const k = STORAGE_KEYS.SESSION_LOG;
        if (datasets.guardianSessionLog.present && datasets.guardianSessionLog.data) {
          storage.setItem(k, JSON.stringify(datasets.guardianSessionLog.data));
          restoredKeys.push(k);
        } else {
          storage.removeItem(k);
        }
      }

      // 4단계: Stale Sync Queue 엔트리 정리 (cloud push 방지 및 stale 오염 방지)
      const rawQueue = storage.getItem(STORAGE_KEYS.SYNC_QUEUE);
      if (rawQueue) {
        const q = _safeJsonParse(rawQueue);
        if (q && typeof q === 'object') {
          let queueModified = false;
          for (const restoredKey of restoredKeys) {
            if (q[restoredKey] !== undefined) {
              delete q[restoredKey];
              queueModified = true;
            }
          }
          if (queueModified) {
            storage.setItem(STORAGE_KEYS.SYNC_QUEUE, JSON.stringify(q));
          }
        }
      }

      return {
        success: true,
        restoredAt: new Date().toISOString(),
        restoredKeys: restoredKeys,
      };
    } catch (writeErr) {
      console.error('[LocalBackupCore] Write exception during restore, rolling back:', writeErr);
      _performRollback();
      return {
        success: false,
        reason: 'write_failed',
        errors: [`데이터 복원 중 오류가 발생하여 기존 상태로 되돌렸습니다: ${writeErr.message}`],
      };
    }
  }

  return Object.freeze({
    FORMAT_MARKER: FORMAT_MARKER,
    SCHEMA_VERSION: SCHEMA_VERSION,
    APP_IDENTIFIER: APP_IDENTIFIER,
    STORAGE_KEYS: STORAGE_KEYS,
    createBackupSnapshot: createBackupSnapshot,
    validateBackup: validateBackup,
    restoreBackup: restoreBackup,
  });
});
