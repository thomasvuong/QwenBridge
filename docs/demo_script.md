# QwenBridge — 3-Minute Demo Script

**Target runtime:** 2:45 – 3:00 exactly  
**Recording tool:** QuickTime (screen + mic)  
**Upload to:** YouTube (public) or Vimeo  

---

## Setup Before Recording

```bash
cd ~/Downloads/QwenHackathon2026/qwenbridge

# Terminal 1: REST API (with REAL keys when available, or MOCK for practice)
MOCK_MODE=false DASHSCOPE_API_KEY=sk-... python3 main.py

# Terminal 2: MCP server (for Claude Code demo section)
MOCK_MODE=false DASHSCOPE_API_KEY=sk-... python3 mcp_server.py
```

Open browser tabs:
- http://localhost:8765/docs  (FastAPI Swagger)
- GitHub: https://github.com/thomasvuong/QwenBridge

Split your screen: terminal left, browser right.

---

## Script

### [0:00 – 0:20] Hook

> "AI agents today run blind. They plan, they execute, and they discover failures  
> after the fact. What if agents could *simulate* their plan first?"

*Show terminal — type slowly:*

```bash
MOCK_MODE=false python3 mcp_server.py
```

> "QwenBridge adds a predict-before-act layer to any AI workflow,  
> using Qwen-AgentWorld — the world's first agent world model."

---

### [0:20 – 0:50] AgentWorld — The Unique Feature

*In a new terminal:*
```bash
curl -s -X POST http://localhost:8765/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Delete all records from the production users table","session_id":"demo"}' \
  | python3 -m json.tool
```

*Pause on the output. Point to `sim_risk: high`.*

> "The orchestrator decomposes this request into subtasks,  
> runs them through AgentWorld for risk assessment —  
> and gets back: HIGH risk. Destructive operation detected.  
> A safety checkpoint is automatically inserted before anything executes."

*Then run a safe query:*
```bash
curl -s -X POST http://localhost:8765/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What are the cheapest Qwen models for code generation?","session_id":"demo"}' \
  | python3 -m json.tool
```

> "For safe tasks — low risk — it routes to the cheapest model automatically."

---

### [0:50 – 1:20] Cost-Aware Model Routing

*Open http://localhost:8765/docs in browser, navigate to POST /api/cost*

> "Every call is tracked. QwenBridge picks the optimal model for each task:  
> vision goes to qwen-vl-max — 15x cheaper than GPT-4o Vision.  
> Reasoning goes to qwen3-max-thinking — 12x cheaper than o3.  
> Simple queries go to qwen-turbo — 50x cheaper than GPT-4o."

*Show the /api/cost response:*
```bash
curl -s http://localhost:8765/api/cost | python3 -m json.tool
```

> "Real-time cost tracking per model, per session, in USD."

---

### [1:20 – 1:50] Persistent Memory

```bash
# Store a fact
curl -s -X POST http://localhost:8765/api/memory \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","key":"project","value":"QwenBridge hackathon, deadline July 9"}' \
  | python3 -m json.tool

# Recall it (simulate a new session)
curl -s http://localhost:8765/api/memory/demo | python3 -m json.tool
```

> "Memory Agent stores context in Alibaba Cloud Table Store.  
> That 'deadline July 9' fact survives across sessions, across devices,  
> because it's backed by real cloud persistence — not an in-process dict."

---

### [1:50 – 2:20] Vision + MCP Tools

```bash
# Analyze an image
curl -s -X POST http://localhost:8765/api/vision \
  -H "Content-Type: application/json" \
  -d '{"image_url":"https://raw.githubusercontent.com/thomasvuong/QwenBridge/master/docs/architecture.png",
       "prompt":"List all components and connections in this architecture diagram"}' \
  | python3 -m json.tool
```

> "Multimodal Agent uses qwen-vl-max. Show it any image — screenshots, diagrams,  
> documents — and it understands them. 15x cheaper than GPT-4o Vision."

*Switch to Claude Code or Cursor, show the MCP server in `.mcp.json`*

> "And since QwenBridge exposes 7 MCP tools, any AI editor — Claude Code, Cursor,  
> Windsurf — can use it as a drop-in Qwen backend. One config line."

---

### [2:20 – 2:45] Architecture + Wrap

*Show the Mermaid architecture diagram (docs/architecture.png)*

> "Four agents — Orchestrator, Memory, Tool, Vision.  
> AgentWorld as the safety layer.  
> Cost-aware routing across 5 Qwen model tiers.  
> Everything deployed on Alibaba Cloud.  
> Apache 2.0. Open source. Ready to fork."

```bash
# Show tests passing
cd ~/Downloads/QwenHackathon2026/qwenbridge
MOCK_MODE=true python3 -m pytest tests/ -q
```

> "29 tests. Zero API keys needed for CI.  
> That's QwenBridge — predict before you act."

---

### [2:45 – 3:00] Outro

> "Links in the description — GitHub, live demo.  
> Built for the Global AI Hackathon Series with Qwen Cloud, Track 3: Agent Society."

*Cut.*

---

## Recording Tips

- Use 1920×1080, 30fps
- Font size 16+ in terminal for readability
- Have all curl commands pre-typed in a text file — copy-paste, don't type live
- Record at least 2 takes; use the cleaner one
- Upload to YouTube as "unlisted" first to get the link, then set to public before submitting
- Add captions: YouTube auto-generates them — review and fix after upload
