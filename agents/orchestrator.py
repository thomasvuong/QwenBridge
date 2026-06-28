"""
orchestrator.py — Master coordinator for QwenBridge's multi-agent system.

Decomposes incoming tasks, simulates via AgentWorld, then dispatches
to specialist agents. Implements predict-before-act pattern.
"""
from __future__ import annotations

import json
import asyncio
from typing import Any

from rich.console import Console

import config
from router import model_router
from agents.memory_agent import MemoryAgent
from agents.tool_agent import ToolAgent
from agents.multimodal_agent import MultimodalAgent

console = Console()

SYSTEM_PROMPT = """You are QwenBridge Orchestrator — a master coordinator for a multi-agent AI system.

Your job:
1. Understand the user's task
2. Break it into atomic subtasks with clear agent assignments
3. Check if simulation (AgentWorld) flagged any risks
4. Coordinate execution and synthesize results

Agents available:
- memory_agent: store/retrieve persistent facts and context across sessions
- tool_agent: execute tools (web search, code run, file ops)
- multimodal_agent: analyze images/audio/video, generate visual content

Respond with a JSON plan:
{
  "subtasks": [
    {"agent": "tool_agent", "task": "...", "priority": 1},
    {"agent": "memory_agent", "task": "...", "priority": 2}
  ],
  "requires_simulation": true,
  "complexity": "simple|medium|complex",
  "reasoning": "..."
}"""


class Orchestrator:
    def __init__(self):
        self.memory   = MemoryAgent()
        self.tool     = ToolAgent()
        self.vision   = MultimodalAgent()
        self._agents  = {
            "memory_agent":     self.memory,
            "tool_agent":       self.tool,
            "multimodal_agent": self.vision,
        }

    async def run(self, user_message: str, session_id: str = "default") -> dict[str, Any]:
        console.rule(f"[bold blue]QwenBridge Orchestrator[/bold blue]")
        console.print(f"[blue]Task:[/blue] {user_message[:100]}")

        # 1. Load session memory
        context = await self.memory.recall(session_id, limit=5)
        context_str = "\n".join(f"- {c}" for c in context) if context else "No prior context."

        # 2. Plan decomposition
        plan = await self._decompose(user_message, context_str)
        console.print(f"[cyan]Plan:[/cyan] {json.dumps(plan, indent=2)[:300]}")

        # 3. AgentWorld pre-flight simulation
        sim_result = None
        if plan.get("requires_simulation") or plan.get("complexity") == "complex":
            from agents.agentworld import AgentWorldSimulator
            sim = AgentWorldSimulator()
            sim_result = await sim.simulate(plan["subtasks"])
            if sim_result.get("risk") == "high":
                console.print("[red]⚠ AgentWorld flagged HIGH RISK — adding safety checks[/red]")
                plan["subtasks"].insert(0, {
                    "agent": "memory_agent",
                    "task": f"Safety check: {sim_result.get('risk_reason', '')}",
                    "priority": 0,
                })

        # 4. Execute subtasks in priority order
        results = {}
        for subtask in sorted(plan["subtasks"], key=lambda x: x.get("priority", 99)):
            agent_name = subtask["agent"]
            agent_task = subtask["task"]
            agent = self._agents.get(agent_name)
            if not agent:
                console.print(f"[yellow]Unknown agent: {agent_name}[/yellow]")
                continue
            console.print(f"\n[green]→ {agent_name}:[/green] {agent_task[:80]}")
            try:
                result = await agent.execute(agent_task, session_id=session_id)
                results[agent_name] = result
            except Exception as e:
                console.print(f"[red]✗ {agent_name} failed: {e}[/red]")
                results[agent_name] = {"error": str(e)}

        # 5. Synthesize final answer
        answer = await self._synthesize(user_message, results)

        # 6. Save to memory
        await self.memory.store(session_id, {
            "task": user_message[:200],
            "answer_preview": answer[:300],
            "agent_count": len(results),
        })

        return {
            "answer":      answer,
            "plan":        plan,
            "sim_result":  sim_result,
            "agent_results": results,
            "cost_report": model_router.session_cost_report(),
        }

    async def _decompose(self, task: str, context: str) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context:\n{context}\n\nTask: {task}"},
        ]
        text, _ = model_router.call(
            messages,
            task={"complexity": "medium", "requires_code": False},
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"subtasks": [{"agent": "tool_agent", "task": task, "priority": 1}],
                    "requires_simulation": False, "complexity": "simple"}

    async def _synthesize(self, original_task: str, results: dict) -> str:
        summary_parts = []
        for agent, res in results.items():
            if isinstance(res, dict):
                summary_parts.append(f"{agent}: {json.dumps(res)[:300]}")
            else:
                summary_parts.append(f"{agent}: {str(res)[:300]}")

        messages = [
            {"role": "system", "content": "Synthesize the agent results into a clear, concise answer for the user."},
            {"role": "user",   "content": f"Original task: {original_task}\n\nAgent results:\n" + "\n".join(summary_parts)},
        ]
        text, _ = model_router.call(messages, task={"complexity": "simple"})
        return text
