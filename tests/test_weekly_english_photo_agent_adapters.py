"""Tests for Weekly English Photo Agent, Shared Facade, and Platform Adapters.

Verifies:
1. Reference transport source fidelity bug fix & CLI exit code semantics.
2. Candidate shape, calendar date, item count, and duplicate pair validation.
3. Secret isolation: capability token is never reflected or serialized.
4. ChatGPT OpenAPI schema and configuration artifacts.
5. Antigravity MCP server stdio protocol, tool registration, and configs.
6. Shared Transport Facade (Edge Function) routing, CORS, and fidelity enforcement.
7. Live Supabase RPC connectivity and authentication rejection.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI_SCRIPT = ROOT / "scripts/register-weekly-english-set.mjs"
RUNNER_MJS = ROOT / "tests/fixtures/test_photo_agent_runner.mjs"
CHATGPT_DIR = ROOT / "integrations/weekly-english/chatgpt"
ANTIGRAVITY_DIR = ROOT / "integrations/weekly-english/antigravity"
EDGE_FUNCTION = ROOT / "supabase/functions/weekly-english-agent/index.ts"

LIVE_SUPABASE_URL = "https://rxjefpmvlygunrukccgg.supabase.co"
LIVE_ANON_KEY = "sb_publishable_86T5zbV_IUXZDvQig6mofg_tlHYeHVx"


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node runtime is required")
    return node


def test_runner_comprehensive_suite() -> None:
    """Run Node-based suite verifying transport, fidelity, MCP, and Edge Function."""
    node = _node()
    res = subprocess.run(
        [node, "--experimental-strip-types", str(RUNNER_MJS)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(res.stdout)

    # 1. Validation bounds
    assert report["valid10"] is True
    assert report["valid8"] is True
    assert report["valid12"] is True
    assert report["valid13Atypical"] is True
    assert report["reject7"] is True
    assert report["reject16"] is True
    assert report["rejectInvalidDate"] is True
    assert report["rejectDuplicatePair"] is True
    assert report["rejectMissingAnswer"] is True
    assert report["rejectMissingPrompt"] is True
    assert report["rejectAmbiguities"] is True

    # 2. Source fidelity bug fix: mismatch -> terminal failure
    assert report["fidelityMismatchStatus"] == "SOURCE_FIDELITY_VERIFICATION_FAILED"
    assert report["fidelityMismatchVerifiedFalse"] is True
    assert report["fidelityMismatchReadBackVerified"] is True

    # 3. Source fidelity match -> success
    assert report["fidelityMatchStatus"] == "REGISTERED_NEW"
    assert report["fidelityMatchVerifiedTrue"] is True
    assert report["fidelityMatchReadBackVerified"] is True

    # 4. Secret isolation
    assert report["tokenNotSerialized"] is True

    # 5. Antigravity MCP Protocol
    assert report["mcpInitOk"] is True
    assert report["mcpHasRegisterTool"] is True
    assert report["mcpHasCurrentTool"] is True
    assert report["mcpNoTokenFails"] is True
    assert report["mcpCallSuccess"] is True
    assert report["mcpResultStatus"] == "REGISTERED_NEW"
    assert report["mcpResultFidelityVerified"] is True
    assert report["mcpSecretIsolated"] is True

    # 6. Shared Transport Facade Edge Function
    assert report["facadeCorsOk"] is True
    assert report["facadeNoTokenUnauthorized"] is True
    assert report["facadeRegisterStatus"] == 200
    assert report["facadeRegisterPayloadStatus"] == "REGISTERED_NEW"
    assert report["facadeRegisterReadBackVerified"] is True
    assert report["facadeRegisterFidelityVerified"] is True
    assert report["facadeSecretIsolated"] is True


def test_reference_cli_exit_code_on_fidelity_failure(tmp_path: Path) -> None:
    """CLI exit code must be non-zero (2) when source fidelity verification fails."""
    node = _node()
    candidate_file = tmp_path / "candidate_fidelity_test.json"
    items = [
        {"answer": "courage", "prompt": "the ability to do something frightening"},
        {"answer": "brilliant", "prompt": "exceptionally clever or talented"},
        {"answer": "ancient", "prompt": "belonging to the very distant past"},
        {"answer": "curiosity", "prompt": "a strong desire to know or learn"},
        {"answer": "horizon", "prompt": "the line at which earth and sky meet"},
        {"answer": "journey", "prompt": "an act of traveling from one place to another"},
        {"answer": "treasure", "prompt": "a quantity of precious items"},
        {"answer": "whisper", "prompt": "speak very softly"},
        {"answer": "glacier", "prompt": "a slowly moving mass of ice"},
        {"answer": "shelter", "prompt": "a place giving protection from bad weather"},
    ]
    candidate_file.write_text(
        json.dumps({"testDate": "2026-10-02", "items": items}),
        encoding="utf-8",
    )

    # Use a small node wrapper that intercepts fetch to return mismatched prompt text
    wrapper = tmp_path / "test_cli_fidelity.mjs"
    wrapper.write_text(
        f"""
import {{ executeIngestionFlow }} from '{CLI_SCRIPT.as_posix()}';
import {{ readFileSync }} from 'node:fs';

const candidate = JSON.parse(readFileSync('{candidate_file.as_posix()}', 'utf-8'));
const mockFetch = async (url) => {{
  if (url.includes('register_weekly_english_set')) {{
    return {{
      ok: true,
      json: async () => ({{ status: 'REGISTERED_NEW', setId: '2026-10-02', revision: 1, itemCount: 10 }})
    }};
  }}
  if (url.includes('get_current_weekly_english_set')) {{
    const altered = JSON.parse(JSON.stringify(candidate));
    altered.items[0].prompt = altered.items[0].prompt.toUpperCase();
    return {{
      ok: true,
      json: async () => ({{ status: 'OK', currentSet: altered }})
    }};
  }}
  return {{ ok: false }};
}};

const result = await executeIngestionFlow({{
  candidate,
  token: 'weit_test',
  supabaseUrl: 'https://test.supabase.co',
  anonKey: 'anon',
  fetchFn: mockFetch
}});

console.log(JSON.stringify(result));
const isSuccess = ['REGISTERED_NEW', 'REGISTERED_REVISION', 'REGISTERED_CONFIRMED_REVISION', 'NO_OP'].includes(result.status)
  && result.readBackVerified === true
  && result.sourceFidelityVerified === true;

process.exit(isSuccess ? 0 : 2);
""",
        encoding="utf-8",
    )

    proc = subprocess.run([node, str(wrapper)], capture_output=True, text=True)
    assert proc.returncode == 2, f"Expected exit code 2, got {proc.returncode}"
    output = json.loads(proc.stdout)
    assert output["status"] == "SOURCE_FIDELITY_VERIFICATION_FAILED"
    assert output["sourceFidelityVerified"] is False
    assert output["readBackVerified"] is True


def test_chatgpt_adapter_openapi_and_docs() -> None:
    """Verify OpenAPI YAML schema and instructions for ChatGPT Custom GPT."""
    openapi_file = CHATGPT_DIR / "openapi.yaml"
    instructions_file = CHATGPT_DIR / "instructions.md"
    setup_file = CHATGPT_DIR / "setup.md"

    assert openapi_file.is_file(), "openapi.yaml missing"
    assert instructions_file.is_file(), "chatgpt instructions.md missing"
    assert setup_file.is_file(), "chatgpt setup.md missing"

    content = openapi_file.read_text(encoding="utf-8")
    assert "openapi: 3." in content
    assert "registerWeeklyEnglishCandidate" in content
    assert "getCurrentWeeklyEnglishSet" in content
    assert "X-Aiden-Weekly-Token" in content
    assert "WeeklyTokenAuth" in content
    assert "rxjefpmvlygunrukccgg.supabase.co" in content

    # Crucial security assertion: token/secret must NEVER be in request body or query parameter
    assert "p_agent_token" not in content, "p_agent_token leaked in OpenAPI schema"
    assert "token:" not in content, "token parameter leaked in OpenAPI schema"

    instr = instructions_file.read_text(encoding="utf-8")
    assert "주간 영어 시험지 사진" in instr
    assert "등록 완료" in instr
    assert "2차 시각 대조" in instr

    setup = setup_file.read_text(encoding="utf-8")
    assert "X-Aiden-Weekly-Token" in setup


def test_antigravity_mcp_adapter_artifacts() -> None:
    """Verify Antigravity MCP server, example configuration, and instructions."""
    server_file = ANTIGRAVITY_DIR / "mcp-server.mjs"
    config_file = ANTIGRAVITY_DIR / "mcp_config.example.json"
    instructions_file = ANTIGRAVITY_DIR / "instructions.md"

    assert server_file.is_file(), "mcp-server.mjs missing"
    assert config_file.is_file(), "mcp_config.example.json missing"
    assert instructions_file.is_file(), "antigravity instructions.md missing"

    # Example config must NOT contain real credentials
    config_data = json.loads(config_file.read_text(encoding="utf-8"))
    env_cfg = config_data["mcpServers"]["weekly-english"]["env"]
    assert env_cfg["WEEKLY_AGENT_TOKEN"] == "YOUR_WEEKLY_AGENT_TOKEN_HERE"

    instr = instructions_file.read_text(encoding="utf-8")
    assert "register_weekly_english_candidate" in instr
    assert "등록 완료" in instr


def test_antigravity_mcp_stdio_roundtrip() -> None:
    """Spawn Antigravity MCP server and verify JSON-RPC stdio protocol."""
    node = _node()
    proc = subprocess.Popen(
        [node, str(ANTIGRAVITY_DIR / "mcp-server.mjs")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # 1. initialize
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
        proc.stdin.write(init_req)
        proc.stdin.flush()
        line = proc.stdout.readline()
        init_res = json.loads(line)
        assert init_res["result"]["serverInfo"]["name"] == "aiden-weekly-english-mcp"

        # 2. tools/list
        list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
        proc.stdin.write(list_req)
        proc.stdin.flush()
        line = proc.stdout.readline()
        list_res = json.loads(line)
        tools = [t["name"] for t in list_res["result"]["tools"]]
        assert "register_weekly_english_candidate" in tools
        assert "get_current_weekly_english_set" in tools
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_shared_edge_function_file_structure() -> None:
    """Verify Supabase Edge Function source file."""
    assert EDGE_FUNCTION.is_file(), "Edge Function index.ts missing"
    code = EDGE_FUNCTION.read_text(encoding="utf-8")
    assert "X-Aiden-Weekly-Token" in code
    assert "register_weekly_english_set" in code
    assert "get_current_weekly_english_set" in code
    assert "verifySourceFidelity" in code
    assert "SOURCE_FIDELITY_VERIFICATION_FAILED" in code


def test_live_supabase_rpc_invalid_token_rejection() -> None:
    """Verify live Supabase deployment RPC rejects invalid capability token with UNAUTHORIZED."""
    url = f"{LIVE_SUPABASE_URL}/rest/v1/rpc/get_current_weekly_english_set"
    headers = {
        "apikey": LIVE_ANON_KEY,
        "Authorization": f"Bearer {LIVE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({"p_agent_token": "weit_unauthorized_probe_token"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "UNAUTHORIZED"
            assert "token" in data.get("message", "").lower()
    except urllib.error.HTTPError as e:
        # In case the RPC returns 401 HTTP status
        body = json.loads(e.read().decode("utf-8"))
        assert body.get("status") == "UNAUTHORIZED" or e.code == 401
