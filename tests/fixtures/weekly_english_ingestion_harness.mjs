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
const TRANSPORT_SCRIPT = path.join(ROOT, 'scripts/register-weekly-english-set.mjs');

// ── In-Memory Postgres DB Mock simulating 003 migration exactly ──
const db = {
  tokens: new Map(), // token_hash -> { id, user_id, is_revoked, expires_at }
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

// Mock PostgreSQL register_weekly_english_set RPC
function rpc_register_weekly_english_set(agent_token, candidate) {
  if (!agent_token || !agent_token.trim()) {
    return { status: 'UNAUTHORIZED', message: 'Agent token is required' };
  }
  const hash = sha256Hex(agent_token.trim());
  const tokenRec = db.tokens.get(hash);
  if (!tokenRec || tokenRec.is_revoked || (tokenRec.expires_at && tokenRec.expires_at <= Date.now())) {
    return { status: 'UNAUTHORIZED', message: 'Invalid or revoked token' };
  }
  const userId = tokenRec.user_id;

  if (!candidate || typeof candidate !== 'object') {
    return { status: 'REJECTED_INVALID', message: 'Candidate must be an object' };
  }
  const testDate = String(candidate.testDate || '').trim();
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(testDate)) {
    return { status: 'REJECTED_INVALID', message: 'Candidate testDate must match YYYY-MM-DD' };
  }
  if (Array.isArray(candidate.ambiguities) && candidate.ambiguities.length > 0) {
    return { status: 'REJECTED_INVALID', message: 'Unresolved ambiguities present' };
  }
  const items = candidate.items;
  if (!Array.isArray(items) || items.length < 8 || items.length > 15) {
    return { status: 'REJECTED_INVALID', message: 'Candidate items out of standard bounds (8-15)' };
  }

  const canonicalItems = [];
  const legacyItems = [];
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

      // Diff count
      const oldPairs = new Set((existing.items || []).map(it => `${it.answer}::${it.prompt}`.toLowerCase()));
      let diffCount = 0;
      for (const it of canonicalItems) {
        if (!oldPairs.has(`${it.answer}::${it.prompt}`.toLowerCase())) {
          diffCount++;
        }
      }

      if (diffCount > 3) {
        return {
          status: 'NEEDS_CONFIRMATION',
          message: 'Large conflict on same test date',
          activeSetId: existingDate,
          activeRevision: existingRev,
          conflictDiffCount: diffCount
        };
      }

      status = 'REGISTERED_REVISION';
      newRev = existingRev + 1;
    } else {
      status = 'REGISTERED_NEW';
      newRev = 1;
    }

    // Rollback preservation: save old current to history
    db.history.push({
      user_id: userId,
      set_id: existingDate,
      revision: existingRev,
      payload: existing,
      is_current: false
    });
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
    registeredAt: nowIso
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
  const body = JSON.parse(options.body);
  if (url.endsWith('register_weekly_english_set')) {
    const res = rpc_register_weekly_english_set(body.p_agent_token, body.p_candidate);
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
  return { ok: false, status: 404 };
}

// Setup test users & tokens
const USER_AIDEN = '00000000-0000-0000-0000-000000000001';
const USER_OTHER = '00000000-0000-0000-0000-000000000002';
const TOKEN_AIDEN = 'aiden-agent-secret-capability-token-xyz';
const TOKEN_REVOKED = 'aiden-agent-revoked-token-abc';
const TOKEN_OTHER = 'other-user-agent-token-123';

db.tokens.set(sha256Hex(TOKEN_AIDEN), { id: 'tok-1', user_id: USER_AIDEN, is_revoked: false });
db.tokens.set(sha256Hex(TOKEN_REVOKED), { id: 'tok-2', user_id: USER_AIDEN, is_revoked: true });
db.tokens.set(sha256Hex(TOKEN_OTHER), { id: 'tok-3', user_id: USER_OTHER, is_revoked: false });

import vm from 'node:vm';

// ── Setup Client Environment ──
globalThis.window = globalThis;
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
  if (dbTime > localTime) {
    localStorage.setItem('aiden_canonical_weekly_vocabulary_v1', JSON.stringify(remoteRow.payload));
    const legacyProj = remoteRow.payload.items.map(it => ({ en: it.word, ko: it.ko, icon: it.icon }));
    localStorage.setItem('englishWeeklyWords', JSON.stringify(legacyProj));
    clientUpdated = true;
  }
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
  const setConflict_candidate = JSON.parse(JSON.stringify(setA_candidate));
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

  // Verify current row was NOT overwritten by conflict candidate
  const currentAfterConflict = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`).payload;
  results.conflictCurrentUnchanged = currentAfterConflict.revision === 2 && currentAfterConflict.items[0].word === 'bravery';

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

  // Client syncs Set B
  const remoteRowB = db.userData.get(`${USER_AIDEN}::aiden_canonical_weekly_vocabulary_v1`);
  localStorage.setItem('aiden_canonical_weekly_vocabulary_v1', JSON.stringify(remoteRowB.payload));
  window.loadWeeklyWords();
  const testSetB = window.WeeklyTestEngine.buildTestSet();
  const bWords = (window.getWeeklyWords ? window.getWeeklyWords() : (window.weeklyWords || []));
  results.setBConsumedEng = bWords.some(w => w.word === 'harvest');
  results.setBConsumedTest = testSetB.setId === '2026-10-02' && testSetB.items.some(it => it.answer === 'harvest');

  // Cross-User Isolation Check
  const otherUserData = db.userData.get(`${USER_OTHER}::aiden_canonical_weekly_vocabulary_v1`);
  results.otherUserIsolated = otherUserData === undefined;

  console.log(JSON.stringify(results));
}

runLifecycle().catch(err => {
  console.error('Lifecycle execution error:', err);
  process.exit(1);
});
