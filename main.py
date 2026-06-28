"""
main.py — QwenBridge REST API + WebSocket server (FastAPI, port 8765).

MCP tools live in mcp_server.py — run that for Claude Code / Cursor / Windsurf.
This file is the REST/WebSocket interface for web and mobile clients.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from rich.console import Console

import config
from agents.orchestrator import Orchestrator
from agents.memory_agent import MemoryAgent
from agents.multimodal_agent import MultimodalAgent
from router.model_router import session_cost_report

console = Console()

_orchestrator: Orchestrator | None = None
_memory:       MemoryAgent   | None = None
_vision:       MultimodalAgent | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = "MOCK" if config.MOCK_MODE else "LIVE"
    console.print(f"[bold green]QwenBridge REST API starting [{mode} mode] ...[/bold green]")
    get_orchestrator()
    yield
    console.print("[bold]QwenBridge shutdown[/bold]")


app = FastAPI(
    title="QwenBridge",
    version="1.0.0",
    description="Multi-agent AI hub powered by Qwen Cloud. MCP tools: run `python mcp_server.py`",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:    str
    session_id: str = "default"
    complexity: str = "medium"


class VisionRequest(BaseModel):
    image_url:  str
    prompt:     str = "Describe this image."
    session_id: str = "default"


class MemoryStoreRequest(BaseModel):
    session_id: str
    key:        str
    value:      str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "service":   "QwenBridge",
        "version":   "1.0.0",
        "mock_mode": config.MOCK_MODE,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    orch   = get_orchestrator()
    result = await orch.run(req.message, session_id=req.session_id)
    return JSONResponse(result)


@app.post("/api/vision")
async def vision(req: VisionRequest):
    global _vision
    if _vision is None:
        _vision = MultimodalAgent()
    result = await _vision.analyze_url(req.image_url, req.prompt)
    return JSONResponse(result)


@app.post("/api/memory")
async def memory_store(req: MemoryStoreRequest):
    global _memory
    if _memory is None:
        _memory = MemoryAgent()
    key = await _memory.store(req.session_id, {"key": req.key, "value": req.value})
    return {"stored": True, "entry_key": key, "session_id": req.session_id}


@app.get("/api/memory/{session_id}")
async def memory_recall(session_id: str, limit: int = 10):
    global _memory
    if _memory is None:
        _memory = MemoryAgent()
    memories = await _memory.recall(session_id, limit=limit)
    return {"session_id": session_id, "memories": memories}


@app.get("/api/cost")
async def cost():
    return session_cost_report()


@app.websocket("/ws/{session_id}")
async def ws_stream(ws: WebSocket, session_id: str):
    await ws.accept()
    try:
        while True:
            data    = await ws.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")
            if not message:
                await ws.send_json({"error": "No message"})
                continue
            await ws.send_json({"status": "processing", "session_id": session_id})
            orch   = get_orchestrator()
            result = await orch.run(message, session_id=session_id)
            await ws.send_json({
                "status": "done",
                "answer": result["answer"],
                "cost":   result["cost_report"].get("__total_usd", 0),
            })
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.MCP_HOST,
        port=config.MCP_PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False,
    )
