/**
 * @fileoverview AidenGame 주간 영단어 단일 진실 소스 (Canonical Weekly Vocabulary Store)
 * @module domains/english/weekly-vocabulary-store
 *
 * 주간 단어 시험과 일반 영어 퀴즈, 보호자 화면이 공유하는 단일 canonical weekly vocabulary authority.
 * 동일 철자(spelling)의 서로 다른 뜻/description(multi-sense)을 itemId로 고유 식별하며,
 * 학원 시험 원문(academyDescription)을 보존한다.
 */

(function (root, factory) {
  'use strict';
  var store = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = store;
  }
  if (root) {
    root.WeeklyVocabularyStore = store;
  }
  if (typeof globalThis !== 'undefined') {
    globalThis.WeeklyVocabularyStore = store;
  }
})(typeof window !== 'undefined' ? window : (typeof self !== 'undefined' ? self : this), function () {
  'use strict';

  var CANONICAL_STORAGE_KEY = 'aiden_canonical_weekly_vocabulary_v1';
  var LEGACY_STORAGE_KEY = 'englishWeeklyWords';
  var SCHEMA_VERSION = 1;
  var DEFAULT_SET_ID = '2026-09-18';

  // 2026-09-18 학원 시험지 (Vocabulary B Unit 2) 기준 원본 데이터
  var SEED_ITEMS = [
    {
      word: 'across',
      academyDescription: 'from one side to the other side',
      ko: '가로질러',
      icon: '↔️'
    },
    {
      word: 'surround',
      academyDescription: 'to be on all sides',
      ko: '둘러싸다',
      icon: '🔄'
    },
    {
      word: 'relaxing',
      academyDescription: 'helping you to rest',
      ko: '편안한',
      icon: '🛋️'
    },
    {
      word: 'peaceful',
      academyDescription: 'calm and not violent',
      ko: '평화로운',
      icon: '🕊️'
    },
    {
      word: 'mystery',
      academyDescription: 'a puzzle or secret',
      ko: '수수께끼',
      icon: '🧩'
    },
    {
      word: 'clear',
      academyDescription: 'see-through',
      ko: '투명한',
      icon: '🪟'
    },
    {
      word: 'bottom',
      academyDescription: 'the lowest part of something',
      ko: '바닥',
      icon: '⬇️'
    },
    {
      word: 'explore',
      academyDescription: 'to look around and discover',
      ko: '탐험하다',
      icon: '🧭'
    },
    {
      word: 'calm',
      academyDescription: 'not moving much',
      ko: '고요한',
      icon: '🧘'
    },
    {
      word: 'imagine',
      academyDescription: 'to picture in your mind',
      ko: '상상하다',
      icon: '💭'
    }
  ];

  function _getStorage(customStorage) {
    if (customStorage) return customStorage;
    if (typeof window !== 'undefined' && window.localStorage) return window.localStorage;
    if (typeof globalThis !== 'undefined' && globalThis.localStorage) return globalThis.localStorage;
    if (typeof localStorage !== 'undefined') return localStorage;
    return null;
  }

  function _hashString(str) {
    var hash = 5381;
    var s = String(str || '');
    for (var i = 0; i < s.length; i++) {
      hash = ((hash << 5) + hash) + s.charCodeAt(i);
      hash = hash & hash;
    }
    return (hash >>> 0).toString(16);
  }

  function createItemId(setId, word, description) {
    var sId = String(setId || DEFAULT_SET_ID).trim().toLowerCase();
    var w = String(word || '').trim().toLowerCase();
    var dHash = _hashString(String(description || '').trim());
    return sId + '-' + w + '-' + dHash;
  }

  function createItem(setId, rawItem) {
    var word = String(rawItem.word || rawItem.answer || rawItem.en || '').trim();
    var desc = String(rawItem.academyDescription !== undefined ? rawItem.academyDescription : (rawItem.prompt !== undefined ? rawItem.prompt : (rawItem.description || '')));
    var sId = String(setId || DEFAULT_SET_ID).trim();
    var id = rawItem.itemId || rawItem.id || createItemId(sId, word, desc);
    return {
      itemId: id,
      id: id,
      word: word,
      answer: word,
      academyDescription: desc,
      prompt: desc,
      ko: rawItem.ko || '',
      icon: rawItem.icon || '',
      acceptedAnswers: Array.isArray(rawItem.acceptedAnswers) ? rawItem.acceptedAnswers.slice() : []
    };
  }

  function buildDefaultSet(setId) {
    var sId = setId || DEFAULT_SET_ID;
    var items = SEED_ITEMS.map(function (seed) {
      return createItem(sId, seed);
    });
    var defaultUpdatedIso = '2026-09-18T00:00:00.000Z';
    var defaultUpdatedMs = new Date(defaultUpdatedIso).getTime();
    return {
      schemaVersion: SCHEMA_VERSION,
      setId: sId,
      testDate: sId,
      title: sId + ' 주간 영단어',
      items: items,
      _updated_at: defaultUpdatedMs,
      registeredAt: defaultUpdatedIso,
      updatedAt: defaultUpdatedIso
    };
  }

  function validateSet(set) {
    if (!set || typeof set !== 'object') return false;
    if (set.schemaVersion !== SCHEMA_VERSION && set.schemaVersion !== 1 && set.schemaVersion !== undefined) return false;
    if (typeof set.setId !== 'string' || !set.setId.trim()) return false;
    if (!Array.isArray(set.items) || set.items.length === 0) return false;
    for (var i = 0; i < set.items.length; i++) {
      var item = set.items[i];
      if (!item || typeof item !== 'object') return false;
      var id = item.itemId || item.id;
      if (id !== undefined && (typeof id !== 'string' || !id)) return false;
      var word = item.word || item.answer;
      if (typeof word !== 'string' || !word.trim()) return false;
      var desc = item.academyDescription !== undefined ? item.academyDescription : item.prompt;
      if (typeof desc !== 'string') return false;
    }
    return true;
  }

  function toLegacyProjection(canonicalSet) {
    if (!canonicalSet || !Array.isArray(canonicalSet.items)) return [];
    return canonicalSet.items.map(function (it) {
      return {
        en: it.word || it.answer,
        ko: it.ko || '',
        icon: it.icon || ''
      };
    });
  }

  function bootstrap(customStorage) {
    var storage = _getStorage(customStorage);
    if (!storage) return buildDefaultSet(DEFAULT_SET_ID);

    try {
      var rawCanonical = storage.getItem(CANONICAL_STORAGE_KEY);
      if (rawCanonical) {
        var parsed = JSON.parse(rawCanonical);
        if (validateSet(parsed)) {
          // 이미 정상 canonical schema가 존재함 - legacy로 덮어쓰지 않고 legacy 키만 동기화
          try {
            var legacyProj = toLegacyProjection(parsed);
            storage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(legacyProj));
          } catch (e) {}
          return parsed;
        }
      }
    } catch (e) {
      // malformed canonical storage fail-soft
    }

    // 신규 bootstrap: shipped 2026-09-18 기본 세트 생성
    var newSet = buildDefaultSet(DEFAULT_SET_ID);

    // legacy storage가 존재할 경우 fail-soft하게 조사 (추가 메타데이터가 있으면 보존)
    try {
      var rawLegacy = storage.getItem(LEGACY_STORAGE_KEY);
      if (rawLegacy) {
        var legacyParsed = JSON.parse(rawLegacy);
        if (Array.isArray(legacyParsed)) {
          // 2026-09-18 seed 항목 중 ko/icon 등이 있으면 매핑
          newSet.items.forEach(function (item) {
            var found = legacyParsed.find(function (leg) {
              return leg && (leg.en === item.word);
            });
            if (found) {
              if (found.ko && !item.ko) item.ko = found.ko;
              if (found.icon && !item.icon) item.icon = found.icon;
            }
          });
        }
      }
    } catch (e) {
      // malformed legacy data fail-soft
    }

    try {
      storage.setItem(CANONICAL_STORAGE_KEY, JSON.stringify(newSet));
      storage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(toLegacyProjection(newSet)));
    } catch (e) {}

    return newSet;
  }

  function getCurrentSet(customStorage) {
    var storage = _getStorage(customStorage);
    if (!storage) return buildDefaultSet(DEFAULT_SET_ID);

    try {
      var raw = storage.getItem(CANONICAL_STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (validateSet(parsed)) return parsed;
      }
    } catch (e) {}

    return bootstrap(customStorage);
  }

  function saveCurrentSet(rawSet, customStorage) {
    if (!rawSet || typeof rawSet !== 'object') {
      throw new Error('Invalid CurrentWeeklyVocabularySet schema');
    }
    var now = new Date();
    var nowIso = now.toISOString();
    var nowMs = now.getTime();
    var updatedMs = typeof rawSet._updated_at === 'number' && !isNaN(rawSet._updated_at)
      ? rawSet._updated_at
      : (rawSet.updatedAt ? new Date(rawSet.updatedAt).getTime() : nowMs);
    var updatedIso = rawSet.updatedAt || new Date(updatedMs).toISOString();

    var set = {
      schemaVersion: rawSet.schemaVersion || SCHEMA_VERSION,
      setId: String(rawSet.setId || rawSet.testDate || DEFAULT_SET_ID).trim(),
      testDate: String(rawSet.testDate || rawSet.setId || DEFAULT_SET_ID).trim(),
      title: rawSet.title || (String(rawSet.setId || rawSet.testDate || DEFAULT_SET_ID).trim() + ' 주간 영단어'),
      revision: typeof rawSet.revision === 'number' ? rawSet.revision : 1,
      contentFingerprint: rawSet.contentFingerprint || '',
      items: Array.isArray(rawSet.items) ? rawSet.items.slice() : [],
      _updated_at: updatedMs,
      registeredAt: rawSet.registeredAt || updatedIso,
      updatedAt: updatedIso
    };
    if (!validateSet(set)) {
      throw new Error('Invalid CurrentWeeklyVocabularySet schema');
    }
    var storage = _getStorage(customStorage);
    if (!storage) return false;

    set.items = set.items.map(function (it) {
      return createItem(set.setId, it);
    });

    try {
      storage.setItem(CANONICAL_STORAGE_KEY, JSON.stringify(set));
      // legacy compatibility projection 동기화
      var legacyProj = toLegacyProjection(set);
      storage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(legacyProj));
      if (typeof window !== 'undefined' && window.SyncEngine && typeof window.SyncEngine.pushStats === 'function') {
        try {
          // Push both canonical store and legacy projection to cloud
          window.SyncEngine.pushStats(CANONICAL_STORAGE_KEY, set);
          window.SyncEngine.pushStats(LEGACY_STORAGE_KEY, legacyProj);
        } catch (syncErr) {}
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  return Object.freeze({
    SCHEMA_VERSION: SCHEMA_VERSION,
    CANONICAL_STORAGE_KEY: CANONICAL_STORAGE_KEY,
    LEGACY_STORAGE_KEY: LEGACY_STORAGE_KEY,
    DEFAULT_SET_ID: DEFAULT_SET_ID,
    createItemId: createItemId,
    createItem: createItem,
    buildDefaultSet: buildDefaultSet,
    validateSet: validateSet,
    toLegacyProjection: toLegacyProjection,
    bootstrap: bootstrap,
    getCurrentSet: getCurrentSet,
    saveCurrentSet: saveCurrentSet
  });
});
