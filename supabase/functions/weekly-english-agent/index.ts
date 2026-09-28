/**
 * @fileoverview Supabase Edge Function: weekly-english-agent
 *
 * Shared transport facade for agent weekly English ingestion (ChatGPT & Antigravity).
 *
 * Contract:
 * - Accepts scoped capability token via dedicated secret header (X-Aiden-Weekly-Token).
 * - Delegates all business semantics & auth authority to PostgreSQL RPCs.
 * - Uses ONLY anon/publishable credentials for PostgREST invocation (NEVER service-role).
 * - Executes post-registration read-back and source-fidelity verification.
 * - Masks credentials; NEVER reflects tokens in responses, errors, or logs.
 */

// ── Constants ────────────────────────────────────────────────
const NORMAL_ITEM_MIN = 8;
const NORMAL_ITEM_MAX = 12;
const ATYPICAL_ITEM_MAX = 15;

const DEFAULT_SUPABASE_URL = 'https://rxjefpmvlygunrukccgg.supabase.co';
const DEFAULT_ANON_KEY = 'sb_publishable_86T5zbV_IUXZDvQig6mofg_tlHYeHVx';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-aiden-weekly-token',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
};

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...CORS_HEADERS,
      'Content-Type': 'application/json'
    }
  });
}

function normalizeText(str: unknown): string {
  return String(str || '').trim().toLowerCase();
}

function isValidCalendarDate(dateStr: string): boolean {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(dateStr)) return false;
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
}

export function validateCandidateShape(candidate: any): { valid: boolean; error?: string } {
  if (!candidate || typeof candidate !== 'object') {
    return { valid: false, error: 'Candidate must be an object' };
  }
  const testDate = String(candidate.testDate || '').trim();
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(testDate)) {
    return { valid: false, error: 'Candidate testDate must be in YYYY-MM-DD format' };
  }
  if (!isValidCalendarDate(testDate)) {
    return { valid: false, error: `Candidate testDate ${testDate} is not a valid calendar date` };
  }
  if (Array.isArray(candidate.ambiguities) && candidate.ambiguities.length > 0) {
    return { valid: false, error: 'Candidate contains unresolved ambiguities; cannot ingest automatically' };
  }
  if (!Array.isArray(candidate.items)) {
    return { valid: false, error: 'Candidate items must be an array' };
  }
  if (candidate.items.length < NORMAL_ITEM_MIN || candidate.items.length > ATYPICAL_ITEM_MAX) {
    return {
      valid: false,
      error: `Candidate items count (${candidate.items.length}) is outside allowed bounds (${NORMAL_ITEM_MIN}-${ATYPICAL_ITEM_MAX})`
    };
  }

  const seenPairs = new Set<string>();
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
    const pairKey = `${ans}::${prompt}`;
    if (seenPairs.has(pairKey)) {
      return { valid: false, error: `Duplicate (answer, prompt) pair at index ${i}: "${ans}" / "${prompt}"` };
    }
    seenPairs.add(pairKey);
  }
  return { valid: true };
}

export function verifyReadBackMatch(candidate: any, readBackSet: any): { ok: boolean; reason?: string } {
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

  for (const cItem of candidateItems) {
    const cAns = normalizeText(cItem.answer || cItem.word);
    const cPrompt = normalizeText(cItem.prompt || cItem.academyDescription);

    const found = remoteItems.some((rItem: any) => {
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

export function verifySourceFidelity(candidate: any, readBackSet: any): { ok: boolean; reason?: string } {
  if (!readBackSet || typeof readBackSet !== 'object') {
    return { ok: false, reason: 'Read-back set is missing or not an object' };
  }

  const candidateItems = candidate.items || [];
  const remoteItems = readBackSet.items || [];

  for (const cItem of candidateItems) {
    const cAns = normalizeText(cItem.answer || cItem.word);
    const cPromptRaw = String(cItem.prompt || cItem.academyDescription || '').trim();

    const found = remoteItems.some((rItem: any) => {
      const rAns = normalizeText(rItem.answer || rItem.word);
      const rPromptRaw = String(rItem.prompt || rItem.academyDescription || '').trim();
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

function extractToken(req: Request): string | null {
  const customHeader = req.headers.get('x-aiden-weekly-token') || req.headers.get('X-Aiden-Weekly-Token');
  if (customHeader && customHeader.trim()) {
    return customHeader.trim();
  }
  const authHeader = req.headers.get('authorization') || req.headers.get('Authorization');
  if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
    const tok = authHeader.slice(7).trim();
    if (tok.startsWith('weit_')) {
      return tok;
    }
  }
  return null;
}

export async function handleRequest(req: Request, envFetcher?: (key: string) => string | undefined): Promise<Response> {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: CORS_HEADERS });
  }

  const getEnv = envFetcher || ((k: string) => (globalThis as any).Deno?.env?.get(k) || process?.env?.[k]);
  const supabaseUrl = (getEnv('SUPABASE_URL') || DEFAULT_SUPABASE_URL).replace(/\/$/, '');
  const anonKey = getEnv('SUPABASE_ANON_KEY') || DEFAULT_ANON_KEY;

  const token = extractToken(req);
  if (!token) {
    return jsonResponse({
      status: 'UNAUTHORIZED',
      message: 'Scoped agent token is required via X-Aiden-Weekly-Token header'
    }, 401);
  }

  const url = new URL(req.url);
  const pathname = url.pathname.replace(/\/$/, '');

  // Dispatch operations:
  // 1. /current or GET request -> getCurrentWeeklyEnglishSet
  // 2. /register or POST request with candidate -> registerWeeklyEnglishCandidate
  const isCurrentReq = pathname.endsWith('/current') || (req.method === 'GET' && !pathname.endsWith('/register'));
  const isRegisterReq = pathname.endsWith('/register') || req.method === 'POST';

  const rpcHeaders = {
    'apikey': anonKey,
    'Authorization': `Bearer ${anonKey}`,
    'Content-Type': 'application/json'
  };

  if (isCurrentReq) {
    try {
      const res = await fetch(`${supabaseUrl}/rest/v1/rpc/get_current_weekly_english_set`, {
        method: 'POST',
        headers: rpcHeaders,
        body: JSON.stringify({ p_agent_token: token })
      });
      if (!res.ok) {
        const errText = await res.text();
        return jsonResponse({
          status: res.status === 401 ? 'UNAUTHORIZED' : 'ERROR',
          httpStatus: res.status,
          message: errText
        }, res.status);
      }
      const data = await res.json();
      return jsonResponse(data, 200);
    } catch (err: any) {
      return jsonResponse({ status: 'NETWORK_ERROR', message: err.message }, 500);
    }
  }

  if (isRegisterReq) {
    let body: any;
    try {
      body = await req.json();
    } catch {
      return jsonResponse({ status: 'REJECTED_INVALID', message: 'Malformed JSON body' }, 400);
    }

    const candidate = body.candidate || body;
    const confirmation = body.confirmation || null;

    const shapeCheck = validateCandidateShape(candidate);
    if (!shapeCheck.valid) {
      return jsonResponse({ status: 'REJECTED_INVALID', message: shapeCheck.error }, 400);
    }

    // 1. Invoke Register RPC
    let regRes: any;
    try {
      const rpcBody: any = {
        p_agent_token: token,
        p_candidate: candidate
      };
      if (confirmation) {
        rpcBody.p_confirmation = confirmation;
      }
      const res = await fetch(`${supabaseUrl}/rest/v1/rpc/register_weekly_english_set`, {
        method: 'POST',
        headers: rpcHeaders,
        body: JSON.stringify(rpcBody)
      });
      if (!res.ok) {
        const errText = await res.text();
        return jsonResponse({
          status: res.status === 401 ? 'UNAUTHORIZED' : 'ERROR',
          httpStatus: res.status,
          message: errText
        }, res.status);
      }
      regRes = await res.json();
    } catch (err: any) {
      return jsonResponse({ status: 'NETWORK_ERROR', message: err.message }, 500);
    }

    // Immediate return for confirmation/auth/invalid flows
    if (['NEEDS_CONFIRMATION', 'CONFIRMATION_STALE', 'REJECTED_CONFIRMATION', 'REJECTED_INVALID', 'UNAUTHORIZED'].includes(regRes?.status)) {
      return jsonResponse(regRes, 200);
    }

    // 2. Perform Read-Back Verification
    let readBackSet: any;
    try {
      const rbRes = await fetch(`${supabaseUrl}/rest/v1/rpc/get_current_weekly_english_set`, {
        method: 'POST',
        headers: rpcHeaders,
        body: JSON.stringify({ p_agent_token: token })
      });
      if (!rbRes.ok) {
        const rbErr = await rbRes.text();
        return jsonResponse({
          status: 'READ_BACK_FAILED',
          httpStatus: rbRes.status,
          message: `Failed to read-back after registration: ${rbErr}`
        }, 500);
      }
      const rbJson = await rbRes.json();
      if (!rbJson || rbJson.status !== 'OK' || !rbJson.currentSet) {
        return jsonResponse({
          status: 'READ_BACK_FAILED',
          message: `Invalid read-back response structure: ${JSON.stringify(rbJson)}`
        }, 500);
      }
      readBackSet = rbJson.currentSet;
    } catch (err: any) {
      return jsonResponse({ status: 'READ_BACK_NETWORK_ERROR', message: err.message }, 500);
    }

    // 3. Normalized Match Verification
    const verification = verifyReadBackMatch(candidate, readBackSet);
    if (!verification.ok) {
      return jsonResponse({
        status: 'READ_BACK_VERIFICATION_FAILED',
        reason: verification.reason,
        candidateSetId: candidate.testDate,
        readBackSet
      }, 422);
    }

    // 4. Source Fidelity Verification
    const fidelityCheck = verifySourceFidelity(candidate, readBackSet);
    if (!fidelityCheck.ok) {
      return jsonResponse({
        status: 'SOURCE_FIDELITY_VERIFICATION_FAILED',
        reason: fidelityCheck.reason,
        setId: regRes.setId,
        testDate: regRes.testDate || regRes.setId,
        revision: regRes.revision,
        readBackVerified: true,
        sourceFidelityVerified: false,
        sourceFidelityReason: fidelityCheck.reason,
        readBackSet
      }, 422);
    }

    return jsonResponse({
      status: regRes.status,
      setId: regRes.setId,
      testDate: regRes.testDate || regRes.setId,
      revision: regRes.revision,
      itemCount: regRes.itemCount,
      contentFingerprint: regRes.contentFingerprint,
      updatedAt: regRes.updatedAt,
      readBackVerified: true,
      sourceFidelityVerified: true
    }, 200);
  }

  return jsonResponse({ status: 'NOT_FOUND', message: `Unrecognized path: ${pathname}` }, 404);
}

// Default Deno serve entrypoint
if (typeof (globalThis as any).Deno !== 'undefined') {
  (globalThis as any).Deno.serve(handleRequest);
}
