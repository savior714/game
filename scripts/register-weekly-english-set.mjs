#!/usr/bin/env node
/**
 * @fileoverview Canonical Reference Transport for Agent Weekly English Ingestion.
 *
 * Contract:
 * - Pure transport-neutral reference client.
 * - Accepts candidate JSON + scoped capability token.
 * - Invokes Supabase RPC register_weekly_english_set.
 * - Executes read-back via get_current_weekly_english_set.
 * - Verifies exact identity, item count, and prompt<->answer semantic equivalence.
 * - Rejects completion if read-back verification fails.
 * - Emits machine-readable JSON completion payload.
 */

import { readFileSync } from 'node:fs';

export function normalizeText(str) {
  return String(str || '').trim().toLowerCase();
}

export function validateCandidateShape(candidate) {
  if (!candidate || typeof candidate !== 'object') {
    return { valid: false, error: 'Candidate must be an object' };
  }
  const testDate = String(candidate.testDate || '').trim();
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(testDate)) {
    return { valid: false, error: 'Candidate testDate must be in YYYY-MM-DD format' };
  }
  if (Array.isArray(candidate.ambiguities) && candidate.ambiguities.length > 0) {
    return { valid: false, error: 'Candidate contains unresolved ambiguities; cannot ingest automatically' };
  }
  if (!Array.isArray(candidate.items)) {
    return { valid: false, error: 'Candidate items must be an array' };
  }
  if (candidate.items.length < 8 || candidate.items.length > 15) {
    return {
      valid: false,
      error: `Candidate items count (${candidate.items.length}) is outside expected weekly range (8-15)`
    };
  }
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
  }
  return { valid: true };
}

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

  // Verify that every prompt <-> answer pair in candidate is present in remote
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

export async function executeIngestionFlow({
  candidate,
  token,
  supabaseUrl,
  anonKey,
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

  // 1. Invoke Register RPC
  let regRes;
  try {
    const res = await fetchFn(rpcRegisterUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        p_agent_token: token.trim(),
        p_candidate: candidate
      })
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

  const allowedStatuses = ['REGISTERED_NEW', 'REGISTERED_REVISION', 'NO_OP', 'NEEDS_CONFIRMATION', 'REJECTED_INVALID', 'UNAUTHORIZED'];
  if (!regRes || !allowedStatuses.includes(regRes.status)) {
    return {
      status: 'UNEXPECTED_RESPONSE',
      raw: regRes
    };
  }

  // If requires confirmation or invalid or unauthorized, return immediately
  if (['NEEDS_CONFIRMATION', 'REJECTED_INVALID', 'UNAUTHORIZED'].includes(regRes.status)) {
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

  // 3. Strict Equality & Semantic Check
  const verification = verifyReadBackMatch(candidate, readBackSet);
  if (!verification.ok) {
    return {
      status: 'READ_BACK_VERIFICATION_FAILED',
      reason: verification.reason,
      candidateSetId: candidate.testDate,
      readBackSet
    };
  }

  return {
    status: regRes.status,
    setId: regRes.setId,
    testDate: regRes.testDate || regRes.setId,
    revision: regRes.revision,
    itemCount: regRes.itemCount,
    contentFingerprint: regRes.contentFingerprint,
    updatedAt: regRes.updatedAt,
    readBackVerified: true
  };
}

// ── CLI Handler ──────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  let candidatePath = null;
  let token = process.env.WEEKLY_AGENT_TOKEN || null;
  let supabaseUrl = process.env.SUPABASE_URL || null;
  let anonKey = process.env.SUPABASE_ANON_KEY || null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--candidate' && args[i + 1]) {
      candidatePath = args[++i];
    } else if (args[i] === '--token' && args[i + 1]) {
      token = args[++i];
    } else if (args[i] === '--url' && args[i + 1]) {
      supabaseUrl = args[++i];
    } else if (args[i] === '--key' && args[i + 1]) {
      anonKey = args[++i];
    }
  }

  if (!candidatePath) {
    console.error('Usage: node scripts/register-weekly-english-set.mjs --candidate <file.json> [--token <tok>] [--url <url>] [--key <key>]');
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

  const result = await executeIngestionFlow({
    candidate,
    token,
    supabaseUrl,
    anonKey
  });

  console.log(JSON.stringify(result, null, 2));

  if (['REGISTERED_NEW', 'REGISTERED_REVISION', 'NO_OP'].includes(result.status) && result.readBackVerified) {
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
