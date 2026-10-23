/**
 * @fileoverview 보상 원장(Reward Ledger) — 획득/사용을 델타로 기록하고 병합하는 순수 도메인 모듈
 * @module reward-ledger
 *
 * 왜 필요한가:
 * - 보상 잔액을 "현재 값 스냅샷"으로만 동기화하면, 소비(차감) 사실이 사라진다.
 *   기기·탭·클라우드에 남아 있는 더 큰 값이 다시 병합되면서 이미 쓴 보상이 되살아난다.
 * - 이 모듈은 잔액을 `base + Σ(delta)`로 계산한다. 획득은 +, 사용은 - 이벤트로 남고,
 *   병합은 이벤트 id 합집합이므로 교환 가능(commutative)·멱등(idempotent)하다.
 *   따라서 "쓴 것은 다시 채워지지 않고", "실제로 획득한 만큼만" 남는다.
 * - 영수증(claimed_receipts)도 합집합으로 병합해 다른 기기에서 같은 보상이 중복 지급되지 않는다.
 *
 * 저장 표현은 `study_rewards.reward_ledger` 한 곳이며, 모든 함수는 순수하다(입력 state를 변형하지 않음).
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.RewardLedger = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const VERSION = 1;
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
  const MAX_EVENTS = 480;
  const KEEP_EVENTS = 120;
  const MAX_ID_LENGTH = 96;
  const BLOCKED_KEYS = Object.freeze(['__proto__', 'constructor', 'prototype']);

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

  function safeAmount(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return 0;
    return Math.max(-MAX_AMOUNT, Math.min(MAX_AMOUNT, Math.trunc(num)));
  }

  function safeLabel(value, maxLength) {
    if (typeof value !== 'string' || value.length === 0) return null;
    return value.slice(0, maxLength);
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
    for (const key of FIELD_KEYS) out[key] = safeAmount(src[key]);
    const custom = isPlainObject(src.custom_inventory) ? src.custom_inventory : {};
    for (const id of Object.keys(custom)) {
      if (!isSafeCustomId(id)) continue;
      out.custom_inventory[id] = safeAmount(custom[id]);
    }
    return out;
  }

  function clampBalances(balances) {
    for (const key of FIELD_KEYS) {
      if (balances[key] < 0) balances[key] = 0;
    }
    for (const id of Object.keys(balances.custom_inventory)) {
      if (balances.custom_inventory[id] < 0) balances.custom_inventory[id] = 0;
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
    for (const key of FIELD_KEYS) out[key] = safeAmount(src[key]);
    const custom = isPlainObject(src.custom_inventory) ? src.custom_inventory : {};
    for (const id of Object.keys(custom)) {
      if (!isSafeCustomId(id)) continue;
      out.custom_inventory[id] = safeAmount(custom[id]);
    }
    return out;
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
  // 2. 원장(ledger) 구조
  // ──────────────────────────────────────────
  function compareEvents(a, b) {
    if (a.at !== b.at) return a.at - b.at;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  }

  function compactEvent(raw) {
    // 초기 병합 결함이 빈 브라우저({})를 하향 스냅샷으로 오인해 남긴
    // legacy_snapshot_downward 가짜 차감 이벤트는 정규화 시 제거해 자가 치유한다.
    if (raw && raw.reason === 'legacy_snapshot_downward') return null;
    const event = {
      id: safeLabel(raw.id, MAX_ID_LENGTH),
      at: Math.max(0, finiteNumber(raw.at, 0)),
      key: normalizeKey(raw.key),
      delta: safeAmount(raw.delta),
      type: safeLabel(raw.type, 32) || 'adjust',
    };
    if (!event.id || !event.key || event.delta === 0) return null;
    const reason = safeLabel(raw.reason, 48);
    if (reason) event.reason = reason;
    const receipt = safeLabel(raw.receipt, 128);
    if (receipt) event.receipt = receipt;
    const group = safeLabel(raw.group, MAX_ID_LENGTH);
    if (group) event.group = group;
    return event;
  }

  function normalizeLedger(raw) {
    const src = isPlainObject(raw) ? raw : {};
    const base = cloneBalances(src.base);
    const foldedAt = Math.max(0, finiteNumber(src.folded_at, 0));
    const rawBaseAt = Math.max(0, finiteNumber(src.base_at, 0));
    // 접힌 이벤트가 없는 상태에서 빈 base(0)에 찍힌 base_at은
    // 다른 기기의 초기 이관 base나 같은 시각의 첫 적립 이벤트를 덮지 못하도록 0으로 정규화한다.
    const baseAt = foldedAt > 0
      ? Math.max(rawBaseAt, foldedAt)
      : (isZeroBalances(base) ? 0 : rawBaseAt);
    const rawEvents = Array.isArray(src.events) ? src.events : [];
    const seen = new Set();
    const events = [];
    for (const item of rawEvents) {
      if (!isPlainObject(item)) continue;
      const event = compactEvent(item);
      if (!event || seen.has(event.id)) continue;
      if (foldedAt > 0 && event.at <= foldedAt) continue;
      seen.add(event.id);
      events.push(event);
    }
    events.sort(compareEvents);
    return { v: VERSION, base, base_at: baseAt, folded_at: foldedAt, events };
  }

  function createLedger(balances, at) {
    const cloned = cloneBalances(balances);
    const baseAt = isZeroBalances(cloned) ? 0 : Math.max(0, finiteNumber(at, 0));
    return {
      v: VERSION,
      base: cloned,
      base_at: baseAt,
      folded_at: 0,
      events: [],
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

  /** 이벤트가 너무 많아지면 오래된 이벤트를 base로 접는다(잔액은 그대로 유지). */
  function foldEvents(ledger) {
    const currentFoldedAt = Math.max(0, finiteNumber(ledger.folded_at, 0));
    if (ledger.events.length <= MAX_EVENTS) {
      return {
        v: VERSION,
        base: ledger.base,
        base_at: ledger.base_at,
        folded_at: currentFoldedAt,
        events: ledger.events,
      };
    }
    const sorted = ledger.events.slice().sort(compareEvents);
    let foldCount = sorted.length - KEEP_EVENTS;
    const cutoffAt = sorted[foldCount - 1].at;
    // 같은 밀리초(at === cutoffAt)에 생성된 이벤트가 경계에 걸치면 함께 접어
    // folded_at 기준 필터링(event.at <= folded_at)에서 누락되는 이벤트가 없게 한다.
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
      base,
      base_at: Math.max(ledger.base_at || 0, nextFoldedAt),
      folded_at: nextFoldedAt,
      events: sorted.slice(foldCount),
    };
  }

  function appendEvents(ledger, specs, meta) {
    const base = normalizeLedger(ledger);
    const options = isPlainObject(meta) ? meta : {};
    const at = Math.max(0, finiteNumber(options.at, Date.now()));
    const group = safeLabel(options.group, MAX_ID_LENGTH);
    const events = base.events.slice();
    const eventIds = [];
    for (const spec of Array.isArray(specs) ? specs : []) {
      if (!isPlainObject(spec)) continue;
      const key = normalizeKey(spec.key);
      const delta = safeAmount(spec.delta);
      if (!key || delta === 0) continue;
      const event = {
        id: makeEventId(at),
        at,
        key,
        delta,
        type: safeLabel(spec.type || options.type, 32) || 'adjust',
      };
      const reason = safeLabel(spec.reason || options.reason, 48);
      if (reason) event.reason = reason;
      const receipt = safeLabel(spec.receipt || options.receipt, 128);
      if (receipt) event.receipt = receipt;
      if (group) event.group = group;
      events.push(event);
      eventIds.push(event.id);
    }
    return {
      ledger: foldEvents({
        v: VERSION,
        base: base.base,
        base_at: base.base_at,
        folded_at: base.folded_at || 0,
        events,
      }),
      eventIds,
    };
  }

  // ──────────────────────────────────────────
  // 3. 상태 정규화 / 구성
  // ──────────────────────────────────────────
  function hasLedgerShape(raw) {
    return isPlainObject(raw) && Number(raw.v) === VERSION && Array.isArray(raw.events);
  }

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
   * - 원장이 없으면 현재 값으로 base를 만들어 1회 이관한다(이관 이후 잔액은 항상 델타의 합).
   * - `adoptFields`가 true면 원장과 다른 필드 값(외부 스크립트·구버전 쓰기)을 조정 이벤트로 남긴다.
   *   값 자체를 지우지 않으면서 감사 기록을 유지하기 위함이다.
   */
  function normalizeState(raw, options) {
    const opts = isPlainObject(options) ? options : {};
    const src = isPlainObject(raw) ? raw : {};
    const observed = readBalances(src);
    const fallbackAt = Math.max(0, finiteNumber(opts.at, finiteNumber(src._updated_at, 0)));
    const hadLedger = hasLedgerShape(src.reward_ledger);
    let ledger;

    if (hadLedger) {
      const hadPoisonedLegacyDownward = Array.isArray(src.reward_ledger.events)
        && src.reward_ledger.events.some((item) => item && item.reason === 'legacy_snapshot_downward');
      ledger = normalizeLedger(src.reward_ledger);
      if (opts.adoptFields !== false && !hadPoisonedLegacyDownward) {
        const expected = balancesToSnapshot(computeBalances(ledger));
        const actual = balancesToSnapshot(observed);
        // 외부 스냅샷 쓰기는 "줄어든 사실"만 인정한다.
        // 잔액을 늘리는 값은 획득 이벤트가 있어야만 반영된다(무단 충전 방지).
        const deltas = diffSnapshots(expected, actual)
          .filter((delta) => delta.delta < 0);
        if (deltas.length > 0) {
          ledger = appendEvents(ledger, deltas, {
            at: fallbackAt,
            type: 'adjust',
            reason: 'external_write',
          }).ledger;
        }
      }
    } else {
      ledger = createLedger(observed, fallbackAt);
    }

    const stray = computeBalances(ledger).youtube_minutes;
    if (stray % YOUTUBE_UNIT !== 0) {
      const normalizedMinutes = Math.max(0, Math.floor(stray / YOUTUBE_UNIT) * YOUTUBE_UNIT);
      ledger = appendEvents(
        ledger,
        [{ key: 'youtube_minutes', delta: normalizedMinutes - stray }],
        { at: fallbackAt, type: 'adjust', reason: 'youtube_stray' }
      ).ledger;
    }

    return composeState(src, ledger);
  }

  /** 현재 상태의 잔액(평면 스냅샷)을 반환한다. */
  function balanceSnapshot(state) {
    if (hasLedgerShape(state && state.reward_ledger)) {
      return balancesToSnapshot(computeBalances(state.reward_ledger));
    }
    return snapshot(state);
  }

  /** 델타 목록을 원장에 추가하고 잔액을 다시 계산한 새 상태를 반환한다. */
  function applyDeltas(state, deltas, meta) {
    const normalized = normalizeState(state, { adoptFields: false, at: meta && meta.at });
    const applied = appendEvents(normalized.reward_ledger, deltas, meta);
    return {
      state: composeState(normalized, applied.ledger),
      eventIds: applied.eventIds,
    };
  }

  /** 절대 수량을 지정한다(보호자 삭제·정리 등). 실제 변화는 조정 이벤트로 기록된다. */
  function setQuantity(state, key, value, meta) {
    const normalized = normalizeState(state, { adoptFields: false, at: meta && meta.at });
    const target = Math.max(0, safeAmount(value));
    const snapshotNow = balancesToSnapshot(computeBalances(normalized.reward_ledger));
    const delta = target - safeAmount(snapshotNow[key] || 0);
    if (delta === 0) return { state: normalized, eventIds: [] };
    return applyDeltas(normalized, [{ key, delta }], meta);
  }

  // ──────────────────────────────────────────
  // 4. 병합(교환 가능 · 멱등)
  // ──────────────────────────────────────────
  function stableJson(value) {
    try {
      const serialized = JSON.stringify(value);
      return serialized === undefined ? 'undefined' : serialized;
    } catch (e) {
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

  /** 두 원장만 병합한다(상태 메타와 무관). 복구 저널·동기화 병합의 공통 기반. */
  function mergeLedgers(ledgerA, ledgerB) {
    const a = normalizeLedger(ledgerA);
    const b = normalizeLedger(ledgerB);
    const foldedAt = Math.max(a.folded_at || 0, b.folded_at || 0);
    const base = pickBase(a, b);
    const baseAt = foldedAt > 0
      ? Math.max(a.base_at, b.base_at, foldedAt)
      : (isZeroBalances(base) ? 0 : Math.max(a.base_at, b.base_at));
    return foldEvents({
      v: VERSION,
      base,
      base_at: baseAt,
      folded_at: foldedAt,
      events: mergeEvents(a.events, b.events, foldedAt),
    });
  }

  function mergeEvents(eventsA, eventsB, foldedAt) {
    const cutoff = Math.max(0, finiteNumber(foldedAt, 0));
    const seen = new Set();
    const merged = [];
    for (const event of [...eventsA, ...eventsB]) {
      if (cutoff > 0 && event.at <= cutoff) continue;
      if (seen.has(event.id)) continue;
      seen.add(event.id);
      merged.push(event);
    }
    merged.sort(compareEvents);
    return merged;
  }

  function normalizeReceipt(raw, id) {
    if (!isPlainObject(raw)) return null;
    if (typeof id !== 'string' || id.length === 0 || id.length > 128) return null;
    const out = {
      receiptId: id,
      grantedAt: Math.max(0, finiteNumber(raw.grantedAt, 0)),
      grants: Array.isArray(raw.grants) ? raw.grants.slice(0, 16) : [],
    };
    return out;
  }

  function mergeReceipts(receiptsA, receiptsB) {
    const out = {};
    for (const source of [receiptsA, receiptsB]) {
      if (!isPlainObject(source)) continue;
      for (const id of Object.keys(source)) {
        if (isBlockedKey(id)) continue;
        const receipt = normalizeReceipt(source[id], id);
        if (!receipt) continue;
        const existing = out[id];
        if (!existing || receipt.grantedAt < existing.grantedAt) out[id] = receipt;
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
    for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
      if (isBlockedKey(key)) continue;
      out[key] = Math.max(0, finiteNumber(a[key], 0), finiteNumber(b[key], 0));
    }
    return out;
  }

  /**
   * 두 보상 상태를 병합한다.
   * 잔액은 이벤트 합집합으로만 결정되므로, 어느 한쪽 스냅샷의 큰 값이 소비를 덮어쓰지 못하며
   * 빈 브라우저({})의 0 잔액도 클라우드 원장을 깎아내리지 못한다(교환 가능·멱등·항등원 보장).
   * @param {object} local
   * @param {object} remote
   * @param {{adoptFields?: boolean, at?: number}} [options]
   */
  function mergeStates(local, remote, options) {
    const opts = isPlainObject(options) ? options : {};
    const adoptFields = opts.adoptFields !== false;
    const localHadLedger = hasLedgerShape(local && local.reward_ledger);
    const remoteHadLedger = hasLedgerShape(remote && remote.reward_ledger);
    const a = normalizeState(local, { adoptFields, at: opts.at });
    const b = normalizeState(remote, { adoptFields, at: opts.at });
    // 한쪽만 원장을 가지고 있다면, 원장 없는 쪽의 미검증 스냅샷 잔액은 base가 될 수 없다
    // (사용 완료한 보상이 옛 스냅샷으로 되살아나는 현상 차단).
    const legacySide = localHadLedger === remoteHadLedger ? null : localHadLedger ? b : a;
    if (legacySide) {
      legacySide.reward_ledger = createLedger({}, 0);
    }
    const ledger = mergeLedgers(a.reward_ledger, b.reward_ledger);

    const combinedMetaSource = {};
    for (const src of [b, a]) {
      for (const key of Object.keys(src)) {
        if (isBlockedKey(key)) continue;
        safeAssign(combinedMetaSource, key, src[key]);
      }
    }
    const merged = composeState(combinedMetaSource, ledger);
    merged.claimed_receipts = mergeReceipts(a.claimed_receipts, b.claimed_receipts);
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
  // 5. 조회/검증
  // ──────────────────────────────────────────
  function activity(state, options) {
    const opts = isPlainObject(options) ? options : {};
    const limit = Math.max(1, Math.min(50, Math.trunc(finiteNumber(opts.limit, 10))));
    const ledger = normalizeLedger(state && state.reward_ledger);
    const balances = cloneBalances(ledger.base);
    const entries = [];
    for (const event of ledger.events) {
      applyDeltaToBalances(balances, event.key, event.delta);
      clampBalances(balances);
      const key = event.key;
      const balanceAfter = key.startsWith(CUSTOM_PREFIX)
        ? balances.custom_inventory[key.slice(CUSTOM_PREFIX.length)] || 0
        : balances[key] || 0;
      entries.push({
        id: event.id,
        at: event.at,
        type: event.type,
        key: event.key,
        delta: event.delta,
        balanceAfter,
        reason: event.reason || null,
        receipt: event.receipt || null,
      });
    }
    return entries.slice(-limit).reverse();
  }

  /** 저장된 잔액과 원장 재계산 결과가 일치하는지 확인한다. */
  function verify(state) {
    if (!hasLedgerShape(state && state.reward_ledger)) {
      return { ok: false, reason: 'missing_ledger', mismatches: [] };
    }
    const expected = balancesToSnapshot(computeBalances(state.reward_ledger));
    const actual = balancesToSnapshot(readBalances(state));
    const mismatches = [];
    for (const key of new Set([...Object.keys(expected), ...Object.keys(actual)])) {
      if (safeAmount(expected[key] || 0) !== safeAmount(actual[key] || 0)) {
        mismatches.push({ key, expected: safeAmount(expected[key] || 0), actual: safeAmount(actual[key] || 0) });
      }
    }
    return { ok: mismatches.length === 0, reason: mismatches.length === 0 ? 'ok' : 'mismatch', mismatches };
  }

  return Object.freeze({
    VERSION,
    FIELD_KEYS,
    CUSTOM_PREFIX,
    YOUTUBE_UNIT,
    customKey,
    snapshot,
    diffSnapshots,
    balanceSnapshot,
    normalizeState,
    createLedger,
    computeBalances,
    applyDeltas,
    setQuantity,
    mergeStates,
    mergeLedgers,
    mergeReceipts,
    activity,
    verify,
  });
});
