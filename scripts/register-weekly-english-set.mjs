#!/usr/bin/env node
/**
 * @fileoverview Canonical Reference Transport for Agent Weekly English Ingestion.
 *
 * Contract:
 * - Pure transport-neutral reference client.
 * - Accepts candidate JSON + scoped capability token.
 * - Invokes Supabase RPC register_weekly_english_set.
 * - Supports confirmed override flow (p_confirmation parameter).
 * - Executes read-back via get_current_weekly_english_set.
 * - Verifies both fingerprint/idempotency AND source-fidelity.
 * - Rejects completion if read-back verification fails.
 * - Emits machine-readable JSON completion payload.
 */

import { readFileSync } from 'node:fs';

// ── Constants ────────────────────────────────────────────────
const NORMAL_ITEM_MIN = 8;
const NORMAL_ITEM_MAX = 12;
const ATYPICAL_ITEM_MAX = 15;

export { NORMAL_ITEM_MIN, NORMAL_ITEM_MAX, ATYPICAL_ITEM_MAX };

export function normalizeText(str) {
  return String(str || '').trim().toLowerCase();
}

/**
 * Validate that a testDate string represents an actual calendar date.
 */
export function isValidCalendarDate(dateStr) {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(dateStr)) return false;
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
}

export function validateCandidateShape(candidate) {
  if (!candidate || typeof candidate !== 'object') {
    return { valid: false, error: 'Candidate must be an object' };
  }
  const testDate = String(candidate.testDate || '').trim();
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(testDate)) {
    return { valid: false, error: 'Candidate testDate must be in YYYY-MM-DD format' };
  }
  // Calendar date validation (#9)
  if (!isValidCalendarDate(testDate)) {
    return { valid: false, error: `Candidate testDate ${testDate} is not a valid calendar date` };
  }
  if (Array.isArray(candidate.ambiguities) && candidate.ambiguities.length > 0) {
    return { valid: false, error: 'Candidate contains unresolved ambiguities; cannot ingest automatically' };
  }
  if (!Array.isArray(candidate.items)) {
    return { valid: false, error: 'Candidate items must be an array' };
  }
  // Item count range (#7): hard reject outside 8-15
  if (candidate.items.length < NORMAL_ITEM_MIN || candidate.items.length > ATYPICAL_ITEM_MAX) {
    return {
      valid: false,
      error: `Candidate items count (${candidate.items.length}) is outside allowed bounds (${NORMAL_ITEM_MIN}-${ATYPICAL_ITEM_MAX})`
    };
  }

  // Per-item validation
  const seenPairs = new Set();
  for (let i = 0; i < candidate.items.length; i++) {
    const item = candidate.items[i];
    if (!item || typeof item !== 'object') {
      return { valid: false, error: `Item at index ${i} is invalid` };
    }
    const ans = normalizeText(item.answer || item.word);
    const prompt = normalizeText(item.prompt || item.academyDescription);
    if (!ans || !prompt) {
      return { valid: false, error: `Item at index ${i} is missing answer or prompt` };
    }

    // Duplicate pair detection (#8)
    const pairKey = `${ans}::${prompt}`;
    if (seenPairs.has(pairKey)) {
      return { valid: false, error: `Duplicate (answer, prompt) pair at index ${i}: "${ans}" / "${prompt}"` };
    }
    seenPairs.add(pairKey);
  }
  return { valid: true };
}

/**
 * Normalized fingerprint comparison: for idempotency/dedup purposes.
 * Uses trim + lowercase for both answer and prompt.
 */
export function verifyReadBackMatch(candidate, readBackSet) {
  if (!readBackSet || typeof readBackSet !== 'object') {
    return { ok: false, reason: 'Read-back set is missing or not an object' };
  }
  const candidateDate = String(candidate.testDate || '').trim();
  const remoteDate = String(readBackSet.testDate || readBackSet.setId || '').trim();
  if (candidateDate !== remoteDate) {
    return {
      ok: false,
      reason: `Set identity mismatch: candidate testDate ${candidateDate} vs remote setId ${remoteDate}`
    };
  }

  const candidateItems = candidate.items || [];
  const remoteItems = readBackSet.items || [];
  if (candidateItems.length !== remoteItems.length) {
    return {
      ok: false,
      reason: `Item count mismatch: candidate ${candidateItems.length} vs remote ${remoteItems.length}`
    };
  }

  // Verify that every prompt <-> answer pair in candidate is present in remote (normalized)
  for (const cItem of candidateItems) {
    const cAns = normalizeText(cItem.answer || cItem.word);
    const cPrompt = normalizeText(cItem.prompt || cItem.academyDescription);

    const found = remoteItems.some(rItem => {
      const rAns = normalizeText(rItem.answer || rItem.word);
      const rPrompt = normalizeText(rItem.prompt || rItem.academyDescription);
      return cAns === rAns && cPrompt === rPrompt;
    });

    if (!found) {
      return {
        ok: false,
        reason: `Missing matching pair in remote set for answer="${cAns}", prompt="${cPrompt}"`
      };
    }
  }

  return { ok: true };
}

/**
 * Source fidelity verification (#10):
 * Verifies that the remote set preserves exact original text of prompts.
 * - answer: normalized comparison is acceptable (case-insensitive)
 * - prompt: exact text must be preserved (capitalization, punctuation)
 */
export function verifySourceFidelity(candidate, readBackSet) {
  if (!readBackSet || typeof readBackSet !== 'object') {
    return { ok: false, reason: 'Read-back set is missing or not an object' };
  }

  const candidateItems = candidate.items || [];
  const remoteItems = readBackSet.items || [];

  for (const cItem of candidateItems) {
    const cAns = normalizeText(cItem.answer || cItem.word);
    const cPromptRaw = String(cItem.prompt || cItem.academyDescription || '').trim();

    const found = remoteItems.some(rItem => {
      const rAns = normalizeText(rItem.answer || rItem.word);
      const rPromptRaw = String(rItem.prompt || rItem.academyDescription || '').trim();
      // Answer: normalized match. Prompt: exact text match.
      return cAns === rAns && cPromptRaw === rPromptRaw;
    });

    if (!found) {
      return {
        ok: false,
        reason: `Source fidelity violation for answer="${cAns}": prompt text not exactly preserved`
      };
    }
  }

  return { ok: true };
}

export async function executeIngestionFlow({
  candidate,
  token,
  supabaseUrl,
  anonKey,
  confirmation = null,
  fetchFn = globalThis.fetch
}) {
  if (!token || typeof token !== 'string' || !token.trim()) {
    return {
      status: 'UNAUTHORIZED',
      message: 'Scoped agent token is required'
    };
  }

  const shapeCheck = validateCandidateShape(candidate);
  if (!shapeCheck.valid) {
    return {
      status: 'REJECTED_INVALID',
      message: shapeCheck.error
    };
  }

  const cleanUrl = String(supabaseUrl || '').replace(/\/$/, '');
  const rpcRegisterUrl = `${cleanUrl}/rest/v1/rpc/register_weekly_english_set`;
  const rpcReadBackUrl = `${cleanUrl}/rest/v1/rpc/get_current_weekly_english_set`;

  const headers = {
    'apikey': anonKey,
    'Authorization': `Bearer ${anonKey}`,
    'Content-Type': 'application/json'
  };

  // 1. Invoke Register RPC (with optional confirmation)
  let regRes;
  try {
    const rpcBody = {
      p_agent_token: token.trim(),
      p_candidate: candidate
    };
    if (confirmation) {
      rpcBody.p_confirmation = confirmation;
    }

    const res = await fetchFn(rpcRegisterUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(rpcBody)
    });
    if (!res.ok) {
      const errText = await res.text();
      return {
        status: res.status === 401 ? 'UNAUTHORIZED' : 'ERROR',
        httpStatus: res.status,
        message: errText
      };
    }
    regRes = await res.json();
  } catch (err) {
    return {
      status: 'NETWORK_ERROR',
      message: err.message
    };
  }

  const allowedStatuses = [
    'REGISTERED_NEW', 'REGISTERED_REVISION', 'REGISTERED_CONFIRMED_REVISION',
    'NO_OP', 'NEEDS_CONFIRMATION', 'CONFIRMATION_STALE', 'REJECTED_CONFIRMATION',
    'REJECTED_INVALID', 'UNAUTHORIZED'
  ];
  if (!regRes || !allowedStatuses.includes(regRes.status)) {
    return {
      status: 'UNEXPECTED_RESPONSE',
      raw: regRes
    };
  }

  // If requires confirmation, stale, invalid or unauthorized, return immediately
  if (['NEEDS_CONFIRMATION', 'CONFIRMATION_STALE', 'REJECTED_CONFIRMATION', 'REJECTED_INVALID', 'UNAUTHORIZED'].includes(regRes.status)) {
    return regRes;
  }

  // 2. Perform Read-Back Verification for Successful Registrations
  let readBackSet;
  try {
    const rbRes = await fetchFn(rpcReadBackUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        p_agent_token: token.trim()
      })
    });
    if (!rbRes.ok) {
      const rbErr = await rbRes.text();
      return {
        status: 'READ_BACK_FAILED',
        httpStatus: rbRes.status,
        message: `Failed to read-back after registration: ${rbErr}`
      };
    }
    const rbJson = await rbRes.json();
    if (!rbJson || rbJson.status !== 'OK' || !rbJson.currentSet) {
      return {
        status: 'READ_BACK_FAILED',
        message: `Invalid read-back response structure: ${JSON.stringify(rbJson)}`
      };
    }
    readBackSet = rbJson.currentSet;
  } catch (err) {
    return {
      status: 'READ_BACK_NETWORK_ERROR',
      message: err.message
    };
  }

  // 3. Fingerprint/idempotency verification (normalized)
  const verification = verifyReadBackMatch(candidate, readBackSet);
  if (!verification.ok) {
    return {
      status: 'READ_BACK_VERIFICATION_FAILED',
      reason: verification.reason,
      candidateSetId: candidate.testDate,
      readBackSet
    };
  }

  // 4. Source fidelity verification (exact prompt text)
  const fidelityCheck = verifySourceFidelity(candidate, readBackSet);

  return {
    status: regRes.status,
    setId: regRes.setId,
    testDate: regRes.testDate || regRes.setId,
    revision: regRes.revision,
    itemCount: regRes.itemCount,
    contentFingerprint: regRes.contentFingerprint,
    updatedAt: regRes.updatedAt,
    readBackVerified: true,
    sourceFidelityVerified: fidelityCheck.ok,
    sourceFidelityReason: fidelityCheck.ok ? undefined : fidelityCheck.reason
  };
}

// ── CLI Handler ──────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  let candidatePath = null;
  let token = process.env.WEEKLY_AGENT_TOKEN || null;
  let supabaseUrl = process.env.SUPABASE_URL || null;
  let anonKey = process.env.SUPABASE_ANON_KEY || null;
  let confirmationPath = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--candidate' && args[i + 1]) {
      candidatePath = args[++i];
    } else if (args[i] === '--token' && args[i + 1]) {
      token = args[++i];
    } else if (args[i] === '--url' && args[i + 1]) {
      supabaseUrl = args[++i];
    } else if (args[i] === '--key' && args[i + 1]) {
      anonKey = args[++i];
    } else if (args[i] === '--confirmation' && args[i + 1]) {
      confirmationPath = args[++i];
    }
  }

  if (!candidatePath) {
    console.error('Usage: node scripts/register-weekly-english-set.mjs --candidate <file.json> [--token <tok>] [--url <url>] [--key <key>] [--confirmation <file.json>]');
    process.exit(1);
  }

  let candidate;
  try {
    const raw = readFileSync(candidatePath, 'utf-8');
    candidate = JSON.parse(raw);
  } catch (err) {
    console.error(`Failed to read candidate JSON from ${candidatePath}:`, err.message);
    process.exit(1);
  }

  let confirmation = null;
  if (confirmationPath) {
    try {
      const raw = readFileSync(confirmationPath, 'utf-8');
      confirmation = JSON.parse(raw);
    } catch (err) {
      console.error(`Failed to read confirmation JSON from ${confirmationPath}:`, err.message);
      process.exit(1);
    }
  }

  const result = await executeIngestionFlow({
    candidate,
    token,
    supabaseUrl,
    anonKey,
    confirmation
  });

  console.log(JSON.stringify(result, null, 2));

  if (['REGISTERED_NEW', 'REGISTERED_REVISION', 'REGISTERED_CONFIRMED_REVISION', 'NO_OP'].includes(result.status) && result.readBackVerified) {
    process.exit(0);
  } else {
    process.exit(2);
  }
}

if (process.argv[1] && process.argv[1].endsWith('register-weekly-english-set.mjs')) {
  main().catch(err => {
    console.error('Fatal execution error:', err);
    process.exit(1);
  });
}
