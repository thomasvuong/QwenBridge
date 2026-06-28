"""
mcp_server.py — QwenBridge MCP Server (stdio transport).

Usage in Claude Code ~/.claude.json / .mcp.json:
  {
    "mcpServers": {
      "qwenbridge": {
        "command": "python3",
        "args": ["/path/to/qwenbridge/mcp_server.py"],
        "env": { "MOCK_MODE": "false", "DASHSCOPE_API_KEY": "sk-..." }
      }
    }
  }

Or run directly for testing:
  MOCK_MODE=true python3 mcp_server.py
"""
from __future__ import annotations

import asyncio
import json
import sys

from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated

import config
from agents.orchestrator import Orchestrator
from agents.memory_agent import MemoryAgent
from agents.multimodal_agent import MultimodalAgent
from agents.tool_agent import ToolAgent
from agents.agentworld import AgentWorldSimulator
from router.model_router import session_cost_report

mcp = FastMCP("QwenBridge")

_orch:   Orchestrator    | None = None
_mem:    MemoryAgent     | None = None
_vision: MultimodalAgent | None = None
_tool:   ToolAgent       | None = None


def _get_orch() -> Orchestrator:
    global _orch
    if _orch is None:
        _orch = Orchestrator()
    return _orch


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
async def qwen_chat(
    message:    str,
    session_id: str = "default",
    complexity: str = "medium",
) -> str:
    """
    Route a message through QwenBridge multi-agent orchestration.
    Automatically picks the cheapest Qwen model for the task.
    Uses AgentWorld to simulate the plan before execution.
    Returns synthesized answer + cost breakdown.
    """
    result = await _get_orch().run(message, session_id=session_id)
    return json.dumps({
        "answer":      result["answer"],
        "cost_usd":    result["cost_report"].get("__total_usd", 0),
        "agents_used": list(result["agent_results"].keys()),
        "sim_risk":    result.get("sim_result", {}).get("risk", "n/a")
                       if result.get("sim_result") else "not_simulated",
    }, ensure_ascii=False, indent=2)


@mcp.tool()
async def qwen_vision(
    image_url:  str,
    prompt:     str = "Describe this image.",
    session_id: str = "default",
) -> str:
    """
    Analyze an image, screenshot, or diagram using Qwen-VL-Max.
    15x cheaper than GPT-4o Vision. Supports OCR, object detection, diagram parsing.
    """
    global _vision
    if _vision is None:
        _vision = MultimodalAgent()
    result = await _vision.analyze_url(image_url, prompt)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def qwen_memory_store(
    session_id: str,
    key:        str,
    value:      str,
) -> str:
    """
    Store a fact or context in persistent memory (Alibaba Cloud Table Store).
    Memory survives across sessions and can be recalled anytime.
    """
    global _mem
    if _mem is None:
        _mem = MemoryAgent()
    entry_key = await _mem.store(session_id, {"key": key, "value": value})
    return json.dumps({"stored": True, "entry_key": entry_key, "session_id": session_id})


@mcp.tool()
async def qwen_memory_recall(
    session_id: str,
    limit:      int = 10,
) -> str:
    """
    Recall stored facts and context from a session.
    Returns most recent memories as a list of strings.
    """
    global _mem
    if _mem is None:
        _mem = MemoryAgent()
    memories = await _mem.recall(session_id, limit=limit)
    return json.dumps({"session_id": session_id, "memories": memories}, ensure_ascii=False)


@mcp.tool()
async def qwen_code(
    code:             str,
    task_description: str = "",
) -> str:
    """
    Execute Python code safely via QwenBridge ToolAgent.
    Runs in an isolated subprocess. Dangerous shell commands are blocked.
    Returns stdout, stderr, and exit code.
    """
    global _tool
    if _tool is None:
        _tool = ToolAgent()
    result = _tool._run_code(code)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def qwen_simulate(
    task:     str,
    subtasks: str = "[]",
) -> str:
    """
    Run Qwen-AgentWorld pre-flight simulation on a planned action.
    Returns risk level (low/medium/high) and recommended adjustments
    BEFORE any action is executed. Unique predict-before-act safety layer.
    """
    sim = AgentWorldSimulator()
    try:
        parsed = json.loads(subtasks)
    except json.JSONDecodeError:
        parsed = [{"agent": "tool_agent", "task": task}]
    result = await sim.simulate(parsed)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def qwen_cost_report() -> str:
    """
    Return the current session's Qwen model usage and cost breakdown.
    Shows tokens used and USD cost per model tier.
    """
    return json.dumps(session_cost_report(), indent=2, ensure_ascii=False)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = "MOCK" if config.MOCK_MODE else "LIVE"
    print(f"QwenBridge MCP Server starting [{mode} mode] ...", file=sys.stderr)
    mcp.run()
