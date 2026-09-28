#!/usr/bin/env node
/**
 * @fileoverview Antigravity Local Stdio MCP Adapter for Weekly English Ingestion.
 *
 * Contract:
 * - Ultra-thin Model Context Protocol (MCP) server communicating over stdio.
 * - Imports and reuses canonical reference transport from scripts/register-weekly-english-set.mjs.
 * - Reuses verification, read-back, and fidelity checks without code duplication.
 * - Authenticates using process.env.WEEKLY_AGENT_TOKEN.
 * - Never leaks or serializes tokens into output payloads, logs, or error responses.
 */

import readline from 'node:readline';
import { executeIngestionFlow, fetchCurrentWeeklyEnglishSet } from '../../../scripts/register-weekly-english-set.mjs';

const DEFAULT_SUPABASE_URL = 'https://rxjefpmvlygunrukccgg.supabase.co';
const DEFAULT_ANON_KEY = 'sb_publishable_86T5zbV_IUXZDvQig6mofg_tlHYeHVx';

const TOOLS = [
  {
    name: 'register_weekly_english_candidate',
    description: 'Registers a weekly English vocabulary candidate extracted from a worksheet. Executes canonical PostgreSQL RPC, read-back verification, and exact source-fidelity check.',
    inputSchema: {
      type: 'object',
      properties: {
        candidate: {
          type: 'object',
          description: 'Candidate payload containing testDate and items (prompt <-> answer pairs).',
          properties: {
            schemaVersion: { type: 'integer', default: 1 },
            testDate: { type: 'string', description: 'YYYY-MM-DD test date printed on worksheet' },
            items: {
              type: 'array',
              description: 'Array of 8-15 items mapping answer to prompt.',
              items: {
                type: 'object',
                properties: {
                  answer: { type: 'string', description: 'Word spelling exactly as printed/resolved' },
                  word: { type: 'string', description: 'Alias for answer' },
                  prompt: { type: 'string', description: 'Prompt or definition text with exact source fidelity' },
                  academyDescription: { type: 'string', description: 'Alias for prompt' },
                  ko: { type: 'string', description: 'Optional Korean translation' },
                  icon: { type: 'string', description: 'Optional emoji icon' }
                },
                required: ['answer', 'prompt']
              }
            },
            ambiguities: {
              type: 'array',
              items: { type: 'string' },
              description: 'Any unresolved ambiguities from visual extraction'
            }
          },
          required: ['testDate', 'items']
        },
        confirmation: {
          type: 'object',
          description: 'Optional confirmation payload required only if a prior call returned NEEDS_CONFIRMATION.',
          properties: {
            reason: { type: 'string' },
            candidateFingerprint: { type: 'string' },
            expectedActiveFingerprint: { type: 'string' },
            expectedActiveRevision: { type: 'integer' }
          },
          required: ['reason', 'candidateFingerprint']
        }
      },
      required: ['candidate']
    }
  },
  {
    name: 'get_current_weekly_english_set',
    description: 'Retrieves the currently active canonical weekly English vocabulary set from Supabase.',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  }
];

function sendJsonRpc(response) {
  process.stdout.write(JSON.stringify(response) + '\n');
}

export async function handleRpcMessage(message, env = process.env) {
  const { id, method, params } = message;

  if (method === 'initialize') {
    return {
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: {
          tools: {}
        },
        serverInfo: {
          name: 'aiden-weekly-english-mcp',
          version: '1.0.0'
        }
      }
    };
  }

  if (method === 'notifications/initialized') {
    return null; // Notifications have no response
  }

  if (method === 'tools/list') {
    return {
      jsonrpc: '2.0',
      id,
      result: {
        tools: TOOLS
      }
    };
  }

  if (method === 'tools/call') {
    const { name, arguments: args } = params || {};
    const token = env.WEEKLY_AGENT_TOKEN;
    const supabaseUrl = env.SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const anonKey = env.SUPABASE_ANON_KEY || DEFAULT_ANON_KEY;

    if (!token) {
      return {
        jsonrpc: '2.0',
        id,
        result: {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                status: 'UNAUTHORIZED',
                message: 'WEEKLY_AGENT_TOKEN environment variable is not configured in MCP server environment.'
              }, null, 2)
            }
          ],
          isError: true
        }
      };
    }

    if (name === 'register_weekly_english_candidate') {
      const candidate = args?.candidate;
      const confirmation = args?.confirmation || null;

      try {
        const result = await executeIngestionFlow({
          candidate,
          token,
          supabaseUrl,
          anonKey,
          confirmation
        });

        // Ensure token is never included in the result
        const sanitized = { ...result };
        delete sanitized.token;
        delete sanitized.p_agent_token;

        const isErrorStatus = ['UNAUTHORIZED', 'REJECTED_INVALID', 'ERROR', 'NETWORK_ERROR', 'SOURCE_FIDELITY_VERIFICATION_FAILED', 'READ_BACK_VERIFICATION_FAILED', 'READ_BACK_FAILED'].includes(sanitized.status);

        return {
          jsonrpc: '2.0',
          id,
          result: {
            content: [
              {
                type: 'text',
                text: JSON.stringify(sanitized, null, 2)
              }
            ],
            isError: isErrorStatus
          }
        };
      } catch (err) {
        return {
          jsonrpc: '2.0',
          id,
          result: {
            content: [
              {
                type: 'text',
                text: JSON.stringify({ status: 'INTERNAL_ERROR', message: err.message }, null, 2)
              }
            ],
            isError: true
          }
        };
      }
    }

    if (name === 'get_current_weekly_english_set') {
      try {
        const result = await fetchCurrentWeeklyEnglishSet({
          token,
          supabaseUrl,
          anonKey
        });

        const sanitized = { ...result };
        delete sanitized.token;
        delete sanitized.p_agent_token;

        return {
          jsonrpc: '2.0',
          id,
          result: {
            content: [
              {
                type: 'text',
                text: JSON.stringify(sanitized, null, 2)
              }
            ],
            isError: result.status !== 'OK'
          }
        };
      } catch (err) {
        return {
          jsonrpc: '2.0',
          id,
          result: {
            content: [
              {
                type: 'text',
                text: JSON.stringify({ status: 'INTERNAL_ERROR', message: err.message }, null, 2)
              }
            ],
            isError: true
          }
        };
      }
    }

    return {
      jsonrpc: '2.0',
      id,
      error: {
        code: -32601,
        message: `Tool not found: ${name}`
      }
    };
  }

  return {
    jsonrpc: '2.0',
    id,
    error: {
      code: -32601,
      message: `Method not found: ${method}`
    }
  };
}

// Stdio Line Reader Loop
if (process.argv[1] && process.argv[1].endsWith('mcp-server.mjs')) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  rl.on('line', async (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    try {
      const msg = JSON.parse(trimmed);
      const res = await handleRpcMessage(msg);
      if (res) sendJsonRpc(res);
    } catch (err) {
      sendJsonRpc({
        jsonrpc: '2.0',
        id: null,
        error: { code: -32700, message: `Parse error: ${err.message}` }
      });
    }
  });
}
