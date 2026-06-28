"""
main.py — QwenBridge MCP Server + FastAPI REST API.

Exposes QwenBridge capabilities as:
  - MCP tools (for Claude Code, Cursor, Windsurf, any MCP client)
  - REST API (for web/mobile integration)
  - WebSocket stream (for real-time agent progress)
"""
from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from rich.console import Console

import config
from agents.orchestrator import Orchestrator
from agents.memory_agent import MemoryAgent
from agents.multimodal_agent import MultimodalAgent
from agents.tool_agent import ToolAgent
from router.model_router import session_cost_report

console = Console()

# ── MCP server ─────────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="QwenBridge",
    version="1.0.0",
    description=(
        "Multi-agent AI orchestration hub powered by the Qwen ecosystem. "
        "Routes tasks across 5 Qwen model tiers with AgentWorld pre-flight simulation, "
        "persistent memory via Alibaba Cloud, and cross-platform skill execution."
    ),
)

_orchestrator = None
_memory       = None
_vision       = None
_tool         = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


# ── MCP Tools ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def qwen_chat(
    message: Annotated[str, Field(description="User message or task to process")],
    session_id: Annotated[str, Field(description="Session ID for memory continuity")] = "default",
    complexity: Annotated[str, Field(description="Task complexity: simple|medium|complex")] = "medium",
) -> str:
    """
    Main entry point. Route message through QwenBridge multi-agent orchestration.
    Uses AgentWorld to simulate the plan before execution. Returns synthesized answer.
    """
    orch = _get_orchestrator()
    result = await orch.run(message, session_id=session_id)
    return json.dumps({
        "answer":      result["answer"],
        "cost_usd":    result["cost_report"].get("__total_usd", 0),
        "agents_used": list(result["agent_results"].keys()),
        "sim_risk":    result.get("sim_result", {}).get("risk", "n/a") if result.get("sim_result") else "not_simulated",
    }, ensure_ascii=False)


@mcp.tool()
async def qwen_vision(
    image_url: Annotated[str, Field(description="URL or file path to analyze")],
    prompt: Annotated[str, Field(description="What to analyze or extract")] = "Describe this image.",
    session_id: Annotated[str, Field(description="Session ID")] = "default",
) -> str:
    """Analyze images, screenshots, diagrams using Qwen-VL-Max (vision model)."""
    global _vision
    if _vision is None:
        _vision = MultimodalAgent()
    result = await _vision.analyze_url(image_url, prompt)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def qwen_memory_store(
    session_id: Annotated[str, Field(description="Session ID to store under")],
    key: Annotated[str, Field(description="Memory key/label")],
    value: Annotated[str, Field(description="Content to remember")],
) -> str:
    """Store a fact or context in persistent memory (Alibaba Table Store). Survives across sessions."""
    global _memory
    if _memory is None:
        _memory = MemoryAgent()
    entry_key = await _memory.store(session_id, {"key": key, "value": value})
    return json.dumps({"stored": True, "entry_key": entry_key, "session_id": session_id})


@mcp.tool()
async def qwen_memory_recall(
    session_id: Annotated[str, Field(description="Session ID to retrieve from")],
    limit: Annotated[int, Field(description="Max number of memories to return")] = 10,
) -> str:
    """Recall stored memories from a session. Returns recent context facts."""
    global _memory
    if _memory is None:
        _memory = MemoryAgent()
    memories = await _memory.recall(session_id, limit=limit)
    return json.dumps({"session_id": session_id, "memories": memories}, ensure_ascii=False)


@mcp.tool()
async def qwen_code(
    code: Annotated[str, Field(description="Python code to execute")],
    task_description: Annotated[str, Field(description="What this code does")] = "",
) -> str:
    """Execute Python code safely via QwenBridge ToolAgent. Returns stdout/stderr/exit_code."""
    global _tool
    if _tool is None:
        _tool = ToolAgent()
    result = _tool._run_code(code)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def qwen_cost_report() -> str:
    """Return the current session's model usage and cost breakdown."""
    report = session_cost_report()
    return json.dumps(report, indent=2, ensure_ascii=False)


@mcp.tool()
async def qwen_simulate(
    task: Annotated[str, Field(description="Task description to simulate before executing")],
    subtasks: Annotated[str, Field(description="JSON array of subtasks to simulate")] = "[]",
) -> str:
    """
    Run AgentWorld pre-flight simulation on a planned action.
    Returns risk assessment and recommended adjustments before any action is taken.
    """
    from agents.agentworld import AgentWorldSimulator
    sim = AgentWorldSimulator()
    try:
        parsed = json.loads(subtasks) if subtasks != "[]" else [{"agent": "tool_agent", "task": task}]
    except json.JSONDecodeError:
        parsed = [{"agent": "tool_agent", "task": task}]
    result = await sim.simulate(parsed)
    return json.dumps(result, ensure_ascii=False)


# ── FastAPI REST App ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    console.print("[bold green]QwenBridge starting...[/bold green]")
    # Warm up orchestrator
    _get_orchestrator()
    yield
    console.print("[bold]QwenBridge shutdown[/bold]")


app = FastAPI(
    title="QwenBridge",
    version="1.0.0",
    description="Multi-agent AI hub powered by Qwen Cloud",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message:    str
    session_id: str = "default"
    complexity: str = "medium"


class VisionRequest(BaseModel):
    image_url:  str
    prompt:     str = "Describe this image."
    session_id: str = "default"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "QwenBridge", "version": "1.0.0"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    orch = _get_orchestrator()
    result = await orch.run(req.message, session_id=req.session_id)
    return JSONResponse(result)


@app.post("/api/vision")
async def vision(req: VisionRequest):
    global _vision
    if _vision is None:
        _vision = MultimodalAgent()
    result = await _vision.analyze_url(req.image_url, req.prompt)
    return JSONResponse(result)


@app.get("/api/memory/{session_id}")
async def get_memory(session_id: str, limit: int = 10):
    global _memory
    if _memory is None:
        _memory = MemoryAgent()
    memories = await _memory.recall(session_id, limit=limit)
    return {"session_id": session_id, "memories": memories}


@app.get("/api/cost")
async def cost():
    return session_cost_report()


@app.websocket("/ws/{session_id}")
async def websocket_stream(ws: WebSocket, session_id: str):
    """Real-time streaming endpoint — sends agent progress updates."""
    await ws.accept()
    console.print(f"[blue]WS connected: {session_id}[/blue]")
    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")
            if not message:
                await ws.send_json({"error": "No message"})
                continue

            await ws.send_json({"status": "processing", "session_id": session_id})
            orch = _get_orchestrator()
            result = await orch.run(message, session_id=session_id)
            await ws.send_json({
                "status": "done",
                "answer": result["answer"],
                "cost":   result["cost_report"].get("__total_usd", 0),
            })
    except WebSocketDisconnect:
        console.print(f"[dim]WS disconnected: {session_id}[/dim]")


# ── Mount MCP on FastAPI ────────────────────────────────────────────────────────
app.mount("/mcp", mcp.http_app())


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.MCP_HOST,
        port=config.MCP_PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False,
    )
