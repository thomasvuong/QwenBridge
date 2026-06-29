# QwenBridge

> Multi-agent AI orchestration hub powered by the Qwen Cloud ecosystem.  
> **Hackathon submission**: Global AI Hackathon Series with Qwen Cloud — Track 3: Agent Society

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Deployed on Alibaba Cloud](https://img.shields.io/badge/Deployed-Alibaba%20Cloud-orange.svg)]()
[![CI](https://github.com/thomasvuong/QwenBridge/actions/workflows/ci.yml/badge.svg)](https://github.com/thomasvuong/QwenBridge/actions/workflows/ci.yml)

---

## What is QwenBridge?

QwenBridge is an open-source multi-agent orchestration hub that:

1. **Routes tasks intelligently** across 5 Qwen model tiers — automatically picking the cheapest model that can handle the task (3–50x cheaper than GPT-4o)
2. **Simulates before executing** using Qwen-AgentWorld — the world's first agent world model predicts consequences and flags risks before any agent acts
3. **Persists memory across sessions** via Alibaba Cloud Table Store — agents remember context between conversations
4. **Exposes everything as MCP tools** — works with Claude Code, Cursor, Windsurf, and any MCP-compatible AI editor
5. **Handles vision, audio, text, and code** — unified interface across Qwen's multimodal models

## Architecture

```
User / MCP Client / REST API
         ↓
  QwenBridge MCP Server (FastAPI + FastMCP)
         ↓
  Orchestrator ← AgentWorld pre-flight simulation
         ↓
  ┌──────────────────────────────────┐
  │ Memory Agent │ Tool Agent │ VL  │
  └──────────────────────────────────┘
         ↓                    ↓
  Qwen Cloud (DashScope)    Alibaba Cloud
  turbo/plus/max/vl/coder   OSS + Table Store
```

See [docs/architecture.mmd](docs/architecture.mmd) for the full Mermaid diagram.

## Key Features

### 1. AgentWorld Pre-flight Simulation
Before executing any complex multi-step plan, QwenBridge feeds the proposed subtasks to Qwen-AgentWorld — a language world model that simulates 7 agent environments. If risk is HIGH, safety checks are automatically inserted.

```python
# Simulate before execute
result = await qwen_simulate("delete all test records from production")
# → risk: high, reason: destructive operation, adjustments: [add confirmation step]
```

### 2. Cost-Aware Model Routing
```
image/video  → qwen-vl-max      ($0.16/$0.64 /1M)  — 15x cheaper than GPT-4o Vision
reasoning    → qwen3-max-think  ($1.20/$6.00 /1M)  — 12x cheaper than o3
code         → qwen-coder-plus  ($0.30/$1.50 /1M)  — 8x cheaper than GPT-4o
simple       → qwen-turbo       ($0.05/$0.20 /1M)  — 50x cheaper than GPT-4o
```

### 3. Persistent Cross-Session Memory
```python
await qwen_memory_store(session_id="project-x", key="deadline", value="July 9 2026")
# Tomorrow, in a new session:
await qwen_memory_recall(session_id="project-x")  # → ["deadline: July 9 2026"]
```

### 4. MCP + OpenClaw Cross-Platform Install
One server, works everywhere:
```json
{
  "mcpServers": {
    "qwenbridge": { "url": "http://localhost:8765/mcp", "transport": "http" }
  }
}
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_GITHUB/qwenbridge.git
cd qwenbridge

# 2. Configure
cp .env.example .env
# Edit .env: fill in DASHSCOPE_API_KEY + Alibaba Cloud credentials

# 3. Install
pip install -r requirements.txt

# 4. Run
python main.py
# → Server at http://localhost:8765
# → MCP endpoint at http://localhost:8765/mcp
# → REST API docs at http://localhost:8765/docs
```

## MCP Tools

| Tool | Description |
|---|---|
| `qwen_chat` | Main orchestration — routes to optimal model |
| `qwen_vision` | Image/diagram/document analysis via Qwen-VL |
| `qwen_memory_store` | Persist facts to Alibaba Table Store |
| `qwen_memory_recall` | Retrieve session memory |
| `qwen_code` | Execute Python code safely |
| `qwen_simulate` | AgentWorld pre-flight risk check |
| `qwen_cost_report` | Real-time cost breakdown |

## REST API

```bash
# Chat
curl -X POST http://localhost:8765/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain the Qwen-AgentWorld architecture", "session_id": "demo"}'

# Vision
curl -X POST http://localhost:8765/api/vision \
  -d '{"image_url": "https://example.com/diagram.png", "prompt": "Convert to JSON spec"}'

# Cost report
curl http://localhost:8765/api/cost
```

## Deployment (Alibaba Cloud)

```bash
# Provision infrastructure (run once)
export ALIBABA_ACCESS_KEY_ID=...
export ALIBABA_ACCESS_KEY_SECRET=...
bash deploy/alibaba/setup.sh

# Update .env with the Table Store endpoint printed by setup.sh
```

## Hackathon Track

**Track 3 — Agent Society**  
QwenBridge demonstrates sophisticated agent collaboration:
- 4 specialized agents with distinct roles (Orchestrator, Memory, Tool, Multimodal)
- AgentWorld as a "metacognitive" 5th agent that validates plans
- Measurable task decomposition with cost tracking
- Full deployment on Alibaba Cloud infrastructure

## License

Apache 2.0 — see [LICENSE](LICENSE).
