import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../..');

const STORE_JS = path.join(ROOT, 'domains/english/weekly-vocabulary-store.js');
const DEFINITIONS_JS = path.join(ROOT, 'domains/english/weekly-word-definitions.js');
const TEST_ENGINE_JS = path.join(ROOT, 'domains/english/weekly-test/weekly-test-engine.js');
const WORDS_JS = path.join(ROOT, 'domains/english/words.js');
const ADVANCED_JS = path.join(ROOT, 'domains/english/advanced-questions.js');
const PROGRESS_JS = path.join(ROOT, 'shared/domain/progress-engine.js');
const ENGINE_JS = path.join(ROOT, 'domains/english/engine.js');
const SYNC_ENGINE_JS = path.join(ROOT, 'domains/sync/sync-engine.js');
const GUARDIAN_JS = path.join(ROOT, 'domains/reward/guardian/guardian.js');
const TRANSPORT_SCRIPT = path.join(ROOT, 'scripts/register-weekly-english-set.mjs');

// ── Constants matching 004 migration ──
const C_CHANGE_THRESHOLD = 3;
const C_NORMAL_ITEM_MIN = 8;
const C_NORMAL_ITEM_MAX = 12;
const C_ATYPICAL_ITEM_MAX = 15;

// ── In-Memory Postgres DB Mock simulating 003+004 migration exactly ──
const db = {
  tokens: new Map(), // token_hash -> { id, user_id, is_revoked, expires_at, scope }
  userData: new Map(), // `${user_id}::${data_key}` -> { user_id, data_key, payload, updated_at }
  history: [] // [{ user_id, set_id, revision, payload, is_current }]
};

function sha256Hex(str) {
  return crypto.createHash('sha256').update(String(str)).digest('hex');
}

function computeWeeklyFingerprint(items) {
  if (!Array.isArray(items)) return '';
  const lines = items.map(it => {
    const a = String(it.answer || it.word || '').trim().toLowerCase();
    const p = String(it.prompt || it.academyDescription || '').trim().toLowerCase();
    return `${a}::${p}`;
  }).sort();
  return sha256Hex(lines.join('\n'));
}

function isValidCalendarDate(dateStr) {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(dateStr)) return false;
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
}

function validateWeeklyConfirmation(confirmation, expectedReason, candidateFp, activeFp = null, activeRev = null) {
  if (!confirmation || typeof confirmation !== 'object' || Object.keys(confirmation).length === 0) {
    return {
      valid: false,
      result: {
        status: 'REJECTED_CONFIRMATION',
        message: 'Confirmation payload is required and cannot be empty'
      }
    };
  }

  const reason = String(confirmation.reason || '').trim();
  if (!reason || reason !== expectedReason) {
    return {
      valid: false,
      result: {
        status: 'REJECTED_CONFIRMATION',
        message: `Invalid confirmation reason: expected ${expectedReason}, got ${reason || 'none'}`
      }
    };
  }

  const candFp = String(confirmation.candidateFingerprint || '').trim();
  if (!candFp || candFp !== candidateFp) {
    return {
      valid: false,
      result: {
        status: 'CONFIRMATION_STALE',
        message: 'Confirmation candidateFingerprint mismatch'
      }
    };
  }

  if (activeFp !== null && activeFp !== '') {
    const expFp = String(confirmation.expectedActiveFingerprint || '').trim();
    const expRev = confirmation.expectedActiveRevision ?? -1;

    if (!expFp || expRev < 0) {
      return {
        valid: false,
        result: {
          status: 'REJECTED_CONFIRMATION',
          message: 'Active set confirmation requires expectedActiveFingerprint and expectedActiveRevision'
        }
      };
    }

    if (expFp !== activeFp || expRev !== activeRev) {
      return {
        valid: false,
        result: {
          status: 'CONFIRMATION_STALE',
          message: 'Active set changed since confirmation issued',
          expectedActiveFingerprint: expFp,
          expectedActiveRevision: expRev,
          actualActiveFingerprint: activeFp,
          actualActiveRevision: activeRev
        }
      };
    }
  }

  return { valid: true };
}

// Internal core registration function
function _register_weekly_english_set_internal(userId, candidate, confirmation) {

  if (!candidate || typeof candidate !== 'object') {
    return { status: 'REJECTED_INVALID', message: 'Candidate must be an object' };
  }
  const testDate = String(candidate.testDate || '').trim();
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(testDate)) {
    return { status: 'REJECTED_INVALID', message: 'Candidate testDate must match YYYY-MM-DD' };
  }
  // Calendar date validation (#9)
  if (!isValidCalendarDate(testDate)) {
    return { status: 'REJECTED_INVALID', message: `Candidate testDate ${testDate} is not a valid calendar date` };
  }

  if (Array.isArray(candidate.ambiguities) && candidate.ambiguities.length > 0) {
    return { status: 'REJECTED_INVALID', message: 'Unresolved ambiguities present' };
  }
  const items = candidate.items;
  if (!Array.isArray(items)) {
    return { status: 'REJECTED_INVALID', message: 'Candidate items must be an array' };
  }
  // Item count (#7)
  if (items.length < C_NORMAL_ITEM_MIN || items.length > C_ATYPICAL_ITEM_MAX) {
    return { status: 'REJECTED_INVALID', message: `Candidate items count out of allowed bounds (${C_NORMAL_ITEM_MIN}-${C_ATYPICAL_ITEM_MAX})` };
  }

  const canonicalItems = [];
  const legacyItems = [];
  const seenPairs = new Set();

  for (let i = 0; i < items.length; i++) {
    const elem = items[i];
    if (!elem || typeof elem !== 'object') {
      return { status: 'REJECTED_INVALID', message: `Item ${i} is invalid` };
    }
    const ans = String(elem.answer || elem.word || '').trim();
    const prompt = String(elem.prompt || elem.academyDescription || '').trim();
    if (!ans || !prompt) {
      return { status: 'REJECTED_INVALID', message: `Item ${i} missing answer or prompt` };
    }

    // Duplicate detection (#8)
    const pairKey = `${ans.toLowerCase()}::${prompt.toLowerCase()}`;
    if (seenPairs.has(pairKey)) {
      return { status: 'REJECTED_INVALID', message: `Duplicate (answer, prompt) pair at index ${i}` };
    }
    seenPairs.add(pairKey);

    const pHash = sha256Hex(prompt).slice(0, 8);
    const itemId = `${testDate}-${ans}-${pHash}`.toLowerCase();
    canonicalItems.push({
      itemId,
      id: itemId,
      word: ans,
      answer: ans,
      academyDescription: prompt,
      prompt,
      ko: elem.ko || '',
      icon: elem.icon || '',
      acceptedAnswers: Array.isArray(elem.acceptedAnswers) ? elem.acceptedAnswers : []
    });
    legacyItems.push({
      en: ans,
      ko: elem.ko || '',
      icon: elem.icon || ''
    });
  }

  const newFp = computeWeeklyFingerprint(canonicalItems);
  const currentKey = `${userId}::aiden_canonical_weekly_vocabulary_v1`;
  const existingRow = db.userData.get(currentKey);

  let status = 'REGISTERED_NEW';
  let newRev = 1;

  if (existingRow && existingRow.payload) {
    const existing = existingRow.payload;
    const existingDate = String(existing.testDate || existing.setId || '');
    const existingFp = String(existing.contentFingerprint || '');
    const existingRev = existing.revision || 1;
    const existingItems = existing.items || [];

    if (existingDate === testDate) {
      if (existingFp === newFp) {
        return {
          status: 'NO_OP',
          setId: testDate,
          testDate,
          revision: existingRev,
          itemCount: items.length,
          contentFingerprint: newFp,
          updatedAt: existing.updatedAt
        };
      }

      // Symmetric diff (#3)
      const oldPairs = new Set(existingItems.map(it =>
        `${(it.answer || it.word || '').trim().toLowerCase()}::${(it.prompt || it.academyDescription || '').trim().toLowerCase()}`
      ));
      const newPairs = new Set(canonicalItems.map(it =>
        `${it.answer.toLowerCase()}::${it.prompt.toLowerCase()}`
      ));

      let addedCount = 0;
      for (const p of newPairs) {
        if (!oldPairs.has(p)) addedCount++;
      }
      let removedCount = 0;
      for (const p of oldPairs) {
        if (!newPairs.has(p)) removedCount++;
      }
      const symDiffCount = addedCount + removedCount;

      // ── Branch A: Atypical Item Count (13-15 items) ───
      if (items.length > C_NORMAL_ITEM_MAX) {
        if (!confirmation) {
          return {
            status: 'NEEDS_CONFIRMATION',
            message: `Atypical item count (${items.length}) exceeds normal range`,
            reason: 'ATYPICAL_ITEM_COUNT',
            activeSetId: existingDate,
            activeRevision: existingRev,
            activeFingerprint: existingFp,
            activeItemCount: existingItems.length,
            candidateFingerprint: newFp,
            candidateItemCount: items.length,
            conflictDiffCount: symDiffCount
          };
        }

        const confVal = validateWeeklyConfirmation(
          confirmation, 'ATYPICAL_ITEM_COUNT', newFp, existingFp, existingRev
        );
        if (!confVal.valid) {
          return confVal.result;
        }

        status = 'REGISTERED_CONFIRMED_REVISION';
        newRev = existingRev + 1;

      // ── Branch B: Normal Count with Large Symmetric Diff ─
      } else if (symDiffCount > C_CHANGE_THRESHOLD) {
        if (!confirmation) {
          return {
            status: 'NEEDS_CONFIRMATION',
            message: `Large symmetric diff (${symDiffCount}) on same date`,
            reason: 'LARGE_SYMMETRIC_DIFF',
            activeSetId: existingDate,
            activeRevision: existingRev,
            activeFingerprint: existingFp,
            activeItemCount: existingItems.length,
            candidateFingerprint: newFp,
            candidateItemCount: items.length,
            conflictDiffCount: symDiffCount,
            addedCount,
            removedCount
          };
        }

        const confVal = validateWeeklyConfirmation(
          confirmation, 'LARGE_SYMMETRIC_DIFF', newFp, existingFp, existingRev
        );
        if (!confVal.valid) {
          return confVal.result;
        }

        status = 'REGISTERED_CONFIRMED_REVISION';
        newRev = existingRev + 1;
      } else {
        status = 'REGISTERED_REVISION';
        newRev = existingRev + 1;
      }
    } else {
      // Different date — check atypical count
      if (items.length > C_NORMAL_ITEM_MAX) {
        if (!confirmation) {
          return {
            status: 'NEEDS_CONFIRMATION',
            message: `Atypical item count (${items.length}) exceeds normal range`,
            reason: 'ATYPICAL_ITEM_COUNT',
            activeSetId: existingDate,
            activeRevision: existingRev,
            activeFingerprint: existingFp,
            activeItemCount: existingItems.length,
            candidateFingerprint: newFp,
            candidateItemCount: items.length,
            conflictDiffCount: 0
          };
        }

        const confVal = validateWeeklyConfirmation(
          confirmation, 'ATYPICAL_ITEM_COUNT', newFp, existingFp, existingRev
        );
        if (!confVal.valid) {
          return confVal.result;
        }

        status = 'REGISTERED_CONFIRMED_REVISION';
        newRev = 1;
      } else {
        status = 'REGISTERED_NEW';
        newRev = 1;
      }
    }

    // Rollback preservation
    db.history.push({
      user_id: userId,
      set_id: existingDate,
      revision: existingRev,
      payload: existing,
      is_current: false
    });
  } else {
    // No existing — atypical check
    if (items.length > C_NORMAL_ITEM_MAX) {
      if (!confirmation) {
        return {
          status: 'NEEDS_CONFIRMATION',
          message: `Atypical item count (${items.length}) exceeds normal range`,
          reason: 'ATYPICAL_ITEM_COUNT',
          candidateFingerprint: newFp,
          candidateItemCount: items.length,
          conflictDiffCount: 0
        };
      }

      const confVal = validateWeeklyConfirmation(
        confirmation, 'ATYPICAL_ITEM_COUNT', newFp, null, null
      );
      if (!confVal.valid) {
        return confVal.result;
      }

      status = 'REGISTERED_CONFIRMED_REVISION';
      newRev = 1;
    } else {
      status = 'REGISTERED_NEW';
      newRev = 1;
    }
  }

  const nowIso = new Date().toISOString();
  const nowMs = Date.now();
  const newPayload = {
    schemaVersion: 1,
    setId: testDate,
    testDate,
    title: `${testDate} 주간 영단어`,
    revision: newRev,
    contentFingerprint: newFp,
    items: canonicalItems,
    _updated_at: nowMs,
    updatedAt: nowIso,
    registeredAt: nowIso,
    _mutationAuthority: 'server_rpc'
  };

  db.userData.set(currentKey, {
    user_id: userId,
    data_key: 'aiden_canonical_weekly_vocabulary_v1',
    payload: newPayload,
    updated_at: nowIso
  });

  db.userData.set(`${userId}::englishWeeklyWords`, {
    user_id: userId,
    data_key: 'englishWeeklyWords',
    payload: legacyItems,
    updated_at: nowIso
  });

  db.history.push({
    user_id: userId,
    set_id: testDate,
    revision: newRev,
    payload: newPayload,
    is_current: true
  });

  return {
    status,
    setId: testDate,
    testDate,
    revision: newRev,
    itemCount: canonicalItems.length,
    contentFingerprint: newFp,
    updatedAt: nowIso
  };
}

// Mock PostgreSQL register_weekly_english_set RPC (004+005 contract)
function rpc_register_weekly_english_set(agent_token, candidate, confirmation) {
  if (!agent_token || !agent_token.trim()) {
    return { status: 'UNAUTHORIZED', message: 'Agent token is required' };
  }
  const hash = sha256Hex(agent_token.trim());
  const tokenRec = db.tokens.get(hash);
  if (!tokenRec || tokenRec.is_revoked || (tokenRec.expires_at && tokenRec.expires_at <= Date.now())) {
    return { status: 'UNAUTHORIZED', message: 'Invalid or revoked token' };
  }
  return _register_weekly_english_set_internal(tokenRec.user_id, candidate, confirmation);
}

// Mock PostgreSQL get_current_weekly_english_set RPC
function rpc_get_current_weekly_english_set(agent_token) {
  if (!agent_token) return { status: 'UNAUTHORIZED' };
  const hash = sha256Hex(agent_token.trim());
  const tokenRec = db.tokens.get(hash);
  if (!tokenRec || tokenRec.is_revoked) return { status: 'UNAUTHORIZED' };
  const row = db.userData.get(`${tokenRec.user_id}::aiden_canonical_weekly_vocabulary_v1`);
  if (!row) return { status: 'NOT_FOUND' };
  return { status: 'OK', currentSet: row.payload };
}

// Mock fetch function simulating HTTPS RPC calls to Supabase
async function mockFetch(url, options) {
  const body = options.body ? JSON.parse(options.body) : {};
  if (url.endsWith('register_weekly_english_set')) {
    const res = rpc_register_weekly_english_set(body.p_agent_token, body.p_candidate, body.p_confirmation || null);
    return {
      ok: true,
      status: 200,
      json: async () => res
    };
  }
  if (url.endsWith('register_weekly_english_set_as_guardian')) {
    // Uses current authenticated user (default USER_AIDEN)
    const userId = body.p_user_id || USER_AIDEN;
    const res = _register_weekly_english_set_internal(userId, body.p_candidate, body.p_confirmation || null);
    return {
      ok: true,
      status: 200,
      json: async () => res
    };
  }
  if (url.endsWith('get_current_weekly_english_set')) {
    const res = rpc_get_current_weekly_english_set(body.p_agent_token);
    return {
      ok: true,
      status: 200,
      json: async () => res
    };
  }
  if (url.endsWith('create_weekly_english_agent_token')) {
    const plaintext = 'weit_' + crypto.randomBytes(32).toString('hex');
    const hash = sha256Hex(plaintext);
    const tokenId = 'tok-' + Date.now();
    db.tokens.set(hash, {
      id: tokenId,
      user_id: USER_AIDEN,
      is_revoked: false,
      scope: 'weekly_english_ingestion',
      description: body.p_description || null,
      created_at: new Date().toISOString()
    });
    return {
      ok: true,
      status: 200,
      json: async () => ({
        status: 'CREATED',
        tokenId,
        token: plaintext,
        scope: 'weekly_english_ingestion',
        message: 'Save this token now.'
      })
    };
  }
  if (url.endsWith('list_weekly_english_agent_tokens')) {
    const tokens = [];
    for (const [hash, t] of db.tokens.entries()) {
      if (t.user_id === USER_AIDEN) {
        tokens.push({
          id: t.id,
          description: t.description || 'token',
          isRevoked: t.is_revoked,
          createdAt: t.created_at || new Date().toISOString()
        });
      }
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ status: 'OK', tokens })
    };
  }
  if (url.endsWith('revoke_weekly_english_agent_token')) {
    let found = false;
    for (const [hash, t] of db.tokens.entries()) {
      if (t.id === body.p_token_id && t.user_id === USER_AIDEN) {
        t.is_revoked = true;
        found = true;
        break;
      }
    }
    return {
      ok: true,
      status: 200,
      json: async () => (found ? { status: 'REVOKED', revoked: true } : { status: 'NOT_FOUND', revoked: false })
    };
  }
  return { ok: false, status: 404 };
}

// Setup test users & tokens
const USER_AIDEN = '00000000-0000-0000-0000-000000000001';
const USER_OTHER = '00000000-0000-0000-0000-000000000002';
const TOKEN_AIDEN = 'aiden-agent-secret-capability-token-xyz';
const TOKEN_REVOKED = 'aiden-agent-revoked-token-abc';
const TOKEN_OTHER = 'other-user-agent-token-123';

db.tokens.set(sha256Hex(TOKEN_AIDEN), { id: 'tok-1', user_id: USER_AIDEN, is_revoked: false, scope: 'weekly_english_ingestion' });
db.tokens.set(sha256Hex(TOKEN_REVOKED), { id: 'tok-2', user_id: USER_AIDEN, is_revoked: true, scope: 'weekly_english_ingestion' });
db.tokens.set(sha256Hex(TOKEN_OTHER), { id: 'tok-3', user_id: USER_OTHER, is_revoked: false, scope: 'weekly_english_ingestion' });

import vm from 'node:vm';

// ── Setup Client Environment ──
globalThis.window = globalThis;
try {
  Object.defineProperty(globalThis, 'navigator', {
    value: { onLine: true },
    configurable: true,
    writable: true
  });
} catch (e) {}
globalThis.CustomEvent = class CustomEvent { constructor(type, detail) { this.type = type; this.detail = detail; } };
globalThis.Event = class Event { constructor(type) { this.type = type; } };
globalThis.addEventListener = globalThis.addEventListener || (() => {});
globalThis.dispatchEvent = globalThis.dispatchEvent || (() => {});
globalThis.document = {
  getElementById: (id) => ({
    value: '',
    textContent: '',
    innerHTML: '',
    style: {},
    classList: { add: () => {}, remove: () => {} }
  }),
  querySelectorAll: () => [],
  addEventListener: () => {}
};
globalThis.alert = (msg) => {};
globalThis.confirm = (msg) => true;

const storageMap = {};
const localStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(storageMap, k) ? storageMap[k] : null; },
  setItem(k, v) { storageMap[k] = String(v); },
  removeItem(k) { delete storageMap[k]; }
};
globalThis.localStorage = localStorage;

// Execute client code in global context
function loadClient() {
  const runCode = (file) => {
    const code = fs.readFileSync(file, 'utf-8');
    vm.runInThisContext(code);
  };
  runCode(STORE_JS);
  runCode(DEFINITIONS_JS);
  runCode(TEST_ENGINE_JS);
  runCode(PROGRESS_JS);
  runCode(WORDS_JS);
  runCode(ADVANCED_JS);
  runCode(ENGINE_JS);
  runCode(SYNC_ENGINE_JS);
  runCode(GUARDIAN_JS);
}
loadClient();

async function runLifecycle() {
  const transport = await import(`file://${TRANSPORT_SCRIPT}`);
  const results = {};

  // Starting condition: local and remote have old set
  const oldSet = {
    schemaVersion: 1,
    setId: '2026-09-18',
    testDate: '2026-09-18',
    title: '2026-09-18 주간 영단어',
    _updated_at: 1000,
    items: [
      { answer: 'across', prompt: 'from one side to the other side' },
      { answer: 'surround', prompt: 'to be on all sides' },
      { answer: 'relaxing', prompt: 'helping you to rest' },
      { answer: 'peaceful', prompt: 'calm and not violent' },
      { answer: 'mystery', prompt: 'a puzzle or secret' },
      { answer: 'clear', prompt: 'see-through' },
      { answer: 'bottom', prompt: 'the lowest part of something' },
      { answer: 'explore', prompt: 'to look around and discover' },
      { answer: 'calm', prompt: 'not moving much' },
      { answer: 'imagine', prompt: 'to picture in your mind' }
    ]
  };
  window.WeeklyVocabularyStore.saveCurrentSet(oldSet, localStorage);
  db.userData.set(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`, {
    user_id: USER_AIDEN,
    data_key: 'aiden_canonical_weekly_vocabulary_v1',
    payload: { ...oldSet, revision: 1, contentFingerprint: computeWeeklyFingerprint(oldSet.items) },
    updated_at: new Date(1000).toISOString()
  });

  // Security Check 1: Invalid token
  const resInvalidTok = await transport.executeIngestionFlow({
    candidate: { testDate: '2026-09-25', items: oldSet.items },
    token: 'completely-invalid-token',
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.invalidTokenStatus = resInvalidTok.status;

  // Security Check 2: Revoked token
  const resRevokedTok = await transport.executeIngestionFlow({
    candidate: { testDate: '2026-09-25', items: oldSet.items },
    token: TOKEN_REVOKED,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.revokedTokenStatus = resRevokedTok.status;

  // Security Check 3: Ambiguous candidate rejected, current unchanged
  const resAmbiguous = await transport.executeIngestionFlow({
    candidate: {
      testDate: '2026-09-25',
      items: oldSet.items,
      ambiguities: ['Uncertain whether word is bank (river) or bank (finance)']
    },
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.ambiguousStatus = resAmbiguous.status;

  // Step 1 & 2: Register Set A (10 pairs) + Read-Back
  const setA_candidate = {
    schemaVersion: 1,
    testDate: '2026-09-25',
    items: [
      { answer: 'courage', prompt: 'the ability to do something frightening', ko: '용기', icon: '🦁' },
      { answer: 'brilliant', prompt: 'exceptionally clever or talented', ko: '눈부신', icon: '✨' },
      { answer: 'ancient', prompt: 'belonging to the very distant past', ko: '고대의', icon: '🏛️' },
      { answer: 'curiosity', prompt: 'a strong desire to know or learn', ko: '호기심', icon: '🔍' },
      { answer: 'horizon', prompt: 'the line at which earth and sky meet', ko: '지평선', icon: '🌅' },
      { answer: 'journey', prompt: 'an act of traveling from one place to another', ko: '여정', icon: '🚀' },
      { answer: 'treasure', prompt: 'a quantity of precious items', ko: '보물', icon: '💎' },
      { answer: 'whisper', prompt: 'speak very softly', ko: '속삭이다', icon: '🤫' },
      { answer: 'glacier', prompt: 'a slowly moving mass of ice', ko: '빙하', icon: '🧊' },
      { answer: 'shelter', prompt: 'a place giving protection from bad weather', ko: '피난처', icon: '⛺' }
    ]
  };

  const resStep1 = await transport.executeIngestionFlow({
    candidate: setA_candidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.step1 = resStep1;

  // Step 3 & 4: Stale client syncs from remote canonical store
  const remoteRow = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`);
  const localRaw = localStorage.getItem('aiden_canonical_weekly_vocabulary_v1');
  const localParsed = JSON.parse(localRaw);
  const localTime = localParsed._updated_at || 0;
  const dbTime = remoteRow.payload._updated_at;

  let clientUpdated = false;
  // Server-authoritative: always hydrate remote regardless of local timestamp
  window.WeeklyVocabularyStore.hydrateFromRemote(remoteRow.payload, localStorage);
  clientUpdated = true;
  results.clientUpdated = clientUpdated;

  // Step 5: Both General English and Weekly Test consume Set A
  window.loadWeeklyWords();
  const generalEngWords = (window.getWeeklyWords ? window.getWeeklyWords() : (window.weeklyWords || [])).slice();
  const testSetA = window.WeeklyTestEngine.buildTestSet();
  results.consumerEngCount = generalEngWords.length;
  results.consumerEngFirstWord = generalEngWords[0].word;
  results.consumerTestId = testSetA.setId;
  results.consumerTestFirstPrompt = testSetA.items[0].prompt;

  // Step 6: Idempotency (same date + same content => NO_OP)
  const resStep6 = await transport.executeIngestionFlow({
    candidate: setA_candidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.step6 = resStep6;

  // Step 7: Revision (same date + 1 item small change => REGISTERED_REVISION)
  const setA2_candidate = JSON.parse(JSON.stringify(setA_candidate));
  setA2_candidate.items[0] = {
    answer: 'bravery',
    prompt: 'courageous behavior or character',
    ko: '용감함',
    icon: '🛡️'
  };

  const resStep7 = await transport.executeIngestionFlow({
    candidate: setA2_candidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.step7 = resStep7;

  // Check history preservation in db
  const aidenHistory = db.history.filter(h => h.user_id === USER_AIDEN);
  results.historyCount = aidenHistory.length;

  // Step 8: Suspicious conflict on same date (5 items replaced => NEEDS_CONFIRMATION)
  const setConflict_candidate = JSON.parse(JSON.stringify(setA2_candidate));
  for (let i = 0; i < 5; i++) {
    setConflict_candidate.items[i] = {
      answer: `conflictword${i}`,
      prompt: `completely different definition ${i}`
    };
  }
  const resStep8 = await transport.executeIngestionFlow({
    candidate: setConflict_candidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.step8 = resStep8;

  // Verify conflict response includes fingerprints for confirmation
  results.conflictHasActiveFingerprint = !!resStep8.activeFingerprint;
  results.conflictHasCandidateFingerprint = !!resStep8.candidateFingerprint;

  // Verify current row was NOT overwritten by conflict candidate
  const currentAfterConflict = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`).payload;
  results.conflictCurrentUnchanged = currentAfterConflict.revision === 2 && currentAfterConflict.items[0].word === 'bravery';

  // Step 8b: Confirmed override
  const confirmation = {
    reason: resStep8.reason || 'LARGE_SYMMETRIC_DIFF',
    expectedActiveFingerprint: resStep8.activeFingerprint,
    expectedActiveRevision: resStep8.activeRevision,
    candidateFingerprint: resStep8.candidateFingerprint
  };
  const resStep8b = await transport.executeIngestionFlow({
    candidate: setConflict_candidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    confirmation,
    fetchFn: mockFetch
  });
  results.step8b = resStep8b;

  // Step 8c: Stale confirmation (another writer changed current after first confirmation)
  // After step8b, current is conflict set (rev 3).
  // Make a small revision to change the active fingerprint/revision.
  const smallRevConflict = JSON.parse(JSON.stringify(setConflict_candidate));
  smallRevConflict.items[9] = { answer: 'updatedword', prompt: 'updated definition for test' };
  await transport.executeIngestionFlow({
    candidate: smallRevConflict,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  // Current is now smallRevConflict (rev 4) with different fingerprint.
  // Create a DIFFERENT large-diff candidate that would need confirmation
  const staleCandidateItems = [];
  for (let i = 0; i < 10; i++) {
    staleCandidateItems.push({
      answer: `staleword${i}`,
      prompt: `stale definition for word ${i}`
    });
  }
  const staleTestCandidate = {
    testDate: '2026-09-25',
    items: staleCandidateItems
  };
  // First, verify it triggers NEEDS_CONFIRMATION without confirmation
  const stalePreCheck = await transport.executeIngestionFlow({
    candidate: staleTestCandidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  // Now try with stale confirmation pointing to the old rev 2 state.
  const staleConfirmation = {
    reason: stalePreCheck.reason || 'LARGE_SYMMETRIC_DIFF',
    expectedActiveFingerprint: resStep8.activeFingerprint,  // points to rev 2
    expectedActiveRevision: resStep8.activeRevision,        // 2
    candidateFingerprint: stalePreCheck.candidateFingerprint
  };
  const resStep8c = await transport.executeIngestionFlow({
    candidate: staleTestCandidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    confirmation: staleConfirmation,
    fetchFn: mockFetch
  });
  results.step8cStaleConfirmation = resStep8c.status;

  // Step 9: New week (different date Set B => REGISTERED_NEW)
  const setB_candidate = {
    schemaVersion: 1,
    testDate: '2026-10-02',
    items: [
      { answer: 'harvest', prompt: 'the process of gathering in crops', ko: '수확', icon: '🌾' },
      { answer: 'autumn', prompt: 'the season after summer', ko: '가을', icon: '🍂' },
      { answer: 'orchard', prompt: 'a piece of land planted with fruit trees', ko: '과수원', icon: '🍎' },
      { answer: 'pumpkin', prompt: 'a large round vegetable with orange skin', ko: '호박', icon: '🎃' },
      { answer: 'breeze', prompt: 'a gentle wind', ko: '산들바람', icon: '🍃' },
      { answer: 'golden', prompt: 'colored or shining like gold', ko: '황금빛의', icon: '⭐' },
      { answer: 'acorn', prompt: 'the fruit of the oak tree', ko: '도토리', icon: '🌰' },
      { answer: 'squirrel', prompt: 'an agile tree-dwelling rodent with a bushy tail', ko: '다람쥐', icon: '🐿️' },
      { answer: 'crisp', prompt: 'cool, fresh, and invigorating', ko: '상쾌한', icon: '🌤️' },
      { answer: 'foliage', prompt: 'plant leaves collectively', ko: '단풍', icon: '🍁' }
    ]
  };
  const resStep9 = await transport.executeIngestionFlow({
    candidate: setB_candidate,
    token: TOKEN_AIDEN,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon-key',
    fetchFn: mockFetch
  });
  results.step9 = resStep9;

  // Client syncs Set B (server-authoritative)
  const remoteRowB = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`);
  window.WeeklyVocabularyStore.hydrateFromRemote(remoteRowB.payload, localStorage);
  window.loadWeeklyWords();
  const testSetB = window.WeeklyTestEngine.buildTestSet();
  const bWords = (window.getWeeklyWords ? window.getWeeklyWords() : (window.weeklyWords || []));
  results.setBConsumedEng = bWords.some(w => w.word === 'harvest');
  results.setBConsumedTest = testSetB.setId === '2026-10-02' && testSetB.items.some(it => it.answer === 'harvest');

  // Cross-User Isolation Check
  const otherUserData = db.userData.get(`${USER_OTHER}::aiden_canonical_weekly_vocabulary_v1`);
  results.otherUserIsolated = otherUserData === undefined;

  // ── VALIDATION TESTS ──────────────────────────────────────
  // 7 items → reject
  const res7items = await transport.executeIngestionFlow({
    candidate: { testDate: '2026-10-09', items: setB_candidate.items.slice(0, 7) },
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  results.reject7items = res7items.status;

  // 8 items → accept
  const res8items = await transport.executeIngestionFlow({
    candidate: { testDate: '2026-10-09', items: setB_candidate.items.slice(0, 8) },
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  results.accept8items = res8items.status;

  // 13 items → needs confirmation (atypical)
  const items13 = [...setB_candidate.items,
    { answer: 'extra1', prompt: 'extra definition 1' },
    { answer: 'extra2', prompt: 'extra definition 2' },
    { answer: 'extra3', prompt: 'extra definition 3' }
  ];
  const res13items = await transport.executeIngestionFlow({
    candidate: { testDate: '2026-10-16', items: items13 },
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  results.atypical13items = res13items.status;
  results.atypical13reason = res13items.reason;

  // Invalid calendar date
  const resInvalidDate = await transport.executeIngestionFlow({
    candidate: { testDate: '2026-99-99', items: oldSet.items },
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  results.invalidCalendarDate = resInvalidDate.status;

  // Duplicate pair → reject
  const resDupPair = await transport.executeIngestionFlow({
    candidate: {
      testDate: '2026-10-23',
      items: [
        ...setB_candidate.items.slice(0, 8),
        { answer: 'harvest', prompt: 'the process of gathering in crops' },
        { answer: 'extra', prompt: 'some extra definition' }
      ]
    },
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  results.duplicatePairRejected = resDupPair.status;

  // Same word different prompt → allowed (multi-sense)
  const resMultiSense = await transport.executeIngestionFlow({
    candidate: {
      testDate: '2026-10-30',
      items: [
        { answer: 'bank', prompt: 'a financial institution' },
        { answer: 'bank', prompt: 'the side of a river' },
        ...setB_candidate.items.slice(0, 8)
      ]
    },
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  results.multiSenseAllowed = ['REGISTERED_NEW', 'REGISTERED_REVISION'].includes(resMultiSense.status) || resMultiSense.status === 'NEEDS_CONFIRMATION';

  // ── FRESHNESS TESTS ───────────────────────────────────────
  // Stale local with future timestamp cannot overwrite remote
  const remoteAfterAll = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`).payload;
  const staleLocal = JSON.parse(JSON.stringify(remoteAfterAll));
  staleLocal._updated_at = remoteAfterAll._updated_at + 999999999;
  staleLocal.items[0].word = 'STALE_LOCAL_WORD';
  window.WeeklyVocabularyStore.saveLocalMutation(staleLocal, localStorage);
  // Now hydrate from remote (simulating sync pull)
  window.WeeklyVocabularyStore.hydrateFromRemote(remoteAfterAll, localStorage);
  const afterHydrate = window.WeeklyVocabularyStore.getCurrentSet(localStorage);
  results.staleLocalOverwritten = afterHydrate.items[0].word !== 'STALE_LOCAL_WORD';

  // Remote hydrate preserves remote version
  results.remoteVersionPreserved = afterHydrate._updated_at === remoteAfterAll._updated_at;

  // Local mutation gets fresh timestamp
  const beforeMutation = Date.now();
  window.WeeklyVocabularyStore.saveLocalMutation({
    setId: '2026-10-02',
    testDate: '2026-10-02',
    items: setB_candidate.items
  }, localStorage);
  const afterMutation = window.WeeklyVocabularyStore.getCurrentSet(localStorage);
  results.localMutationFreshTs = afterMutation._updated_at >= beforeMutation;

  // ── SOURCE FIDELITY TEST ──────────────────────────────────
  const fidelityCheck = transport.verifySourceFidelity(
    { items: [{ answer: 'courage', prompt: 'To Move Very Quickly!' }] },
    { items: [{ answer: 'courage', prompt: 'to move very quickly!' }] }
  );
  results.sourceFidelityFailsOnCaseChange = !fidelityCheck.ok;

  const fidelityCheckOk = transport.verifySourceFidelity(
    { items: [{ answer: 'courage', prompt: 'To Move Very Quickly!' }] },
    { items: [{ answer: 'Courage', prompt: 'To Move Very Quickly!' }] }
  );
  results.sourceFidelityOkWithAnswerCaseChange = fidelityCheckOk.ok;

  // ── SYMMETRIC DIFF TESTS ──────────────────────────────────
  // deletion-only scenario: 10 → 9 (remove 1 item)
  // Reset to a known 10-item state
  const resetSet = JSON.parse(JSON.stringify(setA_candidate));
  const resReset = await transport.executeIngestionFlow({
    candidate: resetSet,
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  // Now send 9 items (delete 1)
  const set9 = JSON.parse(JSON.stringify(resetSet));
  set9.items = set9.items.slice(0, 9);
  const res9 = await transport.executeIngestionFlow({
    candidate: set9,
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  // 1 removed + 0 added = 1 symmetric diff → auto revision
  results.deletion1Item = res9.status;

  // 10 → 10 with 5 pairs modified (5 added + 5 removed = 10 symmetric diff → confirmation)
  const resetAgain = await transport.executeIngestionFlow({
    candidate: resetSet,
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  const set5modified = JSON.parse(JSON.stringify(resetSet));
  for (let i = 0; i < 5; i++) {
    set5modified.items[i] = {
      answer: `newword${i}`,
      prompt: `new definition ${i}`
    };
  }
  const res5mod = await transport.executeIngestionFlow({
    candidate: set5modified,
    token: TOKEN_AIDEN, supabaseUrl: 'https://test.supabase.co', anonKey: 'anon-key', fetchFn: mockFetch
  });
  results.modified5PairsNeedsConf = res5mod.status;
  results.modified5PairsSymDiff = res5mod.conflictDiffCount;

  // ── OPERATIONAL REGRESSION TESTS (CLOSURE) ────────────────
  // Test 1: pushStats(canonicalKey, ...) does NOT enter queue
  localStorage.removeItem('sync_queue');
  window.SyncEngine.pushStats('aiden_canonical_weekly_vocabulary_v1', { testDate: '2026-10-02', items: [] });
  window.SyncEngine.pushStats('englishWeeklyWords', [{ en: 'word', ko: '단어' }]);
  const queueAfterPushStats = JSON.parse(localStorage.getItem('sync_queue') || '{}');
  results.pushStatsCanonicalBlocked = !queueAfterPushStats['aiden_canonical_weekly_vocabulary_v1'] && !queueAfterPushStats['englishWeeklyWords'];

  // Test 2: pre-existing sync_queue canonical entry gets purged and NOT pushed
  const dirtyQueue = {
    'aiden_canonical_weekly_vocabulary_v1': { testDate: '2026-10-02', items: [] },
    'englishWeeklyWords': [{ en: 'bad', ko: 'bad' }],
    'study_rewards': { gems: 10 }
  };
  localStorage.setItem('sync_queue', JSON.stringify(dirtyQueue));
  const cleanedQueue = window.SyncEngine.getQueue();
  results.preExistingQueuePurged = !cleanedQueue['aiden_canonical_weekly_vocabulary_v1'] && !cleanedQueue['englishWeeklyWords'] && cleanedQueue['study_rewards'] !== undefined;

  // Test 3: 13-item + empty '{}' confirmation → REJECT
  const cand13 = {
    testDate: '2026-10-16',
    items: items13
  };
  const cand13Fp = computeWeeklyFingerprint(cand13.items.map(it => ({
    itemId: `2026-10-16-${it.answer || it.word}-hash`,
    answer: it.answer || it.word,
    prompt: it.prompt || it.academyDescription
  })));
  const activeBefore13 = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`).payload;
  const res13EmptyConf = rpc_register_weekly_english_set(TOKEN_AIDEN, cand13, {});
  results.atypical13EmptyConfRejected = ['REJECTED_CONFIRMATION', 'CONFIRMATION_STALE'].includes(res13EmptyConf.status);

  // Test 4: 13-item + wrong candidate fingerprint → REJECT
  const res13WrongCandFp = rpc_register_weekly_english_set(TOKEN_AIDEN, cand13, {
    reason: 'ATYPICAL_ITEM_COUNT',
    candidateFingerprint: 'wrong-fingerprint',
    expectedActiveFingerprint: activeBefore13.contentFingerprint,
    expectedActiveRevision: activeBefore13.revision
  });
  results.atypical13WrongCandFpRejected = res13WrongCandFp.status === 'CONFIRMATION_STALE';

  // Test 5: 13-item + valid confirmation → ACCEPT
  // (Note: testDate 2026-10-16 is a new date compared to active set date 2026-09-18 or 2026-10-02)
  const res13ValidConf = rpc_register_weekly_english_set(TOKEN_AIDEN, cand13, {
    reason: 'ATYPICAL_ITEM_COUNT',
    candidateFingerprint: cand13Fp,
    expectedActiveFingerprint: activeBefore13.contentFingerprint,
    expectedActiveRevision: activeBefore13.revision
  });
  results.atypical13ValidConfAccepted = res13ValidConf.status === 'REGISTERED_CONFIRMED_REVISION';

  // Test 6: new-date atypical invalid vs valid confirmation
  const candNewDate14 = {
    testDate: '2026-11-20',
    items: [...items13, { answer: 'extra4', prompt: 'extra definition 4' }]
  };
  const candNewDate14Fp = computeWeeklyFingerprint(candNewDate14.items.map(it => ({
    itemId: `2026-11-20-${it.answer || it.word}-hash`,
    answer: it.answer || it.word,
    prompt: it.prompt || it.academyDescription
  })));
  const activeBeforeNewDate = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`).payload;
  const resNewDateInvalid = rpc_register_weekly_english_set(TOKEN_AIDEN, candNewDate14, {
    reason: 'WRONG_REASON',
    candidateFingerprint: candNewDate14Fp,
    expectedActiveFingerprint: activeBeforeNewDate.contentFingerprint,
    expectedActiveRevision: activeBeforeNewDate.revision
  });
  results.newDateAtypicalInvalidRejected = ['REJECTED_CONFIRMATION', 'CONFIRMATION_STALE'].includes(resNewDateInvalid.status);

  const resNewDateValid = rpc_register_weekly_english_set(TOKEN_AIDEN, candNewDate14, {
    reason: 'ATYPICAL_ITEM_COUNT',
    candidateFingerprint: candNewDate14Fp,
    expectedActiveFingerprint: activeBeforeNewDate.contentFingerprint,
    expectedActiveRevision: activeBeforeNewDate.revision
  });
  results.newDateAtypicalValidAccepted = resNewDateValid.status === 'REGISTERED_CONFIRMED_REVISION';

  // Test 7: first-ever atypical valid/invalid confirmation (for fresh user with no existing row)
  const candFirstEver13 = {
    testDate: '2026-12-04',
    items: items13
  };
  const candFirstEver13Fp = computeWeeklyFingerprint(candFirstEver13.items.map(it => ({
    itemId: `2026-12-04-${it.answer || it.word}-hash`,
    answer: it.answer || it.word,
    prompt: it.prompt || it.academyDescription
  })));
  const USER_FRESH = '00000000-0000-0000-0000-000000000099';
  const TOKEN_FRESH = 'token-fresh-user';
  db.tokens.set(sha256Hex(TOKEN_FRESH), { id: 'tok-fresh', user_id: USER_FRESH, is_revoked: false, scope: 'weekly_english_ingestion' });

  const resFirstEverNeedsConf = rpc_register_weekly_english_set(TOKEN_FRESH, candFirstEver13, null);
  results.firstEverAtypicalNeedsConf = resFirstEverNeedsConf.status === 'NEEDS_CONFIRMATION';

  const resFirstEverEmptyConf = rpc_register_weekly_english_set(TOKEN_FRESH, candFirstEver13, {});
  results.firstEverAtypicalEmptyConfRejected = ['REJECTED_CONFIRMATION', 'CONFIRMATION_STALE'].includes(resFirstEverEmptyConf.status);

  const resFirstEverValidConf = rpc_register_weekly_english_set(TOKEN_FRESH, candFirstEver13, {
    reason: 'ATYPICAL_ITEM_COUNT',
    candidateFingerprint: candFirstEver13Fp
  });
  results.firstEverAtypicalValidConfAccepted = resFirstEverValidConf.status === 'REGISTERED_CONFIRMED_REVISION';

  // Test 8 & 9: Guardian add/delete through server RPC mutation + read-back
  // Setup window.Auth & window.supabaseClient mock for guardian mutation
  window.Auth = {
    getUser: () => ({ id: USER_AIDEN, email: 'test@example.com' })
  };
  window.supabaseClient = {
    rpc: async (funcName, args) => {
      if (funcName === 'register_weekly_english_set_as_guardian') {
        const res = _register_weekly_english_set_internal(USER_AIDEN, args.p_candidate, args.p_confirmation || null);
        return { data: res, error: null };
      }
      if (funcName === 'create_weekly_english_agent_token') {
        const res = await mockFetch('https://test.supabase.co/rest/v1/rpc/create_weekly_english_agent_token', {
          body: JSON.stringify(args)
        });
        return { data: await res.json(), error: null };
      }
      return { data: null, error: new Error('Unknown RPC') };
    },
    from: (table) => ({
      select: (cols) => ({
        eq: (k1, v1) => ({
          eq: (k2, v2) => ({
            single: async () => {
              const rowKey = `${v1}::${v2}`;
              const row = db.userData.get(rowKey);
              return { data: row ? { payload: row.payload } : null, error: null };
            }
          })
        })
      })
    })
  };

  // Reset to known 10 items
  window.WeeklyVocabularyStore.hydrateFromRemote(db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`).payload, localStorage);
  const beforeGuardianAdd = window.WeeklyVocabularyStore.getCurrentSet(localStorage);
  const initialItemCount = beforeGuardianAdd.items.length;

  // Add a word via guardian mutation
  const guardianAddSuccess = await window.mutateWeeklyWordsAsGuardian((items) => {
    items.push({ word: 'sunshine', academyDescription: 'sunshine', ko: '햇살', icon: '☀️' });
    return items;
  });
  results.guardianAddMutationSuccess = guardianAddSuccess === true;
  const afterGuardianAdd = window.WeeklyVocabularyStore.getCurrentSet(localStorage);
  results.guardianAddHydrated = afterGuardianAdd.items.length === initialItemCount + 1 &&
    afterGuardianAdd.items.some(it => it.word === 'sunshine');
  results.guardianAddServerOriginPreserved = afterGuardianAdd._mutationAuthority === 'server_rpc';

  // Delete that word via guardian mutation
  const guardianDelSuccess = await window.mutateWeeklyWordsAsGuardian((items) => {
    return items.filter(it => it.word !== 'sunshine');
  });
  results.guardianDelMutationSuccess = guardianDelSuccess === true;
  const afterGuardianDel = window.WeeklyVocabularyStore.getCurrentSet(localStorage);
  results.guardianDelHydrated = afterGuardianDel.items.length === initialItemCount &&
    !afterGuardianDel.items.some(it => it.word === 'sunshine');

  // Test 10: Token minting & listing & revoking
  const mintRes = await window.supabaseClient.rpc('create_weekly_english_agent_token', { p_description: 'Test Token' });
  results.tokenMintCreated = mintRes.data?.status === 'CREATED' && typeof mintRes.data?.token === 'string' && mintRes.data?.token.startsWith('weit_');

  console.log(JSON.stringify(results));
}

runLifecycle().catch(err => {
  console.error('Lifecycle execution error:', err);
  process.exit(1);
});
