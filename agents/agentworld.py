"""
agentworld.py — Qwen-AgentWorld pre-flight simulator.

Uses the AgentWorld model to simulate proposed agent actions BEFORE execution.
"Predict before you act" — the key differentiator for QwenBridge.

Supports both API mode (pointing at a vLLM/transformers server running AgentWorld)
and a lightweight offline mode that pattern-matches known risky actions.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx
from rich.console import Console

import config

console = Console()

RISKY_PATTERNS = [
    (re.compile(r"\bdelete\b|\brm\b|\bdrop\b|\btruncate\b", re.I), "destructive operation"),
    (re.compile(r"\bpayment\b|\bcharge\b|\bbilling\b", re.I),       "financial action"),
    (re.compile(r"\bpassword\b|\bsecret\b|\bcredential\b", re.I),   "credential access"),
    (re.compile(r"\bsudo\b|\bchmod\b|\bchown\b", re.I),             "privilege escalation"),
    (re.compile(r"\bpublish\b|\bdeploy\s+to\s+prod\b", re.I),       "production deployment"),
]

AGENTWORLD_SYSTEM = """You are Qwen-AgentWorld, a simulation environment that predicts the consequences
of multi-agent actions before they are executed.

Given a list of planned subtasks, simulate:
1. What each agent will actually do
2. Whether any risks exist (data loss, security, irreversibility)
3. Whether the plan will succeed or fail

Respond with JSON:
{
  "simulation": [
    {"agent": "...", "predicted_action": "...", "outcome": "success|partial|fail", "notes": "..."}
  ],
  "risk": "low|medium|high",
  "risk_reason": "...",
  "recommended_adjustments": ["..."]
}"""


class AgentWorldSimulator:
    def __init__(self):
        self.mode = config.AGENTWORLD_MODE  # "api" or "local"

    async def simulate(self, subtasks: list[dict]) -> dict[str, Any]:
        console.print("[magenta]⟳ AgentWorld: simulating plan...[/magenta]")
        tasks_text = json.dumps(subtasks, indent=2)

        # Fast offline pattern check
        fast_risks = self._pattern_check(tasks_text)

        if self.mode == "api":
            result = await self._api_simulate(tasks_text)
        else:
            result = self._offline_simulate(subtasks, fast_risks)

        risk_level = result.get("risk", "low")
        emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk_level, "⚪")
        console.print(f"[magenta]AgentWorld result: {emoji} {risk_level} risk[/magenta]")
        if result.get("risk_reason"):
            console.print(f"[magenta]  Reason: {result['risk_reason']}[/magenta]")
        return result

    def _pattern_check(self, text: str) -> list[str]:
        found = []
        for pattern, label in RISKY_PATTERNS:
            if pattern.search(text):
                found.append(label)
        return found

    async def _api_simulate(self, tasks_text: str) -> dict:
        """Call AgentWorld running as an OpenAI-compat server (vLLM / local transformers)."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{config.AGENTWORLD_API_URL}/chat/completions",
                    json={
                        "model": config.AGENTWORLD_MODEL,
                        "messages": [
                            {"role": "system",  "content": AGENTWORLD_SYSTEM},
                            {"role": "user",    "content": f"Simulate these subtasks:\n{tasks_text}"},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                return json.loads(text)
        except Exception as e:
            console.print(f"[yellow]AgentWorld API unavailable ({e}), using offline mode[/yellow]")
            return self._offline_simulate([], self._pattern_check(tasks_text))

    def _offline_simulate(self, subtasks: list[dict], fast_risks: list[str]) -> dict:
        """Lightweight offline simulation based on pattern matching."""
        sim = []
        for st in subtasks:
            task_text = st.get("task", "")
            risks = [label for patt, label in RISKY_PATTERNS if patt.search(task_text)]
            sim.append({
                "agent":            st.get("agent", "unknown"),
                "predicted_action": task_text[:100],
                "outcome":          "fail" if risks else "success",
                "notes":            f"Pattern-detected risks: {', '.join(risks)}" if risks else "No obvious risks",
            })

        combined_risks = fast_risks
        risk_level = "high" if combined_risks else "low"
        return {
            "simulation":              sim,
            "risk":                    risk_level,
            "risk_reason":             ", ".join(combined_risks) if combined_risks else "",
            "recommended_adjustments": [f"Add confirmation step for: {r}" for r in combined_risks],
            "mode":                    "offline_pattern_match",
        }
