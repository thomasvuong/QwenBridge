# QwenBridge Skill

> Connect any AI editor to Qwen Cloud's full model ecosystem with AgentWorld pre-flight simulation, persistent memory, and multi-agent orchestration.

## What This Skill Does

QwenBridge gives your AI assistant access to:

| Capability | Model Used | Cost vs GPT-4o |
|---|---|---|
| Multi-agent orchestration | qwen-max | 6x cheaper |
| Vision / image analysis | qwen-vl-max | 15x cheaper |
| Reasoning / math | qwen3-max-thinking | 12x cheaper |
| Code generation | qwen-coder-plus | 8x cheaper |
| Simple Q&A | qwen-turbo | 50x cheaper |
| Pre-flight simulation | Qwen-AgentWorld | Unique feature |

## Installation

### Option A: MCP (Claude Code / Cursor / Windsurf)

Add to your MCP settings:
```json
{
  "mcpServers": {
    "qwenbridge": {
      "url": "http://localhost:8765/mcp",
      "transport": "http"
    }
  }
}
```

Start the server:
```bash
cd qwenbridge
cp .env.example .env   # fill in DASHSCOPE_API_KEY
pip install -r requirements.txt
python main.py
```

### Option B: OpenClaw Skill Pack

```bash
# In your OpenClaw config
skills:
  - path: ./skills/qwenbridge
    name: qwenbridge
```

## Available Tools

### `qwen_chat`
Main reasoning entry point. Routes to the optimal model automatically.

```
Input:  message, session_id, complexity
Output: answer, cost_usd, agents_used, sim_risk
```

### `qwen_vision`
Analyze images, screenshots, diagrams, or documents.

```
Input:  image_url, prompt, session_id
Output: result, model, tokens
```

### `qwen_memory_store` / `qwen_memory_recall`
Persistent cross-session memory backed by Alibaba Cloud Table Store.

```
Store:  session_id, key, value → entry_key
Recall: session_id, limit      → memories[]
```

### `qwen_code`
Execute Python code safely in a sandboxed subprocess.

```
Input:  code, task_description
Output: stdout, stderr, exit_code
```

### `qwen_simulate`
**Unique feature**: Run AgentWorld pre-flight simulation before any action.

```
Input:  task, subtasks (JSON)
Output: simulation[], risk (low/medium/high), recommended_adjustments[]
```

### `qwen_cost_report`
Real-time cost tracking across all Qwen model calls.

```
Output: {model: {calls, tokens, cost_usd}} per model + __total_usd
```

## Key Feature: Predict Before You Act

Unlike traditional agent systems, QwenBridge uses **Qwen-AgentWorld** to simulate
proposed actions before executing them. AgentWorld is a world model trained to predict
the consequences of AI agent actions across 7 environments.

```
User request → Orchestrator decomposes → AgentWorld simulates
    → Risk check → Execute (if safe) → Synthesize answer
```

If AgentWorld flags HIGH RISK, a safety check subtask is automatically inserted.

## Usage Examples

### Simple chat
```
qwen_chat(message="Summarize the latest AI research on transformers")
```

### Vision analysis
```
qwen_vision(image_url="https://example.com/diagram.png", prompt="Convert to JSON spec")
```

### With memory
```
qwen_memory_store(session_id="project-x", key="deadline", value="July 9 2026")
# Later...
qwen_memory_recall(session_id="project-x")  → ["deadline: July 9 2026", ...]
```

### Pre-flight simulation
```
qwen_simulate(task="Delete all test data from production database")
# Returns: risk=high, risk_reason=destructive operation, recommended_adjustments=[...]
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DASHSCOPE_API_KEY` | Yes | From dashscope.aliyun.com |
| `ALIBABA_ACCESS_KEY_ID` | For memory | Alibaba Cloud RAM user |
| `ALIBABA_ACCESS_KEY_SECRET` | For memory | Alibaba Cloud RAM secret |
| `ALIBABA_TABLESTORE_ENDPOINT` | For memory | Table Store instance endpoint |
| `AGENTWORLD_MODE` | No | "api" or "offline" (default: api) |

## License

Apache 2.0 — see LICENSE file.
