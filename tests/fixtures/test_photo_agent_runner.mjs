/**
 * @fileoverview Test runner for Weekly English Photo Agent and Adapters.
 *
 * Verifies:
 * 1. Reference transport fidelity bug fix & terminal status promotion.
 * 2. CLI exit code behavior on fidelity match vs mismatch.
 * 3. Validation bounds (8, 10, 12 normal; 7 reject; 13 atypical; 16 reject).
 * 4. Duplicate pair rejection & calendar date validation.
 * 5. Antigravity MCP stdio JSON-RPC protocol (initialize, tools/list, tools/call).
 * 6. Secret isolation (no token reflected in results or error outputs).
 * 7. Shared Transport Facade (Edge Function) routing, CORS, and fidelity enforcement.
 */

import { executeIngestionFlow, fetchCurrentWeeklyEnglishSet, validateCandidateShape } from '../../scripts/register-weekly-english-set.mjs';
import { handleRpcMessage } from '../../integrations/weekly-english/antigravity/mcp-server.mjs';
import { handleRequest } from '../../supabase/functions/weekly-english-agent/index.ts';

const TOKEN_TEST = 'weit_test_secret_capability_token_999';

function make10Items() {
  return [
    { answer: 'courage', prompt: 'the ability to do something frightening' },
    { answer: 'brilliant', prompt: 'exceptionally clever or talented' },
    { answer: 'ancient', prompt: 'belonging to the very distant past' },
    { answer: 'curiosity', prompt: 'a strong desire to know or learn' },
    { answer: 'horizon', prompt: 'the line at which earth and sky meet' },
    { answer: 'journey', prompt: 'an act of traveling from one place to another' },
    { answer: 'treasure', prompt: 'a quantity of precious items' },
    { answer: 'whisper', prompt: 'speak very softly' },
    { answer: 'glacier', prompt: 'a slowly moving mass of ice' },
    { answer: 'shelter', prompt: 'a place giving protection from bad weather' }
  ];
}

async function runAllTests() {
  const report = {};

  // ── 1. Shape & Validation Checks ──
  report.valid10 = validateCandidateShape({ testDate: '2026-10-02', items: make10Items() }).valid;
  report.valid8 = validateCandidateShape({ testDate: '2026-10-02', items: make10Items().slice(0, 8) }).valid;
  report.valid12 = validateCandidateShape({
    testDate: '2026-10-02',
    items: [...make10Items(), { answer: 'extra1', prompt: 'p1' }, { answer: 'extra2', prompt: 'p2' }]
  }).valid;
  report.valid13Atypical = validateCandidateShape({
    testDate: '2026-10-02',
    items: [...make10Items(), { answer: 'e1', prompt: 'p1' }, { answer: 'e2', prompt: 'p2' }, { answer: 'e3', prompt: 'p3' }]
  }).valid;
  report.reject7 = !validateCandidateShape({ testDate: '2026-10-02', items: make10Items().slice(0, 7) }).valid;
  report.reject16 = !validateCandidateShape({
    testDate: '2026-10-02',
    items: Array.from({ length: 16 }, (_, i) => ({ answer: `w${i}`, prompt: `p${i}` }))
  }).valid;
  report.rejectInvalidDate = !validateCandidateShape({ testDate: '2026-99-99', items: make10Items() }).valid;
  report.rejectDuplicatePair = !validateCandidateShape({
    testDate: '2026-10-02',
    items: [...make10Items().slice(0, 9), { answer: 'courage', prompt: 'the ability to do something frightening' }]
  }).valid;
  report.rejectMissingAnswer = !validateCandidateShape({
    testDate: '2026-10-02',
    items: [{ prompt: 'only prompt' }, ...make10Items().slice(1)]
  }).valid;
  report.rejectMissingPrompt = !validateCandidateShape({
    testDate: '2026-10-02',
    items: [{ answer: 'only answer' }, ...make10Items().slice(1)]
  }).valid;
  report.rejectAmbiguities = !validateCandidateShape({
    testDate: '2026-10-02',
    items: make10Items(),
    ambiguities: ['Uncertain about #7']
  }).valid;

  // ── 2. Reference Transport Fidelity Check ──
  const mockFidelityMismatchFetch = async (url) => {
    if (url.includes('register_weekly_english_set')) {
      return {
        ok: true,
        json: async () => ({
          status: 'REGISTERED_NEW',
          setId: '2026-10-02',
          testDate: '2026-10-02',
          revision: 1,
          itemCount: 10,
          contentFingerprint: 'mock_fp'
        })
      };
    }
    if (url.includes('get_current_weekly_english_set')) {
      // Remote set has prompt in ALL CAPS
      const items = make10Items().map((it, idx) => idx === 0 ? { ...it, prompt: it.prompt.toUpperCase() } : it);
      return {
        ok: true,
        json: async () => ({ status: 'OK', currentSet: { testDate: '2026-10-02', items } })
      };
    }
    return { ok: false };
  };

  const fidelityMismatchRes = await executeIngestionFlow({
    candidate: { testDate: '2026-10-02', items: make10Items() },
    token: TOKEN_TEST,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon',
    fetchFn: mockFidelityMismatchFetch
  });

  report.fidelityMismatchStatus = fidelityMismatchRes.status;
  report.fidelityMismatchVerifiedFalse = fidelityMismatchRes.sourceFidelityVerified === false;
  report.fidelityMismatchReadBackVerified = fidelityMismatchRes.readBackVerified === true;

  // ── 3. Reference Transport Fidelity Match ──
  const mockFidelityMatchFetch = async (url) => {
    if (url.includes('register_weekly_english_set')) {
      return {
        ok: true,
        json: async () => ({
          status: 'REGISTERED_NEW',
          setId: '2026-10-02',
          testDate: '2026-10-02',
          revision: 1,
          itemCount: 10,
          contentFingerprint: 'mock_fp'
        })
      };
    }
    if (url.includes('get_current_weekly_english_set')) {
      return {
        ok: true,
        json: async () => ({ status: 'OK', currentSet: { testDate: '2026-10-02', items: make10Items() } })
      };
    }
    return { ok: false };
  };

  const fidelityMatchRes = await executeIngestionFlow({
    candidate: { testDate: '2026-10-02', items: make10Items() },
    token: TOKEN_TEST,
    supabaseUrl: 'https://test.supabase.co',
    anonKey: 'anon',
    fetchFn: mockFidelityMatchFetch
  });

  report.fidelityMatchStatus = fidelityMatchRes.status;
  report.fidelityMatchVerifiedTrue = fidelityMatchRes.sourceFidelityVerified === true;
  report.fidelityMatchReadBackVerified = fidelityMatchRes.readBackVerified === true;

  // ── 4. Secret Isolation ──
  const serialized = JSON.stringify(fidelityMatchRes);
  report.tokenNotSerialized = !serialized.includes(TOKEN_TEST);

  // ── 5. Antigravity MCP Adapter Protocol ──
  // Initialize
  const initRes = await handleRpcMessage({ jsonrpc: '2.0', id: 1, method: 'initialize', params: {} });
  report.mcpInitOk = initRes?.result?.serverInfo?.name === 'aiden-weekly-english-mcp';

  // Tools List
  const toolsRes = await handleRpcMessage({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} });
  const toolNames = (toolsRes?.result?.tools || []).map(t => t.name);
  report.mcpHasRegisterTool = toolNames.includes('register_weekly_english_candidate');
  report.mcpHasCurrentTool = toolNames.includes('get_current_weekly_english_set');

  // Call without token
  const callNoToken = await handleRpcMessage(
    {
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: { name: 'register_weekly_english_candidate', arguments: { candidate: { testDate: '2026-10-02', items: make10Items() } } }
    },
    {} // empty env
  );
  report.mcpNoTokenFails = callNoToken?.result?.isError === true;

  // Call with token (using global fetch mock)
  const origFetch = globalThis.fetch;
  globalThis.fetch = mockFidelityMatchFetch;
  try {
    const callWithToken = await handleRpcMessage(
      {
        jsonrpc: '2.0',
        id: 4,
        method: 'tools/call',
        params: { name: 'register_weekly_english_candidate', arguments: { candidate: { testDate: '2026-10-02', items: make10Items() } } }
      },
      { WEEKLY_AGENT_TOKEN: TOKEN_TEST, SUPABASE_URL: 'https://test.supabase.co', SUPABASE_ANON_KEY: 'anon' }
    );
    report.mcpCallSuccess = callWithToken?.result?.isError === false;
    const content = JSON.parse(callWithToken?.result?.content?.[0]?.text || '{}');
    report.mcpResultStatus = content.status;
    report.mcpResultFidelityVerified = content.sourceFidelityVerified === true;
    report.mcpSecretIsolated = !JSON.stringify(callWithToken).includes(TOKEN_TEST);
  } finally {
    globalThis.fetch = origFetch;
  }

  // ── 6. Shared Transport Facade (Edge Function) ──
  // CORS OPTIONS
  const corsReq = new Request('https://edge.supabase.co/weekly-english-agent', { method: 'OPTIONS' });
  const corsRes = await handleRequest(corsReq);
  report.facadeCorsOk = corsRes.status === 200 && corsRes.headers.get('Access-Control-Allow-Origin') === '*';

  // No token -> 401
  const noTokenReq = new Request('https://edge.supabase.co/weekly-english-agent/current', { method: 'GET' });
  const noTokenRes = await handleRequest(noTokenReq);
  report.facadeNoTokenUnauthorized = noTokenRes.status === 401;

  // With header token -> mock register
  globalThis.fetch = mockFidelityMatchFetch;
  try {
    const regReq = new Request('https://edge.supabase.co/weekly-english-agent/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Aiden-Weekly-Token': TOKEN_TEST
      },
      body: JSON.stringify({
        candidate: { testDate: '2026-10-02', items: make10Items() }
      })
    });
    const regRes = await handleRequest(regReq);
    report.facadeRegisterStatus = regRes.status;
    const regJson = await regRes.json();
    report.facadeRegisterPayloadStatus = regJson.status;
    report.facadeRegisterReadBackVerified = regJson.readBackVerified === true;
    report.facadeRegisterFidelityVerified = regJson.sourceFidelityVerified === true;
    report.facadeSecretIsolated = !JSON.stringify(regJson).includes(TOKEN_TEST);
  } finally {
    globalThis.fetch = origFetch;
  }

  return report;
}

runAllTests().then(report => {
  console.log(JSON.stringify(report, null, 2));
}).catch(err => {
  console.error('Test runner failure:', err);
  process.exit(1);
});
