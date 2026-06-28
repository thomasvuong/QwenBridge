"""
model_router.py — Cost-optimized routing across Qwen model tiers.

Routing priority:
  image/video input → qwen-vl-max      ($0.16/$0.64 per 1M)
  reasoning/math    → qwen3-max-think  ($1.20/$6.00 per 1M)
  code generation   → qwen-coder-plus  ($0.30/$1.50 per 1M)
  simple text       → qwen-turbo       ($0.05/$0.20 per 1M)
  medium            → qwen-plus        ($0.40/$1.20 per 1M)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from openai import OpenAI
from rich.console import Console

import config

console = Console()

# Cost per 1M tokens in USD
_COST = {
    config.MODEL_TURBO:        (0.05, 0.20),
    config.MODEL_PLUS:         (0.40, 1.20),
    config.MODEL_MAX:          (1.60, 6.40),
    config.MODEL_MAX_THINKING: (1.20, 6.00),
    config.MODEL_VL_32B:       (0.16, 0.64),
    config.MODEL_CODER:        (0.30, 1.50),
}

TaskType = Literal["vision", "reasoning", "code", "simple", "medium"]


@dataclass
class RoutingDecision:
    model: str
    task_type: TaskType
    reason: str
    cost_per_1m_input: float
    cost_per_1m_output: float


@dataclass
class ModelUsage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    calls: int = 0

    @property
    def cost_usd(self) -> float:
        inp, out = _COST.get(self.model, (0, 0))
        return (self.input_tokens * inp + self.output_tokens * out) / 1_000_000


# Session-level usage tracker
_session_usage: dict[str, ModelUsage] = {}


def route(task: dict) -> RoutingDecision:
    """Decide which Qwen model to use based on task characteristics."""
    has_image   = bool(task.get("image_url") or task.get("image_base64"))
    needs_math  = task.get("requires_reasoning") or task.get("math")
    needs_code  = task.get("requires_code") or "code" in task.get("type", "")
    complexity  = task.get("complexity", "medium")  # simple | medium | complex

    if has_image:
        return RoutingDecision(config.MODEL_VL_32B, "vision",
                               "Image/video input → vision model",
                               *_COST[config.MODEL_VL_32B])
    if needs_math or complexity == "complex":
        return RoutingDecision(config.MODEL_MAX_THINKING, "reasoning",
                               "Complex reasoning required → thinking model",
                               *_COST[config.MODEL_MAX_THINKING])
    if needs_code:
        return RoutingDecision(config.MODEL_CODER, "code",
                               "Code generation → coder model",
                               *_COST[config.MODEL_CODER])
    if complexity == "simple":
        return RoutingDecision(config.MODEL_TURBO, "simple",
                               "Simple task → turbo (cheapest)",
                               *_COST[config.MODEL_TURBO])
    return RoutingDecision(config.MODEL_PLUS, "medium",
                           "Medium complexity → plus",
                           *_COST[config.MODEL_PLUS])


def _mock_call(messages: list[dict], decision: RoutingDecision, **kwargs) -> tuple[str, ModelUsage]:
    """Return a realistic fake response — used when MOCK_MODE=true."""
    import json as _json
    user_content = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    # If caller wants JSON, return a valid stub
    if kwargs.get("response_format", {}).get("type") == "json_object":
        stub = _json.dumps({
            "subtasks": [
                {"agent": "tool_agent",    "task": f"[MOCK] {user_content[:60]}", "priority": 1},
                {"agent": "memory_agent",  "task": "Store task context",          "priority": 2},
            ],
            "requires_simulation": True,
            "complexity": "medium",
            "reasoning": "[MOCK] Simulated orchestration plan",
        })
    else:
        stub = (
            f"[MOCK — {decision.model}] "
            f"This is a simulated response to: \"{user_content[:80]}\". "
            "In production this calls the real Qwen API via DashScope. "
            "The routing logic, AgentWorld simulation, and memory layer are all live."
        )
    latency = 42.0
    usage = _session_usage.setdefault(decision.model, ModelUsage(decision.model))
    usage.input_tokens  += 120
    usage.output_tokens += 80
    usage.latency_ms    += latency
    usage.calls         += 1
    console.print(f"[dim magenta]🔷 MOCK {decision.model} | 120in/80out | {latency:.0f}ms[/dim magenta]")
    return stub, usage


def call(messages: list[dict], task: dict | None = None,
         model: str | None = None, **kwargs) -> tuple[str, ModelUsage]:
    """
    Route and call DashScope. Returns (reply_text, usage).
    Falls back: max → plus → turbo on rate-limit.
    When MOCK_MODE=true, returns a realistic stub without any API call.
    """
    task = task or {}
    decision = route(task) if model is None else RoutingDecision(
        model, "medium", "explicit override", *_COST.get(model, (0, 0)))

    if config.MOCK_MODE:
        return _mock_call(messages, decision, **kwargs)

    client = OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.DASHSCOPE_BASE_URL)
    fallback_chain = [decision.model, config.MODEL_PLUS, config.MODEL_TURBO]

    for attempt_model in fallback_chain:
        console.print(f"[cyan]→ Routing to [bold]{attempt_model}[/bold] "
                      f"({decision.reason})[/cyan]")
        t0 = time.monotonic()
        try:
            resp = client.chat.completions.create(
                model=attempt_model,
                messages=messages,
                **kwargs,
            )
            latency = (time.monotonic() - t0) * 1000

            usage = _session_usage.setdefault(attempt_model, ModelUsage(attempt_model))
            usage.input_tokens  += resp.usage.prompt_tokens
            usage.output_tokens += resp.usage.completion_tokens
            usage.latency_ms    += latency
            usage.calls         += 1

            console.print(f"[green]✓ {attempt_model} | "
                          f"{resp.usage.prompt_tokens}in/{resp.usage.completion_tokens}out | "
                          f"{latency:.0f}ms | ${usage.cost_usd:.5f}[/green]")

            return resp.choices[0].message.content, usage

        except Exception as e:
            if "rate" in str(e).lower() and attempt_model != config.MODEL_TURBO:
                console.print(f"[yellow]⚠ {attempt_model} rate-limited, trying fallback...[/yellow]")
                continue
            raise

    raise RuntimeError("All models exhausted")


def session_cost_report() -> dict:
    """Return cost breakdown for the current session."""
    report = {}
    total = 0.0
    for model, u in _session_usage.items():
        report[model] = {
            "calls": u.calls,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "cost_usd": round(u.cost_usd, 6),
            "avg_latency_ms": round(u.latency_ms / max(u.calls, 1), 1),
        }
        total += u.cost_usd
    report["__total_usd"] = round(total, 6)
    return report
