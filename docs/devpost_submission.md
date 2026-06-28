# QwenBridge — Devpost Submission

> Copy-paste each section into the Devpost form fields.

---

## Project Name
QwenBridge

## Track
Track 3 — Agent Society

## Tagline (one line)
Multi-agent AI hub with AgentWorld pre-flight simulation — predict before you act.

---

## Inspiration

Every AI assistant today runs blind — it proposes actions, executes them, and discovers failures after the fact. We asked: what if agents could *simulate* their plan before running it?

Qwen-AgentWorld, released June 22 2026, is the world's first language world model — trained to simulate 7 agent environments (Terminal, Web Browser, MCP, Search, Android, Desktop, SWE). We built QwenBridge to put this power at the center of a production-ready multi-agent system.

---

## What It Does

QwenBridge is an open-source multi-agent orchestration hub with five key capabilities:

**1. AgentWorld Pre-flight Simulation**
Before executing any complex plan, QwenBridge feeds the proposed subtasks to Qwen-AgentWorld. The world model predicts outcomes and flags risks (destructive operations, financial actions, privilege escalation) before a single API call is made. HIGH-risk plans automatically receive a safety checkpoint.

**2. Cost-Aware Model Routing**
Tasks are automatically routed to the right Qwen tier:
- Image/video → `qwen-vl-max` (15× cheaper than GPT-4o Vision)
- Reasoning/math → `qwen3-max-thinking` (12× cheaper than o3)
- Code → `qwen-coder-plus` (8× cheaper than GPT-4o)
- Simple text → `qwen-turbo` (50× cheaper than GPT-4o)

Every response includes a cost breakdown showing exactly what was spent.

**3. Persistent Cross-Session Memory**
Memory Agent stores and retrieves facts across sessions via Alibaba Cloud Table Store. Context from last week's conversation is available in today's.

**4. MCP + REST + WebSocket — Works Everywhere**
- Claude Code, Cursor, and Windsurf connect via the MCP stdio server (7 tools)
- Web/mobile apps use the FastAPI REST API
- Real-time agent progress streams over WebSocket

**5. Multi-Agent Architecture**
Four specialized agents collaborate on every task:
- Orchestrator — decomposes requests, coordinates agents
- Memory Agent — persistent context (Alibaba Table Store)
- Tool Agent — code execution, HTTP, file operations (Alibaba OSS)
- Multimodal Agent — vision analysis via qwen-vl-max

---

## How We Built It

**Stack:**
- Python 3.12 + FastAPI for the REST/WebSocket server
- MCP SDK (Anthropic) for the stdio MCP server
- Qwen APIs via DashScope (OpenAI-compatible client)
- Alibaba Cloud Table Store for persistent memory
- Alibaba Cloud OSS for file storage
- Qwen-AgentWorld (offline pattern-matching + API simulation modes)
- Rich for beautiful terminal output during demos

**Key design decisions:**
- MOCK_MODE=true lets the entire pipeline run without API keys for development/testing
- Automatic fallback chain: max → plus → turbo on rate limits
- AgentWorld runs offline (pattern matching) if the full 35B model isn't available, ensuring the safety layer never blocks execution

**Testing:**
- 29 tests (unit + integration), all running in mock mode — zero API calls needed for CI
- GitHub Actions CI runs on every push

---

## Challenges

**1. AgentWorld integration without running 35B locally**
The 35B model requires significant hardware. We built a dual-mode simulator: when the model isn't available, pattern-based risk detection runs offline. This makes the predict-before-act feature available even in constrained environments.

**2. MCP library version fragmentation**
fastmcp has gone through 3 major versions (0.4, 2.x, 3.x) with incompatible APIs. We settled on the official `mcp` SDK (Anthropic's own) for the MCP server to ensure long-term compatibility.

**3. Cost tracking across async agent calls**
The model router tracks token usage per model per session using a module-level accumulator. Making this thread-safe and session-aware required careful design to avoid double-counting in the orchestrator's parallel dispatch.

---

## Accomplishments

- Full multi-agent pipeline running in under 8 hours of development
- 29/29 tests passing in CI with no API keys
- 7 MCP tools exposing the full QwenBridge capability surface
- AgentWorld correctly flags `delete`, `rm`, `payment`, `credential` patterns as high-risk
- REST API with docs at `/docs`, WebSocket for real-time streaming
- Apache 2.0 licensed — fully open source

---

## What We Learned

The Qwen model tier pricing makes genuinely cost-aware routing viable. Routing a simple query to `qwen-turbo` instead of `qwen-max` is a 32× cost reduction with no quality loss for most tasks. The routing logic pays for itself within the first few hundred queries.

AgentWorld as a "metacognitive" agent — one that reasons about what other agents will do — is a powerful pattern that doesn't exist anywhere else. We barely scratched the surface; with the full 397B model, the simulation fidelity jumps dramatically.

---

## What's Next

- Full AgentWorld 397B API integration when Qwen Cloud exposes it
- Tool-use streaming so the WebSocket shows individual agent steps in real time
- Agent memory graph — visualize what each session has remembered
- Slack + Telegram integrations via OpenClaw skill pack
- More MCP tools: Git operations, database queries, calendar

---

## Built With

`python` `fastapi` `mcp-sdk` `qwen-cloud` `dashscope` `alibaba-cloud` `table-store` `alibaba-oss` `qwen-agentworld` `qwen-vl` `qwen-turbo` `multi-agent` `orchestration`

---

## Links

- **GitHub**: https://github.com/thomasvuong/QwenBridge
- **License**: Apache 2.0
- **Demo video**: [to be added]
- **Alibaba Cloud deployment proof**: [to be added]
