/**
 * @fileoverview 수학 학습 증거 저장소 (Durable Raw Learning Evidence)
 * @module math/evidence
 *
 * 문제 풀이 시점의 원시 학습 증거를 버전 관리 스키마로 로컬 저장소에 안전하게 보존.
 * fail-soft 복구 및 롤링 윈도우(최대 500건) 기반 바운디드 스토리지 보장.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MathEvidenceStore = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const STORAGE_KEY = 'aiden_math_learning_evidence_v1';
  const SCHEMA_VERSION = 1;
  const DEFAULT_MAX_ITEMS = 500;

  function _getStorage(customStorage) {
    if (customStorage) return customStorage;
    if (typeof localStorage !== 'undefined') return localStorage;
    return null;
  }

  function createDefaultEvidenceState() {
    return {
      schemaVersion: SCHEMA_VERSION,
      lastUpdated: new Date().toISOString(),
      items: [],
    };
  }

  function _isValidState(data) {
    return (
      data !== null &&
      typeof data === 'object' &&
      data.schemaVersion === SCHEMA_VERSION &&
      Array.isArray(data.items)
    );
  }

  function _normalizeItem(raw, now) {
    if (!raw || typeof raw !== 'object') return null;

    const timestamp = typeof raw.timestamp === 'number' && Number.isFinite(raw.timestamp) ? raw.timestamp : (now || Date.now());
    const id = typeof raw.id === 'string' && raw.id.length > 0 ? raw.id : `ev-${timestamp}-${Math.random().toString(36).slice(2, 8)}`;
    const skillId = typeof raw.skillId === 'string' && raw.skillId.length > 0 ? raw.skillId : 'math.add.within_10';
    const problemKey = typeof raw.problemKey === 'string' ? raw.problemKey : `${raw.a || 0}${raw.op || '+'}${raw.b || 0}`;
    const operation = typeof raw.op === 'string' ? raw.op : (typeof raw.operation === 'string' ? raw.operation : '+');
    const a = typeof raw.a === 'number' ? raw.a : 0;
    const b = typeof raw.b === 'number' ? raw.b : 0;
    const result = typeof raw.result === 'number' ? raw.result : 0;
    const correct = Boolean(raw.correct);
    const firstAttempt = raw.firstAttempt !== undefined ? Boolean(raw.firstAttempt) : true;
    const attempts = typeof raw.attempts === 'number' && raw.attempts >= 1 ? raw.attempts : 1;
    const elapsedSeconds = typeof raw.elapsedSeconds === 'number' && Number.isFinite(raw.elapsedSeconds) ? raw.elapsedSeconds : 0;
    const isWeakness = Boolean(raw.isWeakness);
    const isReinforcement = Boolean(raw.isReinforcement);

    return {
      id: id,
      timestamp: timestamp,
      skillId: skillId,
      problemKey: problemKey,
      operation: operation,
      a: a,
      b: b,
      result: result,
      correct: correct,
      firstAttempt: firstAttempt,
      attempts: attempts,
      elapsedSeconds: elapsedSeconds,
      isWeakness: isWeakness,
      isReinforcement: isReinforcement,
    };
  }

  /**
   * 저장소에서 전체 증거 상태 로드 (손상 시 기본값으로 안전 복구)
   */
  function loadEvidence(options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const key = opts.key || STORAGE_KEY;

    if (!storage || typeof storage.getItem !== 'function') {
      return createDefaultEvidenceState();
    }

    try {
      const raw = storage.getItem(key);
      if (!raw) return createDefaultEvidenceState();

      const parsed = JSON.parse(raw);
      if (!_isValidState(parsed)) {
        return createDefaultEvidenceState();
      }

      const validItems = [];
      for (const item of parsed.items) {
        const normalized = _normalizeItem(item, 0);
        if (normalized) validItems.push(normalized);
      }

      return {
        schemaVersion: SCHEMA_VERSION,
        lastUpdated: parsed.lastUpdated || new Date().toISOString(),
        items: validItems,
      };
    } catch (err) {
      console.warn('[MathEvidenceStore] Failed to parse evidence storage, returning default state:', err);
      return createDefaultEvidenceState();
    }
  }

  /**
   * 저장소에 전체 증거 상태 저장
   */
  function saveEvidence(state, options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const key = opts.key || STORAGE_KEY;

    if (!storage || typeof storage.setItem !== 'function') {
      return false;
    }

    try {
      const payload = {
        schemaVersion: SCHEMA_VERSION,
        lastUpdated: new Date().toISOString(),
        items: Array.isArray(state.items) ? state.items : [],
      };
      storage.setItem(key, JSON.stringify(payload));
      return true;
    } catch (err) {
      console.error('[MathEvidenceStore] Failed to save evidence:', err);
      return false;
    }
  }

  /**
   * 단일 증거 항목 추가 (바운디드 스토리지 유지)
   */
  function appendEvidence(rawItem, options) {
    const opts = options || {};
    const now = typeof opts.now === 'number' ? opts.now : Date.now();
    const maxItems = typeof opts.maxItems === 'number' ? opts.maxItems : DEFAULT_MAX_ITEMS;

    const normalized = _normalizeItem(rawItem, now);
    if (!normalized) return null;

    const state = loadEvidence(opts);
    state.items.push(normalized);

    // 바운디드 윈도우 유지: 최대 개수 초과 시 가장 오래된 항목 제거
    if (state.items.length > maxItems) {
      state.items = state.items.slice(state.items.length - maxItems);
    }

    saveEvidence(state, opts);
    return normalized;
  }

  /**
   * 특정 스킬의 증거 목록 또는 전체 목록 조회
   */
  function getEvidenceList(options) {
    const opts = options || {};
    const state = loadEvidence(opts);
    if (opts.skillId) {
      return state.items.filter(item => item.skillId === opts.skillId);
    }
    return [...state.items];
  }

  /**
   * 증거 초기화
   */
  function clearEvidence(options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const key = opts.key || STORAGE_KEY;

    if (storage && typeof storage.removeItem === 'function') {
      try {
        storage.removeItem(key);
      } catch (e) {}
    }
  }

  return Object.freeze({
    STORAGE_KEY: STORAGE_KEY,
    SCHEMA_VERSION: SCHEMA_VERSION,
    DEFAULT_MAX_ITEMS: DEFAULT_MAX_ITEMS,
    createDefaultEvidenceState: createDefaultEvidenceState,
    loadEvidence: loadEvidence,
    saveEvidence: saveEvidence,
    appendEvidence: appendEvidence,
    getEvidenceList: getEvidenceList,
    clearEvidence: clearEvidence,
  });
});
