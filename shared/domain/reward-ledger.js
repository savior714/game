/**
 * @fileoverview 보상 감사 원장(Reward Audit Ledger) — 획득/사용/교환/조정/초기화를 기록·검증하는 순수 도메인 모듈
 * @module reward-ledger
 *
 * 설계 불변식:
 * 1. 기준점 초기화(Epoch Cutover & Monotonic Reset):
 *    - `BASELINE_RESET_EPOCH = 1` 미만의 모든 이전 보상 데이터(미검증 스냅샷 및 구 epoch 원장)는
 *      최초 정규화·병합 시 즉시 잔액 `0`, 빈 이벤트, 빈 영수증으로 초기화되며,
 *      기존 잔액 스냅샷은 `reset_history` 감사 증적으로만 보존된다.
 *    - 보호자가 전체 초기화를 실행하면 `reset_epoch`가 `epoch + 1`로 증가하며,
 *      모든 병합(`mergeLedgers`, `mergeStates`)에서 항상 더 높은 `reset_epoch`가 절대 우위를 가진다.
 * 2. 순수 델타 원장 & 무결성 검증:
 *    - 현재 epoch의 모든 잔액은 `base + Σ(events.delta)`로 결정된다.
 *    - 각 이벤트는 `id`, `at`(발생 시각 ms), `type`(`grant`|`consume`|`exchange`|`adjust`),
 *      `key`, `delta`, `reason`, `detail`, `source`, `actor`, `surface`, `client`, `receipt`, `group`을 보존한다.
 * 3. 교환법칙·결합법칙·멱등성 & 빈 브라우저 항등원:
 *    - 동일 epoch 내 병합은 이벤트 `id` 합집합이므로 획득(+)과 사용(-) 모두 유실되거나 되살아나지 않는다.
 *    - 빈 상태 `{}`는 현재 기준 epoch의 항등원으로 동작하므로 새 브라우저 로그인 시 초기화 이후 획득한
 *      클라우드 보상을 0으로 덮어쓰지 않는다.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    const exported = factory();
    root.RewardLedger = exported;
    if (typeof window !== 'undefined' && window) window.RewardLedger = exported;
    if (typeof globalThis !== 'undefined' && globalThis) globalThis.RewardLedger = exported;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const VERSION = 1;
  const BASELINE_RESET_EPOCH = 1;
  const FIELD_KEYS = Object.freeze([
    'gems',
    'youtube_minutes',
    'snacks',
    'marble_plays',
    'bubble_plays',
  ]);
  const CUSTOM_INVENTORY_KEY = 'custom_inventory';
  const CUSTOM_PREFIX = 'custom:';
  const YOUTUBE_UNIT = 10;
  const MAX_AMOUNT = 1000000;
  const MAX_EVENTS = 1000;
  const KEEP_EVENTS = 500;
  const MAX_RESET_HISTORY = 50;
  const MAX_ID_LENGTH = 128;
  const BLOCKED_KEYS = Object.freeze(['__proto__', 'constructor', 'prototype']);

  const KEY_LABELS = Object.freeze({
    gems: '💎 보석',
    youtube_minutes: '📺 유튜브 자유시간',
    snacks: '🍪 간식',
    marble_plays: '🔮 마블 플레이권',
    bubble_plays: '🫧 버블 플레이권',
  });

  const TYPE_LABELS = Object.freeze({
    grant: '획득',
    consume: '사용',
    exchange: '교환',
    adjust: '조정',
    reset: '초기화',
  });

  const SURFACE_LABELS = Object.freeze({
    hub: '홈 허브',
    math: '수학 놀이',
    english: '영어 놀이',
    'weekly-test': '주간 영단어 시험',
    korean: '국어 놀이',
    science: '과학 놀이',
    guardian: '보호자 관리',
    'ocean-rescue': '오션 레스큐',
    marble: '마블 게임',
    bubble: '버블 게임',
  });

  const SOURCE_LABELS = Object.freeze({
    math: '수학',
    english: '영어',
    'weekly-test': '주간 영단어',
    korean: '국어',
    science: '과학',
    hub: '홈 허브',
    shop: '보석 상점',
    youtube_modal: '유튜브 자유시간 모달',
    youtube_timer: '유튜브 브라우저 타이머',
    snack_modal: '간식 사용 모달',
    custom_modal: '커스텀 보상 모달',
    guardian: '보호자 관리',
    system: '시스템',
    quiz: '학습 퀴즈',
  });

  let eventSeq = 0;

  // ──────────────────────────────────────────
  // 1. 기본 검증/정규화 유틸
  // ──────────────────────────────────────────
  function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function isBlockedKey(key) {
    return BLOCKED_KEYS.includes(key);
  }

  function safeAssign(target, key, value) {
    if (typeof key !== 'string' || isBlockedKey(key)) return;
    target[key] = value;
  }

  function finiteNumber(value, fallback) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
  }

  function resolveTimestamp(opts, fallback) {
    if (isPlainObject(opts)) {
      if (opts.at !== undefined && Number.isFinite(Number(opts.at))) {
        return Math.max(0, Math.trunc(Number(opts.at)));
      }
      if (opts.now !== undefined && Number.isFinite(Number(opts.now))) {
        return Math.max(0, Math.trunc(Number(opts.now)));
      }
    }
    return Math.max(0, finiteNumber(fallback, 0));
  }

  function minPositive(a, b) {
    const na = Math.max(0, Math.trunc(finiteNumber(a, 0)));
    const nb = Math.max(0, Math.trunc(finiteNumber(b, 0)));
    if (na === 0) return nb;
    if (nb === 0) return na;
    return Math.min(na, nb);
  }

  function safeAmount(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return 0;
    return Math.max(-MAX_AMOUNT, Math.min(MAX_AMOUNT, Math.trunc(num)));
  }

  function safeLabel(value, maxLength) {
    if (typeof value !== 'string') return null;
    const trimmed = value.trim();
    if (trimmed.length === 0) return null;
    return trimmed.slice(0, maxLength);
  }

  function pickLabel(a, b, maxLength) {
    const sa = safeLabel(a, maxLength);
    const sb = safeLabel(b, maxLength);
    if (!sa) return sb;
    if (!sb) return sa;
    if (sa.length !== sb.length) return sa.length > sb.length ? sa : sb;
    return sa <= sb ? sa : sb;
  }

  function isSafeCustomId(id) {
    return (
      typeof id === 'string' &&
      id.length > 0 &&
      id.length <= 64 &&
      !isBlockedKey(id) &&
      !id.startsWith(CUSTOM_PREFIX)
    );
  }

  function normalizeKey(rawKey) {
    if (typeof rawKey !== 'string') return null;
    if (FIELD_KEYS.includes(rawKey)) return rawKey;
    if (rawKey.startsWith(CUSTOM_PREFIX)) {
      const id = rawKey.slice(CUSTOM_PREFIX.length);
      return isSafeCustomId(id) ? rawKey : null;
    }
    return null;
  }

  function customKey(id) {
    return CUSTOM_PREFIX + id;
  }

  function isCustomKey(key) {
    return typeof key === 'string' && key.startsWith(CUSTOM_PREFIX) && key.length > CUSTOM_PREFIX.length;
  }

  function customIdFromKey(key) {
    return isCustomKey(key) ? key.slice(CUSTOM_PREFIX.length) : '';
  }

  function detectSurface() {
    try {
      const loc = typeof location !== 'undefined' && location ? String(location.pathname || '') : '';
      if (!loc) return null;
      if (loc.includes('/domains/english/weekly-test')) return 'weekly-test';
      if (loc.includes('/domains/math')) return 'math';
      if (loc.includes('/domains/english')) return 'english';
      if (loc.includes('/domains/korean')) return 'korean';
      if (loc.includes('/domains/science')) return 'science';
      if (loc.includes('/domains/reward/guardian')) return 'guardian';
      if (loc.includes('/ocean-rescue')) return 'ocean-rescue';
      if (loc.includes('/experiments/marble')) return 'marble';
      if (loc.includes('/experiments/bubble')) return 'bubble';
      if (loc === '/' || loc.endsWith('/index.html')) return 'hub';
      return safeLabel(loc, 80);
    } catch (_e) {
      return null;
    }
  }

  function detectClient() {
    try {
      const ua = typeof navigator !== 'undefined' && navigator ? String(navigator.userAgent || '') : '';
      if (!ua) return null;
      if (/iPad/i.test(ua)) return 'iPad';
      if (/iPhone/i.test(ua)) return 'iPhone';
      if (/Android/i.test(ua)) {
        return /Mobile/i.test(ua) ? 'Android 모바일' : 'Android 태블릿';
      }
      if (/Macintosh|Mac OS X/i.test(ua)) return 'macOS 브라우저';
      if (/Windows/i.test(ua)) return 'Windows 브라우저';
      if (/Linux/i.test(ua)) return 'Linux 브라우저';
      return 'Web 브라우저';
    } catch (_e) {
      return null;
    }
  }

  function emptyBalances() {
    return {
      gems: 0,
      youtube_minutes: 0,
      snacks: 0,
      marble_plays: 0,
      bubble_plays: 0,
      custom_inventory: {},
    };
  }

  function isZeroBalances(balances) {
    if (!isPlainObject(balances)) return true;
    for (const key of FIELD_KEYS) {
      if (safeAmount(balances[key]) !== 0) return false;
    }
    const custom = isPlainObject(balances.custom_inventory) ? balances.custom_inventory : {};
    for (const id of Object.keys(custom)) {
      if (isSafeCustomId(id) && safeAmount(custom[id]) !== 0) return false;
    }
    return true;
  }

  function cloneBalances(source) {
    const out = emptyBalances();
    const src = isPlainObject(source) ? source : {};
    for (const key of FIELD_KEYS) out[key] = Math.max(0, safeAmount(src[key]));
    const custom = isPlainObject(src.custom_inventory) ? src.custom_inventory : {};
    for (const id of Object.keys(custom).sort()) {
      if (!isSafeCustomId(id)) continue;
      const val = safeAmount(custom[id]);
      if (val > 0) out.custom_inventory[id] = val;
    }
    return out;
  }

  function clampBalances(balances) {
    for (const key of FIELD_KEYS) {
      if (balances[key] < 0) balances[key] = 0;
    }
    for (const id of Object.keys(balances.custom_inventory)) {
      if (balances.custom_inventory[id] <= 0) delete balances.custom_inventory[id];
    }
    return balances;
  }

  function applyDeltaToBalances(balances, key, delta) {
    if (!key || delta === 0) return;
    if (key.startsWith(CUSTOM_PREFIX)) {
      const id = key.slice(CUSTOM_PREFIX.length);
      if (!isSafeCustomId(id)) return;
      balances.custom_inventory[id] = (balances.custom_inventory[id] || 0) + delta;
      return;
    }
    if (!FIELD_KEYS.includes(key)) return;
    balances[key] = (balances[key] || 0) + delta;
  }

  function readBalances(state) {
    const src = isPlainObject(state) ? state : {};
    const out = emptyBalances();
    for (const key of FIELD_KEYS) out[key] = Math.max(0, safeAmount(src[key]));
    const custom = isPlainObject(src.custom_inventory) ? src.custom_inventory : {};
    for (const id of Object.keys(custom).sort()) {
      if (!isSafeCustomId(id)) continue;
      const val = safeAmount(custom[id]);
      if (val > 0) out.custom_inventory[id] = val;
    }
    return out;
  }

  function balancesSignature(balances) {
    const parts = [];
    for (const key of FIELD_KEYS) {
      parts.push(`${key}=${Math.max(0, safeAmount(balances[key]))}`);
    }
    const custom = isPlainObject(balances.custom_inventory) ? balances.custom_inventory : {};
    for (const id of Object.keys(custom).sort()) {
      if (isSafeCustomId(id) && safeAmount(custom[id]) > 0) {
        parts.push(`custom:${id}=${safeAmount(custom[id])}`);
      }
    }
    return parts.join(';');
  }

  /** 잔액을 평면 스냅샷(`custom:아이디` 키 포함)으로 바꾼다. */
  function balancesToSnapshot(balances) {
    const out = {};
    for (const key of FIELD_KEYS) out[key] = safeAmount(balances[key]);
    for (const id of Object.keys(balances.custom_inventory || {})) {
      out[customKey(id)] = safeAmount(balances.custom_inventory[id]);
    }
    return out;
  }

  function snapshot(state) {
    return balancesToSnapshot(readBalances(state));
  }

  function diffSnapshots(before, after) {
    const a = isPlainObject(before) ? before : {};
    const b = isPlainObject(after) ? after : {};
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    const deltas = [];
    for (const key of keys) {
      const normalized = normalizeKey(key);
      if (!normalized) continue;
      const delta = safeAmount(b[key] || 0) - safeAmount(a[key] || 0);
      if (delta !== 0) deltas.push({ key: normalized, delta });
    }
    return deltas;
  }

  // ──────────────────────────────────────────
  // 2. 원장(ledger) 구조 및 Epoch 기준점
  // ──────────────────────────────────────────
  function compareEvents(a, b) {
    if (a.at !== b.at) return a.at - b.at;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  }

  function inferEventType(rawType, reason, delta) {
    if (rawType === 'grant' || rawType === 'consume' || rawType === 'exchange' || rawType === 'adjust') {
      return rawType;
    }
    if (typeof reason === 'string' && reason.startsWith('gem_exchange:')) {
      return 'exchange';
    }
    return delta > 0 ? 'grant' : 'consume';
  }

  function compactEvent(raw) {
    if (!isPlainObject(raw) || raw.reason === 'legacy_snapshot_downward') return null;
    const id = safeLabel(raw.id, MAX_ID_LENGTH);
    const key = normalizeKey(raw.key);
    const delta = safeAmount(raw.delta);
    if (!id || !key || delta === 0) return null;
    const reason = safeLabel(raw.reason, 80);
    const event = {
      id,
      at: Math.max(0, Math.trunc(finiteNumber(raw.at, 0))),
      key,
      delta,
      type: inferEventType(safeLabel(raw.type, 32), reason, delta),
    };
    if (reason) event.reason = reason;
    const receipt = safeLabel(raw.receipt, 128);
    if (receipt) event.receipt = receipt;
    const group = safeLabel(raw.group, MAX_ID_LENGTH);
    if (group) event.group = group;
    const source = safeLabel(raw.source, 64);
    if (source) event.source = source;
    const actor = safeLabel(raw.actor, 32);
    if (actor) event.actor = actor;
    const surface = safeLabel(raw.surface, 64);
    if (surface) event.surface = surface;
    const client = safeLabel(raw.client, 64);
    if (client) event.client = client;
    const detail = safeLabel(raw.detail, 240);
    if (detail) event.detail = detail;
    return event;
  }

  function mergeDuplicateEventMeta(a, b) {
    const out = {
      id: a.id,
      at: Math.min(a.at, b.at),
      key: a.key,
      delta: a.delta,
      type: a.type <= b.type ? a.type : b.type,
    };
    const optionalSpecs = [
      ['reason', 80],
      ['receipt', 128],
      ['group', MAX_ID_LENGTH],
      ['source', 64],
      ['actor', 32],
      ['surface', 64],
      ['client', 64],
      ['detail', 240],
    ];
    for (const [field, maxLen] of optionalSpecs) {
      const mergedVal = pickLabel(a[field], b[field], maxLen);
      if (mergedVal) out[field] = mergedVal;
    }
    return out;
  }

  function normalizeResetEntry(raw) {
    if (!isPlainObject(raw)) return null;
    const id = safeLabel(raw.id, 160);
    const epoch = Math.max(0, Math.trunc(finiteNumber(raw.epoch, 0)));
    if (!id || epoch < 1) return null;
    const entry = {
      id,
      epoch,
      at: Math.max(0, Math.trunc(finiteNumber(raw.at, 0))),
      reason: safeLabel(raw.reason, 80) || 'reset',
      actor: safeLabel(raw.actor, 32) || 'system',
      previous_balances: cloneBalances(raw.previous_balances),
    };
    const note = safeLabel(raw.note, 240);
    if (note) entry.note = note;
    const surface = safeLabel(raw.surface, 64);
    if (surface) entry.surface = surface;
    const client = safeLabel(raw.client, 64);
    if (client) entry.client = client;
    return entry;
  }

  function compareResetEntries(a, b) {
    if (a.epoch !== b.epoch) return a.epoch - b.epoch;
    if (a.at !== b.at) return a.at - b.at;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  }

  function mergeResetHistory(listA, listB) {
    const byId = new Map();
    for (const list of [listA, listB]) {
      if (!Array.isArray(list)) continue;
      for (const item of list) {
        const entry = normalizeResetEntry(item);
        if (!entry) continue;
        const existing = byId.get(entry.id);
        if (!existing) {
          byId.set(entry.id, entry);
        } else {
          existing.at = minPositive(existing.at, entry.at);
          existing.reason = pickLabel(existing.reason, entry.reason, 80) || 'reset';
          existing.actor = pickLabel(existing.actor, entry.actor, 32) || 'system';
          const note = pickLabel(existing.note, entry.note, 240);
          if (note) existing.note = note;
          const surface = pickLabel(existing.surface, entry.surface, 64);
          if (surface) existing.surface = surface;
          const client = pickLabel(existing.client, entry.client, 64);
          if (client) existing.client = client;
        }
      }
    }
    const sorted = Array.from(byId.values()).sort(compareResetEntries);
    return sorted.length > MAX_RESET_HISTORY ? sorted.slice(-MAX_RESET_HISTORY) : sorted;
  }

  function hasLedgerShape(raw) {
    return isPlainObject(raw) && Number(raw.v) === VERSION && Array.isArray(raw.events);
  }

  function getEpoch(ledgerOrState) {
    if (!isPlainObject(ledgerOrState)) return 0;
    const ledger = hasLedgerShape(ledgerOrState.reward_ledger)
      ? ledgerOrState.reward_ledger
      : (hasLedgerShape(ledgerOrState) ? ledgerOrState : null);
    if (!ledger) return 0;
    return Math.max(0, Math.trunc(finiteNumber(ledger.reset_epoch, 0)));
  }

  function createLedger(balances, at, options) {
    const opts = isPlainObject(options) ? options : {};
    const epoch = Math.max(BASELINE_RESET_EPOCH, Math.trunc(finiteNumber(opts.epoch, BASELINE_RESET_EPOCH)));
    const cloned = cloneBalances(balances);
    const baseAt = isZeroBalances(cloned) ? 0 : Math.max(0, Math.trunc(finiteNumber(at, 0)));
    return {
      v: VERSION,
      reset_epoch: epoch,
      reset_at: Math.max(0, Math.trunc(finiteNumber(opts.resetAt, 0))),
      reset_reason: safeLabel(opts.resetReason, 80) || 'initial_audit_cutover',
      reset_history: mergeResetHistory(opts.resetHistory, null),
      base: cloned,
      base_at: baseAt,
      folded_at: 0,
      folded_count: 0,
      events: [],
    };
  }

  function computeRawBalancesUnchecked(ledger) {
    if (!isPlainObject(ledger)) return emptyBalances();
    const balances = cloneBalances(ledger.base);
    if (Array.isArray(ledger.events)) {
      for (const item of ledger.events) {
        const ev = compactEvent(item);
        if (ev) applyDeltaToBalances(balances, ev.key, ev.delta);
      }
    }
    return clampBalances(balances);
  }

  function normalizeLedger(raw) {
    const src = isPlainObject(raw) ? raw : {};
    if (!hasLedgerShape(src) || getEpoch(src) < BASELINE_RESET_EPOCH) {
      return createLedger({}, 0, {
        epoch: BASELINE_RESET_EPOCH,
        resetReason: 'initial_audit_cutover',
        resetHistory: src.reset_history,
      });
    }
    const epoch = Math.max(BASELINE_RESET_EPOCH, getEpoch(src));
    const base = cloneBalances(src.base);
    const foldedAt = Math.max(0, Math.trunc(finiteNumber(src.folded_at, 0)));
    const foldedCount = Math.max(0, Math.trunc(finiteNumber(src.folded_count, 0)));
    const rawBaseAt = Math.max(0, Math.trunc(finiteNumber(src.base_at, 0)));
    const baseAt = foldedAt > 0
      ? Math.max(rawBaseAt, foldedAt)
      : (isZeroBalances(base) ? 0 : rawBaseAt);

    const byId = new Map();
    for (const item of src.events) {
      if (!isPlainObject(item)) continue;
      const event = compactEvent(item);
      if (!event) continue;
      if (foldedAt > 0 && event.at <= foldedAt) continue;
      const existing = byId.get(event.id);
      if (!existing) {
        byId.set(event.id, event);
      } else {
        byId.set(event.id, mergeDuplicateEventMeta(existing, event));
      }
    }
    const events = Array.from(byId.values()).sort(compareEvents);
    return {
      v: VERSION,
      reset_epoch: epoch,
      reset_at: Math.max(0, Math.trunc(finiteNumber(src.reset_at, 0))),
      reset_reason: safeLabel(src.reset_reason, 80) || 'initial_audit_cutover',
      reset_history: mergeResetHistory(src.reset_history, null),
      base,
      base_at: baseAt,
      folded_at: foldedAt,
      folded_count: foldedCount,
      events,
    };
  }

  function computeBalances(ledger) {
    const normalized = normalizeLedger(ledger);
    const balances = cloneBalances(normalized.base);
    for (const event of normalized.events) {
      applyDeltaToBalances(balances, event.key, event.delta);
    }
    return clampBalances(balances);
  }

  function makeEventId(at) {
    eventSeq = (eventSeq + 1) % 1e9;
    const random = Math.random().toString(36).slice(2, 8);
    return `ev-${at.toString(36)}-${eventSeq.toString(36)}-${random}`;
  }

  /** 이벤트가 MAX_EVENTS를 넘으면 오래된 이벤트를 base로 접고 folded_count를 누적한다. */
  function foldEvents(ledger) {
    const currentFoldedAt = Math.max(0, Math.trunc(finiteNumber(ledger.folded_at, 0)));
    const currentFoldedCount = Math.max(0, Math.trunc(finiteNumber(ledger.folded_count, 0)));
    if (ledger.events.length <= MAX_EVENTS) {
      return {
        v: VERSION,
        reset_epoch: ledger.reset_epoch,
        reset_at: ledger.reset_at || 0,
        reset_reason: ledger.reset_reason || 'initial_audit_cutover',
        reset_history: mergeResetHistory(ledger.reset_history, null),
        base: ledger.base,
        base_at: ledger.base_at,
        folded_at: currentFoldedAt,
        folded_count: currentFoldedCount,
        events: ledger.events,
      };
    }
    const sorted = ledger.events.slice().sort(compareEvents);
    let foldCount = sorted.length - KEEP_EVENTS;
    const cutoffAt = sorted[foldCount - 1].at;
    while (foldCount < sorted.length && sorted[foldCount].at <= cutoffAt) {
      foldCount += 1;
    }
    const folded = sorted.slice(0, foldCount);
    const base = cloneBalances(ledger.base);
    for (const event of folded) applyDeltaToBalances(base, event.key, event.delta);
    clampBalances(base);
    const nextFoldedAt = Math.max(currentFoldedAt, folded[folded.length - 1].at);
    return {
      v: VERSION,
      reset_epoch: ledger.reset_epoch,
      reset_at: ledger.reset_at || 0,
      reset_reason: ledger.reset_reason || 'initial_audit_cutover',
      reset_history: mergeResetHistory(ledger.reset_history, null),
      base,
      base_at: Math.max(ledger.base_at || 0, nextFoldedAt),
      folded_at: nextFoldedAt,
      folded_count: currentFoldedCount + folded.length,
      events: sorted.slice(foldCount),
    };
  }

  function appendEvents(ledger, specs, meta) {
    const base = normalizeLedger(ledger);
    const options = isPlainObject(meta) ? meta : {};
    const at = resolveTimestamp(options, Date.now());
    const specList = Array.isArray(specs) ? specs : [];
    const autoGroup = specList.length > 1 ? `tx-${makeEventId(at).slice(3)}` : null;
    const group = safeLabel(options.group, MAX_ID_LENGTH) || autoGroup;
    const defaultSource = safeLabel(options.source, 64);
    const defaultActor = safeLabel(options.actor, 32);
    const defaultSurface = safeLabel(options.surface, 64) || detectSurface();
    const defaultClient = safeLabel(options.client, 64) || detectClient();
    const defaultDetail = safeLabel(options.detail, 240);
    const events = base.events.slice();
    const eventIds = [];

    for (const spec of specList) {
      if (!isPlainObject(spec)) continue;
      const key = normalizeKey(spec.key);
      const delta = safeAmount(spec.delta);
      if (!key || delta === 0) continue;
      const reason = safeLabel(spec.reason || options.reason, 80);
      const event = {
        id: safeLabel(spec.id, MAX_ID_LENGTH) || makeEventId(at),
        at: spec.at !== undefined ? Math.max(0, Math.trunc(finiteNumber(spec.at, at))) : at,
        key,
        delta,
        type: inferEventType(safeLabel(spec.type || options.type, 32), reason, delta),
      };
      if (reason) event.reason = reason;
      const receipt = safeLabel(spec.receipt || options.receipt, 128);
      if (receipt) event.receipt = receipt;
      const evGroup = safeLabel(spec.group, MAX_ID_LENGTH) || group;
      if (evGroup) event.group = evGroup;
      const source = safeLabel(spec.source, 64) || defaultSource;
      if (source) event.source = source;
      const actor = safeLabel(spec.actor, 32) || defaultActor;
      if (actor) event.actor = actor;
      const surface = safeLabel(spec.surface, 64) || defaultSurface;
      if (surface) event.surface = surface;
      const client = safeLabel(spec.client, 64) || defaultClient;
      if (client) event.client = client;
      const detail = safeLabel(spec.detail, 240) || defaultDetail;
      if (detail) event.detail = detail;
      events.push(event);
      eventIds.push(event.id);
    }

    return {
      ledger: foldEvents({
        v: VERSION,
        reset_epoch: base.reset_epoch,
        reset_at: base.reset_at,
        reset_reason: base.reset_reason,
        reset_history: base.reset_history,
        base: base.base,
        base_at: base.base_at,
        folded_at: base.folded_at || 0,
        folded_count: base.folded_count || 0,
        events,
      }),
      eventIds,
    };
  }

  // ──────────────────────────────────────────
  // 3. 상태 정규화 / 구성 / 초기화
  // ──────────────────────────────────────────
  function composeState(source, ledger) {
    const src = isPlainObject(source) ? source : {};
    const balances = computeBalances(ledger);
    const out = {};
    for (const key of Object.keys(src)) {
      if (isBlockedKey(key)) continue;
      if (FIELD_KEYS.includes(key)) continue;
      if (key === CUSTOM_INVENTORY_KEY || key === 'reward_ledger') continue;
      safeAssign(out, key, src[key]);
    }
    for (const key of FIELD_KEYS) out[key] = balances[key];
    out.custom_inventory = { ...balances.custom_inventory };
    out.reward_ledger = ledger;
    return out;
  }

  /**
   * 저장/전달받은 임의의 보상 상태를 신뢰 가능한 형태로 정규화한다.
   * - `reset_epoch < BASELINE_RESET_EPOCH`인 모든 레거시/이전 데이터는 즉시 잔액 `0`(Epoch #1)으로 초기화하고
   *   이전 양수 잔액은 `reset_history` 감사 증적으로 남긴다.
   * - 현행 epoch 상태에서는 `adoptFields !== false`일 때 외부 하향 쓰기(감소분)만 조정 이벤트로 남기고,
   *   이벤트 없는 상향 스냅샷 값은 무시한다(무단 충전/부활 방지).
   */
  function normalizeState(raw, options) {
    const opts = isPlainObject(options) ? options : {};
    const src = isPlainObject(raw) ? raw : {};
    const observed = readBalances(src);
    const fallbackAt = resolveTimestamp(opts, finiteNumber(src._updated_at, 0));
    const currentEpoch = getEpoch(src);
    let ledger;
    let sourceForCompose = src;

    if (currentEpoch < BASELINE_RESET_EPOCH) {
      const priorLedgerBalances = hasLedgerShape(src.reward_ledger)
        ? computeRawBalancesUnchecked(src.reward_ledger)
        : emptyBalances();
      const priorCombined = emptyBalances();
      for (const key of FIELD_KEYS) {
        priorCombined[key] = Math.max(observed[key], priorLedgerBalances[key]);
      }
      const allCustomIds = new Set([
        ...Object.keys(observed.custom_inventory || {}),
        ...Object.keys(priorLedgerBalances.custom_inventory || {}),
      ]);
      for (const id of Array.from(allCustomIds).sort()) {
        if (!isSafeCustomId(id)) continue;
        const maxVal = Math.max(
          observed.custom_inventory[id] || 0,
          priorLedgerBalances.custom_inventory[id] || 0
        );
        if (maxVal > 0) priorCombined.custom_inventory[id] = maxVal;
      }

      let history = isPlainObject(src.reward_ledger)
        ? mergeResetHistory(src.reward_ledger.reset_history, null)
        : [];
      if (!isZeroBalances(priorCombined)) {
        const sig = balancesSignature(priorCombined);
        history = mergeResetHistory(history, [{
          id: `cutover-epoch-${BASELINE_RESET_EPOCH}:${sig}`,
          epoch: BASELINE_RESET_EPOCH,
          at: fallbackAt,
          reason: 'initial_audit_cutover',
          actor: 'system',
          note: '이전 누적 보상 전체 0 초기화 (감사 원장 기준점 적용)',
          previous_balances: priorCombined,
        }]);
      }
      ledger = createLedger({}, 0, {
        epoch: BASELINE_RESET_EPOCH,
        resetAt: fallbackAt,
        resetReason: 'initial_audit_cutover',
        resetHistory: history,
      });
      sourceForCompose = { ...src, claimed_receipts: {} };
    } else {
      const hadPoisonedLegacyDownward = Array.isArray(src.reward_ledger.events)
        && src.reward_ledger.events.some((item) => item && item.reason === 'legacy_snapshot_downward');
      ledger = normalizeLedger(src.reward_ledger);
      if (opts.adoptFields !== false && !hadPoisonedLegacyDownward) {
        const expected = balancesToSnapshot(computeBalances(ledger));
        const actual = balancesToSnapshot(observed);
        const deltas = diffSnapshots(expected, actual).filter((delta) => delta.delta < 0);
        if (deltas.length > 0) {
          ledger = appendEvents(ledger, deltas, {
            at: fallbackAt,
            type: 'adjust',
            reason: 'external_write',
            source: 'system',
            actor: 'system',
            detail: '외부 스냅샷 하향 차감 반영',
          }).ledger;
        }
      }
      sourceForCompose = {
        ...src,
        claimed_receipts: mergeReceipts(src.claimed_receipts, null),
      };
    }

    const stray = computeBalances(ledger).youtube_minutes;
    if (stray % YOUTUBE_UNIT !== 0) {
      const normalizedMinutes = Math.max(0, Math.floor(stray / YOUTUBE_UNIT) * YOUTUBE_UNIT);
      ledger = appendEvents(
        ledger,
        [{ key: 'youtube_minutes', delta: normalizedMinutes - stray }],
        {
          at: fallbackAt,
          type: 'adjust',
          reason: 'youtube_stray',
          source: 'system',
          actor: 'system',
          detail: `10분 미만 자투리 자유시간(${stray - normalizedMinutes}분) 자동 정리`,
        }
      ).ledger;
    }

    return composeState(sourceForCompose, ledger);
  }

  /**
   * 모든 획득 보상을 `0`으로 초기화하고 `reset_epoch`를 단조 증가(`epoch + 1`)시킨다.
   * 이전 잔액 스냅샷과 초기화 사유·메모·시각을 `reset_history`에 남긴다.
   */
  function resetState(state, options) {
    const opts = isPlainObject(options) ? options : {};
    const at = resolveTimestamp(opts, Date.now());
    const normalized = normalizeState(state, { adoptFields: false, at });
    const prevBalances = readBalances(normalized);
    const nextEpoch = opts.targetEpoch !== undefined
      ? Math.max(normalized.reward_ledger.reset_epoch, Math.trunc(finiteNumber(opts.targetEpoch, 0)))
      : normalized.reward_ledger.reset_epoch + 1;
    const reason = safeLabel(opts.reason, 80) || 'guardian_manual_reset';
    const actor = safeLabel(opts.actor, 32) || 'guardian';
    const surface = safeLabel(opts.surface, 64) || detectSurface();
    const client = safeLabel(opts.client, 64) || detectClient();
    const note = safeLabel(opts.note, 240) || '보호자 전체 보상 초기화';

    const checkpoint = {
      id: makeEventId(at).replace(/^ev-/, 'reset-'),
      epoch: nextEpoch,
      at,
      reason,
      actor,
      note,
      previous_balances: prevBalances,
    };
    if (surface) checkpoint.surface = surface;
    if (client) checkpoint.client = client;

    const nextHistory = mergeResetHistory(normalized.reward_ledger.reset_history, [checkpoint]);
    const nextLedger = createLedger({}, 0, {
      epoch: nextEpoch,
      resetAt: at,
      resetReason: reason,
      resetHistory: nextHistory,
    });
    const out = composeState(normalized, nextLedger);
    out.claimed_receipts = {};
    out._updated_at = at;
    return out;
  }

  /** 현재 상태의 잔액(평면 스냅샷)을 반환한다. */
  function balanceSnapshot(state) {
    if (hasLedgerShape(state && state.reward_ledger) && getEpoch(state) >= BASELINE_RESET_EPOCH) {
      return balancesToSnapshot(computeBalances(state.reward_ledger));
    }
    return snapshot(normalizeState(state, { adoptFields: false }));
  }

  /** 델타 목록을 원장에 추가하고 잔액을 다시 계산한 새 상태를 반환한다. */
  function applyDeltas(state, deltas, meta) {
    const normalized = normalizeState(state, { adoptFields: false, at: resolveTimestamp(meta, 0) });
    const applied = appendEvents(normalized.reward_ledger, deltas, meta);
    return {
      state: composeState(normalized, applied.ledger),
      eventIds: applied.eventIds,
    };
  }

  /** 절대 수량을 지정한다(보호자 삭제·정리 등). 실제 변화는 조정 이벤트로 기록된다. */
  function setQuantity(state, key, value, meta) {
    const normalized = normalizeState(state, { adoptFields: false, at: resolveTimestamp(meta, 0) });
    const target = Math.max(0, safeAmount(value));
    const snapshotNow = balancesToSnapshot(computeBalances(normalized.reward_ledger));
    const delta = target - safeAmount(snapshotNow[key] || 0);
    if (delta === 0) return { state: normalized, eventIds: [] };
    return applyDeltas(normalized, [{ key, delta }], meta);
  }

  // ──────────────────────────────────────────
  // 4. 병합(교환 가능 · 결합 가능 · 멱등 · Epoch 우위)
  // ──────────────────────────────────────────
  function stableJson(value) {
    try {
      const serialized = JSON.stringify(value);
      return serialized === undefined ? 'undefined' : serialized;
    } catch (_e) {
      return 'unserializable';
    }
  }

  function pickBase(ledgerA, ledgerB) {
    const foldedA = Math.max(0, finiteNumber(ledgerA.folded_at, 0));
    const foldedB = Math.max(0, finiteNumber(ledgerB.folded_at, 0));
    if (foldedA !== foldedB) {
      return foldedA > foldedB ? ledgerA.base : ledgerB.base;
    }
    if (foldedA === 0) {
      const zeroA = isZeroBalances(ledgerA.base);
      const zeroB = isZeroBalances(ledgerB.base);
      if (zeroA !== zeroB) {
        return zeroA ? ledgerB.base : ledgerA.base;
      }
    }
    if (ledgerA.base_at !== ledgerB.base_at) {
      return ledgerA.base_at > ledgerB.base_at ? ledgerA.base : ledgerB.base;
    }
    return stableJson(ledgerA.base) >= stableJson(ledgerB.base) ? ledgerA.base : ledgerB.base;
  }

  function mergeEvents(eventsA, eventsB, foldedAt) {
    const cutoff = Math.max(0, finiteNumber(foldedAt, 0));
    const byId = new Map();
    for (const event of [...eventsA, ...eventsB]) {
      if (cutoff > 0 && event.at <= cutoff) continue;
      const existing = byId.get(event.id);
      if (!existing) {
        byId.set(event.id, event);
      } else {
        byId.set(event.id, mergeDuplicateEventMeta(existing, event));
      }
    }
    return Array.from(byId.values()).sort(compareEvents);
  }

  /**
   * 두 원장만 병합한다(복구 저널·동기화 병합의 공통 기반).
   * - `reset_epoch`가 높은 쪽이 절대 우위를 가진다(이전 epoch의 base·이벤트 완전 폐기).
   * - 동일 epoch에서는 이벤트 ID 합집합으로 병합한다.
   */
  function mergeLedgers(ledgerA, ledgerB) {
    const a = normalizeLedger(ledgerA);
    const b = normalizeLedger(ledgerB);
    const combinedHistory = mergeResetHistory(a.reset_history, b.reset_history);

    if (a.reset_epoch !== b.reset_epoch) {
      const winner = a.reset_epoch > b.reset_epoch ? a : b;
      return foldEvents({
        v: VERSION,
        reset_epoch: winner.reset_epoch,
        reset_at: winner.reset_at,
        reset_reason: winner.reset_reason,
        reset_history: combinedHistory,
        base: cloneBalances(winner.base),
        base_at: winner.base_at,
        folded_at: winner.folded_at,
        folded_count: winner.folded_count,
        events: winner.events.slice(),
      });
    }

    const foldedAt = Math.max(a.folded_at || 0, b.folded_at || 0);
    const base = pickBase(a, b);
    const baseAt = foldedAt > 0
      ? Math.max(a.base_at, b.base_at, foldedAt)
      : (isZeroBalances(base) ? 0 : Math.max(a.base_at, b.base_at));
    return foldEvents({
      v: VERSION,
      reset_epoch: a.reset_epoch,
      reset_at: minPositive(a.reset_at, b.reset_at),
      reset_reason: pickLabel(a.reset_reason, b.reset_reason, 80) || 'initial_audit_cutover',
      reset_history: combinedHistory,
      base,
      base_at: baseAt,
      folded_at: foldedAt,
      folded_count: Math.max(a.folded_count || 0, b.folded_count || 0),
      events: mergeEvents(a.events, b.events, foldedAt),
    });
  }

  function normalizeReceipt(raw, id) {
    if (!isPlainObject(raw)) return null;
    if (typeof id !== 'string' || id.length === 0 || id.length > 128) return null;
    const out = {
      receiptId: id,
      grantedAt: Math.max(0, Math.trunc(finiteNumber(raw.grantedAt, 0))),
      grants: Array.isArray(raw.grants) ? raw.grants.slice(0, 16) : [],
    };
    const source = safeLabel(raw.source, 64);
    if (source) out.source = source;
    const detail = safeLabel(raw.detail, 240);
    if (detail) out.detail = detail;
    return out;
  }

  function mergeReceipts(receiptsA, receiptsB) {
    const out = {};
    for (const source of [receiptsA, receiptsB]) {
      if (!isPlainObject(source)) continue;
      for (const id of Object.keys(source).sort()) {
        if (isBlockedKey(id)) continue;
        const receipt = normalizeReceipt(source[id], id);
        if (!receipt) continue;
        const existing = out[id];
        if (!existing || receipt.grantedAt < existing.grantedAt) {
          out[id] = receipt;
        }
      }
    }
    return out;
  }

  function metaAt(state, key) {
    const meta = isPlainObject(state && state._meta_at) ? state._meta_at : {};
    const own = Math.max(0, finiteNumber(meta[key], 0));
    if (own > 0) return own;
    return Math.max(0, finiteNumber(state && state._updated_at, 0));
  }

  function pickMeta(local, remote, key) {
    const hasLocal = isPlainObject(local) && local[key] !== undefined;
    const hasRemote = isPlainObject(remote) && remote[key] !== undefined;
    if (hasLocal !== hasRemote) return hasLocal ? local[key] : remote[key];
    const localAt = metaAt(local, key);
    const remoteAt = metaAt(remote, key);
    if (localAt !== remoteAt) return localAt > remoteAt ? local[key] : remote[key];
    if (Array.isArray(local[key]) && Array.isArray(remote[key]) && local[key].length !== remote[key].length) {
      return local[key].length > remote[key].length ? local[key] : remote[key];
    }
    const localJson = stableJson(local[key]);
    const remoteJson = stableJson(remote[key]);
    return localJson >= remoteJson ? local[key] : remote[key];
  }

  function mergeMetaAt(local, remote) {
    const a = isPlainObject(local && local._meta_at) ? local._meta_at : {};
    const b = isPlainObject(remote && remote._meta_at) ? remote._meta_at : {};
    const out = {};
    for (const key of Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).sort()) {
      if (isBlockedKey(key)) continue;
      out[key] = Math.max(0, finiteNumber(a[key], 0), finiteNumber(b[key], 0));
    }
    return out;
  }

  /**
   * 두 보상 상태를 병합한다.
   */
  function mergeStates(local, remote, options) {
    const opts = isPlainObject(options) ? options : {};
    const adoptFields = opts.adoptFields !== false;
    const at = resolveTimestamp(opts, undefined);
    const a = normalizeState(local, { adoptFields, at });
    const b = normalizeState(remote, { adoptFields, at });
    const ledger = mergeLedgers(a.reward_ledger, b.reward_ledger);

    const epochA = a.reward_ledger.reset_epoch;
    const epochB = b.reward_ledger.reset_epoch;
    let mergedReceipts;
    if (epochA > epochB) {
      mergedReceipts = mergeReceipts(a.claimed_receipts, null);
    } else if (epochB > epochA) {
      mergedReceipts = mergeReceipts(b.claimed_receipts, null);
    } else {
      mergedReceipts = mergeReceipts(a.claimed_receipts, b.claimed_receipts);
    }

    const combinedMetaSource = {};
    for (const src of [b, a]) {
      for (const key of Object.keys(src)) {
        if (isBlockedKey(key)) continue;
        safeAssign(combinedMetaSource, key, src[key]);
      }
    }
    const merged = composeState(combinedMetaSource, ledger);
    merged.claimed_receipts = mergedReceipts;
    if (Array.isArray(a.shop_items) || Array.isArray(b.shop_items)) {
      merged.shop_items = pickMeta(a, b, 'shop_items');
    }
    if (typeof a.theme === 'string' || typeof b.theme === 'string') {
      merged.theme = pickMeta(a, b, 'theme');
    }
    merged._meta_at = mergeMetaAt(a, b);
    merged._updated_at = Math.max(
      Math.max(0, finiteNumber(a._updated_at, 0)),
      Math.max(0, finiteNumber(b._updated_at, 0))
    );
    return merged;
  }

  // ──────────────────────────────────────────
  // 5. 감사 리포트 / 활동 내역 / 무결성 검증 / CSV 내보내기
  // ──────────────────────────────────────────
  function resolveKeyLabel(key, shopItems) {
    if (KEY_LABELS[key]) return KEY_LABELS[key];
    if (isCustomKey(key)) {
      const cid = customIdFromKey(key);
      if (Array.isArray(shopItems)) {
        const found = shopItems.find((item) => item && item.id === cid);
        if (found) return `${found.icon || '🎁'} ${found.label || cid}`;
      }
      return `🎁 ${cid}`;
    }
    return key;
  }

  function describeReasonFallback(ev, shopItems) {
    const r = ev.reason || '';
    if (r === 'math_daily_goal') return '수학 오늘의 목표 달성 보상';
    if (r === 'daily_streak') return '일일 출석 학습 보상';
    if (r === 'diversity') return '다과목 학습 보상';
    if (r === 'milestone' || r.startsWith('milestone:')) return '학습 마일스톤 달성 보상';
    if (r === 'rocket_launch') return '연속 정답 로켓 발사 보상';
    if (r.startsWith('gem_exchange:')) {
      const target = r.slice('gem_exchange:'.length);
      if (target === 'youtube') return '보석 상점 교환 (유튜브 10분)';
      if (target === 'snack') return '보석 상점 교환 (간식)';
      return `보석 상점 교환 (${resolveKeyLabel(customKey(target), shopItems)})`;
    }
    if (r === 'youtube_ticket') return '유튜브 자유시간 모달 사용 차감';
    if (r === 'free_time_session') return '유튜브 브라우저 타이머 시작';
    if (r === 'snack') return '간식 사용 모달 차감';
    if (r.startsWith('custom_reward:')) {
      return `${resolveKeyLabel(customKey(r.slice('custom_reward:'.length)), shopItems)} 사용 승인`;
    }
    if (r === 'guardian_reward_removed') return '보호자 상점 항목 삭제에 따른 수량 정리';
    if (r === 'youtube_stray') return '10분 미만 자투리 자유시간 자동 정리';
    if (r === 'external_write') return '외부 스냅샷 하향 차감 반영';
    if (r === 'receipt') return '일일 학습 목표 달성 보상';
    if (r.startsWith('add:')) return '학습 보상 지급';
    return r || (ev.delta > 0 ? '보상 획득' : '보상 사용');
  }

  function buildAnnotatedEvents(ledger, shopItems) {
    const balances = cloneBalances(ledger.base);
    const entries = [];
    for (const event of ledger.events) {
      const key = event.key;
      const balanceBefore = key.startsWith(CUSTOM_PREFIX)
        ? balances.custom_inventory[key.slice(CUSTOM_PREFIX.length)] || 0
        : balances[key] || 0;
      applyDeltaToBalances(balances, key, event.delta);
      clampBalances(balances);
      const balanceAfter = key.startsWith(CUSTOM_PREFIX)
        ? balances.custom_inventory[key.slice(CUSTOM_PREFIX.length)] || 0
        : balances[key] || 0;

      entries.push({
        id: event.id,
        at: event.at,
        type: event.type,
        typeLabel: TYPE_LABELS[event.type] || event.type,
        key,
        keyLabel: resolveKeyLabel(key, shopItems),
        unit: key === 'youtube_minutes' ? '분' : '개',
        delta: event.delta,
        balanceBefore,
        balanceAfter,
        reason: event.reason || null,
        detail: event.detail || describeReasonFallback(event, shopItems),
        source: event.source || null,
        sourceLabel: event.source ? (SOURCE_LABELS[event.source] || event.source) : null,
        actor: event.actor || null,
        surface: event.surface || null,
        surfaceLabel: event.surface ? (SURFACE_LABELS[event.surface] || event.surface) : null,
        client: event.client || null,
        receipt: event.receipt || null,
        group: event.group || null,
      });
    }
    return entries;
  }

  function activity(state, options) {
    const rawLimit = typeof options === 'number'
      ? options
      : (isPlainObject(options) ? options.limit : undefined);
    const limit = Math.max(1, Math.min(500, Math.trunc(finiteNumber(rawLimit, 10))));
    const ledger = normalizeLedger(state && state.reward_ledger);
    const shopItems = isPlainObject(state) && Array.isArray(state.shop_items) ? state.shop_items : [];
    const entries = buildAnnotatedEvents(ledger, shopItems);
    return entries.slice(-limit).reverse();
  }

  /** 저장된 잔액과 원장 재계산 결과가 일치하는지 확인한다. */
  function verify(state) {
    if (!hasLedgerShape(state && state.reward_ledger)) {
      return { ok: false, reason: 'missing_ledger', mismatches: [] };
    }
    if (getEpoch(state) < BASELINE_RESET_EPOCH) {
      return { ok: false, reason: 'legacy_epoch', mismatches: [{ key: 'reset_epoch', expected: BASELINE_RESET_EPOCH, actual: getEpoch(state) }] };
    }
    const expected = balancesToSnapshot(computeBalances(state.reward_ledger));
    const actual = balancesToSnapshot(readBalances(state));
    const mismatches = [];
    for (const key of new Set([...Object.keys(expected), ...Object.keys(actual)])) {
      if (safeAmount(expected[key] || 0) !== safeAmount(actual[key] || 0)) {
        mismatches.push({
          key,
          expected: safeAmount(expected[key] || 0),
          actual: safeAmount(actual[key] || 0),
        });
      }
    }
    return {
      ok: mismatches.length === 0,
      reason: mismatches.length === 0 ? 'ok' : 'mismatch',
      mismatches,
    };
  }

  function formatLocalTimestamp(ms) {
    const num = Number(ms);
    if (!Number.isFinite(num) || num <= 0) return '-';
    const d = new Date(num);
    if (Number.isNaN(d.getTime())) return '-';
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  /**
   * 전체 감사 리포트(무결성 증명, 항목별 누적 획득/사용 합계, 전후 잔액 타임라인, 영수증, 초기화 이력)를 반환한다.
   */
  function auditReport(state, filter) {
    const flt = isPlainObject(filter) ? filter : {};
    const integrity = verify(state);
    const norm = normalizeState(state, { adoptFields: false });
    const ledger = norm.reward_ledger;
    const shopItems = Array.isArray(norm.shop_items) ? norm.shop_items : [];
    const allDesc = buildAnnotatedEvents(ledger, shopItems).reverse();

    const expectedSnap = balancesToSnapshot(computeBalances(ledger));
    const actualSnap = isPlainObject(state) ? balancesToSnapshot(readBalances(state)) : {};
    const summaryKeys = [...FIELD_KEYS];
    for (const item of shopItems) {
      if (item && item.id && !['youtube', 'snack', 'marble', 'bubble'].includes(item.id) && isSafeCustomId(item.id)) {
        const ck = customKey(item.id);
        if (!summaryKeys.includes(ck)) summaryKeys.push(ck);
      }
    }
    for (const k of Object.keys({ ...expectedSnap, ...actualSnap }).sort()) {
      if (!summaryKeys.includes(k)) summaryKeys.push(k);
    }

    const baseSnap = balancesToSnapshot(ledger.base);
    const totalsByKey = {};
    for (const key of summaryKeys) {
      const exp = safeAmount(expectedSnap[key] || 0);
      const act = safeAmount(actualSnap[key] || 0);
      totalsByKey[key] = {
        key,
        label: resolveKeyLabel(key, shopItems),
        unit: key === 'youtube_minutes' ? '분' : '개',
        base: safeAmount(baseSnap[key] || 0),
        earned: 0,
        exchangedIn: 0,
        exchangedOut: 0,
        consumed: 0,
        adjusted: 0,
        expected: exp,
        actual: act,
        matches: exp === act,
        eventCount: 0,
      };
    }

    for (const ev of allDesc) {
      const bucket = totalsByKey[ev.key];
      if (!bucket) continue;
      bucket.eventCount += 1;
      if (ev.type === 'exchange') {
        if (ev.delta > 0) bucket.exchangedIn += ev.delta;
        else bucket.exchangedOut += Math.abs(ev.delta);
      } else if (ev.type === 'adjust') {
        bucket.adjusted += ev.delta;
      } else if (ev.delta > 0) {
        bucket.earned += ev.delta;
      } else {
        bucket.consumed += Math.abs(ev.delta);
      }
    }

    const resetHistoryDesc = ledger.reset_history.slice().reverse();
    const timeline = allDesc.slice();
    for (const r of resetHistoryDesc) {
      timeline.push({
        id: r.id,
        at: r.at,
        type: 'reset',
        typeLabel: TYPE_LABELS.reset,
        key: 'all',
        keyLabel: '🔄 전체 보상 초기화',
        unit: '',
        delta: 0,
        balanceBefore: 0,
        balanceAfter: 0,
        reason: r.reason,
        detail: `${r.note || '전체 보상 0 초기화'} (Epoch #${r.epoch})`,
        source: r.actor === 'guardian' ? 'guardian' : 'system',
        sourceLabel: r.actor === 'guardian' ? '보호자 관리' : '시스템 기준점',
        actor: r.actor,
        surface: r.surface || null,
        surfaceLabel: r.surface ? (SURFACE_LABELS[r.surface] || r.surface) : null,
        client: r.client || null,
        receipt: null,
        group: null,
        epoch: r.epoch,
        previousBalances: r.previous_balances,
      });
    }

    timeline.sort((a, b) => {
      if (b.at !== a.at) return b.at - a.at;
      if (a.type === 'reset' && b.type !== 'reset') return 1;
      if (b.type === 'reset' && a.type !== 'reset') return -1;
      return a.id < b.id ? 1 : a.id > b.id ? -1 : 0;
    });

    const wantType = safeLabel(flt.type, 40) || 'all';
    const wantKey = safeLabel(flt.key, 80) || 'all';
    const since = flt.since !== undefined ? Math.max(0, finiteNumber(flt.since, 0)) : 0;
    const until = flt.until !== undefined ? Math.max(0, finiteNumber(flt.until, 0)) : 0;
    const query = (safeLabel(flt.query, 120) || '').toLowerCase();

    const filtered = timeline.filter((row) => {
      if (wantType !== 'all') {
        if (wantType === 'system') {
          if (row.type !== 'adjust' && row.type !== 'reset') return false;
        } else if (row.type !== wantType) {
          return false;
        }
      }
      if (wantKey !== 'all') {
        if (wantKey === 'custom') {
          if (!isCustomKey(row.key)) return false;
        } else if (row.key !== wantKey) {
          return false;
        }
      }
      if (since > 0 && row.at < since) return false;
      if (until > 0 && row.at > until) return false;
      if (query) {
        const hay = [
          row.detail,
          row.keyLabel,
          row.typeLabel,
          row.reason,
          row.sourceLabel,
          row.surfaceLabel,
          row.client,
          row.receipt,
          row.id,
        ].filter(Boolean).join(' ').toLowerCase();
        if (!hay.includes(query)) return false;
      }
      return true;
    });

    const limit = flt.limit && flt.limit > 0 ? Math.trunc(flt.limit) : filtered.length;
    const receiptMap = norm.claimed_receipts || {};
    const receipts = Object.keys(receiptMap)
      .map((id) => receiptMap[id])
      .sort((a, b) => (b.grantedAt || 0) - (a.grantedAt || 0));

    return {
      ok: integrity.ok,
      reason: integrity.reason,
      mismatches: integrity.mismatches,
      epoch: ledger.reset_epoch,
      resetAt: ledger.reset_at,
      resetReason: ledger.reset_reason,
      foldedCount: ledger.folded_count,
      foldedAt: ledger.folded_at,
      totalEvents: allDesc.length,
      summaries: summaryKeys.map((k) => totalsByKey[k]),
      entries: filtered.slice(0, limit),
      totalMatched: filtered.length,
      receipts,
      resetHistory: resetHistoryDesc,
    };
  }

  function escapeCsvCell(val) {
    const s = val === null || val === undefined ? '' : String(val);
    if (s.includes('"') || s.includes(',') || s.includes('\n') || s.includes('\r')) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  }

  function auditCsv(state, filter) {
    const report = auditReport(state, filter);
    const header = [
      '발생시각(로컬)',
      '발생시각(ISO)',
      '구분',
      '보상항목',
      '변화량',
      '변경전잔액',
      '변경후잔액',
      '상세사유',
      '사유코드',
      '출처/과목',
      '화면',
      '기기',
      '실행주체',
      '영수증ID',
      '트랜잭션그룹',
      '이벤트ID',
    ];
    const lines = [header.map(escapeCsvCell).join(',')];
    for (const e of report.entries) {
      const iso = e.at > 0 ? new Date(e.at).toISOString() : '';
      const deltaStr = e.type === 'reset'
        ? '0(전체초기화)'
        : `${e.delta > 0 ? '+' : ''}${e.delta}${e.unit}`;
      lines.push([
        formatLocalTimestamp(e.at),
        iso,
        e.typeLabel,
        e.keyLabel,
        deltaStr,
        e.type === 'reset' ? '-' : `${e.balanceBefore}${e.unit}`,
        e.type === 'reset' ? '0' : `${e.balanceAfter}${e.unit}`,
        e.detail,
        e.reason || '',
        e.sourceLabel || '',
        e.surfaceLabel || '',
        e.client || '',
        e.actor || '',
        e.receipt || '',
        e.group || '',
        e.id,
      ].map(escapeCsvCell).join(','));
    }
    return lines.join('\r\n');
  }

  return Object.freeze({
    VERSION,
    BASELINE_RESET_EPOCH,
    FIELD_KEYS,
    CUSTOM_PREFIX,
    YOUTUBE_UNIT,
    KEY_LABELS,
    TYPE_LABELS,
    SURFACE_LABELS,
    SOURCE_LABELS,
    customKey,
    isCustomKey,
    customIdFromKey,
    formatLocalTimestamp,
    getEpoch,
    snapshot,
    diffSnapshots,
    balanceSnapshot,
    normalizeState,
    resetState,
    createLedger,
    computeBalances,
    applyDeltas,
    setQuantity,
    mergeStates,
    mergeLedgers,
    mergeReceipts,
    activity,
    verify,
    auditReport,
    auditCsv,
  });
});
